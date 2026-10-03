"""Term registry and composer for G1 robot observation terms.

Public API
----------
TERM_DIMS       — static per-term output dimensions
TERM_REGISTRY   — dict mapping term name → compute function
register_term   — decorator to add a new term to the registry
NormContext     — pre-computed normalization quantities for one batch
TermComposer    — composes raw history dicts into policy-ready tensors
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np
import torch

from diffusion_policy.utils.traj_utils import (
    box_minus,
    get_euler_xyz,
    quat_from_euler_xyz,
    quat_rotate_inverse,
)

# Populated by g1_dataset at import time via a deferred import.
# Using a lambda avoids circular imports while still resolving correctly.
def _get_g1_constants():
    from diffusion_policy.dataset.g1_dataset import BODY_NAMES, JOINT_NAMES, DEFAULT_EE_IDXS
    return BODY_NAMES, JOINT_NAMES, DEFAULT_EE_IDXS


# ---------------------------------------------------------------------------
# Term dimensions (static, per term name)
# ---------------------------------------------------------------------------

# Mapping term name → output dimension (None = determined at runtime from data)
TERM_DIMS: Dict[str, Optional[int]] = {
    "body_pos_local":      None,   # len(BODY_NAMES) * 3 = 90, filled after constants load
    "body_lin_vel_local":  None,   # 90
    "root_pos_local":      3,
    "root_rot_local":      3,
    "root_lin_vel_local":  3,
    "root_ang_vel_local":  3,
    "ee_rot_local":        None,   # 2 * ee_count * 3, depends on ee_idxs
    "joint_pos":           None,   # len(JOINT_NAMES) = 29
    "joint_vel":           None,   # 29
    "projected_gravity":   3,
    "base_lin_vel":        3,
    "base_ang_vel":        3,
    "last_actions":        None,   # 29
    "text_cond":           None,   # CLIP embedding dim, varies
    # Reference motion terms (world-frame zarr keys → local-frame outputs)
    "ref_root_pos_local":     3,
    "ref_root_rot_local":     3,
    "ref_root_lin_vel_local": 3,
    "ref_root_ang_vel_local": 3,
    "ref_joint_pos":          None,   # 29, filled by _init_term_dims
    "ref_joint_vel":          None,   # 29, filled by _init_term_dims
}


def _init_term_dims():
    """Fill in TERM_DIMS values that depend on G1 skeleton constants."""
    BODY_NAMES, JOINT_NAMES, _ = _get_g1_constants()
    TERM_DIMS["body_pos_local"] = len(BODY_NAMES) * 3
    TERM_DIMS["body_lin_vel_local"] = len(BODY_NAMES) * 3
    TERM_DIMS["joint_pos"] = len(JOINT_NAMES)
    TERM_DIMS["joint_vel"] = len(JOINT_NAMES)
    TERM_DIMS["last_actions"] = len(JOINT_NAMES)
    TERM_DIMS["ref_joint_pos"] = len(JOINT_NAMES)
    TERM_DIMS["ref_joint_vel"] = len(JOINT_NAMES)


# ---------------------------------------------------------------------------
# NormContext — shared computation cache for one batch
# ---------------------------------------------------------------------------

@dataclass
class NormContext:
    """Pre-computed normalization quantities shared across term functions."""
    nominal_frame_idx: int
    ee_idxs: np.ndarray
    # Populated lazily by terms that need yaw-frame normalization
    yaw_quat: Optional[torch.Tensor] = None        # [B, H, 4]
    root_pos_init: Optional[torch.Tensor] = None   # [B, 3] at nominal frame

    @classmethod
    def from_raw(cls, raw: dict, nominal_frame_idx: int, ee_idxs: np.ndarray) -> "NormContext":
        ctx = cls(nominal_frame_idx=nominal_frame_idx, ee_idxs=ee_idxs)
        if "root_rot" in raw:
            ctx._compute_yaw_frame(raw["root_rot"].clone())
            ctx.root_pos_init = raw["root_pos"][:, nominal_frame_idx].clone() if "root_pos" in raw else None
        return ctx

    def _compute_yaw_frame(self, root_rot_frame: torch.Tensor):
        """Derive yaw-aligned quaternion for every (batch, step) pair."""
        B, H = root_rot_frame.shape[:2]
        q = root_rot_frame.float().reshape(-1, 4)
        roll, pitch, yaw = get_euler_xyz(q)
        self.yaw_quat = quat_from_euler_xyz(roll * 0, pitch * 0, yaw).reshape(B, H, 4)

    def ensure_yaw(self, raw: dict):
        if self.yaw_quat is None and "root_rot" in raw:
            self._compute_yaw_frame(raw["root_rot"].clone())


# ---------------------------------------------------------------------------
# Term Registry
# ---------------------------------------------------------------------------

TERM_REGISTRY: Dict[str, Callable] = {}

# Maps term name → raw dict keys that the term function reads.
# Used by compose_cond to surface a clear error when a required key is absent.
_TERM_REQUIRED_KEYS: Dict[str, list] = {
    "joint_pos":           ["joint_pos"],
    "joint_vel":           ["joint_vel"],
    "projected_gravity":   ["projected_gravity"],
    "base_lin_vel":        ["base_lin_vel"],
    "base_ang_vel":        ["base_ang_vel"],
    "last_actions":        ["last_actions"],
    "text_cond":           ["motion_latent"],
    "body_pos_local":      ["body_pos", "root_pos", "root_rot"],
    "body_lin_vel_local":  ["body_lin_vel", "root_pos", "root_rot"],
    "root_pos_local":      ["root_pos", "root_rot"],
    "root_rot_local":      ["root_rot"],
    "root_lin_vel_local":  ["body_lin_vel", "root_rot"],
    "root_ang_vel_local":  ["body_ang_vel", "root_rot"],
    "ee_rot_local":        ["body_rot", "root_rot"],
    # Reference motion terms
    "ref_root_pos_local":     ["motion_ref_root_pos", "root_pos", "root_rot"],
    "ref_root_rot_local":     ["motion_ref_root_rot", "root_rot"],
    "ref_root_lin_vel_local": ["motion_ref_root_lin_vel", "root_rot"],
    "ref_root_ang_vel_local": ["motion_ref_root_ang_vel", "root_rot"],
    "ref_joint_pos":          ["motion_ref_joint_pos"],
    "ref_joint_vel":          ["motion_ref_joint_vel"],
}


def register_term(name: str):
    """Decorator to register a term-compute function under *name*."""
    def decorator(fn: Callable) -> Callable:
        TERM_REGISTRY[name] = fn
        return fn
    return decorator


# --- Pass-through terms (already in local/sensor frame) ---

@register_term("joint_pos")
def _term_joint_pos(raw: dict, ctx: NormContext) -> torch.Tensor:
    return raw["joint_pos"].clone().float()


@register_term("joint_vel")
def _term_joint_vel(raw: dict, ctx: NormContext) -> torch.Tensor:
    return raw["joint_vel"].clone().float()


@register_term("projected_gravity")
def _term_projected_gravity(raw: dict, ctx: NormContext) -> torch.Tensor:
    return raw["projected_gravity"].clone().float()


@register_term("base_lin_vel")
def _term_base_lin_vel(raw: dict, ctx: NormContext) -> torch.Tensor:
    return raw["base_lin_vel"].clone().float()


@register_term("base_ang_vel")
def _term_base_ang_vel(raw: dict, ctx: NormContext) -> torch.Tensor:
    return raw["base_ang_vel"].clone().float()


@register_term("last_actions")
def _term_last_actions(raw: dict, ctx: NormContext) -> torch.Tensor:
    return raw["last_actions"].clone().float()


@register_term("text_cond")
def _term_text_cond(raw: dict, ctx: NormContext) -> torch.Tensor:
    return raw["motion_latent"].clone().float()


# --- Yaw-frame normalized terms ---

@register_term("body_pos_local")
def _term_body_pos_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Body positions relative to root, rotated to yaw frame. [B, H, J*3]"""
    ctx.ensure_yaw(raw)
    body_pos = raw["body_pos"].clone().float()
    root_pos = raw["root_pos"].clone().float()
    B, H = root_pos.shape[:2]
    body_pos = body_pos.view(B, H, -1, 3)
    J = body_pos.shape[2]
    yaw_quat = ctx.yaw_quat  # [B, H, 4]

    # Remove root XY translation
    body_pos[:, :, :, :2] -= root_pos[:, :, None, :2]

    # Rotate to yaw frame
    body_pos_local = quat_rotate_inverse(
        yaw_quat[:, :, None, :].expand(-1, -1, J, -1).reshape(-1, 4),
        body_pos.reshape(-1, 3),
    ).reshape(B, H, J, 3)

    return body_pos_local.reshape(B, H, J * 3)


@register_term("body_lin_vel_local")
def _term_body_lin_vel_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Body linear velocities minus root velocity, rotated to yaw frame. [B, H, J*3]"""
    ctx.ensure_yaw(raw)
    body_lin_vel = raw["body_lin_vel"].clone().float()
    root_pos = raw["root_pos"].clone().float()
    B, H = root_pos.shape[:2]
    body_lin_vel = body_lin_vel.view(B, H, -1, 3)
    J = body_lin_vel.shape[2]
    yaw_quat = ctx.yaw_quat

    # Subtract root (pelvis) linear velocity
    root_lin_vel = body_lin_vel[:, :, 0:1, :].clone()
    body_lin_vel_local = body_lin_vel - root_lin_vel

    body_lin_vel_local = quat_rotate_inverse(
        yaw_quat[:, :, None, :].expand(-1, -1, J, -1).reshape(-1, 4),
        body_lin_vel_local.reshape(-1, 3),
    ).reshape(B, H, J, 3)

    return body_lin_vel_local.reshape(B, H, J * 3)


@register_term("root_pos_local")
def _term_root_pos_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Root position relative to nominal frame, rotated to yaw frame. [B, H, 3]"""
    ctx.ensure_yaw(raw)
    root_pos = raw["root_pos"].clone().float()
    B, H = root_pos.shape[:2]
    nom = ctx.nominal_frame_idx
    yaw_quat = ctx.yaw_quat

    root_pos_local = root_pos
    root_pos_local[:, :, :2] -= root_pos[:, nom:nom+1, :2].clone()

    root_pos_local = quat_rotate_inverse(
        yaw_quat[:, nom:nom+1, :].expand(-1, H, -1).reshape(-1, 4),
        root_pos_local.reshape(-1, 3),
    ).reshape(B, H, 3)

    return root_pos_local


@register_term("root_rot_local")
def _term_root_rot_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Root rotation relative to nominal yaw, as rotation vector. [B, H, 3]"""
    ctx.ensure_yaw(raw)
    root_rot = raw["root_rot"].clone().float()
    B, H = root_rot.shape[:2]
    nom = ctx.nominal_frame_idx
    yaw_quat = ctx.yaw_quat

    root_rot_local = box_minus(
        root_rot.reshape(-1, 4),
        yaw_quat[:, nom:nom+1, :].expand(-1, H, -1).reshape(-1, 4),
    ).reshape(B, H, 3)

    return root_rot_local


@register_term("root_lin_vel_local")
def _term_root_lin_vel_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Root (pelvis) linear velocity rotated to nominal yaw frame. [B, H, 3]"""
    ctx.ensure_yaw(raw)
    body_lin_vel = raw["body_lin_vel"].clone().float()
    B, H = body_lin_vel.shape[:2]
    nom = ctx.nominal_frame_idx
    yaw_quat = ctx.yaw_quat

    root_lin_vel = body_lin_vel.view(B, H, -1, 3)[:, :, 0, :]  # [B, H, 3]

    root_lin_vel_local = quat_rotate_inverse(
        yaw_quat[:, nom:nom+1, :].expand(-1, H, -1).reshape(-1, 4),
        root_lin_vel.reshape(-1, 3),
    ).reshape(B, H, 3)

    return root_lin_vel_local


@register_term("root_ang_vel_local")
def _term_root_ang_vel_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Root (pelvis) angular velocity rotated to nominal yaw frame. [B, H, 3]"""
    ctx.ensure_yaw(raw)
    body_ang_vel = raw["body_ang_vel"].clone().float()
    B, H = body_ang_vel.shape[:2]
    nom = ctx.nominal_frame_idx
    yaw_quat = ctx.yaw_quat

    root_ang_vel = body_ang_vel.view(B, H, -1, 3)[:, :, 0, :]  # [B, H, 3]

    root_ang_vel_local = quat_rotate_inverse(
        yaw_quat[:, nom:nom+1, :].expand(-1, H, -1).reshape(-1, 4),
        root_ang_vel.reshape(-1, 3),
    ).reshape(B, H, 3)

    return root_ang_vel_local


@register_term("ee_rot_local")
def _term_ee_rot_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """End-effector rotation vectors in yaw frame. [B, H, n_ee*3]"""
    ctx.ensure_yaw(raw)
    body_rot = raw["body_rot"].clone().float()
    B, H = body_rot.shape[:2]
    yaw_quat = ctx.yaw_quat

    body_rot_4d = body_rot.view(B, H, -1, 4)
    J = body_rot_4d.shape[2]

    body_rot_local = box_minus(
        body_rot_4d.reshape(-1, 4),
        yaw_quat[:, :, None, :].expand(-1, -1, J, -1).reshape(-1, 4),
    ).reshape(B, H, J, 3)

    ee_rot = body_rot_local[:, :, ctx.ee_idxs, :]  # [B, H, n_ee, 3]
    return ee_rot.reshape(B, H, -1)


# ---------------------------------------------------------------------------
# Reference motion terms (world-frame zarr keys → character-local outputs)
# ---------------------------------------------------------------------------

@register_term("ref_root_pos_local")
def _term_ref_root_pos_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Reference root position relative to nominal frame, in yaw frame. [B, H, 3]"""
    ctx.ensure_yaw(raw)
    ref_pos = raw["motion_ref_root_pos"].clone().float()   # [B, H, 3] world-frame
    robot_pos = raw["root_pos"].clone().float()             # [B, H, 3] world-frame
    B, H = ref_pos.shape[:2]
    nom = ctx.nominal_frame_idx

    # Subtract robot nominal XY (same reference point as root_pos_local)
    ref_pos[:, :, :2] -= robot_pos[:, nom:nom+1, :2].clone()

    ref_pos_local = quat_rotate_inverse(
        ctx.yaw_quat[:, nom:nom+1, :].expand(-1, H, -1).reshape(-1, 4),
        ref_pos.reshape(-1, 3),
    ).reshape(B, H, 3)
    return ref_pos_local


@register_term("ref_root_rot_local")
def _term_ref_root_rot_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Reference root rotation relative to nominal yaw, as rotation vector. [B, H, 3]"""
    ctx.ensure_yaw(raw)
    ref_rot = raw["motion_ref_root_rot"].clone().float()   # [B, H, 4]
    B, H = ref_rot.shape[:2]
    nom = ctx.nominal_frame_idx

    ref_rot_local = box_minus(
        ref_rot.reshape(-1, 4),
        ctx.yaw_quat[:, nom:nom+1, :].expand(-1, H, -1).reshape(-1, 4),
    ).reshape(B, H, 3)
    return ref_rot_local


@register_term("ref_root_lin_vel_local")
def _term_ref_root_lin_vel_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Reference root linear velocity rotated to nominal yaw frame. [B, H, 3]"""
    ctx.ensure_yaw(raw)
    ref_vel = raw["motion_ref_root_lin_vel"].clone().float()  # [B, H, 3]
    B, H = ref_vel.shape[:2]
    nom = ctx.nominal_frame_idx

    ref_vel_local = quat_rotate_inverse(
        ctx.yaw_quat[:, nom:nom+1, :].expand(-1, H, -1).reshape(-1, 4),
        ref_vel.reshape(-1, 3),
    ).reshape(B, H, 3)
    return ref_vel_local


@register_term("ref_root_ang_vel_local")
def _term_ref_root_ang_vel_local(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Reference root angular velocity rotated to nominal yaw frame. [B, H, 3]"""
    ctx.ensure_yaw(raw)
    ref_ang_vel = raw["motion_ref_root_ang_vel"].clone().float()  # [B, H, 3]
    B, H = ref_ang_vel.shape[:2]
    nom = ctx.nominal_frame_idx

    ref_ang_vel_local = quat_rotate_inverse(
        ctx.yaw_quat[:, nom:nom+1, :].expand(-1, H, -1).reshape(-1, 4),
        ref_ang_vel.reshape(-1, 3),
    ).reshape(B, H, 3)
    return ref_ang_vel_local


@register_term("ref_joint_pos")
def _term_ref_joint_pos(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Reference joint positions (pass-through). [B, H, 29]"""
    return raw["motion_ref_joint_pos"].clone().float()


@register_term("ref_joint_vel")
def _term_ref_joint_vel(raw: dict, ctx: NormContext) -> torch.Tensor:
    """Reference joint velocities (pass-through). [B, H, 29]"""
    return raw["motion_ref_joint_vel"].clone().float()


# ---------------------------------------------------------------------------
# TermComposer
# ---------------------------------------------------------------------------

class TermComposer:
    """Composes raw observation history into policy-ready tensors.

    This is the runner-side counterpart of the dataset's collate_fn.  Both
    share the same TERM_REGISTRY functions, so the normalization is identical
    during training and deployment.
    """

    def __init__(self, profile, n_obs_steps: int, ee_idxs: np.ndarray = None, text_cond_dim: int = 512, n_task_steps: int = 1):
        if ee_idxs is None:
            _, _, ee_idxs = _get_g1_constants()
        self.profile = profile
        self.n_obs_steps = n_obs_steps
        self.n_task_steps = n_task_steps
        self.nominal_frame_idx = n_obs_steps - 1
        self.ee_idxs = ee_idxs
        self._text_cond_dim = text_cond_dim  # CLIP / MotionCLIP embedding dim (varies per model)

        # Ensure TERM_DIMS is initialised with correct G1 constants.
        if TERM_DIMS["joint_pos"] is None:
            _init_term_dims()

        # Pre-validate that all requested terms are registered
        for term in profile.observation.terms + profile.task_condition.terms:
            if term not in TERM_REGISTRY:
                raise ValueError(
                    f"Term '{term}' is not registered in TERM_REGISTRY. "
                    f"Available: {sorted(TERM_REGISTRY.keys())}"
                )

    # ------------------------------------------------------------------
    # Observation composition
    # ------------------------------------------------------------------

    def compose_obs(self, raw: dict) -> torch.Tensor:
        """Compute and concatenate all observation terms.

        Args:
            raw: dict mapping raw key → Tensor[B, H, ...].

        Returns:
            Tensor[B, H, D_obs]  (D_obs = 0 if terms is null/empty → zeros fallback in actor)
        """
        terms = self.profile.observation.terms or []
        if not terms:
            # No observation terms — return a 0-dim placeholder so the pipeline stays valid.
            # CondCoDiffuseActor._build_x will substitute real zeros of the correct x_input_dim.
            sample = next(iter(raw.values()))
            B, H = sample.shape[:2]
            return torch.zeros(B, H, 0, device=sample.device if hasattr(sample, 'device') else None)
        ctx = NormContext.from_raw(raw, self.nominal_frame_idx, self.ee_idxs)
        parts = []
        for term in terms:
            parts.append(TERM_REGISTRY[term](raw, ctx))
        return torch.cat(parts, dim=-1)

    # Alias used by runners that previously called obs_composer.compose()
    def compose(self, raw: dict) -> torch.Tensor:
        return self.compose_obs(raw)

    # ------------------------------------------------------------------
    # Conditioning composition (task conditions, e.g. CLIP embeddings)
    # ------------------------------------------------------------------

    def compose_cond(self, raw: dict) -> torch.Tensor:
        """Compute and concatenate all task_condition terms.

        All required terms must already be present in *raw* — callers are
        responsible for injecting externally-sourced terms (e.g. CLIP
        embeddings) before calling this method.  A missing term raises
        ``KeyError`` immediately so the error is easy to diagnose.

        Args:
            raw: dict mapping key → Tensor[B, H, ...].  Must contain every
                key referenced by the task_condition terms in the profile.

        Returns:
            Tensor[B, n_task_steps, D_cond]
        """
        # Validate that all required source keys are present.
        # If the term's output key already exists in raw (pre-computed/injected),
        # skip the source-key check for that term entirely.
        for term in self.profile.task_condition.terms:
            if term in raw:
                continue  # already pre-computed; no need to validate source keys
            required = _TERM_REQUIRED_KEYS.get(term)
            if required is not None:
                for key in required:
                    if key not in raw:
                        raise KeyError(
                            f"Task condition term '{term}' requires raw key '{key}', "
                            f"but it is not present. "
                            f"Inject it via _attach_task_condition before composing."
                        )

        ctx = NormContext.from_raw(raw, self.nominal_frame_idx, self.ee_idxs)
        parts = []
        # Generalized horizon alignment: a condition may span the full
        # model horizon (one cond token per horizon row, e.g. the per-row dyed
        # motion_latent), not only the n_obs_steps history prefix.
        raw_horizons = {
            int(torch.as_tensor(value).shape[1])
            for value in raw.values()
            if torch.as_tensor(value).ndim >= 2
        }
        if len(raw_horizons) != 1:
            raise ValueError(
                f"task condition raw fields have inconsistent horizons: {raw_horizons}"
            )
        raw_horizon = raw_horizons.pop()
        if self.n_task_steps <= self.n_obs_steps:
            if raw_horizon < self.n_obs_steps:
                raise ValueError(
                    f"task condition requires {self.n_obs_steps} history rows, "
                    f"got {raw_horizon}"
                )
            cond_slice = slice(
                self.n_obs_steps - self.n_task_steps, self.n_obs_steps
            )
        else:
            if raw_horizon < self.n_task_steps:
                raise ValueError(
                    f"aligned task condition requires {self.n_task_steps} rows, "
                    f"got {raw_horizon}"
                )
            cond_slice = slice(0, self.n_task_steps)
        for term in self.profile.task_condition.terms:
            if term in raw:
                # Use pre-computed value directly; skip calling the term function.
                t = raw[term]  # [B, H, D]
            else:
                t = TERM_REGISTRY[term](raw, ctx)  # [B, H, D]
            selected = t[:, cond_slice, :]
            if selected.shape[1] != self.n_task_steps:
                raise ValueError(
                    f"task condition term {term!r} produced "
                    f"{selected.shape[1]} rows, expected {self.n_task_steps}"
                )
            parts.append(selected)

        if not parts:
            return torch.zeros(0)

        return torch.cat(parts, dim=-1)

    # ------------------------------------------------------------------
    # History management (used by runners)
    # ------------------------------------------------------------------

    @staticmethod
    def init_history(terms: dict, n_obs_steps: int) -> dict:
        """Repeat one-step terms into an initial temporal history.

        Args:
            terms: dict with values of shape [B, 1, ...].
            n_obs_steps: number of history steps to create.

        Returns:
            dict with values of shape [B, n_obs_steps, ...].
        """
        history = {}
        for key, value in terms.items():
            if value.dim() < 2:
                raise ValueError(f"Expected at least [B, T, ...] for term '{key}'")
            if value.shape[1] != 1:
                raise ValueError(
                    f"init_history expects T=1 terms, but '{key}' has T={value.shape[1]}"
                )
            repeat_shape = [1, n_obs_steps] + [1] * (value.dim() - 2)
            history[key] = value.repeat(*repeat_shape)
        return history

    @staticmethod
    def shift_append(history: dict, latest_terms: dict) -> dict:
        """Shift temporal history left and append latest one-step terms."""
        out = {}
        for key, hist in history.items():
            new_val = latest_terms[key]
            out[key] = torch.cat([hist[:, 1:], new_val], dim=1)
        return out

    # ------------------------------------------------------------------
    # Dimension introspection
    # ------------------------------------------------------------------

    def _dim_of(self, term: str) -> int:
        if TERM_DIMS["joint_pos"] is None:
            _init_term_dims()
        d = TERM_DIMS.get(term)
        if d is not None:
            return d
        if term == "ee_rot_local":
            return len(self.ee_idxs) * 3
        if term == "text_cond":
            return self._text_cond_dim
        raise ValueError(f"Cannot statically determine dimension for term '{term}'")

    @property
    def obs_dim(self) -> int:
        terms = self.profile.observation.terms or []
        return sum(self._dim_of(t) for t in terms)

    @property
    def cond_dim(self) -> int:
        if not self.profile.task_condition.terms:
            return 0
        return sum(self._dim_of(t) for t in self.profile.task_condition.terms)

    @property
    def cond_term_boundaries(self):
        """[(term_name, start_dim, end_dim), ...] for task_condition terms.

        Used by TaskMaskGenerator to locate each term's slice in the condition
        vector so it can apply per-term masking.
        """
        boundaries = []
        offset = 0
        for term in self.profile.task_condition.terms:
            d = self._dim_of(term)
            boundaries.append((term, offset, offset + d))
            offset += d
        return boundaries

    @property
    def use_task_interface(self) -> bool:
        return bool(self.profile.task_condition.terms)

    # Keep the profile name accessible for legacy checks
    @property
    def profile_name(self) -> str:
        return self.profile.name
