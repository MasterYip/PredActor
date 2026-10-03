"""State normalization helpers for G1 robot observations.

Public API
----------
build_g1_reflect_ops   — construct left/right reflection operators for a given
                         observation term layout
state_unnormalize      — convert body-position observations from local frame
                         back to global coordinates
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import torch

from diffusion_policy.utils.symm_utils import get_reflect_op, get_reflect_reps
from diffusion_policy.utils.traj_utils import (
    box_plus,
    get_euler_xyz,
    get_yaw_quat,
    quat_from_euler_xyz,
    quat_rotate,
)


def build_g1_reflect_ops(obs_terms: List[str], ee_idxs: np.ndarray, text_cond_dim: Optional[int] = None):
    """Construct left-right reflection operators for the given observation layout.

    Args:
        obs_terms:     Ordered list of term names (obs or task_condition terms).
        ee_idxs:       End-effector body indices.
        text_cond_dim: When provided, include an identity block of this size for
                       ``text_cond`` (CLIP embeddings) instead of skipping it.
                       Required when the term list mixes rlobs + text_cond so the
                       resulting op covers the full concatenated dimension.

    Returns (obs_reflect_op, action_reflect_op) as float64 tensors.
    """
    from diffusion_policy.dataset.g1_dataset import BODY_NAMES, JOINT_NAMES

    Q, Rd, Rd_pseudo, Q_Rd, Q_Rd_pseudo, num_bodies = get_reflect_reps(BODY_NAMES, JOINT_NAMES)

    # Map term name → reflection block
    _term_to_rep = {
        "body_pos_local":     Q_Rd,
        "body_lin_vel_local": Q_Rd,
        "root_pos_local":     Rd,
        "root_rot_local":     Rd_pseudo,
        "root_lin_vel_local": Rd,
        "root_ang_vel_local": Rd_pseudo,
        "joint_pos":          Q,
        "joint_vel":          Q,
        "projected_gravity":  Rd,
        "base_lin_vel":       Rd,
        "base_ang_vel":       Rd_pseudo,
        "last_actions":       Q,
        "text_cond":          None,  # CLIP embeddings: no reflection
        # Reference (task condition) variants — same physical quantities
        "ref_root_pos_local":     Rd,
        "ref_root_lin_vel_local": Rd,
        "ref_root_ang_vel_local": Rd_pseudo,
        "ref_joint_pos":          Q,
        "ref_joint_vel":          Q,
    }

    obs_reps = []
    for term in obs_terms:
        if term == "ee_rot_local":
            # Build ee-specific pseudo-vector reflection block
            Q_Rd_pseudo_4d = Q_Rd_pseudo.view(num_bodies, 3, num_bodies, 3)
            Q_Rd_pseudo_ee = Q_Rd_pseudo_4d[ee_idxs][:, :, ee_idxs]
            obs_reps.append(Q_Rd_pseudo_ee.reshape(len(ee_idxs) * 3, len(ee_idxs) * 3))
        elif term in _term_to_rep:
            rep = _term_to_rep[term]
            if rep is not None:
                obs_reps.append(rep)
            elif text_cond_dim is not None:
                # Include identity block for terms with no left-right symmetry (e.g. text_cond).
                # Required when the caller needs the reflect_op to span the full cond dimension.
                obs_reps.append(torch.eye(text_cond_dim, dtype=torch.float64))
            # else: skip (caller did not provide a dim, block omitted)
        # unknown terms: skip (user is responsible)

    if obs_reps:
        obs_reflect_op = get_reflect_op(obs_reps).to(torch.float64)
    else:
        obs_reflect_op = torch.eye(1, dtype=torch.float64)

    action_reflect_op = get_reflect_op([Q]).to(torch.float64)
    return obs_reflect_op, action_reflect_op


def state_unnormalize(state: torch.Tensor, global_root=None, return_rot: bool = False):
    """Unnormalize body positions from local to global coordinates.

    Expects *state* with standard G1 layout:
      [body_pos_local(90), body_lin_vel_local(90), root_pos(3), root_rot(3), ...]

    Args:
        state:       Tensor[B, H, D]
        global_root: Optional Tensor[B, H, 7] — global (pos + quat).
                     If None, assumes identity root pose.
        return_rot:  Unused; kept for API parity with old classes.

    Returns:
        body_pos: Tensor[B, H, J, 3] in global frame.
    """
    body_pos_local = state[:, :, 0:90]
    root_pos_frame = state[:, :, 180:183]
    root_rot_frame = state[:, :, 183:186]
    B, H = state.shape[:2]
    body_pos_local = body_pos_local.view(B, H, -1, 3)
    J = body_pos_local.shape[2]
    body_pos = body_pos_local.clone()

    if global_root is not None:
        root_pos_global = global_root[:, :, 0:3].to(body_pos.device)
        root_rot_global = global_root[:, :, 3:7].to(body_pos.device)
        root_rot_global = get_yaw_quat(root_rot_global)
    else:
        root_rot_global = torch.zeros((*body_pos_local.shape[:2], 4), device=body_pos_local.device)
        root_rot_global[..., 0] = 1

    root_rot_frame_q = box_plus(
        root_rot_global.flatten(0, 1),
        -root_rot_frame.flatten(0, 1),
    ).view(B, H, 4)
    roll, pitch, yaw = get_euler_xyz(root_rot_frame_q.view(-1, 4))
    yaw_quat = quat_from_euler_xyz(roll * 0, pitch * 0, yaw).reshape(B, H, 4)

    body_pos = quat_rotate(
        yaw_quat[:, :, None, :].expand(-1, -1, J, -1).flatten(0, 2),
        body_pos.flatten(0, 2),
    ).view(B, H, J, 3)
    body_pos[..., :2] += quat_rotate(
        root_rot_global[:, :, None, :].expand(-1, -1, J, -1).flatten(0, 2),
        root_pos_frame.flatten(0, 2),
    ).view(B, H, J, 3)[..., :2]
    if global_root is not None:
        body_pos[..., :2] += root_pos_global[:, :, None, :2]

    return body_pos
