from __future__ import annotations

import torch
from typing import TYPE_CHECKING
from typing import Callable

import isaaclab.utils.math as math_utils

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv

from isaaclab.assets import Articulation, RigidObject
from isaaclab.managers import SceneEntityCfg
from isaaclab.envs.mdp.terminations import joint_pos_out_of_limit, joint_vel_out_of_limit, joint_vel_out_of_manual_limit

from rl_tracker.tasks.tracking.mdp import MotionCommand
from rl_tracker.tasks.tracking.mdp.rewards import _get_body_indexes

@torch.jit.script
def quat_apply_inverse(quat: torch.Tensor, vec: torch.Tensor) -> torch.Tensor:
    """Apply an inverse quaternion rotation to a vector.

    Args:
        quat: The quaternion in (w, x, y, z). Shape is (..., 4).
        vec: The vector in (x, y, z). Shape is (..., 3).

    Returns:
        The rotated vector in (x, y, z). Shape is (..., 3).
    """
    # store shape
    shape = vec.shape
    # reshape to (N, 3) for multiplication
    quat = quat.reshape(-1, 4)
    vec = vec.reshape(-1, 3)
    # extract components from quaternions
    xyz = quat[:, 1:]
    t = xyz.cross(vec, dim=-1) * 2
    return (vec - quat[:, 0:1] * t + xyz.cross(t, dim=-1)).view(shape)

def termination_cond_on_pfail(term_fn: Callable) -> Callable:
    def wrapper(env: ManagerBasedRLEnv, pfail_threshold: float, *args) -> torch.Tensor:
        termination = term_fn(env, *args)
        pfail_total = env.command_manager.get_term("motion").metrics["pfail_total"]
        termination = termination.logical_and(pfail_total < pfail_threshold)

        return termination

    return wrapper


def joint_pos_out_of_limit_cond_on_pfail(
    env: ManagerBasedRLEnv, pfail_threshold: float, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")
) -> torch.Tensor:
    return termination_cond_on_pfail(joint_pos_out_of_limit)(env, pfail_threshold, asset_cfg)


def joint_vel_out_of_limit_cond_on_pfail(
    env: ManagerBasedRLEnv, pfail_threshold: float, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")
) -> torch.Tensor:
    return termination_cond_on_pfail(joint_vel_out_of_limit)(env, pfail_threshold, asset_cfg)


def joint_vel_out_of_manual_limit_cond_on_pfail(
    env: ManagerBasedRLEnv,
    pfail_threshold: float,
    max_velocity: float,
    asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")
) -> torch.Tensor:
    return termination_cond_on_pfail(joint_vel_out_of_manual_limit)(env, pfail_threshold, max_velocity, asset_cfg)


###########################


def joint_effort_out_of_limit_fixed(
    env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")
) -> torch.Tensor:
    """Terminate when effort applied on the asset's joints are outside of the soft joint limits.

    In the actuators, the applied torque are the efforts applied on the joints. These are computed by clipping
    the computed torques to the joint limits. Hence, we check if the computed torques are equal to the applied
    torques.
    """
    # extract the used quantities (to enable type-hinting)
    asset: Articulation = env.scene[asset_cfg.name]
    # check if any joint effort is out of limit
    out_of_limits = torch.logical_not(
        torch.isclose(
            asset.data.computed_torque[:, asset_cfg.joint_ids], asset.data.applied_torque[:, asset_cfg.joint_ids]
        )
    )
    return torch.any(out_of_limits, dim=1)


def joint_effort_out_of_limit_fixed_cond_on_pfail(
    env: ManagerBasedRLEnv, pfail_threshold: float, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")
) -> torch.Tensor:
    return termination_cond_on_pfail(joint_effort_out_of_limit_fixed)(env, pfail_threshold, asset_cfg)


def bad_anchor_pos(env: ManagerBasedRLEnv, command_name: str, threshold: float) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)
    failed = torch.norm(command.anchor_pos_w - command.robot_anchor_pos_w, dim=1) > threshold
    return _record_only_or_terminate(command, "anchor_pos", _mask_command_reset_grace(command, failed))


def bad_anchor_pos_z_only(env: ManagerBasedRLEnv, command_name: str, threshold: float) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)
    failed = torch.abs(command.anchor_pos_w[:, -1] - command.robot_anchor_pos_w[:, -1]) > threshold
    return _record_only_or_terminate(command, "anchor_pos", _mask_command_reset_grace(command, failed))


def bad_anchor_ori(
    env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg, command_name: str, threshold: float
) -> torch.Tensor:
    asset: RigidObject | Articulation = env.scene[asset_cfg.name]

    command: MotionCommand = env.command_manager.get_term(command_name)
    motion_projected_gravity_b = quat_apply_inverse(command.anchor_quat_w, asset.data.GRAVITY_VEC_W)

    robot_projected_gravity_b = quat_apply_inverse(command.robot_anchor_quat_w, asset.data.GRAVITY_VEC_W)
    # GRAVITY_VEC_W: [0,0,-9.81]

    failed = (motion_projected_gravity_b[:, 2] - robot_projected_gravity_b[:, 2]).abs() > threshold
    return _record_only_or_terminate(command, "anchor_ori", _mask_command_reset_grace(command, failed))


def bad_motion_body_pos(
    env: ManagerBasedRLEnv, command_name: str, threshold: float, body_names: list[str] | None = None
) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)

    body_indexes = _get_body_indexes(command, body_names)
    error = torch.norm(command.body_pos_relative_w[:, body_indexes] - command.robot_body_pos_w[:, body_indexes], dim=-1)
    return _record_only_or_terminate(
        command, "ee_body_pos", _mask_command_reset_grace(command, torch.any(error > threshold, dim=-1))
    )


def bad_motion_body_pos_z_only(
    env: ManagerBasedRLEnv, command_name: str, threshold: float, body_names: list[str] | None = None
) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)

    body_indexes = _get_body_indexes(command, body_names)
    error = torch.abs(command.body_pos_relative_w[:, body_indexes, -1] - command.robot_body_pos_w[:, body_indexes, -1])
    # Preserve the exact values used by the termination manager before the
    # environment reset overwrites derived body state only when the bounded
    # Optional diagnostic explicitly enables it.
    if getattr(command, "diagnostic_capture_termination_diagnostics", False):
        command.diagnostic_last_ee_body_pos_z_error = error.detach().clone()
    return _record_only_or_terminate(
        command, "ee_body_pos", _mask_command_reset_grace(command, torch.any(error > threshold, dim=-1))
    )


def _record_only_or_terminate(command: MotionCommand, name: str, failed: torch.Tensor) -> torch.Tensor:
    """Record a BFM failure predicate without resetting its IsaacLab env."""
    if not getattr(command.cfg, "record_only_termination", False):
        return failed

    command.diagnostic_raw_termination_terms[name] = failed.detach().clone()
    counts = command.diagnostic_raw_termination_counts.get(name)
    if counts is None:
        counts = torch.zeros(command.num_envs, dtype=torch.long, device=failed.device)
        command.diagnostic_raw_termination_counts[name] = counts
    counts.add_(failed.to(dtype=torch.long))
    return torch.zeros_like(failed)


def _mask_command_reset_grace(command: MotionCommand, failed: torch.Tensor) -> torch.Tensor:
    """Ignore stale derived-body state for explicitly configured reset steps."""
    grace_steps = int(getattr(command.cfg, "termination_grace_steps", 0))
    if grace_steps <= 0 or not hasattr(command, "time_steps"):
        return failed
    return failed & (command.time_steps > grace_steps)


def motion_terminate(env: ManagerBasedRLEnv, command_name: str) -> torch.Tensor:
    # Terminate if at the end of the motion
    command = env.command_manager.get_term(command_name)
    reset_idx = command.motion_end_reset_env_idx.clone()
    command.motion_end_reset_env_idx = torch.zeros(env.num_envs, dtype=torch.bool, device=env.device)
    return reset_idx
