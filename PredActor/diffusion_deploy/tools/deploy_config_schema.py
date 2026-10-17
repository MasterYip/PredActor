"""deploy_config_schema.py — headless schema core for the deploy config editor.

Pure-logic module (NO customtkinter import).  Owns the field specs, default
extraction, validation, sampler-mode derivation, body-group mapping, and the
actor/WBG merge helpers shared by:

  * ``tools/export_config_editor.py``  — the customtkinter editor GUI
  * ``tools/export_policy.py --gui``   — the export merge path

Config naming is Python-aligned: the editable fields carry the exact names the
Python training config uses under ``policy.actor`` (``backbone.{x_input_dim,
...}``, ``clean_past_state``, ``data_profile``, ``ddim_*``, ...), so defaults
come from the GIVEN config YAML (e.g. ``g1prdp_cond_diffuse.yaml``), never from
hardcoded values.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from typing import Any, Optional

from diffusion_policy.task_provider.whole_body_guidance.body_groups import G1_BODY_GROUPS

# ── Field specs ────────────────────────────────────────────────────────────

#: Editable Policy Backbone fields (Python config names).
BACKBONE_FIELDS: list[str] = [
    "x_input_dim",
    "x_output_dim",
    "cond_dim",
    "n_cond_steps",
    "cross_attn_window",
    "cross_attn_mode",
]

#: Editable Actor & Diffusion fields (Python config names).
ACTOR_DDIM_FIELDS: list[str] = [
    "delay_action_step",
    "clean_past_state",
    "no_state_override",
    "data_profile",
    "ddim_steps",
    "ddim_eta",
    "use_ns_ddim",
    "randomize_noise_schedule",
]

#: Valid ``cross_attn_mode`` values (accepted by the C++ config_parser).
CROSS_ATTN_MODES: tuple[str, ...] = ("full", "state", "action", "no_attn")

#: Valid ``obs_profile`` values written into the deploy config.
OBS_PROFILES: tuple[str, ...] = ("G1", "G1_RLObs", "G1_Q", "G1WQ")

#: Valid ``sampler_mode`` values (C++ config_parser cross-check).
SAMPLER_MODES: tuple[str, ...] = (
    "full_ddpm", "scalar_ddim", "rolling_ddim", "rolling_ddpm", "ns_ddim",
)

#: Whole-body-guidance keys in the v2 ``guidances`` block.
GUIDANCE_KEYS: tuple[str, ...] = (
    "vx_guide", "vy_guide", "vz_guide", "wz_guide",
    "hz_guide", "left_wrist_guide", "right_wrist_guide", "point_reach",
)

#: Fields stored as integers (None when the GUI entry is empty).
_INT_FIELDS: set[str] = {
    "x_input_dim", "x_output_dim", "cond_dim", "n_cond_steps",
    "cross_attn_window", "ddim_steps",
}

#: Fields stored as floats (None when the GUI entry is empty).
_FLOAT_FIELDS: set[str] = {"ddim_eta", "delay_action_step"}

#: Fields stored as booleans (accepted from GUI string vars).
_BOOL_FIELDS: set[str] = {
    "clean_past_state", "no_state_override", "use_ns_ddim",
    "randomize_noise_schedule",
}


# ── Editor dataclasses ─────────────────────────────────────────────────────

@dataclass
class EditorDefaults:
    """Default values pre-loaded from the GIVEN Python config (not hardcoded).

    Attributes:
        actor: Flat dict of Python-aligned actor/diffusion fields
            (BACKBONE_FIELDS + ACTOR_DDIM_FIELDS keys).
        wbg: ``whole_body_guidance_config`` v2 dict.
        advanced: Advanced export fields (obs_profile / use_fk / urdf_path /
            output / deploy_config / device / mode / write_* flags).
    """
    actor: dict = field(default_factory=dict)
    wbg: dict = field(default_factory=dict)
    advanced: dict = field(default_factory=dict)


@dataclass
class EditorResult:
    """Edited values returned by the GUI (``None`` result = user cancelled).

    Attributes:
        actor: Flat dict of Python-aligned actor/diffusion fields.
        wbg: Edited ``whole_body_guidance_config`` v2 dict.
        advanced: Edited advanced export fields.
    """
    actor: dict = field(default_factory=dict)
    wbg: dict = field(default_factory=dict)
    advanced: dict = field(default_factory=dict)


# ── Plain conversion ───────────────────────────────────────────────────────

def to_plain(v: Any) -> Any:
    """Recursively convert OmegaConf / nested values to plain Python types."""
    if isinstance(v, Mapping):
        return {k: to_plain(v[k]) for k in v}
    if isinstance(v, (list, tuple)):
        return [to_plain(i) for i in v]
    return v


def _first(d: Mapping, *keys: str, default: Any = None) -> Any:
    """Return the first present key from ``keys`` in ``d`` (with fallback)."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


# ── Default extraction ─────────────────────────────────────────────────────

def extract_actor_defaults(
    actor_dict: Optional[Mapping], runner_dict: Optional[Mapping] = None
) -> dict:
    """Extract config-YAML-first editable actor fields.

    Args:
        actor_dict: ``cfg.policy.actor`` (dict / OmegaConf DictConfig / None).

    Returns:
        Flat dict keyed by the Python-aligned field names
        (BACKBONE_FIELDS + ACTOR_DDIM_FIELDS).  Missing keys fall back to
        sensible defaults so old checkpoints without the fields still open
        the editor.
    """
    actor = to_plain(actor_dict) if actor_dict else {}
    runner = to_plain(runner_dict) if runner_dict else {}
    bb = actor.get("backbone", {}) or {}
    ddim_steps = actor.get("ddim_steps")
    return {
        # Backbone
        "x_input_dim": bb.get("x_input_dim", 384),
        "x_output_dim": bb.get("x_output_dim", 384),
        "cond_dim": bb.get("cond_dim", 96),
        "n_cond_steps": bb.get("n_cond_steps", 4),
        "cross_attn_window": bb.get("cross_attn_window"),  # None = null
        "cross_attn_mode": bb.get("cross_attn_mode", "full"),
        # Actor & diffusion
        "delay_action_step": runner.get("delay_action_step", 0),
        "clean_past_state": actor.get("clean_past_state", False),
        "no_state_override": actor.get("no_state_override", False),
        "data_profile": actor.get("data_profile", ""),
        "ddim_steps": ddim_steps,  # None = null (DDPM, no DDIM acceleration)
        "ddim_eta": actor.get("ddim_eta", 0.0),
        "use_ns_ddim": actor.get("use_ns_ddim", False),
        "randomize_noise_schedule": actor.get("randomize_noise_schedule", False),
    }


def extract_wbg_defaults(actor_dict: Optional[Mapping]) -> dict:
    """Extract the ``whole_body_guidance_config`` v2 dict from the actor block.

    Returns ``{}`` when the config carries no WBG block (the editor then
    seeds the WBG tab from the PRDP defaults).
    """
    actor = to_plain(actor_dict) if actor_dict else {}
    wbg = actor.get("whole_body_guidance_config", {}) or {}
    return to_plain(wbg)


# ── Validation ─────────────────────────────────────────────────────────────

def validate_actor_overrides(fields: Mapping) -> list[str]:
    """Return a human-readable error list for edited actor fields.

    Checks mirror the C++ ``config_parser.cpp`` cross-checks:
      * ``cross_attn_mode`` ∈ CROSS_ATTN_MODES
      * ``x_input_dim == x_output_dim``
      * ``cross_attn_window >= 0``
      * ``ddim_eta >= 0``
    """
    errors: list[str] = []
    mode = fields.get("cross_attn_mode")
    if mode is not None and mode not in CROSS_ATTN_MODES:
        errors.append(
            f"cross_attn_mode must be one of {list(CROSS_ATTN_MODES)}, got {mode!r}")

    xi = fields.get("x_input_dim")
    xo = fields.get("x_output_dim")
    if xi is not None and xo is not None and int(xi) != int(xo):
        errors.append(f"x_input_dim ({xi}) != x_output_dim ({xo})")

    w = fields.get("cross_attn_window")
    if w is not None and int(w) < 0:
        errors.append(f"cross_attn_window must be >= 0, got {w}")

    eta = fields.get("ddim_eta")
    if eta is not None and float(eta) < 0:
        errors.append(f"ddim_eta must be >= 0, got {eta}")
    delay = fields.get("delay_action_step")
    if delay is not None and not math.isfinite(float(delay)):
        errors.append(f"delay_action_step must be finite, got {delay}")
    return errors


# ── Sampler-mode derivation (mirrors _extract_actor_config) ────────────────

def derive_sampler_mode(fields: Mapping) -> str:
    """Derive the C++ ``sampler_mode`` from edited actor fields.

    Mirrors the four branches of ``export_policy._extract_actor_config`` so the
    GUI merge and the export path always agree:
      * use_ns_ddim                  → "ns_ddim"
      * ddim_steps is not None       → "rolling_ddim" (randomize_noise_schedule)
                                        else "scalar_ddim"
      * randomize_noise_schedule     → "rolling_ddpm"
      * else                         → "full_ddpm"
    """
    if bool(fields.get("use_ns_ddim", False)):
        return "ns_ddim"
    ddim_steps = fields.get("ddim_steps")
    if ddim_steps is not None:
        return ("rolling_ddim" if bool(fields.get("randomize_noise_schedule", False))
                else "scalar_ddim")
    if bool(fields.get("randomize_noise_schedule", False)):
        return "rolling_ddpm"
    return "full_ddpm"


# ── Body-group mapping ─────────────────────────────────────────────────────

def guided_groups_to_body_indices(groups: Optional[list[str]]) -> list[int]:
    """Map guidance body-group names to sorted G1 body indices.

    Examples::
        guided_groups_to_body_indices(["pelvis_torso"]) == [0, 9]
        guided_groups_to_body_indices(["torso"]) == [0, 3, 4, 5, 6, 7, 8, 9]
    """
    if not groups:
        return []
    idx: set[int] = set()
    for g in groups:
        idx.update(G1_BODY_GROUPS.get(g, []))
    return sorted(idx)


# ── Field coercion (GUI str vars → typed) ─────────────────────────────────

def coerce_field(fields: Mapping) -> dict:
    """Convert GUI ``str``/``StringVar``-style values to typed values.

    Integer/float fields treat empty strings (and ``"None"``/``"null"``) as
    ``None``.  Boolean fields accept ``"1"/"true"/"yes"/"on"``.
    """
    out: dict = dict(fields)
    for k in _INT_FIELDS:
        if k not in out:
            continue
        v = out[k]
        if isinstance(v, str):
            v = v.strip()
        if v in (None, "", "None", "null"):
            out[k] = None
        else:
            out[k] = int(v)
    for k in _FLOAT_FIELDS:
        if k not in out:
            continue
        v = out[k]
        if isinstance(v, str):
            v = v.strip()
        if v in (None, "", "None", "null"):
            out[k] = None
        else:
            out[k] = float(v)
    for k in _BOOL_FIELDS:
        if k in out and isinstance(out[k], str):
            out[k] = out[k].strip().lower() in ("1", "true", "yes", "on")
    return out


# ── Merge helpers ──────────────────────────────────────────────────────────

def merge_actor_override(actor_cfg: dict, gui_actor: Mapping) -> dict:
    """Merge GUI actor fields into the extracted ``actor_cfg`` (GUI wins).

    Recomputes derived fields so the deploy YAML stays coherent:
      * ``sampler_mode``            ← derive_sampler_mode
      * ``backbone_cond_dim``       ← cond_dim (Python ``backbone.cond_dim``)
      * ``motion_dim`` / ``has_motion_cond`` ← cond_dim vs obs_dim
    """
    merged = dict(actor_cfg)
    for k in BACKBONE_FIELDS + ACTOR_DDIM_FIELDS:
        if k in gui_actor:
            merged[k] = gui_actor[k]

    cond = gui_actor.get("cond_dim")
    if cond is not None:
        cond = int(cond)
        merged["backbone_cond_dim"] = cond
        actor_type = merged.get("actor_type", "")
        if actor_type in ("joint_diffusion", "diffuse_cloc", "prdp"):
            merged["motion_dim"] = cond
            merged["has_motion_cond"] = cond > 0
        else:
            merged["has_motion_cond"] = cond > int(merged.get("obs_dim", 0))
            merged["motion_dim"] = (cond - int(merged.get("obs_dim", 0))
                                    if merged["has_motion_cond"] else 0)

    merged["sampler_mode"] = derive_sampler_mode(merged)
    return merged


def wbg_to_deploy_block(wbg_cfg: Optional[Mapping]) -> Optional[dict]:
    """Translate a Python ``whole_body_guidance_config`` into the C++ deploy form.

    This is the canonical implementation of the exporter's ``_wbg_deploy_block``
    (moved here so the GUI merge and the headless export always agree).  The C++
    config_parser reads ``model.whole_body_guidance`` as::

        enabled, mode, trajectory_mode, axis_gradient_impl, dt,
        enable_zeta_comp, enable_damping_comp,
        vx/vy/wz (each: enabled, command, kp[, body_indices])

    ``body_groups`` names are NOT translated here (the headless path keeps the
    C++ default index set unless numeric ``body_indices`` are present); the GUI
    serialization computes ``body_indices`` from the edited body groups before
    returning.  Returns ``None`` when WBG is not enabled (caller omits the
    block).  C++ consumes ONLY vx/vy/wz; vz/hz/wrists/point_reach round-trip in
    the Python config but are not exported to the C++ block.
    """
    if not wbg_cfg or not wbg_cfg.get("enabled", False):
        return None
    guidances = wbg_cfg.get("guidances", {}) or {}

    def _axis(name: str) -> dict:
        g = guidances.get(name) or {}
        axis: dict = {
            "enabled": bool(g.get("enabled", False)),
            "command": 0.0,
            "kp": float(g.get("kp", 1.0)),
        }
        # Optional per-axis override (used by the --wbg-config CLI flag and the
        # GUI serialization): a default command in m/s (vx/vy) or rad/s (wz),
        # and numeric body indices.  Training configs do not carry these, so
        # they stay at the C++ defaults.
        if g.get("command") is not None:
            axis["command"] = float(g["command"])
        if g.get("body_indices"):
            axis["body_indices"] = [int(i) for i in g["body_indices"]]
        return axis

    return {
        "enabled": True,
        "mode": str(wbg_cfg.get("guidance_mode", "classifier")),
        "trajectory_mode": str(wbg_cfg.get("mode", "simple")),
        "axis_gradient_impl": str(wbg_cfg.get("axis_gradient_impl", "sequential")),
        "dt": 0.02,
        "enable_zeta_comp": bool(wbg_cfg.get("enable_zeta_comp", True)),
        "enable_damping_comp": bool(wbg_cfg.get("enable_damping_comp", True)),
        "vx": _axis("vx_guide"),
        "vy": _axis("vy_guide"),
        "wz": _axis("wz_guide"),
    }


def merge_wbg_override(actor_cfg: dict, gui_wbg: Optional[Mapping]) -> dict:
    """Merge the GUI WBG config into ``actor_cfg`` (GUI wins).

    When the GUI WBG is enabled, the C++ block is serialized via
    :func:`wbg_to_deploy_block`; an explicit GUI disable pops the block
    (removing the injected PRDP default).
    """
    merged = dict(actor_cfg)
    if gui_wbg is None or not gui_wbg.get("enabled", False):
        merged.pop("whole_body_guidance", None)
        return merged
    block = wbg_to_deploy_block(gui_wbg)
    if block is not None:
        merged["whole_body_guidance"] = block
    else:
        merged.pop("whole_body_guidance", None)
    return merged
