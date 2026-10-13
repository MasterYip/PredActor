"""
Deterministic Motion Collection Command for Data Collection

This module implements a deterministic sampling strategy for data collection:
- M motion files × N samples per motion = M*N total episodes
- Each environment is assigned to a specific (motion_id, sample_id) pair
- No resampling on failure - failed episodes don't count as completed
- When all assignments complete, idle envs reset to default pose

This ensures complete coverage of the action distribution for all motions.
"""

from __future__ import annotations

from copy import deepcopy
import math
import numpy as np
import os
import torch
from collections.abc import Sequence
from dataclasses import MISSING
from typing import TYPE_CHECKING, Any, Optional

import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation
from isaaclab.managers import CommandTerm, CommandTermCfg
from isaaclab.markers import VisualizationMarkers, VisualizationMarkersCfg
from isaaclab.utils import configclass
from isaaclab.utils.math import (
    quat_apply,
    quat_error_magnitude,
    quat_from_euler_xyz,
    quat_inv,
    quat_mul,
    sample_uniform,
    yaw_quat,
)

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


class MultiMotionLoader:
    """
    Loads multiple motion files with different lengths.
    Each motion is stored independently without padding.
    """

    def __init__(self,
                 motion_files: list[str],
                 body_indexes: Sequence[int],
                 device: str = "cpu"):
        assert len(motion_files) > 0, "motion_files cannot be empty"
        self.num_files = len(motion_files)
        self._body_indexes = body_indexes
        self.device = device

        # Store each motion's data in lists (no padding)
        self.joint_pos_list = []
        self.joint_vel_list = []
        self._body_pos_w_list = []
        self._body_quat_w_list = []
        self._body_lin_vel_w_list = []
        self._body_ang_vel_w_list = []
        self.fps_list = []
        self.file_lengths = []

        for motion_file in motion_files:
            assert os.path.isfile(
                motion_file), f"Invalid file path: {motion_file}"
            data = np.load(motion_file)

            self.fps_list.append(data["fps"])

            jp = torch.tensor(data["joint_pos"],
                              dtype=torch.float32,
                              device=device)
            jv = torch.tensor(data["joint_vel"],
                              dtype=torch.float32,
                              device=device)
            bp = torch.tensor(data["body_pos_w"],
                              dtype=torch.float32,
                              device=device)
            bq = torch.tensor(data["body_quat_w"],
                              dtype=torch.float32,
                              device=device)
            blv = torch.tensor(data["body_lin_vel_w"],
                               dtype=torch.float32,
                               device=device)
            bav = torch.tensor(data["body_ang_vel_w"],
                               dtype=torch.float32,
                               device=device)

            self.joint_pos_list.append(jp)
            self.joint_vel_list.append(jv)
            self._body_pos_w_list.append(bp)
            self._body_quat_w_list.append(bq)
            self._body_lin_vel_w_list.append(blv)
            self._body_ang_vel_w_list.append(bav)
            self.file_lengths.append(jp.shape[0])

        self.file_lengths = torch.tensor(self.file_lengths,
                                         dtype=torch.long,
                                         device=self.device)
        self.fps = self.fps_list[0]

    def get_motion_data_batch(
            self, motion_idx: int, time_steps_start: torch.Tensor,
            time_steps_end: torch.Tensor) -> dict[str, torch.Tensor]:
        """Get a time range of motion data for a specific motion."""
        time_steps_tensor = torch.arange(time_steps_start,
                                         time_steps_end,
                                         device=self.device)  # type: ignore
        time_steps_tensor = torch.clamp(time_steps_tensor,
                                        torch.tensor(0, device=self.device),
                                        self.file_lengths[motion_idx] - 1)

        return {
            "joint_pos":
            self.joint_pos_list[motion_idx][time_steps_tensor],
            "joint_vel":
            self.joint_vel_list[motion_idx][time_steps_tensor],
            "body_pos_w":
            self._body_pos_w_list[motion_idx][time_steps_tensor]
            [:, self._body_indexes],
            "body_quat_w":
            self._body_quat_w_list[motion_idx][time_steps_tensor]
            [:, self._body_indexes],
            "body_lin_vel_w":
            self._body_lin_vel_w_list[motion_idx][time_steps_tensor]
            [:, self._body_indexes],
            "body_ang_vel_w":
            self._body_ang_vel_w_list[motion_idx][time_steps_tensor]
            [:, self._body_indexes],
        }


class MotionCollectionCommand(CommandTerm):
    """
    Deterministic motion collection command for M*N sampling strategy.
    
    Key features:
    - Each env assigned to (motion_id, sample_id) pair
    - Failed episodes don't count as completed
    - Idle envs reset to default pose when all tasks done
    """
    
    cfg: MotionCollectionCommandCfg

    def __init__(self, cfg: MotionCollectionCommandCfg, env: ManagerBasedRLEnv):
        super().__init__(cfg, env)

        self.robot: Articulation = env.scene[cfg.asset_name]
        self.robot_anchor_body_index = self.robot.body_names.index(
            self.cfg.anchor_body_name)
        self.motion_anchor_body_index = self.cfg.body_names.index(
            self.cfg.anchor_body_name)
        self.body_indexes = torch.tensor(self.robot.find_bodies(
            self.cfg.body_names, preserve_order=True)[0],
                                         dtype=torch.long,
                                         device=self.device)

        self.motion = MultiMotionLoader(self.cfg.motion_files,
                                        self.body_indexes.tolist(),
                                        device=self.device)

        self.buffer_length: int = np.min(
            [env.max_episode_length,
             (self.motion.file_lengths.max().item())]
        ) + self.cfg.future_steps  # type: ignore

        # === Collection-specific tracking ===
        self.num_motions = len(self.cfg.motion_files)
        self.samples_per_motion = self.cfg.samples_per_motion
        self.total_tasks = self.num_motions * self.samples_per_motion
        
        # Track task status: [M, N]
        # 0 = not started, -1 = assigned (in progress), 1 = completed
        self.task_status = torch.zeros(self.num_motions, self.samples_per_motion,
                                       dtype=torch.long, device=self.device)
        
        # Track which task each env is working on: [num_envs]
        # Stores linear index: motion_idx * samples_per_motion + sample_idx
        self.env_task_assignment = torch.full((self.num_envs,), -1,
                                             dtype=torch.long, device=self.device)
        
        # Track if env is idle (all tasks done)
        self.env_is_idle = torch.zeros(self.num_envs, dtype=torch.long,
                                       device=self.device)

        # The command term resamples during env.step(), before the outer
        # collector applies its quality gate. Preserve the just-finished
        # outcome explicitly so a failure coincident with motion_end cannot be
        # mistaken for a successful timeout by the outer loop.
        self.last_episode_failed = torch.zeros(
            self.num_envs, dtype=torch.bool, device=self.device
        )
        self.last_episode_succeeded = torch.zeros(
            self.num_envs, dtype=torch.bool, device=self.device
        )
        # Optional BFM record-only mode keeps failure predicates as telemetry
        # while allowing the teacher to recover without an environment reset.
        self.diagnostic_raw_termination_terms: dict[str, torch.Tensor] = {}
        self.diagnostic_raw_termination_counts: dict[str, torch.Tensor] = {}
        
        # Motion and time tracking (same as original)
        self.time_steps = torch.zeros(self.num_envs,
                                      dtype=torch.long,
                                      device=self.device)
        self.motion_idx = torch.zeros(self.num_envs,
                                      dtype=torch.long,
                                      device=self.device)
        self.sample_idx = torch.zeros(self.num_envs,
                                      dtype=torch.long,
                                      device=self.device)
        self.motion_length = torch.zeros(self.num_envs,
                                         dtype=torch.long,
                                         device=self.device)
        self.buffer_start_time = torch.zeros(self.num_envs,
                                             dtype=torch.long,
                                             device=self.device)

        # Initialize buffers
        self._init_buffers()

        # Transform buffers
        self.body_pos_relative_w = torch.zeros(self.num_envs,
                                               len(cfg.body_names),
                                               3,
                                               device=self.device)
        self.body_quat_relative_w = torch.zeros(self.num_envs,
                                                len(cfg.body_names),
                                                4,
                                                device=self.device)
        self.body_quat_relative_w[:, :, 0] = 1.0

        # Metrics
        self.metrics["error_anchor_pos"] = torch.zeros(self.num_envs,
                                                       device=self.device)
        self.metrics["error_anchor_rot"] = torch.zeros(self.num_envs,
                                                       device=self.device)
        self.metrics["error_joint_pos"] = torch.zeros(self.num_envs,
                                                      device=self.device)
        self.metrics["error_joint_vel"] = torch.zeros(self.num_envs,
                                                      device=self.device)
        self.metrics["tasks_completed"] = torch.zeros(self.num_envs,
                                                      device=self.device)
        self.metrics["tasks_total"] = torch.zeros(self.num_envs,
                                                  device=self.device)
        self.metrics["collection_progress"] = torch.zeros(self.num_envs,
                                                         device=self.device)

        # Per-env directional yaw offset for dataset coverage augmentation [num_envs]
        self.direction_yaw = torch.zeros(self.num_envs, device=self.device)

        # For motion end termination
        self.motion_end_reset_env_idx = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)

    def _init_buffers(self):
        """Initialize buffers for trajectory data."""
        joint_dim = self.motion.joint_pos_list[0].shape[1]
        body_dim = len(self.cfg.body_names)

        self.joint_pos_buffer = torch.zeros(self.num_envs,
                                            self.buffer_length,
                                            joint_dim,
                                            device=self.device)
        self.joint_vel_buffer = torch.zeros(self.num_envs,
                                            self.buffer_length,
                                            joint_dim,
                                            device=self.device)
        self.body_pos_w_buffer = torch.zeros(self.num_envs,
                                             self.buffer_length,
                                             body_dim,
                                             3,
                                             device=self.device)
        self.body_quat_w_buffer = torch.zeros(self.num_envs,
                                              self.buffer_length,
                                              body_dim,
                                              4,
                                              device=self.device)
        self.body_lin_vel_w_buffer = torch.zeros(self.num_envs,
                                                 self.buffer_length,
                                                 body_dim,
                                                 3,
                                                 device=self.device)
        self.body_ang_vel_w_buffer = torch.zeros(self.num_envs,
                                                 self.buffer_length,
                                                 body_dim,
                                                 3,
                                                 device=self.device)
        self.body_quat_w_buffer[:, :, :, 0] = 1.0

    def _update_buffers(self, env_ids: Optional[torch.Tensor] = None):
        """Update buffers from motion data."""
        if env_ids is None:
            env_ids = torch.arange(self.num_envs, device=self.device)

        if len(env_ids) == 0:
            return

        for env_id in env_ids:
            motion_data = self.motion.get_motion_data_batch(
                int(self.motion_idx[env_id].item()),
                self.buffer_start_time[env_id],
                self.buffer_start_time[env_id] + self.buffer_length,
            )

            self.joint_pos_buffer[env_id] = motion_data[
                "joint_pos"]  # [num_envs, buffer_length, joint_dim]
            self.joint_vel_buffer[env_id] = motion_data["joint_vel"]
            self.body_pos_w_buffer[env_id] = motion_data["body_pos_w"]
            self.body_quat_w_buffer[env_id] = motion_data["body_quat_w"]
            self.body_lin_vel_w_buffer[env_id] = motion_data["body_lin_vel_w"]
            self.body_ang_vel_w_buffer[env_id] = motion_data["body_ang_vel_w"]

            # Apply directional yaw rotation to the entire buffer for this env.
            # This makes the same motion play toward a different heading per sample,
            # enriching dataset coverage without additional data collection runs.
            yaw = self.direction_yaw[env_id].item()
            if yaw != 0.0:
                half = yaw / 2.0
                yaw_q = torch.tensor([math.cos(half), 0.0, 0.0, math.sin(half)],
                                     dtype=torch.float32, device=self.device)  # (w,x,y,z)
                BL = self.buffer_length
                BD = len(self.cfg.body_names)
                N = BL * BD
                yaw_q_exp = yaw_q.unsqueeze(0).expand(N, -1)  # [N, 4]

                # Rotate body positions around the initial anchor XY position
                anchor0 = self.body_pos_w_buffer[env_id, 0, self.motion_anchor_body_index].clone()  # [3]
                pos = self.body_pos_w_buffer[env_id]  # [BL, BD, 3]
                delta = (pos - anchor0[None, None, :]).reshape(N, 3)
                self.body_pos_w_buffer[env_id] = (
                    quat_apply(yaw_q_exp, delta).reshape(BL, BD, 3) + anchor0[None, None, :])

                # Rotate orientations: q_new = q_yaw * q_original
                quat = self.body_quat_w_buffer[env_id].reshape(N, 4)
                self.body_quat_w_buffer[env_id] = quat_mul(yaw_q_exp, quat).reshape(BL, BD, 4)

                # Rotate linear and angular velocities
                linvel = self.body_lin_vel_w_buffer[env_id].reshape(N, 3)
                self.body_lin_vel_w_buffer[env_id] = quat_apply(yaw_q_exp, linvel).reshape(BL, BD, 3)
                angvel = self.body_ang_vel_w_buffer[env_id].reshape(N, 3)
                self.body_ang_vel_w_buffer[env_id] = quat_apply(yaw_q_exp, angvel).reshape(BL, BD, 3)

        if self.cfg.random_static_prob > 0:
            # Usage: p = random_static_prob
            # p=0.1, then 10% of the envs will be static.
            # p<0: disable random static.
            # p>1: enable all envs to be static.
            static_mask = torch.rand(
                len(env_ids), device=self.device) < self.cfg.random_static_prob
            if static_mask.any():
                static_env_ids = env_ids[static_mask]
                # 平移所有body, 使得所有帧的anchor等于第一帧的anchor
                # [N, buffer_length, body_dim, 3]
                anchor_first = self.body_pos_w_buffer[
                    static_env_ids, 0:1,
                    self.motion_anchor_body_index, :]  # [N, 1, 3]
                anchor_current = self.body_pos_w_buffer[
                    static_env_ids, :,
                    self.motion_anchor_body_index, :]  # [N, buffer_length, 3]
                translation = anchor_first - anchor_current  # [N, buffer_length, 3]
                self.body_pos_w_buffer[
                    static_env_ids, :, :, :] += translation[:, :, None, :]

                # 修正body的速度：移除anchor translation后的anchor vel分量, 只保留相对速度
                # frame_dt应为buffer内的步长, 取自数据
                # anchor 原先vel [N, buffer_length, 3]
                anchor_vel = self.body_lin_vel_w_buffer[
                    static_env_ids, :,
                    self.motion_anchor_body_index, :]  # [N, buffer_length, 3]
                # 修正每个body vel：减去anchor vel
                self.body_lin_vel_w_buffer[
                    static_env_ids, :, :, :] -= anchor_vel[:, :, None, :]

    def _get_next_task(self) -> Optional[tuple[int, int]]:
        """Get next unassigned task and mark it as assigned."""
        # Find tasks that are not started (status == 0)
        unassigned_mask = self.task_status == 0
        if not unassigned_mask.any():
            return None
        
        # Find first unassigned task
        unassigned_indices = torch.nonzero(unassigned_mask, as_tuple=False)
        if len(unassigned_indices) == 0:
            return None
        
        motion_idx, sample_idx = unassigned_indices[0].tolist()
        
        # Mark as assigned (-1) to prevent other envs from taking it
        self.task_status[motion_idx, sample_idx] = -1
        
        return (motion_idx, sample_idx)

    def _assign_task_to_env(self, env_id: int, motion_idx: int, sample_idx: int):
        """Assign a specific task to an environment."""
        self.motion_idx[env_id] = motion_idx
        self.sample_idx[env_id] = sample_idx
        self.motion_length[env_id] = self.motion.file_lengths[motion_idx]
        
        # Store task assignment
        task_id = motion_idx * self.samples_per_motion + sample_idx
        self.env_task_assignment[env_id] = task_id
        
        # Always start from beginning for deterministic collection
        self.time_steps[env_id] = 0
        self.buffer_start_time[env_id] = 0

        # Compute directional yaw: evenly tile [lo, hi) across samples_per_motion.
        # sample_idx 0 → lo, 1 → lo + span/N, ..., N-1 → lo + (N-1)/N * span.
        # If direction_range is (0,0) all yaws are 0 (no rotation).
        yaw_lo, yaw_hi = self.cfg.direction_range
        if yaw_lo != yaw_hi:
            span = yaw_hi - yaw_lo
            self.direction_yaw[env_id] = yaw_lo + (sample_idx / max(self.samples_per_motion, 1)) * span
        else:
            self.direction_yaw[env_id] = 0.0

        # Update buffers (direction_yaw must be set first — rotation is applied inside)
        self._update_buffers(torch.tensor([env_id], device=self.device))

    def retry_rejected_timeout(self, env_id: int, motion_idx: int, sample_idx: int):
        """Atomically reclaim a timeout-completed task rejected by a later quality gate."""
        status = int(self.task_status[motion_idx, sample_idx].item())
        if status == -1:
            raise RuntimeError(
                f"Cannot retry assigned task: motion={motion_idx}, sample={sample_idx}"
            )

        current_task = int(self.env_task_assignment[env_id].item())
        rejected_task = motion_idx * self.samples_per_motion + sample_idx
        if current_task >= 0 and current_task != rejected_task:
            current_motion, current_sample = divmod(
                current_task, self.samples_per_motion
            )
            if int(self.task_status[current_motion, current_sample].item()) == -1:
                self.task_status[current_motion, current_sample] = 0

        self.task_status[motion_idx, sample_idx] = -1
        self.env_is_idle[env_id] = 0
        self._assign_task_to_env(env_id, motion_idx, sample_idx)
        self._apply_initialization_randomization(
            torch.tensor([env_id], device=self.device)
        )

    def reconcile_saved_tasks(self, saved_task_ids: Sequence[int]) -> torch.Tensor:
        """Rebuild assignments from the collector's authoritative accepted task IDs."""
        saved_ids = sorted({int(task_id) for task_id in saved_task_ids})
        if saved_ids and (saved_ids[0] < 0 or saved_ids[-1] >= self.total_tasks):
            raise ValueError("saved task ID is outside the deterministic task range")

        saved_mask = torch.zeros(self.total_tasks, dtype=torch.bool, device=self.device)
        if saved_ids:
            saved_mask[torch.tensor(saved_ids, dtype=torch.long, device=self.device)] = True
        missing_task_ids = torch.where(~saved_mask)[0]
        if missing_task_ids.numel() > self.num_envs:
            raise RuntimeError(
                f"Cannot reopen {missing_task_ids.numel()} tasks with {self.num_envs} envs"
            )

        flat_status = self.task_status.view(-1)
        flat_status.zero_()
        flat_status[saved_mask] = 1
        self.env_task_assignment.fill_(-1)
        self.env_is_idle.fill_(1)

        reopened_env_ids = torch.arange(
            missing_task_ids.numel(), dtype=torch.long, device=self.device
        )
        for env_id, task_id in zip(reopened_env_ids.tolist(), missing_task_ids.tolist()):
            motion_idx, sample_idx = divmod(task_id, self.samples_per_motion)
            flat_status[task_id] = -1
            self.env_is_idle[env_id] = 0
            self._assign_task_to_env(env_id, motion_idx, sample_idx)

        if reopened_env_ids.numel() > 0:
            self._apply_initialization_randomization(reopened_env_ids)
        return reopened_env_ids

    def _reset_to_idle(self, env_ids: torch.Tensor, state=None):
        """Reset idle environments to default pose to avoid termination."""
        if len(env_ids) == 0:
            return
        if state is not None:
            self.env_is_idle[env_ids] = state
        # -1 means first time being idle, will be set to 1 in `data_collection.py` after episode collected
        
        # Set to default/zero pose
        joint_dim = self.joint_pos_buffer.shape[2]
        
        # Default joint positions (zeros or specified default)
        default_joint_pos = torch.zeros(len(env_ids), joint_dim,
                                       device=self.device)
        default_joint_vel = torch.zeros(len(env_ids), joint_dim,
                                       device=self.device)
        
        # Default root state (standing at env origin)
        default_root_pos = self._env.scene.env_origins[env_ids].clone()
        default_root_pos[:, 2] += self.cfg.default_height  # Add height offset
        
        default_root_quat = torch.zeros(len(env_ids), 4, device=self.device)
        default_root_quat[:, 0] = 1.0  # Identity quaternion
        
        default_root_lin_vel = torch.zeros(len(env_ids), 3, device=self.device)
        default_root_ang_vel = torch.zeros(len(env_ids), 3, device=self.device)
        
        # Write to simulation
        self.robot.write_joint_state_to_sim(default_joint_pos,
                                           default_joint_vel,
                                           env_ids=env_ids)
        self.robot.write_root_state_to_sim(
            torch.cat([default_root_pos, default_root_quat,
                      default_root_lin_vel, default_root_ang_vel], dim=-1),
            env_ids=env_ids,
        )
        
        # Set buffers to maintain default state
        for i, env_id in enumerate(env_ids):
            self.joint_pos_buffer[env_id, :] = default_joint_pos[i]
            self.joint_vel_buffer[env_id, :] = default_joint_vel[i]

    # === Properties (same as original) ===
    
    @property
    def command(self) -> torch.Tensor:
        cmd = torch.cat([self.motion_joint_pos, self.motion_joint_vel], dim=1)
        return cmd

    @property
    def joint_pos(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.joint_pos_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices]

    @property
    def joint_vel(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.joint_vel_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices]

    @property
    def body_pos_w(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.body_pos_w_buffer[
            torch.arange(self.num_envs, device=self.device),
            buffer_indices] + self._env.scene.env_origins[:, None, :]

    @property
    def body_quat_w(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.body_quat_w_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices]

    @property
    def body_lin_vel_w(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.body_lin_vel_w_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices]

    @property
    def body_ang_vel_w(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.body_ang_vel_w_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices]

    @property
    def anchor_pos_w(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return (self.body_pos_w_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices,
            self.motion_anchor_body_index] + self._env.scene.env_origins)

    @property
    def anchor_quat_w(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.body_quat_w_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices,
            self.motion_anchor_body_index]

    @property
    def anchor_lin_vel_w(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.body_lin_vel_w_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices,
            self.motion_anchor_body_index]

    @property
    def anchor_ang_vel_w(self) -> torch.Tensor:
        buffer_indices = torch.clamp(self.time_steps - self.buffer_start_time,
                                     0, self.buffer_length - 1)
        return self.body_ang_vel_w_buffer[
            torch.arange(self.num_envs, device=self.device), buffer_indices,
            self.motion_anchor_body_index]

    # Future reference properties for N-step lookahead
    @property
    def motion_joint_pos(self) -> torch.Tensor:
        """Future N-step joint positions reference."""
        if self.cfg.future_steps <= 1:
            return self.joint_pos
        else:
            current_indices = torch.clamp(
                self.time_steps - self.buffer_start_time, 0,
                self.buffer_length - 1)
            future_indices = current_indices[:, None] + torch.arange(
                self.cfg.future_steps, device=self.device)[None, :]
            future_indices = torch.clamp(future_indices, 0,
                                         self.buffer_length - 1)
            return self.joint_pos_buffer[
                torch.arange(self.num_envs, device=self.device)[:, None],
                future_indices].view(self.num_envs, -1)

    @property
    def motion_joint_vel(self) -> torch.Tensor:
        """Future N-step joint velocities reference."""
        if self.cfg.future_steps <= 1:
            return self.joint_vel
        else:
            current_indices = torch.clamp(
                self.time_steps - self.buffer_start_time, 0,
                self.buffer_length - 1)
            future_indices = current_indices[:, None] + torch.arange(
                self.cfg.future_steps, device=self.device)[None, :]
            future_indices = torch.clamp(future_indices, 0,
                                         self.buffer_length - 1)
            return self.joint_vel_buffer[
                torch.arange(self.num_envs, device=self.device)[:, None],
                future_indices].view(self.num_envs, -1)

    @property
    def motion_anchor_pos(self) -> torch.Tensor:
        """Future N-step anchor positions reference."""
        if self.cfg.future_steps <= 1:
            return self.anchor_pos_w
        else:
            current_indices = torch.clamp(
                self.time_steps - self.buffer_start_time, 0,
                self.buffer_length - 1)
            future_indices = current_indices[:, None] + torch.arange(
                self.cfg.future_steps, device=self.device)[None, :]
            future_indices = torch.clamp(future_indices, 0,
                                         self.buffer_length - 1)
            future_pos = self.body_pos_w_buffer[
                torch.arange(self.num_envs, device=self.device)[:, None],
                future_indices, self.motion_anchor_body_index]
            return (future_pos + self._env.scene.env_origins[:, None, :]).view(
                self.num_envs, -1)

    @property
    def motion_anchor_quat(self) -> torch.Tensor:
        """Future N-step anchor quaternions reference."""
        if self.cfg.future_steps <= 1:
            return self.anchor_quat_w
        else:
            current_indices = torch.clamp(
                self.time_steps - self.buffer_start_time, 0,
                self.buffer_length - 1)
            future_indices = current_indices[:, None] + torch.arange(
                self.cfg.future_steps, device=self.device)[None, :]
            future_indices = torch.clamp(future_indices, 0,
                                         self.buffer_length - 1)
            future_quat = self.body_quat_w_buffer[
                torch.arange(self.num_envs, device=self.device)[:, None],
                future_indices, self.motion_anchor_body_index]
            # breakpoint()
            return future_quat.view(self.num_envs, -1)

    @property
    def robot_joint_pos(self) -> torch.Tensor:
        return self.robot.data.joint_pos

    @property
    def robot_joint_vel(self) -> torch.Tensor:
        return self.robot.data.joint_vel

    @property
    def robot_body_pos_w(self) -> torch.Tensor:
        return self.robot.data.body_pos_w[:, self.body_indexes]

    @property
    def robot_body_quat_w(self) -> torch.Tensor:
        return self.robot.data.body_quat_w[:, self.body_indexes]

    @property
    def robot_body_lin_vel_w(self) -> torch.Tensor:
        return self.robot.data.body_lin_vel_w[:, self.body_indexes]

    @property
    def robot_body_ang_vel_w(self) -> torch.Tensor:
        return self.robot.data.body_ang_vel_w[:, self.body_indexes]

    @property
    def robot_anchor_pos_w(self) -> torch.Tensor:
        return self.robot.data.body_pos_w[:, self.robot_anchor_body_index]

    @property
    def robot_anchor_quat_w(self) -> torch.Tensor:
        return self.robot.data.body_quat_w[:, self.robot_anchor_body_index]

    @property
    def robot_anchor_lin_vel_w(self) -> torch.Tensor:
        return self.robot.data.body_lin_vel_w[:, self.robot_anchor_body_index]

    @property
    def robot_anchor_ang_vel_w(self) -> torch.Tensor:
        return self.robot.data.body_ang_vel_w[:, self.robot_anchor_body_index]

    # [Necessary]
    def _update_metrics(self):
        """Update tracking metrics."""
        self.metrics["error_anchor_pos"] = torch.norm(self.anchor_pos_w -
                                                      self.robot_anchor_pos_w,
                                                      dim=-1)
        self.metrics["error_anchor_rot"] = quat_error_magnitude(
            self.anchor_quat_w, self.robot_anchor_quat_w)
        self.metrics["error_anchor_lin_vel"] = torch.norm(
            self.anchor_lin_vel_w - self.robot_anchor_lin_vel_w, dim=-1)
        self.metrics["error_anchor_ang_vel"] = torch.norm(
            self.anchor_ang_vel_w - self.robot_anchor_ang_vel_w, dim=-1)

        self.metrics["error_body_pos"] = torch.norm(self.body_pos_relative_w -
                                                    self.robot_body_pos_w,
                                                    dim=-1).mean(dim=-1)
        self.metrics["error_body_rot"] = quat_error_magnitude(
            self.body_quat_relative_w, self.robot_body_quat_w).mean(dim=-1)

        self.metrics["error_body_lin_vel"] = torch.norm(
            self.body_lin_vel_w - self.robot_body_lin_vel_w,
            dim=-1).mean(dim=-1)
        self.metrics["error_body_ang_vel"] = torch.norm(
            self.body_ang_vel_w - self.robot_body_ang_vel_w,
            dim=-1).mean(dim=-1)

        self.metrics["error_joint_pos"] = torch.norm(self.joint_pos -
                                                     self.robot_joint_pos,
                                                     dim=-1)
        self.metrics["error_joint_vel"] = torch.norm(self.joint_vel -
                                                     self.robot_joint_vel,
                                                     dim=-1)
        
        # Collection progress metrics
        completed_count = (self.task_status == 1).sum().item()
        assigned_count = (self.task_status == -1).sum().item()
        self.metrics["tasks_completed"][:] = completed_count
        self.metrics["tasks_total"][:] = self.total_tasks
        self.metrics["collection_progress"][:] = completed_count / max(self.total_tasks, 1)

    def _resample_command(self, env_ids: torch.Tensor):
        """
        Resample command for environments that need new tasks.
        
        Key logic:
        - On episode end, check if it was successful (full length)
        - If successful, mark task as completed and assign next task
        - If failed (terminated early), reassign same task
        - If no tasks left, set to idle
        """
        if len(env_ids) == 0:
            return

        # Ensure env_ids is a 1D tensor on the right device
        env_ids = env_ids.to(device=self.device).view(-1)
        self.last_episode_failed[env_ids] = False
        self.last_episode_succeeded[env_ids] = False

        # Determine which of these envs were successful (not terminated by failure/time-out)
        was_successful = ~self._env.termination_manager.terminated[env_ids]  # type: ignore

        # Active envs are those not idle and with a valid task assignment
        active_mask = (self.env_is_idle[env_ids] == 0) & (self.env_task_assignment[env_ids] >= 0)
        active_envs = env_ids[active_mask]

        # Split active envs into success/failure
        if active_envs.numel() > 0:
            succ_mask = was_successful[active_mask]
            fail_mask = ~succ_mask

            # Handle successes in batch
            if succ_mask.any():
                succ_envs = active_envs[succ_mask]
                self.last_episode_succeeded[succ_envs] = True
                motion_ids = self.motion_idx[succ_envs]
                sample_ids = self.sample_idx[succ_envs]
                self.task_status[motion_ids, sample_ids] = 1
                completed_count = (self.task_status == 1).sum().item()
                # for e, m, s in zip(succ_envs.tolist(), motion_ids.tolist(), sample_ids.tolist()):
                #     print(f"[Collection] Env {e} Completed: Motion {m}, Sample {s} ({completed_count}/{self.total_tasks})")

            # Handle failures in batch (mark as unassigned to retry)
            if fail_mask.any():
                fail_envs = active_envs[fail_mask]
                self.last_episode_failed[fail_envs] = True
                motion_ids = self.motion_idx[fail_envs]
                sample_ids = self.sample_idx[fail_envs]
                self.task_status[motion_ids, sample_ids] = 0
                for e, m, s in zip(fail_envs.tolist(), motion_ids.tolist(), sample_ids.tolist()):
                    print(f"[Collection] Env {e} Failed: Motion {m}, Sample {s} - will retry")

        # Determine next actions for each env: either assign next task or set idle
        assign_list = []
        idle_first_list = []
        idle_repeat_list = []

        for e in env_ids.tolist():
            next_task = self._get_next_task()
            if next_task is None:
                if self.env_is_idle[e] == 0:
                    idle_first_list.append(e)
                else:
                    idle_repeat_list.append(e)
            else:
                assign_list.append((e, next_task[0], next_task[1]))

        # Reset to idle in batch (first-time and repeat separately to set state flag)
        if len(idle_first_list) > 0:
            self._reset_to_idle(torch.tensor(idle_first_list, device=self.device), -1)
        # if len(idle_repeat_list) > 0:
        #     self._reset_to_idle(torch.tensor(idle_repeat_list, device=self.device))

        # Assign tasks (loop per-env is okay; heavy ops are buffered; randomization will be batched)
        assigned_env_ids = []
        for e, m, s in assign_list:
            self._assign_task_to_env(e, m, s)
            assigned_env_ids.append(e)

        # Apply initialization randomization in batch for all newly assigned envs
        if len(assigned_env_ids) > 0:
            self._apply_initialization_randomization(torch.tensor(assigned_env_ids, device=self.device))

    def _apply_initialization_randomization(self, env_ids: torch.Tensor):
        """Apply pose/velocity/joint randomization on episode start."""
        if len(env_ids) == 0:
            return
        
        root_pos = self.body_pos_w[:, 0].clone()
        root_ori = self.body_quat_w[:, 0].clone()
        root_lin_vel = self.body_lin_vel_w[:, 0].clone()
        root_ang_vel = self.body_ang_vel_w[:, 0].clone()

        # Pose randomization
        range_list = [
            self.cfg.pose_range.get(key, (0.0, 0.0))
            for key in ["x", "y", "z", "roll", "pitch", "yaw"]
        ]
        ranges = torch.tensor(range_list, device=self.device)
        rand_samples = sample_uniform(ranges[:, 0],
                                      ranges[:, 1], (len(env_ids), 6),
                                      device=self.device)
        root_pos[env_ids] += rand_samples[:, 0:3]
        orientations_delta = quat_from_euler_xyz(rand_samples[:, 3],
                                                 rand_samples[:, 4],
                                                 rand_samples[:, 5])
        root_ori[env_ids] = quat_mul(orientations_delta, root_ori[env_ids])

        # Velocity randomization
        range_list = [
            self.cfg.velocity_range.get(key, (0.0, 0.0))
            for key in ["x", "y", "z", "roll", "pitch", "yaw"]
        ]
        ranges = torch.tensor(range_list, device=self.device)
        rand_samples = sample_uniform(ranges[:, 0],
                                      ranges[:, 1], (len(env_ids), 6),
                                      device=self.device)
        root_lin_vel[env_ids] += rand_samples[:, :3]
        root_ang_vel[env_ids] += rand_samples[:, 3:]

        # Joint randomization
        joint_pos = self.joint_pos.clone()
        joint_vel = self.joint_vel.clone()

        joint_pos += sample_uniform(*self.cfg.joint_position_range,
                                    joint_pos.shape,
                                    device=self.device)
        soft_joint_pos_limits = self.robot.data.soft_joint_pos_limits[env_ids]
        joint_pos[env_ids] = torch.clip(joint_pos[env_ids],
                                        soft_joint_pos_limits[:, :, 0],
                                        soft_joint_pos_limits[:, :, 1])

        # Write to simulation
        self.robot.write_joint_state_to_sim(joint_pos[env_ids],
                                           joint_vel[env_ids],
                                           env_ids=env_ids)
        self.robot.write_root_state_to_sim(
            torch.cat([
                root_pos[env_ids], root_ori[env_ids], root_lin_vel[env_ids],
                root_ang_vel[env_ids]
            ], dim=-1),
            env_ids=env_ids,
        )

    def _update_command(self):
        """Update command each step."""
        # Only advance time for non-idle envs
        active_mask = self.env_is_idle == 0
        self.time_steps[active_mask] += 1
        
        # Find envs that reached motion end
        env_ids = torch.where(self.time_steps >= self.motion_length)[0]
        if hasattr(self.cfg, "motion_end_reset") and self.cfg.motion_end_reset:
            self.motion_end_reset_env_idx = self.time_steps >= self.motion_length
        else:
            self._resample_command(env_ids)

        # Transform motion reference to robot frame (same as original)
        anchor_pos_w_repeat = self.anchor_pos_w[:, None, :].repeat(
            1, len(self.cfg.body_names), 1)
        anchor_quat_w_repeat = self.anchor_quat_w[:, None, :].repeat(
            1, len(self.cfg.body_names), 1)
        robot_anchor_pos_w_repeat = self.robot_anchor_pos_w[:, None, :].repeat(
            1, len(self.cfg.body_names), 1)
        robot_anchor_quat_w_repeat = self.robot_anchor_quat_w[:,
                                                              None, :].repeat(
                                                                  1,
                                                                  len(self.cfg.
                                                                      body_names
                                                                      ), 1)

        delta_pos_w = robot_anchor_pos_w_repeat
        delta_pos_w[..., 2] = anchor_pos_w_repeat[..., 2]
        delta_ori_w = yaw_quat(
            quat_mul(robot_anchor_quat_w_repeat,
                     quat_inv(anchor_quat_w_repeat)))

        self.body_quat_relative_w = quat_mul(delta_ori_w, self.body_quat_w)
        self.body_pos_relative_w = delta_pos_w + quat_apply(
            delta_ori_w, self.body_pos_w - anchor_pos_w_repeat)

    def _set_debug_vis_impl(self, debug_vis: bool):
        """Show the tracked robot and its aligned reference body positions."""
        if debug_vis:
            if not hasattr(self, "current_anchor_visualizer"):
                current_material = sim_utils.PreviewSurfaceCfg(diffuse_color=(0.8, 0.2, 0.2))
                reference_material = sim_utils.PreviewSurfaceCfg(diffuse_color=(0.0, 1.0, 0.0))

                def marker_cfg(prim_path: str, radius: float,
                               material: sim_utils.PreviewSurfaceCfg) -> VisualizationMarkersCfg:
                    return VisualizationMarkersCfg(
                        prim_path=prim_path,
                        markers={
                            "target": sim_utils.SphereCfg(
                                radius=radius,
                                visual_material=material,
                            ),
                        },
                    )

                self.current_anchor_visualizer = VisualizationMarkers(
                    marker_cfg("/Visuals/Command/current/anchor", 0.05, current_material))
                self.goal_anchor_visualizer = VisualizationMarkers(
                    marker_cfg("/Visuals/Command/reference/anchor", 0.12, reference_material))
                self.current_body_visualizers = [
                    VisualizationMarkers(
                        marker_cfg(f"/Visuals/Command/current/{name}", 0.02, current_material))
                    for name in self.cfg.body_names
                ]
                self.goal_body_visualizers = [
                    VisualizationMarkers(
                        marker_cfg(f"/Visuals/Command/reference/{name}", 0.055, reference_material))
                    for name in self.cfg.body_names
                ]

            self.current_anchor_visualizer.set_visibility(True)
            self.goal_anchor_visualizer.set_visibility(True)
            for current, goal in zip(self.current_body_visualizers, self.goal_body_visualizers):
                current.set_visibility(True)
                goal.set_visibility(True)
        elif hasattr(self, "current_anchor_visualizer"):
            self.current_anchor_visualizer.set_visibility(False)
            self.goal_anchor_visualizer.set_visibility(False)
            for current, goal in zip(self.current_body_visualizers, self.goal_body_visualizers):
                current.set_visibility(False)
                goal.set_visibility(False)

    def _debug_vis_callback(self, event):
        """Update current (red) and reference (green) markers."""
        if not self.robot.is_initialized:
            return

        if not hasattr(self, "_debug_vis_confirmed"):
            print(f"[MotionCollection] Reference visualization active: "
                  f"{len(self.goal_body_visualizers)} green body markers per environment")
            self._debug_vis_confirmed = True

        self.current_anchor_visualizer.visualize(self.robot_anchor_pos_w, self.robot_anchor_quat_w)
        self.goal_anchor_visualizer.visualize(self.anchor_pos_w, self.anchor_quat_w)
        for body_index, (current, goal) in enumerate(
                zip(self.current_body_visualizers, self.goal_body_visualizers)):
            current.visualize(self.robot_body_pos_w[:, body_index], self.robot_body_quat_w[:, body_index])
            goal.visualize(self.body_pos_relative_w[:, body_index], self.body_quat_relative_w[:, body_index])


@configclass
class MotionCollectionCommandCfg(CommandTermCfg):
    """Configuration for motion collection command."""

    class_type: type = MotionCollectionCommand

    asset_name: str = MISSING
    motion_files: list[str] = MISSING
    anchor_body_name: str = MISSING
    body_names: list[str] = MISSING

    # Collection-specific
    samples_per_motion: int = 1  # N samples per motion
    default_height: float = 0.98  # Default height for idle pose

    # Randomization ranges
    pose_range: dict[str, tuple[float, float]] = {}
    velocity_range: dict[str, tuple[float, float]] = {}
    joint_position_range: tuple[float, float] = (-0.52, 0.52)

    # Future steps for N-step lookahead
    future_steps: int = 1
    # Random Static
    random_static_prob: float = -1.0
    # Motion end reset
    motion_end_reset: bool = True
    # Optional physics synchronization window after directly writing reset state.
    termination_grace_steps: int = 0
    # Evaluate anchor/EE failure predicates for telemetry but do not terminate.
    # Motion-end and fixed-horizon timeout terms remain active.
    record_only_termination: bool = False

    # Directional yaw range for dataset coverage augmentation.
    # Each sample_idx maps to an evenly-spaced yaw in [lo, hi):
    #   sample i → lo + i/N * (hi - lo)
    # Set to (-pi, pi) to cover the full 360° across N samples.
    # Set to (0.0, 0.0) to disable (default).
    direction_range: tuple[float, float] = (0.0, 0.0)
