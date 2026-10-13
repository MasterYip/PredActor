"""
Motion format converter for MotionCLIP encoding.

Converts G1 motion data from IsaacLab format to MotionCLIP input format.
Handles different pose representations (xyz, rot6d, posquat, posvel).

IMPORTANT: Automatically handles body/joint index remapping from IsaacLab (alphabetical)
to MotionCLIP (semantic) ordering.
"""

import torch
import numpy as np
# from pytorch3d import transforms as geometry
geometry = None  # The public dyeing profile uses xyz positions.
from body_index_mapping import remap_isaaclab_to_motionclip


class G1MotionConverter:
    """
    Converts G1 motion data to MotionCLIP input format.
    
    IsaacLab format (from data_collection.py):
        - body_pos: [T, 30, 3] - body positions
        - body_rot: [T, 30, 4] - body rotations (quaternions)
        - body_lin_vel: [T, 30, 3] - body linear velocities
        - body_ang_vel: [T, 30, 3] - body angular velocities
        - joint_pos: [T, 29] - joint positions
        - joint_vel: [T, 29] - joint velocities
    
    MotionCLIP format (see dataset.py _load):
        - Shape: [num_bodies, feat_dim, seq_len]
        - pose_rep options: 'xyz', 'rot6d', 'posquat', 'posvel'
    """
    
    def __init__(self, pose_rep='posquat', translation=True, glob=True, device='cuda'):
        """
        Args:
            pose_rep: Pose representation ('xyz', 'rot6d', 'posquat', 'posvel')
            translation: Whether to include translation
            glob: Whether to include global orientation
            device: Torch device
        """
        self.pose_rep = pose_rep
        self.translation = translation
        self.glob = glob
        self.device = device
        
    def convert(self, body_pos, body_rot, body_lin_vel=None, body_ang_vel=None):
        """
        Convert motion data to MotionCLIP format.
        
        Args:
            body_pos: [seq_len, 30, 3] - body positions (IsaacLab order)
            body_rot: [seq_len, 30, 4] - body rotations in quaternions (IsaacLab order)
            body_lin_vel: [seq_len, 30, 3] - body linear velocities (IsaacLab order, optional)
            body_ang_vel: [seq_len, 30, 3] - body angular velocities (IsaacLab order, optional)
            
        Returns:
            Tensor in MotionCLIP format: [30, feat_dim, seq_len] (MotionCLIP order)
        
        Note:
            This function automatically remaps body indices from IsaacLab (alphabetical)
            to MotionCLIP (semantic) ordering before processing.
        """
        # Convert to torch tensors
        body_pos = self._to_torch(body_pos)  # [T, 30, 3]
        body_rot = self._to_torch(body_rot)  # [T, 30, 4]
        
        # CRITICAL: Remap from IsaacLab order to MotionCLIP order
        data_dict = {
            'body_pos': body_pos,
            'body_rot': body_rot,
        }
        if body_lin_vel is not None:
            data_dict['body_lin_vel'] = self._to_torch(body_lin_vel)
        if body_ang_vel is not None:
            data_dict['body_ang_vel'] = self._to_torch(body_ang_vel)
        
        data_dict = remap_isaaclab_to_motionclip(data_dict, inplace=True)
        
        # Extract remapped data
        body_pos = data_dict['body_pos']  # [T, 30, 3] - now in MotionCLIP order
        body_rot = data_dict['body_rot']  # [T, 30, 4] - now in MotionCLIP order
        
        # Center at root body position of first frame
        body_pos = body_pos - body_pos[0, 0, :]  # [T, 30, 3]
        
        # Store translation if needed
        if self.translation:
            ret_tr = body_pos[:, 0, :]  # [T, 3] - root body trajectory
        
        # Convert based on pose representation
        if self.pose_rep == 'xyz':
            ret = body_pos  # [T, 30, 3]
            
        elif self.pose_rep == 'rot6d':
            raise ValueError("The public dyeing profile supports pose_rep=xyz only")
            
        elif self.pose_rep == 'posquat':
            # Concatenate position and quaternion
            ret = torch.cat((body_pos, body_rot), dim=2)  # [T, 30, 7]
            
        elif self.pose_rep == 'posvel':
            if body_lin_vel is None:
                raise ValueError("body_lin_vel required for 'posvel' representation")
            body_lin_vel = self._to_torch(body_lin_vel)  # [T, 30, 3]
            ret = torch.cat((body_pos, body_lin_vel), dim=2)  # [T, 30, 6]
            
        else:
            raise ValueError(f"Unsupported pose_rep: {self.pose_rep}")
        
        # Add translation as extra "body" if needed
        if self.pose_rep != 'xyz' and self.translation:
            # Create padded translation vector matching feature dimension
            padded_tr = torch.zeros((ret.shape[0], ret.shape[2]), 
                                   dtype=ret.dtype, device=ret.device)
            padded_tr[:, :3] = ret_tr  # Fill first 3 dims with xyz
            ret = torch.cat((ret, padded_tr[:, None]), dim=1)  # [T, 31, feat_dim]
        
        # Permute to MotionCLIP format: [bodies, features, time]
        ret = ret.permute(1, 2, 0).contiguous()  # [30 or 31, feat_dim, T]
        
        return ret.float()
    
    def _to_torch(self, data):
        """Convert numpy array or torch tensor to torch tensor on device."""
        if isinstance(data, np.ndarray):
            data = torch.from_numpy(data)
        if not isinstance(data, torch.Tensor):
            data = torch.tensor(data)
        return data.to(self.device)


def extract_motion_window(data_dict, center_idx, window_size, boundary_mode='pad', episode_start=None, episode_end=None):
    """
    Extract a motion window centered at a specific frame.
    
    Args:
        data_dict: Dictionary with motion data fields
        center_idx: Center frame index (global index in dataset)
        window_size: Total window size (e.g., 60 frames)
        boundary_mode: How to handle boundaries ('pad', 'truncate', 'mirror')
        episode_start: Start index of the episode (if None, assumes single episode starting at 0)
        episode_end: End index of the episode (if None, uses total_frames)
        
    Returns:
        Dictionary with windowed motion data
    """
    total_frames = data_dict['body_pos'].shape[0]
    
    # Set episode boundaries
    if episode_start is None:
        episode_start = 0
    if episode_end is None:
        episode_end = total_frames
    
    half_window = window_size // 2
    
    # Calculate window indices (relative to global dataset)
    start_idx = center_idx - half_window
    end_idx = center_idx + half_window
    
    # Convert to episode-relative indices for boundary checking
    episode_relative_center = center_idx - episode_start
    episode_relative_start = start_idx - episode_start
    episode_relative_end = end_idx - episode_start
    episode_length = episode_end - episode_start
    
    # Handle boundary cases WITHIN the episode
    if boundary_mode == 'pad':
        # Pad with edge values of the episode
        if episode_relative_start < 0:
            left_pad = -episode_relative_start
            actual_start = episode_start  # Start of episode
        else:
            left_pad = 0
            actual_start = start_idx
            
        if episode_relative_end > episode_length:
            right_pad = episode_relative_end - episode_length
            actual_end = episode_end  # End of episode
        else:
            right_pad = 0
            actual_end = end_idx
        
        # Extract window from within episode
        window_dict = {}
        for key, value in data_dict.items():
            if isinstance(value, (np.ndarray, torch.Tensor)):
                window_data = value[actual_start:actual_end]
                
                # Pad if needed (using episode boundary values)
                if left_pad > 0:
                    if isinstance(window_data, np.ndarray):
                        pad_value = np.repeat(window_data[0:1], left_pad, axis=0)
                        window_data = np.concatenate([pad_value, window_data], axis=0)
                    else:
                        pad_value = window_data[0:1].repeat(left_pad, *([1] * (window_data.ndim - 1)))
                        window_data = torch.cat([pad_value, window_data], dim=0)
                
                if right_pad > 0:
                    if isinstance(window_data, np.ndarray):
                        pad_value = np.repeat(window_data[-1:], right_pad, axis=0)
                        window_data = np.concatenate([window_data, pad_value], axis=0)
                    else:
                        pad_value = window_data[-1:].repeat(right_pad, *([1] * (window_data.ndim - 1)))
                        window_data = torch.cat([window_data, pad_value], dim=0)
                
                window_dict[key] = window_data
            else:
                window_dict[key] = value
                
    elif boundary_mode == 'truncate':
        # Truncate window to episode boundaries
        actual_start = max(episode_start, start_idx)
        actual_end = min(episode_end, end_idx)
        
        window_dict = {}
        for key, value in data_dict.items():
            if isinstance(value, (np.ndarray, torch.Tensor)):
                window_dict[key] = value[actual_start:actual_end]
            else:
                window_dict[key] = value
                
    elif boundary_mode == 'mirror':
        # Mirror padding at episode boundaries
        indices = list(range(start_idx, end_idx))
        
        # Mirror indices that fall outside episode boundaries
        mirrored_indices = []
        for i in indices:
            episode_relative_i = i - episode_start
            if episode_relative_i < 0:
                # Mirror from start
                mirrored_indices.append(episode_start + abs(episode_relative_i))
            elif episode_relative_i >= episode_length:
                # Mirror from end
                overflow = episode_relative_i - episode_length + 1
                mirrored_indices.append(episode_end - 1 - overflow)
            else:
                mirrored_indices.append(i)
        
        window_dict = {}
        for key, value in data_dict.items():
            if isinstance(value, (np.ndarray, torch.Tensor)):
                window_dict[key] = value[mirrored_indices]
            else:
                window_dict[key] = value
    else:
        raise ValueError(f"Unknown boundary_mode: {boundary_mode}")
    
    return window_dict


def create_motion_batches(total_frames, window_size, batch_size, boundary_mode='pad'):
    """
    Create batch indices for processing all frames.
    
    Args:
        total_frames: Total number of frames in the dataset
        window_size: Window size for each frame
        batch_size: Batch size for processing
        boundary_mode: Boundary handling mode
        
    Returns:
        List of (batch_start, batch_end, center_indices) tuples
    """
    batches = []
    
    for batch_start in range(0, total_frames, batch_size):
        batch_end = min(batch_start + batch_size, total_frames)
        center_indices = list(range(batch_start, batch_end))
        batches.append((batch_start, batch_end, center_indices))
    
    return batches


def load_motion_npz(motion_file, device='cpu'):
    """
    Load motion from npz file (IsaacLab format).
    
    Args:
        motion_file: Path to motion.npz file
        device: Torch device
        
    Returns:
        Dictionary with motion data in IsaacLab format:
            - body_pos: [T, 30, 3]
            - body_rot: [T, 30, 4] (quaternions)
            - body_lin_vel: [T, 30, 3]
            - body_ang_vel: [T, 30, 3]
            - joint_pos: [T, 29]
            - joint_vel: [T, 29]
            - fps: scalar
            - motion_length: scalar (number of frames)
    """
    data = np.load(motion_file)
    
    # Extract motion data (matches MultiMotionLoader format)
    motion_dict = {
        'joint_pos': torch.from_numpy(data['joint_pos']).float().to(device),  # [T, 29]
        'joint_vel': torch.from_numpy(data['joint_vel']).float().to(device),  # [T, 29]
        'body_pos': torch.from_numpy(data['body_pos_w']).float().to(device),  # [T, num_bodies, 3]
        'body_rot': torch.from_numpy(data['body_quat_w']).float().to(device),  # [T, num_bodies, 4]
        'body_lin_vel': torch.from_numpy(data['body_lin_vel_w']).float().to(device),  # [T, num_bodies, 3]
        'body_ang_vel': torch.from_numpy(data['body_ang_vel_w']).float().to(device),  # [T, num_bodies, 3]
        'fps': float(data['fps']),
        'motion_length': data['joint_pos'].shape[0],
    }
    
    return motion_dict
