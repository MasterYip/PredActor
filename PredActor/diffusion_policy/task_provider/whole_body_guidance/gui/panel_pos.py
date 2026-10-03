"""PosPanel — composite panel for z-height + end-effector guidances."""

from __future__ import annotations

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
except ImportError:
    _CTK_AVAILABLE = False

from . import SCALE
from .gui_panel_base import BaseGuiPanel

class PosPanel(BaseGuiPanel):
    """Composite panel: hz slider + left/right wrist delta sliders."""

    guidance_name = "Position"

    def __init__(self, guidances: list):
        self._guidances = guidances
        super().__init__(guidances[0] if guidances else None)

    def build(self, parent, root_tk):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True)
        self._root_tk = root_tk
        self._slider_vars: dict[str, tk.DoubleVar] = {}

        guides: dict[str, object] = {}
        for g in self._guidances:
            if g is not None:
                guides[g.guidance_name] = g

        ctk.CTkLabel(
            frame, text="Position Commands  (local frame)",
            font=ctk.CTkFont(size=13, family="Arial", weight="bold"),
        ).pack(anchor="w", padx=12, pady=(8, 4))

        # ── Z-height ──────────────────────────────────────────────────
        hz = guides.get("hz")
        if hz is not None:
            z_section = ctk.CTkFrame(frame, fg_color="transparent")
            z_section.pack(fill="x", padx=12, pady=4)

            self._hz_en_var = tk.BooleanVar(master=root_tk, value=hz.activation.enabled)
            def _toggle_hz():
                hz.activation.enabled = self._hz_en_var.get()
            ctk.CTkCheckBox(
                z_section, text="Hz Guide", variable=self._hz_en_var,
                command=_toggle_hz, font=ctk.CTkFont(size=11, family="Arial"),
            ).pack(side="left", padx=4)

            ctk.CTkLabel(z_section, text="z", width=22, anchor="w",
                         font=ctk.CTkFont(size=11, family="Arial", weight="bold")).pack(side="left")
            var = tk.DoubleVar(master=root_tk, value=hz.get_target())
            self._slider_vars["hz"] = var
            val_lbl = ctk.CTkLabel(z_section, text=f"{hz.get_target():.2f}",
                                   width=50, anchor="e", font=ctk.CTkFont(size=11, family="Arial"))
            def _on_hz(v, _g=hz, _lbl=val_lbl, _var=var):
                val = _var.get()
                _lbl.configure(text=f"{val:.2f}")
                _g.set_target(val)
            ctk.CTkSlider(
                z_section, from_=hz.z_range[0], to=hz.z_range[1],
                variable=var, width=200, command=_on_hz,
            ).pack(side="left", padx=4)
            val_lbl.pack(side="left")

        # ── Left / right wrist rows ───────────────────────────────────
        for side_tag, side_label in [("left", "Left Wrist"), ("right", "Right Wrist")]:
            wrist_g = None
            for g in self._guidances:
                if g is not None and hasattr(g, 'side') and g.side == side_tag:
                    wrist_g = g
                    break
            if wrist_g is None:
                continue

            # Section label
            wx_header = ctk.CTkFrame(frame, fg_color="transparent")
            wx_header.pack(fill="x", padx=16, pady=(6, 2))

            en_var = tk.BooleanVar(master=root_tk, value=wrist_g.activation.enabled)
            def _make_toggle(_g=wrist_g, _v=en_var):
                _g.activation.enabled = _v.get()
            ctk.CTkCheckBox(
                wx_header, text=side_label, variable=en_var,
                command=_make_toggle, font=ctk.CTkFont(size=11, family="Arial"),
            ).pack(side="left", padx=4)

            init_dx, init_dy, init_dz = wrist_g.get_target()
            # Three sliders in one row
            wx_row = ctk.CTkFrame(frame, fg_color="transparent")
            wx_row.pack(fill="x", padx=20, pady=2)

            for axis_letter, rng, init_val, attr_suffix in [
                ("X", wrist_g.dx_range, init_dx, "dx"),
                ("Y", wrist_g.dy_range, init_dy, "dy"),
                ("Z", wrist_g.dz_range, init_dz, "dz"),
            ]:
                sub = ctk.CTkFrame(wx_row, fg_color="transparent")
                sub.pack(side="left", padx=2, expand=True, fill="x")

                ctk.CTkLabel(sub, text=axis_letter, width=16, anchor="w",
                             font=ctk.CTkFont(size=11, family="Arial", weight="bold")).pack(side="left")
                var = tk.DoubleVar(master=root_tk, value=init_val)
                self._slider_vars[f"{side_tag}_{attr_suffix}"] = var
                val_lbl = ctk.CTkLabel(sub, text=f"{init_val:+.2f}",
                                       width=44, anchor="e", font=ctk.CTkFont(size=11, family="Arial"))
                _idx = {"dx": 0, "dy": 1, "dz": 2}[attr_suffix]

                def _on_wx(v, _g=wrist_g, _lbl=val_lbl, _var=var, _i=_idx):
                    val = _var.get()
                    _lbl.configure(text=f"{val:+.2f}")
                    cur = list(_g.get_target())
                    cur[_i] = val
                    _g.set_target(*cur)

                ctk.CTkSlider(
                    sub, from_=rng[0], to=rng[1], variable=var,
                    width=80, command=_on_wx,
                ).pack(side="left", padx=2)
                val_lbl.pack(side="left")

        return frame

    def refresh_status(self) -> str:
        parts = []
        for g in self._guidances:
            if g is not None:
                s = g.get_cmd_summary()
                parts.append(f"{g.guidance_name}={s}")
        return " ".join(parts)
