"""export_config_editor.py — customtkinter config editor for the deploy export.

DEPLOY-WORKFLOW-GUI-017.  Opens a CustomTkinter window pre-loaded from the GIVEN
Python config (via ``tools/deploy_config_schema``) and returns an
:class:`EditorResult` with the user's edits, or ``None`` when cancelled.

The WBG tab reuses the WBGv2 GUI panels (``VelPanel`` / ``PosPanel`` /
``PointReachGuiPanel``) built on OUR OWN guidance instances
(``WholeBodyGuidance(guidances=..., gui_enabled=False)`` — no GUI thread),
plus per-axis range min/max + body-group editors seeded from the config.

Import-safe: customtkinter is imported inside a try/except and the module can
be imported on a headless box (a display is only needed to *open* the window).
"""

from __future__ import annotations

import sys
from typing import Optional

try:
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import messagebox
    _CTK_AVAILABLE = True
    from diffusion_policy.task_provider.whole_body_guidance.gui.ctk_linux_fix import _apply as _apply_ctk_fix
    _apply_ctk_fix()
except ImportError:  # pragma: no cover - exercised on ctk-less installs
    _CTK_AVAILABLE = False
    ctk = None  # type: ignore
    tk = None  # type: ignore
    messagebox = None  # type: ignore

from diffusion_policy.task_provider.whole_body_guidance.gui import SCALE
from diffusion_policy.task_provider.whole_body_guidance.gui.panel_vel import VelPanel
from diffusion_policy.task_provider.whole_body_guidance.gui.panel_pos import PosPanel
from diffusion_policy.task_provider.whole_body_guidance.gui.panel_point_reach import PointReachGuiPanel
from diffusion_policy.task_provider.whole_body_guidance.whole_body_guidance import WholeBodyGuidance
from diffusion_policy.task_provider.whole_body_guidance.body_groups import _BODY_ABBR
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.axes_vel import (
    VxGuidance, VyGuidance, VzGuidance, WzGuidance,
)
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.hz_guide import HzGuidance
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.wrist_guide import WristGuidance
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.point_reach import PointReachGuidance

from diffusion_deploy.tools.deploy_config_schema import (
    EditorDefaults,
    EditorResult,
    GUIDANCE_KEYS,
    OBS_PROFILES,
    SAMPLER_MODES,
    coerce_field,
    derive_sampler_mode,
    guided_groups_to_body_indices,
    validate_actor_overrides,
)

# ── Fonts ──────────────────────────────────────────────────────────────────


def _f(size: int = 11, weight: str = "normal"):
    # Font sizes are logical pixels.  customtkinter's ``set_widget_scaling``
    # (driven by ``SCALE``) scales them at render time, so we must NOT pre-multiply
    # here — pre-multiplying would double-scale (SCALE^2) and break HiDPI (×2).
    return ("Arial", size, weight)


# ── Guidance key mapping ───────────────────────────────────────────────────

_GUIDANCE_NAME_TO_KEY = {
    "vx": "vx_guide",
    "vy": "vy_guide",
    "vz": "vz_guide",
    "wz": "wz_guide",
    "hz": "hz_guide",
    "wrist_left": "left_wrist_guide",
    "wrist_right": "right_wrist_guide",
    "PointReach": "point_reach",
}


class DeployConfigEditor:
    """CustomTkinter editor for the deploy export config.

    Tabs: Backbone / Actor-DDIM / WBG / Advanced / Export.  On ``Export`` the
    edited values are coerced + validated and stashed in ``self._result``.
    """

    # Ranges surfaced by the range editor, keyed by guidance config key.
    _RANGE_SPECS = {
        "vx_guide": [("range", "range")],
        "vy_guide": [("range", "range")],
        "vz_guide": [("range", "range")],
        "wz_guide": [("range", "range")],
        "hz_guide": [("z_range", "z_range")],
        "left_wrist_guide": [("dx_range", "dx"), ("dy_range", "dy"), ("dz_range", "dz")],
        "right_wrist_guide": [("dx_range", "dx"), ("dy_range", "dy"), ("dz_range", "dz")],
        "point_reach": [
            ("vx_range", "vx"), ("vy_range", "vy"), ("vz_range", "vz"),
            ("target_x_range", "tgt_x"), ("target_y_range", "tgt_y"),
            ("target_z_range", "tgt_z"),
        ],
    }

    def __init__(self, defaults: EditorDefaults):
        if not _CTK_AVAILABLE:
            raise RuntimeError(
                "customtkinter is not installed; cannot open the config editor")
        self._defaults = defaults
        self._result: Optional[EditorResult] = None

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        ctk.set_widget_scaling(SCALE)

        self._root = ctk.CTk()
        self._root.title("Deploy Config Editor  (export_policy --gui)")
        self._root.geometry(f"{int(760*SCALE)}x{int(820*SCALE)}")
        self._root.minsize(640, 600)

        # ── vars ──────────────────────────────────────────────────────
        self._actor_vars: dict[str, object] = {}
        self._advanced_vars: dict[str, object] = {}
        self._wbg_master_var = tk.BooleanVar(master=self._root, value=False)
        self._wbg_guidance_mode_var = tk.StringVar(master=self._root, value="classifier")
        self._wbg_mode_var = tk.StringVar(master=self._root, value="simple")
        self._wbg_enable_zeta_var = tk.BooleanVar(master=self._root, value=True)
        self._wbg_enable_damping_var = tk.BooleanVar(master=self._root, value=True)
        self._wbg_instances: list = []
        self._wbg_key_by_name: dict[str, str] = {}
        self._range_vars: dict[tuple[str, str], tuple] = {}
        self._bg_vars: dict[str, tk.StringVar] = {}
        self._body_index_vars: dict[tuple[str, int], tk.BooleanVar] = {}
        self._body_index_sets: dict[str, set[int]] = {}
        self._body_idx_sel_var: Optional[tk.StringVar] = None
        self._body_idx_selected_key: Optional[str] = None
        self._body_idx_grid = None
        self._activation_vars: dict[str, tk.BooleanVar] = {}
        self._kp_vars: dict[str, tk.DoubleVar] = {}
        self._status_labels: dict[str, tk.Label] = {}
        self._sampler_readout = None
        self._export_summary = None

        self._build()
        self._seed_actor_vars()
        self._seed_advanced_vars()
        self._seed_wbg()
        self._refresh_export_summary()

    # ═════════════════════════════════════════════════════════════════════
    # Build
    # ═════════════════════════════════════════════════════════════════════

    def _build(self) -> None:
        self._tabview = ctk.CTkTabview(self._root)
        self._tabview.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        for name in ("Backbone", "Actor/DDIM", "WBG", "Advanced", "Export"):
            self._tabview.add(name)

        self._build_backbone_tab()
        self._build_actor_tab()
        self._build_wbg_tab()
        self._build_advanced_tab()
        self._build_export_tab()
        self._build_bottom_bar()

    # ── Backbone ──────────────────────────────────────────────────────

    def _build_backbone_tab(self) -> None:
        tab = self._tabview.tab("Backbone")
        ctk.CTkLabel(
            tab, text="Policy Backbone  (Python-aligned names)",
            font=_f(13, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            tab, text="C++ config_parser checks: cond_dim == backbone_cond_dim, "
                      "x_input_dim == x_output_dim, cross_attn_mode ∈ "
                      "{full,state,action,no_attn}, cross_attn_window >= 0.",
            font=_f(10), text_color="#888",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        self._actor_vars["x_input_dim"] = self._entry_row(tab, "x_input_dim", "int")
        self._actor_vars["x_output_dim"] = self._entry_row(tab, "x_output_dim", "int")
        self._actor_vars["cond_dim"] = self._entry_row(tab, "cond_dim", "int")
        self._actor_vars["n_cond_steps"] = self._entry_row(tab, "n_cond_steps", "int")
        self._actor_vars["cross_attn_window"] = self._entry_row(
            tab, "cross_attn_window", "int-or-null", hint="empty = null (disabled)")

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row, text="cross_attn_mode", width=180, anchor="w",
                     font=_f(12, "bold")).pack(side="left")
        var = tk.StringVar(master=self._root, value="full")
        self._actor_vars["cross_attn_mode"] = var
        ctk.CTkOptionMenu(row, variable=var, values=["full", "state", "action", "no_attn"],
                          font=_f(11)).pack(side="left")

    # ── Actor/DDIM ────────────────────────────────────────────────────

    def _build_actor_tab(self) -> None:
        tab = self._tabview.tab("Actor/DDIM")
        ctk.CTkLabel(
            tab, text="Actor & Diffusion",
            font=_f(13, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        self._actor_vars["clean_past_state"] = self._switch_row(
            tab, "clean_past_state")
        self._actor_vars["delay_action_step"] = self._entry_row(
            tab, "delay_action_step", "float",
            hint="signed offset; fractions interpolate clean adjacent slots")
        self._actor_vars["no_state_override"] = self._switch_row(
            tab, "no_state_override")
        self._actor_vars["use_ns_ddim"] = self._switch_row(
            tab, "use_ns_ddim")
        self._actor_vars["randomize_noise_schedule"] = self._switch_row(
            tab, "randomize_noise_schedule")

        self._actor_vars["data_profile"] = self._entry_row(
            tab, "data_profile", "str")
        self._actor_vars["ddim_steps"] = self._entry_row(
            tab, "ddim_steps", "int-or-null", hint="empty = null (full DDPM, no acceleration)")
        self._actor_vars["ddim_eta"] = self._entry_row(
            tab, "ddim_eta", "float", hint="0.0 = fully deterministic DDIM")

        # Sampler-mode auto readout + optional override
        srow = ctk.CTkFrame(tab, fg_color="transparent")
        srow.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(srow, text="sampler_mode (auto)", width=180, anchor="w",
                     font=_f(12, "bold")).pack(side="left")
        self._sampler_readout = ctk.CTkLabel(srow, text="", width=140, anchor="w",
                                             font=_f(11, "bold"), text_color="#8ab4f8")
        self._sampler_readout.pack(side="left")
        override_var = tk.StringVar(master=self._root, value="")
        self._actor_vars["sampler_mode_override"] = override_var
        ctk.CTkOptionMenu(srow, variable=override_var,
                          values=[""] + list(SAMPLER_MODES),
                          font=_f(10), width=110).pack(side="right")
        ctk.CTkLabel(srow, text="override", font=_f(10),
                     text_color="#888").pack(side="right", padx=(0, 4))

        for var in (self._actor_vars["use_ns_ddim"], self._actor_vars["randomize_noise_schedule"],
                    self._actor_vars["ddim_steps"], self._actor_vars["ddim_eta"]):
            self._trace_sampler(var)
        self._update_sampler_readout()

    # ── WBG ───────────────────────────────────────────────────────────

    def _build_wbg_tab(self) -> None:
        tab = self._tabview.tab("WBG")
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(
            scroll, text="Whole-Body Guidance  (reuses the WBGv2 GUI panels)",
            font=_f(13, "bold"),
        ).pack(anchor="w", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            scroll, text="C++ exports vx/vy/wz only; vz/hz/wrists/point_reach are "
                         "Python-only and round-trip in the config.",
            font=_f(10), text_color="#888",
        ).pack(anchor="w", padx=8, pady=(0, 6))

        # Master switch + mode selects
        mrow = ctk.CTkFrame(scroll, fg_color="transparent")
        mrow.pack(fill="x", padx=8, pady=4)
        ctk.CTkSwitch(mrow, text="enabled", variable=self._wbg_master_var,
                      font=_f(12, "bold"),
                      switch_width=44, switch_height=22,
                      ).pack(side="left")
        ctk.CTkLabel(mrow, text="guidance_mode", font=_f(11), text_color="#888").pack(
            side="left", padx=(16, 4))
        ctk.CTkOptionMenu(mrow, variable=self._wbg_guidance_mode_var,
                          values=["classifier", "pd"], font=_f(10), width=110
                          ).pack(side="left")
        ctk.CTkLabel(mrow, text="mode", font=_f(11), text_color="#888").pack(
            side="left", padx=(16, 4))
        ctk.CTkOptionMenu(mrow, variable=self._wbg_mode_var,
                          values=["simple", "integration"], font=_f(10), width=120
                          ).pack(side="left")

        # DDIM compensation switches (C++ deploy parity)
        comp_row = ctk.CTkFrame(scroll, fg_color="transparent")
        comp_row.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(comp_row, text="DDIM compensation",
                     font=_f(11, "bold"), text_color="#8ab4f8",
                     ).pack(side="left")
        ctk.CTkSwitch(comp_row, text="zeta_comp",
                      variable=self._wbg_enable_zeta_var,
                      font=_f(10),
                      switch_width=40, switch_height=20,
                      ).pack(side="left", padx=(16, 8))
        ctk.CTkSwitch(comp_row, text="damping_comp",
                      variable=self._wbg_enable_damping_var,
                      font=_f(10),
                      switch_width=40, switch_height=20,
                      ).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(comp_row, text="  integrated zeta mass · damping compensation",
                     font=_f(9), text_color="#888",
                     ).pack(side="left", padx=(8, 0))

        # Container frames: activation rows + panels + range editor are built
        # in _seed_wbg() once the guidance instances exist.
        self._wbg_act_frame = ctk.CTkFrame(scroll, border_width=1, border_color="#3a3a3a")
        self._wbg_act_frame.pack(fill="x", padx=8, pady=(4, 6))
        self._wbg_panels_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._wbg_panels_frame.pack(fill="x", padx=4, pady=2)
        self._wbg_body_idx_frame = ctk.CTkFrame(scroll, border_width=1, border_color="#3a3a3a")
        self._wbg_body_idx_frame.pack(fill="x", padx=8, pady=(6, 4))
        self._wbg_range_frame = ctk.CTkFrame(scroll, border_width=1, border_color="#3a3a3a")
        self._wbg_range_frame.pack(fill="x", padx=8, pady=(6, 4))

    # ── Advanced ──────────────────────────────────────────────────────

    def _build_advanced_tab(self) -> None:
        tab = self._tabview.tab("Advanced")
        ctk.CTkLabel(
            tab, text="Advanced export options",
            font=_f(13, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        self._advanced_vars["obs_profile"] = self._option_row(
            tab, "obs_profile", list(OBS_PROFILES))
        self._advanced_vars["use_fk"] = self._switch_row_adv(tab, "use_fk")
        self._advanced_vars["urdf_path"] = self._entry_row_adv(tab, "urdf_path", "str")
        self._advanced_vars["output"] = self._entry_row_adv(tab, "output", "str")
        self._advanced_vars["deploy_config"] = self._entry_row_adv(
            tab, "deploy_config", "str")
        self._advanced_vars["device"] = self._entry_row_adv(tab, "device", "str")
        self._advanced_vars["mode"] = self._option_row(
            tab, "mode", ["backbone", "full_loop"])
        ctk.CTkLabel(
            tab, text="NOTE: --mode full_loop does NOT write a deploy config (the "
                      "editor's actor edits apply to --mode backbone only).",
            font=_f(10), text_color="#b8860b",
        ).pack(anchor="w", padx=12, pady=(0, 8))
        self._advanced_vars["write_actor_config"] = self._switch_row_adv(
            tab, "write_actor_config")
        self._advanced_vars["write_normalizer_stats"] = self._switch_row_adv(
            tab, "write_normalizer_stats")

    # ── Export ────────────────────────────────────────────────────────

    def _build_export_tab(self) -> None:
        tab = self._tabview.tab("Export")
        ctk.CTkLabel(
            tab, text="Export summary & validation",
            font=_f(13, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        self._export_summary = ctk.CTkTextbox(tab, font=_f(11), wrap="word",
                                              height=560)
        self._export_summary.pack(fill="both", expand=True, padx=12, pady=(4, 8))
        self._export_summary.configure(state="disabled")

    # ── Bottom bar ────────────────────────────────────────────────────

    def _build_bottom_bar(self) -> None:
        bar = ctk.CTkFrame(self._root, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkButton(bar, text="Cancel", width=100, height=30, fg_color="#555",
                      hover_color="#777", font=_f(11),
                      command=self._on_cancel).pack(side="right", padx=(8, 0))
        ctk.CTkButton(bar, text="Export", width=120, height=30,
                      fg_color="#2d6a4f", hover_color="#40916c", font=_f(11, "bold"),
                      command=self._on_export).pack(side="right")

    # ═════════════════════════════════════════════════════════════════════
    # Widget helpers
    # ═════════════════════════════════════════════════════════════════════

    def _entry_row(self, parent, label, kind, hint=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row, text=label, width=180, anchor="w",
                     font=_f(12, "bold")).pack(side="left")
        var = tk.StringVar(master=self._root, value="")
        ctk.CTkEntry(row, textvariable=var, width=220,
                     font=_f(11)).pack(side="left")
        if hint:
            ctk.CTkLabel(row, text=hint, font=_f(9),
                         text_color="#888").pack(side="left", padx=(8, 0))
        return var

    def _switch_row(self, parent, label):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row, text=label, width=180, anchor="w",
                     font=_f(12, "bold")).pack(side="left")
        var = tk.BooleanVar(master=self._root, value=False)
        ctk.CTkSwitch(row, variable=var, font=_f(11),
                      switch_width=40, switch_height=20,
                      ).pack(side="left")
        return var

    def _option_row(self, parent, label, values):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row, text=label, width=180, anchor="w",
                     font=_f(12, "bold")).pack(side="left")
        var = tk.StringVar(master=self._root, value=values[0] if values else "")
        ctk.CTkOptionMenu(row, variable=var, values=values,
                          font=_f(11)).pack(side="left")
        return var

    def _entry_row_adv(self, parent, label, kind):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row, text=label, width=180, anchor="w",
                     font=_f(12, "bold")).pack(side="left")
        var = tk.StringVar(master=self._root, value="")
        ctk.CTkEntry(row, textvariable=var, width=380,
                     font=_f(11)).pack(side="left")
        return var

    def _switch_row_adv(self, parent, label):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row, text=label, width=180, anchor="w",
                     font=_f(12, "bold")).pack(side="left")
        var = tk.BooleanVar(master=self._root, value=False)
        ctk.CTkSwitch(row, variable=var, font=_f(11),
                      switch_width=40, switch_height=20,
                      ).pack(side="left")
        return var

    # ═════════════════════════════════════════════════════════════════════
    # Seeding
    # ═════════════════════════════════════════════════════════════════════

    def _seed_actor_vars(self) -> None:
        a = self._defaults.actor
        for k, var in self._actor_vars.items():
            if k == "sampler_mode_override":
                continue
            if isinstance(var, tk.BooleanVar):
                var.set(bool(a.get(k, False)))
            elif isinstance(var, tk.StringVar):
                v = a.get(k, 0 if k == "delay_action_step" else None)
                var.set("" if v is None else str(v))
        self._update_sampler_readout()

    def _seed_advanced_vars(self) -> None:
        adv = self._defaults.advanced
        for k, var in self._advanced_vars.items():
            if isinstance(var, tk.BooleanVar):
                var.set(bool(adv.get(k, False)))
            elif isinstance(var, tk.StringVar):
                v = adv.get(k)
                var.set("" if v is None else str(v))

    def _seed_wbg(self) -> None:
        wbg = self._defaults.wbg or {}
        self._wbg_master_var.set(bool(wbg.get("enabled", False)))
        self._wbg_guidance_mode_var.set(str(wbg.get("guidance_mode", "classifier")))
        self._wbg_mode_var.set(str(wbg.get("mode", "simple")))
        self._wbg_enable_zeta_var.set(bool(wbg.get("enable_zeta_comp", True)))
        self._wbg_enable_damping_var.set(bool(wbg.get("enable_damping_comp", True)))
        guidances = wbg.get("guidances", {}) or {}
        if not guidances:
            guidances = {key: {"enabled": False, "kp": 1.0} for key in GUIDANCE_KEYS}

        try:
            self._wbg = WholeBodyGuidance(
                profile=str(wbg.get("profile", "g1_standard")),
                guidances=guidances,
                gui_enabled=False,
                mode=str(wbg.get("mode", "simple")),
                guidance_mode=str(wbg.get("guidance_mode", "classifier")),
            )
        except Exception as exc:  # bad/malformed WBG config → minimal fallback
            print(f"[export_config_editor] WBG build fallback: {exc}", flush=True)
            self._wbg = WholeBodyGuidance(
                guidances={key: {"enabled": False, "kp": 1.0} for key in GUIDANCE_KEYS},
                gui_enabled=False,
                mode="simple",
                guidance_mode="classifier",
            )

        self._wbg_instances = list(self._wbg._manager.guidances)
        self._wbg_key_by_name = {}
        for g in self._wbg_instances:
            key = _GUIDANCE_NAME_TO_KEY.get(getattr(g, "guidance_name", ""))
            if key:
                self._wbg_key_by_name[getattr(g, "guidance_name")] = key

        # Authoritative per-body index set per guidance, seeded from the named
        # body groups.  The per-body grid toggles edit this set; the serialized
        # ``body_indices`` (sorted, unique) is authoritative for the deploy path.
        self._body_index_sets = {}
        for g in self._wbg_instances:
            key = self._wbg_key_by_name.get(getattr(g, "guidance_name", ""))
            if key:
                self._body_index_sets[key] = set(guided_groups_to_body_indices(
                    getattr(g.activation, "guided_body_groups", []) or []))

        self._build_activation_rows(self._wbg_act_frame)
        self._build_wbg_panels(self._wbg_panels_frame)
        self._build_body_index_editor(self._wbg_body_idx_frame)
        self._build_range_editor(self._wbg_range_frame)

    # ── WBG activation rows (mirrors GuiManager._build_guidance_row) ──

    def _build_activation_rows(self, parent) -> None:
        ctk.CTkLabel(parent, text="Activation  (switch + kp gain + guided body groups)",
                     font=_f(11, "bold"), text_color="#8ab4f8"
                     ).pack(anchor="w", padx=8, pady=(6, 2))
        for g in self._wbg_instances:
            nm = getattr(g, "guidance_name", "?")
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)
            en_var = tk.BooleanVar(master=self._root, value=g.activation.enabled)
            self._activation_vars[nm] = en_var

            def _toggle(_g=g, _v=en_var):
                _g.activation.enabled = _v.get()
                lbl = self._status_labels.get(_g.guidance_name)
                if lbl is not None:
                    lbl.configure(text="ON" if _v.get() else "OFF",
                                  text_color="#4CAF50" if _v.get() else "#888")
            ctk.CTkSwitch(row, text=nm, variable=en_var, command=_toggle,
                          font=_f(11),
                          switch_width=36, switch_height=18,
                          fg_color="#555", progress_color="#4CAF50",
                          ).pack(side="left", padx=(0, 6))
            kp_var = tk.DoubleVar(master=self._root, value=g.activation.kp)
            self._kp_vars[nm] = kp_var
            kp_lbl = ctk.CTkLabel(row, text=f"{g.activation.kp:.2f}", width=34,
                                  anchor="e", font=_f(10), text_color="#aaa")

            def _on_kp(v, _g=g, _l=kp_lbl, _v=kp_var):
                val = _v.get()
                _l.configure(text=f"{val:.2f}")
                _g.activation.kp = float(val)
            ctk.CTkLabel(row, text="kp", font=_f(10), text_color="#888",
                         width=16).pack(side="left")
            ctk.CTkSlider(row, from_=0.0, to=2.0, variable=kp_var, width=70,
                          command=_on_kp).pack(side="left", padx=2)
            kp_lbl.pack(side="left", padx=(0, 8))
            st = ctk.CTkLabel(row, text="ON" if g.activation.enabled else "OFF",
                              font=_f(10),
                              text_color="#4CAF50" if g.activation.enabled else "#888",
                              width=24)
            st.pack(side="left", padx=(0, 6))
            self._status_labels[nm] = st
            bg = getattr(g.activation, "guided_body_groups", []) or []
            ctk.CTkLabel(row, text=", ".join(bg), font=_f(10),
                         text_color="#666", anchor="w").pack(side="left")

    # ── WBG panels (VelPanel / PosPanel / PointReachGuiPanel) ─────────

    def _build_wbg_panels(self, parent) -> None:
        vel = [g for g in self._wbg_instances
               if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance))]
        pos = [g for g in self._wbg_instances
               if isinstance(g, (HzGuidance, WristGuidance))]
        pr = [g for g in self._wbg_instances if isinstance(g, PointReachGuidance)]

        if vel:
            VelPanel(vel).build(parent, self._root)
        if pos:
            PosPanel(pos).build(parent, self._root)
        if pr:
            PointReachGuiPanel(pr[0]).build(parent, self._root)

    # ── Range + body-group editor ─────────────────────────────────────

    def _build_range_editor(self, parent) -> None:
        ctk.CTkLabel(
            parent, text="Per-axis range (min/max) & body groups  (serialized into the "
                         "returned guidances dict)",
            font=_f(11, "bold"), text_color="#8ab4f8",
        ).pack(anchor="w", padx=8, pady=(6, 2))

        for g in self._wbg_instances:
            nm = getattr(g, "guidance_name", "?")
            key = self._wbg_key_by_name.get(nm)
            if key is None:
                continue
            specs = self._RANGE_SPECS.get(key, [])
            bg = getattr(g.activation, "guided_body_groups", []) or []

            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(row, text=nm, width=90, anchor="w",
                         font=_f(11, "bold")).pack(side="left")

            for range_key, label in specs:
                rng = self._range_of(g, range_key)
                lo_var = tk.StringVar(master=self._root, value=f"{rng[0]:g}")
                hi_var = tk.StringVar(master=self._root, value=f"{rng[1]:g}")
                self._range_vars[(key, range_key)] = (lo_var, hi_var)
                ctk.CTkLabel(row, text=label, font=_f(9),
                             text_color="#888").pack(side="left", padx=(6, 2))
                e = ctk.CTkEntry(row, textvariable=lo_var, width=52,
                                 font=_f(10))
                e.pack(side="left")
                ctk.CTkLabel(row, text="..", font=_f(9),
                             text_color="#888").pack(side="left", padx=1)
                e2 = ctk.CTkEntry(row, textvariable=hi_var, width=52,
                                  font=_f(10))
                e2.pack(side="left")

            bg_var = tk.StringVar(master=self._root, value=", ".join(bg))
            self._bg_vars[key] = bg_var
            # Live-sync: editing the named-group entry recomputes the per-body
            # index set (authoritative for deploy) and refreshes the grid.
            # NOTE: bind key/bg_var as defaults so each loop iteration keeps its
            # own closure values (otherwise all traces share the last iteration).
            def _on_bg_change(*_a, _key=key, _var=bg_var):
                self._on_body_groups_text(_key, _var)

            bg_var.trace_add("write", _on_bg_change)
            ctk.CTkLabel(row, text="bodies", font=_f(9),
                         text_color="#888").pack(side="left", padx=(8, 2))
            ctk.CTkEntry(row, textvariable=bg_var, width=150,
                         font=_f(10)).pack(side="left")

    @staticmethod
    def _range_of(g, range_key: str):
        try:
            if range_key == "range":
                return g.value_range
            if range_key == "z_range":
                return g.z_range
            return getattr(g, range_key)
        except Exception:
            return (-5.0, 5.0)

    # ── Per-body activation grid ────────────────────────────────────────

    def _build_body_index_editor(self, parent) -> None:
        """Per-body activation grid: 30 checkboxes (5 cols × 6 rows) per guidance.

        A guidance selector picks which guidance's 30-cell grid is shown; the
        grid is seeded from the selected guidance's current guided indices
        (derived from the named ``guided_body_groups``).  Toggling a cell
        updates the authoritative ``_body_index_sets`` (serialized as
        ``body_indices``) and the guidance activation's
        ``body_intensity_overrides`` so the Python WBG respects the exact
        toggled set.

        Uses native ``tk.Checkbutton`` (styled to match the dark theme) instead
        of ``ctk.CTkCheckBox``: a ``CTkCheckBox`` leaves a stale variable trace /
        ``after`` callback on root destroy that hangs a subsequent ``CTk()`` in
        the same process (hit when the GUI smoke tests build several editors),
        and showing all 30×N cells at once makes that teardown cost explode.
        A single 30-cell grid keeps the widget count flat regardless of how many
        guidances the config carries.
        """
        ctk.CTkLabel(
            parent, text="Per-body activation  (5 cols × 6 rows; toggle each body 0–29)",
            font=_f(11, "bold"), text_color="#8ab4f8",
        ).pack(anchor="w", padx=8, pady=(6, 2))

        sel_row = ctk.CTkFrame(parent, fg_color="transparent")
        sel_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(sel_row, text="guidance", font=_f(10, "bold"),
                     text_color="#ccc").pack(side="left")
        names = [
            getattr(g, "guidance_name", "?")
            for g in self._wbg_instances
            if self._wbg_key_by_name.get(getattr(g, "guidance_name", ""))
        ]
        first_key = None
        if self._wbg_instances:
            first_key = self._wbg_key_by_name.get(
                getattr(self._wbg_instances[0], "guidance_name", ""))
        self._body_idx_selected_key = first_key
        sel_var = tk.StringVar(master=self._root, value=first_key or "")
        self._body_idx_sel_var = sel_var
        ctk.CTkOptionMenu(sel_row, variable=sel_var, values=names, font=_f(10),
                          width=140, command=self._on_body_idx_sel_change,
                          ).pack(side="left", padx=(8, 0))

        # Single grid (native tk; see the class docstring note on CTkCheckBox).
        self._body_idx_grid = tk.Frame(parent, bg="#2b2b2b")
        self._body_idx_grid.pack(anchor="w", padx=12, pady=(2, 6))
        self._refresh_body_index_grid(first_key)

    def _on_body_idx_sel_change(self, name: str) -> None:
        key = self._wbg_key_by_name.get(name)
        if key:
            self._body_idx_selected_key = key
            self._refresh_body_index_grid(key)

    def _refresh_body_index_grid(self, key) -> None:
        """Rebuild the 30-cell grid for guidance *key* from ``_body_index_sets``."""
        for child in self._body_idx_grid.winfo_children():
            child.destroy()
        if key is None:
            return
        guided = self._body_index_sets.get(key, set())
        # Native tk fonts are NOT scaled by ctk.set_widget_scaling — pre-scale.
        _font = ("Arial", max(int(9 * SCALE), 9))
        for i in range(30):
            var = tk.BooleanVar(master=self._root, value=(i in guided))
            self._body_index_vars[(key, i)] = var

            def _toggle(_key=key, _i=i, _v=var):
                self._on_body_index_toggle(_key, _i, _v)

            tk.Checkbutton(
                self._body_idx_grid, text=f"{i:02d} {_BODY_ABBR[i]}",
                variable=var, command=_toggle, font=_font,
                bg="#2b2b2b", fg="#d0d0d0", activebackground="#2b2b2b",
                activeforeground="#ffffff", selectcolor="#1e1e1e",
                highlightthickness=0, bd=0,
            ).grid(row=i // 5, column=i % 5, sticky="w", padx=3, pady=1)

    def _on_body_index_toggle(self, key: str, idx: int, var) -> None:
        """Toggle body *idx* in the guidance's authoritative per-body set."""
        guided = bool(var.get())
        s = self._body_index_sets.setdefault(key, set())
        if guided:
            s.add(idx)
        else:
            s.discard(idx)
        g = self._guidance_for_key(key)
        if g is not None:
            # Per-body override drives the activation's body intensity so the
            # Python WBG heatmap/gradient respects the exact toggled set.
            g.activation.body_intensity_overrides[idx] = 1.0 if guided else 0.0

    def _on_body_groups_text(self, key: str, var) -> None:
        """Recompute the per-body index set when the named-group entry changes."""
        g = self._guidance_for_key(key)
        names = [s.strip() for s in var.get().split(",") if s.strip()]
        if g is not None and names:
            g.activation.guided_body_groups = names
            g.activation.group_intensities = {n: 1.0 for n in names}
            # The group entry is now the source of truth — drop any per-body
            # overrides left by earlier grid toggles.
            g.activation.body_intensity_overrides.clear()
        self._body_index_sets[key] = set(guided_groups_to_body_indices(names))
        if self._body_idx_selected_key == key:
            self._refresh_body_index_grid(key)

    # ═════════════════════════════════════════════════════════════════════
    # Sampler readout
    # ═════════════════════════════════════════════════════════════════════

    def _trace_sampler(self, var) -> None:
        try:
            var.trace_add("write", lambda *_: self._update_sampler_readout())
        except Exception:
            pass

    def _update_sampler_readout(self) -> None:
        if self._sampler_readout is None:
            return
        fields = self._current_actor_fields()
        mode = derive_sampler_mode(fields)
        override = fields.get("sampler_mode_override")
        self._sampler_readout.configure(text=str(override or mode))

    # ═════════════════════════════════════════════════════════════════════
    # Value collection
    # ═════════════════════════════════════════════════════════════════════

    def _current_actor_fields(self) -> dict:
        fields: dict = {}
        for k, var in self._actor_vars.items():
            if isinstance(var, tk.BooleanVar):
                fields[k] = var.get()
            elif isinstance(var, tk.StringVar):
                fields[k] = var.get().strip()
        return coerce_field(fields)

    def _apply_range_edits(self) -> None:
        """Push range + body-group edits into the guidance instances."""
        for (key, range_key), (lo_var, hi_var) in self._range_vars.items():
            g = self._guidance_for_key(key)
            if g is None:
                continue
            try:
                lo = float(lo_var.get())
                hi = float(hi_var.get())
            except ValueError:
                continue
            rng = (lo, hi)
            if range_key == "range" and isinstance(
                    g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
                g._range = rng
            elif range_key == "z_range" and isinstance(g, HzGuidance):
                g._z_range = rng
            elif hasattr(g, range_key):
                setattr(g, "_" + range_key, rng)
        for key, var in self._bg_vars.items():
            g = self._guidance_for_key(key)
            if g is None:
                continue
            names = [s.strip() for s in var.get().split(",") if s.strip()]
            if names:
                g.activation.guided_body_groups = names
                g.activation.group_intensities = {n: 1.0 for n in names}

    def _guidance_for_key(self, key: str):
        for g in self._wbg_instances:
            if self._wbg_key_by_name.get(getattr(g, "guidance_name", "")) == key:
                return g
        return None

    def _collect_wbg(self) -> dict:
        self._apply_range_edits()
        guidances: dict = {}
        for g in self._wbg_instances:
            nm = getattr(g, "guidance_name", "?")
            key = self._wbg_key_by_name.get(nm)
            if key is None:
                continue
            bg = list(getattr(g.activation, "guided_body_groups", []) or [])
            # ``body_indices`` is the authoritative per-body set for the deploy
            # path (sorted, unique); ``body_groups`` is kept for the Python
            # round-trip (the per-body grid / group entry edits this set).
            body_indices = sorted(self._body_index_sets.get(
                key, set(guided_groups_to_body_indices(bg))))
            cfg: dict = {
                "enabled": bool(g.activation.enabled),
                "kp": float(g.activation.kp),
                "body_groups": {"guided": bg},
                "body_indices": body_indices,
            }
            if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
                cfg["range"] = [float(g.value_range[0]), float(g.value_range[1])]
                cfg["command"] = float(g.get_value())
            elif isinstance(g, HzGuidance):
                cfg["z_range"] = [float(g.z_range[0]), float(g.z_range[1])]
                cfg["z_init"] = float(g.get_target())
            elif isinstance(g, WristGuidance):
                cfg["dx_range"] = [float(g.dx_range[0]), float(g.dx_range[1])]
                cfg["dy_range"] = [float(g.dy_range[0]), float(g.dy_range[1])]
                cfg["dz_range"] = [float(g.dz_range[0]), float(g.dz_range[1])]
            elif isinstance(g, PointReachGuidance):
                pt = g.get_point_target()
                cfg.update({
                    "kp_pos": float(g.kp_pos),
                    "vx_range": list(g.vx_range),
                    "vy_range": list(g.vy_range),
                    "vz_range": list(g.vz_range),
                    "wz_range": list(g.wz_range),
                    "target_x_range": list(g.target_x_range),
                    "target_y_range": list(g.target_y_range),
                    "target_z_range": list(g.target_z_range),
                    "target_init": [float(pt["x"]), float(pt["y"]), float(pt["z"])],
                })
            guidances[key] = cfg
        return {
            "enabled": bool(self._wbg_master_var.get()),
            "guidance_mode": str(self._wbg_guidance_mode_var.get()),
            "mode": str(self._wbg_mode_var.get()),
            "enable_zeta_comp": bool(self._wbg_enable_zeta_var.get()),
            "enable_damping_comp": bool(self._wbg_enable_damping_var.get()),
            "guidances": guidances,
        }

    def _collect_advanced(self) -> dict:
        adv: dict = {}
        for k, var in self._advanced_vars.items():
            if isinstance(var, tk.BooleanVar):
                adv[k] = var.get()
            elif isinstance(var, tk.StringVar):
                adv[k] = var.get().strip()
        return adv

    # ═════════════════════════════════════════════════════════════════════
    # Actions
    # ═════════════════════════════════════════════════════════════════════

    def _on_cancel(self) -> None:
        self._result = None
        self._root.destroy()

    def _on_export(self) -> None:
        actor_fields = self._current_actor_fields()
        errors = validate_actor_overrides(actor_fields)

        if errors:
            if messagebox is not None:
                messagebox.showerror("Invalid settings",
                                     "Cannot export:\n  - " + "\n  - ".join(errors))
            else:
                print("Invalid settings:\n  - " + "\n  - ".join(errors), file=sys.stderr)
            return

        override = actor_fields.get("sampler_mode_override")
        if override:
            actor_fields["sampler_mode"] = override
        actor_fields.pop("sampler_mode_override", None)

        wbg = self._collect_wbg()
        advanced = self._collect_advanced()

        self._result = EditorResult(actor=actor_fields, wbg=wbg, advanced=advanced)
        self._root.destroy()

    def _refresh_export_summary(self) -> None:
        if self._export_summary is None:
            return
        fields = self._current_actor_fields()
        mode = fields.get("sampler_mode_override") or derive_sampler_mode(fields)
        lines = [
            "Actor / diffusion",
            f"  sampler_mode      : {mode}",
            f"  cond_dim          : {fields.get('cond_dim')}",
            f"  x_input_dim       : {fields.get('x_input_dim')}",
            f"  x_output_dim      : {fields.get('x_output_dim')}",
            f"  cross_attn_window : {fields.get('cross_attn_window')}",
            f"  cross_attn_mode   : {fields.get('cross_attn_mode')}",
            f"  ddim_steps        : {fields.get('ddim_steps')}",
            f"  ddim_eta          : {fields.get('ddim_eta')}",
            "",
            "WBG",
            f"  enabled           : {self._wbg_master_var.get()}",
            f"  guidance_mode     : {self._wbg_guidance_mode_var.get()}",
            f"  mode              : {self._wbg_mode_var.get()}",
            f"  enable_zeta_comp  : {self._wbg_enable_zeta_var.get()}",
            f"  enable_damping_comp: {self._wbg_enable_damping_var.get()}",
        ]
        self._export_summary.configure(state="normal")
        self._export_summary.delete("1.0", "end")
        self._export_summary.insert("1.0", "\n".join(lines))
        self._export_summary.configure(state="disabled")

    # ═════════════════════════════════════════════════════════════════════
    # Lifecycle
    # ═════════════════════════════════════════════════════════════════════

    def run(self) -> Optional[EditorResult]:
        self._root.mainloop()
        return self._result

    def close(self) -> None:
        """Programmatic close (used by the GUI smoke test)."""
        try:
            self._root.destroy()
        except Exception:
            pass


def run_deploy_config_editor(defaults: EditorDefaults) -> Optional[EditorResult]:
    """Open the editor and return the user's edits, or ``None`` if cancelled.

    Args:
        defaults: Pre-loaded defaults from the GIVEN Python config.

    Returns:
        :class:`EditorResult` on Export, ``None`` on Cancel.
    """
    if not _CTK_AVAILABLE:
        raise RuntimeError(
            "customtkinter is not installed; cannot open the config editor")
    editor = DeployConfigEditor(defaults)
    return editor.run()


# ═════════════════════════════════════════════════════════════════════════
# Standalone CLI: load a config YAML → defaults → editor → dump result YAML
# ═════════════════════════════════════════════════════════════════════════

def _standalone_main(argv=None) -> int:
    import argparse
    import pathlib

    from omegaconf import OmegaConf
    from diffusion_policy.utils.config_loader import load_config
    from diffusion_policy import DIFFUSION_POLICY_ROOT
    from diffusion_deploy.tools.deploy_config_schema import (
        extract_actor_defaults, extract_wbg_defaults, to_plain,
    )

    ap = argparse.ArgumentParser(
        description="Standalone deploy-config editor (no checkpoint required).")
    ap.add_argument("--config", default="g1prdp_cond_diffuse.yaml",
                    help="Python config YAML name/path (default: "
                         "g1prdp_cond_diffuse.yaml)")
    ap.add_argument("-o", "--output", default="editor_result.yaml",
                    help="Where to dump the edited result YAML (default: "
                         "editor_result.yaml)")
    args = ap.parse_args(argv)

    config_path = pathlib.Path(args.config)
    if not config_path.is_file():
        candidate = pathlib.Path(DIFFUSION_POLICY_ROOT) / "config_files" / args.config
        if candidate.is_file():
            config_path = candidate
    cfg = load_config(config_path)
    OmegaConf.resolve(cfg)
    actor_plain = to_plain(cfg.policy.actor)

    defaults = EditorDefaults(
        actor=extract_actor_defaults(actor_plain),
        wbg=extract_wbg_defaults(actor_plain),
        advanced={},
    )
    result = run_deploy_config_editor(defaults)
    if result is None:
        print("Cancelled.")
        return 0
    result_yaml = {
        "actor": result.actor,
        "whole_body_guidance_config": result.wbg,
        "advanced": result.advanced,
    }
    with open(args.output, "w") as f:
        import yaml
        yaml.dump(result_yaml, f, default_flow_style=None, sort_keys=False)
    print(f"Editor result saved to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(_standalone_main())
