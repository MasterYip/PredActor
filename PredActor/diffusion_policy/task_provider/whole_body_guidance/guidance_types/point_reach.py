"""PointReachGuidance — world-frame point-reach target guidance.

Extends :class:`VelBasedGuidance` and auto-computes ``vx``, ``vy``, ``vz``
from the world-frame target → pelvis error, rotated to body (yaw) frame.

When no world data is available (GUI-only mode), falls back to manual
velocity commands set via the GUI sliders.
"""

from __future__ import annotations

import math
import threading
from typing import Any, Optional

from .vel_based import VelBasedGuidance
from ..guidance_activation_set import GuidanceActivationSet


class PointReachGuidance(VelBasedGuidance):
    """Auto-computes velocity commands from world-frame target → pelvis error.

    Overrides :meth:`get_cmd` to compute ``vx, vy, vz`` proportional to the
    body-frame error between the current pelvis position and a world-frame
    target point.  ``wz`` is forced to zero (point reach does not control
    yaw).

    Falls back to manual :meth:`set_cmd` values when no world data is
    available (e.g. before the simulator starts feeding positions).
    """

    guidance_name: str = "PointReach"

    def __init__(
        self,
        activation: GuidanceActivationSet,
        vx_range: tuple = (-10.0, 10.0),
        vy_range: tuple = (-10.0, 10.0),
        vz_range: tuple = (-5.0, 5.0),
        wz_range: tuple = (-5.0, 5.0),
        kp_pos: float = 2.0,
        target_x_range: tuple = (-3.0, 3.0),
        target_y_range: tuple = (-3.0, 3.0),
        target_z_range: tuple = (0.0, 2.0),
        target_init: tuple = (0.0, 0.0, 0.8),
    ):
        """
        Args:
            activation: Guidance activation set.
            vx_range: Velocity clip range for computed vx.
            vy_range: Velocity clip range for computed vy.
            vz_range: Velocity clip range for computed vz.
            wz_range: Unused (wz forced to 0 in point-reach mode).
            kp_pos: Position→velocity proportional gain (m⁻¹ → m·s⁻¹).
            target_x_range: GUI slider range for target x.
            target_y_range: GUI slider range for target y.
            target_z_range: GUI slider range for target z.
            target_init: Initial ``(x, y, z)`` target point.
        """
        super().__init__(activation, vx_range, vy_range, vz_range, wz_range)
        self._kp_pos = kp_pos
        self._target_x_range = target_x_range
        self._target_y_range = target_y_range
        self._target_z_range = target_z_range

        # ── World-frame state (updated by env_runner each control step) ──
        self._world_pelvis: Optional[tuple] = None
        self._world_lwrist: Optional[tuple] = None
        self._world_rwrist: Optional[tuple] = None
        self._world_root_pos: Optional[tuple] = None
        self._world_root_yaw: float = 0.0

        # ── Target point (GUI-adjustable, world frame) ───────────────────
        self._target_x: float = target_init[0]
        self._target_y: float = target_init[1]
        self._target_z: float = target_init[2]
        self._guide_lwrist: bool = False
        self._guide_rwrist: bool = False

    # ── World-frame body position feed ────────────────────────────────────

    def set_world_body_pos(
        self,
        pelvis_pos: Optional[tuple] = None,
        left_wrist_pos: Optional[tuple] = None,
        right_wrist_pos: Optional[tuple] = None,
        root_yaw: float = 0.0,
        root_pos: Optional[tuple] = None,
    ) -> None:
        """Update world-frame body positions from the simulator.

        Called by ``env_runner`` each control step.
        """
        with self._lock:
            self._world_pelvis = pelvis_pos
            self._world_lwrist = left_wrist_pos
            self._world_rwrist = right_wrist_pos
            self._world_root_yaw = root_yaw
            self._world_root_pos = root_pos

    def get_point_target(self) -> dict:
        """Return the current point-reach target and wrist toggles."""
        with self._lock:
            return {
                'x': self._target_x, 'y': self._target_y, 'z': self._target_z,
                'guide_lwrist': self._guide_lwrist,
                'guide_rwrist': self._guide_rwrist,
                'has_world_data': self._world_pelvis is not None,
            }

    # ── Command override (auto-computes from world-frame error) ───────────

    def get_cmd(self) -> tuple[float, float, float, float]:
        """Compute velocity commands from world-frame target→pelvis error.

        Returns:
            ``(vx, vy, vz, wz)`` — wz is always 0.0 in point-reach mode.
        """
        with self._lock:
            if self._world_pelvis is not None:
                px, py, pz = self._world_pelvis
                tx, ty, tz = self._target_x, self._target_y, self._target_z
                yaw = self._world_root_yaw

                # World-frame delta
                dx_w, dy_w, dz_w = tx - px, ty - py, tz - pz

                # Rotate to body (yaw) frame
                cos_y, sin_y = math.cos(yaw), math.sin(yaw)
                dx_b = cos_y * dx_w + sin_y * dy_w
                dy_b = -sin_y * dx_w + cos_y * dy_w

                # Proportional velocity command
                kp_p = self._kp_pos
                vx = max(self._vx_range[0], min(self._vx_range[1], kp_p * dx_b))
                vy = max(self._vy_range[0], min(self._vy_range[1], kp_p * dy_b))
                vz = max(self._vz_range[0], min(self._vz_range[1], kp_p * dz_w))
                return vx, vy, vz, 0.0

            # Fallback: manual velocity from GUI / set_cmd
            return self._vx, self._vy, self._vz, 0.0

    # ── Target-point command (thread-safe, GUI writes) ────────────────────

    def set_target(self, x: float, y: float, z: float) -> None:
        with self._lock:
            self._target_x = float(x)
            self._target_y = float(y)
            self._target_z = float(z)

    def set_wrist_guide(self, left: bool, right: bool) -> None:
        with self._lock:
            self._guide_lwrist = left
            self._guide_rwrist = right

    @property
    def target_x_range(self) -> tuple:
        return self._target_x_range

    @property
    def target_y_range(self) -> tuple:
        return self._target_y_range

    @property
    def target_z_range(self) -> tuple:
        return self._target_z_range

    @property
    def kp_pos(self) -> float:
        return self._kp_pos

    @property
    def has_point_reach(self) -> bool:
        """Whether point-reach logic is active (always True for this class)."""
        return True

    @property
    def has_world_data(self) -> bool:
        with self._lock:
            return self._world_pelvis is not None

    def get_cmd_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "type": "point_reach",
                "target": (self._target_x, self._target_y, self._target_z),
                "pelvis": self._world_pelvis,
                "yaw": self._world_root_yaw,
                "vx": self._vx, "vy": self._vy, "vz": self._vz,
                "kp_pos": self._kp_pos,
                "kp": self.activation.kp, "enabled": self.activation.enabled,
            }
