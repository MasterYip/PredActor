"""PosBasedGuidance — position-based whole-body guidance.

Two independently toggleable sub-features:

* **z-guidance**: Ramps root_pos_local[:,:,2] toward a target height.
  Pelvis body z follows proportionally.  Useful for controlling torso/pelvis
  height independently of velocity commands.

* **ee-guidance** (end-effector): Ramps left/right wrist body positions
  (indices 24–29) toward target deltas from current torso position.
  No world-frame dependency at inference time.

Superposable with :class:`VelBasedGuidance` — PosBased modifies positions
only, leaving velocity terms for VelBased to handle.
"""

from __future__ import annotations

import threading
from typing import Any

import torch

from ..guidance_base import GuidanceBase
from ..guidance_activation_set import GuidanceActivationSet
from ..term_resolver import TermResolver


class PosBasedGuidance(GuidanceBase):
    """Position-based guidance: z-height and end-effector relative positioning.

    Command state is thread-safe (GUI writes, inference reads).
    """

    guidance_name: str = "Pos"

    # ── Wrist body indices in the 30-body layout ──────────────────────────
    WRIST_INDICES = list(range(24, 30))  # 24-29: left+right wrist roll/pitch/yaw

    def __init__(
        self,
        activation: GuidanceActivationSet,
        z_range: tuple = (0.3, 1.1),
        z_init: float = 0.75,
        wrist_ranges: tuple | None = None,
    ):
        """
        Args:
            activation: Guidance activation set.
            z_range: ``(min_z, max_z)`` for GUI slider.
            z_init: Initial target z height.
            wrist_ranges: ``(dx_range, dy_range, dz_range)`` for ee sliders.
                          Defaults to ``((-0.5, 0.5), (-0.5, 0.5), (-0.3, 0.3))``.
        """
        super().__init__(activation)
        self._lock = threading.Lock()
        self._z_range = z_range
        self._z_init = z_init
        self._wrist_ranges = wrist_ranges or ((-0.5, 0.5), (-0.5, 0.5), (-0.3, 0.3))

        # ── Z-guidance state ──────────────────────────────────────────
        self._target_z: float = z_init
        self._z_enabled: bool = True

        # ── EE-guidance state ─────────────────────────────────────────
        self._lwrist_dx: float = 0.0
        self._lwrist_dy: float = 0.0
        self._lwrist_dz: float = 0.0
        self._rwrist_dx: float = 0.0
        self._rwrist_dy: float = 0.0
        self._rwrist_dz: float = 0.0
        self._lwrist_enabled: bool = False
        self._rwrist_enabled: bool = False

    # ── Command access (thread-safe) ──────────────────────────────────────

    def set_z_target(self, z: float) -> None:
        with self._lock:
            self._target_z = float(z)

    def get_z_target(self) -> float:
        with self._lock:
            return self._target_z

    def set_z_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._z_enabled = enabled

    def get_z_enabled(self) -> bool:
        with self._lock:
            return self._z_enabled

    def set_wrist_target(
        self,
        side: str,
        dx: float = 0.0, dy: float = 0.0, dz: float = 0.0,
        enabled: bool = False,
    ) -> None:
        with self._lock:
            if side == "left":
                self._lwrist_dx, self._lwrist_dy, self._lwrist_dz = float(dx), float(dy), float(dz)
                self._lwrist_enabled = enabled
            elif side == "right":
                self._rwrist_dx, self._rwrist_dy, self._rwrist_dz = float(dx), float(dy), float(dz)
                self._rwrist_enabled = enabled

    def get_wrist_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "left": {"dx": self._lwrist_dx, "dy": self._lwrist_dy, "dz": self._lwrist_dz,
                         "enabled": self._lwrist_enabled},
                "right": {"dx": self._rwrist_dx, "dy": self._rwrist_dy, "dz": self._rwrist_dz,
                          "enabled": self._rwrist_enabled},
            }

    @property
    def z_range(self) -> tuple:
        return self._z_range

    @property
    def wrist_ranges(self) -> tuple:
        return self._wrist_ranges

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
        """Build position-only targets: z-height for root+pelvis, delta targets for wrists.

        Velocity terms are NOT produced — those come from :class:`VelBasedGuidance`.
        The manager superposes position targets from this guidance onto any existing
        targets from VelBased.
        """
        B, H, _D = state_unnorm.shape
        device = state_unnorm.device
        now = n_past_steps - 1

        with self._lock:
            target_z = self._target_z
            z_enabled = self._z_enabled
            lw_en = self._lwrist_enabled
            rw_en = self._rwrist_enabled
            ldx, ldy, ldz = self._lwrist_dx, self._lwrist_dy, self._lwrist_dz
            rdx, rdy, rdz = self._rwrist_dx, self._rwrist_dy, self._rwrist_dz

        targets: dict[str, torch.Tensor] = {}

        # ── Z-height guidance ─────────────────────────────────────────────
        if z_enabled:
            root_pos_now = term_resolver.get(state_unnorm[:, now, :], "root_pos_local")
            body_pos_now = term_resolver.get(state_unnorm[:, now, :], "body_pos_local")

            steps = torch.arange(H, dtype=torch.float32, device=device) - now
            steps = steps.clamp(min=0)
            dz = target_z - root_pos_now[:, 2]  # [B] — error from target

            # Ramp z toward target over horizon
            target_root_pos = term_resolver.get(state_unnorm, "root_pos_local").clone()
            for t in range(n_past_steps, H):
                blend = min(1.0, steps[t].item() / max(1, H - n_past_steps))
                target_root_pos[:, t, 2] = root_pos_now[:, 2] + dz * blend

            targets["root_pos_local"] = target_root_pos

            # Pelvis body z follows root z proportionally (body index 0)
            pelvis_z_now = body_pos_now[:, 2:3]  # [B, 1]
            pelvis_offset = pelvis_z_now - root_pos_now[:, 2:3]  # [B, 1]
            target_body_pos = term_resolver.get(state_unnorm, "body_pos_local").clone()
            for t in range(n_past_steps, H):
                target_body_pos[:, t, 2] = target_root_pos[:, t, 2] + pelvis_offset[:, 0]
            targets["body_pos_local"] = target_body_pos

        # ── End-effector guidance ─────────────────────────────────────────
        if lw_en or rw_en:
            # Get or create body_pos_local target
            if "body_pos_local" not in targets:
                targets["body_pos_local"] = term_resolver.get(state_unnorm, "body_pos_local").clone()

            bp = targets["body_pos_local"]
            body_pos_now = term_resolver.get(state_unnorm[:, now, :], "body_pos_local")

            # Reference: torso position (body index 9)
            torso_now = body_pos_now[:, 27:30]  # [B, 3] — body 9 × 3 = offset 27

            steps = torch.arange(H, dtype=torch.float32, device=device) - now
            steps = steps.clamp(min=0)

            # Left wrist (indices 24-26, offsets 72-80)
            if lw_en:
                for i, (body_idx, delta) in enumerate(zip(
                    [24, 25, 26], [ldx, ldy, ldz]
                )):
                    base = body_idx * 3
                    wrist_now = body_pos_now[:, base:base + 3]
                    body_offset = wrist_now - torso_now  # [B, 3] — relative to torso

                    if i == 0:  # x
                        target_body = torso_now[:, 0:1] + body_offset[:, 0:1] + delta
                    elif i == 1:  # y
                        target_body = torso_now[:, 1:2] + body_offset[:, 1:2] + delta
                    else:  # z
                        target_body = torso_now[:, 2:3] + body_offset[:, 2:3] + delta

                    for t in range(n_past_steps, H):
                        blend = min(1.0, steps[t].item() / max(1, H - n_past_steps))
                        current = bp[:, t, base + i]
                        bp[:, t, base + i] = current + (target_body[:, 0] - current) * blend

            # Right wrist (indices 27-29, offsets 81-89)
            if rw_en:
                for i, (body_idx, delta) in enumerate(zip(
                    [27, 28, 29], [rdx, rdy, rdz]
                )):
                    base = body_idx * 3
                    wrist_now = body_pos_now[:, base:base + 3]
                    body_offset = wrist_now - torso_now

                    if i == 0:
                        target_body = torso_now[:, 0:1] + body_offset[:, 0:1] + delta
                    elif i == 1:
                        target_body = torso_now[:, 1:2] + body_offset[:, 1:2] + delta
                    else:
                        target_body = torso_now[:, 2:3] + body_offset[:, 2:3] + delta

                    for t in range(n_past_steps, H):
                        blend = min(1.0, steps[t].item() / max(1, H - n_past_steps))
                        current = bp[:, t, base + i]
                        bp[:, t, base + i] = current + (target_body[:, 0] - current) * blend

        return targets

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
                "target_z": self._target_z, "z_enabled": self._z_enabled,
                "lwrist": f"({self._lwrist_dx:+.2f},{self._lwrist_dy:+.2f},{self._lwrist_dz:+.2f})",
                "rwrist": f"({self._rwrist_dx:+.2f},{self._rwrist_dy:+.2f},{self._rwrist_dz:+.2f})",
                "kp": self.activation.kp, "enabled": self.activation.enabled,
            }
