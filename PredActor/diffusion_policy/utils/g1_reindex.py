"""
G1 Robot Joint and Body Index Mapping Utilities.

This module contains all joint ordering and remapping utilities for the G1 robot.
Supports different joint orderings used across:
- IsaacLab: Alphabetical ordering from URDF
- MuJoCo: Unitree SDK/MuJoCo simulation ordering
- MotionCLIP: Motion capture dataset ordering (future support)
"""

import numpy as np


# ============================================================================
# IsaacLab Joint and Body Names (Alphabetical from URDF)
# ============================================================================

# G1 body names matching DiffuseCLOC dataset (30 bodies, IsaacLab order)
ISAACLAB_BODY_NAMES = [
    'pelvis', 'left_hip_pitch_link', 'right_hip_pitch_link', 'waist_yaw_link', 
    'left_hip_roll_link', 'right_hip_roll_link', 'waist_roll_link', 
    'left_hip_yaw_link', 'right_hip_yaw_link', 'torso_link', 
    'left_knee_link', 'right_knee_link', 'left_shoulder_pitch_link', 
    'right_shoulder_pitch_link', 'left_ankle_pitch_link', 'right_ankle_pitch_link', 
    'left_shoulder_roll_link', 'right_shoulder_roll_link', 'left_ankle_roll_link', 
    'right_ankle_roll_link', 'left_shoulder_yaw_link', 'right_shoulder_yaw_link', 
    'left_elbow_link', 'right_elbow_link', 'left_wrist_roll_link', 
    'right_wrist_roll_link', 'left_wrist_pitch_link', 'right_wrist_pitch_link', 
    'left_wrist_yaw_link', 'right_wrist_yaw_link'
]

# G1 joint names in IsaacLab order (29 actuated joints, alphabetical)
ISAACLAB_DOF_NAMES = [
    'left_hip_pitch_joint', 'right_hip_pitch_joint', 'waist_yaw_joint', 
    'left_hip_roll_joint', 'right_hip_roll_joint', 'waist_roll_joint', 
    'left_hip_yaw_joint', 'right_hip_yaw_joint', 'waist_pitch_joint', 
    'left_knee_joint', 'right_knee_joint', 'left_shoulder_pitch_joint', 
    'right_shoulder_pitch_joint', 'left_ankle_pitch_joint', 'right_ankle_pitch_joint', 
    'left_shoulder_roll_joint', 'right_shoulder_roll_joint', 'left_ankle_roll_joint', 
    'right_ankle_roll_joint', 'left_shoulder_yaw_joint', 'right_shoulder_yaw_joint', 
    'left_elbow_joint', 'right_elbow_joint', 'left_wrist_roll_joint', 
    'right_wrist_roll_joint', 'left_wrist_pitch_joint', 'right_wrist_pitch_joint', 
    'left_wrist_yaw_joint', 'right_wrist_yaw_joint'
]

# G1 joint names in MuJoCo/Pinocchio order (29 actuated joints, URDF kinematic tree order)
# This is the order used by unitree_sdk2py and MuJoCo simulation
MUJOCO_DOF_NAMES = [
    'left_hip_pitch_joint', 'left_hip_roll_joint', 'left_hip_yaw_joint', 
    'left_knee_joint', 'left_ankle_pitch_joint', 'left_ankle_roll_joint', 
    'right_hip_pitch_joint', 'right_hip_roll_joint', 'right_hip_yaw_joint', 
    'right_knee_joint', 'right_ankle_pitch_joint', 'right_ankle_roll_joint', 
    'waist_yaw_joint', 'waist_roll_joint', 'waist_pitch_joint', 
    'left_shoulder_pitch_joint', 'left_shoulder_roll_joint', 'left_shoulder_yaw_joint', 
    'left_elbow_joint', 'left_wrist_roll_joint', 'left_wrist_pitch_joint', 
    'left_wrist_yaw_joint', 'right_shoulder_pitch_joint', 'right_shoulder_roll_joint', 
    'right_shoulder_yaw_joint', 'right_elbow_joint', 'right_wrist_roll_joint', 
    'right_wrist_pitch_joint', 'right_wrist_yaw_joint'
]


# ============================================================================
# IsaacLab Default Joint Positions and Action Scaling
# ============================================================================

# Default joint positions matching IsaacLab standing pose (in ISAACLAB_DOF_NAMES order)
# These are added to policy actions to get absolute target positions
ISAACLAB_DEFAULT_JOINT_POS = np.array([
    -0.312,  # left_hip_pitch_joint
    -0.312,  # right_hip_pitch_joint
    0.0,     # waist_yaw_joint
    0.0,     # left_hip_roll_joint
    0.0,     # right_hip_roll_joint
    0.0,     # waist_roll_joint
    0.0,     # left_hip_yaw_joint
    0.0,     # right_hip_yaw_joint
    0.0,     # waist_pitch_joint
    0.669,   # left_knee_joint
    0.669,   # right_knee_joint
    0.2,     # left_shoulder_pitch_joint
    0.2,     # right_shoulder_pitch_joint
    -0.363,  # left_ankle_pitch_joint
    -0.363,  # right_ankle_pitch_joint
    0.2,     # left_shoulder_roll_joint
    -0.2,    # right_shoulder_roll_joint
    0.0,     # left_ankle_roll_joint
    0.0,     # right_ankle_roll_joint
    0.0,     # left_shoulder_yaw_joint
    0.0,     # right_shoulder_yaw_joint
    0.6,     # left_elbow_joint
    0.6,     # right_elbow_joint
    0.0,     # left_wrist_roll_joint
    0.0,     # right_wrist_roll_joint
    0.0,     # left_wrist_pitch_joint
    0.0,     # right_wrist_pitch_joint
    0.0,     # left_wrist_yaw_joint
    0.0,     # right_wrist_yaw_joint
])

# Action scale factors (applied before adding default positions)
# Maps pattern-based joint limits to individual joints in ISAACLAB_DOF_NAMES order
ISAACLAB_ACTION_SCALE = np.array([
    0.5475464652142303,  # left_hip_pitch_joint (.*_hip_pitch_joint)
    0.5475464652142303,  # right_hip_pitch_joint (.*_hip_pitch_joint)
    0.5475464652142303,  # waist_yaw_joint
    0.3506614663788243,  # left_hip_roll_joint (.*_hip_roll_joint)
    0.3506614663788243,  # right_hip_roll_joint (.*_hip_roll_joint)
    0.43857731392336724, # waist_roll_joint
    0.5475464652142303,  # left_hip_yaw_joint (.*_hip_yaw_joint)
    0.5475464652142303,  # right_hip_yaw_joint (.*_hip_yaw_joint)
    0.43857731392336724, # waist_pitch_joint
    0.3506614663788243,  # left_knee_joint (.*_knee_joint)
    0.3506614663788243,  # right_knee_joint (.*_knee_joint)
    0.43857731392336724, # left_shoulder_pitch_joint (.*_shoulder_pitch_joint)
    0.43857731392336724, # right_shoulder_pitch_joint (.*_shoulder_pitch_joint)
    0.43857731392336724, # left_ankle_pitch_joint (.*_ankle_pitch_joint)
    0.43857731392336724, # right_ankle_pitch_joint (.*_ankle_pitch_joint)
    0.43857731392336724, # left_shoulder_roll_joint (.*_shoulder_roll_joint)
    0.43857731392336724, # right_shoulder_roll_joint (.*_shoulder_roll_joint)
    0.43857731392336724, # left_ankle_roll_joint (.*_ankle_roll_joint)
    0.43857731392336724, # right_ankle_roll_joint (.*_ankle_roll_joint)
    0.43857731392336724, # left_shoulder_yaw_joint (.*_shoulder_yaw_joint)
    0.43857731392336724, # right_shoulder_yaw_joint (.*_shoulder_yaw_joint)
    0.43857731392336724, # left_elbow_joint (.*_elbow_joint)
    0.43857731392336724, # right_elbow_joint (.*_elbow_joint)
    0.43857731392336724, # left_wrist_roll_joint (.*_wrist_roll_joint)
    0.43857731392336724, # right_wrist_roll_joint (.*_wrist_roll_joint)
    0.07450087032950714, # left_wrist_pitch_joint (.*_wrist_pitch_joint)
    0.07450087032950714, # right_wrist_pitch_joint (.*_wrist_pitch_joint)
    0.07450087032950714, # left_wrist_yaw_joint (.*_wrist_yaw_joint)
    0.07450087032950714, # right_wrist_yaw_joint (.*_wrist_yaw_joint)
])

# Mujoco Defualt Jpos & action scale

# Default positions for 29DOF
MUJOCO_DEFAULT_JOINT_POS = np.array([
                 -0.312, 0.0, 0.0, 0.669, -0.363, 0.0,
                 -0.312, 0.0, 0.0, 0.669, -0.363, 0.0,
                 0.0, 0.0, 0.0, 
                 0.2, 0.2, 0.0, 0.6, 0.0, 0.0, 0.0, 
                 0.2, -0.2,0.0, 0.6, 0.0, 0.0, 0.0])

# Action scaling for 29DOF
MUJOCO_ACTION_SCALE = np.array([
            0.5475464652142303, 0.3506614663788243, 0.5475464652142303, 0.3506614663788243, 0.43857731392336724, 0.43857731392336724,
            0.5475464652142303, 0.3506614663788243, 0.5475464652142303, 0.3506614663788243, 0.43857731392336724, 0.43857731392336724,
            0.5475464652142303, 0.43857731392336724, 0.43857731392336724, 
            0.43857731392336724, 0.43857731392336724, 0.43857731392336724, 0.43857731392336724, 0.43857731392336724, 0.07450087032950714, 0.07450087032950714,
            0.43857731392336724, 0.43857731392336724, 0.43857731392336724, 0.43857731392336724, 0.43857731392336724, 0.07450087032950714, 0.07450087032950714])


# ============================================================================
# Joint Remapping Functions
# ============================================================================

def create_isaaclab_to_mujoco_mapping(pinocchio_joint_names: list) -> np.ndarray:
    """
    Create mapping from IsaacLab joint order to MuJoCo/Pinocchio URDF tree order.
    
    Args:
        pinocchio_joint_names: List of joint names from Pinocchio model (URDF tree order)
    
    Returns:
        remapping: Array where remapping[mujoco_idx] = isaaclab_idx
                  Used to convert IsaacLab-ordered arrays to MuJoCo order:
                  mujoco_array = isaaclab_array[remapping]
    """
    remapping = np.zeros(29, dtype=np.int32)
    
    for isaaclab_idx, isaaclab_joint_name in enumerate(ISAACLAB_DOF_NAMES):
        try:
            mujoco_idx = pinocchio_joint_names.index(isaaclab_joint_name)
            remapping[mujoco_idx] = isaaclab_idx
        except ValueError:
            raise ValueError(f"Joint '{isaaclab_joint_name}' not found in Pinocchio model")
    
    return remapping


def apply_action_transform(
    action_isaaclab: np.ndarray,
    joint_remapping: np.ndarray,
    apply_scale: bool = True,
    apply_default_pos: bool = True
) -> np.ndarray:
    """
    Transform policy action from IsaacLab format to MuJoCo/SDK format.
    
    Pipeline:
    1. Scale action (if enabled): action_scaled = action * ISAACLAB_ACTION_SCALE
    2. Add default positions (if enabled): action_absolute = action_scaled + ISAACLAB_DEFAULT_JOINT_POS
    3. Remap to MuJoCo order: action_mujoco = action_absolute[joint_remapping]
    
    Args:
        action_isaaclab: Policy action in IsaacLab order [29]
        joint_remapping: Mapping from IsaacLab to MuJoCo order (from create_isaaclab_to_mujoco_mapping)
        apply_scale: Whether to apply action scaling
        apply_default_pos: Whether to add default joint positions
    
    Returns:
        action_mujoco: Action ready for MuJoCo/Unitree SDK [29]
    """
    action = action_isaaclab.copy()
    
    # Step 2: Apply action scaling
    if apply_scale:
        action = action * ISAACLAB_ACTION_SCALE
    
    # Step 3: Add default positions
    if apply_default_pos:
        action = action + ISAACLAB_DEFAULT_JOINT_POS

    # Step 1: Remap to MuJoCo order
    action = action[joint_remapping]

    # # Step 2: Apply action scaling
    # if apply_scale:
    #     action = action * MUJOCO_ACTION_SCALE
    
    # # Step 3: Add default positions
    # if apply_default_pos:
    #     action = action + MUJOCO_DEFAULT_JOINT_POS
    
    return action
