"""Build policy observations from deployable G1 sensor channels only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import torch

from diffusion_policy.utils.traj_utils import quat_rotate


@dataclass(frozen=True)
class DeployableFKObservationConfig:
    control_dt: float = 0.02
    initial_root_position_m: tuple[float, float, float] = (0.0, 0.0, 0.8)
    initial_yaw_rad: float = 0.0


class DeployableFKObservationBuilder:
    """Replace privileged flat-observation fields using sensor-estimated FK.

    The only raw observation slices read by this class are joint position,
    joint velocity, projected gravity, base linear/angular velocity, and last
    action. Base linear and angular velocity are declared in the body frame.
    Roll/pitch come from the IMU gravity vector, yaw is integrated from the
    IMU angular velocity, and position is integrated from estimated velocity.
    """

    OBS_DIM = 494
    JOINT_POS = slice(390, 419)
    JOINT_VEL = slice(419, 448)
    PROJECTED_GRAVITY = slice(456, 459)
    BASE_LIN_VEL = slice(459, 462)
    BASE_ANG_VEL = slice(462, 465)
    LAST_ACTIONS = slice(465, 494)
    ALLOWED_SLICES = (
        ("joint_pos", JOINT_POS),
        ("joint_vel", JOINT_VEL),
        ("projected_gravity", PROJECTED_GRAVITY),
        ("base_lin_vel", BASE_LIN_VEL),
        ("base_ang_vel", BASE_ANG_VEL),
        ("last_actions", LAST_ACTIONS),
    )

    def __init__(self, fk_calculator, config: DeployableFKObservationConfig) -> None:
        if config.control_dt <= 0.0:
            raise ValueError("deployable FK control_dt must be positive")
        self.fk_calculator = fk_calculator
        self.config = config
        self._base_position: torch.Tensor | None = None
        self._yaw: torch.Tensor | None = None
        self._initialized: torch.Tensor | None = None

    @classmethod
    def provenance(cls) -> dict[str, object]:
        return {
            "schema_version": "deployable-fk-observation-v1",
            "policy_input_sources": [name for name, _ in cls.ALLOWED_SLICES],
            "forbidden_policy_input_sources": [
                "simulator_body_position",
                "simulator_body_rotation",
                "simulator_body_linear_velocity",
                "simulator_body_angular_velocity",
                "simulator_root_position",
                "simulator_root_rotation",
                "reference_future_state",
                "contacts",
            ],
            "frames": {
                "projected_gravity": "body",
                "base_linear_velocity": "body",
                "base_angular_velocity": "body",
                "fk_body_position": "estimated_world",
                "fk_body_linear_velocity": "estimated_world",
            },
            "base_orientation": {
                "roll_pitch": "imu_projected_gravity",
                "yaw": "integrated_imu_angular_velocity_world_z",
            },
            "base_position": "integrated_body_linear_velocity_from_fixed_reset_calibration",
        }

    @staticmethod
    def _as_tensor(value, like: torch.Tensor) -> torch.Tensor:
        if torch.is_tensor(value):
            return value.to(device=like.device, dtype=like.dtype)
        return torch.as_tensor(value, device=like.device, dtype=like.dtype)

    @staticmethod
    def _orientation(projected_gravity: torch.Tensor, yaw: torch.Tensor) -> torch.Tensor:
        gravity = projected_gravity / projected_gravity.norm(dim=-1, keepdim=True).clamp_min(1e-6)
        pitch = torch.asin(gravity[:, 0].clamp(-1.0, 1.0))
        roll = torch.atan2(-gravity[:, 1], -gravity[:, 2])
        half_roll, half_pitch, half_yaw = roll * 0.5, pitch * 0.5, yaw * 0.5
        cr, sr = torch.cos(half_roll), torch.sin(half_roll)
        cp, sp = torch.cos(half_pitch), torch.sin(half_pitch)
        cy, sy = torch.cos(half_yaw), torch.sin(half_yaw)
        return torch.stack((
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ), dim=-1)

    def _ensure_state(self, raw_obs: torch.Tensor) -> None:
        if raw_obs.ndim != 2 or raw_obs.shape[1] < self.OBS_DIM:
            raise ValueError(f"expected flat observations [N, >= {self.OBS_DIM}], got {tuple(raw_obs.shape)}")
        count = raw_obs.shape[0]
        if self._base_position is not None and self._base_position.shape[0] == count:
            return
        initial = torch.tensor(
            self.config.initial_root_position_m, device=raw_obs.device, dtype=raw_obs.dtype
        )
        self._base_position = initial.repeat(count, 1)
        self._yaw = torch.full(
            (count,), float(self.config.initial_yaw_rad), device=raw_obs.device, dtype=raw_obs.dtype
        )
        self._initialized = torch.zeros(count, dtype=torch.bool, device=raw_obs.device)

    def reset(self, raw_obs: torch.Tensor, env_indices: Iterable[int] | None = None) -> torch.Tensor:
        self._ensure_state(raw_obs)
        assert self._base_position is not None and self._yaw is not None and self._initialized is not None
        indices = list(range(raw_obs.shape[0])) if env_indices is None else [int(value) for value in env_indices]
        if not indices:
            raise ValueError("deployable FK reset requires at least one environment index")
        index = torch.tensor(indices, device=raw_obs.device, dtype=torch.long)
        initial = torch.tensor(
            self.config.initial_root_position_m, device=raw_obs.device, dtype=raw_obs.dtype
        )
        self._base_position[index] = initial
        self._yaw[index] = float(self.config.initial_yaw_rad)
        self._initialized[index] = True
        return self._build(raw_obs)

    def update(self, raw_obs: torch.Tensor) -> torch.Tensor:
        self._ensure_state(raw_obs)
        assert self._base_position is not None and self._yaw is not None and self._initialized is not None
        if not bool(self._initialized.all().item()):
            missing = torch.nonzero(~self._initialized, as_tuple=False).flatten().tolist()
            raise RuntimeError(f"deployable FK state was not reset for environments {missing}")
        gravity = raw_obs[:, self.PROJECTED_GRAVITY]
        orientation = self._orientation(gravity, self._yaw)
        angular_world = quat_rotate(orientation, raw_obs[:, self.BASE_ANG_VEL])
        self._yaw = self._yaw + angular_world[:, 2] * float(self.config.control_dt)
        orientation = self._orientation(gravity, self._yaw)
        linear_world = quat_rotate(orientation, raw_obs[:, self.BASE_LIN_VEL])
        self._base_position = self._base_position + linear_world * float(self.config.control_dt)
        return self._build(raw_obs, orientation=orientation, linear_world=linear_world, angular_world=angular_world)

    def _build(
        self,
        raw_obs: torch.Tensor,
        *,
        orientation: torch.Tensor | None = None,
        linear_world: torch.Tensor | None = None,
        angular_world: torch.Tensor | None = None,
    ) -> torch.Tensor:
        assert self._base_position is not None and self._yaw is not None
        gravity = raw_obs[:, self.PROJECTED_GRAVITY]
        orientation = self._orientation(gravity, self._yaw) if orientation is None else orientation
        linear_world = (
            quat_rotate(orientation, raw_obs[:, self.BASE_LIN_VEL])
            if linear_world is None else linear_world
        )
        angular_world = (
            quat_rotate(orientation, raw_obs[:, self.BASE_ANG_VEL])
            if angular_world is None else angular_world
        )
        result: Mapping[str, object] = self.fk_calculator.compute_fk(
            joint_pos=raw_obs[:, self.JOINT_POS],
            joint_vel=raw_obs[:, self.JOINT_VEL],
            imu_pose=orientation,
            imu_gyro=angular_world,
            base_lin_vel=linear_world,
            base_pos=self._base_position,
            isaaclab_q_order=True,
        )
        body_pos = self._as_tensor(result["body_pos"], raw_obs)
        body_lin_vel = self._as_tensor(result["body_lin_vel"], raw_obs)
        if body_pos.shape != (raw_obs.shape[0], 30, 3) or body_lin_vel.shape != body_pos.shape:
            raise ValueError("G1 FK returned an incompatible body tensor shape")

        policy_obs = torch.zeros_like(raw_obs)
        for _, field in self.ALLOWED_SLICES:
            policy_obs[:, field] = raw_obs[:, field]
        policy_obs[:, :90] = body_pos.reshape(raw_obs.shape[0], -1)
        body_rot = torch.zeros(raw_obs.shape[0], 30, 4, device=raw_obs.device, dtype=raw_obs.dtype)
        body_rot[:, :, 0] = 1.0
        body_rot[:, 0] = orientation
        policy_obs[:, 90:210] = body_rot.reshape(raw_obs.shape[0], -1)
        policy_obs[:, 210:300] = body_lin_vel.reshape(raw_obs.shape[0], -1)
        body_ang_vel = torch.zeros(raw_obs.shape[0], 30, 3, device=raw_obs.device, dtype=raw_obs.dtype)
        body_ang_vel[:, 0] = angular_world
        policy_obs[:, 300:390] = body_ang_vel.reshape(raw_obs.shape[0], -1)
        policy_obs[:, 448:451] = self._base_position
        policy_obs[:, 451:455] = orientation
        return policy_obs


class ProprioceptiveObservationBuilder:
    """Expose only deployable proprioceptive channels to FK-free policies."""

    OBS_DIM = DeployableFKObservationBuilder.OBS_DIM
    ALLOWED_SLICES = DeployableFKObservationBuilder.ALLOWED_SLICES

    @classmethod
    def build(cls, raw_obs: torch.Tensor) -> torch.Tensor:
        if raw_obs.ndim != 2 or raw_obs.shape[1] < cls.OBS_DIM:
            raise ValueError(f"expected flat observations [N, >= {cls.OBS_DIM}], got {tuple(raw_obs.shape)}")
        policy_obs = torch.zeros_like(raw_obs)
        for _, field in cls.ALLOWED_SLICES:
            policy_obs[:, field] = raw_obs[:, field]
        return policy_obs

    @classmethod
    def provenance(cls) -> dict[str, object]:
        return {
            "schema_version": "proprioceptive-observation-v1",
            "policy_input_sources": [name for name, _ in cls.ALLOWED_SLICES],
            "forbidden_policy_input_sources": [
                "simulator_body_position",
                "simulator_body_rotation",
                "simulator_body_linear_velocity",
                "simulator_body_angular_velocity",
                "simulator_root_position",
                "simulator_root_rotation",
                "reference_future_state",
                "contacts",
            ],
            "body_and_root_placeholders": "zero",
            "forward_kinematics": "disabled",
        }
