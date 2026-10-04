"""
MuJoCo Environment for Loop-Sync Simulation.
Provides a unified interface for controlling G1 robot in MuJoCo simulation
with deterministic loop-sync timing, matching the observation/action format expected by DiffuseCLOC policies.
"""

import numpy as np
import torch
import time
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, fields
from diffusion_policy.env.base_env import BaseEnv
from diffusion_policy.env.deployable_fk_observation import (
    DeployableFKObservationBuilder,
    DeployableFKObservationConfig,
    ProprioceptiveObservationBuilder,
)

try:
    import mujoco
    import mujoco_viewer
    MUJOCO_AVAILABLE = True
except ImportError:
    MUJOCO_AVAILABLE = False
    print("[WARNING] MuJoCo not available. Please install: pip install mujoco mujoco-python-viewer")


# G1 Robot Constants
G1_NUM_MOTOR = 29

# Default PD gains (from deploy_mujoco.py)
DEFAULT_KP = np.array([
    60, 60, 60, 100, 40, 40,      # legs
    60, 60, 60, 100, 40, 40,      # legs
    60, 40, 40,                   # waist
    40, 40, 40, 40, 40, 40, 40,   # arms
    40, 40, 40, 40, 40, 40, 40    # arms
], dtype=np.float32)

DEFAULT_KD = np.array([
    1, 1, 1, 2, 1, 1,     # legs
    1, 1, 1, 2, 1, 1,     # legs
    1, 1, 1,              # waist
    1, 1, 1, 1, 1, 1, 1,  # arms
    1, 1, 1, 1, 1, 1, 1   # arms
], dtype=np.float32)

# Action scale (from deploy_mujoco.py)
DEFAULT_ACTION_SCALE = np.array([
    0.5475464652142303,   # left_hip_pitch
    0.3506614663788243,   # left_hip_roll
    0.5475464652142303,   # left_hip_yaw
    0.3506614663788243,   # left_knee
    0.43857731392336724,  # left_ankle_pitch
    0.43857731392336724,  # left_ankle_roll
    0.5475464652142303,   # right_hip_pitch
    0.3506614663788243,   # right_hip_roll
    0.5475464652142303,   # right_hip_yaw
    0.3506614663788243,   # right_knee
    0.43857731392336724,  # right_ankle_pitch
    0.43857731392336724,  # right_ankle_roll
    0.5475464652142303,   # waist_yaw
    0.43857731392336724,  # waist_roll
    0.43857731392336724,  # waist_pitch
    0.43857731392336724,  # left_shoulder_pitch
    0.43857731392336724,  # left_shoulder_roll
    0.43857731392336724,  # left_shoulder_yaw
    0.43857731392336724,  # left_elbow
    0.43857731392336724,  # left_wrist_roll
    0.07450087032950714,  # left_wrist_pitch
    0.07450087032950714,  # left_wrist_yaw
    0.43857731392336724,  # right_shoulder_pitch
    0.43857731392336724,  # right_shoulder_roll
    0.43857731392336724,  # right_shoulder_yaw
    0.43857731392336724,  # right_elbow
    0.43857731392336724,  # right_wrist_roll
    0.07450087032950714,  # right_wrist_pitch
    0.07450087032950714,  # right_wrist_yaw
], dtype=np.float32)

# Default joint positions (from deploy_mujoco.py)
DEFAULT_JOINT_POS = np.array([-0.312, 0.0, 0.0, 0.669, -0.363, 0.0,
                 -0.312, 0.0, 0.0, 0.669, -0.363, 0.0,
                 0.0, 0.0, 0.0, 
                 0.2, 0.2, 0.0, 0.6, 0.0, 0.0, 0.0, 
                 0.2, -0.2,0.0, 0.6, 0.0, 0.0, 0.0], dtype=np.float32)

# Joint name mappings (IsaacLab <-> MuJoCo)
ISAACLAB_JOINT_NAMES = [
    "left_hip_pitch_joint",
    "right_hip_pitch_joint",
    "waist_yaw_joint",
    "left_hip_roll_joint",
    "right_hip_roll_joint",
    "waist_roll_joint",
    "left_hip_yaw_joint",
    "right_hip_yaw_joint",
    "waist_pitch_joint",
    "left_knee_joint",
    "right_knee_joint",
    "left_shoulder_pitch_joint",
    "right_shoulder_pitch_joint",
    "left_ankle_pitch_joint",
    "right_ankle_pitch_joint",
    "left_shoulder_roll_joint",
    "right_shoulder_roll_joint",
    "left_ankle_roll_joint",
    "right_ankle_roll_joint",
    "left_shoulder_yaw_joint",
    "right_shoulder_yaw_joint",
    "left_elbow_joint",
    "right_elbow_joint",
    "left_wrist_roll_joint",
    "right_wrist_roll_joint",
    "left_wrist_pitch_joint",
    "right_wrist_pitch_joint",
    "left_wrist_yaw_joint",
    "right_wrist_yaw_joint",
]

MUJOCO_JOINT_NAMES = [
    "left_hip_pitch_joint",
    "left_hip_roll_joint",
    "left_hip_yaw_joint",
    "left_knee_joint",
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_hip_pitch_joint",
    "right_hip_roll_joint",
    "right_hip_yaw_joint",
    "right_knee_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
    "waist_yaw_joint",
    "waist_roll_joint",
    "waist_pitch_joint",
    "left_shoulder_pitch_joint",
    "left_shoulder_roll_joint",
    "left_shoulder_yaw_joint",
    "left_elbow_joint",
    "left_wrist_roll_joint",
    "left_wrist_pitch_joint",
    "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint",
    "right_shoulder_roll_joint",
    "right_shoulder_yaw_joint",
    "right_elbow_joint",
    "right_wrist_roll_joint",
    "right_wrist_pitch_joint",
    "right_wrist_yaw_joint",
]

# Create index mappings
ISAACLAB_TO_MUJOCO_REINDEX = [ISAACLAB_JOINT_NAMES.index(name) for name in MUJOCO_JOINT_NAMES]
MUJOCO_TO_ISAACLAB_REINDEX = [MUJOCO_JOINT_NAMES.index(name) for name in ISAACLAB_JOINT_NAMES]
MUJOCO_JOINT_POSITION_SENSOR_NAMES = [name.removesuffix("_joint") + "_pos" for name in MUJOCO_JOINT_NAMES]
MUJOCO_JOINT_VELOCITY_SENSOR_NAMES = [name.removesuffix("_joint") + "_vel" for name in MUJOCO_JOINT_NAMES]


@dataclass
class MuJoCoEnvConfig:
    """Configuration for MuJoCo environment"""
    control_dt: float = 0.02  # 50 Hz control frequency (control decimation)
    simulation_dt: float = 0.002  # 500 Hz simulation frequency
    num_dof: int = 29  # Number of controlled DOFs
    xml_path: str = None  # Path to MuJoCo XML model
    Kp: Optional[np.ndarray] = None  # Custom Kp gains (None = use defaults)
    Kd: Optional[np.ndarray] = None  # Custom Kd gains (None = use defaults)
    action_scale: Optional[np.ndarray] = None  # Action scale (None = use defaults)
    default_joint_pos: Optional[np.ndarray] = None  # Default joint positions (None = use defaults)
    enable_viewer: bool = False  # Enable MuJoCo viewer
    camera_follow: bool = False  # Keep the viewer camera centered on the robot root
    camera_follow_body: str = "pelvis"  # MuJoCo body name; G1 root is pelvis
    camera_lookat_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    camera_lookat_height_offset: float = -0.05  # Vertical offset applied to the followed root position
    camera_follow_yaw: bool = False  # False keeps a world-fixed camera heading
    camera_smoothing_tau: float = 0.0  # Follow damping time constant in seconds
    camera_distance: float = 3.0  # Viewer camera distance
    camera_azimuth: float = 0.0  # Viewer camera azimuth in degrees
    camera_elevation: float = -20.0  # Viewer camera elevation in degrees
    urdf_path: Optional[str] = None  # Path to URDF for FK
    use_fk: bool = True  # Use forward kinematics (True) or direct MuJoCo states (False)
    fk_calculator_type: str = 'pinocchio'  # FK backend: 'pinocchio' or 'torch'
    fk_device: str = 'cpu'  # Torch device for FK computation (only used with fk_calculator_type='torch')
    reset_height: float = 0.3  # Root z below this threshold triggers episode reset
    policy_observation_mode: str = "legacy"
    initial_root_position_m: Tuple[float, float, float] = (0.0, 0.0, 0.8)
    initial_yaw_rad: float = 0.0
    imu_quaternion_sensor: str = "imu_quat"
    imu_gyro_sensor: str = "imu_gyro"
    base_linear_velocity_sensor: str = "frame_vel"
    
    def __post_init__(self):
        # Set defaults
        if self.Kp is None:
            self.Kp = DEFAULT_KP.copy()
        if self.Kd is None:
            self.Kd = DEFAULT_KD.copy()
        if self.action_scale is None:
            self.action_scale = DEFAULT_ACTION_SCALE.copy()
        if self.default_joint_pos is None:
            self.default_joint_pos = DEFAULT_JOINT_POS.copy()

        # Normalize list-like inputs (e.g., Hydra/OmegaConf) to numpy arrays.
        self.Kp = np.asarray(self.Kp, dtype=np.float32)
        self.Kd = np.asarray(self.Kd, dtype=np.float32)
        self.action_scale = np.asarray(self.action_scale, dtype=np.float32)
        self.default_joint_pos = np.asarray(self.default_joint_pos, dtype=np.float32)

        if self.Kp.shape[0] != self.num_dof:
            raise ValueError(f"Kp length ({self.Kp.shape[0]}) must match num_dof ({self.num_dof})")
        if self.Kd.shape[0] != self.num_dof:
            raise ValueError(f"Kd length ({self.Kd.shape[0]}) must match num_dof ({self.num_dof})")
        if self.action_scale.shape[0] != self.num_dof:
            raise ValueError(
                f"action_scale length ({self.action_scale.shape[0]}) must match num_dof ({self.num_dof})"
            )
        if self.default_joint_pos.shape[0] != self.num_dof:
            raise ValueError(
                f"default_joint_pos length ({self.default_joint_pos.shape[0]}) must match num_dof ({self.num_dof})"
            )
        if len(self.camera_lookat_offset) != 3:
            raise ValueError("camera_lookat_offset must contain exactly 3 values")
        if self.camera_smoothing_tau < 0.0:
            raise ValueError("camera_smoothing_tau must be non-negative")
        if self.policy_observation_mode not in {"legacy", "deployable_fk", "proprioceptive_only"}:
            raise ValueError(
                "policy_observation_mode must be 'legacy', 'deployable_fk', or 'proprioceptive_only'"
            )
        self.initial_root_position_m = tuple(float(value) for value in self.initial_root_position_m)
        if len(self.initial_root_position_m) != 3:
            raise ValueError("initial_root_position_m must contain exactly three values")
        if not np.isfinite(self.initial_root_position_m).all():
            raise ValueError("initial_root_position_m must contain finite values")
        self.initial_yaw_rad = float(self.initial_yaw_rad)
        if not np.isfinite(self.initial_yaw_rad):
            raise ValueError("initial_yaw_rad must be finite")
        for field_name in ("imu_quaternion_sensor", "imu_gyro_sensor", "base_linear_velocity_sensor"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty sensor name")
        auxiliary_sensors = (
            self.imu_quaternion_sensor,
            self.imu_gyro_sensor,
            self.base_linear_velocity_sensor,
        )
        joint_sensors = set(MUJOCO_JOINT_POSITION_SENSOR_NAMES + MUJOCO_JOINT_VELOCITY_SENSOR_NAMES)
        if len(set(auxiliary_sensors)) != len(auxiliary_sensors) or joint_sensors.intersection(auxiliary_sensors):
            raise ValueError("deployable auxiliary sensor names must be distinct from each other and joint sensors")
        if self.policy_observation_mode == "deployable_fk" and self.fk_calculator_type != "torch":
            raise ValueError("deployable_fk observations require the batched torch FK backend")
        if self.policy_observation_mode == "proprioceptive_only" and self.use_fk:
            raise ValueError("proprioceptive_only observations require use_fk=false")
        
        # Compute control decimation
        self.control_decimation = int(self.control_dt / self.simulation_dt)
        if abs(self.control_decimation * self.simulation_dt - self.control_dt) > 1e-6:
            raise ValueError(f"control_dt must be a multiple of simulation_dt")


class MuJoCoG1Env(BaseEnv):
    """
    MuJoCo G1 Environment for Loop-Sync Simulation.
    
    Provides observation/action interface compatible with DiffuseCLOC policies:
    - Same interface as UnitreeG1Env for seamless integration
    - Deterministic loop-sync timing (simulation step is controlled by env.step())
    - FK-based observations matching IsaacLab format
    
    Key difference from UnitreeG1Env:
    - Loop-sync: Each step() call advances simulation by exactly control_dt
    - Real-time: UnitreeG1Env.step() doesn't guarantee fixed dt (sim runs independently)
    """
    
    def __init__(self, config: Optional[MuJoCoEnvConfig] = None):
        """
        Initialize MuJoCo G1 environment.
        
        Args:
            config: Environment configuration (uses defaults if None)
        """
        if not MUJOCO_AVAILABLE:
            raise ImportError("MuJoCo not available. Install with: pip install mujoco mujoco-python-viewer")
        
        self.config = self._coerce_config(config)
        
        # Validate config
        if self.config.xml_path is None:
            raise ValueError("xml_path must be provided in config")
        
        # State tracking
        self.initialized: bool = False
        self.step_count: int = 0
        
        # MuJoCo model and data
        self.model = None
        self.data = None
        # These indices are resolved from the loaded MJCF by joint name.  Do
        # not assume that an XML's declaration order is the SDK order: IsaacLab
        # and MuJoCo are allowed to serialize the same named joints differently.
        self._joint_qpos_indices: Optional[np.ndarray] = None
        self._joint_qvel_indices: Optional[np.ndarray] = None
        self._joint_ctrl_indices: Optional[np.ndarray] = None
        self.viewer = None
        self._camera_follow_body_id = None
        self._camera_follower = None
        # Public benchmark wrench state. Forces are specified in the target
        # body's local frame and transformed before every physics substep.
        self._external_body_wrenches: Dict[int, Tuple[np.ndarray, np.ndarray, str]] = {}
        self._external_wrench_substeps = 0
        self._external_wrench_world = np.zeros((0, 6), dtype=np.float64)
        
        # Forward kinematics (optional)
        self.fk_calculator = None
        self.joint_remapping = None
        self.body_names = None
        self.deployable_fk_builder: Optional[DeployableFKObservationBuilder] = None
        self.proprioceptive_builder: Optional[ProprioceptiveObservationBuilder] = None
        self._deployable_policy_obs: Optional[torch.Tensor] = None
        self._deployable_observation_step: Optional[int] = None
        self._deployable_sensor_ids: Dict[str, int] = {}

        # Debug markers — per-frame visual geometry rendered in the viewer.
        # Each marker is a dict of kwargs forwarded to add_marker / mjv_initGeom:
        #   type:   mjtGeom enum (SPHERE, BOX, CYLINDER, CAPSULE, ELLIPSOID,
        #            ARROW, ARROW1, ARROW2, LINE, LINEBOX)
        #   size:   [sx, sy, sz] — sphere: [r, 0, 0]; box: [hx, hy, hz];
        #            cylinder: [r, h, 0]; arrow: [shaft_r, shaft_h, head_r]
        #   pos:    [x, y, z] world-frame centre / base
        #   mat:    [9] flattened 3×3 rotation matrix (default: identity)
        #   rgba:   [r, g, b, a] 0–1
        #   label:  str key (suppressed from geom, used for lifecycle mgmt)
        self._debug_markers: list[dict] = []
        self.body_ids = None
        
        needs_fk = self.config.use_fk or self.config.policy_observation_mode == "deployable_fk"
        if needs_fk:
            # Use configured FK backend
            if self.config.urdf_path is None:
                raise ValueError("urdf_path must be provided when FK observations are enabled")
            from diffusion_policy.utils.g1fk_torch import build_fk_calculator
            self.fk_calculator = build_fk_calculator(
                fk_type=self.config.fk_calculator_type,
                urdf_path=self.config.urdf_path,
                device=self.config.fk_device,
            )
            self.joint_remapping = self.fk_calculator.joint_remapping
            print(f"[MuJoCoG1Env] Using {self.config.fk_calculator_type} FK from {self.config.urdf_path}")
        if self.joint_remapping is None:
            from diffusion_policy.utils.g1_reindex import create_isaaclab_to_mujoco_mapping
            self.joint_remapping = create_isaaclab_to_mujoco_mapping(MUJOCO_JOINT_NAMES)
        from diffusion_policy.utils.g1_reindex import ISAACLAB_BODY_NAMES
        self.body_names = ISAACLAB_BODY_NAMES
        if self.config.policy_observation_mode == "deployable_fk":
            self.deployable_fk_builder = DeployableFKObservationBuilder(
                self.fk_calculator,
                DeployableFKObservationConfig(
                    control_dt=self.config.control_dt,
                    initial_root_position_m=self.config.initial_root_position_m,
                    initial_yaw_rad=self.config.initial_yaw_rad,
                ),
            )
        elif self.config.policy_observation_mode == "proprioceptive_only":
            self.proprioceptive_builder = ProprioceptiveObservationBuilder()
        if not self.config.use_fk:
            print(f"[MuJoCoG1Env] Using direct MuJoCo state extraction (no FK)")
        
        obs_format = (
            "deployable-sensor FK"
            if self.deployable_fk_builder is not None
            else "FK-based" if self.config.use_fk else "Direct MuJoCo"
        )
        print(f"[MuJoCoG1Env] Initialized with {self.config.num_dof} DOFs, dt={self.config.control_dt}s, obs={obs_format}")

    @staticmethod
    def _coerce_config(config: Optional[Any]) -> MuJoCoEnvConfig:
        """Convert incoming config object (including DictConfig) to MuJoCoEnvConfig."""
        if config is None:
            return MuJoCoEnvConfig()
        if isinstance(config, MuJoCoEnvConfig):
            return config

        raw_cfg = config
        try:
            from omegaconf import DictConfig, OmegaConf  # type: ignore

            if isinstance(raw_cfg, DictConfig):
                raw_cfg = OmegaConf.to_container(raw_cfg, resolve=True)
        except Exception:
            pass

        if isinstance(raw_cfg, dict):
            cfg_dict = dict(raw_cfg)
        elif hasattr(raw_cfg, "items"):
            cfg_dict = dict(raw_cfg.items())
        elif hasattr(raw_cfg, "__dict__"):
            cfg_dict = dict(vars(raw_cfg))
        else:
            raise TypeError(f"Unsupported MuJoCo config type: {type(config)}")

        valid_keys = {f.name for f in fields(MuJoCoEnvConfig)}
        filtered = {k: v for k, v in cfg_dict.items() if k in valid_keys}
        return MuJoCoEnvConfig(**filtered)
    
    def initialize(self):
        """Initialize MuJoCo simulation"""
        if self.initialized:
            return
        
        print(f"[MuJoCoG1Env] Loading MuJoCo model from {self.config.xml_path}")
        self.model = mujoco.MjModel.from_xml_path(self.config.xml_path)
        self._resolve_physical_joint_mapping()
        self.data = mujoco.MjData(self.model)
        self._external_wrench_world = np.zeros((self.model.nbody, 6), dtype=np.float64)
        mujoco.mj_forward(self.model, self.data)
        
        # Set simulation timestep
        self.model.opt.timestep = self.config.simulation_dt
        
        # Metrics always retain direct simulator state, independently of the
        # observation path selected for the policy.
        self.body_ids = []
        for body_name in self.body_names:
            body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, body_name)
            if body_id == -1:
                print(f"[WARNING] Body '{body_name}' not found in MuJoCo model")
            self.body_ids.append(body_id)
        print(f"[MuJoCoG1Env] Body ID mapping created for {len(self.body_ids)} bodies")
        if self.deployable_fk_builder is not None or self.proprioceptive_builder is not None:
            self._resolve_deployable_sensors()
        
        # Initialize viewer if requested
        if self.config.enable_viewer:
            self.viewer = mujoco_viewer.MujocoViewer(self.model, self.data)
            self._configure_viewer_camera()
            self._update_viewer_camera()
        
        self.initialized = True
        print(f"[MuJoCoG1Env] MuJoCo simulation initialized")
        print(f"  Simulation dt: {self.config.simulation_dt}s ({1/self.config.simulation_dt:.0f} Hz)")
        print(f"  Control dt: {self.config.control_dt}s ({1/self.config.control_dt:.0f} Hz)")
        print(f"  Control decimation: {self.config.control_decimation}")
    
    def _resolve_physical_joint_mapping(self) -> None:
        """Resolve named physical joints to MuJoCo qpos/qvel/control slots.

        Policy arrays use the canonical IsaacLab order internally and are
        converted to ``MUJOCO_JOINT_NAMES`` order at the physical boundary.
        The latter is a semantic order, rather than an assumption about the
        order in which a particular MJCF declares joints or actuators.
        """
        joint_ids = np.asarray([
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            for name in MUJOCO_JOINT_NAMES
        ], dtype=np.int64)
        if np.any(joint_ids < 0):
            missing = [name for name, joint_id in zip(MUJOCO_JOINT_NAMES, joint_ids) if joint_id < 0]
            raise ValueError(f"MuJoCo XML is missing declared G1 joints: {missing}")
        if len(np.unique(joint_ids)) != len(MUJOCO_JOINT_NAMES):
            raise ValueError("MuJoCo XML maps multiple declared G1 joint names to one joint id")

        qpos_indices = np.asarray(self.model.jnt_qposadr[joint_ids], dtype=np.int64)
        qvel_indices = np.asarray(self.model.jnt_dofadr[joint_ids], dtype=np.int64)
        if len(np.unique(qpos_indices)) != len(MUJOCO_JOINT_NAMES) or len(np.unique(qvel_indices)) != len(MUJOCO_JOINT_NAMES):
            raise ValueError("MuJoCo XML has overlapping G1 qpos/qvel addresses")

        ctrl_by_joint = {}
        for ctrl_index, row in enumerate(np.asarray(self.model.actuator_trnid)):
            actuator_joint_id = int(row[0])
            if actuator_joint_id < 0:
                continue
            if actuator_joint_id in ctrl_by_joint:
                raise ValueError("MuJoCo XML has multiple actuators for a declared G1 joint")
            ctrl_by_joint[actuator_joint_id] = ctrl_index
        missing_actuators = [
            name for name, joint_id in zip(MUJOCO_JOINT_NAMES, joint_ids)
            if int(joint_id) not in ctrl_by_joint
        ]
        if missing_actuators:
            raise ValueError(f"MuJoCo XML is missing actuators for declared G1 joints: {missing_actuators}")

        self._joint_qpos_indices = qpos_indices
        self._joint_qvel_indices = qvel_indices
        self._joint_ctrl_indices = np.asarray([ctrl_by_joint[int(joint_id)] for joint_id in joint_ids], dtype=np.int64)
        print("[MuJoCoG1Env] Resolved named physical mapping for 29 G1 joints")

    def _joint_positions_mujoco(self) -> np.ndarray:
        """Return q in canonical physical MuJoCo order."""
        if self._joint_qpos_indices is None:
            raise RuntimeError("MuJoCo physical joint mapping is not initialized")
        return np.asarray(self.data.qpos[self._joint_qpos_indices], dtype=np.float64).copy()

    def _joint_velocities_mujoco(self) -> np.ndarray:
        """Return dq in canonical physical MuJoCo order."""
        if self._joint_qvel_indices is None:
            raise RuntimeError("MuJoCo physical joint mapping is not initialized")
        return np.asarray(self.data.qvel[self._joint_qvel_indices], dtype=np.float64).copy()

    def _set_joint_positions_mujoco(self, positions: np.ndarray) -> None:
        """Write q in canonical physical MuJoCo order to named qpos slots."""
        if self._joint_qpos_indices is None:
            raise RuntimeError("MuJoCo physical joint mapping is not initialized")
        values = np.asarray(positions, dtype=np.float64)
        if values.shape != (self.config.num_dof,):
            raise ValueError(f"joint position shape mismatch: expected {(self.config.num_dof,)}, got {values.shape}")
        self.data.qpos[self._joint_qpos_indices] = values

    def _set_joint_torques_mujoco(self, torques: np.ndarray) -> None:
        """Write torques in canonical physical MuJoCo order to actuator slots."""
        if self._joint_ctrl_indices is None:
            raise RuntimeError("MuJoCo physical joint mapping is not initialized")
        values = np.asarray(torques, dtype=np.float64)
        if values.shape != (self.config.num_dof,):
            raise ValueError(f"joint torque shape mismatch: expected {(self.config.num_dof,)}, got {values.shape}")
        self.data.ctrl[:] = 0.0
        self.data.ctrl[self._joint_ctrl_indices] = values

    def _validate_physical_joint_order(self) -> None:
        """Compatibility validator for callers that require canonical MJCF order.

        The runtime no longer needs this restriction because the mapping above
        addresses joints and actuators by name.  Keep the explicit validator
        for older audit tools and tests that intentionally reject a reordered
        model.
        """
        self._resolve_physical_joint_mapping()
        if (
            not np.array_equal(self._joint_qpos_indices, np.arange(7, 36, dtype=np.int64))
            or not np.array_equal(self._joint_qvel_indices, np.arange(6, 35, dtype=np.int64))
            or not np.array_equal(self._joint_ctrl_indices, np.arange(len(MUJOCO_JOINT_NAMES), dtype=np.int64))
        ):
            raise ValueError("MuJoCo XML qpos/qvel/actuator order differs from the declared physical joint order")

    def _quat_to_rpy(self, quat: np.ndarray) -> np.ndarray:
        """Convert quaternion (w,x,y,z) to roll-pitch-yaw (Euler angles)"""
        w, x, y, z = quat
        
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        pitch = np.arcsin(np.clip(sinp, -1, 1))
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)
        
        return np.array([roll, pitch, yaw])
    
    def _pd_control(self, target_q: np.ndarray, q: np.ndarray, target_dq: np.ndarray, dq: np.ndarray) -> np.ndarray:
        """Calculate torques from position commands using PD control"""
        return (target_q - q) * self.config.Kp + (target_dq - dq) * self.config.Kd

    def action_to_joint_target(self, action: np.ndarray, *, action_is_isaaclab_order: bool) -> np.ndarray:
        """Map normalized policy actions to absolute MuJoCo-order joint targets."""
        normalized = np.asarray(action, dtype=np.float32)
        if normalized.shape != (self.config.num_dof,):
            raise ValueError(f"Action shape mismatch: expected {self.config.num_dof}, got {normalized.shape}")
        if action_is_isaaclab_order:
            # FK remapping targets its own chain; actuator buffers use physical MuJoCo order.
            normalized = normalized[ISAACLAB_TO_MUJOCO_REINDEX]
        return normalized * self.config.action_scale + self.config.default_joint_pos

    def _configure_viewer_camera(self) -> None:
        """Resolve the configured body by name and initialize camera-only state."""
        self._camera_follow_body_id = None
        self._camera_follower = None
        if not self.config.camera_follow:
            return
        body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, self.config.camera_follow_body)
        if body_id < 0:
            raise ValueError(f"camera_follow_body {self.config.camera_follow_body!r} does not exist in the MuJoCo model")
        from diffusion_policy.env.camera_follow import CameraFollower
        offset = list(self.config.camera_lookat_offset)
        offset[2] += self.config.camera_lookat_height_offset
        self._camera_follow_body_id = body_id
        self._camera_follower = CameraFollower(
            offset=tuple(offset),
            azimuth=self.config.camera_azimuth,
            follow_yaw=self.config.camera_follow_yaw,
            smoothing_tau=self.config.camera_smoothing_tau,
        )

    def _update_viewer_camera(self) -> None:
        """Apply the configured camera pose and optional follow target."""
        if self.viewer is None:
            return

        self.viewer.cam.distance = float(self.config.camera_distance)
        self.viewer.cam.azimuth = float(self.config.camera_azimuth)
        self.viewer.cam.elevation = float(self.config.camera_elevation)

        if self.config.camera_follow:
            lookat, azimuth = self._camera_follower.update(
                self.data.xpos[self._camera_follow_body_id],
                self.data.xquat[self._camera_follow_body_id],
                self.config.control_dt,
            )
            self.viewer.cam.lookat[:] = lookat
            self.viewer.cam.azimuth = azimuth
        else:
            self.viewer.cam.lookat[:] = np.array([0.0, 0.0, 0.7], dtype=np.float64)

    # ── Debug marker rendering ──────────────────────────────────────────

    # Convenience helpers that build a marker dict for common shapes.
    @staticmethod
    def _make_marker(
        type_: int, size: tuple, pos: tuple,
        rgba: tuple = (1.0, 0.2, 0.2, 0.8),
        mat: Optional[np.ndarray] = None, label: str = "_wbg_",
    ) -> dict:
        size = tuple(size) + (0.0,) * (3 - len(size))
        return {
            "type": type_, "size": size[:3], "pos": tuple(pos),
            "mat": np.asarray(mat, dtype=np.float64).flatten() if mat is not None else np.eye(3, dtype=np.float64).flatten(),
            "rgba": tuple(rgba), "label": label,
        }

    # Backward-compatible sphere API — delegates to the generic marker list.
    def set_debug_sphere(self, pos: tuple, radius: float = 0.05,
                         rgba: tuple = (1.0, 0.2, 0.2, 0.8)) -> None:
        """Convenience: show a sphere marker at *pos*.

        Use ``add_debug_marker()`` for other shapes.
        """
        import mujoco as _mj
        self._debug_markers[:] = [self._make_marker(
            _mj.mjtGeom.mjGEOM_SPHERE, (radius, 0, 0), pos, rgba, label="_wbg_sphere",
        )]

    def clear_debug_sphere(self) -> None:
        """Remove all debug markers."""
        self._debug_markers.clear()

    def add_debug_marker(
        self,
        type_: int,
        size: tuple,
        pos: tuple,
        rgba: tuple = (1.0, 0.2, 0.2, 0.8),
        mat: Optional[np.ndarray] = None,
        label: str = "_wbg_",
    ) -> None:
        """Add a persistent per-frame debug marker of any shape.

        Parameters
        ----------
        type_ : int
            ``mujoco.mjtGeom.mjGEOM_SPHERE``, ``mjGEOM_BOX``, ``mjGEOM_CYLINDER``,
            ``mjGEOM_CAPSULE``, ``mjGEOM_ELLIPSOID``, ``mjGEOM_ARROW``, etc.
        size : tuple
            Sphere: ``(radius,)``.  Box: ``(hx, hy, hz)``.
            Cylinder / capsule: ``(radius, half_height)``.
            Ellipsoid: ``(rx, ry, rz)``.
            Arrow: ``(shaft_radius, shaft_half_height, head_radius)``.
        pos : tuple
            World-frame (x, y, z) centre.
        rgba : tuple
            ``(r, g, b, a)`` 0–1.
        mat : np.ndarray | None
            3×3 rotation matrix; ``None`` = identity.
        label : str
            Internal key for lifecycle management.  Markers with the same
            label overwrite each other.
        """
        import mujoco as _mj
        if len(size) < 3:
            size = tuple(size) + (0.0,) * (3 - len(size))
        if mat is None:
            mat = np.eye(3)
        marker = {
            "type": type_, "size": tuple(size[:3]), "pos": tuple(pos),
            "mat": np.asarray(mat, dtype=np.float64).flatten(),
            "rgba": tuple(rgba), "label": label,
        }
        # Replace existing marker with same label, or append
        for i, m in enumerate(self._debug_markers):
            if m.get("label") == label:
                self._debug_markers[i] = marker
                return
        self._debug_markers.append(marker)

    def remove_debug_marker(self, label: str) -> None:
        """Remove the marker with the given *label*."""
        self._debug_markers[:] = [m for m in self._debug_markers if m.get("label") != label]

    def _render_debug_markers(self) -> None:
        """Inject all debug markers into the viewer scene.

        Patches ``viewer._add_marker_to_scene`` once to use
        ``mujoco.mjv_initGeom`` (the official API).
        """
        viewer = self.viewer
        if viewer is None or not MUJOCO_AVAILABLE:
            return

        import mujoco as _mj

        # Remove markers we added last frame (label starts with _wbg_)
        viewer._markers[:] = [
            m for m in viewer._markers
            if not str(m.get("label", "")).startswith("_wbg_")
        ]

        if not self._debug_markers:
            return

        # ── Patch _add_marker_to_scene once ─────────────────────────────
        if not getattr(viewer, "_wbg_patched", False):
            print("[DEBUG_MARKER] Installing mjv_initGeom-based _add_marker_to_scene")

            def _patched_add_marker(marker):
                if viewer.scn.ngeom >= viewer.scn.maxgeom:
                    return
                g = viewer.scn.geoms[viewer.scn.ngeom]
                mtype = marker.get("type", _mj.mjtGeom.mjGEOM_SPHERE)
                size = np.asarray(marker.get("size", [0.1, 0.0, 0.0]), dtype=np.float64)
                pos = np.asarray(marker.get("pos", [0.0, 0.0, 0.0]), dtype=np.float64)
                mat = np.asarray(marker.get("mat", np.eye(3)), dtype=np.float64).flatten()
                rgba = np.asarray(marker.get("rgba", [1.0, 1.0, 1.0, 1.0]), dtype=np.float32)
                _mj.mjv_initGeom(g, mtype, size, pos, mat, rgba)
                viewer.scn.ngeom += 1

            viewer._add_marker_to_scene = _patched_add_marker
            viewer._wbg_patched = True

        # Add all current markers
        for m in self._debug_markers:
            viewer.add_marker(**m)

    def get_observation(self) -> Dict[str, np.ndarray]:
        """
        Get joint-space observation (for compatibility).
        
        Returns:
            Dictionary containing:
                - state: [q (29), dq (29), base_ang_vel (3), projected_gravity (3)] = 64-dim
        """
        if not self.initialized:
            raise RuntimeError("Environment not initialized. Call initialize() first.")
        
        # Get joint positions and velocities (MuJoCo order)
        q_mujoco = self._joint_positions_mujoco()  # [29], named physical order
        dq_mujoco = self._joint_velocities_mujoco()  # [29], named physical order
        
        # Convert to IsaacLab order
        q = q_mujoco[MUJOCO_TO_ISAACLAB_REINDEX]
        dq = dq_mujoco[MUJOCO_TO_ISAACLAB_REINDEX]
        
        # Get base angular velocity (already in body frame)
        base_ang_vel = self.data.qvel[3:6].copy()  # [3]
        
        # Get projected gravity
        quat = self.data.qpos[3:7].copy()  # [w, x, y, z]
        qw, qx, qy, qz = quat
        projected_gravity = np.array([
            2 * (-qz * qx + qw * qy),
            -2 * (qz * qy + qw * qx),
            1 - 2 * (qw * qw + qz * qz)
        ])
        
        # Concatenate observation
        state = np.concatenate([q, dq, base_ang_vel, projected_gravity])
        
        return {'state': state.astype(np.float32)}
    
    def get_fk_observation(self, last_actions: Optional[np.ndarray] = None) -> Dict[str, torch.Tensor]:
        """
        Get FK-based observation or direct MuJoCo state (192-dim body-space state).
        
        Returns:
            dict with torch tensors [1, 1, ...] for batch compatibility:
                - 'body_pos': [1, 1, 30, 3] - body positions
                - 'body_rot': [1, 1, 30, 4] - body rotations (quaternions)
                - 'body_lin_vel': [1, 1, 30, 3] - body linear velocities
                - 'body_ang_vel': [1, 1, 30, 3] - body angular velocities
                - 'joint_pos': [1, 1, 29] - joint positions
                - 'root_pos': [1, 1, 3] - root position
                - 'root_rot': [1, 1, 4] - root rotation (quaternion)
                - 'projected_gravity': [1, 1, 3]
                - 'base_lin_vel': [1, 1, 3] (body frame)
                - 'base_ang_vel': [1, 1, 3] (body frame)
                - 'last_actions': [1, 1, 29]
        """
        if not self.initialized:
            raise RuntimeError("Environment not initialized. Call initialize() first.")
        
        if self.config.use_fk:
            # Use Pinocchio FK computation
            return self._get_fk_observation_pinocchio(last_actions=last_actions)
        else:
            # Use direct MuJoCo state extraction
            return self._get_fk_observation_mujoco(last_actions=last_actions)

    def get_obs_terms(self, last_actions: Optional[np.ndarray] = None) -> Dict[str, torch.Tensor]:
        """BaseEnv observation-term accessor used by ObsComposer."""
        if getattr(self, "proprioceptive_builder", None) is not None:
            return self._terms_from_flat_observation(
                self.proprioceptive_builder.build(self._deployable_sensor_observation(last_actions))
            )
        if self.deployable_fk_builder is not None:
            if self._deployable_policy_obs is None or self._deployable_observation_step is None:
                raise RuntimeError("Deployable FK state is not initialized. Call reset() first.")
            raw_obs = self._deployable_sensor_observation(last_actions)
            if self._deployable_observation_step != self.step_count:
                self._deployable_policy_obs = self.deployable_fk_builder.update(raw_obs)
                self._deployable_observation_step = self.step_count
            else:
                # The action channel can change on a repeated read, but the
                # pose/velocity estimator must advance at most once per step.
                self._deployable_policy_obs = self._deployable_policy_obs.clone()
                self._deployable_policy_obs[:, DeployableFKObservationBuilder.LAST_ACTIONS] = raw_obs[
                    :, DeployableFKObservationBuilder.LAST_ACTIONS
                ]
            return self._terms_from_flat_observation(self._deployable_policy_obs)
        return self.get_fk_observation(last_actions=last_actions)

    def get_metric_obs_terms(self, last_actions: Optional[np.ndarray] = None) -> Dict[str, torch.Tensor]:
        """Return direct MuJoCo state for metrics, reset checks, and rendering only."""
        if not self.initialized:
            raise RuntimeError("Environment not initialized. Call initialize() first.")
        return self._get_fk_observation_mujoco(last_actions=last_actions)

    def policy_observation_provenance(self) -> dict[str, object]:
        if getattr(self, "proprioceptive_builder", None) is not None:
            return {
                **self.proprioceptive_builder.provenance(),
                "mode": "proprioceptive_only",
                "simulator": "mujoco",
                "privileged_simulator_state_allowed": False,
                "mujoco_sensor_channels": self._deployable_sensor_provenance(),
            }
        if self.deployable_fk_builder is None:
            return {
                "schema_version": "policy-observation-provenance-v1",
                "mode": "legacy_fk" if self.config.use_fk else "simulator_state",
                "privileged_simulator_state_allowed": True,
            }
        return {
            **self.deployable_fk_builder.provenance(),
            "mode": "deployable_fk",
            "simulator": "mujoco",
            "privileged_simulator_state_allowed": False,
            "control_dt": float(self.config.control_dt),
            "initial_root_position_m": list(self.config.initial_root_position_m),
            "initial_yaw_rad": float(self.config.initial_yaw_rad),
            "fk_backend": self.config.fk_calculator_type,
            "urdf_path": self.config.urdf_path,
            "mujoco_sensor_channels": self._deployable_sensor_provenance(),
            "sensor_transforms": {
                "projected_gravity": "derived_from_imu_quaternion",
                "base_linear_velocity_body": "world_sensor_rotated_by_inverse_imu_quaternion",
            },
        }

    def privileged_perturbation_terms(self, last_actions: Optional[np.ndarray] = None):
        """Prove that direct simulator body/root fields cannot affect policy terms."""
        if self.deployable_fk_builder is None and getattr(self, "proprioceptive_builder", None) is None:
            raise RuntimeError("privileged perturbation audit requires a deployable policy observation mode")
        raw = self._flat_metric_observation(last_actions)
        mask = torch.ones(raw.shape[1], dtype=torch.bool, device=raw.device)
        for _, field in ProprioceptiveObservationBuilder.ALLOWED_SLICES:
            mask[field] = False
        perturbed = raw.clone()
        values = torch.arange(int(mask.sum().item()), device=raw.device, dtype=raw.dtype)
        perturbed[:, mask] = 17.0 + values.unsqueeze(0)
        if getattr(self, "proprioceptive_builder", None) is not None:
            baseline = self.proprioceptive_builder.build(raw)
            alternate = self.proprioceptive_builder.build(perturbed)
        else:
            config = DeployableFKObservationConfig(
                control_dt=self.config.control_dt,
                initial_root_position_m=self.config.initial_root_position_m,
                initial_yaw_rad=self.config.initial_yaw_rad,
            )
            baseline = DeployableFKObservationBuilder(self.fk_calculator, config).reset(raw)
            alternate = DeployableFKObservationBuilder(self.fk_calculator, config).reset(perturbed)
        baseline_terms = self._terms_from_flat_observation(baseline)
        alternate_terms = self._terms_from_flat_observation(alternate)
        differences = {
            name: float((baseline_terms[name] - alternate_terms[name]).abs().max().item())
            for name in baseline_terms
        }
        return baseline_terms, alternate_terms, {
            "schema_version": "privileged-policy-input-perturbation-v1",
            "status": "pass" if max(differences.values(), default=0.0) == 0.0 else "fail",
            "perturbed_dimensions": int(mask.sum().item()),
            "preserved_dimensions": int((~mask).sum().item()),
            "max_abs_by_term": differences,
            "policy_input_sources": [name for name, _ in ProprioceptiveObservationBuilder.ALLOWED_SLICES],
            "mode": self.config.policy_observation_mode,
        }

    def _deployable_sensor_provenance(self) -> dict[str, object]:
        return {
            "joint_position": list(MUJOCO_JOINT_POSITION_SENSOR_NAMES),
            "joint_velocity": list(MUJOCO_JOINT_VELOCITY_SENSOR_NAMES),
            "imu_quaternion": self.config.imu_quaternion_sensor,
            "imu_angular_velocity_body": self.config.imu_gyro_sensor,
            "base_linear_velocity_world": self.config.base_linear_velocity_sensor,
        }

    def _resolve_deployable_sensors(self) -> None:
        self._deployable_sensor_ids = {}
        names = (
            *MUJOCO_JOINT_POSITION_SENSOR_NAMES,
            *MUJOCO_JOINT_VELOCITY_SENSOR_NAMES,
            self.config.imu_quaternion_sensor,
            self.config.imu_gyro_sensor,
            self.config.base_linear_velocity_sensor,
        )
        dimensions = {
            **{name: 1 for name in MUJOCO_JOINT_POSITION_SENSOR_NAMES},
            **{name: 1 for name in MUJOCO_JOINT_VELOCITY_SENSOR_NAMES},
            self.config.imu_quaternion_sensor: 4,
            self.config.imu_gyro_sensor: 3,
            self.config.base_linear_velocity_sensor: 3,
        }
        resolved: Dict[str, int] = {}
        errors = []
        for name in names:
            sensor_id = int(mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SENSOR, name))
            if sensor_id < 0:
                errors.append(f"missing sensor {name!r}")
                continue
            observed_dim = int(self.model.sensor_dim[sensor_id])
            if observed_dim != dimensions[name]:
                errors.append(f"sensor {name!r} has dimension {observed_dim}, expected {dimensions[name]}")
                continue
            resolved[name] = sensor_id
        if errors:
            raise ValueError("deployable MuJoCo observation sensor contract failed: " + "; ".join(errors))
        self._deployable_sensor_ids = resolved

    def _read_deployable_sensor(self, name: str) -> np.ndarray:
        if name not in self._deployable_sensor_ids:
            raise RuntimeError("Deployable MuJoCo sensor contract is not initialized")
        sensor_id = self._deployable_sensor_ids[name]
        address = int(self.model.sensor_adr[sensor_id])
        dimension = int(self.model.sensor_dim[sensor_id])
        value = np.asarray(self.data.sensordata[address:address + dimension], dtype=np.float32).copy()
        if value.shape != (dimension,) or not np.isfinite(value).all():
            raise ValueError(f"MuJoCo sensor {name!r} returned invalid data")
        return value

    @staticmethod
    def _world_vector_to_body(quaternion_wxyz: np.ndarray, vector_world: np.ndarray) -> np.ndarray:
        w, x, y, z = np.asarray(quaternion_wxyz, dtype=np.float64)
        rotation_world_from_body = np.asarray([
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ])
        return (rotation_world_from_body.T @ np.asarray(vector_world, dtype=np.float64)).astype(np.float32)

    def _deployable_sensor_observation(self, last_actions: Optional[np.ndarray]) -> torch.Tensor:
        q_mujoco = np.asarray(
            [self._read_deployable_sensor(name)[0] for name in MUJOCO_JOINT_POSITION_SENSOR_NAMES],
            dtype=np.float32,
        )
        dq_mujoco = np.asarray(
            [self._read_deployable_sensor(name)[0] for name in MUJOCO_JOINT_VELOCITY_SENSOR_NAMES],
            dtype=np.float32,
        )
        imu_quat = self._read_deployable_sensor(self.config.imu_quaternion_sensor)
        norm = float(np.linalg.norm(imu_quat))
        if norm < 1e-8:
            raise ValueError("MuJoCo IMU quaternion sensor returned a zero quaternion")
        imu_quat = imu_quat / norm
        base_ang_vel_body = self._read_deployable_sensor(self.config.imu_gyro_sensor)
        base_lin_vel_world = self._read_deployable_sensor(self.config.base_linear_velocity_sensor)
        base_lin_vel_body = self._world_vector_to_body(imu_quat, base_lin_vel_world)
        action = np.zeros(self.config.num_dof, dtype=np.float32) if last_actions is None else np.asarray(
            last_actions, dtype=np.float32
        )
        if action.shape == (1, self.config.num_dof):
            action = action[0]
        if action.shape != (self.config.num_dof,) or not np.isfinite(action).all():
            raise ValueError(f"last_actions must have shape ({self.config.num_dof},)")
        raw = torch.zeros(
            (1, DeployableFKObservationBuilder.OBS_DIM),
            device=self.config.fk_device,
            dtype=torch.float32,
        )
        raw[:, DeployableFKObservationBuilder.JOINT_POS] = torch.as_tensor(
            q_mujoco[MUJOCO_TO_ISAACLAB_REINDEX], device=raw.device
        )
        raw[:, DeployableFKObservationBuilder.JOINT_VEL] = torch.as_tensor(
            dq_mujoco[MUJOCO_TO_ISAACLAB_REINDEX], device=raw.device
        )
        raw[:, DeployableFKObservationBuilder.PROJECTED_GRAVITY] = torch.as_tensor(
            self._get_projected_gravity(imu_quat), device=raw.device
        )
        raw[:, DeployableFKObservationBuilder.BASE_LIN_VEL] = torch.as_tensor(
            base_lin_vel_body, device=raw.device
        )
        raw[:, DeployableFKObservationBuilder.BASE_ANG_VEL] = torch.as_tensor(
            base_ang_vel_body, device=raw.device
        )
        raw[:, DeployableFKObservationBuilder.LAST_ACTIONS] = torch.as_tensor(action, device=raw.device)
        return raw

    @staticmethod
    def _terms_from_flat_observation(policy_obs: torch.Tensor) -> Dict[str, torch.Tensor]:
        history = policy_obs.unsqueeze(1)
        count = policy_obs.shape[0]
        return {
            "body_pos": history[:, :, :90].reshape(count, 1, 30, 3),
            "body_rot": history[:, :, 90:210].reshape(count, 1, 30, 4),
            "body_lin_vel": history[:, :, 210:300].reshape(count, 1, 30, 3),
            "body_ang_vel": history[:, :, 300:390].reshape(count, 1, 30, 3),
            "joint_pos": history[:, :, 390:419],
            "joint_vel": history[:, :, 419:448],
            "root_pos": history[:, :, 448:451],
            "root_rot": history[:, :, 451:455],
            "projected_gravity": history[:, :, 456:459],
            "base_lin_vel": history[:, :, 459:462],
            "base_ang_vel": history[:, :, 462:465],
            "last_actions": history[:, :, 465:494],
        }

    def _flat_metric_observation(self, last_actions: Optional[np.ndarray]) -> torch.Tensor:
        metric = self.get_metric_obs_terms(last_actions=last_actions)
        raw = self._deployable_sensor_observation(last_actions)
        raw[:, :90] = metric["body_pos"][:, 0].reshape(1, -1).to(raw)
        raw[:, 90:210] = metric["body_rot"][:, 0].reshape(1, -1).to(raw)
        raw[:, 210:300] = metric["body_lin_vel"][:, 0].reshape(1, -1).to(raw)
        raw[:, 300:390] = metric["body_ang_vel"][:, 0].reshape(1, -1).to(raw)
        raw[:, 448:451] = metric["root_pos"][:, 0].to(raw)
        raw[:, 451:455] = metric["root_rot"][:, 0].to(raw)
        return raw

    def _reset_deployable_observation(self) -> None:
        if self.deployable_fk_builder is None:
            return
        raw_obs = self._deployable_sensor_observation(last_actions=None)
        self._deployable_policy_obs = self.deployable_fk_builder.reset(raw_obs)
        self._deployable_observation_step = self.step_count

    def check_terminate(self) -> bool:
        """Return True if the root z-height is below the configured reset_height."""
        root_z = float(self.data.qpos[2])
        return root_z < self.config.reset_height
    
    def _get_fk_observation_pinocchio(self, last_actions: Optional[np.ndarray] = None) -> Dict[str, torch.Tensor]:
        """Get observation using Pinocchio FK computation."""
        # Get joint data (MuJoCo order)
        q_mujoco = self._joint_positions_mujoco()  # [29], named physical order
        dq_mujoco = self._joint_velocities_mujoco()  # [29], named physical order
        
        # Get base orientation as quaternion (w, x, y, z)
        base_quat = self.data.qpos[3:7].copy()  # [4] (w, x, y, z)
        
        # Get base angular velocity (body frame)
        imu_gyro = self.data.qvel[3:6].copy()  # [3]
        
        # Get base linear velocity (world frame)
        base_lin_vel = self.data.qvel[0:3].copy()  # [3]
        
        # Get base position
        base_pos = self.data.qpos[0:3].copy()  # [3]
        
        # Compute FK – pass quaternion wxyz directly via imu_pose
        fk_result = self.fk_calculator.compute_fk(
            joint_pos=q_mujoco,
            joint_vel=dq_mujoco,
            imu_pose=base_quat,
            imu_gyro=imu_gyro,
            base_lin_vel=base_lin_vel,
            base_pos=base_pos
        )
        
        # Convert to torch tensors with batch and time dimensions
        body_pos = torch.from_numpy(fk_result['body_pos']).double().unsqueeze(0).unsqueeze(0)
        body_rot = torch.zeros((1, 1, 30, 4), dtype=torch.float64)  # Placeholder
        body_lin_vel = torch.from_numpy(fk_result['body_lin_vel']).double().unsqueeze(0).unsqueeze(0)
        body_ang_vel = torch.zeros((1, 1, 30, 3), dtype=torch.float64)  # Placeholder
        body_ang_vel[:, :, 0, :] = torch.from_numpy(fk_result['root_ang_vel']).double().unsqueeze(0).unsqueeze(0)
        # Expose joint states in IsaacLab order for downstream policy normalization.
        q_isaaclab = q_mujoco[MUJOCO_TO_ISAACLAB_REINDEX]
        dq_isaaclab = dq_mujoco[MUJOCO_TO_ISAACLAB_REINDEX]
        joint_pos = torch.from_numpy(q_isaaclab).double().unsqueeze(0).unsqueeze(0)
        joint_vel = torch.from_numpy(dq_isaaclab).double().unsqueeze(0).unsqueeze(0)
        root_pos = torch.from_numpy(fk_result['root_pos']).double().unsqueeze(0).unsqueeze(0)
        root_rot = torch.from_numpy(fk_result['root_rot']).double().unsqueeze(0).unsqueeze(0)

        # RLObs terms expected by G1_Dataset_RLObs
        projected_gravity_np = self._get_projected_gravity(fk_result['root_rot'])
        base_lin_vel_body_np = self._quat_rotate(fk_result['root_rot'], fk_result['root_lin_vel'])
        base_ang_vel_body_np = fk_result['root_ang_vel']
        if last_actions is None:
            last_actions = np.zeros(self.config.num_dof, dtype=np.float64)

        projected_gravity = torch.from_numpy(projected_gravity_np).double().unsqueeze(0).unsqueeze(0)
        base_lin_vel_body = torch.from_numpy(base_lin_vel_body_np).double().unsqueeze(0).unsqueeze(0)
        base_ang_vel_body = torch.from_numpy(base_ang_vel_body_np).double().unsqueeze(0).unsqueeze(0)
        last_actions_t = torch.from_numpy(last_actions).double().unsqueeze(0).unsqueeze(0)
        
        return {
            'body_pos': body_pos,
            'body_rot': body_rot,
            'body_lin_vel': body_lin_vel,
            'body_ang_vel': body_ang_vel,
            'joint_pos': joint_pos,
            'joint_vel': joint_vel,
            'root_pos': root_pos,
            'root_rot': root_rot,
            'projected_gravity': projected_gravity,
            'base_lin_vel': base_lin_vel_body,
            'base_ang_vel': base_ang_vel_body,
            'last_actions': last_actions_t,
        }
    
    def _get_fk_observation_mujoco(self, last_actions: Optional[np.ndarray] = None) -> Dict[str, torch.Tensor]:
        """Get observation by directly reading MuJoCo body states."""
        # Get joint positions in MuJoCo order
        q_mujoco = self._joint_positions_mujoco()  # [29], named physical order
        
        # Extract body positions and velocities directly from MuJoCo
        body_pos = np.zeros((30, 3), dtype=np.float64)
        body_rot = np.zeros((30, 4), dtype=np.float64)
        body_lin_vel = np.zeros((30, 3), dtype=np.float64)
        body_ang_vel = np.zeros((30, 3), dtype=np.float64)
        
        # base_ang_vel = self.data.qvel[3:6].copy()  # [3]
        # base_rot_mat = self.data.xmat[1].reshape(3, 3)  # Base rotation matrix
        base_pos = self.data.qpos[0:3].copy()  # [3]
        for i, body_id in enumerate(self.body_ids):
            if body_id == -1:
                continue  # Skip bodies not found in model
            
            # Body position in world frame
            body_pos[i] = self.data.xpos[body_id].copy()
            
            # Body orientation (quaternion: w, x, y, z)
            body_rot[i] = self.data.xquat[body_id].copy()
            
            # Body velocity (spatial velocity: angular, linear)
            # MuJoCo stores cvel as [angular, linear] in body frame
            body_ang_vel_local = self.data.cvel[body_id, :3].copy()  # Angular velocity
            body_lin_vel_local = self.data.cvel[body_id, 3:].copy()  # Linear velocity
            
            # Transform velocities to world frame using body rotation matrix
            body_ang_vel[i] = body_ang_vel_local
            body_lin_vel[i] = body_lin_vel_local + np.cross(body_ang_vel_local, body_pos[i] - base_pos)  # v = v_local + w x r
        
        # Get root (pelvis) state
        root_pos = self.data.qpos[0:3].copy()  # [3]
        root_rot = self.data.qpos[3:7].copy()  # [4] quaternion (w, x, y, z)
        
        # Get joint velocities in MuJoCo order
        dq_mujoco = self._joint_velocities_mujoco()  # [29], named physical order
        
        # Convert to torch tensors with batch and time dimensions
        body_pos_t = torch.from_numpy(body_pos).double().unsqueeze(0).unsqueeze(0)
        body_rot_t = torch.from_numpy(body_rot).double().unsqueeze(0).unsqueeze(0)
        body_lin_vel_t = torch.from_numpy(body_lin_vel).double().unsqueeze(0).unsqueeze(0)
        body_ang_vel_t = torch.from_numpy(body_ang_vel).double().unsqueeze(0).unsqueeze(0)
        # Expose joint states in IsaacLab order for downstream policy normalization.
        q_isaaclab = q_mujoco[MUJOCO_TO_ISAACLAB_REINDEX]
        dq_isaaclab = dq_mujoco[MUJOCO_TO_ISAACLAB_REINDEX]
        joint_pos_t = torch.from_numpy(q_isaaclab).double().unsqueeze(0).unsqueeze(0)
        joint_vel_t = torch.from_numpy(dq_isaaclab).double().unsqueeze(0).unsqueeze(0)
        root_pos_t = torch.from_numpy(root_pos).double().unsqueeze(0).unsqueeze(0)
        root_rot_t = torch.from_numpy(root_rot).double().unsqueeze(0).unsqueeze(0)

        # RLObs terms expected by G1_Dataset_RLObs
        projected_gravity_np = self._get_projected_gravity(root_rot)
        base_lin_vel_body_np = self._quat_rotate(root_rot, body_lin_vel[0])
        base_ang_vel_body_np = self._quat_rotate(root_rot, body_ang_vel[0])
        if last_actions is None:
            last_actions = np.zeros(self.config.num_dof, dtype=np.float64)

        projected_gravity_t = torch.from_numpy(projected_gravity_np).double().unsqueeze(0).unsqueeze(0)
        base_lin_vel_t = torch.from_numpy(base_lin_vel_body_np).double().unsqueeze(0).unsqueeze(0)
        base_ang_vel_t = torch.from_numpy(base_ang_vel_body_np).double().unsqueeze(0).unsqueeze(0)
        last_actions_t = torch.from_numpy(last_actions).double().unsqueeze(0).unsqueeze(0)
        
        return {
            'body_pos': body_pos_t,
            'body_rot': body_rot_t,
            'body_lin_vel': body_lin_vel_t,
            'body_ang_vel': body_ang_vel_t,
            'joint_pos': joint_pos_t,
            'joint_vel': joint_vel_t,
            'root_pos': root_pos_t,
            'root_rot': root_rot_t,
            'projected_gravity': projected_gravity_t,
            'base_lin_vel': base_lin_vel_t,
            'base_ang_vel': base_ang_vel_t,
            'last_actions': last_actions_t,
        }
    
    def get_tracking_observation(self, motion_loader, motion_t: int, last_actions: np.ndarray, init_frame_data: dict) -> np.ndarray:
        """
        Get observation for motion tracking policy (428-dim).
        
        Args:
            motion_loader: MotionLoader instance with reference motion data
            motion_t: Current frame index in motion
            last_actions: Last executed actions [29] in IsaacLab order
            init_frame_data: Initial frame data with 'pos' and 'rot' for world frame alignment
        
        Returns:
            Observation array [428] = command(290) + anchor_pos(15) + anchor_ori(30) + proj_grav(3) + 
                                     base_lin_vel(3) + base_ang_vel(3) + joint_pos(29) + joint_vel(29) + last_actions(29)
        """
        if not self.initialized:
            raise RuntimeError("Environment not initialized. Call initialize() first.")
        
        # Get current state (MuJoCo order)
        q_mujoco = self._joint_positions_mujoco()  # [29], named physical order
        dq_mujoco = self._joint_velocities_mujoco()  # [29], named physical order
        base_quat = self.data.qpos[3:7].copy()  # [4] (w, x, y, z)
        base_ang_vel = self.data.qvel[3:6].copy()  # [3]
        base_lin_vel = self.data.qvel[0:3].copy()  # [3]
        base_pos = self.data.qpos[0:3].copy()  # [3]
        
        # Convert to IsaacLab order for observation
        q_isaaclab = q_mujoco[MUJOCO_TO_ISAACLAB_REINDEX]
        dq_isaaclab = dq_mujoco[MUJOCO_TO_ISAACLAB_REINDEX]
        
        # Get default joint positions in IsaacLab order
        default_q_isaaclab = self.config.default_joint_pos[MUJOCO_TO_ISAACLAB_REINDEX]
        
        # 1. Command (290): future dof_pos + dof_vel [5 * (29 + 29)]
        command = motion_loader.get_command(motion_t, horizon=5)  # [290]
        
        # 2 & 3. Motion anchor positions (15) and orientations (30): 
        # Get pelvis anchor body across 5 future timesteps, transformed to body frame
        anchor_pos_body, anchor_ori_6d = self._compute_anchor_observations(
            motion_loader, motion_t, base_pos, base_quat, init_frame_data
        )
        
        # 4. Projected gravity (3)
        proj_gravity = self._get_projected_gravity(base_quat)
        
        # BUG: base_lin_vel_body and base_ang_vel_body may not be correctly computed
        # 5. Base linear velocity (3) - in body frame
        # base_lin_vel is already in world frame, convert to body
        base_lin_vel_body = self._quat_rotate_inverse(base_quat, base_lin_vel)
        
        # 6. Base angular velocity (3) - already in body frame
        base_ang_vel_body = base_ang_vel
        
        # 7. Joint positions relative to default (29) - IsaacLab order
        joint_pos_rel = q_isaaclab - default_q_isaaclab
        
        # 8. Joint velocities (29) - IsaacLab order
        joint_vel = dq_isaaclab
        
        # 9. Last actions (29) - already in IsaacLab order
        last_actions_obs = last_actions
        
        # Concatenate all observations
        obs = np.concatenate([
            command,             # 290
            anchor_pos_body,     # 15
            anchor_ori_6d,       # 30
            proj_gravity,        # 3
            base_lin_vel_body,   # 3
            base_ang_vel_body,   # 3
            joint_pos_rel,       # 29
            joint_vel,           # 29
            last_actions_obs     # 29
        ])  # Total: 431 dimensions
        
        return obs.astype(np.float32)
    
    def _compute_anchor_observations(self, motion_loader, motion_t: int, robot_pos: np.ndarray,
                                     robot_quat: np.ndarray, init_frame_data: dict) -> tuple:
        """
        Compute anchor body observations matching C++ observation_computer.cpp.
        
        Returns:
            (anchor_pos_body [15], anchor_ori_6d [30])
        """
        pos_b = np.zeros(15, dtype=np.float32)  # 5 timesteps * 3
        ori_b = np.zeros(30, dtype=np.float32)  # 5 timesteps * 6
        
        if motion_t < 0:
            return pos_b, ori_b
        
        # Get init frame transforms
        ref_init_pos = init_frame_data['ref_pos']  # Reference initial position
        ref_init_quat = init_frame_data['ref_quat']  # Reference initial heading quat
        robot_init_pos = init_frame_data['robot_pos']  # Robot initial position  
        ref_to_robot_quat = init_frame_data['ref_to_robot_quat']  # Transform quat
        
        num_frames = motion_loader.num_frames
        
        # Iterate over 5 future timesteps
        for i in range(5):
            step_idx = min(motion_t + i, num_frames - 1)
            
            # Get reference anchor body (pelvis) pose at this timestep
            ref_pos, ref_quat = motion_loader.get_anchor_body_pose_at_frame(step_idx)
            
            # Transform from reference frame to robot frame
            ref_pos_b, ref_quat_b = self._transform_ref_to_robot_frame(
                ref_pos, ref_quat, ref_init_pos, ref_init_quat, 
                robot_init_pos, ref_to_robot_quat
            )
            
            # Transform to current body frame using subtract_frame_transforms
            pos_b_step, quat_b_step = self._subtract_frame_transforms(
                robot_pos, robot_quat, ref_pos_b, ref_quat_b
            )
            
            # Store position
            pos_b[i*3:(i+1)*3] = pos_b_step
            
            # Convert quaternion to 6D rotation (first 2 rows of rotation matrix)
            rot_mat = self._quat_to_rotation_matrix(quat_b_step)
            ori_b[i*6:(i+1)*6] = [
                rot_mat[0, 0], rot_mat[0, 1],  # First row, first 2 cols
                rot_mat[1, 0], rot_mat[1, 1],  # Second row, first 2 cols  
                rot_mat[2, 0], rot_mat[2, 1]   # Third row, first 2 cols
            ]
        
        return pos_b, ori_b
    
    def _transform_ref_to_robot_frame(self, ref_pos: np.ndarray, ref_quat: np.ndarray,
                                      ref_init_pos: np.ndarray, ref_init_quat: np.ndarray,
                                      robot_init_pos: np.ndarray, ref_to_robot_quat: np.ndarray) -> tuple:
        """
        Transform reference motion pose to robot frame (matching C++ transform_ref_to_robot_frame).
        
        Returns:
            (pos_new, quat_new)
        """
        # Transform position: robot_init_pos + quat_apply(ref_init_quat_inv, ref_pos - ref_init_pos)
        ref_init_quat_inv = self._quat_inv(ref_init_quat)
        pos_diff = ref_pos - ref_init_pos
        pos_rel = self._quat_apply(ref_init_quat_inv, pos_diff)
        pos_new = robot_init_pos + pos_rel
        
        # Transform quaternion: ref_to_robot_quat * ref_quat
        quat_new = self._quat_mul(ref_to_robot_quat, ref_quat)
        
        return pos_new, quat_new
    
    def _subtract_frame_transforms(self, pos_a: np.ndarray, quat_a: np.ndarray,
                                   pos_b: np.ndarray, quat_b: np.ndarray) -> tuple:
        """
        Compute relative transform from frame A to frame B (matching C++ subtract_frame_transforms).
        
        Returns:
            (relative_pos, relative_quat)
        """
        # q10 = quat_inv(quat_a)
        q10 = self._quat_inv(quat_a)
        
        # q12 = quat_mul(q10, quat_b)
        q12 = self._quat_mul(q10, quat_b)
        
        # t12 = quat_apply(q10, pos_b - pos_a)
        pos_diff = pos_b - pos_a
        t12 = self._quat_apply(q10, pos_diff)
        
        return t12, q12
    
    def _quat_mul(self, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        """Multiply two quaternions [w, x, y, z]."""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ], dtype=np.float32)
    
    def _quat_inv(self, q: np.ndarray) -> np.ndarray:
        """Invert quaternion [w, x, y, z]."""
        w, x, y, z = q
        norm_sq = w*w + x*x + y*y + z*z
        if norm_sq < 1e-8:
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        return np.array([w, -x, -y, -z], dtype=np.float32) / norm_sq
    
    def _quat_apply(self, q: np.ndarray, v: np.ndarray) -> np.ndarray:
        """Apply quaternion rotation to vector."""
        w, x, y, z = q
        vx, vy, vz = v
        
        # Compute q * [0, v] * q_conj
        return np.array([
            vx + 2*y*(w*vz - x*vy) + 2*z*(-w*vy - x*vz),
            vy + 2*z*(w*vx - y*vz) + 2*x*(-w*vz - y*vx),
            vz + 2*x*(w*vy - z*vx) + 2*y*(-w*vx - z*vy)
        ], dtype=np.float32)
    
    def _quat_to_rotation_matrix(self, quat: np.ndarray) -> np.ndarray:
        """Convert quaternion [w,x,y,z] to 3x3 rotation matrix."""
        w, x, y, z = quat
        return np.array([
            [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
        ], dtype=np.float32)
    
    def _transform_positions_to_body_frame(self, positions_world: np.ndarray, base_pos: np.ndarray, 
                                           base_quat: np.ndarray, init_frame_data: dict) -> np.ndarray:
        """Transform world positions to body frame relative to init frame."""
        # Subtract init frame position (align world coordinate)
        positions_aligned = positions_world - init_frame_data['pos']
        
        # Transform to current body frame
        positions_body = np.array([
            self._quat_rotate_inverse(base_quat, pos - base_pos)
            for pos in positions_aligned
        ])
        
        return positions_body
    
    def _get_projected_gravity(self, quat: np.ndarray) -> np.ndarray:
        """Get projected gravity vector from quaternion (w,x,y,z)."""
        qw, qx, qy, qz = quat
        return np.array([
            2 * (-qz * qx + qw * qy),
            -2 * (qz * qy + qw * qx),
            1 - 2 * (qw * qw + qz * qz)
        ], dtype=np.float32)
    
    def _quat_rotate_inverse(self, quat: np.ndarray, vec: np.ndarray) -> np.ndarray:
        """Rotate vector by inverse of quaternion (w,x,y,z)."""
        qw, qx, qy, qz = quat
        # Conjugate quaternion for inverse rotation
        quat_conj = np.array([qw, -qx, -qy, -qz])
        
        # Apply rotation: v' = q_conj * [0, v] * q
        # Simplified formula
        t = 2 * np.cross(quat_conj[1:], vec)
        return vec - quat_conj[0] * t + np.cross(quat_conj[1:], t)

    def _quat_rotate(self, quat: np.ndarray, vec: np.ndarray) -> np.ndarray:
        """Rotate vector by quaternion (w,x,y,z)."""
        qw, qx, qy, qz = quat
        q_xyz = np.array([qx, qy, qz], dtype=np.float64)
        vec = np.asarray(vec, dtype=np.float64)
        t = 2.0 * np.cross(q_xyz, vec)
        return vec - qw * t + np.cross(q_xyz, t)
    
    def step(self, action: np.ndarray, action_is_isaaclab_order: bool = False) -> Tuple[Dict[str, np.ndarray], float, bool, Dict]:
        """
        Execute one control step (loop-sync: advances simulation by exactly control_dt).
        
        Args:
            action: Target joint positions [q_target (num_dof)]
                   If action_is_isaaclab_order=True: IsaacLab order (will be transformed)
                   If action_is_isaaclab_order=False: MuJoCo order (used directly)
            action_is_isaaclab_order: Whether action needs IsaacLab->MuJoCo transformation
        
        Returns:
            obs: Next observation (None if FK not enabled, use get_fk_observation())
            reward: Reward (always 0 for deployment)
            done: Episode done flag (always False for deployment)
            info: Additional info dict
        """
        if not self.initialized:
            raise RuntimeError("Environment not initialized. Call initialize() first.")
        
        action_mujoco = self.action_to_joint_target(
            action, action_is_isaaclab_order=action_is_isaaclab_order)
        
        # Compute target joint positions (action_mujoco is already target positions)
        target_q = action_mujoco
        target_dq = np.zeros(self.config.num_dof)
        
        self._external_wrench_substeps = 0
        # Execute control_decimation simulation steps
        for _ in range(self.config.control_decimation):
            # Get current joint state
            q = self._joint_positions_mujoco()
            dq = self._joint_velocities_mujoco()
            
            # Compute torques using PD control
            tau = self._pd_control(target_q, q, target_dq, dq)
            
            # Apply torques
            self._set_joint_torques_mujoco(tau)

            self._apply_external_body_wrenches()
            
            # Step simulation
            mujoco.mj_step(self.model, self.data)
            
        # Update viewer if enabled
        if self.viewer is not None:
            self._update_viewer_camera()
            self._render_debug_markers()
            self.viewer.render()
        
        self.step_count += 1
        
        # Return None for obs (use get_fk_observation() separately)
        return None, 0.0, False, {}

    def set_external_body_wrench(
        self,
        body_name: str,
        force_body: np.ndarray,
        torque_body: Optional[np.ndarray] = None,
    ) -> None:
        """Set a persistent body-local wrench using MuJoCo's public buffer.

        The body-local command is re-expressed in world coordinates before
        every physics substep, matching a force whose direction is attached
        to the moving body instead of a world-fixed impulse.
        """
        if not self.initialized:
            raise RuntimeError("Environment not initialized. Call initialize() first.")
        body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        if body_id < 0:
            raise ValueError(f"unknown MuJoCo body: {body_name!r}")
        force = np.asarray(force_body, dtype=np.float64)
        torque = np.zeros(3, dtype=np.float64) if torque_body is None else np.asarray(torque_body, dtype=np.float64)
        if force.shape != (3,) or torque.shape != (3,) or not np.isfinite(force).all() or not np.isfinite(torque).all():
            raise ValueError("external force and torque must be finite three-vectors")
        self._external_body_wrenches[body_id] = (force.copy(), torque.copy(), "body_local")

    def set_external_body_wrench_world(
        self,
        body_name: str,
        force_world: np.ndarray,
        torque_world: Optional[np.ndarray] = None,
    ) -> None:
        """Set a persistent world-frame wrench at a body's center of mass."""
        if not self.initialized:
            raise RuntimeError("Environment not initialized. Call initialize() first.")
        body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        if body_id < 0:
            raise ValueError(f"unknown MuJoCo body: {body_name!r}")
        force = np.asarray(force_world, dtype=np.float64)
        torque = np.zeros(3, dtype=np.float64) if torque_world is None else np.asarray(torque_world, dtype=np.float64)
        if force.shape != (3,) or torque.shape != (3,) or not np.isfinite(force).all() or not np.isfinite(torque).all():
            raise ValueError("external force and torque must be finite three-vectors")
        self._external_body_wrenches[body_id] = (force.copy(), torque.copy(), "world")

    def clear_external_body_wrenches(self) -> None:
        """Clear all benchmark wrenches and the public MuJoCo force buffer."""
        self._external_body_wrenches.clear()
        self._external_wrench_substeps = 0
        if self.data is not None:
            self.data.xfrc_applied.fill(0.0)
        self._external_wrench_world.fill(0.0)

    def external_body_wrench_audit(self, body_name: str) -> Dict[str, np.ndarray]:
        """Return requested body-local and last applied world-frame wrench."""
        if not self.initialized:
            raise RuntimeError("Environment not initialized. Call initialize() first.")
        body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        if body_id < 0:
            raise ValueError(f"unknown MuJoCo body: {body_name!r}")
        force, torque, frame = self._external_body_wrenches.get(
            body_id, (np.zeros(3, dtype=np.float64), np.zeros(3, dtype=np.float64), "none"))
        return {
            "body_id": np.asarray(body_id, dtype=np.int64),
            "force_body": force.copy(),
            "torque_body": torque.copy(),
            "requested_frame": frame,
            "application_point": "body_center_of_mass",
            "last_step_substeps_applied": getattr(self, "_external_wrench_substeps", 0),
            "wrench_world": self._external_wrench_world[body_id].copy(),
            "xfrc_applied": self.data.xfrc_applied[body_id].copy(),
        }

    def _apply_external_body_wrenches(self) -> None:
        # The viewer clears and rebuilds mouse perturbations. Refresh them at
        # physics rate, then add benchmark forces without erasing Ctrl-drag.
        if self.viewer is not None:
            self.viewer.apply_perturbations()
        elif self._external_body_wrenches or np.any(self._external_wrench_world):
            # A headless web session writes its force directly before step().
            # Only take ownership of the buffer when benchmark forces are used.
            self.data.xfrc_applied.fill(0.0)
        self._external_wrench_world.fill(0.0)
        for body_id, (force_body, torque_body, frame) in self._external_body_wrenches.items():
            if frame == "body_local":
                rotation_world_from_body = self.data.xmat[body_id].reshape(3, 3)
                wrench_world = np.concatenate((
                    rotation_world_from_body @ force_body,
                    rotation_world_from_body @ torque_body,
                ))
            else:
                wrench_world = np.concatenate((force_body, torque_body))
            self.data.xfrc_applied[body_id] += wrench_world
            self._external_wrench_world[body_id] = wrench_world
        if self._external_body_wrenches:
            self._external_wrench_substeps = getattr(self, "_external_wrench_substeps", 0) + 1
    
    def reset(
        self,
        target_pos: Optional[np.ndarray] = None,
        root_pos: Optional[np.ndarray] = None,
        root_quat_wxyz: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Reset the simulation environment to initial state.
        
        Args:
            target_pos: Target joint positions for reset (MuJoCo order, None = use defaults)
            root_pos: Optional initial root position in world coordinates.
            root_quat_wxyz: Optional initial root quaternion in MuJoCo wxyz order.
        
        Returns:
            Initial observation after reset
        """
        if not self.initialized:
            self.initialize()
        
        print("[MuJoCoG1Env] Resetting environment...")
        self.clear_external_body_wrenches()
        
        # Reset simulation state
        mujoco.mj_resetData(self.model, self.data)
        if self._camera_follower is not None:
            self._camera_follower.reset()
        
        # Set initial joint positions
        if target_pos is not None:
            self._set_joint_positions_mujoco(target_pos)
        else:
            self._set_joint_positions_mujoco(self.config.default_joint_pos)
        # Set initial base pose.
        initial_root_pos = np.array([0.0, 0.0, 0.78]) if root_pos is None else np.asarray(root_pos, dtype=np.float64)
        initial_root_quat = (
            np.array([1.0, 0.0, 0.0, 0.0])
            if root_quat_wxyz is None else np.asarray(root_quat_wxyz, dtype=np.float64)
        )
        if initial_root_pos.shape != (3,) or not np.isfinite(initial_root_pos).all():
            raise ValueError("root_pos must be a finite three-vector")
        if initial_root_quat.shape != (4,) or not np.isfinite(initial_root_quat).all():
            raise ValueError("root_quat_wxyz must be a finite four-vector")
        quat_norm = float(np.linalg.norm(initial_root_quat))
        if quat_norm < 1e-8:
            raise ValueError("root_quat_wxyz must be nonzero")
        self.data.qpos[0:3] = initial_root_pos
        self.data.qpos[3:7] = initial_root_quat / quat_norm
        self.data.qvel[:] = 0.0  # Zero velocities
        self.data.ctrl[:] = 0.0  # Zero controls
        # Step once to update kinematics
        mujoco.mj_step(self.model, self.data)

        if self.viewer is not None:
            self._update_viewer_camera()
        
        self.step_count = 0
        self._reset_deployable_observation()
        
        print("[MuJoCoG1Env] Reset complete")
        
        # Return current observation
        return self.get_observation()
    
    def close(self):
        """Cleanup resources"""
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None
        
        self.initialized = False
        self._deployable_policy_obs = None
        self._deployable_observation_step = None
        self._deployable_sensor_ids = {}
        print("[MuJoCoG1Env] Environment closed")
