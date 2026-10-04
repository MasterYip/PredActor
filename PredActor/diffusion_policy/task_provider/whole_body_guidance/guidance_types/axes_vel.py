"""Per-axis velocity guidances — each controls a single DOF.

``VxGuidance``, ``VyGuidance``, ``VzGuidance`` each control one body-frame
translation axis.  ``WzGuidance`` controls yaw angular velocity.

Each owns a single float command value and produces deltas only for the
components it controls.  Superposition is handled by the manager summing
deltas — non-overlapping axis components accumulate correctly.

They all delegate to the standard kinematic target builders
(``_build_simple_target`` / ``_build_target_trajectory``) with only their
axis non-zero, then compute ``delta = target - current`` and mask to
their axis components.
"""

from __future__ import annotations

import math
import threading
from typing import Any

import torch

from ..guidance_base import GuidanceBase
from ..guidance_activation_set import GuidanceActivationSet
from ..term_resolver import TermResolver
from ..kinematic_utils import _build_simple_target, _build_target_trajectory


# ── Axis → component indices within each term ─────────────────────────────
# The standard G1 192-d FK layout has:
#   body_pos_local      [  0: 90]  30 bodies × 3 (x,y,z)
#   body_lin_vel_local  [ 90:180]  30 bodies × 3 (x,y,z)
#   root_pos_local      [180:183]  (x,y,z)
#   root_rot_local      [183:186]  (roll,pitch,yaw)
#   root_lin_vel_local  [186:189]  (x,y,z)
#   root_ang_vel_local  [189:192]  (roll_rate,pitch_rate,yaw_rate)

def _axis_body_mask(axis: int, term_dim: int) -> torch.Tensor:
    """Build a mask tensor [term_dim] with 1.0 at positions matching *axis*.

    For body terms (90-d): axis 0=x (indices 0,3,6,...), axis 1=y (1,4,7,...),
    axis 2=z (2,5,8,...).  For root terms (3-d): axis 0/1/2 maps to dim 0/1/2.
    """
    mask = torch.zeros(term_dim)
    if term_dim == 90:          # 30 bodies × 3
        for i in range(30):
            mask[i * 3 + axis] = 1.0
    elif term_dim == 3:         # root pos / rot / vel
        mask[axis] = 1.0
    return mask


# Pre-built axis masks (cached per axis→term_name)
_AXIS_MASKS: dict[tuple[int, str], torch.Tensor] = {}


def _get_axis_mask(axis: int, term_name: str) -> torch.Tensor:
    """Return a 1-D mask for *axis* within *term_name*."""
    key = (axis, term_name)
    if key not in _AXIS_MASKS:
        # term dims: body terms = 90, root terms = 3
        dim = 90 if term_name.startswith("body_") else 3
        _AXIS_MASKS[key] = _axis_body_mask(axis, dim)
    return _AXIS_MASKS[key]


# ── Per-axis velocity guidance ────────────────────────────────────────────

class _SingleAxisVelGuidance(GuidanceBase):
    """Base for single-axis velocity guidance (vx, vy, vz, or wz).

    Subclasses set ``axis`` (0=vx, 1=vy, 2=vz) or handle ``wz`` specially.
    """

    axis: int = 0          # 0, 1, or 2 for position axes
    _is_wz: bool = False

    def __init__(
        self,
        activation: GuidanceActivationSet,
        value_range: tuple = (-5.0, 5.0),
    ):
        super().__init__(activation)
        self._lock = threading.Lock()
        self._value: float = 0.0
        self._batch_value: torch.Tensor | None = None
        self._range = value_range

    @property
    def value_range(self) -> tuple:
        return self._range

    def set_value(self, val: float) -> None:
        with self._lock:
            self._value = float(val)

    def get_value(self) -> float:
        with self._lock:
            return self._value

    def set_batch_value(self, value: torch.Tensor) -> None:
        """Temporarily supply one command value per vectorized environment."""
        if not isinstance(value, torch.Tensor) or value.ndim != 1:
            raise ValueError("axis batch value must be a 1-D torch tensor")
        with self._lock:
            self._batch_value = value

    def clear_batch_value(self) -> None:
        with self._lock:
            self._batch_value = None

    def _get_effective_value(self):
        with self._lock:
            return self._batch_value if self._batch_value is not None else self._value

    def get_effective_value(self):
        """Return the scalar or batched value actually consumed by guidance."""
        with self._lock:
            if self._batch_value is None:
                return self._value
            return self._batch_value.detach().clone()

    def _get_vxvyvzwz(self) -> tuple[float, float, float, float]:
        """Return (vx, vy, vz, wz) with only this axis non-zero."""
        v = self._get_effective_value()
        if self._is_wz:
            return 0.0, 0.0, 0.0, v
        return (
            v if self.axis == 0 else 0.0,
            v if self.axis == 1 else 0.0,
            v if self.axis == 2 else 0.0,
            0.0,
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
        """Build full kinematic target with only this axis non-zero, then
        compute ``delta = target - current`` and mask to axis components."""
        B, H, _D = state_unnorm.shape
        device = state_unnorm.device

        vx, vy, vz, wz = self._get_vxvyvzwz()
        builder = _build_simple_target if mode == "simple" else _build_target_trajectory
        targets = builder(state_unnorm, term_resolver, vx, vy, vz, wz, dt, n_past_steps,
                          body_intensity=body_intensity)

        deltas: dict[str, torch.Tensor] = {}
        for term in self.activation.effective_terms:
            target = targets.get(term)
            if target is None:
                continue
            current = term_resolver.get(state_unnorm, term)
            delta_full = target - current  # [B, H, D_term]

            # Mask to only this axis's components
            mask = _get_axis_mask(self.axis if not self._is_wz else 2, term).to(device)
            deltas[term] = delta_full * mask[None, None, :]

        return deltas

    def get_cmd_summary(self) -> dict[str, Any]:
        with self._lock:
            return {"value": self._value, "kp": self.activation.kp,
                    "enabled": self.activation.enabled}


class VxGuidance(_SingleAxisVelGuidance):
    """Forward (body-frame x) velocity guidance."""
    guidance_name: str = "vx"
    axis: int = 0


class VyGuidance(_SingleAxisVelGuidance):
    """Lateral (body-frame y) velocity guidance."""
    guidance_name: str = "vy"
    axis: int = 1


class VzGuidance(_SingleAxisVelGuidance):
    """Vertical (body-frame z) velocity guidance."""
    guidance_name: str = "vz"
    axis: int = 2


class WzGuidance(_SingleAxisVelGuidance):
    """Yaw angular velocity (body-frame z rotation) guidance."""
    guidance_name: str = "wz"
    axis: int = 2       # uses z component of rot/ang_vel
    _is_wz: bool = True
