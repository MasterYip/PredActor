"""VelBasedGuidance — velocity-based whole-body guidance.

Owns ``(vx, vy, vz, wz)`` command state with thread-safe access.
Builds kinematic targets via ``_build_simple_target`` or
``_build_target_trajectory`` from :mod:`kinematic_utils`.

Replaces v1's ``WholeBodyPosVelGuide``.
"""

from __future__ import annotations

import threading
from typing import Any

import torch

from ..guidance_base import GuidanceBase
from ..guidance_activation_set import GuidanceActivationSet
from ..term_resolver import TermResolver
from ..kinematic_utils import _build_simple_target, _build_target_trajectory


class VelBasedGuidance(GuidanceBase):
    """Velocity-based guidance: vx, vy, vz, wz linearly superposable commands.

    Drives the existing kinematic target builders.  Produces targets for
    all 6 standard kinematic terms (body_pos_local, body_lin_vel_local,
    root_pos_local, root_lin_vel_local, root_rot_local, root_ang_vel_local).

    Command state is thread-safe (GUI writes, inference reads).
    """

    guidance_name: str = "Vel"

    def __init__(
        self,
        activation: GuidanceActivationSet,
        vx_range: tuple = (-5.0, 5.0),
        vy_range: tuple = (-4.0, 4.0),
        vz_range: tuple = (-2.0, 2.0),
        wz_range: tuple = (-2.0, 2.0),
    ):
        super().__init__(activation)
        self._lock = threading.Lock()
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._vz: float = 0.0
        self._wz: float = 0.0
        self._vx_range = vx_range
        self._vy_range = vy_range
        self._vz_range = vz_range
        self._wz_range = wz_range

    # ── Command access (thread-safe) ──────────────────────────────────────

    def set_cmd(self, vx: float, vy: float, vz: float, wz: float) -> None:
        with self._lock:
            self._vx = float(vx)
            self._vy = float(vy)
            self._vz = float(vz)
            self._wz = float(wz)

    def get_cmd(self) -> tuple[float, float, float, float]:
        with self._lock:
            return self._vx, self._vy, self._vz, self._wz

    @property
    def vx_range(self) -> tuple:
        return self._vx_range

    @property
    def vy_range(self) -> tuple:
        return self._vy_range

    @property
    def vz_range(self) -> tuple:
        return self._vz_range

    @property
    def wz_range(self) -> tuple:
        return self._wz_range

    # ── Core ──────────────────────────────────────────────────────────────

    def build_targets(
        self,
        state_unnorm: torch.Tensor,
        term_resolver: TermResolver,
        body_intensity: list[float],
        dt: float,
        n_past_steps: int,
        mode: str,
    ) -> dict[str, torch.Tensor]:
        """Build full kinematic targets (backward-compat)."""
        vx, vy, vz, wz = self.get_cmd()
        builder = _build_simple_target if mode == "simple" else _build_target_trajectory
        return builder(
            state_unnorm, term_resolver,
            vx, vy, vz, wz, dt, n_past_steps,
            body_intensity=body_intensity,
        )

    def build_deltas(
        self,
        state_unnorm: torch.Tensor,
        term_resolver: TermResolver,
        body_intensity: list[float],
        dt: float,
        n_past_steps: int,
        mode: str,
    ) -> dict[str, torch.Tensor]:
        """Build per-term deltas = target - current."""
        targets = self.build_targets(state_unnorm, term_resolver, body_intensity, dt, n_past_steps, mode)
        deltas: dict[str, torch.Tensor] = {}
        for term in self.activation.effective_terms:
            target = targets.get(term)
            if target is None:
                continue
            current = term_resolver.get(state_unnorm, term)
            deltas[term] = target - current
        return deltas

    def get_cmd_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "vx": self._vx, "vy": self._vy, "vz": self._vz, "wz": self._wz,
                "kp": self.activation.kp, "enabled": self.activation.enabled,
            }
