"""
FK Input Noise Simulator for Sim2Real Gap Reduction.

Simulates realistic sensor noise on FK inputs to make data collection
observations match what the policy will receive on real hardware:

- IMU orientation: yaw drift (Gauss-Markov) + per-axis jitter (white Gaussian)
- Joint encoders: additive Gaussian + optional quantization
- Gyro: constant per-episode bias + white noise
- Base velocity: OU drift (Gauss-Markov)
- Base position: 2nd-order random walk (odometry drift)

All noise processes are batch-aware [B, ...] and support per-environment
reset when episodes end.

Usage:
    model = FKNoiseModel(cfg, num_envs=1000, device="cuda")
    noisy_quat = model.corrupt_imu_orientation(root_quat)
    noisy_jpos = model.corrupt_joint_positions(joint_pos)
    ...
    model.step()  # advance temporal processes

    # On episode end for env i:
    model.reset_env(i)
"""

from __future__ import annotations

import numpy as np
import torch
from typing import Optional, Dict


def quat_wxyz_to_rpy(q: torch.Tensor) -> torch.Tensor:
    """Convert quaternion [..., 4] wxyz → [..., 3] roll-pitch-yaw."""
    qw, qx, qy, qz = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    roll = torch.atan2(2 * (qw * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy))
    sinp = 2 * (qw * qy - qz * qx)
    pitch = torch.asin(torch.clamp(sinp, -1.0, 1.0))
    yaw = torch.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
    return torch.stack([roll, pitch, yaw], dim=-1)


def rpy_to_quat_wxyz(rpy: torch.Tensor) -> torch.Tensor:
    """Convert [..., 3] roll-pitch-yaw → quaternion [..., 4] wxyz."""
    roll, pitch, yaw = rpy[..., 0], rpy[..., 1], rpy[..., 2]
    cr = torch.cos(roll * 0.5)
    sr = torch.sin(roll * 0.5)
    cp = torch.cos(pitch * 0.5)
    sp = torch.sin(pitch * 0.5)
    cy = torch.cos(yaw * 0.5)
    sy = torch.sin(yaw * 0.5)
    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    return torch.stack([qw, qx, qy, qz], dim=-1)


class GaussMarkovProcess:
    """
    1st-order Gauss-Markov (OU-like) process: x_{t+1} = x_t * decay + sigma * sqrt(1-decay^2) * N(0,1).

    Steady-state std = sigma. Correlation time governed by decay = exp(-dt/tau).

    Shape: [B, D] — independent processes per environment and dimension.
    """

    def __init__(
        self,
        batch_size: int,
        dim: int,
        sigma: float,
        tau: float,
        dt: float = 0.02,
        device: torch.device = torch.device("cpu"),
        dtype: torch.dtype = torch.float32,
    ):
        self.batch_size = batch_size
        self.dim = dim
        self.sigma = sigma
        self.decay = float(np.exp(-dt / tau)) if tau > 0 else 0.0
        self.device = device
        self.dtype = dtype
        self.state: torch.Tensor = torch.zeros(batch_size, dim, device=device, dtype=dtype)
        # Warm-start: initialize from steady-state distribution
        self.state = sigma * torch.randn(batch_size, dim, device=device, dtype=dtype)

    def sample(self) -> torch.Tensor:
        """Return current state and advance one step."""
        current = self.state.clone()
        noise = (self.sigma * np.sqrt(max(1.0 - self.decay ** 2, 0.0))
                 * torch.randn(self.batch_size, self.dim, device=self.device, dtype=self.dtype))
        self.state = self.state * self.decay + noise
        return current

    def reset_env(self, env_idx: int):
        """Reset a single environment's state to steady-state draw."""
        self.state[env_idx] = self.sigma * torch.randn(self.dim, device=self.device, dtype=self.dtype)


class RandomWalkProcess:
    """
    Discrete random walk: x_{t+1} = x_t + sigma * sqrt(dt) * N(0,1).

    Shape: [B, D].
    """

    def __init__(
        self,
        batch_size: int,
        dim: int,
        sigma: float,
        dt: float = 0.02,
        device: torch.device = torch.device("cpu"),
        dtype: torch.dtype = torch.float32,
    ):
        self.batch_size = batch_size
        self.dim = dim
        self.sigma = sigma
        self.sqrt_dt = np.sqrt(dt)
        self.device = device
        self.dtype = dtype
        self.state: torch.Tensor = torch.zeros(batch_size, dim, device=device, dtype=dtype)

    def sample(self) -> torch.Tensor:
        """Return current state and advance one step."""
        current = self.state.clone()
        noise = (self.sigma * self.sqrt_dt
                 * torch.randn(self.batch_size, self.dim, device=self.device, dtype=self.dtype))
        self.state = self.state + noise
        return current

    def reset_env(self, env_idx: int):
        """Reset a single environment's state to zero."""
        self.state[env_idx] = 0.0


class FKNoiseModel:
    """
    Simulates realistic sensor noise on FK inputs.

    Noise channels (each independently configurable):
    1. IMU orientation: yaw drift (Gauss-Markov) + per-axis jitter
    2. Joint encoders: additive Gaussian + optional quantization
    3. Gyro: per-episode constant bias + white noise
    4. Base linear velocity: Gauss-Markov drift
    5. Base position: 2nd-order random walk (velocity bias → position drift)
    """

    def __init__(
        self,
        cfg,
        num_envs: int,
        dt: float = 0.02,
        device: torch.device = torch.device("cpu"),
        dtype: torch.dtype = torch.float32,
    ):
        """
        Args:
            cfg: OmegaConf/DictConfig for fk.noise section, or a plain dict.
            num_envs: Number of parallel environments (batch size).
            dt: Simulation timestep in seconds (default 0.02 = 50Hz).
            device: Torch device.
            dtype: Torch dtype.
        """
        self.num_envs = num_envs
        self.dt = dt
        self.device = device
        self.dtype = dtype

        # --- Helper to read cfg values (supports both OmegaConf and dict) ---
        def _get(section, key, default):
            if section is None:
                return default
            val = section.get(key, default)
            # OmegaConf may return None for missing keys
            return val if val is not None else default

        # shorthand
        self._enabled = lambda section, key="enable": _get(section, key, False)

        # --- IMU orientation noise ---
        imu_cfg = cfg.get("imu_orientation") if cfg else None
        self.imu_enabled = self._enabled(imu_cfg)
        self.imu_yaw_drift: Optional[GaussMarkovProcess] = None
        self.imu_yaw_jitter_sigma: float = 0.0
        self.imu_rp_jitter_sigma: float = 0.0

        if self.imu_enabled:
            yaw_cfg = imu_cfg.get("yaw_drift") if isinstance(imu_cfg, dict) else getattr(imu_cfg, "yaw_drift", None)
            if yaw_cfg and _get(yaw_cfg, "enable", True):
                self.imu_yaw_drift = GaussMarkovProcess(
                    batch_size=num_envs,
                    dim=1,  # yaw only
                    sigma=float(_get(yaw_cfg, "sigma", 0.0005)),
                    tau=float(_get(yaw_cfg, "tau", 60.0)),
                    dt=dt,
                    device=device,
                    dtype=dtype,
                )
            self.imu_yaw_jitter_sigma = float(_get(imu_cfg, "yaw_jitter_sigma", 0.003))
            self.imu_rp_jitter_sigma = float(_get(imu_cfg, "roll_pitch_jitter_sigma", 0.001))

        # --- Joint encoder noise ---
        jnt_cfg = cfg.get("joint_encoder") if cfg else None
        self.joint_enabled = self._enabled(jnt_cfg)
        self.joint_std: float = 0.0
        self.joint_qstep: float = 0.0
        self.joint_calib_sigma: float = 0.0
        self._joint_calib_bias: Optional[torch.Tensor] = None  # [B, 29]

        if self.joint_enabled:
            self.joint_std = float(_get(jnt_cfg, "white_noise_sigma", 0.001))
            self.joint_qstep = float(_get(jnt_cfg, "quantization_step", 0.0))
            self.joint_calib_sigma = float(_get(jnt_cfg, "calibration_bias_sigma", 0.01))
            if self.joint_calib_sigma > 0:
                self._joint_calib_bias = self.joint_calib_sigma * torch.randn(
                    num_envs, 29, device=device, dtype=dtype,
                )

        # --- Gyro noise ---
        gyro_cfg = cfg.get("gyro") if cfg else None
        self.gyro_enabled = self._enabled(gyro_cfg)
        self.gyro_bias_sigma: float = 0.0
        self.gyro_white_sigma: float = 0.0
        self._gyro_bias: Optional[torch.Tensor] = None  # [B, 3]

        if self.gyro_enabled:
            self.gyro_bias_sigma = float(_get(gyro_cfg, "bias_sigma", 0.005))
            self.gyro_white_sigma = float(_get(gyro_cfg, "white_noise_sigma", 0.005))
            if self.gyro_bias_sigma > 0:
                self._gyro_bias = self.gyro_bias_sigma * torch.randn(
                    num_envs, 3, device=device, dtype=dtype,
                )

        # --- Base velocity noise ---
        vel_cfg = cfg.get("base_velocity") if cfg else None
        self.vel_enabled = self._enabled(vel_cfg)
        self.vel_drift: Optional[GaussMarkovProcess] = None

        if self.vel_enabled:
            drift_cfg = vel_cfg.get("drift") if isinstance(vel_cfg, dict) else getattr(vel_cfg, "drift", None)
            if drift_cfg and _get(drift_cfg, "enable", True):
                self.vel_drift = GaussMarkovProcess(
                    batch_size=num_envs,
                    dim=3,
                    sigma=float(_get(drift_cfg, "sigma", 0.05)),
                    tau=float(_get(drift_cfg, "tau", 2.0)),
                    dt=dt,
                    device=device,
                    dtype=dtype,
                )

        # --- Base position noise (2nd-order random walk) ---
        pos_cfg = cfg.get("base_position") if cfg else None
        self.pos_enabled = self._enabled(pos_cfg)
        self.pos_vel_bias: Optional[torch.Tensor] = None  # [B, 3] velocity bias state
        self.pos_bias: Optional[torch.Tensor] = None       # [B, 3] accumulated position bias
        self.pos_sigma: float = 0.0

        if self.pos_enabled:
            drift_cfg = pos_cfg.get("drift") if isinstance(pos_cfg, dict) else getattr(pos_cfg, "drift", None)
            if drift_cfg and _get(drift_cfg, "enable", True):
                self.pos_sigma = float(_get(drift_cfg, "sigma", 0.02))
                self.pos_vel_bias = torch.zeros(num_envs, 3, device=device, dtype=dtype)
                self.pos_bias = torch.zeros(num_envs, 3, device=device, dtype=dtype)

        # Summary
        any_enabled = any([
            self.imu_enabled, self.joint_enabled, self.gyro_enabled,
            self.vel_enabled, self.pos_enabled,
        ])
        if any_enabled:
            parts = []
            if self.imu_enabled:
                parts.append("IMU-orientation")
            if self.joint_enabled:
                parts.append("joint-encoder")
            if self.gyro_enabled:
                parts.append("gyro")
            if self.vel_enabled:
                parts.append("base-velocity")
            if self.pos_enabled:
                parts.append("base-position")
            print(f"[FKNoise] Enabled channels: {', '.join(parts)}")
        else:
            print("[FKNoise] All noise channels disabled (no-op)")

    # ------------------------------------------------------------------
    # Public corruption API
    # ------------------------------------------------------------------

    def corrupt_imu_orientation(self, root_quat: torch.Tensor) -> torch.Tensor:
        """
        Apply IMU orientation noise.

        Args:
            root_quat: [B, 4] wxyz quaternion (ground truth).

        Returns:
            [B, 4] wxyz quaternion with noise applied.
        """
        if not self.imu_enabled:
            return root_quat

        rpy = quat_wxyz_to_rpy(root_quat)  # [B, 3]

        # Yaw drift (Gauss-Markov)
        if self.imu_yaw_drift is not None:
            yaw_drift = self.imu_yaw_drift.sample()  # [B, 1]
            rpy = rpy.clone()
            rpy[:, 2] = rpy[:, 2] + yaw_drift.squeeze(-1)

        # Jitter (white Gaussian, per-axis)
        jitter = torch.randn_like(rpy)
        jitter[:, 0] *= self.imu_rp_jitter_sigma   # roll
        jitter[:, 1] *= self.imu_rp_jitter_sigma   # pitch
        jitter[:, 2] *= self.imu_yaw_jitter_sigma  # yaw (typically larger)
        rpy = rpy + jitter

        return rpy_to_quat_wxyz(rpy)

    def corrupt_joint_positions(self, joint_pos: torch.Tensor) -> torch.Tensor:
        """
        Apply encoder quantization and calibration bias.

        Args:
            joint_pos: [B, 29] joint positions (rad).

        Returns:
            [B, 29] noisy joint positions.
        """
        if not self.joint_enabled:
            return joint_pos

        result = joint_pos.clone()

        # Calibration bias (static per episode)
        if self._joint_calib_bias is not None:
            result = result + self._joint_calib_bias

        # White noise
        if self.joint_std > 0:
            result = result + self.joint_std * torch.randn_like(result)

        # Quantization
        if self.joint_qstep > 0:
            result = torch.round(result / self.joint_qstep) * self.joint_qstep

        return result

    def corrupt_gyro(self, root_ang_vel: torch.Tensor) -> torch.Tensor:
        """
        Apply gyro bias and white noise.

        Args:
            root_ang_vel: [B, 3] angular velocity (rad/s).

        Returns:
            [B, 3] noisy angular velocity.
        """
        if not self.gyro_enabled:
            return root_ang_vel

        result = root_ang_vel.clone()

        # Constant per-episode bias
        if self._gyro_bias is not None:
            result = result + self._gyro_bias

        # White noise
        if self.gyro_white_sigma > 0:
            result = result + self.gyro_white_sigma * torch.randn_like(result)

        return result

    def corrupt_base_velocity(self, root_lin_vel: torch.Tensor) -> torch.Tensor:
        """
        Apply velocity estimation drift.

        Args:
            root_lin_vel: [B, 3] base linear velocity (m/s).

        Returns:
            [B, 3] noisy base linear velocity.
        """
        if not self.vel_enabled or self.vel_drift is None:
            return root_lin_vel

        drift = self.vel_drift.sample()  # [B, 3]
        return root_lin_vel + drift

    def corrupt_base_position(self, root_pos: torch.Tensor) -> torch.Tensor:
        """
        Apply 2nd-order random walk for odometry position drift.

        Args:
            root_pos: [B, 3] base position (m).

        Returns:
            [B, 3] noisy base position.
        """
        if not self.pos_enabled or self.pos_vel_bias is None or self.pos_bias is None:
            return root_pos

        # Velocity bias random walk
        vel_noise = (self.pos_sigma * np.sqrt(self.dt)
                     * torch.randn(self.num_envs, 3, device=self.device, dtype=self.dtype))
        self.pos_vel_bias = self.pos_vel_bias + vel_noise

        # Position bias = integral of velocity bias
        self.pos_bias = self.pos_bias + self.pos_vel_bias * self.dt

        return root_pos + self.pos_bias

    def step(self):
        """
        Advance all temporal noise processes.

        Called once per simulation step. Processes that use internal
        sampling (GaussMarkov, RandomWalk) are advanced inside their
        respective corrupt_*() methods, so this is a no-op if all
        processes are sampled during corruption.

        This is a hook for any future global step logic.
        """
        pass

    # ------------------------------------------------------------------
    # Episode reset
    # ------------------------------------------------------------------

    def reset_env(self, env_idx: int):
        """
        Reset noise state for a single environment (called on episode end).

        Args:
            env_idx: Integer index of the environment to reset.
        """
        if self.imu_yaw_drift is not None:
            self.imu_yaw_drift.reset_env(env_idx)
        if self.vel_drift is not None:
            self.vel_drift.reset_env(env_idx)
        if self._gyro_bias is not None and self.gyro_bias_sigma > 0:
            self._gyro_bias[env_idx] = self.gyro_bias_sigma * torch.randn(
                3, device=self.device, dtype=self.dtype,
            )
        if self._joint_calib_bias is not None and self.joint_calib_sigma > 0:
            self._joint_calib_bias[env_idx] = self.joint_calib_sigma * torch.randn(
                29, device=self.device, dtype=self.dtype,
            )
        if self.pos_vel_bias is not None:
            self.pos_vel_bias[env_idx] = 0.0
        if self.pos_bias is not None:
            self.pos_bias[env_idx] = 0.0

    # ------------------------------------------------------------------
    # Config export (for metadata)
    # ------------------------------------------------------------------

    def config_summary(self) -> Dict:
        """Return a dict summarising active noise parameters for metadata."""
        summary = {
            "imu_enabled": self.imu_enabled,
            "joint_enabled": self.joint_enabled,
            "gyro_enabled": self.gyro_enabled,
            "vel_enabled": self.vel_enabled,
            "pos_enabled": self.pos_enabled,
        }
        if self.imu_enabled:
            summary["imu_yaw_jitter_sigma"] = self.imu_yaw_jitter_sigma
            summary["imu_rp_jitter_sigma"] = self.imu_rp_jitter_sigma
            if self.imu_yaw_drift is not None:
                summary["imu_yaw_drift_sigma"] = self.imu_yaw_drift.sigma
                summary["imu_yaw_drift_tau"] = float(np.log(self.imu_yaw_drift.decay) * (-self.dt))
        if self.joint_enabled:
            summary["joint_std"] = self.joint_std
            summary["joint_qstep"] = self.joint_qstep
            summary["joint_calib_sigma"] = self.joint_calib_sigma
        if self.gyro_enabled:
            summary["gyro_bias_sigma"] = self.gyro_bias_sigma
            summary["gyro_white_sigma"] = self.gyro_white_sigma
        if self.vel_enabled and self.vel_drift is not None:
            summary["vel_drift_sigma"] = self.vel_drift.sigma
        if self.pos_enabled:
            summary["pos_drift_sigma"] = self.pos_sigma
        return summary
