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
from isaaclab.markers.config import FRAME_MARKER_CFG, DEFORMABLE_TARGET_MARKER_CFG
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


class MotionLoader:

    def __init__(self,
                 motion_file: str,
                 body_indexes: Sequence[int],
                 device: str = "cpu"):
        assert os.path.isfile(motion_file), f"Invalid file path: {motion_file}"
        data = np.load(motion_file)
        self.fps = data["fps"]
        self.joint_pos = torch.tensor(data["joint_pos"],
                                      dtype=torch.float32,
                                      device=device)

        self.joint_vel = torch.tensor(data["joint_vel"],
                                      dtype=torch.float32,
                                      device=device)
        self._body_pos_w = torch.tensor(data["body_pos_w"],
                                        dtype=torch.float32,
                                        device=device)
        self._body_quat_w = torch.tensor(data["body_quat_w"],
                                         dtype=torch.float32,
                                         device=device)
        self._body_lin_vel_w = torch.tensor(data["body_lin_vel_w"],
                                            dtype=torch.float32,
                                            device=device)
        self._body_ang_vel_w = torch.tensor(data["body_ang_vel_w"],
                                            dtype=torch.float32,
                                            device=device)
        self._body_indexes = body_indexes
        self.time_step_total = self.joint_pos.shape[0]

    @property
    def body_pos_w(self) -> torch.Tensor:
        return self._body_pos_w[:, self._body_indexes]

    @property
    def body_quat_w(self) -> torch.Tensor:
        return self._body_quat_w[:, self._body_indexes]

    @property
    def body_lin_vel_w(self) -> torch.Tensor:
        return self._body_lin_vel_w[:, self._body_indexes]

    @property
    def body_ang_vel_w(self) -> torch.Tensor:
        return self._body_ang_vel_w[:, self._body_indexes]


class MultiMotionLoader:

    def __init__(self,
                 motion_files: list[str],
                 body_indexes: Sequence[int],
                 device: str = "cpu"):
        assert len(motion_files) > 0, "motion_files 不能为空"
        self.num_files = len(motion_files)
        self._body_indexes = body_indexes
        self.device = device

        # 存储每个motion的数据为list，不进行填充
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
        self.fps = self.fps_list[0]  # 可以根据需求调整

    def get_motion_data_batch(
            self, motion_idx: int, time_steps_start: torch.Tensor,
            time_steps_end: torch.Tensor) -> dict[str, torch.Tensor]:
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


class MotionCommand(CommandTerm):
    cfg: MotionCommandCfg

    _HORIZON_TEACHER_GLOBAL_TENSORS = (
        "failed_motion_count",
        "success_motion_count",
        "current_failed_motion_count",
        "current_success_motion_count",
    )
    _HORIZON_TEACHER_GLOBAL_SCALARS = (
        "failed_total_count",
        "success_total_count",
    )

    def __init__(self, cfg: MotionCommandCfg, env: ManagerBasedRLEnv):
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
             (self.motion.file_lengths.max().item())]  # type: ignore
        ) + self.cfg.future_steps  # type: ignore

        # 初始化状态变量
        self.time_steps = torch.zeros(self.num_envs,
                                      dtype=torch.long,
                                      device=self.device)
        self.motion_idx = torch.zeros(self.num_envs,
                                      dtype=torch.long,
                                      device=self.device)
        self.motion_length = torch.zeros(self.num_envs,
                                         dtype=torch.long,
                                         device=self.device)
        self.buffer_start_time = torch.zeros(self.num_envs,
                                             dtype=torch.long,
                                             device=self.device)

        # 初始化buffer，存储轨迹数据
        self._init_buffers()

        self.body_pos_relative_w = torch.zeros(self.num_envs,
                                               len(cfg.body_names),
                                               3,
                                               device=self.device)
        self.body_quat_relative_w = torch.zeros(self.num_envs,
                                                len(cfg.body_names),
                                                4,
                                                device=self.device)
        self.body_quat_relative_w[:, :, 0] = 1.0

        self.num_motion: int = self.motion.file_lengths.shape[0]  # type:ignore
        self.failed_motion_count = torch.zeros(
            self.num_motion, dtype=torch.float, device=self.device) + 1
        self.success_motion_count = torch.zeros(
            self.num_motion, dtype=torch.float, device=self.device) + 1
        self.failed_total_count: float = 0.0 + 1e-8
        self.success_total_count: float = 0.0 + 1e-8
        self.current_failed_motion_count = torch.zeros(self.num_motion,
                                                       dtype=torch.float,
                                                       device=self.device)
        self.current_success_motion_count = torch.zeros(self.num_motion,
                                                        dtype=torch.float,
                                                        device=self.device)

        if self.cfg.adaptive_length_weighted:
            assert self.cfg.ads_type == "v1", "Adaptive length weighted is only supported for v1 adaptive sampling type"

        self.metrics["error_anchor_pos"] = torch.zeros(self.num_envs,
                                                       device=self.device)
        self.metrics["error_anchor_rot"] = torch.zeros(self.num_envs,
                                                       device=self.device)
        self.metrics["error_anchor_lin_vel"] = torch.zeros(self.num_envs,
                                                           device=self.device)
        self.metrics["error_anchor_ang_vel"] = torch.zeros(self.num_envs,
                                                           device=self.device)
        self.metrics["error_body_pos"] = torch.zeros(self.num_envs,
                                                     device=self.device)
        self.metrics["error_body_rot"] = torch.zeros(self.num_envs,
                                                     device=self.device)
        self.metrics["error_joint_pos"] = torch.zeros(self.num_envs,
                                                      device=self.device)
        self.metrics["error_joint_vel"] = torch.zeros(self.num_envs,
                                                      device=self.device)
        self.metrics["sampling_entropy"] = torch.zeros(self.num_envs,
                                                       device=self.device)
        self.metrics["pfail_entropy"] = torch.zeros(self.num_envs,
                                                    device=self.device)
        self.metrics["pfail_mean"] = torch.zeros(self.num_envs,
                                                 device=self.device)
        self.metrics["failed_total_count"] = torch.zeros(
            self.num_envs, device=self.device)  # Strange But works
        self.metrics["success_total_count"] = torch.zeros(self.num_envs,
                                                          device=self.device)
        self.metrics["pfail_total"] = torch.zeros(self.num_envs,
                                                  device=self.device)
        self.metrics["sampling_top1_prob"] = torch.zeros(self.num_envs,
                                                         device=self.device)
        # self.metrics["sampling_top1_bin"] = torch.zeros(self.num_envs, device=self.device)

        # For motion end termination
        self.motion_end_reset_env_idx = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)

    def _init_buffers(self):
        """初始化buffer存储轨迹数据"""
        # 获取joint数量
        joint_dim = self.motion.joint_pos_list[0].shape[1]
        body_dim = len(self.cfg.body_names)

        # 初始化buffer，形状为 (num_envs, buffer_length, ...)
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

        # 初始化quaternion为[1,0,0,0]
        self.body_quat_w_buffer[:, :, :, 0] = 1.0

    def _update_buffers(self, env_ids: Optional[torch.Tensor] = None):
        """更新buffer，从motion数据中填充buffer"""
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

    def __old_adaptive_sampling(self, env_ids: Sequence[int]):
        raise NotImplementedError("Adaptive sampling is not implemented")
        episode_failed = self._env.termination_manager.terminated[env_ids]
        if torch.any(episode_failed):
            # 每个env当前的time_steps对应的bin的索引
            current_bin_index = torch.clamp(
                (self.time_steps * self.bin_count) //
                max(self.motion.file_lengths.max().item(), 1), 0,
                self.bin_count - 1)
            # current_bin_index = [0, 2, 1, 3]
            # episode_failed = [False, True, False, True]
            # fail_bins = current_bin_index[env_ids][episode_failed]  # [2, 3]
            fail_bins = current_bin_index[env_ids][episode_failed]
            # 统计每个bin的失败次数
            self._current_bin_failed[:] = torch.bincount(
                fail_bins, minlength=self.bin_count)

        # Sample
        # 添加一点均匀分布的概率，防止有些动作采样概率为0
        sampling_probabilities = self.bin_failed_count + self.cfg.adaptive_uniform_ratio / float(
            self.bin_count)
        # 填充只在最后一个维度（length） 上进行
        sampling_probabilities = torch.nn.functional.pad(
            sampling_probabilities.unsqueeze(0).unsqueeze(0),
            (0, self.cfg.adaptive_kernel_size - 1),  # Non-causal kernel
            mode="replicate",
        )  # replicate 保证填充的值不改变统计趋势（用最后一个 bin 的失败概率）
        # 因为后面邻居的失败可能跟前面有关，且越近相关程度越高，所以卷积核采用的是指数形式的，会考虑未来的失败
        sampling_probabilities = torch.nn.functional.conv1d(
            sampling_probabilities, self.kernel.view(1, 1, -1)).view(-1)

        sampling_probabilities = sampling_probabilities / sampling_probabilities.sum(
        )

        sampled_bins = torch.multinomial(sampling_probabilities,
                                         len(env_ids),
                                         replacement=True)

        self.time_steps[env_ids] = (
            (sampled_bins +
             sample_uniform(0.0, 1.0, (len(env_ids), ), device=self.device)) /
            self.bin_count *
            (self.motion.file_lengths.max().item() - 1)).long()
        # 再从bin转回time_steps
        self.time_steps[env_ids] = (
            sampled_bins / self.bin_count *
            (self.motion.file_lengths.max().item() - 1)).long()

        # Metrics
        H = -(sampling_probabilities *
              (sampling_probabilities + 1e-12).log()).sum()
        H_norm = H / math.log(self.bin_count)
        pmax, imax = sampling_probabilities.max(dim=0)
        self.metrics["sampling_entropy"][:] = H_norm
        self.metrics["sampling_top1_prob"][:] = pmax
        self.metrics["sampling_top1_bin"][:] = imax.float() / self.bin_count

    def _adaptive_sampling(self, env_ids: torch.Tensor) -> torch.Tensor:
        episode_failed: torch.Tensor = self._env.termination_manager.terminated[
            env_ids]  # type:ignore
        episode_timeout: torch.Tensor = self._env.termination_manager.time_outs[
            env_ids]  # type:ignore
        episode_success: torch.Tensor = ~episode_failed  # 所有不是episode_failed的env
        # 既不是terminate也不是timeout:  在一个episode内, motion结束了, 也会resample. 统计为success
        # total_episode_env = len(env_ids)
        # print(
        #     f"episode_failed: {episode_failed.sum().item()} | episode_timeout: {episode_timeout.sum().item()} | episode_success: {episode_success.sum().item()} | total_episode_env: {total_episode_env}"
        # )
        if torch.any(episode_failed):
            # 统计每个motion的失败次数
            failed_motions = self.motion_idx[env_ids][episode_failed]
            self.current_failed_motion_count[:] = torch.bincount(
                failed_motions, minlength=self.num_motion)
        if torch.any(episode_success):
            # 统计每个motion的成功次数
            success_motions = self.motion_idx[env_ids][episode_success]
            self.current_success_motion_count[:] = torch.bincount(
                success_motions, minlength=self.num_motion)

        if self.cfg.ads_type == "v1":
            p_fail = self.failed_motion_count / (
                self.failed_motion_count.sum() + 1e-8)
            if self.cfg.adaptive_length_weighted:
                p_fail = p_fail * self.motion.file_lengths
                p_fail = p_fail / (p_fail.sum() + 1e-8)
            p_fail_sample = torch.pow(p_fail, self.cfg.adaptive_beta)
            p_fail_sample = p_fail_sample / (p_fail_sample.sum() + 1e-8)

            sampling_probabilities = (
                p_fail_sample * (1 - self.cfg.adaptive_uniform_ratio) +
                self.cfg.adaptive_uniform_ratio / float(self.num_motion))
        elif self.cfg.ads_type == "v2":
            p_fail = self.failed_motion_count / (
                self.failed_motion_count + self.success_motion_count + 1e-8)
            p_fail_sample = torch.pow(p_fail, self.cfg.adaptive_beta)
            p_fail_sample = p_fail_sample / (p_fail_sample.sum() + 1e-8)

            sampling_probabilities = (
                p_fail_sample * (1 - self.cfg.adaptive_uniform_ratio) +
                self.cfg.adaptive_uniform_ratio / float(self.num_motion))
        elif self.cfg.ads_type == "v3":
            p_fail = self.failed_motion_count / (
                self.failed_motion_count + self.success_motion_count + 1e-8)
            p_fail_sample = 1 - torch.pow(1 - p_fail, self.cfg.adaptive_beta)
            p_fail_sample = p_fail_sample / (p_fail_sample.sum() + 1e-8)

            sampling_probabilities = (
                p_fail_sample * (1 - self.cfg.adaptive_uniform_ratio) +
                self.cfg.adaptive_uniform_ratio / float(self.num_motion))
        else:
            raise ValueError(
                f"Unsupported adaptive sampling type: {self.cfg.ads_type}")

        # 根据概率进行采样
        sampled_motion_ids = torch.multinomial(sampling_probabilities,
                                               len(env_ids),
                                               replacement=True)

        # Metrics
        H_samp = -(sampling_probabilities *
                   (sampling_probabilities + 1e-12).log()).sum()
        H_samp_norm = H_samp / math.log(self.num_motion)

        p_fail_norm = p_fail / (p_fail.sum() + 1e-8)
        H_pfail = -(p_fail_norm * (p_fail_norm + 1e-12).log()).sum()
        H_pfail_norm = H_pfail / math.log(self.num_motion)

        pmax, imax = sampling_probabilities.max(dim=0)
        self.metrics["sampling_entropy"][:] = H_samp_norm
        self.metrics["pfail_entropy"][:] = H_pfail_norm
        self.metrics["pfail_mean"][:] = p_fail.mean()

        self.metrics["sampling_top1_prob"][:] = pmax
        # self.metrics["sampling_top1_bin"][:] = imax.float() / self.num_motion
        return sampled_motion_ids

    def _uniform_sampling(self, env_ids: torch.Tensor) -> torch.Tensor:
        return (sample_uniform(0.0, 1.0,
                               (len(env_ids), ), device=self.device) *
                self.motion.num_files).long()
        ...

    # [Necessary]
    def _resample_command(self, env_ids: torch.Tensor):
        if len(env_ids) == 0:
            return

        if self.cfg.enable_adaptive_sampling:
            self.motion_idx[env_ids] = self._adaptive_sampling(env_ids)
        else:
            self.motion_idx[env_ids] = self._uniform_sampling(env_ids)
        # self.motion_idx[env_ids] = self._uniform_sampling(env_ids)
        self.motion_length[env_ids] = self.motion.file_lengths[
            self.motion_idx[env_ids]]

        if self.cfg.start_from_zero_step:
            self.time_steps[env_ids] = torch.zeros(len(env_ids),
                                                   dtype=torch.long,
                                                   device=self.device)
        else:
            self.time_steps[env_ids] = (
                sample_uniform(0.0, 1.0,
                               (len(env_ids), ), device=self.device) *
                self.motion_length[env_ids]).long()

        self.buffer_start_time[env_ids] = self.time_steps[env_ids].clone()

        # 取出 所有环境, 整个episode的reference motion data
        self._update_buffers(env_ids)

        root_pos = self.body_pos_w[:, 0].clone()
        root_ori = self.body_quat_w[:, 0].clone()
        root_lin_vel = self.body_lin_vel_w[:, 0].clone()
        root_ang_vel = self.body_ang_vel_w[:, 0].clone()

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

        joint_pos = self.joint_pos.clone()
        joint_vel = self.joint_vel.clone()

        joint_pos += sample_uniform(*self.cfg.joint_position_range,
                                    joint_pos.shape,
                                    device=self.device)
        soft_joint_pos_limits = self.robot.data.soft_joint_pos_limits[env_ids]
        joint_pos[env_ids] = torch.clip(joint_pos[env_ids],
                                        soft_joint_pos_limits[:, :, 0],
                                        soft_joint_pos_limits[:, :, 1])
        self.robot.write_joint_state_to_sim(joint_pos[env_ids],
                                            joint_vel[env_ids],
                                            env_ids=env_ids)  # type: ignore
        self.robot.write_root_state_to_sim(
            torch.cat([
                root_pos[env_ids], root_ori[env_ids], root_lin_vel[env_ids],
                root_ang_vel[env_ids]
            ],
                      dim=-1),
            env_ids=env_ids,  # type: ignore
        )

    def horizon_teacher_capture_global_state(self) -> dict[str, Any]:
        """Capture adaptive statistics shared by all physical environment rows."""
        state: dict[str, Any] = {}
        for name in self._HORIZON_TEACHER_GLOBAL_TENSORS:
            state[name] = getattr(self, name).clone()
        for name in self._HORIZON_TEACHER_GLOBAL_SCALARS:
            state[name] = float(getattr(self, name))
        return state

    def horizon_teacher_restore_global_state(self,
                                             state: dict[str, Any]) -> None:
        """Restore adaptive statistics after an isolated teacher transaction."""
        expected = set(self._HORIZON_TEACHER_GLOBAL_TENSORS)
        expected.update(self._HORIZON_TEACHER_GLOBAL_SCALARS)
        if set(state) != expected:
            raise RuntimeError(
                "invalid horizon-teacher adaptive state inventory: "
                f"expected={sorted(expected)}, got={sorted(state)}")
        for name in self._HORIZON_TEACHER_GLOBAL_TENSORS:
            getattr(self, name).copy_(state[name])
        for name in self._HORIZON_TEACHER_GLOBAL_SCALARS:
            setattr(self, name, float(state[name]))

    def horizon_teacher_prepare_pairing(self, main_env_ids: torch.Tensor,
                                        shadow_env_ids: torch.Tensor) -> None:
        """Discard shadow initialization contributions to adaptive statistics."""
        main_env_ids = self._horizon_teacher_validate_env_ids(main_env_ids)
        shadow_env_ids = self._horizon_teacher_validate_env_ids(shadow_env_ids)
        if main_env_ids.shape != shadow_env_ids.shape:
            raise ValueError("main and shadow environment ids must have equal shape")
        if len(torch.unique(torch.cat([main_env_ids, shadow_env_ids]))) != (
                len(main_env_ids) + len(shadow_env_ids)):
            raise ValueError("main and shadow environment ids must be disjoint")

        terminated = self._env.termination_manager.terminated[main_env_ids]
        motion_ids = self.motion_idx[main_env_ids]
        self.current_failed_motion_count.copy_(torch.bincount(
            motion_ids[terminated], minlength=self.num_motion))
        self.current_success_motion_count.copy_(torch.bincount(
            motion_ids[~terminated], minlength=self.num_motion))

    def horizon_teacher_compute_selected(self,
                                         env_ids: torch.Tensor,
                                         dt: float,
                                         *,
                                         update_adaptive_state: bool,
                                         allow_resample: bool) -> None:
        """Advance only selected command rows for a paired main/shadow step."""
        env_ids = self._horizon_teacher_validate_env_ids(env_ids)
        if len(env_ids) == 0:
            return

        self._update_metrics()
        self.time_left[env_ids] -= dt
        resample_env_ids = env_ids[self.time_left[env_ids] <= 0.0]
        if len(resample_env_ids):
            if not allow_resample:
                raise RuntimeError(
                    "teacher shadow command reached a resampling boundary")
            self._resample(resample_env_ids)

        self._horizon_teacher_advance_phase(env_ids,
                                            allow_resample=allow_resample)
        if update_adaptive_state:
            self._update_adaptive_statistics()

    def _horizon_teacher_validate_env_ids(
            self, env_ids: torch.Tensor) -> torch.Tensor:
        env_ids = torch.as_tensor(env_ids,
                                  device=self.device,
                                  dtype=torch.long).flatten()
        if len(torch.unique(env_ids)) != len(env_ids):
            raise ValueError("environment ids must be unique")
        if len(env_ids) and (int(env_ids.min()) < 0
                             or int(env_ids.max()) >= self.num_envs):
            raise ValueError("environment id is outside the physical scene")
        return env_ids

    def _horizon_teacher_advance_phase(self, env_ids: torch.Tensor, *,
                                       allow_resample: bool) -> None:
        if not self.cfg.freeze_motion:
            self.time_steps[env_ids] += 1
        motion_ended = self.time_steps[env_ids] >= self.motion_length[env_ids]
        if hasattr(self.cfg, "motion_end_reset") and self.cfg.motion_end_reset:
            self.motion_end_reset_env_idx[env_ids] = motion_ended
        elif bool(motion_ended.any()):
            if not allow_resample:
                raise RuntimeError(
                    "teacher shadow motion ended before the horizon completed")
            self._resample_command(env_ids[motion_ended])
        self._update_relative_targets_selected(env_ids)

    def _update_relative_targets_selected(self,
                                          env_ids: torch.Tensor) -> None:
        body_count = len(self.cfg.body_names)
        anchor_pos_w = self.anchor_pos_w[env_ids]
        anchor_quat_w = self.anchor_quat_w[env_ids]
        robot_anchor_pos_w = self.robot_anchor_pos_w[env_ids]
        robot_anchor_quat_w = self.robot_anchor_quat_w[env_ids]

        anchor_pos_w_repeat = anchor_pos_w[:, None, :].repeat(
            1, body_count, 1)
        anchor_quat_w_repeat = anchor_quat_w[:, None, :].repeat(
            1, body_count, 1)
        robot_anchor_pos_w_repeat = robot_anchor_pos_w[:, None, :].repeat(
            1, body_count, 1)
        robot_anchor_quat_w_repeat = robot_anchor_quat_w[:, None, :].repeat(
            1, body_count, 1)

        delta_pos_w = robot_anchor_pos_w_repeat.clone()
        delta_pos_w[..., 2] = anchor_pos_w_repeat[..., 2]
        delta_ori_w = yaw_quat(
            quat_mul(robot_anchor_quat_w_repeat,
                     quat_inv(anchor_quat_w_repeat)))
        self.body_quat_relative_w[env_ids] = quat_mul(
            delta_ori_w, self.body_quat_w[env_ids])
        self.body_pos_relative_w[env_ids] = delta_pos_w + quat_apply(
            delta_ori_w,
            self.body_pos_w[env_ids] - anchor_pos_w_repeat)

    def _update_adaptive_statistics(self) -> None:
        alpha = self.cfg.adaptive_alpha
        if not self.cfg.ads_stable_count:
            self.failed_motion_count = self.cfg.adaptive_alpha * self.current_failed_motion_count + (
                1 - self.cfg.adaptive_alpha) * self.failed_motion_count
            self.success_motion_count = self.cfg.adaptive_alpha * self.current_success_motion_count + (
                1 - self.cfg.adaptive_alpha) * self.success_motion_count
        else:
            tried = (self.current_failed_motion_count +
                     self.current_success_motion_count > 0.5)
            # Only decay the count when Tried.
            self.failed_motion_count = torch.where(
                tried, alpha * self.current_failed_motion_count +
                (1 - alpha) * self.failed_motion_count,
                self.failed_motion_count)
            self.success_motion_count = torch.where(
                tried, alpha * self.current_success_motion_count +
                (1 - alpha) * self.success_motion_count,
                self.success_motion_count)

        total_current_failed_count = self.current_failed_motion_count.sum(
        ).item()
        total_current_success_count = self.current_success_motion_count.sum(
        ).item()
        tried = (total_current_failed_count + total_current_success_count
                 > 0.5)
        if tried:
            self.failed_total_count = alpha * total_current_failed_count + (
                1 - alpha) * self.failed_total_count
            self.success_total_count = alpha * total_current_success_count + (
                1 - alpha) * self.success_total_count
        self.metrics["failed_total_count"][:] = self.failed_total_count
        self.metrics["success_total_count"][:] = self.success_total_count
        self.metrics["pfail_total"][:] = self.failed_total_count / (
            self.failed_total_count + self.success_total_count + 1e-8)

        # print(
        #     "DEBUG: failed_total_count: ", self.failed_total_count, "success_total_count: ", self.success_total_count,
        #     "pfail_total: ", self.metrics["pfail_total"][0]
        # )

        self.current_failed_motion_count.zero_()
        self.current_success_motion_count.zero_()

    # [Necessary]
    def _update_command(self):
        env_ids = torch.arange(self.num_envs,
                               dtype=torch.long,
                               device=self.device)
        self._horizon_teacher_advance_phase(env_ids, allow_resample=True)
        self._update_adaptive_statistics()

    # [Necessary]
    def _set_debug_vis_impl(self, debug_vis: bool):
        if debug_vis:
            if not hasattr(self, "current_anchor_visualizer"):
                red_color = sim_utils.PreviewSurfaceCfg(diffuse_color=(0.8,
                                                                       0.2,
                                                                       0.2))
                green_color = sim_utils.PreviewSurfaceCfg(diffuse_color=(0.2,
                                                                         0.8,
                                                                         0.2))
                current_anchor_visualizer_cfg: VisualizationMarkersCfg = VisualizationMarkersCfg(
                    prim_path="/Visuals/Command/current/anchor",
                    markers={
                        "hit":
                        sim_utils.SphereCfg(
                            radius=0.05,
                            visual_material=red_color,
                        ),
                    },
                )
                goal_anchor_visualizer_cfg: VisualizationMarkersCfg = VisualizationMarkersCfg(
                    prim_path="/Visuals/Command/goal/anchor",
                    markers={
                        "hit":
                        sim_utils.SphereCfg(
                            radius=0.05,
                            visual_material=green_color,
                        ),
                    },
                )

                self.current_anchor_visualizer = VisualizationMarkers(
                    current_anchor_visualizer_cfg)
                self.goal_anchor_visualizer = VisualizationMarkers(
                    goal_anchor_visualizer_cfg)

                self.current_body_visualizers = []
                self.goal_body_visualizers = []
                for name in self.cfg.body_names:
                    current_body_visualizer_cfg: VisualizationMarkersCfg = VisualizationMarkersCfg(
                        prim_path="/Visuals/Command/current/" + name,
                        markers={
                            "target":
                            sim_utils.SphereCfg(
                                radius=0.02,
                                visual_material=red_color,
                            ),
                        },
                    )
                    goal_body_visualizer_cfg: VisualizationMarkersCfg = VisualizationMarkersCfg(
                        prim_path="/Visuals/Command/goal/" + name,
                        markers={
                            "target":
                            sim_utils.SphereCfg(
                                radius=0.02,
                                visual_material=green_color,
                            ),
                        },
                    )
                    self.current_body_visualizers.append(
                        VisualizationMarkers(current_body_visualizer_cfg))
                    self.goal_body_visualizers.append(
                        VisualizationMarkers(goal_body_visualizer_cfg))

            self.current_anchor_visualizer.set_visibility(True)
            self.goal_anchor_visualizer.set_visibility(True)
            for i in range(len(self.cfg.body_names)):
                self.current_body_visualizers[i].set_visibility(True)
                self.goal_body_visualizers[i].set_visibility(True)

        else:
            if hasattr(self, "current_anchor_visualizer"):
                self.current_anchor_visualizer.set_visibility(False)
                self.goal_anchor_visualizer.set_visibility(False)
                for i in range(len(self.cfg.body_names)):
                    self.current_body_visualizers[i].set_visibility(False)
                    self.goal_body_visualizers[i].set_visibility(False)

    # [Necessary]
    def _debug_vis_callback(self, event):
        if not self.robot.is_initialized:
            return

        self.current_anchor_visualizer.visualize(self.robot_anchor_pos_w,
                                                 self.robot_anchor_quat_w)
        self.goal_anchor_visualizer.visualize(self.anchor_pos_w,
                                              self.anchor_quat_w)

        for i in range(len(self.cfg.body_names)):
            self.current_body_visualizers[i].visualize(
                self.robot_body_pos_w[:, i], self.robot_body_quat_w[:, i])
            self.goal_body_visualizers[i].visualize(
                self.body_pos_relative_w[:, i], self.body_quat_relative_w[:,
                                                                          i])


@configclass
class MotionCommandCfg(CommandTermCfg):
    """Configuration for the motion command."""

    class_type: type = MotionCommand

    asset_name: str = MISSING  # type: ignore

    # motion_file: str = MISSING
    motion_files: list[str] = MISSING  # type: ignore

    anchor_body_name: str = MISSING  # type: ignore
    body_names: list[str] = MISSING  # type: ignore

    pose_range: dict[str, tuple[float, float]] = {}
    velocity_range: dict[str, tuple[float, float]] = {}

    joint_position_range: tuple[float, float] = (-0.52, 0.52)

    # Future steps configuration for N-step lookahead
    future_steps: int = 1

    # Start from zero configuration
    start_from_zero_step: bool = False

    # [[Rewrite Adaptive Sampling, not BeyondMimic's Mechanism]]
    enable_adaptive_sampling: bool = False
    ads_type: str = "v1"
    ads_stable_count: bool = True
    adaptive_length_weighted: bool = False
    adaptive_uniform_ratio: float = 0.1
    adaptive_alpha: float = 0.001
    adaptive_beta: float = 0.5

    # Random Static
    random_static_prob: float = -1.0

    # Motion end reset
    motion_end_reset: bool = False
    # Freeze motion
    freeze_motion: bool = False
