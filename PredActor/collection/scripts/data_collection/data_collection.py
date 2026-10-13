"""
Script to collect G1 dataset for diffuse_cloc training from RLTracker environment.

This script collects data from a trained tracking policy and saves it in zarr format
compatible with g1_offline_dataset.py and offline_dataset.py.

Required data fields (matching OfflineDataset in offline_dataset.py):
    - act: joint position actions [T, 29]
    - body_ang_vel: body angular velocities [T, 30, 3]
    - body_lin_vel: body linear velocities [T, 30, 3]
    - body_pos: body positions [T, 30, 3]
    - body_rot: body rotations (quaternions) [T, 30, 4]
    - joint_pos: joint positions [T, 29]
    - joint_vel: joint velocities [T, 29]
    - root_pos: root position [T, 3]
    - root_rot: root rotation (quaternion) [T, 4]
    - projected_gravity: projected gravity vector [T, 3]
    - base_lin_vel: base linear velocity [T, 3]
    - base_ang_vel: base angular velocity [T, 3]
    - last_actions: previous actions [T, 29]

Action Noise Injection:
    Following BeyondMimic, we inject temporally correlated OU noise during rollout:
    η_{t+1} = η_t + θ(μ - η_t)Δt + σ√Δt ε_t
    
    This creates state diversity and collects corrective actions for robustness.

Collection Modes:
    - standard: Random sampling with quality filters (original behavior)
    - deterministic: M motions × N samples = M*N episodes, full coverage
"""

import glob
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict

import hydra
from omegaconf import DictConfig, OmegaConf
import numpy as np
import torch
import yaml
from tqdm import tqdm

# Add paths for imports
ROOT_DIR = str(Path(__file__).parent)
sys.path.append(ROOT_DIR)

from diffusion_policy.utils.replay_buffer import ReplayBuffer
from diffusion_policy.utils.g1fk_torch import build_fk_calculator
from fk_noise import FKNoiseModel


def _seed_collection_runtime(seed: int) -> None:
    """Seed every RNG used before the IsaacLab environment is constructed."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    print(f"[COLLECTION_SEED] seed={seed}")


def _first_nonfinite_tensor(value, prefix: str = "") -> str | None:
    """Return a path for the first non-finite tensor in a nested rollout value."""
    if torch.is_tensor(value):
        return None if torch.isfinite(value).all().item() else (prefix or "tensor")
    if isinstance(value, dict):
        for key, item in value.items():
            path = _first_nonfinite_tensor(item, f"{prefix}.{key}" if prefix else str(key))
            if path is not None:
                return path
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            path = _first_nonfinite_tensor(item, f"{prefix}[{index}]")
            if path is not None:
                return path
    return None


def _parse_diffusion_obs(
    diffusion_obs_concat: torch.Tensor,
    split_sizes: list,
    fk_calculator=None,
    fk_noise_model=None,
    fk_noise_cfg=None,
):
    """Parse the 691-dim diffusion observation into robot_state dict.

    Observation layout (22 groups):
      body_pos(90) + body_rot(120) + body_lin_vel(90) + body_ang_vel(90)
      + joint_pos(29) + joint_vel(29) + root_pos(3) + root_rot(4) + motion_idx(1)
      + projected_gravity(3) + base_lin_vel(3) + base_ang_vel(3) + last_actions(29)
      + motion_ref_root_pos(3) + motion_ref_root_rot(4) + motion_ref_root_lin_vel(3)
      + motion_ref_root_ang_vel(3)
      + motion_ref_joint_pos(29) + motion_ref_joint_vel(29)
      + motion_ref_body_pos(42) + motion_ref_body_vel(42) + motion_ref_body_pos_rel(42)
      = 691 dims

    Returns (robot_state, robot_state_np) — torch and numpy versions.
    """
    obs_list = torch.split(diffusion_obs_concat, split_sizes, dim=-1)
    robot_state = {
        "body_pos": obs_list[0].reshape(-1, 30, 3),
        "body_rot": obs_list[1].reshape(-1, 30, 4),
        "body_lin_vel": obs_list[2].reshape(-1, 30, 3),
        "body_ang_vel": obs_list[3].reshape(-1, 30, 3),
        "joint_pos": obs_list[4],
        "joint_vel": obs_list[5],
        "root_pos": obs_list[6],
        "root_rot": obs_list[7],
        "motion_idx": obs_list[8].squeeze(-1).long(),
        "projected_gravity": obs_list[9],
        "base_lin_vel": obs_list[10],
        "base_ang_vel": obs_list[11],
        "last_actions": obs_list[12],
        "motion_ref_root_pos": obs_list[13],
        "motion_ref_root_rot": obs_list[14],
        "motion_ref_root_lin_vel": obs_list[15],
        "motion_ref_root_ang_vel": obs_list[16],
        "motion_ref_joint_pos": obs_list[17],
        "motion_ref_joint_vel": obs_list[18],
        "motion_ref_body_pos": obs_list[19].reshape(-1, 14, 3),
        "motion_ref_body_vel": obs_list[20].reshape(-1, 14, 3),
        "motion_ref_body_pos_rel": obs_list[21].reshape(-1, 14, 3),
    }

    # FK override
    if fk_calculator is not None:
        joint_pos_batch = robot_state["joint_pos"]
        joint_vel_batch = robot_state["joint_vel"]
        root_quat = robot_state["root_rot"]
        root_ang_vel = robot_state["body_ang_vel"][:, 0, :]
        root_lin_vel = robot_state["body_lin_vel"][:, 0, :]
        root_pos = robot_state["root_pos"]

        # --- Dual recording: preserve simulation body_pos before FK override ---
        record_gt = (fk_noise_cfg is not None
                     and fk_noise_cfg.get("record_ground_truth", False))
        if record_gt:
            robot_state["body_pos_sim"] = robot_state["body_pos"].clone()  # [B, 30, 3]

        # --- Apply FK input noise (simulates real sensor imperfections) ---
        if fk_noise_model is not None:
            noisy_root_quat = fk_noise_model.corrupt_imu_orientation(root_quat)
            noisy_joint_pos = fk_noise_model.corrupt_joint_positions(joint_pos_batch)
            noisy_root_ang_vel = fk_noise_model.corrupt_gyro(root_ang_vel)
            noisy_root_lin_vel = fk_noise_model.corrupt_base_velocity(root_lin_vel)
            noisy_root_pos = fk_noise_model.corrupt_base_position(root_pos)
        else:
            noisy_root_quat = root_quat
            noisy_joint_pos = joint_pos_batch
            noisy_root_ang_vel = root_ang_vel
            noisy_root_lin_vel = root_lin_vel
            noisy_root_pos = root_pos

        fk_result = fk_calculator.compute_fk(
            joint_pos=noisy_joint_pos.cpu().numpy() if isinstance(noisy_joint_pos, torch.Tensor) else noisy_joint_pos,
            joint_vel=joint_vel_batch.cpu().numpy() if isinstance(joint_vel_batch, torch.Tensor) else joint_vel_batch,
            imu_pose=noisy_root_quat.cpu().numpy() if isinstance(noisy_root_quat, torch.Tensor) else noisy_root_quat,
            imu_gyro=noisy_root_ang_vel.cpu().numpy() if isinstance(noisy_root_ang_vel, torch.Tensor) else noisy_root_ang_vel,
            base_lin_vel=noisy_root_lin_vel.cpu().numpy() if isinstance(noisy_root_lin_vel, torch.Tensor) else noisy_root_lin_vel,
            base_pos=noisy_root_pos.cpu().numpy() if isinstance(noisy_root_pos, torch.Tensor) else noisy_root_pos,
            isaaclab_q_order=True,
        )
        if isinstance(fk_result['body_pos'], torch.Tensor):
            robot_state["body_pos"] = fk_result['body_pos']
            robot_state["body_lin_vel"] = fk_result['body_lin_vel']
        else:
            robot_state["body_pos"] = torch.from_numpy(fk_result['body_pos']).to(robot_state["body_pos"].device)
            robot_state["body_lin_vel"] = torch.from_numpy(fk_result['body_lin_vel']).to(robot_state["body_lin_vel"].device)

    robot_state_np = {
        key: value.cpu().numpy() for key, value in robot_state.items()
    }
    return robot_state, robot_state_np


class OUNoise:
    """
    Ornstein-Uhlenbeck noise generator for temporally correlated action perturbations.
    
    Following BeyondMimic: "Overdamped PD gains suppress high-frequency perturbations,
    limiting state diversity. OU noise produces temporally correlated action perturbations."
    
    Update formula: η_{t+1} = η_t + θ(μ - η_t)Δt + σ√Δt ε_t
    
    Args:
        action_dim: Dimension of action space (e.g., 29 for G1 joints)
        theta: Mean reversion rate (default: 0.8)
        mu: Long-term mean (default: 0.0)
        sigma: Joint-wise noise scale (default: 0.1)
        dt: Time step (default: 1.0)
        device: Torch device
    """
    
    def __init__(
        self,
        action_dim: int,
        theta: float = 0.8,
        mu: float = 0.0,
        sigma: float = 0.1,
        dt: float = 1.0,
        device: torch.device = torch.device("cpu"),
    ):
        self.action_dim = action_dim
        self.theta = theta
        self.mu = mu
        self.sigma = sigma
        self.dt = dt
        self.device = device
        
        # Initialize noise state
        self.state = None
        
    def reset(self, batch_size: int):
        """Reset noise state to zero (or mu)."""
        self.state = torch.ones(batch_size, self.action_dim, device=self.device) * self.mu
        
    def sample(self) -> torch.Tensor:
        """
        Generate next noise sample using OU process.
        
        Returns:
            Noise tensor [batch_size, action_dim]
        """
        if self.state is None:
            raise RuntimeError("OUNoise must be reset before sampling")
        
        # ε_t ~ N(0, I)
        epsilon = torch.randn_like(self.state)
        
        # η_{t+1} = η_t + θ(μ - η_t)Δt + σ√Δt ε_t
        self.state = (
            self.state
            + self.theta * (self.mu - self.state) * self.dt
            + self.sigma * np.sqrt(self.dt) * epsilon
        )
        
        return self.state.clone()


def _apply_push_robot_override(env_cfg, cfg: DictConfig) -> Dict:
    """Apply the collector's Hydra push setting to the typed IsaacLab config."""
    env_overrides = cfg.get("env", {})
    has_velocity_override = "push_robot_velocity_range" in env_overrides
    has_interval_override = "push_robot_interval_range_s" in env_overrides

    if has_velocity_override:
        raw_velocity_range = env_overrides.push_robot_velocity_range
        velocity_range = (
            None
            if raw_velocity_range is None
            else OmegaConf.to_container(raw_velocity_range, resolve=True)
        )
        env_cfg.push_robot_velocity_range = velocity_range
        if velocity_range is None:
            env_cfg.events.push_robot = None
        else:
            if env_cfg.events.push_robot is None:
                raise ValueError(
                    "Cannot enable push_robot from Hydra because the typed event is absent"
                )
            env_cfg.events.push_robot.params["velocity_range"] = velocity_range

    if has_interval_override:
        interval_range = tuple(env_overrides.push_robot_interval_range_s)
        env_cfg.push_robot_interval_range_s = interval_range
        if env_cfg.events.push_robot is not None:
            env_cfg.events.push_robot.interval_range_s = interval_range

    push_event_enabled = env_cfg.events.push_robot is not None
    result = {
        "enabled": push_event_enabled,
        "velocity_range": getattr(env_cfg, "push_robot_velocity_range", None),
        "interval_range_s": getattr(env_cfg, "push_robot_interval_range_s", None),
    }
    print(f"[INFO] Resolved push_robot config: {result}")
    return result


def _verify_runtime_push_robot(env_unwrapped, expected: Dict) -> Dict:
    """Verify the event manager retained the resolved push contract."""
    event_manager = env_unwrapped.event_manager
    active_names = {
        name
        for names in event_manager._mode_term_names.values()
        for name in names
    }
    enabled = "push_robot" in active_names
    if enabled != expected["enabled"]:
        raise RuntimeError(
            "Post-gym push_robot mismatch: "
            f"expected enabled={expected['enabled']}, got enabled={enabled}"
        )

    velocity_range = None
    interval_range_s = None
    if enabled:
        term_cfg = event_manager.get_term_cfg("push_robot")
        velocity_range = term_cfg.params.get("velocity_range")
        interval_range_s = tuple(term_cfg.interval_range_s)
        expected_velocity = expected["velocity_range"]
        expected_interval = tuple(expected["interval_range_s"])
        if velocity_range != expected_velocity or interval_range_s != expected_interval:
            raise RuntimeError(
                "Post-gym push_robot term mismatch: "
                f"expected velocity={expected_velocity}, interval={expected_interval}; "
                f"got velocity={velocity_range}, interval={interval_range_s}"
            )

    result = {
        "enabled": enabled,
        "velocity_range": velocity_range,
        "interval_range_s": interval_range_s,
    }
    print(f"[COLLECTION_POST_GYM_PUSH_ROBOT] {result}")
    return result


@hydra.main(version_base=None, config_path=".", config_name="data_collection")
def main(cfg: DictConfig):
    """Main data collection entry point with Hydra configuration."""
    
    # Print configuration
    print("="*70)
    print("G1 Dataset Collection Configuration")
    print("="*70)
    print(OmegaConf.to_yaml(cfg))
    print("="*70)
    
    # Run data collection
    collect_data(cfg)


def collect_data(cfg: DictConfig):
    """Main data collection loop with OU noise injection."""

    # Set Isaac Sim root path before any isaacsim import.
    # The pip-installed isaacsim-rl package needs ISAAC_PATH to find bundled
    # Omniverse Kit extensions (omni.kit.*); without it, SimulationApp fails
    # with "ModuleNotFoundError: No module named 'omni.kit.usd'".
    if "ISAAC_PATH" not in os.environ:
        import importlib.util as _importlib_util
        _isaacsim_spec = _importlib_util.find_spec("isaacsim")
        if _isaacsim_spec and _isaacsim_spec.origin:
            # isaacsim/__init__.py → site-packages/isaacsim = ISAAC_PATH
            os.environ["ISAAC_PATH"] = os.path.dirname(_isaacsim_spec.origin)

    # Omniverse Kit writes user config/cache to omni/data/ inside the conda env.
    # On shared/read-only envs that directory is not writable.  Point it into the
    # user's home so the Kit app can start without PermissionError.
    if "OMNI_KIT_APP_DATA" not in os.environ:
        _kit_data = os.path.join(os.path.expanduser("~"), ".cache", "isaacsim", "kit-data")
        os.environ["OMNI_KIT_APP_DATA"] = _kit_data
        os.makedirs(_kit_data, exist_ok=True)

    # Import Isaac Sim related modules
    from isaaclab.app import AppLauncher
    import argparse
    
    # Create app launcher
    _livestream = getattr(cfg.visualization, "livestream", 0)
    _livestream_int = int(_livestream) if _livestream else 0
    # When headless + livestream, use headless rendering experience instead of
    # the full GUI experience (isaaclab.python.kit), which requires online
    # extension registry access for GUI extensions like omni.kit.menu.edit.
    _experience = str(cfg.visualization.get("experience", "")).strip()
    if not _experience and cfg.visualization.headless and _livestream_int >= 1:
        _experience = "isaaclab.python.headless.rendering.kit"
    app_launcher_args = argparse.Namespace(
        headless=cfg.visualization.headless,
        livestream=_livestream_int,
        device="cuda:0" if torch.cuda.is_available() else "cpu",
        enable_cameras=cfg.visualization.enable_cameras,
        experience=_experience,
    )
    app_launcher = AppLauncher(app_launcher_args)
    simulation_app = app_launcher.app
    collection_seed = int(cfg.task.seed)
    _seed_collection_runtime(collection_seed)

    # Start MJPEG streaming server for browser-based viewing.
    # Uses omni.syntheticdata to capture viewport frames and serves them
    # as MJPEG.  Set environment variable MJPEG_PORT to override.
    _mjpeg_port = int(os.environ.get("MJPEG_PORT", "39200"))
    try:
        import importlib.util as _iu
        _mjpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mjpeg_stream.py")
        _mjpeg_spec = _iu.spec_from_file_location("mjpeg_stream", _mjpeg_path)
        _mjpeg_mod = _iu.module_from_spec(_mjpeg_spec)
        _mjpeg_spec.loader.exec_module(_mjpeg_mod)
        _mjpeg_mod.start_mjpeg_server(port=_mjpeg_port)
    except Exception as _e:
        print(f"[MJPEG] Could not start streaming server: {_e}")

    import gymnasium as gym
    from rsl_rl.runners import OnPolicyRunner
    
    # Import tasks to register environment
    import rl_tracker.tasks  # noqa: F401
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper
    from isaaclab_tasks.utils.hydra import register_task_to_hydra
    from isaaclab.utils.io.pkl import load_pickle
    
    # Try to load config using Hydra first (like play.py), fallback to pickle
    if cfg.checkpoint.load_pickle_cfg:
        param_dir = Path(cfg.checkpoint.path).parent / "params"
        env_cfg = load_pickle(str(param_dir / "env.pkl"))
        agent_cfg = load_pickle(str(param_dir / "agent.pkl"))
        # env_cfg.scene.robot.spawn.fix_base = True  # Ensure robot base is fixed
        print(f"[INFO] Successfully loaded config from pickle files")
    else:
        env_cfg, agent_cfg = register_task_to_hydra(cfg.task.name, "rsl_rl_cfg_entry_point")
        print(f"[INFO] Successfully loaded config using Hydra")

    # The top-level data-collection seed was historically receipt-only. Apply it
    # to IsaacLab as well so matched teacher lanes begin from identical resets.
    env_cfg.seed = collection_seed

    push_robot_config = _apply_push_robot_override(env_cfg, cfg)

    
    # Update environment config
    env_cfg.scene.num_envs = cfg.task.num_envs
    
    # Set motion files
    motion_root = Path(os.environ.get("PREDACTOR_MOTION_ROOT", "../Artifacts/motions"))
    motion_pattern = motion_root / Path(cfg.motion.pattern) / "motion.npz"
    motion_files = sorted(glob.glob(str(motion_pattern)))
    if not motion_files:
        raise FileNotFoundError(f"No motion.npz found for {motion_pattern}")
    
    # === Handle collection mode ===
    collection_mode = cfg.collection.get("mode", "standard")
    
    if collection_mode == "deterministic":
        # Deterministic M*N sampling mode
        samples_per_motion = cfg.collection.samples_per_motion
        print(f"[INFO] Using DETERMINISTIC collection mode")
        print(f"[INFO] {len(motion_files)} motions × {samples_per_motion} samples = {len(motion_files) * samples_per_motion} total episodes")
        
        # Need to use collection command term instead of standard motion command
        from rl_tracker.tasks.tracking.mdp.commands_collection import MotionCollectionCommandCfg
        bfm_exact_reference_reset = bool(
            cfg.get("bfm_zero", {}).get("enable", False)
            and cfg.get("bfm_zero", {}).get("exact_reference_reset", False)
        )
        bfm_record_only_termination = bool(
            cfg.get("bfm_zero", {}).get("enable", False)
            and cfg.get("bfm_zero", {}).get("record_only_termination", False)
        )
        zero_pose_velocity_range = {
            key: (0.0, 0.0) for key in ("x", "y", "z", "roll", "pitch", "yaw")
        }

        # Replace motion command with collection command
        env_cfg.commands.motion = MotionCollectionCommandCfg(
            asset_name=env_cfg.commands.motion.asset_name,
            anchor_body_name=env_cfg.commands.motion.anchor_body_name,
            body_names=env_cfg.commands.motion.body_names,
            motion_files=motion_files,
            samples_per_motion=samples_per_motion,
            default_height=getattr(env_cfg.commands.motion, "default_height", 2.0),
            pose_range=(
                zero_pose_velocity_range
                if bfm_exact_reference_reset
                else getattr(env_cfg.commands.motion, "pose_range", {})
            ),
            velocity_range=(
                zero_pose_velocity_range
                if bfm_exact_reference_reset
                else getattr(env_cfg.commands.motion, "velocity_range", {})
            ),
            joint_position_range=(
                (0.0, 0.0)
                if bfm_exact_reference_reset
                else getattr(env_cfg.commands.motion, "joint_position_range", (-0.52, 0.52))
            ),
            future_steps=getattr(env_cfg.commands.motion, "future_steps", 1),
            direction_range=tuple(cfg.collection.get("direction_range", [0.0, 0.0])),
            resampling_time_range=(1.0e9, 1.0e9),
            termination_grace_steps=1 if bfm_exact_reference_reset else 0,
            record_only_termination=bfm_record_only_termination,
        )
        env_cfg.rewards = None
    else:
        # Standard random sampling mode (backward compatible)
        print(f"[INFO] Using STANDARD collection mode")
        if len(motion_files) > cfg.task.num_envs:
            print(f"[WARNING] Number of motion files ({len(motion_files)}) exceeds num_envs ({cfg.task.num_envs}), truncating for loading speed.")
            motion_files = motion_files[:cfg.task.num_envs]
        
        env_cfg.commands.motion.motion_files = motion_files
    
    use_mimic_lite = cfg.get("mimic_lite", {}).get("enable", False)
    use_bfm_zero = cfg.get("bfm_zero", {}).get("enable", False)
    if use_mimic_lite and use_bfm_zero:
        raise ValueError("mimic_lite.enable and bfm_zero.enable are mutually exclusive")

    print(f"[INFO] Using {len(motion_files)} motion files")
    print(f"[INFO] Number of environments: {cfg.task.num_envs}")
    if not (use_mimic_lite or use_bfm_zero):
        print(f"[INFO] Loading checkpoint: {cfg.checkpoint.path}")
    
    # Print noise configuration
    if cfg.noise.enable:
        print(f"[INFO] Action noise injection ENABLED")
        print(f"[INFO] Noise type: {cfg.noise.type}")
        if cfg.noise.type == "ou":
            print(f"[INFO] OU parameters: θ={cfg.noise.theta}, μ={cfg.noise.mu}, σ={cfg.noise.sigma}, Δt={cfg.noise.dt}")
    else:
        print(f"[INFO] Action noise injection DISABLED")
    
    # Create environment
    # MimicLite retains its legacy absolute-target bridge. BFM converts its
    # internal joint target back to RLTracker's normalized action space so the
    # stored action and OU-noise contracts exactly match PDP051.
    if use_mimic_lite:
        from mimic_lite_bridge import (
            MimicLiteObsBuilder,
            MimicLiteONNXPolicy,
            MimicLiteDeployONNXPolicy,
        )
        env_cfg.actions.joint_pos.use_default_offset = False
        env_cfg.actions.joint_pos.offset = 0.0
        env_cfg.actions.joint_pos.scale = 1.0

    if use_mimic_lite:
        # Override robot config with MimicLite-aligned PD gains (matches deploy YAML joint_kp/joint_kd)
        from rl_tracker.robots.g1 import G1_CYLINDER_CFG_MIMICLITE
        env_cfg.scene.robot = G1_CYLINDER_CFG_MIMICLITE.replace(prim_path="{ENV_REGEX_NS}/Robot")
        print(f"[MimicLite] Robot PD gains aligned with deploy YAML (hip_pitch=7520_22, wrist=custom)")
    elif use_bfm_zero and str(
        cfg.get("bfm_zero", {}).get("plant_profile", "pdp051")
    ) == "released_bfm":
        from rl_tracker.robots.g1 import G1_CYLINDER_CFG_BFM
        env_cfg.scene.robot = G1_CYLINDER_CFG_BFM.replace(prim_path="{ENV_REGEX_NS}/Robot")
        print("[BFM-Zero] Robot PD gains aligned with released G1 policy YAML")
    elif use_bfm_zero:
        print("[BFM-Zero] Inheriting the unmodified PDP051 RLTracker plant")

    record_rgb = bool(cfg.visualization.get("record_rgb", False))
    env = gym.make(cfg.task.name, cfg=env_cfg, render_mode="rgb_array" if record_rgb else None)
    env_unwrapped = env.unwrapped
    motion_debug_term = env_unwrapped.command_manager._terms.get("motion")
    reference_debug_vis = motion_debug_term is not None and (
        not cfg.visualization.headless or record_rgb
    )
    if reference_debug_vis:
        motion_debug_term._set_debug_vis_impl(True)
        print("[INFO] Reference motion visualization ENABLED (green body markers)")
    runtime_push_robot_config = _verify_runtime_push_robot(env_unwrapped, push_robot_config)
    
    # Load policy
    log_dir = os.path.dirname(cfg.checkpoint.path)
    wrapped_env = RslRlVecEnvWrapper(env)
    
    policy = None
    if not (use_mimic_lite or use_bfm_zero):
        ppo_runner = OnPolicyRunner(wrapped_env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
        ppo_runner.load(cfg.checkpoint.path)
        policy = ppo_runner.get_inference_policy(device=env_unwrapped.device)

    # ---- MimicLite ONNX policy (optional) ----
    mimic_lite_bridge = None
    mimic_lite_policy = None
    if use_mimic_lite:
        ml_cfg = cfg.mimic_lite
        onnx_path = ml_cfg.get("deploy_onnx_path", "") or ml_cfg.onnx_path
        deploy_yaml_path = ml_cfg.get("deploy_yaml", "")
        print(f"[MimicLite] Enabling MimicLite ONNX policy")
        print(f"[MimicLite]   ONNX: {onnx_path}")
        if deploy_yaml_path:
            print(f"[MimicLite]   Deploy YAML: {deploy_yaml_path}")

        # Load deploy YAML for observation builder + policy
        deploy_cfg = {}
        if deploy_yaml_path and os.path.exists(deploy_yaml_path):
            with open(deploy_yaml_path) as f:
                deploy_cfg = yaml.safe_load(f) or {}
            print(f"[MimicLite]   Loaded deploy YAML ({len(deploy_cfg)} keys)")

        # Build observation bridge (needs motion config from deploy YAML)
        cmd_mgr = env_unwrapped.command_manager
        mimic_lite_bridge = MimicLiteObsBuilder(
            num_envs=cfg.task.num_envs,
            device=env_unwrapped.device,
            command_manager=cmd_mgr,
            deploy_cfg=deploy_cfg,
        )

        # Decide ONNX format
        is_deploy_fmt = bool(ml_cfg.get("deploy_onnx_path", ""))
        if is_deploy_fmt:
            mimic_lite_policy = MimicLiteDeployONNXPolicy(
                onnx_path=onnx_path,
                device=env_unwrapped.device,
            )
        else:
            mimic_lite_policy = MimicLiteONNXPolicy(
                onnx_path=onnx_path,
                device=env_unwrapped.device,
                deploy_yaml_path=deploy_yaml_path or None,
            )
        print(f"[MimicLite] Ready")

    # ---- BFM-Zero/UFO actor + backward encoder (optional) ----
    bfm_zero_policy = None
    bfm_plant_contract = None
    if use_bfm_zero:
        from bfm_zero_bridge import BFMZeroONNXPolicy, ISAACLAB_DOF_NAMES, _resolve_pattern_values
        bfm_cfg = cfg.bfm_zero
        bfm_plant_profile = str(bfm_cfg.get("plant_profile", "pdp051"))
        if bfm_plant_profile not in {"pdp051", "released_bfm"}:
            raise ValueError("bfm_zero.plant_profile must be pdp051 or released_bfm")
        from rl_tracker.robots.g1 import G1_ACTION_SCALE
        collector_action_scale = torch.as_tensor(
            _resolve_pattern_values(G1_ACTION_SCALE, ISAACLAB_DOF_NAMES),
            dtype=torch.float32,
            device=env_unwrapped.device,
        )
        collector_default_dof_pos = env_unwrapped.scene["robot"].data.default_joint_pos[0]
        runtime_robot = env_unwrapped.scene["robot"]
        if list(runtime_robot.joint_names) != ISAACLAB_DOF_NAMES:
            raise RuntimeError(
                "BFM runtime joint order mismatch: "
                f"expected {ISAACLAB_DOF_NAMES}, got {list(runtime_robot.joint_names)}"
            )
        with Path(bfm_cfg.policy_yaml_path).expanduser().resolve().open(encoding="utf-8") as stream:
            released_policy_cfg = yaml.safe_load(stream) or {}
        expected_effort = _resolve_pattern_values(
            {
                ".*_hip_pitch_joint": 139.0,
                ".*_hip_roll_joint": 139.0,
                ".*_hip_yaw_joint": 88.0,
                ".*_knee_joint": 139.0,
                ".*_ankle_pitch_joint": 50.0,
                ".*_ankle_roll_joint": 50.0,
                "waist_yaw_joint": 88.0,
                "waist_roll_joint": 50.0,
                "waist_pitch_joint": 50.0,
                ".*_shoulder_.*_joint": 25.0,
                ".*_elbow_joint": 25.0,
                ".*_wrist_roll_joint": 25.0,
                ".*_wrist_pitch_joint": 13.4,
                ".*_wrist_yaw_joint": 13.4,
            }, ISAACLAB_DOF_NAMES
        )
        expected_velocity = _resolve_pattern_values(
            {
                ".*_hip_pitch_joint": 32.0,
                ".*_hip_roll_joint": 32.0,
                ".*_hip_yaw_joint": 32.0,
                ".*_knee_joint": 20.0,
                ".*_ankle_.*_joint": 37.0,
                "waist_yaw_joint": 32.0,
                "waist_roll_joint": 37.0,
                "waist_pitch_joint": 37.0,
                ".*_shoulder_.*_joint": 37.0,
                ".*_elbow_joint": 37.0,
                ".*_wrist_roll_joint": 37.0,
                ".*_wrist_pitch_joint": 27.0,
                ".*_wrist_yaw_joint": 27.0,
            }, ISAACLAB_DOF_NAMES
        )
        expected_armature = _resolve_pattern_values(
            {
                ".*_hip_pitch_joint": 0.025101925,
                ".*_hip_roll_joint": 0.025101925,
                ".*_hip_yaw_joint": 0.01017752004,
                ".*_knee_joint": 0.025101925,
                ".*_ankle_.*_joint": 0.00721945,
                "waist_yaw_joint": 0.01017752004,
                "waist_roll_joint": 0.00721945,
                "waist_pitch_joint": 0.00721945,
                ".*_shoulder_.*_joint": 0.003609725,
                ".*_elbow_joint": 0.003609725,
                ".*_wrist_roll_joint": 0.003609725,
                ".*_wrist_pitch_joint": 0.00425,
                ".*_wrist_yaw_joint": 0.00425,
            }, ISAACLAB_DOF_NAMES
        )
        expected_stiffness = _resolve_pattern_values(
            released_policy_cfg["joint_kp"], ISAACLAB_DOF_NAMES
        )
        expected_damping = _resolve_pattern_values(
            released_policy_cfg["joint_kd"], ISAACLAB_DOF_NAMES
        )
        actual_values = {
            "effort_limit": runtime_robot.data.joint_effort_limits[0],
            "velocity_limit": runtime_robot.data.joint_vel_limits[0],
            "armature": runtime_robot.data.joint_armature[0],
            "friction": runtime_robot.data.joint_friction_coeff[0],
            "stiffness": runtime_robot.data.joint_stiffness[0],
            "damping": runtime_robot.data.joint_damping[0],
        }
        expected_values = {
            "effort_limit": expected_effort,
            "velocity_limit": expected_velocity,
            "armature": expected_armature,
            "friction": [0.03] * len(ISAACLAB_DOF_NAMES),
            "stiffness": expected_stiffness,
            "damping": expected_damping,
        }
        if bfm_plant_profile == "pdp051":
            # The causal BFM comparison keeps the exact control plant. The
            # released YAML still defines target safety and action conversion,
            # but it must not silently alter simulator dynamics.
            expected_values = {
                key: actual.detach().clone() for key, actual in actual_values.items()
            }
        max_abs_error = {}
        for key, actual in actual_values.items():
            expected = torch.as_tensor(expected_values[key], dtype=actual.dtype, device=actual.device)
            error = float(torch.max(torch.abs(actual - expected)).item())
            max_abs_error[key] = error
            if error > 1.0e-3:
                raise RuntimeError(f"BFM runtime plant {key} mismatch: max_abs_error={error}")
        articulation_props = env_unwrapped.cfg.scene.robot.spawn.articulation_props
        if bfm_plant_profile == "released_bfm" and (
            articulation_props.solver_position_iteration_count != 4
            or articulation_props.solver_velocity_iteration_count != 0
        ):
            raise RuntimeError(
                "BFM runtime solver mismatch: expected 4/0, got "
                f"{articulation_props.solver_position_iteration_count}/"
                f"{articulation_props.solver_velocity_iteration_count}"
            )
        policy_path = Path(bfm_cfg.policy_yaml_path).expanduser().resolve()
        bfm_plant_contract = {
            "status": (
                "BFM_PDP051_PLANT_INHERITED"
                if bfm_plant_profile == "pdp051"
                else "BFM_RELEASED_BFM_PLANT_PASS"
            ),
            "source": (
                "unmodified PDP051 RLTracker collection environment"
                if bfm_plant_profile == "pdp051"
                else "BFM-Zero g1_29dof_new_effort_limit + hard-waist + released policy YAML"
            ),
            "profile": bfm_plant_profile,
            "policy_yaml_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            "max_abs_error": max_abs_error,
            "solver_position_iterations": articulation_props.solver_position_iteration_count,
            "solver_velocity_iterations": articulation_props.solver_velocity_iteration_count,
            "physics_dt_s": float(env_unwrapped.physics_dt),
            "control_dt_s": float(env_unwrapped.step_dt),
            "self_collisions": bool(articulation_props.enabled_self_collisions),
            "terrain_static_friction": float(env_unwrapped.cfg.scene.terrain.physics_material.static_friction),
            "terrain_dynamic_friction": float(env_unwrapped.cfg.scene.terrain.physics_material.dynamic_friction),
            "max_depenetration_velocity": float(
                env_unwrapped.cfg.scene.robot.spawn.rigid_props.max_depenetration_velocity
            ),
        }
        print(f"[BFM_BFM_PLANT] {bfm_plant_contract}")
        robot_yaml_path = str(bfm_cfg.get("robot_yaml_path", "")).strip()
        if robot_yaml_path:
            with Path(robot_yaml_path).expanduser().resolve().open(encoding="utf-8") as stream:
                released_robot_cfg = yaml.safe_load(stream) or {}
            joint_pos_lower_limit = torch.as_tensor(
                _resolve_pattern_values(
                    released_robot_cfg["joint_pos_lower_limit"], ISAACLAB_DOF_NAMES
                ),
                dtype=torch.float32,
                device=env_unwrapped.device,
            )
            joint_pos_upper_limit = torch.as_tensor(
                _resolve_pattern_values(
                    released_robot_cfg["joint_pos_upper_limit"], ISAACLAB_DOF_NAMES
                ),
                dtype=torch.float32,
                device=env_unwrapped.device,
            )
            joint_velocity_limit = torch.as_tensor(
                _resolve_pattern_values(
                    released_robot_cfg["joint_velocity_limit"], ISAACLAB_DOF_NAMES
                ),
                dtype=torch.float32,
                device=env_unwrapped.device,
            )
            print(f"[BFM-Zero] Joint safety limits loaded from released robot YAML: {robot_yaml_path}")
        else:
            joint_pos_limits = env_unwrapped.scene["robot"].data.soft_joint_pos_limits[0]
            joint_pos_lower_limit = joint_pos_limits[:, 0]
            joint_pos_upper_limit = joint_pos_limits[:, 1]
            joint_velocity_limit = env_unwrapped.scene["robot"].data.joint_vel_limits[0]
        bfm_zero_policy = BFMZeroONNXPolicy(
            actor_path=bfm_cfg.actor_path,
            backward_path=bfm_cfg.backward_path,
            policy_yaml_path=bfm_cfg.policy_yaml_path,
            num_envs=cfg.task.num_envs,
            device=env_unwrapped.device,
            command_manager=env_unwrapped.command_manager,
            providers=list(bfm_cfg.get("providers", [])) or None,
            context_window=int(bfm_cfg.get("context_window", 3)),
            context_gamma=float(bfm_cfg.get("context_gamma", 0.8)),
            tracking_seq_length=int(bfm_cfg.get("tracking_seq_length", 1)),
            backward_angular_velocity_mode=str(
                bfm_cfg.get("backward_angular_velocity_mode", "body_scaled")
            ),
            extended_head_velocity_mode=str(
                bfm_cfg.get("extended_head_velocity_mode", "finite_difference")
            ),
            tail_context_mode=str(
                bfm_cfg.get("tail_context_mode", "official_shorten")
            ),
            actor_history_timing=str(
                bfm_cfg.get("actor_history_timing", "deploy_current")
            ),
            reference_preprocessing_mode=str(
                bfm_cfg.get("reference_preprocessing_mode", "stored_rltracker")
            ),
            official_robot_xml_path=str(
                bfm_cfg.get("official_robot_xml_path", "")
            ).strip() or None,
            context_mode=str(bfm_cfg.get("context_mode", "deploy_gamma")),
            collector_default_dof_pos=collector_default_dof_pos,
            collector_action_scale=collector_action_scale,
            joint_pos_lower_limit=joint_pos_lower_limit,
            joint_pos_upper_limit=joint_pos_upper_limit,
            joint_velocity_limit=joint_velocity_limit,
            control_dt=float(env_unwrapped.step_dt),
            action_target_mode=str(
                bfm_cfg.get("action_target_mode", "deploy_slew")
            ),
        )
        if str(bfm_cfg.get("reference_preprocessing_mode", "stored_rltracker")) == "official_ufo_fk":
            # The command term copied its active source buffers before the BFM
            # adapter existed. Refresh them in place, preserving task IDs and
            # frame-zero indexing, then rewrite the exact UFO reference reset.
            collection_term = env_unwrapped.command_manager._terms["motion"]
            all_env_ids = torch.arange(cfg.task.num_envs, device=env_unwrapped.device)
            collection_term._update_buffers(all_env_ids)
            collection_term._apply_initialization_randomization(all_env_ids)
            bfm_zero_policy.reset(all_env_ids)
            print("[BFM-Zero] Active motion buffers/reset refreshed from official UFO FK")
        print("[BFM-Zero] Ready")
    
    # Initialize noise generator if enabled
    noise_generator = None
    if cfg.noise.enable:
        action_dim = wrapped_env.num_actions
        if cfg.noise.type == "ou":
            noise_generator = OUNoise(
                action_dim=action_dim,
                theta=cfg.noise.theta,
                mu=cfg.noise.mu,
                sigma=cfg.noise.sigma,
                dt=cfg.noise.dt,
                device=env_unwrapped.device,
            )
            noise_generator.reset(cfg.task.num_envs)
            print(f"[INFO] Initialized OU noise generator for {action_dim} actions")
        else:
            raise ValueError(f"Unknown noise type: {cfg.noise.type}")
    
    # Initialize FK calculator if enabled
    fk_calculator = None
    if cfg.fk.use_fk:
        print(f"[INFO] Forward Kinematics ENABLED")
        print(f"[INFO] FK backend: {cfg.fk.fk_type}, device: {cfg.fk.fk_device}")

        # Resolve URDF path: auto-resolves from rl_tracker package assets when empty
        _assets_dir = os.environ.get("PREDACTOR_ASSET_ROOT", os.path.join(os.path.dirname(__file__), "..", "..", "source", "rl_tracker", "rl_tracker", "assets"))
        urdf_cfg = cfg.fk.urdf_path
        if urdf_cfg and os.path.isabs(urdf_cfg):
            urdf_path = urdf_cfg
        elif urdf_cfg:
            urdf_path = os.path.join(_assets_dir, urdf_cfg)
        else:
            urdf_path = os.path.join(_assets_dir, "unitree_description", "urdf", "g1", "main.urdf")
        if not os.path.exists(urdf_path):
            raise FileNotFoundError(
                f"URDF not found at {urdf_path}. Set fk.urdf_path in the config."
            )

        fk_calculator = build_fk_calculator(
            fk_type=cfg.fk.fk_type,
            urdf_path=urdf_path,
            device=cfg.fk.fk_device,
        )
        print(f"[INFO] FK calculator initialized")
    else:
        print(f"[INFO] Forward Kinematics DISABLED (using simulation body states)")

    # Initialize FK noise model (simulates sensor noise on FK inputs)
    fk_noise_model = None
    fk_noise_cfg = None
    if cfg.fk.use_fk and cfg.fk.get("noise", {}).get("enable", False):
        fk_noise_cfg = dict(cfg.fk.noise) if hasattr(cfg.fk.noise, 'items') else cfg.fk.noise
        try:
            fk_noise_model = FKNoiseModel(
                cfg=cfg.fk.noise,
                num_envs=cfg.task.num_envs,
                dt=0.02,  # 50Hz control
                device=env_unwrapped.device,
            )
            print(f"[INFO] FK noise model initialized ({fk_noise_model.config_summary()})")
        except Exception as e:
            print(f"[WARNING] FK noise model initialization failed: {e}. Disabling FK noise.")
            fk_noise_model = None
    
    # Initialize replay buffer
    buffer = ReplayBuffer.create_empty_numpy()

    # Determine which fields to record (controlled by output.fields in config)
    _ALL_FIELDS = [
        "act", "body_pos", "body_rot", "body_lin_vel", "body_ang_vel",
        "joint_pos", "joint_vel", "root_pos", "root_rot", "motion_idx",
        "projected_gravity", "base_lin_vel", "base_ang_vel", "last_actions",
        "motion_ref_root_pos", "motion_ref_root_rot", "motion_ref_root_lin_vel", "motion_ref_root_ang_vel",
        "motion_ref_joint_pos", "motion_ref_joint_vel", "motion_ref_body_pos", "motion_ref_body_vel",
        "motion_ref_body_pos_rel",
        "body_pos_sim",  # optional: sim ground-truth body_pos (dual recording with FK noise)
    ]
    fields_to_save = list(cfg.output.get("fields", _ALL_FIELDS))
    if cfg.output.get("sort_by_motion_idx", False) and "motion_idx" not in fields_to_save:
        print("[WARNING] sort_by_motion_idx requires motion_idx; adding it automatically.")
        fields_to_save.append("motion_idx")
    # Dual recording: add body_pos_sim field when FK noise and ground-truth recording are enabled
    if (cfg.fk.use_fk
            and cfg.fk.get("noise", {}).get("enable", False)
            and cfg.fk.noise.get("record_ground_truth", False)):
        if "body_pos_sim" not in fields_to_save:
            fields_to_save.append("body_pos_sim")
            print("[INFO] FK dual recording enabled — adding 'body_pos_sim' field (sim ground-truth body positions)")
    print(f"[INFO] Recording {len(fields_to_save)} fields: {fields_to_save}")

    # Storage for current episodes (only for configured fields)
    episode_data = {field: [[] for _ in range(cfg.task.num_envs)] for field in fields_to_save}
    
    # Track episode statistics for quality filtering
    episode_lengths = np.zeros(cfg.task.num_envs, dtype=np.int32)
    episode_rewards = np.zeros(cfg.task.num_envs, dtype=np.float32)
    
    # Track which envs just reset (to skip storing their first frame)
    env_just_reset = np.ones(cfg.task.num_envs, dtype=bool)  # All envs start as "just reset"
    
    # Statistics tracking
    total_saved_steps = 0
    total_episodes_collected = 0
    total_episodes_saved = 0
    total_non_timeout_failures = 0
    total_failure_motion_end_coincidences = 0
    saved_task_ids: set[int] = set()
    bfm_diagnostics_enabled = bool(
        use_bfm_zero and cfg.get("bfm_zero", {}).get("diagnostics", False)
    )
    bfm_initial_state_diagnostics: list[dict[str, object]] = []
    bfm_failure_diagnostics: list[dict[str, object]] = []
    teacher_canary_cfg = cfg.get("teacher_canary", {})
    teacher_canary_enabled = bool(teacher_canary_cfg.get("enable", False))
    bfm_stop_after_first_attempts = bool(
        teacher_canary_enabled
        or (
            use_bfm_zero
            and cfg.get("bfm_zero", {}).get("stop_after_first_attempts", False)
        )
    )
    bfm_first_attempt_report_path = str(
        teacher_canary_cfg.get("report_path", "")
        or cfg.get("bfm_zero", {}).get("first_attempt_report_path", "")
    ).strip()
    teacher_canary_trace_dir = str(
        teacher_canary_cfg.get("trace_dir", "")
    ).strip()
    if bfm_stop_after_first_attempts and collection_mode != "deterministic":
        raise ValueError("BFM first-attempt diagnostics require deterministic collection mode")
    if bfm_stop_after_first_attempts and not bfm_first_attempt_report_path:
        raise ValueError(
            "teacher canary first-attempt mode requires a report path"
        )
    if bfm_diagnostics_enabled or bfm_stop_after_first_attempts:
        # Enable the termination-side snapshot only for explicit BFM
        # diagnostics; normal production collection keeps the original path.
        env_unwrapped.command_manager._terms["motion"].bfm_diagnostic_capture_termination_diagnostics = True
    bfm_first_attempts: dict[int, dict[str, object]] = {}
    bfm_first_attempts_complete = False
    
    # Reset environment
    obs, _ = wrapped_env.get_observations()
    
    print(f"[INFO] Starting data collection...")
    print(f"[INFO] Target: {cfg.collection.len_to_save} timesteps")
    print(f"[INFO] Quality filter: min_episode_length={cfg.collection.min_episode_length}")
    if cfg.collection.min_mean_reward is not None:
        print(f"[INFO] Quality filter: min_mean_reward={cfg.collection.min_mean_reward}")
    
    # === Deterministic mode: target is M*N episodes, not timesteps ===
    if collection_mode == "deterministic":
        total_tasks = len(motion_files) * samples_per_motion
        target_episodes = total_tasks
        print(f"[INFO] Deterministic mode: collecting {target_episodes} episodes")
        pbar = tqdm(total=target_episodes, desc="Collecting episodes")
    else:
        target_episodes = float('inf')  # No limit
        pbar = tqdm(total=cfg.collection.len_to_save, desc="Collecting data")

    # Stall-timeout tracking (deterministic mode only)
    stall_progress_threshold = float(cfg.collection.get("stall_progress_threshold", 0.99))
    stall_timeout_seconds = float(cfg.collection.get("stall_timeout_seconds", 120))
    _stall_last_saved = 0
    _stall_last_time = time.time()
    _stall_recoveries = 0
    stall_max_recoveries = int(cfg.collection.get("stall_max_recoveries", 3))

    with torch.inference_mode():
        while simulation_app.is_running():
            # Check stopping conditions
            if collection_mode == "deterministic":
                if total_episodes_saved >= target_episodes:
                    break
                # Stall-timeout: exit early if >threshold done and no progress for N seconds
                if total_episodes_saved != _stall_last_saved:
                    _stall_last_saved = total_episodes_saved
                    _stall_last_time = time.time()
                elif (total_episodes_saved / max(target_episodes, 1) >= stall_progress_threshold
                      and time.time() - _stall_last_time >= stall_timeout_seconds):
                    if _stall_recoveries >= stall_max_recoveries:
                        print(f"\n[WARNING] Stall timeout: {total_episodes_saved}/{target_episodes} "
                              f"episodes saved after {_stall_recoveries} recoveries. Exiting early.")
                        break

                    collection_term = env_unwrapped.command_manager._terms["motion"]
                    reopened_env_ids = collection_term.reconcile_saved_tasks(saved_task_ids)
                    reopened_env_list = reopened_env_ids.cpu().tolist()
                    for env_idx in reopened_env_list:
                        for key in episode_data:
                            episode_data[key][env_idx] = []
                        episode_lengths[env_idx] = 0
                        episode_rewards[env_idx] = 0
                        env_just_reset[env_idx] = True
                        if noise_generator is not None:
                            noise_generator.state[env_idx] = noise_generator.mu
                        if fk_noise_model is not None:
                            fk_noise_model.reset_env(env_idx)

                    _stall_recoveries += 1
                    _stall_last_saved = total_episodes_saved
                    _stall_last_time = time.time()
                    print(
                        f"\n[Collection] Stall recovery {_stall_recoveries}/"
                        f"{stall_max_recoveries}: reopened {len(reopened_env_list)} missing "
                        f"assignments after {stall_timeout_seconds:.0f}s without progress"
                    )
                    continue
            else:
                if total_saved_steps >= cfg.collection.len_to_save:
                    break
            
            # Compute diffusion observations once (shared by recording + MimicLite).
            # Observation manager applies noise internally based on the ObsTerm config.
            # 691-dim layout (22 groups):
            #   body_pos(90) + body_rot(120) + body_lin_vel(90) + body_ang_vel(90)
            #   + joint_pos(29) + joint_vel(29) + root_pos(3) + root_rot(4) + motion_idx(1)
            #   + projected_gravity(3) + base_lin_vel(3) + base_ang_vel(3) + last_actions(29)
            #   + motion_ref_root_pos(3) + motion_ref_root_rot(4) + motion_ref_root_lin_vel(3)
            #   + motion_ref_root_ang_vel(3)
            #   + motion_ref_joint_pos(29) + motion_ref_joint_vel(29)
            #   + motion_ref_body_pos(42) + motion_ref_body_vel(42) + motion_ref_body_pos_rel(42)
            SPLIT_691 = [90, 120, 90, 90, 29, 29, 3, 4, 1, 3, 3, 3, 29, 3, 4, 3, 3, 29, 29, 42, 42, 42]
            diffusion_obs_concat = wrapped_env.unwrapped.observation_manager.compute_group("diffusion")
            robot_state, robot_state_np = _parse_diffusion_obs(
                diffusion_obs_concat, SPLIT_691, fk_calculator,
                fk_noise_model=fk_noise_model,
                fk_noise_cfg=fk_noise_cfg,
            )
            if (bfm_diagnostics_enabled or teacher_canary_enabled) and len(bfm_initial_state_diagnostics) < 32:
                collection_term = env_unwrapped.command_manager._terms["motion"]
                for env_idx in np.flatnonzero(env_just_reset):
                    if len(bfm_initial_state_diagnostics) >= 32:
                        break
                    if (
                        int(collection_term.env_task_assignment[env_idx].item()) < 0
                        or int(collection_term.env_is_idle[env_idx].item()) != 0
                    ):
                        continue
                    initial_diag = {
                        "env_idx": int(env_idx),
                        "task_id": int(collection_term.env_task_assignment[env_idx].item()),
                        "motion_idx": int(collection_term.motion_idx[env_idx].item()),
                        "sample_idx": int(collection_term.sample_idx[env_idx].item()),
                        "time_step": int(collection_term.time_steps[env_idx].item()),
                        "root_position_error_m": float(torch.linalg.vector_norm(
                            robot_state["root_pos"][env_idx]
                            - robot_state["motion_ref_root_pos"][env_idx]
                        ).item()),
                        "joint_position_mae_rad": float(torch.mean(torch.abs(
                            robot_state["joint_pos"][env_idx]
                            - robot_state["motion_ref_joint_pos"][env_idx]
                        )).item()),
                        "root_pos": robot_state["root_pos"][env_idx].detach().cpu().tolist(),
                        "root_rot": robot_state["root_rot"][env_idx].detach().cpu().tolist(),
                        "root_lin_vel": robot_state["base_lin_vel"][env_idx].detach().cpu().tolist(),
                        "root_ang_vel": robot_state["base_ang_vel"][env_idx].detach().cpu().tolist(),
                        "joint_pos": robot_state["joint_pos"][env_idx].detach().cpu().tolist(),
                        "joint_vel": robot_state["joint_vel"][env_idx].detach().cpu().tolist(),
                        "reference_root_pos": robot_state["motion_ref_root_pos"][env_idx].detach().cpu().tolist(),
                        "reference_root_rot": robot_state["motion_ref_root_rot"][env_idx].detach().cpu().tolist(),
                        "reference_root_lin_vel": robot_state["motion_ref_root_lin_vel"][env_idx].detach().cpu().tolist(),
                        "reference_root_ang_vel": robot_state["motion_ref_root_ang_vel"][env_idx].detach().cpu().tolist(),
                        "reference_joint_pos": robot_state["motion_ref_joint_pos"][env_idx].detach().cpu().tolist(),
                        "reference_joint_vel": robot_state["motion_ref_joint_vel"][env_idx].detach().cpu().tolist(),
                    }
                    bfm_initial_state_diagnostics.append(initial_diag)
                    print(f"[BFM_BFM_INITIAL_STATE] {json.dumps(initial_diag, sort_keys=True)}")

            # Get action from policy (RLTracker PPO, MimicLite, or BFM-Zero/UFO ONNX).
            if use_mimic_lite and mimic_lite_bridge is not None:
                ml_obs = mimic_lite_bridge.build(robot_state=robot_state)
                actions = mimic_lite_policy(ml_obs)           # returns q_target (joint position targets)
                mimic_lite_bridge.advance(mimic_lite_policy.last_raw_action)  # prev_actions uses raw ONNX output
            elif use_bfm_zero and bfm_zero_policy is not None:
                actions = bfm_zero_policy(robot_state)        # clean normalized RLTracker action
            else:
                actions = policy(obs)

            # Store current state and action for all envs (EXCEPT those that just reset)
            # This ensures we don't store the inconsistent first frame after reset
            for env_idx in range(cfg.task.num_envs):
                if not env_just_reset[env_idx]:  # Only store if env did NOT just reset
                    if "act" in fields_to_save:
                        episode_data["act"][env_idx].append(actions[env_idx].cpu().numpy())
                    for field in fields_to_save:
                        if field != "act":
                            episode_data[field][env_idx].append(robot_state_np[field][env_idx])
                else:
                    # This env just reset, mark as no longer fresh after this iteration
                    env_just_reset[env_idx] = False
            
            # Apply action noise if enabled
            if noise_generator is not None:
                noise = noise_generator.sample()
                actions = actions + noise
                # Optionally clip actions to valid range
                # actions = torch.clamp(actions, -1.0, 1.0)

            if bfm_zero_policy is not None:
                actions = bfm_zero_policy.prepare_execution(actions)
                bfm_zero_policy.advance(actions, robot_state)

            if use_bfm_zero:
                nonfinite_path = _first_nonfinite_tensor(actions, "actions")
                if nonfinite_path is None:
                    nonfinite_path = _first_nonfinite_tensor(robot_state, "robot_state")
                if nonfinite_path is not None:
                    raise RuntimeError(f"BFM BFM rollout became non-finite before env.step: {nonfinite_path}")

            # The command term resamples inside env.step(). Snapshot the task
            # that produced this episode so the outer quality gate can reopen
            # a timeout-completed assignment that it rejects.
            if collection_mode == "deterministic":
                collection_term = env_unwrapped.command_manager._terms["motion"]
                pre_step_task_assignment = collection_term.env_task_assignment.clone()
                pre_step_motion_idx = collection_term.motion_idx.clone()
                pre_step_sample_idx = collection_term.sample_idx.clone()
                pre_step_env_is_idle = collection_term.env_is_idle.clone()
                pre_step_time_steps = collection_term.time_steps.clone()
                pre_step_ee_names = (
                    "left_ankle_roll_link",
                    "right_ankle_roll_link",
                    "left_wrist_yaw_link",
                    "right_wrist_yaw_link",
                )
                pre_step_ee_indices = [
                    collection_term.cfg.body_names.index(name) for name in pre_step_ee_names
                ]
                pre_step_ee_pos_z_error = torch.abs(
                    collection_term.body_pos_relative_w[:, pre_step_ee_indices, 2]
                    - collection_term.robot_body_pos_w[:, pre_step_ee_indices, 2]
                ).clone()

            # Step environment
            obs, rewards, terminated, infos = wrapped_env.step(actions)
            dones = terminated
            # The collection loop does not consistently emit Kit's post-update
            # event, so drive command visualization directly before rendering.
            if reference_debug_vis:
                motion_debug_term._debug_vis_callback(None)
            if record_rgb:
                frame = env_unwrapped.render()
                if frame is not None and "_mjpeg_mod" in locals():
                    _mjpeg_mod.record_rgb_frame(frame)
            if use_bfm_zero:
                nonfinite_path = _first_nonfinite_tensor(obs, "obs")
                if nonfinite_path is None:
                    nonfinite_path = _first_nonfinite_tensor(rewards, "rewards")
                if nonfinite_path is None:
                    nonfinite_path = _first_nonfinite_tensor(terminated, "terminated")
                if nonfinite_path is not None:
                    raise RuntimeError(f"BFM BFM rollout became non-finite after env.step: {nonfinite_path}")

            # Capture the post-step body state and termination-manager outputs
            # used by the q10 timing diagnostic. The pre-step snapshot above is
            # retained because it is the state recorded by the collector; this
            # second snapshot isolates stale derived-body state after physics.
            if collection_mode == "deterministic":
                termination_manager = env_unwrapped.termination_manager
                post_step_ee_pos_z_error = torch.abs(
                    collection_term.body_pos_relative_w[:, pre_step_ee_indices, 2]
                    - collection_term.robot_body_pos_w[:, pre_step_ee_indices, 2]
                ).clone()
                termination_eval_ee_pos_z_error = getattr(
                    collection_term,
                    "bfm_diagnostic_last_ee_body_pos_z_error",
                    post_step_ee_pos_z_error,
                ).clone()
                post_step_termination_terms = {
                    name: termination_manager.get_term(name).clone()
                    for name in termination_manager.active_terms
                }
                post_step_termination_terms.update({
                    name: values.clone()
                    for name, values in getattr(collection_term, "bfm_diagnostic_raw_termination_terms", {}).items()
                })
            
            # Update episode statistics
            episode_lengths += 1
            episode_rewards += rewards.cpu().numpy()
            
            # Check for finished episodes
            if dones.any():
                done_indices = torch.where(dones)[0].cpu().numpy()
                if bfm_zero_policy is not None:
                    bfm_zero_policy.reset(torch.where(dones)[0])
                
                for env_idx in done_indices:
                    total_episodes_collected += 1
                    ep_length = episode_lengths[env_idx]
                    ep_reward = episode_rewards[env_idx]
                    mean_reward = ep_reward / ep_length if ep_length > 0 else 0
                    first_field = fields_to_save[0] if fields_to_save else "act"
                    
                    task_was_active = True
                    if collection_mode == "deterministic":
                        task_was_active = (
                            pre_step_env_is_idle[env_idx].item() == 0
                            and pre_step_task_assignment[env_idx].item() >= 0
                        )
                        if task_was_active and collection_term.last_episode_failed[env_idx]:
                            total_non_timeout_failures += 1
                            if bool(infos["time_outs"][env_idx]):
                                total_failure_motion_end_coincidences += 1
                            if bfm_diagnostics_enabled:
                                termination_manager = env_unwrapped.termination_manager
                                failure_diag = {
                                    "env_idx": int(env_idx),
                                    "motion_idx": int(pre_step_motion_idx[env_idx].item()),
                                    "sample_idx": int(pre_step_sample_idx[env_idx].item()),
                                    "episode_length": int(ep_length),
                                    "pre_step_time_step": int(pre_step_time_steps[env_idx].item()),
                                    "termination_terms": {
                                        name: bool(termination_manager.get_term(name)[env_idx].item())
                                        for name in termination_manager.active_terms
                                    },
                                    "pre_step_root_position_error_m": float(
                                        torch.linalg.vector_norm(
                                            robot_state["root_pos"][env_idx]
                                            - robot_state["motion_ref_root_pos"][env_idx]
                                        ).item()
                                    ),
                                    "pre_step_joint_position_mae_rad": float(torch.mean(torch.abs(
                                        robot_state["joint_pos"][env_idx]
                                        - robot_state["motion_ref_joint_pos"][env_idx]
                                    )).item()),
                                }
                                bfm_failure_diagnostics.append(failure_diag)
                                print(f"[BFM_BFM_FAILURE] {json.dumps(failure_diag, sort_keys=True)}")

                    # Apply quality filters
                    keep_episode = task_was_active
                    duplicate_task = False
                    old_task_id = -1
                    if collection_mode == "deterministic" and task_was_active:
                        old_task_id = int(pre_step_task_assignment[env_idx].item())
                        duplicate_task = old_task_id in saved_task_ids
                        if duplicate_task:
                            keep_episode = False
                        if collection_term.last_episode_failed[env_idx]:
                            keep_episode = False

                        if (
                            bfm_stop_after_first_attempts
                            and old_task_id not in bfm_first_attempts
                            and len(episode_data[first_field][env_idx]) > 0
                        ):
                            from bfm_diagnostic.analyze_canary import analyze_arrays

                            attempt_arrays = {
                                field: np.asarray(
                                    episode_data[field][env_idx],
                                    dtype=np.int64 if field == "motion_idx" else np.float64,
                                )
                                for field in fields_to_save
                            }
                            ee_error = pre_step_ee_pos_z_error[env_idx]
                            termination_manager = env_unwrapped.termination_manager
                            bfm_first_attempts[old_task_id] = {
                                "task_id": old_task_id,
                                "motion_idx": int(pre_step_motion_idx[env_idx].item()),
                                "sample_idx": int(pre_step_sample_idx[env_idx].item()),
                                "outcome": (
                                    "non_timeout_failure"
                                    if bool(collection_term.last_episode_failed[env_idx])
                                    else "completion"
                                ),
                                "episode_length_counter": int(ep_length),
                                "recorded_samples": int(len(attempt_arrays[first_field])),
                                "pre_step_time_step": int(pre_step_time_steps[env_idx].item()),
                                "termination_terms": {
                                    name: bool(termination_manager.get_term(name)[env_idx].item())
                                    for name in termination_manager.active_terms
                                },
                                "ee_body_pos_z_threshold_m": 0.25,
                                "ee_body_pos_z_error_m": {
                                    name: float(error)
                                    for name, error in zip(pre_step_ee_names, ee_error.detach().cpu().tolist())
                                },
                                "ee_body_pos_z_max_error_m": float(torch.max(ee_error).item()),
                                "ee_body_pos_z_max_exceedance_m": float(torch.max(ee_error).item() - 0.25),
                                "post_step_termination_terms": {
                                    name: bool(values[env_idx].item())
                                    for name, values in post_step_termination_terms.items()
                                },
                                "raw_termination_counts": {
                                    name: int(values[env_idx].item())
                                    for name, values in getattr(
                                        collection_term,
                                        "bfm_diagnostic_raw_termination_counts",
                                        {},
                                    ).items()
                                },
                                "post_step_ee_body_pos_z_error_m": {
                                    name: float(error)
                                    for name, error in zip(
                                        pre_step_ee_names,
                                        post_step_ee_pos_z_error[env_idx].detach().cpu().tolist(),
                                    )
                                },
                                "post_step_ee_body_pos_z_max_error_m": float(
                                    torch.max(post_step_ee_pos_z_error[env_idx]).item()
                                ),
                                "post_step_ee_body_pos_z_max_exceedance_m": float(
                                    torch.max(post_step_ee_pos_z_error[env_idx]).item() - 0.25
                                ),
                                "termination_eval_ee_body_pos_z_error_m": {
                                    name: float(error)
                                    for name, error in zip(
                                        pre_step_ee_names,
                                        termination_eval_ee_pos_z_error[env_idx].detach().cpu().tolist(),
                                    )
                                },
                                "termination_eval_ee_body_pos_z_max_error_m": float(
                                    torch.max(termination_eval_ee_pos_z_error[env_idx]).item()
                                ),
                                "termination_eval_ee_body_pos_z_max_exceedance_m": float(
                                    torch.max(termination_eval_ee_pos_z_error[env_idx]).item() - 0.25
                                ),
                                "metrics": analyze_arrays(
                                    attempt_arrays,
                                    source=f"task_id={old_task_id}:first_attempt",
                                ),
                            }
                            if teacher_canary_trace_dir:
                                trace_path = (
                                    Path(teacher_canary_trace_dir).expanduser()
                                    / f"task_{old_task_id:03d}.npz"
                                )
                                trace_path.parent.mkdir(parents=True, exist_ok=True)
                                np.savez_compressed(trace_path, **attempt_arrays)
                                trace_sha256 = hashlib.sha256(trace_path.read_bytes()).hexdigest()
                                bfm_first_attempts[old_task_id]["trace_path"] = str(trace_path)
                                bfm_first_attempts[old_task_id]["trace_sha256"] = trace_sha256
                            print(
                                "[BFM_BFM_FIRST_ATTEMPT] "
                                + json.dumps(bfm_first_attempts[old_task_id], sort_keys=True)
                            )
                        elif (
                            bfm_stop_after_first_attempts
                            and old_task_id not in bfm_first_attempts
                            and len(episode_data[first_field][env_idx]) == 0
                        ):
                            print(
                                "[BFM_BOOTSTRAP_EVENT] ignored zero-sample reset event "
                                f"for task_id={old_task_id}; termination telemetry retained"
                            )
                    
                    if ep_length < 5: # Ignore 1-step episodes (caused by env init)
                        keep_episode = False
                        total_episodes_collected -= 1  # Don't count zero-length episodes

                    # Filter out idle env timeouts (all tasks completed, env is just waiting)
                    if collection_mode == "deterministic":
                        # Check if env is idle from command manager metrics
                        if env_unwrapped.command_manager._terms["motion"].env_is_idle[env_idx] == -1:
                            # Collect this episode, mark as idle
                            env_unwrapped.command_manager._terms["motion"].env_is_idle[env_idx] = 1
                        elif env_unwrapped.command_manager._terms["motion"].env_is_idle[env_idx] == 1:
                            # Skip idle env timeouts
                            keep_episode = False
                            total_episodes_collected -= 1  # Don't count towards collected
                        # In deterministic mode, discard terminated (and not idle)
                        elif not infos["time_outs"][env_idx]:
                            keep_episode = False

                    # Filter by episode length: If is shorter than min length, discard
                    if ep_length < cfg.collection.min_episode_length:
                        keep_episode = False
                    
                    # Filter by mean reward (if specified)
                    if cfg.collection.min_mean_reward is not None and mean_reward < cfg.collection.min_mean_reward:
                        keep_episode = False
                    
                    # MotionCollectionCommand marks a timeout-completed task as
                    # done during env.step(), before this quality gate runs. If
                    # the gate rejects that active episode, reopen its exact
                    # assignment. Never reopen early-failure assignments here:
                    # the command term already retries those atomically.
                    if (collection_mode == "deterministic" and task_was_active
                            and not keep_episode and not duplicate_task
                            and infos["time_outs"][env_idx]):
                        old_motion = int(pre_step_motion_idx[env_idx].item())
                        old_sample = int(pre_step_sample_idx[env_idx].item())
                        collection_term.retry_rejected_timeout(
                            int(env_idx), old_motion, old_sample
                        )
                        print(
                            f"[Collection] Env {env_idx} Reopened after quality rejection: "
                            f"Motion {old_motion}, Sample {old_sample}"
                        )

                    if keep_episode and len(episode_data[first_field][env_idx]) > 0:
                        # Convert lists to numpy arrays; motion_idx uses int64, all others float64
                        ep_data = {
                            field: np.array(
                                episode_data[field][env_idx],
                                dtype=np.int64 if field == "motion_idx" else np.float64,
                            )
                            for field in fields_to_save
                        }
                        
                        # Add episode to buffer
                        buffer.add_episode(ep_data)
                        total_saved_steps += ep_length
                        total_episodes_saved += 1
                        if collection_mode == "deterministic":
                            saved_task_ids.add(old_task_id)
                        
                        # Update progress bar based on mode
                        if collection_mode == "deterministic":
                            pbar.update(1)  # Count episodes
                        else:
                            pbar.update(ep_length)  # Count timesteps
                    
                    # Reset episode data for this environment
                    for key in episode_data:
                        episode_data[key][env_idx] = []
                    episode_lengths[env_idx] = 0
                    episode_rewards[env_idx] = 0
                    
                    # Mark this env as just reset (to skip storing first frame)
                    env_just_reset[env_idx] = True
                    
                    # Reset noise for finished environments if noise is enabled
                    if noise_generator is not None:
                        # Only reset noise for this specific environment
                        noise_generator.state[env_idx] = noise_generator.mu

                    # Reset FK noise for finished environment (new per-episode biases)
                    if fk_noise_model is not None:
                        fk_noise_model.reset_env(env_idx)

                if bfm_stop_after_first_attempts and len(bfm_first_attempts) == target_episodes:
                    bfm_first_attempts_complete = True
                    break

            if bfm_first_attempts_complete:
                break
            
    
    pbar.close()

    if bfm_stop_after_first_attempts:
        attempts = [bfm_first_attempts[index] for index in sorted(bfm_first_attempts)]
        payload = {
            "schema": "bfm-teacher-first-attempt-diagnostic-v1",
            "controller": "bfm_zero_ufo" if use_bfm_zero else "rl_tracker_ppo",
            "complete": len(attempts) == target_episodes,
            "target_attempts": int(target_episodes),
            "recorded_attempts": len(attempts),
            "completion_count": sum(attempt["outcome"] == "completion" for attempt in attempts),
            "non_timeout_failure_count": sum(
                attempt["outcome"] == "non_timeout_failure" for attempt in attempts
            ),
            "initial_state_diagnostics": bfm_initial_state_diagnostics,
            "controller_safety_summary": (
                bfm_zero_policy.safety_summary()
                if use_bfm_zero and bfm_zero_policy is not None
                else None
            ),
            "attempts": attempts,
        }
        report_path = Path(bfm_first_attempt_report_path).expanduser()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"[BFM_TEACHER_FIRST_ATTEMPT_REPORT] {report_path}")
        print(
            "[BFM_TEACHER_FIRST_ATTEMPT_COMPLETE] no partial zarr written: "
            f"{payload['completion_count']} completions, "
            f"{payload['non_timeout_failure_count']} failures"
        )
        env.close()
        simulation_app.close()
        return payload

    if collection_mode == "deterministic" and len(saved_task_ids) != target_episodes:
        raise RuntimeError(
            "Deterministic collection incomplete: "
            f"saved {len(saved_task_ids)}/{target_episodes} unique assignments"
        )
    
    # Print statistics
    print(f"\n[INFO] Data collection complete!")
    print(f"[INFO] Total episodes collected: {total_episodes_collected}")
    print(f"[INFO] Total episodes saved: {total_episodes_saved}")
    print(f"[INFO] Total timesteps saved: {total_saved_steps}")
    print(f"[INFO] Episode retention rate: {total_episodes_saved/max(total_episodes_collected,1)*100:.1f}%")
    
    # Save dataset
    output_path = os.path.join(cfg.output.dir, cfg.output.zarr_name)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[INFO] Saving dataset to {output_path}")
    
    # Sort episodes by motion_idx if requested (ensures motion1: eps0-N, motion2: eps(N+1)-2N, etc.)
    if cfg.output.get('sort_by_motion_idx', False):
        print(f"[INFO] Sorting {buffer.n_episodes} episodes by motion_idx...")
        
        # Extract motion_idx for each episode and create sorting index
        episode_motion_indices = []
        for ep_idx in range(buffer.n_episodes):
            episode = buffer.get_episode(ep_idx, copy=False)
            motion_idx = int(episode['motion_idx'][0])  # Get scalar value
            episode_motion_indices.append((ep_idx, motion_idx))
        
        # Sort by motion_idx (stable sort preserves order within same motion)
        sorted_episodes = sorted(episode_motion_indices, key=lambda x: x[1])
        
        # Create new buffer with sorted episodes
        sorted_buffer = ReplayBuffer.create_empty_numpy()
        for orig_idx, motion_idx in tqdm(sorted_episodes, desc="Sorting episodes"):
            episode_data = buffer.get_episode(orig_idx, copy=True)
            sorted_buffer.add_episode(episode_data)
        
        buffer = sorted_buffer
        print(f"[INFO] Episodes sorted by motion_idx (motion files in order)")
    
    # Set chunk length
    chunk_length = cfg.output.chunk_length if cfg.output.chunk_length > 0 else None
    
    # Save with optimal compression for disk storage
    buffer.save_to_path(
        output_path,
        chunks={field: None for field in fields_to_save} if chunk_length is None else {},
        compressors=cfg.output.compressor,
    )
    
    if use_bfm_zero:
        controller_name = "bfm_zero_ufo"
        controller_config = {
            "actor_path": str(Path(cfg.bfm_zero.actor_path).expanduser().resolve()),
            "backward_path": str(Path(cfg.bfm_zero.backward_path).expanduser().resolve()),
            "policy_yaml_path": str(Path(cfg.bfm_zero.policy_yaml_path).expanduser().resolve()),
            "robot_yaml_path": (
                str(Path(cfg.bfm_zero.robot_yaml_path).expanduser().resolve())
                if str(cfg.bfm_zero.get("robot_yaml_path", "")).strip()
                else None
            ),
            "context_window": int(cfg.bfm_zero.get("context_window", 3)),
            "context_gamma": float(cfg.bfm_zero.get("context_gamma", 0.8)),
            "tracking_seq_length": int(cfg.bfm_zero.get("tracking_seq_length", 1)),
            "backward_angular_velocity_mode": str(
                cfg.bfm_zero.get("backward_angular_velocity_mode", "body_scaled")
            ),
            "extended_head_velocity_mode": str(
                cfg.bfm_zero.get("extended_head_velocity_mode", "finite_difference")
            ),
            "tail_context_mode": str(
                cfg.bfm_zero.get("tail_context_mode", "official_shorten")
            ),
            "context_mode": str(cfg.bfm_zero.get("context_mode", "deploy_gamma")),
            "actor_history_timing": str(
                cfg.bfm_zero.get("actor_history_timing", "deploy_current")
            ),
            "reference_preprocessing_mode": str(
                cfg.bfm_zero.get("reference_preprocessing_mode", "stored_rltracker")
            ),
            "official_robot_xml_path": (
                str(Path(cfg.bfm_zero.official_robot_xml_path).expanduser().resolve())
                if str(cfg.bfm_zero.get("official_robot_xml_path", "")).strip()
                else None
            ),
            "action_adapter": "absolute_q_to_rltracker_normalized",
            "action_target_mode": str(
                cfg.bfm_zero.get("action_target_mode", "deploy_slew")
            ),
            "q_target_slew_safety_factor": bfm_zero_policy.q_target_slew_safety_factor,
            "exact_reference_reset": bool(cfg.bfm_zero.get("exact_reference_reset", False)),
            "termination_grace_steps": int(
                getattr(env_unwrapped.command_manager._terms["motion"].cfg, "termination_grace_steps", 0)
            ),
            "record_only_termination": bool(
                getattr(env_unwrapped.command_manager._terms["motion"].cfg, "record_only_termination", False)
            ),
            "diagnostics_enabled": bfm_diagnostics_enabled,
            "plant_contract": bfm_plant_contract,
            "safety_summary": bfm_zero_policy.safety_summary(),
        }
    elif use_mimic_lite:
        controller_name = "mimic_lite"
        controller_config = {
            "onnx_path": str(Path(onnx_path).expanduser().resolve()),
            "deploy_yaml": str(Path(deploy_yaml_path).expanduser().resolve()) if deploy_yaml_path else None,
        }
    else:
        controller_name = "rl_tracker_ppo"
        controller_config = {"checkpoint": str(Path(cfg.checkpoint.path).expanduser().resolve())}

    # Save metadata
    metadata = {
        'task': cfg.task.name,
        'checkpoint': cfg.checkpoint.path,
        'controller': controller_name,
        'controller_config': controller_config,
        'motion_pattern': cfg.motion.pattern,
        'num_envs': int(cfg.task.num_envs),
        'collection_mode': collection_mode,
        'samples_per_motion': int(cfg.collection.samples_per_motion) if collection_mode == "deterministic" else None,
        'min_episode_length': int(cfg.collection.min_episode_length),
        'min_mean_reward': float(cfg.collection.min_mean_reward) if cfg.collection.min_mean_reward is not None else None,
        'len_to_save': int(cfg.collection.len_to_save),
        'total_episodes_collected': int(total_episodes_collected),
        'total_episodes_saved': int(total_episodes_saved),
        'total_non_timeout_failures': int(total_non_timeout_failures),
        'total_failure_motion_end_coincidences': int(total_failure_motion_end_coincidences),
        'termination_policy': (
            'record_only_failure_predicates_motion_end_and_fixed_horizon_stop'
            if use_bfm_zero and getattr(env_unwrapped.command_manager._terms["motion"].cfg, "record_only_termination", False)
            else 'normal_termination'
        ),
        'termination_predicate_counts': {
            name: values.detach().cpu().tolist()
            for name, values in getattr(
                env_unwrapped.command_manager._terms["motion"],
                "bfm_diagnostic_raw_termination_counts",
                {},
            ).items()
        },
        'bfm_initial_state_diagnostics': bfm_initial_state_diagnostics,
        'bfm_failure_diagnostics': bfm_failure_diagnostics,
        'total_timesteps': int(total_saved_steps),
        'n_episodes': int(buffer.n_episodes),
        'seed': int(cfg.task.seed),
        'noise_enabled': cfg.noise.enable,
        'noise_type': cfg.noise.type if cfg.noise.enable else None,
        'noise_application_space': (
            'rltracker_normalized_execution_action'
            if cfg.noise.enable and use_bfm_zero
            else ('environment_execution_action' if cfg.noise.enable else None)
        ),
        'stored_action_space': (
            'rltracker_normalized_clean_teacher_action'
            if use_bfm_zero
            else ('absolute_joint_target' if use_mimic_lite else 'rltracker_normalized_clean_teacher_action')
        ),
        'noise_params': {
            'theta': cfg.noise.theta,
            'mu': cfg.noise.mu,
            'sigma': cfg.noise.sigma,
            'dt': cfg.noise.dt,
        } if cfg.noise.enable and cfg.noise.type == "ou" else None,
        'fk_enabled': cfg.fk.use_fk,
        'fk_type': cfg.fk.fk_type if cfg.fk.use_fk else None,
        'fk_device': cfg.fk.fk_device if cfg.fk.use_fk else None,
        'fk_noise_enabled': (fk_noise_model is not None),
        'fk_noise_config': fk_noise_model.config_summary() if fk_noise_model is not None else None,
        'fk_record_ground_truth': (fk_noise_cfg is not None and fk_noise_cfg.get("record_ground_truth", False)),
        'push_robot_enabled': push_robot_config['enabled'],
        'push_robot_velocity_range': push_robot_config['velocity_range'],
        'push_robot_interval_range_s': push_robot_config['interval_range_s'],
        'push_robot_post_gym_verified': True,
        'push_robot_runtime_config': runtime_push_robot_config,
        'fields_saved': fields_to_save,
        'creation_time': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"[INFO] Metadata saved to {metadata_path}")
    print(f"[INFO] Dataset contains {buffer.n_episodes} episodes")
    
    # Close environment and simulation
    env.close()
    simulation_app.close()
    
    return metadata


if __name__ == "__main__":
    main()
