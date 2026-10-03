"""
G1 Robot Forward Kinematics using Pinocchio.
Converts joint-space observations (from Unitree SDK) to body-space observations (for DiffuseCLOC).
"""

import numpy as np
import pinocchio as pin
from typing import Optional, Dict
import torch

from .g1_reindex import (
    ISAACLAB_BODY_NAMES,
    ISAACLAB_DOF_NAMES,
    create_isaaclab_to_mujoco_mapping
)


class G1ForwardKinematics:
    """
    Forward kinematics calculator for G1 robot using Pinocchio.
    
    Converts Unitree SDK observations to DiffuseCLOC format:
    - Input: joint positions (29), joint velocities (29), IMU data (RPY, gyro)
    - Output: 192-dim state [body_pos(90), body_lin_vel(90), root_pos(3), root_rot(3), root_lin_vel(3), root_ang_vel(3)]
    """
    
    def __init__(self, urdf_path: str):
        """
        Initialize Pinocchio model from URDF.
        
        Args:
            urdf_path: Path to G1 URDF file
        """
        # Load robot model
        self.model = pin.buildModelFromUrdf(urdf_path)
        self.data = self.model.createData()
        
        # Get frame IDs for all bodies
        self.body_frame_ids = []
        for body_name in ISAACLAB_BODY_NAMES:
            if self.model.existFrame(body_name):
                frame_id = self.model.getFrameId(body_name)
                self.body_frame_ids.append(frame_id)
            else:
                raise ValueError(f"Body '{body_name}' not found in URDF model")
        
        # Create joint remapping from IsaacLab order to Pinocchio URDF order
        # Pinocchio orders joints based on URDF tree structure
        pinocchio_joint_names = [self.model.names[i] for i in range(1, self.model.njoints)]  # Skip universe
        self.joint_remapping = create_isaaclab_to_mujoco_mapping(pinocchio_joint_names)
        
        print(f"[G1FK] Initialized Pinocchio model from {urdf_path}")
        print(f"  Number of joints: {self.model.nv}")
        print(f"  Number of bodies: {len(self.body_frame_ids)}")
        print(f"  Joint remapping created: IsaacLab -> Pinocchio order")
    
    def compute_fk(
        self,
        joint_pos: np.ndarray,
        joint_vel: np.ndarray,
        imu_pose: Optional[np.ndarray] = None,
        imu_gyro: Optional[np.ndarray] = None,
        base_lin_vel: Optional[np.ndarray] = None,
        base_pos: Optional[np.ndarray] = None,
        isaaclab_q_order: bool = False,
        # backward-compat alias
        imu_rpy: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Compute forward kinematics to get 192-dim DiffuseCLOC state.
        
        Args:
            joint_pos: Joint positions [29] (actuated joints only)
            joint_vel: Joint velocities [29]
            imu_pose: IMU orientation as roll-pitch-yaw [3] OR quaternion wxyz [4] (world frame).
                      Accepts the deprecated alias `imu_rpy` for backward compatibility.
            imu_gyro: IMU angular velocity [3] (world frame)
            base_lin_vel: Base linear velocity [3] (world frame, optional, estimated if None)
            base_pos: Base position in world frame [3] (world frame, optional, zero if None)
        
        Returns:
            state_dict with:
                - 'body_pos': Body positions [30, 3] = 90 dims
                - 'body_lin_vel': Body linear velocities [30, 3] = 90 dims
                - 'root_pos': Root position [3]
                - 'root_rot': Root rotation as rotation vector [3]
                - 'root_lin_vel': Root linear velocity [3]
                - 'root_ang_vel': Root angular velocity [3]
                - 'state': Concatenated 192-dim state vector
        """
        # Resolve imu_pose / imu_rpy alias
        if imu_pose is None and imu_rpy is None:
            raise ValueError("imu_pose (or deprecated imu_rpy) must be provided")
        if imu_pose is None:
            imu_pose = imu_rpy  # backward compat
        # Convert quaternion wxyz [4] to RPY [3] if necessary
        if imu_pose.shape[-1] == 4:
            imu_rpy = self._quat_wxyz_to_rpy(imu_pose)
        else:
            imu_rpy = imu_pose

        # Compute FK in base frame (fixed base model - 29 DOFs only)
        # Pinocchio configuration: just joint positions [29]
        if isaaclab_q_order:
            # Remap from IsaacLab order to Pinocchio URDF order
            q = joint_pos[self.joint_remapping]
            v = joint_vel[self.joint_remapping]
        else:
            q = joint_pos
            v = joint_vel
        
        # Compute forward kinematics in base frame
        pin.forwardKinematics(self.model, self.data, q, v)
        pin.updateFramePlacements(self.model, self.data)
        
        # Extract body positions and velocities in base frame
        body_pos_base = np.zeros((len(self.body_frame_ids), 3))
        body_lin_vel_base = np.zeros((len(self.body_frame_ids), 3))
        
        for i, frame_id in enumerate(self.body_frame_ids):
            # Get body position in base frame
            body_pos_base[i] = self.data.oMf[frame_id].translation
            
            # Get body velocity in base frame
            v_frame = pin.getFrameVelocity(
                self.model, self.data, frame_id, pin.ReferenceFrame.LOCAL_WORLD_ALIGNED
            )
            body_lin_vel_base[i] = v_frame.linear
        
        # Convert RPY to rotation matrix for world frame transformation
        base_rot_mat = self._rpy_to_rotation_matrix(imu_rpy)
        
        # Get base position (default to zero if not provided)
        base_position = base_pos if base_pos is not None else np.zeros(3)
        base_lin_vel = base_lin_vel if base_lin_vel is not None else np.zeros(3)
        
        # Transform positions and velocities to world frame
        body_pos = np.zeros((len(self.body_frame_ids), 3))
        body_lin_vel = np.zeros((len(self.body_frame_ids), 3))
        
        for i in range(len(self.body_frame_ids)):
            # Transform position to world frame: p_world = R * p_base + t
            body_pos[i] = base_rot_mat @ body_pos_base[i] + base_position
            
            # Transform velocity to world frame: v_world = R * v_base + v_root + ω × r
            # where ω is root angular velocity and r is position vector from root to body
            # Position vector from root to body in world frame
            r = body_pos[i] - base_position
            
            #BUG: Looks like some thing is not considered here
            # Velocity contribution from root angular velocity: ω × r
            ang_vel_contribution = np.cross(imu_gyro, r)
            
            body_lin_vel[i] = base_rot_mat @ body_lin_vel_base[i] + base_lin_vel + ang_vel_contribution
        
        # Extract root (pelvis) state
        # Use base_pos if provided, otherwise use pelvis position from FK
        root_pos = base_position if base_pos is not None else body_pos[0]
        
        # Root rotation as rotation vector (axis-angle)
        root_rot = self._rpy_to_quat(imu_rpy)
        #[xyzw] -> [wxyz] for conversion
        root_rot = np.array([root_rot[3], root_rot[0], root_rot[1], root_rot[2]])
        # root_rot = self._quat_to_rotvec(root_quat_xyzw)
        
        root_lin_vel = base_lin_vel if base_lin_vel is not None else np.zeros(3)
        root_ang_vel = imu_gyro
        
        # Flatten to match DiffuseCLOC format (192 dims)
        state = np.concatenate([
            body_pos.flatten(),      # 90 dims
            body_lin_vel.flatten(),  # 90 dims
            root_pos,                # 3 dims
            root_rot,                # 4 dims
            root_lin_vel,            # 3 dims
            root_ang_vel,            # 3 dims
        ])
        
        return {
            'body_pos': body_pos,
            'body_lin_vel': body_lin_vel,
            'root_pos': root_pos,
            'root_rot': root_rot,
            'root_lin_vel': root_lin_vel,
            'root_ang_vel': root_ang_vel,
            'state': state,
        }
    
    @staticmethod
    def _rpy_to_quat(rpy: np.ndarray) -> np.ndarray:
        """Convert roll-pitch-yaw to quaternion [x, y, z, w]"""
        roll, pitch, yaw = rpy
        
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)
        
        qw = cr * cp * cy + sr * sp * sy
        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy
        
        return np.array([qx, qy, qz, qw])
    
    @staticmethod
    def _rpy_to_rotation_matrix(rpy: np.ndarray) -> np.ndarray:
        """Convert roll-pitch-yaw to 3x3 rotation matrix"""
        roll, pitch, yaw = rpy
        
        # Rotation matrix from ZYX Euler angles (yaw-pitch-roll)
        cr, sr = np.cos(roll), np.sin(roll)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)
        
        # R = Rz(yaw) * Ry(pitch) * Rx(roll)
        R = np.array([
            [cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr],
            [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr],
            [-sp,   cp*sr,            cp*cr           ]
        ])
        
        return R
    
    @staticmethod
    def _quat_wxyz_to_rpy(q: np.ndarray) -> np.ndarray:
        """Convert quaternion [w, x, y, z] to roll-pitch-yaw [3]."""
        qw, qx, qy, qz = q
        roll  = np.arctan2(2*(qw*qx + qy*qz), 1 - 2*(qx*qx + qy*qy))
        sinp  = 2*(qw*qy - qz*qx)
        pitch = np.arcsin(np.clip(sinp, -1.0, 1.0))
        yaw   = np.arctan2(2*(qw*qz + qx*qy), 1 - 2*(qy*qy + qz*qz))
        return np.array([roll, pitch, yaw])

    @staticmethod
    def _quat_to_rotvec(quat_xyzw: np.ndarray) -> np.ndarray:
        """Convert quaternion [x, y, z, w] to rotation vector (axis-angle)"""
        qx, qy, qz, qw = quat_xyzw
        
        # Normalize quaternion
        norm = np.sqrt(qx**2 + qy**2 + qz**2 + qw**2)
        qx, qy, qz, qw = qx/norm, qy/norm, qz/norm, qw/norm
        
        # Compute angle
        angle = 2 * np.arccos(np.clip(qw, -1, 1))
        
        # Compute axis
        if np.abs(angle) < 1e-10:
            # Small angle, return zero rotation
            return np.zeros(3)
        
        s = np.sqrt(1 - qw**2)
        if s < 1e-10:
            # Avoid division by zero
            axis = np.array([1, 0, 0])
        else:
            axis = np.array([qx, qy, qz]) / s
        
        # Rotation vector is axis * angle
        return axis * angle

