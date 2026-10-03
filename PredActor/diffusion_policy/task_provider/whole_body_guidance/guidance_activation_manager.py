"""GuidanceActivationManager — holds guidance instances, dispatches, superposes.

The central orchestrator of WholeBodyGuidance v2.  Replaces the monolithic
``WholeBodyGuidance.compute_cost_gradient()`` / ``apply()`` methods with a
clean dispatch loop over independently toggleable :class:`GuidanceBase`
instances.
"""

from __future__ import annotations

import threading
from typing import Optional

import torch

from .guidance_base import GuidanceBase
from .term_resolver import TermResolver
from .body_groups import G1_BODY_GROUPS
from .guidance_types.point_reach import PointReachGuidance


class GuidanceActivationManager:
    """Manages a collection of guidance types with independent activation sets.

    Responsibilities:
      - Holds ordered list of :class:`GuidanceBase` instances
      - Dispatches :meth:`compute_cost_gradient` / :meth:`apply_pd` across
        active guidances, superposing results
      - Provides the activation model used by the GUI activation manager panel
      - Thread-safe activation toggling for debugging
    """

    def __init__(
        self,
        guidances: list[GuidanceBase],
        mode: str = "simple",
        guidance_mode: str = "classifier",
        denoising_steps: int = 20,
        dt: float = 0.02,
        n_past_steps: int = 4,
        horizon: int = 20,
        enable_zeta_comp: bool = True,
        enable_damping_comp: bool = True,
        kp_init: float = 1.0,
    ):
        if mode not in ("simple", "integration"):
            raise ValueError(f"mode must be 'simple' or 'integration', got '{mode}'")
        if guidance_mode not in ("classifier", "pd"):
            raise ValueError(f"guidance_mode must be 'classifier' or 'pd', got '{guidance_mode}'")

        self._guidances = guidances
        self.mode = mode
        self.guidance_mode = guidance_mode
        self.denoising_steps = denoising_steps
        self.dt = dt
        self.n_past_steps = n_past_steps
        self.horizon = horizon
        self.enable_zeta_comp = bool(enable_zeta_comp)
        self.enable_damping_comp = bool(enable_damping_comp)

        self._lock = threading.Lock()
        self._normalizer_obs = None
        self._kp_init = kp_init

        # ── Horizon weight ramp ─────────────────────────────────────────
        ramp_steps = min(4, horizon - n_past_steps)
        weights: list[float] = [0.0] * n_past_steps
        for i in range(ramp_steps):
            weights.append((i + 1) / ramp_steps)
        weights += [1.0] * max(0, horizon - len(weights))
        self._horizon_weight = torch.tensor(weights[:horizon], dtype=torch.float32)

    # ── Guidance access ───────────────────────────────────────────────────

    @property
    def guidances(self) -> list[GuidanceBase]:
        return self._guidances

    def get_active_guidances(self) -> list[GuidanceBase]:
        """Return guidances whose ``activation.enabled`` is ``True``."""
        with self._lock:
            return [g for g in self._guidances if g.activation.enabled]

    def get_guidance_by_index(self, index: int) -> GuidanceBase:
        return self._guidances[index]

    def set_guidance_enabled(self, index: int, enabled: bool) -> None:
        """Thread-safe toggle of a single guidance's activation."""
        with self._lock:
            self._guidances[index].activation.enabled = enabled

    def set_all_enabled(self, enabled: bool) -> None:
        """Thread-safe toggle of all guidances."""
        with self._lock:
            for g in self._guidances:
                g.activation.enabled = enabled

    def get_point_reach_guidance(self) -> PointReachGuidance | None:
        """Return the first PointReachGuidance instance, or None."""
        for g in self._guidances:
            if isinstance(g, PointReachGuidance):
                return g
        return None

    @property
    def has_point_reach(self) -> bool:
        return self.get_point_reach_guidance() is not None

    # ── Normalizer ────────────────────────────────────────────────────────

    def set_normalizer(self, normalizer) -> None:
        """Store the observation normalizer for grad computation."""
        self._normalizer_obs = normalizer['obs'] if normalizer is not None else None

    def _unnormalize_obs(self, x: torch.Tensor) -> torch.Tensor:
        """Unnormalize observation tensor (inverse of normalize, grad-safe)."""
        norm = self._normalizer_obs
        if norm is None:
            return x
        scale = norm.params_dict['scale']
        offset = norm.params_dict['offset']
        return (x - offset.to(x.device)) / scale.to(x.device)

    def _normalize_obs_grad(self, x: torch.Tensor) -> torch.Tensor:
        """Normalize gradient: scale only, no offset (grad-safe forward norm)."""
        norm = self._normalizer_obs
        if norm is None:
            return x
        scale = norm.params_dict['scale']
        return x * scale.to(x.device)

    # ── Composite gradient (classifier mode) ──────────────────────────────

    def compute_cost_gradient(
        self,
        state_norm: torch.Tensor,        # [B, H, D_proj]
        emphasis_mat_inv: torch.Tensor,  # [D_proj, D_obs]
        term_resolver: TermResolver,
    ) -> torch.Tensor:
        """Compute ∇_s G(s) for classifier guidance — sum of all active guidances.

        Args:
            state_norm: Current x0 prediction in projected space.
            emphasis_mat_inv: Pseudoinverse of emphasis matrix.

        Returns:
            ``grad_proj``: ``[B, H, D_proj]`` — ∇G in projected space.
        """
        active = self.get_active_guidances()
        gate_active = self.has_point_reach and self.get_point_reach_guidance().has_world_data
        if not active and not gate_active:
            return torch.zeros_like(state_norm)

        # 1. Unproject + unnormalize to physical space
        state_norm_unproj = state_norm @ emphasis_mat_inv
        state_unnorm = self._unnormalize_obs(state_norm_unproj)

        # 2. Compute per-guidance gradient in physical space, sum
        grad_total = torch.zeros_like(state_unnorm)
        w = self._horizon_weight.to(device=state_norm.device, dtype=state_norm.dtype)

        for guidance in active:
            bi = guidance.activation.build_body_intensity(G1_BODY_GROUPS)
            grad_contribution = guidance.compute_gradient(
                state_unnorm, term_resolver, bi,
                self.dt, self.n_past_steps, w, self.mode,
            )
            grad_total = grad_total + grad_contribution

        # 3. Compensate emphasis matrix damping, then normalize + reproject.
        #
        # The classifier gradient flows through pinv(E).T (once to project the
        # gradient, once during the next predict_x0 unproject).  The product
        #   pinv(E).T @ pinv(E) ≈ diag(1 / (w_i² + 1))
        # dampens physical-space dimensions in proportion to their emphasis
        # weight: a dim with w=4.0 sees ~17× attenuation vs PD mode which
        # operates directly on the physical state with no projection.
        #
        # Multiplying the gradient by the inverse of this diagonal BEFORE
        # projection cancels the damping, restoring magnitude parity with PD.
        if self.enable_damping_comp:
            damping = torch.diag(emphasis_mat_inv.T @ emphasis_mat_inv)
            inv_damping = 1.0 / damping.clamp(min=1e-6)
            grad_total = grad_total * inv_damping[None, None, :]

        # 4. Normalize gradient (scale only) + reproject
        grad_norm = self._normalize_obs_grad(grad_total)
        grad_proj = grad_norm @ emphasis_mat_inv.T

        return grad_proj

    # ── Composite PD application (legacy PD mode) ─────────────────────────

    def apply_pd(
        self,
        state_unnorm: torch.Tensor,
        term_resolver: TermResolver,
    ) -> None:
        """Apply PD correction from all active guidances (in-place).

        Each active guidance's :meth:`apply_deltas` modifies *state_unnorm*
        toward its targets.  Overlapping terms receive superposed corrections
        (the last guidance to write wins for each element).
        """
        active = self.get_active_guidances()
        gate_active = self.has_point_reach and self.get_point_reach_guidance().has_world_data
        if not active and not gate_active:
            return

        w = self._horizon_weight.to(state_unnorm.device)

        for guidance in active:
            bi = guidance.activation.build_body_intensity(G1_BODY_GROUPS)
            guidance.apply_deltas(
                state_unnorm, term_resolver, bi,
                self.dt, self.n_past_steps, w, self.mode,
            )

    # ── Zeta (noise-level scaling) ────────────────────────────────────────

    def get_zeta(
        self,
        state_t: torch.Tensor,
        state_t_prev: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Noise-level-dependent guidance strength scaling.

        For adjacent DDPM steps, ``ζ(k) = k / K_max``.  A DDIM jump integrates
        that same discrete schedule over every skipped level, preserving the
        full-step guidance mass without introducing a sampler-specific gain.
        """
        current = state_t.float()
        denominator = max(self.denoising_steps - 1, 1)
        if not self.enable_zeta_comp or state_t_prev is None:
            return current / denominator

        previous = state_t_prev.to(device=current.device).float()
        mass = (
            current * (current + 1.0)
            - previous * (previous + 1.0)
        ) / 2.0
        return mass.clamp(min=0.0) / denominator

    # ── Horizon weight access ─────────────────────────────────────────────

    @property
    def horizon_weight(self) -> torch.Tensor:
        return self._horizon_weight

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def stop(self) -> None:
        """Call :meth:`stop` on all guidance instances."""
        for g in self._guidances:
            g.stop()
