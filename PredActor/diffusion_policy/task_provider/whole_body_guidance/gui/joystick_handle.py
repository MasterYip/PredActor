"""JoystickHandle — headless-safe adapter to the WholeBodyGuidance joystick
source.

The GUI needs to drive the hardware-joystick source that lives on
:class:`~diffusion_policy.task_provider.whole_body_guidance.whole_body_guidance.WholeBodyGuidance`
(``enable_joystick`` / ``set_joystick_source`` / ``update_joystick`` /
``get_joystick_command``), but it should not hold the whole guidance facade.
This class exposes exactly the surface the joystick panel needs:

    device / device_present / is_connected / enable / disable / update /
    get_command

It is intentionally free of ``customtkinter`` / ``tkinter`` / ``torch`` so it
can be imported and unit-tested without a display.
"""

from __future__ import annotations

import os
from typing import Any


class JoystickHandle:
    """Minimal controller wrapper for the WholeBodyGuidance joystick source.

    ``wbg`` is duck-typed: any object exposing the WBG joystick methods (or,
    for ``is_connected``, an ``is_joystick_connected()`` accessor / ``_joystick``
    attribute) works, which keeps the GUI decoupled from the guidance facade.
    """

    def __init__(
        self,
        wbg: Any,
        device: str = "/dev/input/js0",
        joystick_type: str = "xbox",
        max_linear_vel: float = 1.5,
        max_angular_vel: float = 1.0,
        min_height: float = 0.4,
        max_height: float = 1.2,
        deadzone: float = 0.10,
    ):
        self._wbg = wbg
        self.device = device
        self.joystick_type = joystick_type
        # max_linear_vel / max_angular_vel are the RAW joystick scaling used to
        # construct JoyStick.  The per-axis GUI range mapping (vx ±5, vy ±4,
        # wz ±2) is derived from each guidance's value_range inside
        # WholeBodyGuidance._apply_joystick, not here.
        self.max_linear_vel = max_linear_vel
        self.max_angular_vel = max_angular_vel
        self.min_height = min_height
        self.max_height = max_height
        # deadzone 0.10 zeroes stick drift so a released stick reads exactly 0.
        self.deadzone = deadzone

    # ── Probe / state ─────────────────────────────────────────────────────

    def device_present(self) -> bool:
        """True when the configured device node exists on the filesystem."""
        return os.path.exists(self.device)

    def is_connected(self) -> bool:
        """True when a joystick source is attached and currently running."""
        fn = getattr(self._wbg, "is_joystick_connected", None)
        if fn is not None:
            return bool(fn())
        joy = getattr(self._wbg, "_joystick", None)
        if joy is None:
            return False
        return bool(joy.is_running())

    # ── Control ───────────────────────────────────────────────────────────

    def enable(self) -> bool:
        """Open the hardware joystick and attach it as the command source.

        Returns ``True`` when the reader/reconnect supervisor is armed. Use
        :meth:`is_connected` for the live device state.
        """
        fn = getattr(self._wbg, "enable_joystick", None)
        if fn is None:
            return False
        return bool(fn(
            device=self.device,
            joystick_type=self.joystick_type,
            max_linear_vel=self.max_linear_vel,
            max_angular_vel=self.max_angular_vel,
            min_height=self.min_height,
            max_height=self.max_height,
            deadzone=self.deadzone,
        ))

    def disable(self) -> None:
        """Detach the joystick source (guidance returns to manual commands)."""
        fn = getattr(self._wbg, "set_joystick_source", None)
        if fn is not None:
            fn(None)

    # ── Data ──────────────────────────────────────────────────────────────

    def update(self) -> dict:
        """Poll the joystick once and apply it to the guidance.

        Returns the last applied ``{"vx", "vy", "wz", "hz"}``.
        """
        fn = getattr(self._wbg, "update_joystick", None)
        if fn is not None:
            return dict(fn())
        return self.get_command()

    def get_command(self) -> dict:
        """Return the last applied joystick command ``{"vx","vy","wz","hz"}``."""
        fn = getattr(self._wbg, "get_joystick_command", None)
        if fn is not None:
            return dict(fn())
        return {"vx": 0.0, "vy": 0.0, "wz": 0.0, "hz": None}
