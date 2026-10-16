"""Configuration for G1 robot with diffusion policy deployment."""

from isaaclab.utils import configclass
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise

from rl_tracker.robots.g1 import G1_ACTION_SCALE, G1_CYLINDER_CFG
from rl_tracker.tasks.tracking.tracking_env_cfg import TrackingEnvCfg, ProjGravObservationsCfg
from rl_tracker.tasks.tracking.config.g1.flat_env_cfg import G1FlatProjGravObsEnvCfg_MotionEndReset
import rl_tracker.tasks.tracking.mdp as mdp
from isaaclab.managers import TerminationTermCfg as DoneTerm

# Independent push velocity range for diffusion configs — separate from
# tracking_env_cfg.VELOCITY_RANGE so it can be tuned without affecting training.
DIFFUSION_PUSH_VELOCITY_RANGE = {
    "x": (-1.0, 1.0),
    "y": (-1.0, 1.0),
    "z": (-0.2, 0.2),
    "roll": (-0.52, 0.52),
    "pitch": (-0.52, 0.52),
    "yaw": (-0.78, 0.78),
}
DIFFUSION_PUSH_INTERVAL_RANGE_S = (4.0, 6.0)

@configclass
class G1DiffusionDataCollectionEnvCfg(G1FlatProjGravObsEnvCfg_MotionEndReset):
    """Configuration for G1 data collection - uses RL policy for inference, priv_obs for data."""
    
    @configclass
    class DataCollectionObservationsCfg(ProjGravObservationsCfg):
        """Observations for data collection - extends ProjGrav with diffusion group."""
        
        @configclass
        class DiffusionCfg(ObsGroup):
            """Diffusion observations for data collection - raw robot state with noise."""
            # Raw robot state components with configurable noise for data collection
            body_pos = ObsTerm(
                func=mdp.robot_body_pos_all,
                noise=None  # ±1cm noise on positions
            )
            body_rot = ObsTerm(
                func=mdp.robot_body_rot_all,
                noise=None  # Small noise on quaternions
            )
            body_lin_vel = ObsTerm(
                func=mdp.robot_body_lin_vel_all,
                noise=None  # ±20cm/s noise on velocities
            )
            body_ang_vel = ObsTerm(
                func=mdp.robot_body_ang_vel_all,
                noise=None  # ±0.05 rad/s noise on angular velocities
            )
            # joint_pos = ObsTerm(
            #     func=mdp.robot_joint_pos_all,
            #     noise=None  # ±0.01 rad noise on joint positions
            # )
            # joint_vel = ObsTerm(
            #     func=mdp.robot_joint_vel_all,
            #     noise=None  # ±0.05 rad/s noise on joint velocities
            # )
            joint_pos = ObsTerm(func=mdp.joint_pos, noise=None)
            joint_vel = ObsTerm(func=mdp.joint_vel, noise=None)
            # FIXME: root_pos & root_rot are under WORLD frame
            root_pos = ObsTerm(
                func=mdp.robot_root_pos,
                noise=None  # ±1cm noise on root position
            )
            root_rot = ObsTerm(
                func=mdp.robot_root_rot,
                noise=None  # Small noise on root quaternion
            )
            motion_idx = ObsTerm(
                func=mdp.robot_motion_idx
            )
            
            # Additional terms from RL Tracker Observations
            projected_gravity = ObsTerm(func=mdp.projected_gravity, noise=None)
            base_lin_vel = ObsTerm(func=mdp.base_lin_vel, noise=None)
            base_ang_vel = ObsTerm(func=mdp.base_ang_vel, noise=None)
            last_actions = ObsTerm(func=mdp.last_action)

            # Reference motion targets from MotionCommand
            motion_ref_root_pos = ObsTerm(
                func=mdp.motion_ref_root_pos,
                params={"command_name": "motion"},
                noise=None,
            )
            motion_ref_root_rot = ObsTerm(
                func=mdp.motion_ref_root_rot,
                params={"command_name": "motion"},
                noise=None,
            )
            motion_ref_root_lin_vel = ObsTerm(
                func=mdp.motion_ref_root_lin_vel,
                params={"command_name": "motion"},
                noise=None,
            )
            motion_ref_root_ang_vel = ObsTerm(
                func=mdp.motion_ref_root_ang_vel,
                params={"command_name": "motion"},
                noise=None,
            )
            motion_ref_joint_pos = ObsTerm(
                func=mdp.motion_ref_joint_pos,
                params={"command_name": "motion"},
                noise=None,
            )
            motion_ref_joint_vel = ObsTerm(
                func=mdp.motion_ref_joint_vel,
                params={"command_name": "motion"},
                noise=None,
            )
            motion_ref_body_pos = ObsTerm(
                func=mdp.motion_ref_body_pos,
                params={"command_name": "motion"},
                noise=None,
            )
            motion_ref_body_vel = ObsTerm(
                func=mdp.motion_ref_body_vel,
                params={"command_name": "motion"},
                noise=None,
            )
            motion_ref_body_pos_rel = ObsTerm(
                func=mdp.motion_ref_body_pos_rel,
                params={"command_name": "motion"},
                noise=None,
            )
            
            def __post_init__(self):
                self.enable_corruption = True  # Enable noise for data collection
                self.concatenate_terms = True  # Concatenate for easy splitting
        
        # Add diffusion group to existing policy and critic groups from ProjGravObservationsCfg
        diffusion: DiffusionCfg = DiffusionCfg()
    
    observations: DataCollectionObservationsCfg = DataCollectionObservationsCfg()

    # Independent push velocity range for data collection.
    # Override via Hydra: env.push_robot_velocity_range.x=[-1.0,1.0] etc.
    # Set to null to disable push_robot entirely.
    push_robot_velocity_range = DIFFUSION_PUSH_VELOCITY_RANGE
    # Interval range (seconds) between pushes. Override via Hydra: env.push_robot_interval_range_s=[0.5,2.0]
    push_robot_interval_range_s = DIFFUSION_PUSH_INTERVAL_RANGE_S

    def __post_init__(self):
        super().__post_init__()
        # All configuration inherited from G1FlatProjGravObsEnvCfg_MotionEndReset:
        # - Robot configuration
        # - Reward weights and pfail_thresholds
        # - Anchor body set to pelvis
        # - Motion end reset enabled
        # - Body names configured

        # Expose direction_range on the motion command so data_collection.py
        # can read it via getattr and forward it to MotionCollectionCommandCfg.
        # Override via Hydra: env.commands.motion.direction_range=[lo,hi]
        # e.g. direction_range=[-3.14159,3.14159] for full 360° yaw coverage.
        self.commands.motion.direction_range = (0.0, 0.0)

        # push_robot with independent velocity range (disable by setting push_robot_velocity_range=null)
        if self.push_robot_velocity_range is not None:
            self.events.push_robot = EventTerm(
                func=mdp.push_by_setting_velocity,
                mode="interval",
                interval_range_s=self.push_robot_interval_range_s,
                params={"velocity_range": self.push_robot_velocity_range},
            )
        else:
            self.events.push_robot = None

        # Disable other domain randomization for clean data collection
        self.events.physics_material = None
        self.events.add_joint_default_pos = None
        self.events.base_com = None


@configclass
class G1DiffusionEnvCfg(TrackingEnvCfg):
    """Configuration for G1 with diffusion policy deployment - evaluation only."""
    
    @configclass
    class DiffusionObservationsCfg:
        """Observations for diffusion policy.

        Reuses the same term layout as data collection DiffusionCfg so runtime
        observation structure stays aligned with offline dataset generation.
        """
        
        @configclass
        class PolicyCfg(G1DiffusionDataCollectionEnvCfg.DataCollectionObservationsCfg.DiffusionCfg):
            """Policy observations reusing data-collection DiffusionCfg terms."""
            
            def __post_init__(self):
                self.enable_corruption = False  # No noise for diffusion deployment
                self.concatenate_terms = True
        
        policy: PolicyCfg = PolicyCfg()
    
    observations: DiffusionObservationsCfg = DiffusionObservationsCfg()

    # Independent push velocity range for evaluation.
    # Override via Hydra or set to null to disable push_robot entirely.
    push_robot_velocity_range = DIFFUSION_PUSH_VELOCITY_RANGE
    # Interval range (seconds) between pushes. Override via Hydra: env.push_robot_interval_range_s=[0.5,2.0]
    push_robot_interval_range_s = DIFFUSION_PUSH_INTERVAL_RANGE_S

    def __post_init__(self):
        super().__post_init__()

        # Set robot configuration
        self.scene.robot = G1_CYLINDER_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        self.actions.joint_pos.scale = G1_ACTION_SCALE

        # Configure motion command
        self.commands.motion.anchor_body_name = "pelvis"
        self.commands.motion.body_names = [
            "pelvis",
            "left_hip_roll_link",
            "left_knee_link",
            "left_ankle_roll_link",
            "right_hip_roll_link",
            "right_knee_link",
            "right_ankle_roll_link",
            "torso_link",
            "left_shoulder_roll_link",
            "left_elbow_link",
            "left_wrist_yaw_link",
            "right_shoulder_roll_link",
            "right_elbow_link",
            "right_wrist_yaw_link",
        ]

        # # Set a dummy motion file - required for MotionCommand initialization
        # # but not actually used during diffusion policy execution (policy generates its own actions)
        # import glob
        # from pathlib import Path
        # ROOT_DIR = Path(__file__).parent.parent.parent.parent.parent.parent.parent.parent
        # motion_files = glob.glob(str(ROOT_DIR / "artifacts" / "Data10k-open" / "*" / "motion.npz"))
        # if motion_files:
        #     self.commands.motion.motion_files = [motion_files[0]]
        # else:
        #     raise FileNotFoundError(f"No motion.npz found in {ROOT_DIR / 'artifacts' / 'Data10k-open'}")

        # Placeholder motion file path (not used during diffusion policy execution)
        self.commands.motion.motion_files = []
        self.commands.motion.freeze_motion = True

        # Conditionally enable push_robot with independent velocity range
        if self.push_robot_velocity_range is not None:
            self.events.push_robot = EventTerm(
                func=mdp.push_by_setting_velocity,
                mode="interval",
                interval_range_s=self.push_robot_interval_range_s,
                params={"velocity_range": self.push_robot_velocity_range},
            )
        else:
            self.events.push_robot = None

        # Disable other domain randomization for clean evaluation
        self.events.physics_material = None
        self.events.add_joint_default_pos = None
        self.events.base_com = None
        self.episode_length_s = 200.0

        self.terminations = self.terminations.replace(
            anchor_pos=DoneTerm(func=mdp.bad_anchor_pos_z_only,
                                params={
                                    "command_name": "motion",
                                    "threshold": 0.4
                                }),
            anchor_ori=None,
            ee_body_pos=None,
            motion_end=None,
        )

        # self.scene.robot.spawn.fix_base = True

        self.viewer.eye = (3.0, 0.0, 0.0)
        self.viewer.lookat = (0.0, 0.0, 0.0)
        # self.viewer.origin_type = "env"
        self.viewer.origin_type = "asset_root"
        self.viewer.asset_name = "robot"


@configclass
class G1DaggerCollectionEnvCfg(G1DiffusionDataCollectionEnvCfg):
    """Configuration for DAgger on-policy data collection.

    Extends the standard data collection config with DAgger-specific support:

    - External action injection (actions come from the diffusion policy or
      expert override, not the RL policy).
    - Both ``policy`` (expert) and ``diffusion`` (student) observation groups
      are available simultaneously.
    - Records expert actions as labels regardless of which policy executed.

    Used by the ``Isaac-PegasusMoDye-DAggerCollection-G1-v0`` gym task.
    """

    def __post_init__(self):
        super().__post_init__()

        # DAgger uses external action injection — the RL policy is NOT used
        # for action generation.  Both student (diffusion) and expert
        # (RLTracker PPO) actions are computed externally and blended.

        # Keep the full diffusion observation group for recording
        # (inherited from parent).  The policy observation group is also
        # available for expert queries.

        # Use deterministic motion collection by default for full coverage
        # across motion files and yaw directions.
        self.commands.motion.direction_range = (-3.14159, 3.14159)
