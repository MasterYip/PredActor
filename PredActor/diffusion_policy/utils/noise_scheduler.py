"""NoiseScheduler — single authority for all denoising schedule logic.

Produces:

* ``(K, H)`` noise matrices — used by the DDPM path and rolling DDIM path
  (with ``get_rolling_traj``).
* ``List[(H,), (H,)]`` DDIM pair schedules — the native format returned by
  ``get_schedule()``.
* ``List[StepSpec]`` — scalar or per-position steps for uniform/NS DDIM paths.

All schedule construction lives here; ``DiffuseCLoC`` and ``DiffusePRDP``
only consume.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import torch


# ═════════════════════════════════════════════════════════════════════════════
# StepSpec — shared between NoiseScheduler and DiffuseCLoC
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class StepSpec:
    """One iteration of the denoising loop.

    Timesteps can be:

    * scalar ``int`` — uniform-t: all *H* horizon positions share the same
      noise level (used by the default fast DDIM path with ``joint_ddim_step``).
    * ``(H,)`` long tensor — per-position: each horizon position has its own
      noise level (used by NS and rolling DDIM with ``joint_ns_ddim_step``).
    """

    index: int                      # 0-based step counter
    a_t_cur: torch.Tensor | int     # action noise level *before* this step
    a_t_prev: torch.Tensor | int    # action noise level *after*  this step
    s_t_cur: torch.Tensor | int     # state  noise level *before* this step
    s_t_prev: torch.Tensor | int    # state  noise level *after*  this step


# ═════════════════════════════════════════════════════════════════════════════
# NoiseScheduler
# ═════════════════════════════════════════════════════════════════════════════


class NoiseScheduler:
    """Generates DDIM-compatible noise schedules for joint diffusion inference.

    Replaces the older ``DiffuseCLoC.generate_denoising_matrix`` inlined logic.
    Supports four schedule types, real-time planning, the DDIM ODE step, and
    the rolling-buffer chain extraction.

    Attributes:
        denoising_steps: Total number of training diffusion steps (e.g. 20).
        horizon: Full trajectory length (past + future).
        n_past_steps: Number of past steps (inpainted as clean, t=0).
        n_future_steps: horizon - n_past_steps.
        alphas_cumprod: (denoising_steps,) tensor from DDPM_init.
    """

    def __init__(
        self,
        denoising_steps: int,
        horizon: int,
        n_past_steps: int,
        alphas_cumprod: torch.Tensor,
    ):
        self.denoising_steps = denoising_steps
        self.horizon = horizon
        self.n_past_steps = n_past_steps
        self.n_future_steps = horizon - n_past_steps
        self.alphas_cumprod = alphas_cumprod  # (T,) on model device

    # ═════════════════════════════════════════════════════════════════════
    # Public: (K, H) noise matrices — DDPM path & rolling buffer
    # ═════════════════════════════════════════════════════════════════════

    def get_denoising_matrix(
        self,
        mode: str,
        is_state: bool = False,
        step_size: int = 1,
    ) -> torch.Tensor:
        """Return a ``(K, H)`` noise-level matrix.

        Each row is one denoising iteration; each column is a horizon position.
        This is the format required by the DDPM path (row-at-a-time iteration)
        and by the rolling DDIM path (sub-sample rows, then ``get_rolling_traj``).

        Args:
            mode: ``"full"``, ``"full_decreasing"``, ``"from_xt_decreasing"``,
                  or ``"from_xt_step"``.
            is_state: Slightly changes the horizon calculation for state vs
                      action (mirrors the legacy convention).
            step_size: Coarse jump size for ``"from_xt_step"`` mode.

        Returns:
            ``(K, H)`` long tensor of noise levels in [0, denoising_steps-1].
        """
        T = self.denoising_steps  # noqa: N806

        # Case-tolerant schedule names: the legacy DiffuseCLoC config used
        # "from_xT_*" while DiffusePRDP / this module historically used
        # "from_xt_*". The C++ side matches both spellings; do the same here
        # so full-loop parity does not depend on letter case.
        mode_l = mode.lower()

        if mode_l == "full":
            mat = torch.flip(torch.arange(T), dims=(0,))
            return mat.unsqueeze(1).repeat(1, self.horizon)

        if "from_xt_decreasing" in mode_l:
            if is_state:
                start = max(T - self.n_future_steps, 0)
            else:
                start = max(T - 8 - 1, 0)
        elif mode_l == "full_decreasing":
            start = T - 1
        elif "from_xt_step" in mode_l:
            start = 14
        else:
            raise ValueError(f"Unknown denoising matrix mode: '{mode}'")

        return self._build_noise_matrix(start=start, is_state=is_state,
                                        step_size=step_size)

    def get_rolling_traj(
        self,
        chain: List[Tuple[torch.Tensor, torch.Tensor]],
        t_all: torch.Tensor,
    ) -> torch.Tensor:
        """Extract the rolling buffer from a denoising chain.

        Args:
            chain: ``List[(traj, t)]`` where ``traj`` is ``(B, H, D)`` and
                   ``t`` is ``(H,)`` noise levels.
            t_all: ``(K, H)`` — full noise schedule matrix.

        Returns:
            ``rolled_traj``: ``(B, H-1, D)`` — partially denoised trajectories
            for the next control tick.
        """
        traj = torch.stack([c[0] for c in chain], dim=1)[:, :, 1:, :]  # (B, K, H-1, D)
        idx = torch.stack([c[1] for c in chain])[:, 1:]                 # (K, H-1)
        needed_idx = t_all[0, :-1] + 1
        mask = idx == needed_idx
        missing = torch.nonzero(~mask.any(dim=0), as_tuple=False).flatten()
        if missing.numel():
            raise RuntimeError(
                "rolling trajectory has no matching denoising snapshot for "
                f"horizon columns {missing.tolist()}")

        # One source snapshot is required per shifted horizon column.  Some
        # subsampled schedules contain a later duplicate match; boolean
        # indexing flattened both matches and returned 2*(H-1) elements.
        # Keep the first occurrence, matching the original contract comment.
        row_idx = mask.to(dtype=torch.int64).argmax(dim=0)
        col_idx = torch.arange(mask.shape[1], device=traj.device)
        return traj[:, row_idx, col_idx, :]

    # ═════════════════════════════════════════════════════════════════════
    # Public: (H,) × (H,) pair schedules — DDIM paths
    # ═════════════════════════════════════════════════════════════════════

    def get_schedule(
        self,
        mode: str,
        is_state: bool = False,
        step_size: int = 10,
    ) -> List[Tuple[torch.Tensor, torch.Tensor]]:
        """Return a DDIM timestep schedule as a list of ``(t_cur, t_prev)`` pairs.

        Each element is a pair of ``(H,)`` long tensors — per-position noise
        levels before and after the step.

        Args:
            mode: ``"full"``, ``"full_decreasing"``, ``"from_xt_decreasing"``,
                  or ``"from_xt_step"``.
            is_state: Horizon calculation tweak for state vs action.
            step_size: Coarse jump size for ``"from_xt_step"``.

        Returns:
            ``List[(t_cur, t_prev)]`` where both are ``(H,)`` long tensors.
        """
        T = self.denoising_steps

        # Case-tolerant schedule names — see get_denoising_matrix().
        mode_l = mode.lower()

        if mode_l == "full":
            return self._full_schedule()
        elif mode_l == "full_decreasing":
            return self._decreasing_schedule(start=T - 1, is_state=is_state)
        elif "from_xt_decreasing" in mode_l:
            if is_state:
                start = max(T - self.n_future_steps, 0)
            else:
                start = max(T - 8 - 1, 0)
            return self._decreasing_schedule(start=start, is_state=is_state)
        elif "from_xt_step" in mode_l:
            return self._decreasing_schedule(start=14, is_state=is_state,
                                             step_size=step_size)
        else:
            raise ValueError(f"Unknown schedule mode: '{mode}'")

    # ═════════════════════════════════════════════════════════════════════
    # Public: StepSpec builders — consumed by DiffuseCLoC.act()
    # ═════════════════════════════════════════════════════════════════════

    def build_uniform_ddim_steps(self, ddim_steps: int) -> List[StepSpec]:
        """Uniform-t DDIM — scalar ints, all horizon positions same level.

        Fast-path default: no schedule matrices, no chain tracking, no
        per-position tensors.

        Args:
            ddim_steps: Number of DDIM inference steps (e.g. 5).

        Returns:
            List of ``StepSpec`` with scalar-int timesteps.
        """
        T = self.denoising_steps
        if ddim_steps >= T:
            timesteps = list(range(T - 1, -1, -1))
        else:
            idx = torch.linspace(0, T - 1, ddim_steps).round().long()
            timesteps = sorted({int(i) for i in idx.tolist()}, reverse=True)

        steps: List[StepSpec] = []
        for i, t in enumerate(timesteps):
            t_prev = timesteps[i + 1] if i + 1 < len(timesteps) else -1
            steps.append(StepSpec(index=i, a_t_cur=t, a_t_prev=t_prev,
                                  s_t_cur=t, s_t_prev=t_prev))
        return steps

    def build_ns_ddim_steps(self, ddim_steps: int) -> List[StepSpec]:
        """NS (NoiseScheduler) per-position DDIM steps.

        Uses ``get_schedule("full")``, uniformly sub-samples to *ddim_steps*,
        and re-stitches ``t_prev`` so each jump targets the next sampled
        noise level.

        Args:
            ddim_steps: Number of DDIM inference steps.

        Returns:
            List of ``StepSpec`` with ``(H,)`` tensor timesteps.
        """
        T = self.denoising_steps
        full = self.get_schedule("full")

        if ddim_steps < T:
            indices = self._uniform_indices(len(full), ddim_steps)
            sub = [full[i] for i in indices]
            # Re-stitch: t_prev must target the next *sampled* t_cur
            stitched: List[Tuple[torch.Tensor, torch.Tensor]] = []
            for i, (t_cur, t_prev) in enumerate(sub):
                if i + 1 < len(sub):
                    t_prev = sub[i + 1][0].clone()
                else:
                    # The final sampled transition must reach clean x_0.  This
                    # matters for the one-step schedule, whose only source pair
                    # otherwise points to the next full-schedule noise level.
                    t_prev = torch.full_like(t_cur, -1)
                stitched.append((t_cur, t_prev))
            full = stitched

        steps: List[StepSpec] = []
        for i, (t_cur, t_prev) in enumerate(full):
            steps.append(StepSpec(index=i, a_t_cur=t_cur, a_t_prev=t_prev,
                                  s_t_cur=t_cur.clone(), s_t_prev=t_prev.clone()))
        return steps

    # ═════════════════════════════════════════════════════════════════════
    # Public: real-time planning
    # ═════════════════════════════════════════════════════════════════════

    def plan_realtime(
        self,
        time_limit_ms: float,
        step_time_ms: float,
        mode: str = "full_decreasing",
        is_state: bool = False,
    ) -> List[Tuple[torch.Tensor, torch.Tensor]]:
        """Auto-plan a DDIM schedule within a real-time budget.

        Computes the full schedule for *mode*, then uniformly sub-samples so
        ``total_steps * step_time_ms < time_limit_ms``.

        Args:
            time_limit_ms: Inference budget in milliseconds.
            step_time_ms: Measured cost per model forward pass in ms.
            mode: Base schedule mode.
            is_state: Passed through to ``get_schedule()``.

        Returns:
            Trimmed list of ``(t_cur, t_prev)`` pairs.
        """
        full_schedule = self.get_schedule(mode=mode, is_state=is_state)
        max_steps = max(1, int(time_limit_ms / step_time_ms))

        if max_steps >= len(full_schedule):
            return full_schedule

        indices = self._uniform_indices(len(full_schedule), max_steps)
        sub = [full_schedule[i] for i in indices]

        stitched = []
        for i, (t_cur, t_prev) in enumerate(sub):
            if i + 1 < len(sub):
                t_prev = sub[i + 1][0].clone()
            stitched.append((t_cur, t_prev))
        return stitched

    # ═════════════════════════════════════════════════════════════════════
    # Public: DDIM ODE step
    # ═════════════════════════════════════════════════════════════════════

    def ddim_step(
        self,
        x_t: torch.Tensor,
        x0_pred: torch.Tensor,
        t_cur: torch.Tensor,
        t_prev: torch.Tensor,
        eta: float = 0.0,
    ) -> torch.Tensor:
        """Single DDIM reverse step from ``t_cur → t_prev``.

        DDIM formula (Song et al. 2020):

        .. math::
            \\hat{\\epsilon} = (x_t - \\sqrt{\\bar\\alpha_t} \\, \\hat{x}_0)
                             / \\sqrt{1 - \\bar\\alpha_t}

            x_{t-1} = \\sqrt{\\bar\\alpha_{t-1}} \\, \\hat{x}_0
                    + \\sqrt{1 - \\bar\\alpha_{t-1} - \\sigma_t^2} \\, \\hat{\\epsilon}
                    + \\sigma_t \\epsilon

        With ``η=0`` (deterministic), ``σ_t = 0``.  With ``η=1``, it recovers
        the DDPM posterior.

        Handles per-position noise levels: different ``t_cur`` / ``t_prev`` per
        horizon position.

        Args:
            x_t:     ``(B, H, D)`` noisy trajectory.
            x0_pred: ``(B, H, D)`` predicted clean trajectory.
            t_cur:   ``(H,)`` current timestep per position.
            t_prev:  ``(H,)`` target timestep (``-1`` = step to clean).
            eta:     Stochasticity coefficient (0=DDIM, 1≈DDPM).

        Returns:
            ``x_prev``: ``(B, H, D)`` denoised trajectory.
        """
        device = x_t.device
        B, H, D = x_t.shape

        t_cur_clamped = t_cur.clamp(0, self.denoising_steps - 1).long()
        t_prev_clamped = t_prev.clamp(0, self.denoising_steps - 1).long()
        is_final_step = (t_prev < 0)

        def _lookup(table: torch.Tensor, idx: torch.Tensor) -> torch.Tensor:
            return table[idx.to(device)].view(1, H, 1)

        acp_t = _lookup(self.alphas_cumprod, t_cur_clamped)
        acp_prev = _lookup(self.alphas_cumprod, t_prev_clamped)
        if is_final_step.any():
            acp_prev = acp_prev.clone()
            acp_prev[0, is_final_step, 0] = 1.0

        sqrt_acp_t = acp_t.sqrt()
        sqrt_acp_prev = acp_prev.sqrt()
        sqrt_1m_t = (1.0 - acp_t).sqrt()
        sqrt_1m_p = (1.0 - acp_prev).sqrt()

        eps_hat = (x_t - sqrt_acp_t * x0_pred) / sqrt_1m_t.clamp(min=1e-8)

        if eta == 0.0:
            x_prev = sqrt_acp_prev * x0_pred + sqrt_1m_p * eps_hat
        else:
            ratio = (1.0 - acp_t / acp_prev.clamp(min=1e-8)).clamp(min=0.0)
            sigma_sq = eta ** 2 * (1.0 - acp_prev) / (1.0 - acp_t).clamp(min=1e-8) * ratio
            sigma = sigma_sq.sqrt()
            dir_coef = (1.0 - acp_prev - sigma_sq).clamp(min=0.0).sqrt()
            noise = torch.randn_like(x_t)
            noise[(t_cur == 0).view(1, H, 1).expand(B, H, D)] = 0.0
            x_prev = sqrt_acp_prev * x0_pred + dir_coef * eps_hat + sigma * noise

        return x_prev

    # ═════════════════════════════════════════════════════════════════════
    # Timing helper
    # ═════════════════════════════════════════════════════════════════════

    @staticmethod
    def measure_step_time(
        model_forward_fn,
        n_warmup: int = 2,
        n_measure: int = 5,
    ) -> float:
        """Measure average model forward pass time in ms."""
        for _ in range(n_warmup):
            model_forward_fn()
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        start = time.perf_counter()
        for _ in range(n_measure):
            model_forward_fn()
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        return (time.perf_counter() - start) / n_measure * 1000.0

    # ═════════════════════════════════════════════════════════════════════
    # Private helpers
    # ═════════════════════════════════════════════════════════════════════

    def _build_noise_matrix(
        self,
        start: int,
        is_state: bool,
        step_size: int = 1,
    ) -> torch.Tensor:
        """Build a ``(K, H)`` noise matrix with decreasing per-column values.

        The matrix layout (same as the legacy ``generate_denoising_matrix``):
        column *j* starts at ``start`` and decreases by *step_size* each
        iteration.  Leftmost columns (past positions, < n_past_steps) are
        always 0.

        Returns:
            ``(K, H)`` long tensor, clamped to [0, denoising_steps-1].
        """
        T = self.denoising_steps
        H = self.horizon

        if step_size == 1:
            if is_state:
                end = start + self.n_future_steps
            else:
                end = start + self.n_future_steps + 1
        else:
            end = T + step_size

        first_row = torch.arange(start, end, step_size)
        m = start + 1
        decrement = -torch.arange(m).view(m, 1)
        matrix = (first_row + decrement).clamp(0, T - 1)  # (m, first_row_len)

        n_pad = H - matrix.shape[1]
        if n_pad > 0:
            left_pad = matrix[:, 0:1].repeat(1, n_pad)
            matrix = torch.cat([left_pad, matrix], dim=-1)  # (m, H)
        elif n_pad < 0:
            # The action scheduler uses n_past_steps=0, so n_future_steps ==
            # horizon and the ``+1`` row-width arithmetic can overshoot by one
            # column.  Trim to exactly H columns (positions 0..H-1).
            matrix = matrix[:, :H]

        matrix[:, : self.n_past_steps] = 0
        return matrix

    def _full_schedule(self) -> List[Tuple[torch.Tensor, torch.Tensor]]:
        """Standard DDPM-equivalent: all positions step t → t-1 simultaneously."""
        T = self.denoising_steps
        schedule = []
        for t in range(T - 1, -1, -1):
            t_cur = torch.full((self.horizon,), t, dtype=torch.long)
            t_prev = torch.full((self.horizon,), t - 1, dtype=torch.long)
            t_cur[: self.n_past_steps] = 0
            t_prev[: self.n_past_steps] = 0
            schedule.append((t_cur, t_prev))
        return schedule

    def _decreasing_schedule(
        self,
        start: int,
        is_state: bool,
        step_size: int = 1,
    ) -> List[Tuple[torch.Tensor, torch.Tensor]]:
        """Staggered per-position schedule, expressed as ``(t_cur, t_prev)`` pairs.

        Internally builds the ``(K, H)`` matrix via ``_build_noise_matrix``,
        then converts consecutive rows into ``(t_cur, t_prev)`` pairs.
        """
        H = self.horizon
        matrix = self._build_noise_matrix(start=start, is_state=is_state,
                                          step_size=step_size)

        schedule: List[Tuple[torch.Tensor, torch.Tensor]] = []
        for i in range(len(matrix) - 1):
            schedule.append((matrix[i].clone(), matrix[i + 1].clone()))

        # Last row → clean
        t_cur = matrix[-1].clone()
        t_prev = torch.zeros(H, dtype=torch.long)
        future_mask = torch.arange(H) >= self.n_past_steps
        t_prev[future_mask] = -1
        schedule.append((t_cur, t_prev))

        return schedule

    @staticmethod
    def _uniform_indices(total: int, n: int) -> List[int]:
        """Select *n* evenly-spaced indices from [0, total), always including
        first and last."""
        if n >= total:
            return list(range(total))
        if n == 1:
            return [0]
        step = (total - 1) / (n - 1)
        return [round(i * step) for i in range(n)]
