from __future__ import annotations

import torch
from typing import TYPE_CHECKING

from isaaclab.utils.math import matrix_from_quat, subtract_frame_transforms

from rl_tracker.tasks.tracking.mdp import MotionCommand
from isaaclab.envs.mdp.observations import SceneEntityCfg
from isaaclab.envs.mdp.observations import Articulation

# Import trajectory utilities from diffuse_cloc for state normalization
from diffusion_policy.utils.traj_utils import (
    quat_from_euler_xyz, get_euler_xyz, quat_mul, quat_rotate,
    box_minus, quat_rotate_inverse, box_plus, get_yaw_quat,
)

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedEnv


def joint_vel_rel_no_ankle(env: ManagerBasedEnv, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")):
    """The joint velocities of the asset w.r.t. the default joint velocities.

    Note: Only the joints configured in :attr:`asset_cfg.joint_ids` will have their velocities returned.
    """
    # extract the used quantities (to enable type-hinting)
    asset: Articulation = env.scene[asset_cfg.name]
    joint_vel_rel = asset.data.joint_vel[:, :] - asset.data.default_joint_vel[:, :]
    # ankle_id  = asset_cfg.joint_ids
    print(joint_vel_rel[:, asset_cfg.joint_ids].norm(dim=-1).mean())
    # breakpoint()
    joint_vel_rel[:, asset_cfg.joint_ids] = 0
    return joint_vel_rel


def robot_anchor_ori_w(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)
    mat = matrix_from_quat(command.robot_anchor_quat_w)
    return mat[..., :2].reshape(mat.shape[0], -1)


def robot_anchor_lin_vel_w(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)

    return command.robot_anchor_vel_w[:, :3].view(env.num_envs, -1)


def robot_anchor_ang_vel_w(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)

    return command.robot_anchor_vel_w[:, 3:6].view(env.num_envs, -1)


def robot_body_pos_b(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)

    num_bodies = len(command.cfg.body_names)
    pos_b, _ = subtract_frame_transforms(
        command.robot_anchor_pos_w[:, None, :].repeat(1, num_bodies, 1),
        command.robot_anchor_quat_w[:, None, :].repeat(1, num_bodies, 1),
        command.robot_body_pos_w,
        command.robot_body_quat_w,
    )

    return pos_b.view(env.num_envs, -1)


def robot_body_ori_b(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)

    num_bodies = len(command.cfg.body_names)
    _, ori_b = subtract_frame_transforms(
        command.robot_anchor_pos_w[:, None, :].repeat(1, num_bodies, 1),
        command.robot_anchor_quat_w[:, None, :].repeat(1, num_bodies, 1),
        command.robot_body_pos_w,
        command.robot_body_quat_w,
    )
    mat = matrix_from_quat(ori_b)
    return mat[..., :2].reshape(mat.shape[0], -1)


def motion_anchor_pos_b(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)

    pos, _ = subtract_frame_transforms(
        command.robot_anchor_pos_w,
        command.robot_anchor_quat_w,
        command.anchor_pos_w,
        command.anchor_quat_w,
    )

    return pos.view(env.num_envs, -1)


def motion_anchor_ori_b(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    command: MotionCommand = env.command_manager.get_term(command_name)

    _, ori = subtract_frame_transforms(
        command.robot_anchor_pos_w,
        command.robot_anchor_quat_w,
        command.anchor_pos_w,
        command.anchor_quat_w,
    )
    mat = matrix_from_quat(ori)
    return mat[..., :2].reshape(mat.shape[0], -1)


def motion_anchor_pos_b_future(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    """Future N-step motion anchor position in body frame, flattened to vector."""
    command: MotionCommand = env.command_manager.get_term(command_name)

    # Reshape future data: (num_envs, future_steps, 3) and (num_envs, future_steps, 4)
    future_anchor_pos_w = command.motion_anchor_pos.view(env.num_envs, -1, 3)
    future_anchor_quat_w = command.motion_anchor_quat.view(env.num_envs, -1, 4)

    # Expand robot anchor for broadcasting: (num_envs, future_steps, 3) and (num_envs, future_steps, 4)
    robot_anchor_pos_w_exp = command.robot_anchor_pos_w[:, None, :].expand(-1, future_anchor_pos_w.shape[1], -1)
    robot_anchor_quat_w_exp = command.robot_anchor_quat_w[:, None, :].expand(-1, future_anchor_quat_w.shape[1], -1)

    # Transform all future steps at once
    pos_b, _ = subtract_frame_transforms(
        robot_anchor_pos_w_exp,
        robot_anchor_quat_w_exp,
        future_anchor_pos_w,
        future_anchor_quat_w,
    )
    return pos_b.view(env.num_envs, -1)


def motion_anchor_ori_b_future(env: ManagerBasedEnv, command_name: str) -> torch.Tensor:
    """Future N-step motion anchor orientation in body frame, flattened to vector."""
    command: MotionCommand = env.command_manager.get_term(command_name)

    # Reshape future data: (num_envs, future_steps, 3) and (num_envs, future_steps, 4)
    future_anchor_pos_w = command.motion_anchor_pos.view(env.num_envs, -1, 3)
    future_anchor_quat_w = command.motion_anchor_quat.view(env.num_envs, -1, 4)

    # Expand robot anchor for broadcasting: (num_envs, future_steps, 3) and (num_envs, future_steps, 4)
    robot_anchor_pos_w_exp = command.robot_anchor_pos_w[:, None, :].expand(-1, future_anchor_pos_w.shape[1], -1)
    robot_anchor_quat_w_exp = command.robot_anchor_quat_w[:, None, :].expand(-1, future_anchor_quat_w.shape[1], -1)

    # Transform all future steps at once
    pos_b, ori_b = subtract_frame_transforms(
        robot_anchor_pos_w_exp,
        robot_anchor_quat_w_exp,
        future_anchor_pos_w,
        future_anchor_quat_w,
    )

    mat = matrix_from_quat(ori_b)
    return mat[..., :2].reshape(mat.shape[0], -1)


def extract_robot_state(env: ManagerBasedEnv, command_name: str = "motion") -> dict:
    """
    Extract raw robot state data from the environment.
    
    This function provides the raw data in the same format used during data collection.
    Returns dictionary with keys matching OfflineDataset requirements:
        - body_pos: [num_envs, 30, 3]
        - body_rot: [num_envs, 30, 4] 
        - body_lin_vel: [num_envs, 30, 3]
        - body_ang_vel: [num_envs, 30, 3]
        - joint_pos: [num_envs, 29]
        - joint_vel: [num_envs, 29]
        - root_pos: [num_envs, 3]
        - root_rot: [num_envs, 4]
        - motion_idx: [num_envs] (scalar per env, indicates which motion file)
    
    Args:
        env: The environment instance
        command_name: Name of the motion command term (default: "motion")
    """
    robot = env.scene["robot"]
    
    # Get body data for all bodies (30 bodies for G1)
    # robot.data.body_pos_w and body_quat_w include all bodies
    body_pos_w = robot.data.body_pos_w.clone()  # [num_envs, num_bodies, 3]
    body_quat_w = robot.data.body_quat_w.clone()  # [num_envs, num_bodies, 4]
    body_lin_vel_w = robot.data.body_lin_vel_w.clone()  # [num_envs, num_bodies, 3]
    body_ang_vel_w = robot.data.body_ang_vel_w.clone()  # [num_envs, num_bodies, 3]
    
    # Remove environment origins to get world-frame positions
    env_origins = env.scene.env_origins  # [num_envs, 3]
    body_pos_w = body_pos_w - env_origins[:, None, :]
    
    # Get joint data (29 joints for G1)
    joint_pos = robot.data.joint_pos.clone()  # [num_envs, 29]
    joint_vel = robot.data.joint_vel.clone()  # [num_envs, 29]
    
    # Get root (pelvis) data - root is the first body (index 0)
    root_pos = body_pos_w[:, 0, :]  # [num_envs, 3]
    root_rot = body_quat_w[:, 0, :]  # [num_envs, 4]
    
    # Get motion_idx from motion command (for tracking which motion file)
    try:
        motion_command = env.command_manager.get_term(command_name)
        motion_idx = motion_command.motion_idx.clone()  # [num_envs]
    except (AttributeError, KeyError):
        # Fallback if command doesn't have motion_idx (e.g., non-collection mode)
        motion_idx = torch.zeros(env.num_envs, dtype=torch.long, device=robot.device)
    
    return {
        "body_pos": body_pos_w,  # [num_envs, 30, 3]
        "body_rot": body_quat_w,  # [num_envs, 30, 4]
        "body_lin_vel": body_lin_vel_w,  # [num_envs, 30, 3]
        "body_ang_vel": body_ang_vel_w,  # [num_envs, 30, 3]
        "joint_pos": joint_pos,  # [num_envs, 29]
        "joint_vel": joint_vel,  # [num_envs, 29]
        "root_pos": root_pos,  # [num_envs, 3]
        "root_rot": root_rot,  # [num_envs, 4]
        "motion_idx": motion_idx,  # [num_envs] - which motion file (for data collection)
    }


def robot_body_pos_all(env: ManagerBasedEnv) -> torch.Tensor:
    """Extract all body positions [num_envs, 30, 3] for data collection with noise."""
    robot = env.scene["robot"]
    body_pos_w = robot.data.body_pos_w.clone()
    env_origins = env.scene.env_origins
    body_pos_w = body_pos_w - env_origins[:, None, :]
    return body_pos_w.view(env.num_envs, -1)  # [num_envs, 90]


def robot_body_rot_all(env: ManagerBasedEnv) -> torch.Tensor:
    """Extract all body rotations [num_envs, 30, 4] for data collection with noise."""
    robot = env.scene["robot"]
    body_quat_w = robot.data.body_quat_w.clone()
    return body_quat_w.view(env.num_envs, -1)  # [num_envs, 120]


def robot_body_lin_vel_all(env: ManagerBasedEnv) -> torch.Tensor:
    """Extract all body linear velocities [num_envs, 30, 3] for data collection with noise."""
    robot = env.scene["robot"]
    body_lin_vel_w = robot.data.body_lin_vel_w.clone()
    return body_lin_vel_w.view(env.num_envs, -1)  # [num_envs, 90]


def robot_body_ang_vel_all(env: ManagerBasedEnv) -> torch.Tensor:
    """Extract all body angular velocities [num_envs, 30, 3] for data collection with noise."""
    robot = env.scene["robot"]
    body_ang_vel_w = robot.data.body_ang_vel_w.clone()
    return body_ang_vel_w.view(env.num_envs, -1)  # [num_envs, 90]


def robot_joint_pos_all(env: ManagerBasedEnv) -> torch.Tensor:
    """Extract all joint positions [num_envs, 29] for data collection with noise."""
    robot = env.scene["robot"]
    joint_pos = robot.data.joint_pos.clone()
    return joint_pos  # [num_envs, 29]


def robot_joint_vel_all(env: ManagerBasedEnv) -> torch.Tensor:
    """Extract all joint velocities [num_envs, 29] for data collection with noise."""
    robot = env.scene["robot"]
    joint_vel = robot.data.joint_vel.clone()
    return joint_vel  # [num_envs, 29]


def robot_root_pos(env: ManagerBasedEnv) -> torch.Tensor:
    """Extract root position [num_envs, 3] for data collection with noise."""
    robot = env.scene["robot"]
    body_pos_w = robot.data.body_pos_w[:, 0, :].clone()
    env_origins = env.scene.env_origins
    root_pos = body_pos_w - env_origins
    return root_pos  # [num_envs, 3]


def robot_root_rot(env: ManagerBasedEnv) -> torch.Tensor:
    """Extract root rotation [num_envs, 4] for data collection with noise."""
    robot = env.scene["robot"]
    root_rot = robot.data.body_quat_w[:, 0, :].clone()
    return root_rot  # [num_envs, 4]


def robot_motion_idx(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Extract motion index [num_envs, 1] for data collection."""
    try:
        motion_command = env.command_manager.get_term(command_name)
        motion_idx = motion_command.motion_idx.clone().float()  # Convert to float for consistency
    except (AttributeError, KeyError):
        motion_idx = torch.zeros(env.num_envs, dtype=torch.float32, device=env.device)
    return motion_idx.unsqueeze(-1)  # [num_envs, 1] for concatenation


def diffusion_state_observation(env: ManagerBasedEnv) -> torch.Tensor:
    """
    Extract raw robot state data for diffusion policy.
    
    Returns concatenated raw state matching data collection format.
    History management and normalization should be done by the runner.
    
    Returns:
        Raw state tensor [num_envs, state_dim] where state_dim includes:
        - body_pos: [num_envs, 90] (30 bodies × 3)
        - body_rot: [num_envs, 120] (30 bodies × 4)
        - body_lin_vel: [num_envs, 90] (30 bodies × 3)
        - body_ang_vel: [num_envs, 90] (30 bodies × 3)
        - joint_pos: [num_envs, 29]
        - joint_vel: [num_envs, 29]
        - root_pos: [num_envs, 3]
        - root_rot: [num_envs, 4]
        
        Total: 90 + 120 + 90 + 90 + 29 + 29 + 3 + 4 = 455 dimensions
    """
    # Extract raw robot state (same as data collection)
    robot_state = extract_robot_state(env)
    
    # Concatenate all state components into a single tensor
    # This matches the format used during data collection
    state_tensor = torch.cat([
        robot_state["body_pos"].flatten(1),      # [B, 30*3] = [B, 90]
        robot_state["body_rot"].flatten(1),      # [B, 30*4] = [B, 120]
        robot_state["body_lin_vel"].flatten(1),  # [B, 30*3] = [B, 90]
        robot_state["body_ang_vel"].flatten(1),  # [B, 30*3] = [B, 90]
        robot_state["joint_pos"],                # [B, 29]
        robot_state["joint_vel"],                # [B, 29]
        robot_state["root_pos"],                 # [B, 3]
        robot_state["root_rot"],                 # [B, 4]
    ], dim=-1)  # [B, 455]

    return state_tensor


def motion_ref_root_pos(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference (target) pelvis/root position in world frame, relative to env origin. [num_envs, 3]"""
    command: MotionCommand = env.command_manager.get_term(command_name)
    # anchor_pos_w already adds env_origins; subtract to get env-local position
    pos = command.anchor_pos_w - env.scene.env_origins
    return pos  # [num_envs, 3]


def motion_ref_root_rot(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference (target) root/pelvis quaternion (w,x,y,z) in world frame. [num_envs, 4]"""
    command: MotionCommand = env.command_manager.get_term(command_name)
    return command.anchor_quat_w.clone()  # [num_envs, 4]


def motion_ref_root_lin_vel(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference (target) root/pelvis linear velocity in world frame. [num_envs, 3]"""
    command: MotionCommand = env.command_manager.get_term(command_name)
    # body_lin_vel_w[:, 0, :] = pelvis linear velocity from motion
    return command.body_lin_vel_w[:, 0, :].clone()  # [num_envs, 3]


def motion_ref_root_ang_vel(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference (target) root/pelvis angular velocity in world frame. [num_envs, 3]"""
    command: MotionCommand = env.command_manager.get_term(command_name)
    # body_ang_vel_w[:, 0, :] = pelvis angular velocity from motion
    return command.body_ang_vel_w[:, 0, :].clone()  # [num_envs, 3]


def motion_ref_joint_pos(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference (target) joint positions from motion. [num_envs, 29]"""
    command: MotionCommand = env.command_manager.get_term(command_name)
    return command.joint_pos.clone()  # [num_envs, 29]


def motion_ref_joint_vel(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference (target) joint velocities from motion. [num_envs, 29]"""
    command: MotionCommand = env.command_manager.get_term(command_name)
    return command.joint_vel.clone()  # [num_envs, 29]


def motion_ref_body_pos(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference body positions for tracked bodies, env-local world frame. [num_envs, N_bodies*3]"""
    command: MotionCommand = env.command_manager.get_term(command_name)
    # body_pos_w adds env_origins; subtract to get env-local, consistent with motion_ref_root_pos.
    pos = command.body_pos_w - env.scene.env_origins[:, None, :]  # [num_envs, N, 3]
    return pos.reshape(pos.shape[0], -1)  # [num_envs, N*3]


def motion_ref_body_vel(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference body linear velocities for tracked bodies in world frame. [num_envs, N_bodies*3]"""
    command: MotionCommand = env.command_manager.get_term(command_name)
    vel = command.body_lin_vel_w  # [num_envs, N, 3]
    return vel.reshape(vel.shape[0], -1).clone()  # [num_envs, N*3]


def motion_ref_body_pos_rel(env: ManagerBasedEnv, command_name: str = "motion") -> torch.Tensor:
    """Reference body positions expressed in the reference anchor (pelvis) local frame. [num_envs, N_bodies*3]

    Unlike motion_ref_body_pos (world-frame), this is translation- and yaw-invariant:
    positions are expressed relative to the reference pelvis pose, making them independent
    of where in the world the motion is placed.
    """
    command: MotionCommand = env.command_manager.get_term(command_name)
    N = command.body_pos_w.shape[1]
    anchor_pos_exp = command.anchor_pos_w[:, None, :].expand(-1, N, -1)   # [num_envs, N, 3]
    anchor_quat_exp = command.anchor_quat_w[:, None, :].expand(-1, N, -1) # [num_envs, N, 4]
    pos_rel, _ = subtract_frame_transforms(
        anchor_pos_exp, anchor_quat_exp,
        command.body_pos_w, command.body_quat_w,
    )  # [num_envs, N, 3] in anchor local frame
    return pos_rel.reshape(env.num_envs, -1)  # [num_envs, N*3]
