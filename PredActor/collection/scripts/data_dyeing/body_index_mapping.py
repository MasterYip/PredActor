"""
Body and Joint Index Mapping Between IsaacLab and MotionCLIP.

This module provides utilities to remap body and joint indices between:
- IsaacLab (RLTracker): Bodies/joints are ordered alphabetically from URDF
- MotionCLIP (G1 AMASS dataset): Bodies/joints follow a specific semantic ordering

CRITICAL: Data collected from IsaacLab must be remapped before being used with MotionCLIP!
"""

import numpy as np
import torch


# MotionCLIP ordering (from MoDyeEnc/src/datasets/g1_amass_utils.py)
MOTIONCLIP_BODY_NAMES = [
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

MOTIONCLIP_DOF_NAMES = [
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

# IsaacLab ordering (alphabetical from URDF)
# Note: This is the order returned by robot.data.body_pos_w, robot.data.body_quat_w, etc.
ISAACLAB_BODY_NAMES = ['pelvis', 'left_hip_pitch_link', 'right_hip_pitch_link', 'waist_yaw_link', 'left_hip_roll_link', 'right_hip_roll_link', 'waist_roll_link', 'left_hip_yaw_link', 'right_hip_yaw_link', 'torso_link', 'left_knee_link', 'right_knee_link', 'left_shoulder_pitch_link', 'right_shoulder_pitch_link', 'left_ankle_pitch_link', 'right_ankle_pitch_link', 'left_shoulder_roll_link', 'right_shoulder_roll_link', 'left_ankle_roll_link', 'right_ankle_roll_link', 'left_shoulder_yaw_link', 'right_shoulder_yaw_link', 'left_elbow_link', 'right_elbow_link', 'left_wrist_roll_link', 'right_wrist_roll_link', 'left_wrist_pitch_link', 'right_wrist_pitch_link', 'left_wrist_yaw_link', 'right_wrist_yaw_link']
ISAACLAB_DOF_NAMES = ['left_hip_pitch_joint', 'right_hip_pitch_joint', 'waist_yaw_joint', 'left_hip_roll_joint', 'right_hip_roll_joint', 'waist_roll_joint', 'left_hip_yaw_joint', 'right_hip_yaw_joint', 'waist_pitch_joint', 'left_knee_joint', 'right_knee_joint', 'left_shoulder_pitch_joint', 'right_shoulder_pitch_joint', 'left_ankle_pitch_joint', 'right_ankle_pitch_joint', 'left_shoulder_roll_joint', 'right_shoulder_roll_joint', 'left_ankle_roll_joint', 'right_ankle_roll_joint', 'left_shoulder_yaw_joint', 'right_shoulder_yaw_joint', 'left_elbow_joint', 'right_elbow_joint', 'left_wrist_roll_joint', 'right_wrist_roll_joint', 'left_wrist_pitch_joint', 'right_wrist_pitch_joint', 'left_wrist_yaw_joint', 'right_wrist_yaw_joint']


def create_body_index_mapping():
    """
    Create index mapping from IsaacLab body order to MotionCLIP body order.
    
    Returns:
        np.ndarray: Array of indices where mapping[i] is the IsaacLab index 
                    for the i-th MotionCLIP body
    
    Example:
        isaaclab_data = np.random.randn(100, 30, 3)  # [T, 30, 3]
        mapping = create_body_index_mapping()
        motionclip_data = isaaclab_data[:, mapping, :]  # Reordered to MotionCLIP order
    """
    mapping = []
    for motionclip_body in MOTIONCLIP_BODY_NAMES:
        isaaclab_idx = ISAACLAB_BODY_NAMES.index(motionclip_body)
        mapping.append(isaaclab_idx)
    return np.array(mapping, dtype=np.int64)


def create_dof_index_mapping():
    """
    Create index mapping from IsaacLab DOF order to MotionCLIP DOF order.
    
    Returns:
        np.ndarray: Array of indices where mapping[i] is the IsaacLab index 
                    for the i-th MotionCLIP DOF
    
    Example:
        isaaclab_joints = np.random.randn(100, 29)  # [T, 29]
        mapping = create_dof_index_mapping()
        motionclip_joints = isaaclab_joints[:, mapping]  # Reordered to MotionCLIP order
    """
    mapping = []
    for motionclip_dof in MOTIONCLIP_DOF_NAMES:
        isaaclab_idx = ISAACLAB_DOF_NAMES.index(motionclip_dof)
        mapping.append(isaaclab_idx)
    return np.array(mapping, dtype=np.int64)


def remap_isaaclab_to_motionclip(data_dict, inplace=False):
    """
    Remap body and joint indices from IsaacLab order to MotionCLIP order.
    
    Args:
        data_dict: Dictionary containing robot state data with keys:
            - body_pos: [T, 30, 3] or [30, 3, T]
            - body_rot: [T, 30, 4] or [30, 4, T]
            - body_lin_vel: [T, 30, 3] or [30, 3, T] (optional)
            - body_ang_vel: [T, 30, 3] or [30, 3, T] (optional)
            - joint_pos: [T, 29] or [29, T] (optional)
            - joint_vel: [T, 29] or [29, T] (optional)
        inplace: If True, modify data_dict in place. Otherwise, create a copy.
    
    Returns:
        dict: Remapped data dictionary
    
    Note:
        Automatically detects data format:
        - [T, num_bodies, feat_dim]: Standard format (data collection)
        - [num_bodies, feat_dim, T]: MotionCLIP format
    """
    if not inplace:
        data_dict = data_dict.copy()
    
    body_mapping = create_body_index_mapping()
    dof_mapping = create_dof_index_mapping()
    
    # Remap body data
    for key in ['body_pos', 'body_rot', 'body_lin_vel', 'body_ang_vel']:
        if key in data_dict:
            data = data_dict[key]
            
            # Convert to numpy if torch tensor
            is_torch = isinstance(data, torch.Tensor)
            if is_torch:
                device = data.device
                data = data.cpu().numpy()
            
            # Detect format and remap
            if data.shape[0] == 30:
                # Format: [30, feat_dim, T]
                data = data[body_mapping, :, :]
            elif data.shape[1] == 30:
                # Format: [T, 30, feat_dim]
                data = data[:, body_mapping, :]
            else:
                raise ValueError(f"Unexpected shape for {key}: {data.shape}")
            
            # Convert back to torch if needed
            if is_torch:
                data = torch.from_numpy(data).to(device)
            
            data_dict[key] = data
    
    # Remap joint data
    for key in ['joint_pos', 'joint_vel']:
        if key in data_dict:
            data = data_dict[key]
            
            # Convert to numpy if torch tensor
            is_torch = isinstance(data, torch.Tensor)
            if is_torch:
                device = data.device
                data = data.cpu().numpy()
            
            # Detect format and remap
            if data.shape[0] == 29:
                # Format: [29, T]
                data = data[dof_mapping, :]
            elif data.shape[1] == 29:
                # Format: [T, 29]
                data = data[:, dof_mapping]
            else:
                raise ValueError(f"Unexpected shape for {key}: {data.shape}")
            
            # Convert back to torch if needed
            if is_torch:
                data = torch.from_numpy(data).to(device)
            
            data_dict[key] = data
    
    return data_dict


def remap_motionclip_to_isaaclab(data_dict, inplace=False):
    """
    Remap body and joint indices from MotionCLIP order to IsaacLab order.
    
    This is the inverse operation of remap_isaaclab_to_motionclip.
    
    Args:
        data_dict: Dictionary containing robot state data in MotionCLIP order
        inplace: If True, modify data_dict in place. Otherwise, create a copy.
    
    Returns:
        dict: Remapped data dictionary in IsaacLab order
    """
    if not inplace:
        data_dict = data_dict.copy()
    
    # Create inverse mappings
    body_mapping = create_body_index_mapping()
    dof_mapping = create_dof_index_mapping()
    
    # Inverse mapping: isaaclab_idx -> motionclip_idx
    inv_body_mapping = np.argsort(body_mapping)
    inv_dof_mapping = np.argsort(dof_mapping)
    
    # Remap body data
    for key in ['body_pos', 'body_rot', 'body_lin_vel', 'body_ang_vel']:
        if key in data_dict:
            data = data_dict[key]
            
            # Convert to numpy if torch tensor
            is_torch = isinstance(data, torch.Tensor)
            if is_torch:
                device = data.device
                data = data.cpu().numpy()
            
            # Detect format and remap
            if data.shape[0] == 30:
                # Format: [30, feat_dim, T]
                data = data[inv_body_mapping, :, :]
            elif data.shape[1] == 30:
                # Format: [T, 30, feat_dim]
                data = data[:, inv_body_mapping, :]
            else:
                raise ValueError(f"Unexpected shape for {key}: {data.shape}")
            
            # Convert back to torch if needed
            if is_torch:
                data = torch.from_numpy(data).to(device)
            
            data_dict[key] = data
    
    # Remap joint data
    for key in ['joint_pos', 'joint_vel']:
        if key in data_dict:
            data = data_dict[key]
            
            # Convert to numpy if torch tensor
            is_torch = isinstance(data, torch.Tensor)
            if is_torch:
                device = data.device
                data = data.cpu().numpy()
            
            # Detect format and remap
            if data.shape[0] == 29:
                # Format: [29, T]
                data = data[inv_dof_mapping, :]
            elif data.shape[1] == 29:
                # Format: [T, 29]
                data = data[:, inv_dof_mapping]
            else:
                raise ValueError(f"Unexpected shape for {key}: {data.shape}")
            
            # Convert back to torch if needed
            if is_torch:
                data = torch.from_numpy(data).to(device)
            
            data_dict[key] = data
    
    return data_dict


def print_mapping_info():
    """Print body and joint index mappings for debugging."""
    print("="*80)
    print("BODY INDEX MAPPING: IsaacLab -> MotionCLIP")
    print("="*80)
    
    body_mapping = create_body_index_mapping()
    print(f"{'MotionCLIP Idx':<18} {'IsaacLab Idx':<15} {'Body Name'}")
    print("-"*80)
    for mc_idx, il_idx in enumerate(body_mapping):
        print(f"{mc_idx:<18} {il_idx:<15} {MOTIONCLIP_BODY_NAMES[mc_idx]}")
    
    print("\n" + "="*80)
    print("DOF INDEX MAPPING: IsaacLab -> MotionCLIP")
    print("="*80)
    
    dof_mapping = create_dof_index_mapping()
    print(f"{'MotionCLIP Idx':<18} {'IsaacLab Idx':<15} {'DOF Name'}")
    print("-"*80)
    for mc_idx, il_idx in enumerate(dof_mapping):
        print(f"{mc_idx:<18} {il_idx:<15} {MOTIONCLIP_DOF_NAMES[mc_idx]}")


if __name__ == '__main__':
    # Print mapping information
    print_mapping_info()
    
    # Test the mapping
    print("\n" + "="*80)
    print("TESTING REMAPPING")
    print("="*80)
    
    # Create dummy data in IsaacLab format
    T = 10
    isaaclab_data = {
        'body_pos': np.random.randn(T, 30, 3),
        'body_rot': np.random.randn(T, 30, 4),
        'joint_pos': np.random.randn(T, 29),
    }
    
    print(f"Original IsaacLab data shapes:")
    for key, val in isaaclab_data.items():
        print(f"  {key}: {val.shape}")
    
    # Remap to MotionCLIP
    motionclip_data = remap_isaaclab_to_motionclip(isaaclab_data)
    
    print(f"\nRemapped to MotionCLIP (same shapes, different order):")
    for key, val in motionclip_data.items():
        print(f"  {key}: {val.shape}")
    
    # Remap back to IsaacLab
    isaaclab_data_back = remap_motionclip_to_isaaclab(motionclip_data)
    
    print(f"\nRemapped back to IsaacLab:")
    for key, val in isaaclab_data_back.items():
        print(f"  {key}: {val.shape}")
    
    # Verify round-trip
    print(f"\nRound-trip verification:")
    for key in isaaclab_data.keys():
        matches = np.allclose(isaaclab_data[key], isaaclab_data_back[key])
        print(f"  {key}: {'✓ PASS' if matches else '✗ FAIL'}")
