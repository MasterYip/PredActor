"""
Motion Loader for Tracking Policies.
Loads motion data from .npz files for motion tracking tasks.
"""

import numpy as np
from typing import Dict, Optional, Tuple
from pathlib import Path


class MotionLoader:
    """
    Loads and manages motion reference data for tracking policies.
    
    Compatible with motion data format from IsaacLab motion tracking tasks.
    """
    
    def __init__(self, motion_file: str):
        """
        Initialize motion loader from .npz file.
        
        Args:
            motion_file: Path to motion .npz file containing reference trajectories
        """
        self.motion_file = Path(motion_file)
        if not self.motion_file.exists():
            raise FileNotFoundError(f"Motion file not found: {motion_file}")
        
        # Load motion data
        data = np.load(str(self.motion_file))
        
        # Extract motion data (all in IsaacLab order)
        # Keys match the actual npz format from npz_motion_publisher.py
        self.motion_dof_pos = data['joint_pos']  # [T, num_dofs] - IsaacLab order
        self.motion_dof_vel = data['joint_vel']  # [T, num_dofs]
        
        # Body data: [T, num_bodies, 3/4]
        self.motion_bodies_pos = data['body_pos_w']  # [T, num_bodies, 3]
        self.motion_bodies_rot = data['body_quat_w']  # [T, num_bodies, 4] (quat wxyz or xyzw format)
        
        # Get dimensions
        self.num_frames = self.motion_dof_pos.shape[0]
        self.num_dofs = self.motion_dof_pos.shape[1]
        self.num_bodies = self.motion_bodies_pos.shape[1]
        
        # Anchor body index - only pelvis (index 0) is used in C++ implementation
        # The "5 anchor bodies" means pelvis at 5 future timesteps, not 5 different bodies
        self.anchor_body_index = 0  # IsaacLab body index for pelvis
        
        print(f"[MotionLoader] Loaded motion from {self.motion_file}")
        print(f"  Frames: {self.num_frames}")
        print(f"  Bodies: {self.num_bodies}")
        print(f"  DOFs: {self.num_dofs}")
    
    def get_motion_frame(self, frame_idx: int) -> Dict[str, np.ndarray]:
        """
        Get motion data at specific frame.
        
        Args:
            frame_idx: Frame index (will be clamped to valid range)
        
        Returns:
            dict with motion data at frame_idx
        """
        frame_idx = np.clip(frame_idx, 0, self.num_frames - 1)
        
        return {
            'bodies_pos': self.motion_bodies_pos[frame_idx],  # [num_bodies, 3]
            'bodies_rot': self.motion_bodies_rot[frame_idx],  # [num_bodies, 4]
            'dof_pos': self.motion_dof_pos[frame_idx],  # [num_dofs]
            'dof_vel': self.motion_dof_vel[frame_idx],  # [num_dofs]
        }
    
    def get_command(self, frame_idx: int, horizon: int = 10) -> np.ndarray:
        """
        Get future joint positions and velocities as command.
        
        Args:
            frame_idx: Current frame index
            horizon: Number of future frames to include
        
        Returns:
            Command vector [horizon * (num_dofs + num_dofs)] = [horizon * 58] for 29 DOFs
        """
        commands_pos = []
        commands_vel = []
        for i in range(horizon):
            future_idx = np.clip(frame_idx + i, 0, self.num_frames - 1)
            dof_pos = self.motion_dof_pos[future_idx]
            dof_vel = self.motion_dof_vel[future_idx]
            commands_pos.append(dof_pos)
            commands_vel.append(dof_vel)
        
        return np.concatenate(commands_pos + commands_vel)  # [horizon * 58]
    
    def get_anchor_body_pose_at_frame(self, frame_idx: int) -> tuple:
        """
        Get anchor body (pelvis) position and rotation at specific frame.
        
        Args:
            frame_idx: Frame index
        
        Returns:
            (position [3], rotation_quat [4])
        """
        frame_idx = np.clip(frame_idx, 0, self.num_frames - 1)
        
        # body_pos_w and body_quat_w are [T, 3] and [T, 4] (only pelvis saved)
        if len(self.motion_bodies_pos.shape) == 2:  # [T, 3]
            pos = self.motion_bodies_pos[frame_idx]
            quat = self.motion_bodies_rot[frame_idx]
        else:  # [T, num_bodies, 3/4]
            pos = self.motion_bodies_pos[frame_idx, self.anchor_body_index]
            quat = self.motion_bodies_rot[frame_idx, self.anchor_body_index]
        
        return pos, quat
    
    def calc_heading_quat(self, quat_wxyz: np.ndarray) -> np.ndarray:
        """
        Calculate heading quaternion (yaw only) from full quaternion.
        
        Args:
            quat_wxyz: Quaternion [w, x, y, z]
        
        Returns:
            Heading quaternion [w, x, y, z] with only yaw component
        """
        w, x, y, z = quat_wxyz
        yaw = np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
        heading_quat = np.array([
            np.cos(yaw / 2),  # w
            0.0,  # x
            0.0,  # y
            np.sin(yaw / 2)   # z
        ], dtype=np.float32)
        return heading_quat
    
    @staticmethod
    def _quat_to_rotation_matrix(quat_xyzw: np.ndarray) -> np.ndarray:
        """
        Convert quaternion (xyzw) to rotation matrix.
        
        Args:
            quat_xyzw: Quaternion [x, y, z, w]
        
        Returns:
            Rotation matrix [3, 3]
        """
        x, y, z, w = quat_xyzw
        
        # Build rotation matrix
        R = np.array([
            [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
        ])
        
        return R
