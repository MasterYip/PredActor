# -*- coding: utf-8 -*-
"""
G1 Robot Joint and Body Names for AMASS Retargeted Dataset

This module defines the joint (DOF) and body (link) names for the Unitree G1 humanoid robot
as used in the G1 retargeted AMASS dataset.
"""

import numpy as np

# G1 Robot Configuration
G1_NUM_DOFS = 29  # Number of actuated joints
G1_NUM_BODIES = 30  # Number of rigid bodies/links (29 joints + 1 root)

# G1 DOF (Joint) Names - 29 actuated joints
G1_DOF_NAMES = [
    # Left Leg (6 DOFs)
    'left_hip_pitch_joint',
    'left_hip_roll_joint',
    'left_hip_yaw_joint',
    'left_knee_joint',
    'left_ankle_pitch_joint',
    'left_ankle_roll_joint',
    
    # Right Leg (6 DOFs)
    'right_hip_pitch_joint',
    'right_hip_roll_joint',
    'right_hip_yaw_joint',
    'right_knee_joint',
    'right_ankle_pitch_joint',
    'right_ankle_roll_joint',
    
    # Waist/Torso (3 DOFs)
    'waist_yaw_joint',
    'waist_roll_joint',
    'waist_pitch_joint',
    
    # Left Arm (7 DOFs)
    'left_shoulder_pitch_joint',
    'left_shoulder_roll_joint',
    'left_shoulder_yaw_joint',
    'left_elbow_joint',
    'left_wrist_roll_joint',
    'left_wrist_pitch_joint',
    'left_wrist_yaw_joint',
    
    # Right Arm (7 DOFs)
    'right_shoulder_pitch_joint',
    'right_shoulder_roll_joint',
    'right_shoulder_yaw_joint',
    'right_elbow_joint',
    'right_wrist_roll_joint',
    'right_wrist_pitch_joint',
    'right_wrist_yaw_joint',
]

# G1 Body (Link) Names - 30 rigid bodies
G1_BODY_NAMES = [
    # Root
    'pelvis',
    
    # Left Leg (6 bodies)
    'left_hip_pitch_link',
    'left_hip_roll_link',
    'left_hip_yaw_link',
    'left_knee_link',
    'left_ankle_pitch_link',
    'left_ankle_roll_link',
    
    # Right Leg (6 bodies)
    'right_hip_pitch_link',
    'right_hip_roll_link',
    'right_hip_yaw_link',
    'right_knee_link',
    'right_ankle_pitch_link',
    'right_ankle_roll_link',
    
    # Torso (3 bodies)
    'waist_yaw_link',
    'waist_roll_link',
    'torso_link',
    
    # Left Arm (7 bodies)
    'left_shoulder_pitch_link',
    'left_shoulder_roll_link',
    'left_shoulder_yaw_link',
    'left_elbow_link',
    'left_wrist_roll_link',
    'left_wrist_pitch_link',
    'left_wrist_yaw_link',
    
    # Right Arm (7 bodies)
    'right_shoulder_pitch_link',
    'right_shoulder_roll_link',
    'right_shoulder_yaw_link',
    'right_elbow_link',
    'right_wrist_roll_link',
    'right_wrist_pitch_link',
    'right_wrist_yaw_link',
]

# Validate counts
assert len(G1_DOF_NAMES) == G1_NUM_DOFS, f"Expected {G1_NUM_DOFS} DOFs, got {len(G1_DOF_NAMES)}"
assert len(G1_BODY_NAMES) == G1_NUM_BODIES, f"Expected {G1_NUM_BODIES} bodies, got {len(G1_BODY_NAMES)}"

# Joint/Body Indices for Different Body Parts
# Root
ROOT_INDEX = 0

# Left Leg
L_LEG_DOF_START = 0
L_LEG_DOF_END = 6
L_LEG_DOFS = np.arange(L_LEG_DOF_START, L_LEG_DOF_END)  # [0, 1, 2, 3, 4, 5]

L_LEG_BODY_START = 1
L_LEG_BODY_END = 7
L_LEG_BODIES = np.arange(L_LEG_BODY_START, L_LEG_BODY_END)  # [1, 2, 3, 4, 5, 6]

# Right Leg
R_LEG_DOF_START = 6
R_LEG_DOF_END = 12
R_LEG_DOFS = np.arange(R_LEG_DOF_START, R_LEG_DOF_END)  # [6, 7, 8, 9, 10, 11]

R_LEG_BODY_START = 7
R_LEG_BODY_END = 13
R_LEG_BODIES = np.arange(R_LEG_BODY_START, R_LEG_BODY_END)  # [7, 8, 9, 10, 11, 12]

# Waist/Torso
WAIST_DOF_START = 12
WAIST_DOF_END = 15
WAIST_DOFS = np.arange(WAIST_DOF_START, WAIST_DOF_END)  # [12, 13, 14]

TORSO_BODY_START = 13
TORSO_BODY_END = 16
TORSO_BODIES = np.arange(TORSO_BODY_START, TORSO_BODY_END)  # [13, 14, 15]

# Left Arm
L_ARM_DOF_START = 15
L_ARM_DOF_END = 22
L_ARM_DOFS = np.arange(L_ARM_DOF_START, L_ARM_DOF_END)  # [15, 16, 17, 18, 19, 20, 21]

L_ARM_BODY_START = 16
L_ARM_BODY_END = 23
L_ARM_BODIES = np.arange(L_ARM_BODY_START, L_ARM_BODY_END)  # [16, 17, 18, 19, 20, 21, 22]

# Right Arm
R_ARM_DOF_START = 22
R_ARM_DOF_END = 29
R_ARM_DOFS = np.arange(R_ARM_DOF_START, R_ARM_DOF_END)  # [22, 23, 24, 25, 26, 27, 28]

R_ARM_BODY_START = 23
R_ARM_BODY_END = 30
R_ARM_BODIES = np.arange(R_ARM_BODY_START, R_ARM_BODY_END)  # [23, 24, 25, 26, 27, 28, 29]

# Combined groups
LEGS_DOFS = np.concatenate([L_LEG_DOFS, R_LEG_DOFS])  # All leg DOFs
ARMS_DOFS = np.concatenate([L_ARM_DOFS, R_ARM_DOFS])  # All arm DOFs
LEGS_BODIES = np.concatenate([L_LEG_BODIES, R_LEG_BODIES])  # All leg bodies
ARMS_BODIES = np.concatenate([L_ARM_BODIES, R_ARM_BODIES])  # All arm bodies

# For analysis and statistics
ROOT_STATS = {name: 0 for name in ['pelvis']}

L_LEG_STATS = {
    G1_DOF_NAMES[i]: i for i in L_LEG_DOFS
}

R_LEG_STATS = {
    G1_DOF_NAMES[i]: i for i in R_LEG_DOFS
}

L_ARM_STATS = {
    G1_DOF_NAMES[i]: i for i in L_ARM_DOFS
}

R_ARM_STATS = {
    G1_DOF_NAMES[i]: i for i in R_ARM_DOFS
}

WAIST_STATS = {
    G1_DOF_NAMES[i]: i for i in WAIST_DOFS
}

# DOF to Body mapping (each DOF drives one body)
# Note: pelvis (body 0) is the root and has no corresponding DOF
DOF_TO_BODY = {
    i: i + 1 for i in range(G1_NUM_DOFS)  # DOF i drives body i+1
}

BODY_TO_DOF = {
    i + 1: i for i in range(G1_NUM_DOFS)  # Body i+1 is driven by DOF i
}
# pelvis (body 0) has no driving DOF

# Kinematic chains (simplified)
# Format: (parent_body_idx, child_body_idx)
KINEMATIC_TREE = [
    # Left leg chain
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
    # Right leg chain
    (0, 7), (7, 8), (8, 9), (9, 10), (10, 11), (11, 12),
    # Torso chain
    (0, 13), (13, 14), (14, 15),
    # Left arm chain
    (15, 16), (16, 17), (17, 18), (18, 19), (19, 20), (20, 21), (21, 22),
    # Right arm chain
    (15, 23), (23, 24), (24, 25), (25, 26), (26, 27), (27, 28), (28, 29),
]

# Verification
assert len(KINEMATIC_TREE) == G1_NUM_BODIES - 1, "Kinematic tree should have 29 edges for 30 bodies"


def get_dof_index(joint_name: str) -> int:
    """Get DOF index from joint name."""
    try:
        return G1_DOF_NAMES.index(joint_name)
    except ValueError:
        raise ValueError(f"Joint name '{joint_name}' not found in G1_DOF_NAMES")


def get_body_index(body_name: str) -> int:
    """Get body index from body name."""
    try:
        return G1_BODY_NAMES.index(body_name)
    except ValueError:
        raise ValueError(f"Body name '{body_name}' not found in G1_BODY_NAMES")


def print_g1_structure():
    """Print G1 robot structure for documentation."""
    print("=" * 60)
    print("G1 Robot Structure")
    print("=" * 60)
    
    print(f"\nTotal DOFs: {G1_NUM_DOFS}")
    print(f"Total Bodies: {G1_NUM_BODIES}")
    
    print("\n" + "=" * 60)
    print("DOF Names (29 actuated joints)")
    print("=" * 60)
    
    print("\nLeft Leg (6 DOFs):")
    for i in L_LEG_DOFS:
        print(f"  {i}: {G1_DOF_NAMES[i]}")
    
    print("\nRight Leg (6 DOFs):")
    for i in R_LEG_DOFS:
        print(f"  {i}: {G1_DOF_NAMES[i]}")
    
    print("\nWaist/Torso (3 DOFs):")
    for i in WAIST_DOFS:
        print(f"  {i}: {G1_DOF_NAMES[i]}")
    
    print("\nLeft Arm (7 DOFs):")
    for i in L_ARM_DOFS:
        print(f"  {i}: {G1_DOF_NAMES[i]}")
    
    print("\nRight Arm (7 DOFs):")
    for i in R_ARM_DOFS:
        print(f"  {i}: {G1_DOF_NAMES[i]}")
    
    print("\n" + "=" * 60)
    print("Body Names (30 rigid bodies)")
    print("=" * 60)
    
    print("\nRoot:")
    print(f"  0: {G1_BODY_NAMES[0]}")
    
    print("\nLeft Leg (6 bodies):")
    for i in L_LEG_BODIES:
        print(f"  {i}: {G1_BODY_NAMES[i]}")
    
    print("\nRight Leg (6 bodies):")
    for i in R_LEG_BODIES:
        print(f"  {i}: {G1_BODY_NAMES[i]}")
    
    print("\nTorso (3 bodies):")
    for i in TORSO_BODIES:
        print(f"  {i}: {G1_BODY_NAMES[i]}")
    
    print("\nLeft Arm (7 bodies):")
    for i in L_ARM_BODIES:
        print(f"  {i}: {G1_BODY_NAMES[i]}")
    
    print("\nRight Arm (7 bodies):")
    for i in R_ARM_BODIES:
        print(f"  {i}: {G1_BODY_NAMES[i]}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_g1_structure()
