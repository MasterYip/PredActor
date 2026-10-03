"""WristGuidance — per-wrist end-effector position guidance.

Left and right wrist are independent guidance instances, each with their
own activation set.  Each controls the wrist body positions (indices 24–26
for left, 27–29 for right) via delta targets relative to the torso.
"""

from __future__ import annotations

import threading
from typing import Any

import torch

from ..guidance_base import GuidanceBase
from ..guidance_activation_set import GuidanceActivationSet
from ..term_resolver import TermResolver


class WristGuidance(GuidanceBase):
    """End-effector position guidance for a single wrist.

    Ramps the wrist body positions (3 bodies × 3 axes) toward a delta
    from the current torso position.  Left wrist uses body indices 24–26,
    right wrist uses 27–29.
    """

    guidance_name: str = "wrist"  # overridden in __init__ to include side

    # Body indices for each side
    _SIDE_INDICES: dict[str, list[int]] = {
        "left":  [24, 25, 26],
        "right": [27, 28, 29],
    }

    def __init__(
        self,
        activation: GuidanceActivationSet,
        side: str = "left",
        dx_range: tuple = (-0.5, 0.5),
        dy_range: tuple = (-0.5, 0.5),
        dz_range: tuple = (-0.3, 0.3),
    ):
        super().__init__(activation)
        if side not in ("left", "right"):
            raise ValueError(f"side must be 'left' or 'right', got '{side}'")
        self._side = side
        self._body_indices = self._SIDE_INDICES[side]
        # Distinguish left vs right in the activation-manager row label
        self.guidance_name = f"wrist_{side}"

        self._lock = threading.Lock()
        self._dx: float = 0.0
        self._dy: float = 0.0
        self._dz: float = 0.0
        self._dx_range = dx_range
        self._dy_range = dy_range
        self._dz_range = dz_range

    @property
    def side(self) -> str:
        return self._side

    @property
    def dx_range(self) -> tuple:
        return self._dx_range

    @property
    def dy_range(self) -> tuple:
        return self._dy_range

    @property
    def dz_range(self) -> tuple:
        return self._dz_range

    def set_target(self, dx: float, dy: float, dz: float) -> None:
        with self._lock:
            self._dx = float(dx)
            self._dy = float(dy)
            self._dz = float(dz)

    def get_target(self) -> tuple[float, float, float]:
        with self._lock:
            return self._dx, self._dy, self._dz

    def build_deltas(
        self,
        state_unnorm: torch.Tensor,
        term_resolver: TermResolver,
        body_intensity: list[float],
        dt: float,
        n_past_steps: int,
        mode: str,
    ) -> dict[str, torch.Tensor]:
        B, H, _D = state_unnorm.shape
        device = state_unnorm.device
        now = n_past_steps - 1

        body_pos_now = term_resolver.get(state_unnorm[:, now, :], "body_pos_local")  # [B, 90]
        # Torso reference: body index 9
        torso_now = body_pos_now[:, 27:30]  # [B, 3]

        with self._lock:
            dx, dy, dz = self._dx, self._dy, self._dz

        steps = torch.arange(H, dtype=torch.float32, device=device) - now
        steps = steps.clamp(min=0)

        # Build delta only for the 3 wrist bodies (9 scalars)
        body_delta = torch.zeros(B, H, 90, device=device)
        deltas_list = [dx, dy, dz]

        for local_i, body_idx in enumerate(self._body_indices):
            w = body_intensity[body_idx] if body_intensity else 1.0
            if w <= 0.0:
                continue
            base = body_idx * 3

            # Compute target delta per axis (x, y, z)
            targets = [0.0, 0.0, 0.0]
            if local_i == 0:  # roll body — all three axes
                targets = [dx * w, dy * w, dz * w]
            elif local_i == 1:  # pitch body
                targets = [dx * w, dy * w, dz * w]
            else:  # yaw body
                targets = [dx * w, dy * w, dz * w]

            for axis in range(3):
                val = targets[axis]
                if abs(val) < 1e-8:
                    continue
                for t in range(n_past_steps, H):
                    blend = min(1.0, steps[t].item() / max(1, H - n_past_steps))
                    body_delta[:, t, base + axis] = val * blend

        return {"body_pos_local": body_delta}

    def get_cmd_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "side": self._side, "dx": self._dx, "dy": self._dy, "dz": self._dz,
                "kp": self.activation.kp, "enabled": self.activation.enabled,
            }
