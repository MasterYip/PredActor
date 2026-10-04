"""JoyTextPanel — integrated GUI for JoyTextWBG.

Single CTk window containing:
  - Joystick status + zone display + semantic text header
  - Velocity / Position / PointReach tabs (reusing existing panels)
  - Activation Manager with per-guidance switches and kp sliders
  - Debug heatmap (when DEBUG=True)

The vx/vy/vz sliders reflect joystick input in real time.  When the
user manually drags a slider, an override flag is set and joystick
input for that axis is ignored until the user releases the override.
"""

from __future__ import annotations

import time as _time
from typing import Optional

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
except ImportError:
    _CTK_AVAILABLE = False

from diffusion_policy.task_provider.whole_body_guidance.body_groups import G1_BODY_GROUPS, DEBUG
from diffusion_policy.task_provider.whole_body_guidance.term_resolver import TermResolver
from diffusion_policy.task_provider.whole_body_guidance.guidance_activation_manager import GuidanceActivationManager
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.axes_vel import (
    VxGuidance, VyGuidance, VzGuidance, WzGuidance,
)
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.hz_guide import HzGuidance
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.wrist_guide import WristGuidance
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.point_reach import PointReachGuidance
from diffusion_policy.task_provider.whole_body_guidance.gui import SCALE
from diffusion_policy.task_provider.whole_body_guidance.gui.debug_panel import DebugPanel
from diffusion_policy.task_provider.whole_body_guidance.gui.panel_vel import VelPanel
from diffusion_policy.task_provider.whole_body_guidance.gui.panel_pos import PosPanel
from diffusion_policy.task_provider.whole_body_guidance.gui.panel_point_reach import PointReachGuiPanel

_SEL_BORDER = "#8ab4f8"
_SEL_BG = "#2a3a4a"


def _cat(g):
    """Return (key, label) for a guidance instance."""
    if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
        return ("Velocity", "Velocity Group")
    elif isinstance(g, (HzGuidance, WristGuidance)):
        return ("Position", "Position Group")
    elif isinstance(g, PointReachGuidance):
        return ("PointReach", "PointReach Group")
    return ("Other", "Other")


class JoyTextPanel:
    """Integrated GUI for JoyTextWBG.

    Args:
        joy_text_wbg: The JoyTextWBG instance to visualise.
    """

    def __init__(self, joy_text_wbg):
        if not _CTK_AVAILABLE:
            raise ImportError("JoyTextPanel requires customtkinter")

        self._jtwbg = joy_text_wbg
        self._mapping = joy_text_wbg.mapping
        self._wbg = joy_text_wbg.wbg
        self._manager: GuidanceActivationManager = self._wbg._manager
        self._term_resolver: TermResolver = self._wbg._term_resolver

        self._root: Optional[ctk.CTk] = None
        self._running = False

        # Per-guidance UI state
        self._enable_vars: dict[int, tk.BooleanVar] = {}
        self._status_labels: dict[int, ctk.CTkLabel] = {}
        self._kp_vars: dict[int, tk.DoubleVar] = {}
        self._selection_frames: dict[int, ctk.CTkFrame] = {}
        self._selected_idx: int = 0

        # Panel references
        self._panels: list = []
        self._debug_panel: Optional[DebugPanel] = None
        self._status_var: Optional[tk.StringVar] = None
        self._master_en_var: Optional[tk.BooleanVar] = None

        # Joystick display widgets
        self._joy_status_label: Optional[ctk.CTkLabel] = None
        self._zone_display_label: Optional[ctk.CTkLabel] = None
        self._text_display_label: Optional[ctk.CTkLabel] = None
        self._joy_vx_label: Optional[ctk.CTkLabel] = None
        self._joy_vy_label: Optional[ctk.CTkLabel] = None
        self._joy_wz_label: Optional[ctk.CTkLabel] = None

        # Override state: when user drags a slider manually, that axis
        # ignores joystick input until the slider is released.
        self._override_vx = False
        self._override_vy = False
        self._override_wz = False

    # ── Lifecycle ────────────────────────────────────────────────────────

    def run(self) -> None:
        """Build the GUI and start the manual update loop (blocking)."""
        self._build()
        root = self._root
        while self._running:
            try:
                root.update()
                root.update_idletasks()
            except Exception:
                break
            _time.sleep(0.05)
        try:
            root.destroy()
        except Exception:
            pass

    def stop(self) -> None:
        self._running = False

    # ═════════════════════════════════════════════════════════════════════
    # Build
    # ═════════════════════════════════════════════════════════════════════

    def _build(self) -> None:
        root = ctk.CTk()
        self._root = root

        try:
            root.tk.call("tk", "scaling", SCALE)
        except Exception:
            pass
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        ctk.set_widget_scaling(SCALE)

        root.title("JoyTextWBG — Joystick + Text Guidance")
        root.geometry(f"{int(580 * SCALE)}x{int(860 * SCALE)}")
        root.minsize(420, 550)
        root.resizable(True, True)
        self._running = True

        # ── Title bar ───────────────────────────────────────────────────
        title_bar = ctk.CTkFrame(root, fg_color="transparent")
        title_bar.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            title_bar, text="JoyTextWBG — Joystick + Text Guidance",
            font=ctk.CTkFont(size=15, family="Arial", weight="bold"),
        ).pack(side="left")

        self._master_en_var = tk.BooleanVar(master=root, value=True)

        def _toggle_master():
            en = self._master_en_var.get()
            self._manager.set_all_enabled(en)
            for v in self._enable_vars.values():
                v.set(en)

        ctk.CTkSwitch(
            title_bar, text="All", variable=self._master_en_var,
            command=_toggle_master,
            font=ctk.CTkFont(size=12, family="Arial"),
            switch_width=int(44 * SCALE), switch_height=int(22 * SCALE),
        ).pack(side="right", padx=4)

        # ── Joystick + Zone header ──────────────────────────────────────
        self._build_joystick_header(root)

        # ── Activation Manager ──────────────────────────────────────────
        self._build_activation_manager(root)

        # ── Tabview ─────────────────────────────────────────────────────
        groups = self._group_guidances()
        if groups:
            tabview = ctk.CTkTabview(root)
            tabview.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            for tab_name, guides in groups.items():
                tabview.add(tab_name)
                tab = tabview.tab(tab_name)
                if tab_name == "Velocity":
                    panel = VelPanel(guides)
                elif tab_name == "Position":
                    panel = PosPanel(guides)
                elif tab_name == "PointReach" and guides:
                    panel = PointReachGuiPanel(guides[0])
                else:
                    continue
                panel.build(tab, root)
                self._panels.append(panel)

        # ── Status bar ──────────────────────────────────────────────────
        self._status_var = tk.StringVar(master=root, value="Ready")
        ctk.CTkLabel(
            root, textvariable=self._status_var,
            anchor="w", font=ctk.CTkFont(size=12, family="Arial"),
            fg_color="#1a1a1a", corner_radius=4, padx=10, pady=4,
        ).pack(fill="x", side="bottom", padx=10, pady=(0, 10))

        def _tick():
            if not self._running:
                return
            self._refresh()
            root.after(100, _tick)

        _tick()

    # ═════════════════════════════════════════════════════════════════════
    # Joystick + Zone Header
    # ═════════════════════════════════════════════════════════════════════

    def _build_joystick_header(self, root) -> None:
        """Build the joystick status / zone / text display section."""
        header = ctk.CTkFrame(root, border_width=1, border_color="#3a3a3a")
        header.pack(fill="x", padx=10, pady=(4, 4))

        # Row 0: Joystick connection status
        joy_row = ctk.CTkFrame(header, fg_color="transparent")
        joy_row.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkLabel(
            joy_row, text="Joystick:",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#888",
        ).pack(side="left")

        self._joy_status_label = ctk.CTkLabel(
            joy_row, text="● disconnected",
            font=ctk.CTkFont(size=11, family="Arial", weight="bold"),
            text_color="#f44",
        )
        self._joy_status_label.pack(side="left", padx=4)

        ctk.CTkLabel(
            joy_row, text="  |  ",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#555",
        ).pack(side="left")

        # Raw joystick values
        ctk.CTkLabel(
            joy_row, text="Raw:",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#888",
        ).pack(side="left")

        self._joy_vx_label = ctk.CTkLabel(
            joy_row, text="vx=+0.00", width=70, anchor="w",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#ccc",
        )
        self._joy_vx_label.pack(side="left")
        self._joy_vy_label = ctk.CTkLabel(
            joy_row, text="vy=+0.00", width=70, anchor="w",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#ccc",
        )
        self._joy_vy_label.pack(side="left")
        self._joy_wz_label = ctk.CTkLabel(
            joy_row, text="wz=+0.00", width=70, anchor="w",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#ccc",
        )
        self._joy_wz_label.pack(side="left")

        # Row 1: Active zones
        zone_row = ctk.CTkFrame(header, fg_color="transparent")
        zone_row.pack(fill="x", padx=8, pady=(2, 2))

        ctk.CTkLabel(
            zone_row, text="Zone:",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#888",
        ).pack(side="left")

        self._zone_display_label = ctk.CTkLabel(
            zone_row, text="(none)",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#ccc",
            anchor="w",
        )
        self._zone_display_label.pack(side="left", padx=4, fill="x", expand=True)

        # Row 2: Semantic text state
        text_row = ctk.CTkFrame(header, fg_color="transparent")
        text_row.pack(fill="x", padx=8, pady=(2, 6))

        ctk.CTkLabel(
            text_row, text="Text:",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#888",
        ).pack(side="left")

        self._text_display_label = ctk.CTkLabel(
            text_row, text="(none)",
            font=ctk.CTkFont(size=12, family="Arial", weight="bold"),
            text_color="#4CAF50", anchor="w",
        )
        self._text_display_label.pack(side="left", padx=4, fill="x", expand=True)

    # ═════════════════════════════════════════════════════════════════════
    # Activation Manager  (mirrors GuiManager._build_activation_manager)
    # ═════════════════════════════════════════════════════════════════════

    def _build_activation_manager(self, root) -> None:
        act_frame = ctk.CTkFrame(root, border_width=1, border_color="#3a3a3a")
        act_frame.pack(fill="x", padx=10, pady=(4, 6))

        # Header
        hdr = ctk.CTkFrame(act_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            hdr, text="Activation Manager",
            font=ctk.CTkFont(size=12, family="Arial", weight="bold"),
            text_color="#8ab4f8",
        ).pack(side="left")
        ctk.CTkLabel(
            hdr, text="Click a row to inspect its heatmap  |  Guidance groups & activation sets",
            font=ctk.CTkFont(size=12, family="Arial"), text_color="#888",
        ).pack(side="left", padx=8)

        # Group guidances by category
        cats: dict[str, tuple[str, list]] = {}
        for idx, g in enumerate(self._manager.guidances):
            key, label = _cat(g)
            if key not in cats:
                cats[key] = (label, [])
            cats[key][1].append((idx, g))

        self._enable_vars.clear()
        self._status_labels.clear()
        self._kp_vars.clear()
        self._selection_frames.clear()

        for _, (label, items) in cats.items():
            self._build_category_section(act_frame, root, label, items)

        # ── Debug heatmap ────────────────────────────────────────────────
        if DEBUG and self._term_resolver is not None:
            try:
                self._debug_panel = DebugPanel(self._manager, self._term_resolver)
                debug_frame = self._debug_panel.build(act_frame, root)
                if debug_frame is not None:
                    debug_frame.pack(fill="x", padx=6, pady=(4, 6))
                    if self._manager.guidances:
                        self._select_guidance(0)
            except Exception as _e:
                print(f"[JoyTextPanel] WARNING: DebugPanel setup failed: {_e}", flush=True)

    def _build_category_section(self, parent, root, label, items) -> None:
        sep = ctk.CTkFrame(parent, height=1, fg_color="#3a3a3a")
        sep.pack(fill="x", padx=8, pady=(4, 0))

        ch = ctk.CTkFrame(parent, fg_color="transparent")
        ch.pack(fill="x", padx=8, pady=(4, 2))
        ctk.CTkLabel(
            ch, text=label,
            font=ctk.CTkFont(size=11, family="Arial", weight="bold"),
            text_color="#ccc",
        ).pack(side="left")

        all_on = all(g.activation.enabled for _, g in items)

        def _toggle():
            new = not all_on
            for idx, g in items:
                self._manager.set_guidance_enabled(idx, new)
                if idx in self._enable_vars:
                    self._enable_vars[idx].set(new)
            self._update_indicators()
            active = len(self._manager.get_active_guidances())
            total = len(self._manager.guidances)
            self._master_en_var.set(active == total)

        ctk.CTkButton(
            ch, text="Toggle Group", width=90, height=22,
            font=ctk.CTkFont(size=11, family="Arial"),
            fg_color="#3a3a3a", hover_color="#555",
            command=_toggle,
        ).pack(side="right")

        rf = ctk.CTkFrame(parent, fg_color="transparent")
        rf.pack(fill="x", padx=6, pady=(0, 4))
        for gidx, g in items:
            self._build_guidance_row(rf, root, gidx, g)

    def _build_guidance_row(self, parent, root, idx, guidance) -> None:
        nm = guidance.guidance_name
        en = guidance.activation.enabled
        kp = guidance.activation.kp
        bg = guidance.activation.guided_body_groups

        # Selection wrapper
        outer = ctk.CTkFrame(parent, fg_color="transparent")
        outer.pack(fill="x", padx=2, pady=1)
        self._selection_frames[idx] = outer
        outer.bind("<Button-1>", lambda e, i=idx: self._select_guidance(i))

        row = ctk.CTkFrame(outer, fg_color="transparent")
        row.pack(fill="x", padx=2, pady=1)
        row.bind("<Button-1>", lambda e, i=idx: self._select_guidance(i))

        # Switch
        var = tk.BooleanVar(master=root, value=en)
        self._enable_vars[idx] = var

        def _make_toggle(_idx=idx, _var=var):
            self._manager.set_guidance_enabled(_idx, _var.get())
            self._update_indicators()
            active = len(self._manager.get_active_guidances())
            total = len(self._manager.guidances)
            self._master_en_var.set(active == total)

        ctk.CTkSwitch(
            row, text=nm, variable=var, command=_make_toggle,
            font=ctk.CTkFont(size=12, family="Arial"),
            switch_width=int(36 * SCALE), switch_height=int(18 * SCALE),
            fg_color="#555", progress_color="#4CAF50",
        ).pack(side="left", padx=(0, 6))

        # kp slider
        ctk.CTkLabel(
            row, text="kp", font=ctk.CTkFont(size=11, family="Arial"),
            text_color="#888", width=16,
        ).pack(side="left")
        kp_var = tk.DoubleVar(master=root, value=kp)
        self._kp_vars[idx] = kp_var
        kp_lbl = ctk.CTkLabel(
            row, text=f"{kp:.2f}", width=34, anchor="e",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#aaa",
        )

        def _on_kp(v, _i=idx, _l=kp_lbl, _v=kp_var):
            val = _v.get()
            _l.configure(text=f"{val:.2f}")
            self._manager.guidances[_i].activation.kp = float(val)

        ctk.CTkSlider(
            row, from_=0.0, to=2.0, variable=kp_var,
            width=int(70 * SCALE), command=_on_kp,
        ).pack(side="left", padx=2)
        kp_lbl.pack(side="left", padx=(0, 8))

        # Status
        st = ctk.CTkLabel(
            row, text="ON" if en else "OFF",
            font=ctk.CTkFont(size=11, family="Arial"),
            text_color="#4CAF50" if en else "#888", width=24,
        )
        st.pack(side="left", padx=(0, 8))
        self._status_labels[idx] = st

        # Body groups
        if bg:
            ctk.CTkLabel(
                row, text=", ".join(bg),
                font=ctk.CTkFont(size=11, family="Arial"),
                text_color="#666", anchor="w",
            ).pack(side="left")

        self._apply_sel_style(idx, idx == self._selected_idx)

    # ── Selection ────────────────────────────────────────────────────────

    def _select_guidance(self, idx) -> None:
        if idx == self._selected_idx:
            return
        old = self._selected_idx
        if old in self._selection_frames:
            self._apply_sel_style(old, False)
        self._selected_idx = idx
        self._apply_sel_style(idx, True)
        if self._debug_panel is not None:
            self._debug_panel.set_selected_guidance(idx)

    def _apply_sel_style(self, idx, sel) -> None:
        f = self._selection_frames.get(idx)
        if f is None:
            return
        f.configure(
            fg_color=_SEL_BG if sel else "transparent",
            border_width=1 if sel else 0,
            border_color=_SEL_BORDER if sel else "",
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def _group_guidances(self) -> dict[str, list]:
        vel, pos, pr = [], [], []
        for g in self._manager.guidances:
            if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
                vel.append(g)
            elif isinstance(g, (HzGuidance, WristGuidance)):
                pos.append(g)
            elif isinstance(g, PointReachGuidance):
                pr.append(g)
        groups = {}
        if vel:
            groups["Velocity"] = vel
        if pos:
            groups["Position"] = pos
        if pr:
            groups["PointReach"] = pr
        return groups

    def _update_indicators(self) -> None:
        for idx, g in enumerate(self._manager.guidances):
            if idx in self._status_labels:
                en = g.activation.enabled
                self._status_labels[idx].configure(
                    text="ON" if en else "OFF",
                    text_color="#4CAF50" if en else "#888",
                )

    # ═════════════════════════════════════════════════════════════════════
    # Periodic refresh (joystick + zone + text display)
    # ═════════════════════════════════════════════════════════════════════

    def _refresh(self) -> None:
        """Called every 100ms.  Updates joystick status, zone info, and text."""
        if not self._running:
            return

        # ── Joystick status ──────────────────────────────────────────────
        connected = self._jtwbg.joystick_connected
        raw = self._jtwbg.get_joystick_raw()

        if self._joy_status_label is not None:
            self._joy_status_label.configure(
                text="● connected" if connected else "○ GUI fallback",
                text_color="#4CAF50" if connected else "#f80",
            )

        if self._joy_vx_label is not None:
            self._joy_vx_label.configure(text=f"vx={raw['vx']:+.2f}")
        if self._joy_vy_label is not None:
            self._joy_vy_label.configure(text=f"vy={raw['vy']:+.2f}")
        if self._joy_wz_label is not None:
            self._joy_wz_label.configure(text=f"wz={raw['wz']:+.2f}")

        # ── Zone display ─────────────────────────────────────────────────
        zones = self._jtwbg.get_active_zones()
        if zones:
            parts = []
            for zone, strength in zones:
                if strength >= 0.99:
                    parts.append(f"{zone.name}")
                else:
                    parts.append(f"{zone.name}({strength:.0%})")
            zone_text = " + ".join(parts)
        else:
            zone_text = "(none)"

        if self._zone_display_label is not None:
            self._zone_display_label.configure(text=zone_text)

        # ── Semantic text display ────────────────────────────────────────
        # In constant mode: show the dominant zone's constant_text.
        # In interp mode: show pair weights and blend percentages.
        if self._mapping.interp_mode == "constant":
            if zones:
                zone = zones[0][0]
                if zone.constant_text:
                    text_display = zone.constant_text
                else:
                    text_display = zone.name
            else:
                text_display = "(none)"
        else:
            # Interp mode: use compute_pair_weights to show active directions
            r = (raw["vx"] ** 2 + raw["vy"] ** 2) ** 0.5
            pair_weights = self._mapping.compute_pair_weights(zones, r)

            text_parts = []
            for pair_name, (text_a, text_b) in self._mapping.text_pairs.items():
                w = pair_weights.get(pair_name, 0.0)
                if abs(w) < 0.01:
                    continue
                if w > 0:
                    if w > 0.95:
                        text_parts.append(f"{text_b}")
                    else:
                        text_parts.append(f"{text_a}→{text_b} ({w:+.0%})")
                else:
                    if w < -0.95:
                        text_parts.append(f"{text_a}")
                    else:
                        text_parts.append(f"{text_b}→{text_a} ({w:+.0%})")
            text_display = " | ".join(text_parts) if text_parts else "(none)"

        if self._text_display_label is not None:
            self._text_display_label.configure(text=text_display)

        # ── Status bar ───────────────────────────────────────────────────
        if self._status_var is not None:
            parts = []
            g_cmd = self._jtwbg.get_current_guidance()
            parts.append(f"Cmd: vx={g_cmd['vx']:+.2f} vy={g_cmd['vy']:+.2f} wz={g_cmd['wz']:+.2f}")
            for g in self._manager.guidances:
                s = g.get_cmd_summary()
                parts.append(f"[{g.guidance_name}] en={'on' if s.get('enabled', g.activation.enabled) else 'off'}")
            self._status_var.set("  |  ".join(parts))

        # ── Debug heatmap ────────────────────────────────────────────────
        if self._debug_panel is not None:
            self._debug_panel.refresh()
