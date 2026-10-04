"""VelPanel — composite slider panel for per-axis velocity guidances.

Drives ``VxGuidance``, ``VyGuidance``, ``VzGuidance``, ``WzGuidance`` instances
(each independently toggleable via their activation set).  All four sliders
share one tab in the ``CTkTabview``.
"""

from __future__ import annotations

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
except ImportError:
    _CTK_AVAILABLE = False

from . import SCALE
from .gui_panel_base import BaseGuiPanel
from ..guidance_types.axes_vel import VxGuidance, VyGuidance, VzGuidance, WzGuidance

class VelPanel(BaseGuiPanel):
    """Composite panel: slider per axis, each drives its own guidance instance."""

    guidance_name = "Velocity"

    def __init__(self, guidances: list):
        self._guidances = guidances
        super().__init__(guidances[0] if guidances else None)

    def build(self, parent, root_tk):
        if not _CTK_AVAILABLE:
            return ctk.CTkFrame(parent)

        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True)
        self._root_tk = root_tk
        self._slider_vars: dict[str, tk.DoubleVar] = {}

        ctk.CTkLabel(
            frame, text="Velocity Commands  (body frame, per-axis)",
            font=ctk.CTkFont(size=13, family="Arial", weight="bold"),
        ).pack(anchor="w", padx=12, pady=(8, 4))

        guides: dict[str, object] = {}
        for g in self._guidances:
            if g is not None:
                guides[g.guidance_name] = g

        for axis, label in [
            ("vx", "vx"), ("vy", "vy"), ("vz", "vz"), ("wz", "wz"),
        ]:
            g = guides.get(axis)
            if g is None:
                continue
            rng = g.value_range
            self._make_slider(frame, label, rng[0], rng[1], g.get_value(), axis, g)

        def _reset():
            for attr in ("vx", "vy", "vz", "wz"):
                if attr in self._slider_vars:
                    self._slider_vars[attr].set(0.0)
                g2 = guides.get(attr)
                if g2:
                    g2.set_value(0.0)

        ctk.CTkButton(
            frame, text="Reset All", width=100, height=28,
            fg_color="#555", hover_color="#777", command=_reset,
            font=ctk.CTkFont(size=11, family="Arial"),
        ).pack(pady=(4, 8))

        return frame

    def _make_slider(self, parent, label, from_, to, init, attr, guidance):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)

        ctk.CTkLabel(row, text=label, width=32, anchor="w",
                     font=ctk.CTkFont(size=12, family="Arial", weight="bold")).pack(side="left")

        var = tk.DoubleVar(master=self._root_tk, value=init)
        self._slider_vars[attr] = var

        val_lbl = ctk.CTkLabel(row, text=f"{init:+.2f}", width=60, anchor="e",
                               font=ctk.CTkFont(size=12, family="Arial"))

        def _on_change(v, _guidance=guidance, _lbl=val_lbl, _var=var):
            val = _var.get()
            _lbl.configure(text=f"{val:+.2f}")
            _guidance.set_value(val)

        ctk.CTkSlider(
            row, from_=from_, to=to, variable=var,
            width=220, command=_on_change,
        ).pack(side="left", padx=6)
        val_lbl.pack(side="left")

    def refresh_status(self) -> str:
        parts = []
        for g in self._guidances:
            if g is not None:
                parts.append(f"{g.guidance_name}={g.get_value():+.2f}")
        return " ".join(parts)
