"""HzGuidance — z-height (pelvis/torso height) guidance.

Controls the z-component of both ``root_pos_local`` and the redundant pelvis
entry in ``body_pos_local``.  Produces deltas that ramp current height toward a
target over the horizon.  No velocity terms — those come from VzGuidance
if vertical velocity is also desired.
"""

from __future__ import annotations

import threading
from typing import Any

import torch

from ..guidance_base import GuidanceBase
from ..guidance_activation_set import GuidanceActivationSet
from ..term_resolver import TermResolver


class HzGuidance(GuidanceBase):
    """Pelvis / torso z-height guidance.

    Ramps ``root_pos_local[:,:,2]`` and pelvis body z (index 0) toward
    ``target_z`` over the horizon.  Past frames are unchanged.
    """

    guidance_name: str = "hz"

    def __init__(
        self,
        activation: GuidanceActivationSet,
        z_range: tuple = (0.3, 1.1),
        z_init: float = 0.75,
    ):
        super().__init__(activation)
        self._lock = threading.Lock()
        self._target_z: float = z_init
        self._z_range = z_range
        self._diag_counter: int = 0

    @property
    def z_range(self) -> tuple:
        return self._z_range

    def set_target(self, z: float) -> None:
        with self._lock:
            self._target_z = float(z)

    def get_target(self) -> float:
        with self._lock:
            return self._target_z

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

        root_pos_now = term_resolver.get(state_unnorm[:, now, :], "root_pos_local")  # [B, 3]
        body_pos_now = term_resolver.get(state_unnorm[:, now, :], "body_pos_local")  # [B, 90]

        with self._lock:
            target_z = self._target_z

        steps = torch.arange(H, dtype=torch.float32, device=device) - now
        steps = steps.clamp(min=0)
        dz = target_z - root_pos_now[:, 2]  # [B] — total z error

        deltas: dict[str, torch.Tensor] = {}

        # root_pos_local: delta only in z (dim 2)
        root_delta = torch.zeros(B, H, 3, device=device)
        for t in range(n_past_steps, H):
            blend = min(1.0, steps[t].item() / max(1, H - n_past_steps))
            root_delta[:, t, 2] = dz * blend
        deltas["root_pos_local"] = root_delta

        # body_pos_local stores world height (only XY translation is removed
        # during term composition), so pelvis z is a redundant observation of
        # root height. Guiding root_pos_local alone creates an inconsistent
        # x-stream and gives the denoiser/action stream little kinematic
        # evidence for a crouch. Shift pelvis z by the same physical delta.
        pelvis_weight = float(body_intensity[0]) if body_intensity else 1.0
        body_delta = torch.zeros(B, H, body_pos_now.shape[-1], device=device)
        body_delta[:, :, 2] = root_delta[:, :, 2] * pelvis_weight
        deltas["body_pos_local"] = body_delta

        # ── Diagnostic (uncomment to debug) ───────────────────────────────
        # self._diag_counter += 1
        # if self._diag_counter % 50 == 0 and dz.abs().max().item() > 1e-6:
        #     print(f"[HzGuidance] target_z={target_z:.3f}  "
        #           f"root_z_now={root_pos_now[:, 2].mean().item():.3f}  "
        #           f"dz_mean={dz.mean().item():+.4f}  kp={self.activation.kp:.2f}  "
        #           f"enabled={self.activation.enabled}",
        #           flush=True)

        return deltas

    def get_cmd_summary(self) -> dict[str, Any]:
        with self._lock:
            return {"target_z": self._target_z, "kp": self.activation.kp,
                    "enabled": self.activation.enabled}
