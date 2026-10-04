"""GuiManager — CustomTkinter lifecycle manager for WholeBodyGuidance v2.

Runs on its own daemon thread with ``CTk()`` root.  Builds a ``CTkTabview``
with grouped tabs: "Velocity" for vx/vy/vz/wz sliders, "Position" for hz +
wrist controls, optional "PointReach" and "DestinationFollow".

The **Activation Manager** panel shows every guidance grouped by category,
each with an independent enable switch, kp-gain slider, and body-group label.
When ``DEBUG`` is ``True``, a per-guidance body-intensity heatmap is embedded
below — click any guidance row to select it; the heatmap follows.
"""

from __future__ import annotations

import threading
import time as _time
from typing import Optional

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
    from . import ctk_linux_fix  # noqa: F401
except ImportError:
    _CTK_AVAILABLE = False

from . import SCALE

from ..guidance_activation_manager import GuidanceActivationManager
from ..guidance_types.vel_based import VelBasedGuidance
from ..guidance_types.pos_based import PosBasedGuidance
from ..guidance_types.point_reach import PointReachGuidance
from ..guidance_types.axes_vel import VxGuidance, VyGuidance, VzGuidance, WzGuidance
from ..guidance_types.hz_guide import HzGuidance
from ..guidance_types.wrist_guide import WristGuidance
from ..body_groups import G1_BODY_GROUPS, DEBUG
from ..term_resolver import TermResolver
from .gui_panel_base import BaseGuiPanel
from .panel_vel import VelPanel
from .panel_pos import PosPanel
from .panel_point_reach import PointReachGuiPanel
from .panel_destination_follow import DestinationFollowGuiPanel
from .panel_joystick import JoystickPanel
from .debug_panel import DebugPanel

# ── Shared constants ──────────────────────────────────────────────────────

_SEL_BORDER = "#8ab4f8"
_SEL_BG = "#2a3a4a"


def _cat(g):
    """Return (key, label) for a guidance instance."""
    if getattr(g, "guidance_name", "") == "destination_follow":
        return ("DestinationFollow", "Destination Follow Group")
    if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
        return ("Velocity", "Velocity Group")
    elif isinstance(g, (HzGuidance, WristGuidance)):
        return ("Position", "Position Group")
    elif isinstance(g, PointReachGuidance):
        return ("PointReach", "PointReach Group")
    return ("Other", "Other")



class GuiManager:
    """GUI lifecycle manager for WholeBodyGuidance v2.

    - Daemon thread + manual ``update()`` loop
    - ``CTkTabview``: "Velocity", "Position", "PointReach" tabs
    - **Activation Manager** with per-guidance switches, kp sliders and a
      per-guidance debug heatmap (when ``DEBUG=True``)
    - Optional **Joystick** section (enable switch + connection status + live
      vx/vy/wz/hz readout) when a :class:`~.joystick_handle.JoystickHandle` is
      supplied via the ``joystick`` kwarg
    - Scale from ``gui.__init__.SCALE``
    """

    def __init__(
        self,
        activation_manager: GuidanceActivationManager,
        term_resolver: TermResolver | None = None,
        gui_enabled: bool = True,
        joystick=None,  # optional JoystickHandle (small controller, not the facade)
        destination_follow_owner=None,
    ):
        self._manager = activation_manager
        self._term_resolver = term_resolver
        self._gui_enabled = gui_enabled
        self._joystick_handle = joystick
        self._destination_follow_owner = destination_follow_owner
        if gui_enabled and not _CTK_AVAILABLE:
            print(
                "[WholeBodyGuidance] WARNING: GUI is enabled in config but customtkinter is "
                "not installed. The GUI window will NOT appear. "
                "Install with: pip install customtkinter",
                flush=True,
            )
        self._root_tk = None
        self._gui_thread: Optional[threading.Thread] = None
        self._gui_started = False
        self._gui_running = False
        self._panels: list[BaseGuiPanel] = []
        self._enable_vars: dict[int, tk.BooleanVar] = {}
        self._status_var = None
        self._debug_panel: Optional[DebugPanel] = None
        self._joy_panel: Optional[JoystickPanel] = None
        self._selected_idx: int = 0
        self._selection_frames: dict[int, ctk.CTkFrame] = {}

    # ── Grouping ──────────────────────────────────────────────────────────

    def _group_guidances(self) -> dict[str, list]:
        vel, pos, pr, destination = [], [], [], []
        for g in self._manager.guidances:
            if getattr(g, "guidance_name", "") == "destination_follow":
                destination.append(g)
            elif isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
                vel.append(g)
            elif isinstance(g, (HzGuidance, WristGuidance)):
                pos.append(g)
            elif isinstance(g, PointReachGuidance):
                pr.append(g)
        groups = {}
        if vel: groups["Velocity"] = vel
        if pos: groups["Position"] = pos
        if pr:  groups["PointReach"] = pr
        if destination: groups["DestinationFollow"] = destination
        return groups

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        if not _CTK_AVAILABLE or not self._gui_enabled or self._gui_started:
            return
        self._gui_started = True
        self._gui_thread = threading.Thread(target=self._run_gui, daemon=True)
        self._gui_thread.start()

    def stop(self) -> None:
        self._gui_running = False
        try:
            if self._root_tk is not None:
                self._root_tk.destroy()
        except Exception:
            pass

    def _run_gui(self) -> None:
        import traceback
        try:
            self._build_gui(master=None)
        except Exception as e:
            print(f"[WholeBodyGuidance] GUI build failed: {e}", flush=True)
            traceback.print_exc()
            self._gui_running = False
            return
        root = self._root_tk
        while self._gui_running:
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
        print("[WholeBodyGuidance] GUI exited", flush=True)

    # ═════════════════════════════════════════════════════════════════════
    # Build
    # ═════════════════════════════════════════════════════════════════════

    def _build_gui(self, master=None) -> None:
        if master is None:
            root = ctk.CTk()
        else:
            root = ctk.CTkToplevel(master=master)
        self._root_tk = root

        try:
            root.tk.call("tk", "scaling", SCALE)
        except Exception:
            pass
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        ctk.set_widget_scaling(SCALE)

        root.title("Whole-Body Guidance v2")
        root.geometry(f"{int(560*SCALE)}x{int(780*SCALE)}")
        root.minsize(400, 500)
        root.resizable(True, True)
        self._gui_running = True

        # ── Title bar ───────────────────────────────────────────────────
        title_bar = ctk.CTkFrame(root, fg_color="transparent")
        title_bar.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(title_bar, text="Whole-Body Guidance",
                     font=ctk.CTkFont(size=15, family="Arial", weight="bold")).pack(side="left")

        self._master_en_var = tk.BooleanVar(master=root, value=True)
        def _toggle_master():
            en = self._master_en_var.get()
            self._manager.set_all_enabled(en)
            for v in self._enable_vars.values():
                v.set(en)
        ctk.CTkSwitch(title_bar, text="All", variable=self._master_en_var,
                      command=_toggle_master, font=ctk.CTkFont(size=12, family="Arial"),
                      switch_width=44, switch_height=22,
                      ).pack(side="right", padx=4)

        # ── Joystick source (optional, hardware opt-in) ─────────────────
        self._build_joystick_section(root)

        # ── Activation Manager (includes debug heatmap) ──────────────────
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
                elif tab_name == "DestinationFollow" and guides:
                    panel = DestinationFollowGuiPanel(
                        guides[0], owner=self._destination_follow_owner)
                else:
                    continue
                panel.build(tab, root)
                self._panels.append(panel)

        # ── Status bar ──────────────────────────────────────────────────
        self._status_var = tk.StringVar(master=root, value="Ready")
        ctk.CTkLabel(root, textvariable=self._status_var,
                     anchor="w", font=ctk.CTkFont(size=12, family="Arial"),
                     fg_color="#1a1a1a", corner_radius=4, padx=10, pady=4,
                     ).pack(fill="x", side="bottom", padx=10, pady=(0, 10))

        def _tick():
            if not self._gui_running:
                return
            parts = []
            for g in self._manager.guidances:
                s = g.get_cmd_summary()
                parts.append(f"[{g.guidance_name}] en={'on' if s.get('enabled', g.activation.enabled) else 'off'}")
            pr = self._manager.get_point_reach_guidance()
            if pr is not None:
                pt = pr.get_point_target()
                if pt.get("has_world_data"):
                    parts.append(f"tgt=({pt['x']:+.1f},{pt['y']:+.1f},{pt['z']:+.2f})")
                else:
                    parts.append("pelvis=?")
            self._status_var.set("  |  ".join(parts))
            self._update_indicators()
            for panel in self._panels:
                try:
                    panel.refresh_status()
                except Exception:
                    pass
            if self._debug_panel is not None:
                self._debug_panel.refresh()
            if self._joy_panel is not None:
                self._joy_panel.refresh()
            root.after(100, _tick)
        _tick()

    # ═════════════════════════════════════════════════════════════════════
    # Joystick source
    # ═════════════════════════════════════════════════════════════════════

    def _build_joystick_section(self, root) -> None:
        """Build the joystick panel when a ``JoystickHandle`` was supplied."""
        if self._joystick_handle is None:
            return
        self._joy_panel = JoystickPanel(self._joystick_handle)
        self._joy_panel.build(root, root)

    # ═════════════════════════════════════════════════════════════════════
    # Activation Manager
    # ═════════════════════════════════════════════════════════════════════

    def _build_activation_manager(self, root) -> None:
        act_frame = ctk.CTkFrame(root, border_width=1, border_color="#3a3a3a")
        act_frame.pack(fill="x", padx=10, pady=(4, 6))

        # Header
        hdr = ctk.CTkFrame(act_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(hdr, text="Activation Manager",
                     font=ctk.CTkFont(size=12, family="Arial", weight="bold"),
                     text_color="#8ab4f8").pack(side="left")
        ctk.CTkLabel(hdr, text="Click a row to inspect its heatmap  |  Guidance groups & activation sets",
                     font=ctk.CTkFont(size=12, family="Arial"),
                     text_color="#888").pack(side="left", padx=8)

        # Group guidances by category
        cats: dict[str, tuple[str, list]] = {}
        for idx, g in enumerate(self._manager.guidances):
            key, label = _cat(g)
            if key not in cats:
                cats[key] = (label, [])
            cats[key][1].append((idx, g))

        self._enable_vars.clear()
        self._status_labels: dict[int, ctk.CTkLabel] = {}
        self._kp_vars: dict[int, tk.DoubleVar] = {}
        self._selection_frames.clear()

        for _, (label, items) in cats.items():
            self._build_category_section(act_frame, root, label, items)

        # ── Debug heatmap (inside activation manager) ────────────────────
        if DEBUG and self._term_resolver is not None:
            try:
                self._debug_panel = DebugPanel(self._manager, self._term_resolver)
                debug_frame = self._debug_panel.build(act_frame, root)
                if debug_frame is None:
                    print("[GuiManager] WARNING: DebugPanel.build() returned None — skipping heatmap", flush=True)
                else:
                    debug_frame.pack(fill="x", padx=6, pady=(4, 6))
                    if self._manager.guidances:
                        self._select_guidance(0)
            except Exception as _e:
                print(f"[GuiManager] WARNING: DebugPanel setup failed: {_e}", flush=True)

    def _build_category_section(self, parent, root, label, items):
        sep = ctk.CTkFrame(parent, height=1, fg_color="#3a3a3a")
        sep.pack(fill="x", padx=8, pady=(4, 0))

        ch = ctk.CTkFrame(parent, fg_color="transparent")
        ch.pack(fill="x", padx=8, pady=(4, 2))
        ctk.CTkLabel(ch, text=label,
                     font=ctk.CTkFont(size=11, family="Arial", weight="bold"),
                     text_color="#ccc").pack(side="left")

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
        ctk.CTkButton(ch, text="Toggle Group", width=90, height=22,
                      font=ctk.CTkFont(size=11, family="Arial"),
                      fg_color="#3a3a3a", hover_color="#555",
                      command=_toggle).pack(side="right")

        rf = ctk.CTkFrame(parent, fg_color="transparent")
        rf.pack(fill="x", padx=6, pady=(0, 4))
        for gidx, g in items:
            self._build_guidance_row(rf, root, gidx, g)

    # ═════════════════════════════════════════════════════════════════════
    # Guidance row
    # ═════════════════════════════════════════════════════════════════════

    def _build_guidance_row(self, parent, root, idx, guidance):
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
        ctk.CTkSwitch(row, text=nm, variable=var, command=_make_toggle,
                      font=ctk.CTkFont(size=12, family="Arial"),
                      switch_width=36, switch_height=18,
                      fg_color="#555", progress_color="#4CAF50",
                      ).pack(side="left", padx=(0, 6))

        # kp slider
        ctk.CTkLabel(row, text="kp", font=ctk.CTkFont(size=11, family="Arial"),
                     text_color="#888", width=16).pack(side="left")
        kp_var = tk.DoubleVar(master=root, value=kp)
        self._kp_vars[idx] = kp_var
        kp_lbl = ctk.CTkLabel(row, text=f"{kp:.2f}", width=34, anchor="e",
                               font=ctk.CTkFont(size=11, family="Arial"),
                               text_color="#aaa")
        def _on_kp(v, _i=idx, _l=kp_lbl, _v=kp_var):
            val = _v.get(); _l.configure(text=f"{val:.2f}")
            self._manager.guidances[_i].activation.kp = float(val)
        ctk.CTkSlider(row, from_=0.0, to=2.0, variable=kp_var,
                      width=70, command=_on_kp,
                      ).pack(side="left", padx=2)
        kp_lbl.pack(side="left", padx=(0, 8))

        # Status
        st = ctk.CTkLabel(row, text="ON" if en else "OFF",
                          font=ctk.CTkFont(size=11, family="Arial"),
                          text_color="#4CAF50" if en else "#888", width=24)
        st.pack(side="left", padx=(0, 8))
        self._status_labels[idx] = st

        # Body groups
        if bg:
            ctk.CTkLabel(row, text=", ".join(bg),
                         font=ctk.CTkFont(size=11, family="Arial"),
                         text_color="#666", anchor="w").pack(side="left")

        self._apply_sel_style(idx, idx == self._selected_idx)

    # ── Selection ────────────────────────────────────────────────────────

    def _select_guidance(self, idx):
        if idx == self._selected_idx:
            return
        old = self._selected_idx
        if old in self._selection_frames:
            self._apply_sel_style(old, False)
        self._selected_idx = idx
        self._apply_sel_style(idx, True)
        if self._debug_panel is not None:
            self._debug_panel.set_selected_guidance(idx)

    def _apply_sel_style(self, idx, sel):
        f = self._selection_frames.get(idx)
        if f is None:
            return
        f.configure(fg_color=_SEL_BG if sel else "transparent",
                     border_width=1 if sel else 0,
                     border_color=_SEL_BORDER if sel else "")

    # ── Helpers ──────────────────────────────────────────────────────────

    def _update_indicators(self):
        for idx, g in enumerate(self._manager.guidances):
            if idx in self._status_labels:
                en = g.activation.enabled
                self._status_labels[idx].configure(
                    text="ON" if en else "OFF",
                    text_color="#4CAF50" if en else "#888")

    @property
    def root_tk(self):
        return self._root_tk
