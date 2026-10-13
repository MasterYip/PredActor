from isaaclab.utils import configclass
from dataclasses import MISSING

from rl_tracker.robots.g1 import G1_ACTION_SCALE, G1_CYLINDER_CFG
from rl_tracker.tasks.tracking.config.g1.agents.rsl_rl_ppo_cfg import LOW_FREQ_SCALE
from rl_tracker.tasks.tracking.tracking_env_cfg import TrackingEnvCfg, PrivPrivObservationsCfg, PropPropObservationsCfg, NoisePrivObservationsCfg, ProjGravObservationsCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
import rl_tracker.tasks.tracking.mdp as mdp

@configclass
class G1FlatEnvCfg(TrackingEnvCfg):

    def __post_init__(self):
        super().__post_init__()

        self.scene.robot = G1_CYLINDER_CFG.replace(
            prim_path="{ENV_REGEX_NS}/Robot")
        self.actions.joint_pos.scale = G1_ACTION_SCALE
        self.commands.motion.anchor_body_name = "torso_link"
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


@configclass
class G1FlatWoStateEstimationEnvCfg(G1FlatEnvCfg):

    def __post_init__(self):
        super().__post_init__()
        self.observations.policy.motion_anchor_pos_b = None
        self.observations.policy.base_lin_vel = None


@configclass
class G1FlatProjGravObsEnvCfg(G1FlatEnvCfg):
    observations: ProjGravObservationsCfg = ProjGravObservationsCfg()
    def __post_init__(self):
        super().__post_init__()
        # Align reward weights and pfail_thresholds to match the pretrained checkpoint (env.yaml)
        # These values differ from the base TrackingEnvCfg defaults
        
        # Reward weight adjustments
        self.rewards.feet_slide.weight = -0.3  # vs -0.1 in base
        self.rewards.soft_landing.weight = -0.0003  # vs -0.00001 in base
        self.rewards.overspeed.weight = -1.0  # vs -0.1 in base
        self.rewards.overeffort.weight = -1.0  # vs -0.1 in base
        
        # pfail_threshold adjustments to match checkpoint behavior
        self.rewards.feet_slide.params["pfail_threshold"] = 1.0  # vs 0.2 in base
        self.rewards.soft_landing.params["pfail_threshold"] = 1.0  # vs 0.2 in base
        self.rewards.overspeed.params["pfail_threshold"] = 1.0  # vs 0.15 in base
        self.rewards.overeffort.params["pfail_threshold"] = 1.0  # vs 0.15 in base

        self.commands.motion.anchor_body_name = "pelvis"

@configclass
class G1FlatProjGravObsEnvCfg_MotionEndReset(G1FlatProjGravObsEnvCfg):
    """G1 Flat environment with projected gravity observations and motion end reset enabled."""

    def __post_init__(self):
        super().__post_init__()
        # Enable motion end reset (episode resets when motion sequence ends)
        self.commands.motion.motion_end_reset = True
        # self.terminations = self.terminations.replace(
        #     anchor_pos=DoneTerm(func=mdp.bad_anchor_pos_z_only,
        #                         params={
        #                             "command_name": "motion",
        #                             "threshold": 0.5
        #                         }),
        #     anchor_ori=None,
        #     ee_body_pos=None,
        # )

# NOTE: Temporarily not used
@configclass
class G1FlatProjGravObsEnvCfg_MotionCollection(G1FlatProjGravObsEnvCfg):
    """G1 Flat environment with projected gravity observations and motion end reset enabled."""

    def __post_init__(self):
        super().__post_init__()
        # Enable motion end reset (episode resets when motion sequence ends)
        self.commands.motion = mdp.MotionCollectionCommandCfg(
            future_steps=5,  # Future N-step lookahead
            asset_name="robot",
            resampling_time_range=(1.0e9, 1.0e9),
            debug_vis=True,
            pose_range={
                "x": (-0.05, 0.05),
                "y": (-0.05, 0.05),
                "z": (-0.01, 0.01),
                "roll": (-0.1, 0.1),
                "pitch": (-0.1, 0.1),
                "yaw": (-0.2, 0.2),
            },
            velocity_range=VELOCITY_RANGE,
            joint_position_range=(-0.1, 0.1),
        )
        self.terminations = self.terminations.replace(
            motion_end=None
        )
        self.rewards = None

@configclass
class G1FlatProjGravObsEnvCfg_LargeHand(G1FlatProjGravObsEnvCfg):

    def __post_init__(self):
        super().__post_init__()
        from rl_tracker.robots.g1 import sim_utils, ASSET_DIR

        self.scene.robot = G1_CYLINDER_CFG.replace(spawn=sim_utils.UrdfFileCfg(
            fix_base=False,
            replace_cylinders_with_capsules=True,
            asset_path=
            f"{ASSET_DIR}/unitree_description/urdf/g1/main_largehand.urdf",
            activate_contact_sensors=True,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                disable_gravity=False,
                retain_accelerations=False,
                linear_damping=0.0,
                angular_damping=0.0,
                max_linear_velocity=1000.0,
                max_angular_velocity=1000.0,
                max_depenetration_velocity=1.0,
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=True,
                solver_position_iteration_count=8,
                solver_velocity_iteration_count=4),
            joint_drive=sim_utils.UrdfConverterCfg.JointDriveCfg(
                gains=sim_utils.UrdfConverterCfg.JointDriveCfg.PDGainsCfg(
                    stiffness=0, damping=0)),
        )).replace(prim_path="{ENV_REGEX_NS}/Robot")

    ...


@configclass
class G1FlatProjGravObsEnvCfg_LargeHandHeavy(G1FlatProjGravObsEnvCfg):

    def __post_init__(self):
        super().__post_init__()
        from rl_tracker.robots.g1 import sim_utils, ASSET_DIR

        self.scene.robot = G1_CYLINDER_CFG.replace(spawn=sim_utils.UrdfFileCfg(
            fix_base=False,
            replace_cylinders_with_capsules=True,
            asset_path=
            f"{ASSET_DIR}/unitree_description/urdf/g1/main_largehand_heavy.urdf",
            activate_contact_sensors=True,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                disable_gravity=False,
                retain_accelerations=False,
                linear_damping=0.0,
                angular_damping=0.0,
                max_linear_velocity=1000.0,
                max_angular_velocity=1000.0,
                max_depenetration_velocity=1.0,
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=True,
                solver_position_iteration_count=8,
                solver_velocity_iteration_count=4),
            joint_drive=sim_utils.UrdfConverterCfg.JointDriveCfg(
                gains=sim_utils.UrdfConverterCfg.JointDriveCfg.PDGainsCfg(
                    stiffness=0, damping=0)),
        )).replace(prim_path="{ENV_REGEX_NS}/Robot")

    ...

    ...


@configclass
class G1FlatPropPropObsEnvCfg(G1FlatEnvCfg):
    observations: PropPropObservationsCfg = PropPropObservationsCfg()


@configclass
class G1FlatPrivPrivObsEnvCfg(G1FlatEnvCfg):
    observations: PrivPrivObservationsCfg = PrivPrivObservationsCfg()


@configclass
class G1FlatNoisePrivObsEnvCfg(G1FlatEnvCfg):
    observations: NoisePrivObservationsCfg = NoisePrivObservationsCfg()


@configclass
class G1FlatLowFreqEnvCfg(G1FlatEnvCfg):

    def __post_init__(self):
        super().__post_init__()
        self.decimation = round(self.decimation / LOW_FREQ_SCALE)
        self.rewards.action_rate_l2.weight *= LOW_FREQ_SCALE
