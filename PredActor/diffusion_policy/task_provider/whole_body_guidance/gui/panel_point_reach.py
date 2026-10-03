"""PointReachGuiPanel — CustomTkinter panel for PointReachGuidance."""

from __future__ import annotations

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
except ImportError:
    _CTK_AVAILABLE = False

from . import SCALE
from .gui_panel_base import BaseGuiPanel

class PointReachGuiPanel(BaseGuiPanel):
    """Panel for point-reach guidance: target x/y/z sliders + wrist toggles."""

    guidance_name = "PointReach"

    def build(self, parent, root_tk):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True)
        self._frame = frame
        self._root_tk = root_tk
        self._slider_vars: dict[str, tk.DoubleVar] = {}

        guidance = self.guidance

        ctk.CTkLabel(
            frame, text="Point Reach Target  (world frame)",
            font=ctk.CTkFont(size=13, family="Arial", weight="bold"),
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self._status_lbl = ctk.CTkLabel(
            frame, text="Pelvis: ?", font=ctk.CTkFont(size=11, family="Arial"), text_color="#888",
        )
        self._status_lbl.pack(anchor="w", padx=12)

        self._make_slider(frame, "tgt_X", *guidance.target_x_range, 0.0, "target_x")
        self._make_slider(frame, "tgt_Y", *guidance.target_y_range, 0.0, "target_y")
        self._make_slider(frame, "tgt_Z", *guidance.target_z_range, 0.8, "target_z")

        self._make_slider(frame, "kp_pos", 0.0, 5.0, guidance.kp_pos, "kp_pos")

        wrist_bar = ctk.CTkFrame(frame, fg_color="transparent")
        wrist_bar.pack(fill="x", padx=12, pady=(4, 2))

        self._lw_var = tk.BooleanVar(master=root_tk, value=False)
        self._rw_var = tk.BooleanVar(master=root_tk, value=False)

        def _toggle_wrist():
            guidance.set_wrist_guide(self._lw_var.get(), self._rw_var.get())

        ctk.CTkCheckBox(
            wrist_bar, text="Left Wrist", variable=self._lw_var,
            command=_toggle_wrist, font=ctk.CTkFont(size=11, family="Arial"),
        ).pack(side="left", padx=4)
        ctk.CTkCheckBox(
            wrist_bar, text="Right Wrist", variable=self._rw_var,
            command=_toggle_wrist, font=ctk.CTkFont(size=11, family="Arial"),
        ).pack(side="left", padx=4)

        self._make_slider(frame, "kp", 0.0, 2.0, guidance.activation.kp, "pr_kp")

        return frame

    def _make_slider(self, parent, label, from_, to, init, attr, width=220):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)

        ctk.CTkLabel(row, text=label, width=60, anchor="w",
                     font=ctk.CTkFont(size=11, family="Arial")).pack(side="left")

        var = tk.DoubleVar(master=self._root_tk, value=init)
        self._slider_vars[attr] = var

        val_lbl = ctk.CTkLabel(row, text=f"{init:+.2f}", width=60, anchor="e",
                               font=ctk.CTkFont(size=11, family="Arial"))

        def _on_change(v, _attr=attr, _lbl=val_lbl, _var=var):
            val = _var.get()
            _lbl.configure(text=f"{val:+.2f}")
            g = self.guidance
            if _attr in ("target_x", "target_y", "target_z"):
                tx = self._slider_vars.get("target_x", tk.DoubleVar(master=self._root_tk, value=0.0)).get()
                ty = self._slider_vars.get("target_y", tk.DoubleVar(master=self._root_tk, value=0.0)).get()
                tz = self._slider_vars.get("target_z", tk.DoubleVar(master=self._root_tk, value=0.8)).get()
                g.set_target(tx, ty, tz)
            elif _attr == "kp_pos":
                g._kp_pos = float(val)
            elif _attr == "pr_kp":
                g.activation.kp = float(val)

        ctk.CTkSlider(
            row, from_=from_, to=to, variable=var,
            width=width, command=_on_change,
        ).pack(side="left", padx=6)
        val_lbl.pack(side="left")

    def refresh_status(self) -> str:
        g = self.guidance
        s = g.get_cmd_summary()
        target = s.get("target", (0, 0, 0))
        pelvis = "ok" if s.get("pelvis") else "?"
        return (f"tgt=({target[0]:+.1f},{target[1]:+.1f},{target[2]:+.2f}) "
                f"pelvis={pelvis} v=({s['vx']:+.1f},{s['vy']:+.1f},{s['vz']:+.1f})")
