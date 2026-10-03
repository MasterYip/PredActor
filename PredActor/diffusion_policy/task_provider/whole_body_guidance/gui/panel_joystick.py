"""JoystickPanel — customtkinter section for the WholeBodyGuidance hardware
joystick source (enable switch + connection status + live vx/vy/wz/hz).

Drives a :class:`~.joystick_handle.JoystickHandle` (never the guidance facade
directly).  The GuiManager places this section at the top of the window and
calls :meth:`refresh` from its existing 100 ms tick so the readout tracks the
hardware joystick live.
"""

from __future__ import annotations

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
except ImportError:
    _CTK_AVAILABLE = False

from . import SCALE


class JoystickPanel:
    """GUI section: enable switch, connection status, live command readout."""

    def __init__(self, handle):
        self._handle = handle
        self._frame = None
        self._root_tk = None
        self._enable_var = None
        self._switch = None
        self._status_lbl = None
        self._readout_lbl = None

    # ── Build ─────────────────────────────────────────────────────────────

    def build(self, parent, root_tk):
        if not _CTK_AVAILABLE or self._handle is None:
            return None

        frame = ctk.CTkFrame(parent, border_width=1, border_color="#3a3a3a")
        frame.pack(fill="x", padx=10, pady=(4, 6))
        self._frame = frame
        self._root_tk = root_tk

        # Header row: title + connection status
        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(hdr, text="Joystick",
                     font=ctk.CTkFont(size=12, family="Arial", weight="bold"),
                     text_color="#8ab4f8").pack(side="left")
        self._status_lbl = ctk.CTkLabel(hdr, text="…",
                                        font=ctk.CTkFont(size=11, family="Arial"),
                                        text_color="#888")
        self._status_lbl.pack(side="left", padx=10)

        # Enable switch
        ctl = ctk.CTkFrame(frame, fg_color="transparent")
        ctl.pack(fill="x", padx=8, pady=(2, 2))
        self._enable_var = tk.BooleanVar(master=root_tk, value=False)
        self._switch = ctk.CTkSwitch(
            ctl, text="Enable joystick", variable=self._enable_var,
            command=self._on_toggle,
            font=ctk.CTkFont(size=12, family="Arial"),
            switch_width=36, switch_height=18,
            fg_color="#555", progress_color="#4CAF50",
        )
        self._switch.pack(side="left")

        # Live readout
        self._readout_lbl = ctk.CTkLabel(
            frame, text="vx=+0.00  vy=+0.00  wz=+0.00  hz=—",
            font=ctk.CTkFont(size=12, family="Arial"), text_color="#ccc",
        )
        self._readout_lbl.pack(anchor="w", padx=8, pady=(2, 6))

        self._sync_device_state()
        return frame

    # ── Interaction ───────────────────────────────────────────────────────

    def _on_toggle(self):
        if self._handle is None or self._enable_var is None:
            return
        if self._enable_var.get():
            ok = self._handle.enable()
            if not ok:
                self._enable_var.set(False)
        else:
            self._handle.disable()
        self._refresh_status()

    def _sync_device_state(self):
        """Grey out / detach the switch when the device node is absent."""
        if self._handle is None:
            return
        present = self._handle.device_present()
        armed = bool(self._enable_var is not None and self._enable_var.get())
        if self._switch is not None:
            self._switch.configure(state="normal" if present or armed else "disabled")
        self._refresh_status()

    # ── Refresh (called from the GuiManager tick) ─────────────────────────

    def refresh(self):
        if self._frame is None or self._handle is None:
            return

        present = self._handle.device_present()
        armed = bool(self._enable_var is not None and self._enable_var.get())
        if self._switch is not None:
            self._switch.configure(state="normal" if present or armed else "disabled")

        connected = self._handle.is_connected()
        if connected:
            cmd = self._handle.update()
        else:
            cmd = self._handle.get_command()

        self._refresh_status()
        self._update_readout(cmd)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _refresh_status(self):
        if self._status_lbl is None or self._handle is None:
            return
        device = getattr(self._handle, "device", "/dev/input/js0")
        connected = self._handle.is_connected()
        present = self._handle.device_present()
        if connected:
            text, color = f"{device}  running", "#4CAF50"
        elif self._enable_var is not None and self._enable_var.get():
            text, color = f"{device}  disconnected; retrying", "#f0ad4e"
        elif present:
            text, color = f"{device}  ready", "#aaa"
        else:
            text, color = f"no joystick ({device} not found)", "#f44"
        self._status_lbl.configure(text=text, text_color=color)

    def _update_readout(self, cmd: dict):
        if self._readout_lbl is None:
            return
        vx = float(cmd.get("vx", 0.0) or 0.0)
        vy = float(cmd.get("vy", 0.0) or 0.0)
        wz = float(cmd.get("wz", 0.0) or 0.0)
        hz = cmd.get("hz")
        hz_text = "—" if hz is None else f"{hz:.2f}"
        self._readout_lbl.configure(
            text=f"vx={vx:+.2f}  vy={vy:+.2f}  wz={wz:+.2f}  hz={hz_text}")
