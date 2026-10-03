"""CustomTkinter controls for the world-frame destination-follow guidance."""

from __future__ import annotations

import math

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
except ImportError:
    _CTK_AVAILABLE = False

from .gui_panel_base import BaseGuiPanel


class DestinationFollowGuiPanel(BaseGuiPanel):
    """Set a destination and tune the controller from the native Tk UI."""

    guidance_name = "DestinationFollow"
    _CONFIG_FIELDS = (
        ("kp_x", "Forward gain"),
        ("kp_y", "Lateral gain"),
        ("kp_w", "Heading gain"),
        ("max_vx", "Max forward"),
        ("max_vy", "Max lateral"),
        ("max_wz", "Max yaw"),
        ("heading_dead_zone", "Heading dead zone"),
        ("arrival_radius", "Arrival radius"),
        ("rearm_radius", "Rearm radius"),
    )

    def __init__(self, guidance, owner=None):
        super().__init__(guidance)
        self._controller = getattr(guidance, "controller", None)
        self._owner = owner
        self._root_tk = None
        self._target_vars: dict[str, tk.StringVar] = {}
        self._config_vars: dict[str, tk.StringVar] = {}
        self._enabled_var = None
        self._status_lbl = None
        self._message_lbl = None
        self._enable_switch = None
        self._target_entries = []

    def build(self, parent, root_tk):
        if not _CTK_AVAILABLE or self._controller is None:
            return None

        self._root_tk = root_tk
        snapshot = self._controller.snapshot()
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True)
        self._frame = frame

        ctk.CTkLabel(
            frame, text="Destination Follow (world frame)",
            font=ctk.CTkFont(size=13, family="Arial", weight="bold"),
        ).pack(anchor="w", padx=12, pady=(8, 4))

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(0, 4))
        self._enabled_var = tk.BooleanVar(master=root_tk, value=bool(snapshot.get("enabled")))
        self._enable_switch = ctk.CTkSwitch(
            header, text="Enabled", variable=self._enabled_var,
            command=self._toggle_enabled,
            font=ctk.CTkFont(size=11, family="Arial"),
            switch_width=36, switch_height=18,
            fg_color="#555", progress_color="#4CAF50",
        )
        self._enable_switch.pack(side="left")
        self._status_lbl = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=11, family="Arial"), text_color="#aaa")
        self._status_lbl.pack(side="left", padx=10)

        target = snapshot.get("target") or (0.0, 0.0, 0.8)
        target_frame = ctk.CTkFrame(frame, fg_color="transparent")
        target_frame.pack(fill="x", padx=12, pady=3)
        for axis, value in zip(("X", "Y", "Z"), target):
            key = axis.lower()
            ctk.CTkLabel(target_frame, text=axis, width=16,
                         font=ctk.CTkFont(size=11, family="Arial", weight="bold")).pack(side="left")
            var = tk.StringVar(master=root_tk, value=f"{float(value):.2f}")
            self._target_vars[key] = var
            entry = ctk.CTkEntry(target_frame, textvariable=var, width=72,
                                 font=ctk.CTkFont(size=11, family="Arial"))
            entry.pack(side="left", padx=(2, 8))
            self._target_entries.append(entry)

        target_actions = ctk.CTkFrame(frame, fg_color="transparent")
        target_actions.pack(fill="x", padx=12, pady=(2, 4))
        ctk.CTkButton(
            target_actions, text="Set + Enable", width=110, height=26,
            command=self._set_target, font=ctk.CTkFont(size=11, family="Arial"),
        ).pack(side="left", padx=(0, 5))
        ctk.CTkButton(
            target_actions, text="Cancel", width=80, height=26,
            fg_color="#555", hover_color="#777", command=self._cancel,
            font=ctk.CTkFont(size=11, family="Arial"),
        ).pack(side="left")

        ctk.CTkLabel(
            frame, text="Controller tuning", font=ctk.CTkFont(size=12, family="Arial", weight="bold"),
            text_color="#8ab4f8",
        ).pack(anchor="w", padx=12, pady=(6, 2))
        config = snapshot.get("config") or {}
        config_frame = ctk.CTkFrame(frame, fg_color="transparent")
        config_frame.pack(fill="x", padx=12, pady=2)
        for key, label in self._CONFIG_FIELDS:
            row = ctk.CTkFrame(config_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, width=120, anchor="w",
                         font=ctk.CTkFont(size=11, family="Arial")).pack(side="left")
            value = config.get(key, 0.0)
            var = tk.StringVar(master=root_tk, value=f"{float(value):.2f}")
            self._config_vars[key] = var
            ctk.CTkEntry(row, textvariable=var, width=90,
                         font=ctk.CTkFont(size=11, family="Arial")).pack(side="left")

        ctk.CTkButton(
            frame, text="Apply tuning", width=110, height=26,
            command=self._apply_config,
            font=ctk.CTkFont(size=11, family="Arial"),
        ).pack(anchor="w", padx=12, pady=(4, 2))
        self._message_lbl = ctk.CTkLabel(
            frame, text="", anchor="w", font=ctk.CTkFont(size=10, family="Arial"), text_color="#f0ad4e")
        self._message_lbl.pack(fill="x", padx=12, pady=(0, 6))
        self.refresh_status()
        return frame

    def _set_message(self, text: str, color: str = "#f0ad4e"):
        if self._message_lbl is not None:
            self._message_lbl.configure(text=text, text_color=color)

    def _toggle_enabled(self):
        enabled = bool(self._enabled_var.get())
        if self._owner is not None:
            self._owner.enable_destination_follow(enabled)
        else:
            self._controller.set_enabled(enabled)
            self.guidance.activation.enabled = enabled
            if not enabled:
                self.guidance.set_cmd(0.0, 0.0, 0.0, 0.0)
        self._set_message("")

    def _set_target(self):
        try:
            target = tuple(float(self._target_vars[key].get()) for key in ("x", "y", "z"))
            if not all(math.isfinite(value) for value in target):
                raise ValueError("target must contain finite numbers")
            if self._owner is not None:
                self._owner.set_destination_target(target)
                self._owner.enable_destination_follow(True)
            else:
                self._controller.set_target(target)
                self._controller.set_enabled(True)
                self.guidance.activation.enabled = True
            self._enabled_var.set(True)
            self._set_message("Target set", "#4CAF50")
        except (TypeError, ValueError) as exc:
            self._set_message(f"Target rejected: {exc}")

    def _cancel(self):
        if self._owner is not None:
            self._owner.cancel_destination_follow()
        else:
            self._controller.cancel()
            self.guidance.activation.enabled = False
            self.guidance.set_cmd(0.0, 0.0, 0.0, 0.0)
        self._enabled_var.set(False)
        self._set_message("Destination cancelled", "#aaa")

    def _apply_config(self):
        try:
            values = {key: float(var.get()) for key, var in self._config_vars.items()}
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError("tuning values must be finite")
            if self._owner is not None:
                self._owner.set_destination_config(values)
            else:
                self._controller.set_config(values)
            self._set_message("Tuning applied", "#4CAF50")
        except (TypeError, ValueError) as exc:
            self._set_message(f"Tuning rejected: {exc}")

    def refresh_status(self) -> str:
        if self._controller is None:
            return "destination unavailable"
        snapshot = self._controller.snapshot()
        enabled = bool(snapshot.get("enabled"))
        if self._enabled_var is not None and not self._enabled_var.get() == enabled:
            self._enabled_var.set(enabled)
        target = snapshot.get("target")
        if target and self._target_vars and not any(entry.focus_get() is entry for entry in self._target_entries):
            for key, value in zip(("x", "y", "z"), target):
                self._target_vars[key].set(f"{float(value):.2f}")
        status = str(snapshot.get("status", "disabled"))
        distance = snapshot.get("distance")
        heading = snapshot.get("heading_error")
        telemetry = status
        if isinstance(distance, (int, float)) and math.isfinite(float(distance)):
            telemetry += f"  d={float(distance):.2f}m"
        if isinstance(heading, (int, float)) and math.isfinite(float(heading)):
            telemetry += f"  heading={float(heading):+.2f}rad"
        command = snapshot.get("command") or {}
        telemetry += (f"  vx={float(command.get('vx', 0.0)):+.2f}"
                      f" vy={float(command.get('vy', 0.0)):+.2f}"
                      f" wz={float(command.get('wz', 0.0)):+.2f}")
        if self._status_lbl is not None:
            self._status_lbl.configure(text=telemetry,
                                       text_color="#4CAF50" if enabled else "#aaa")
        return telemetry
