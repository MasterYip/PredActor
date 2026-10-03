"""GuidanceBase — abstract base for all guidance types in v2.

Each subclass owns a :class:`GuidanceActivationSet`, its own command state,
and provides standard interfaces for classifier-guidance gradient and
PD-mode target application.

The key architectural principle: each guidance produces **deltas**
(changes from current state), NOT full targets.  The
:class:`GuidanceActivationManager` sums deltas across all active
guidances, then computes the gradient ONCE from the combined delta.
This makes superposition mathematically correct — non-overlapping
axis components accumulate independently without double-counting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import torch

from .term_resolver import TermResolver
from .guidance_activation_set import GuidanceActivationSet


class GuidanceBase(ABC):
    """Abstract base for a guidance module.

    Each subclass:
      - Owns a :class:`GuidanceActivationSet` (independently configurable)
      - Owns its command state (a single float per DOF)
      - Builds per-term **delta** tensors via :meth:`build_deltas`
      - Default :meth:`compute_gradient` and :meth:`apply_deltas`
        work directly from deltas — no full-target construction needed
    """

    guidance_name: str = "Base"

    def __init__(self, activation: GuidanceActivationSet):
        self.activation = activation

    # ── Core (subclasses MUST implement) ──────────────────────────────────

    @abstractmethod
    def build_deltas(
        self,
        state_unnorm: torch.Tensor,
        term_resolver: TermResolver,
        body_intensity: list[float],
        dt: float,
        n_past_steps: int,
        mode: str,
    ) -> dict[str, torch.Tensor]:
        """Build per-term delta tensors (change from current state).

        Each returned tensor ``[B, H, D_term]`` is the desired CHANGE from
        the current state at each horizon step.  Past frames (t < n_past_steps)
        have zero delta.  Components not controlled by this guidance are zero.

        Args:
            state_unnorm: ``[B, H, D]`` in physical space.
            term_resolver: Term→slice mapper.
            body_intensity: Per-body weight list (length 30).
            dt: Control timestep in seconds.
            n_past_steps: Number of past observation steps.
            mode: ``"simple"`` or ``"integration"``.

        Returns:
            Dict mapping term names to delta tensors ``[B, H, D_term]``.
        """
        ...

    # ── Gradient / PD (default implementations based on deltas) ───────────

    def compute_gradient(
        self,
        state_unnorm: torch.Tensor,
        term_resolver: TermResolver,
        body_intensity: list[float],
        dt: float,
        n_past_steps: int,
        horizon_weight: torch.Tensor,
        mode: str,
    ) -> torch.Tensor:
        """Compute ∇G for classifier guidance from deltas.

        G(s) = Σ_w w[t]·||s[t] - (s_cur[t] + delta[t])||²
        ∇G   = −2 · delta[t] · w[t]

        Returns a tensor ``[B, H, D]`` in physical space.  The manager
        sums these across all active guidances.
        """
        deltas = self.build_deltas(state_unnorm, term_resolver, body_intensity, dt, n_past_steps, mode)
        grad = torch.zeros_like(state_unnorm)
        w = horizon_weight.to(device=state_unnorm.device, dtype=state_unnorm.dtype)
        kp = self.activation.kp if self.activation.enabled else 0.0

        for term in self.activation.effective_terms:
            d = deltas.get(term)
            if d is None:
                continue
            grad_term = -2.0 * kp * d * w[None, :, None]
            # Accumulate: multiple guidances may write to the same term
            existing = term_resolver.get(grad, term)
            term_resolver.set(grad, term, existing + grad_term)

        return grad

    def apply_deltas(
        self,
        state_unnorm: torch.Tensor,
        term_resolver: TermResolver,
        body_intensity: list[float],
        dt: float,
        n_past_steps: int,
        horizon_weight: torch.Tensor,
        mode: str,
    ) -> None:
        """PD mode: add ``kp * delta * w`` to the state in-place."""
        deltas = self.build_deltas(state_unnorm, term_resolver, body_intensity, dt, n_past_steps, mode)
        w = horizon_weight.to(state_unnorm.device)
        kp = self.activation.kp if self.activation.enabled else 0.0

        for term in self.activation.effective_terms:
            d = deltas.get(term)
            if d is None:
                continue
            correction = kp * d * w[None, :, None]
            current = term_resolver.get(state_unnorm, term)
            term_resolver.set(state_unnorm, term, current + correction)

    # ── GUI (optional) ────────────────────────────────────────────────────

    def build_gui_panel(self, parent, root_tk) -> 'BaseGuiPanel | None':
        """Return a GUI panel widget for this guidance type, or ``None``."""
        return None

    # ── Status ────────────────────────────────────────────────────────────

    @abstractmethod
    def get_cmd_summary(self) -> dict[str, Any]:
        """Return dict summarising current command state (for GUI status bar)."""
        ...

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def stop(self) -> None:
        """Cleanup hook called on teardown."""
        pass
