"""
Real-time robot visualization debugger for sim2sim alignment.
Visualizes body positions, velocities, and kinematic tree for debugging policy execution.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
import time
from pathlib import Path
from typing import Dict, Optional, List
from collections import deque


# G1 kinematic chain in IsaacLab body ordering (30 bodies, alphabetical from URDF)
SKELETON_CONNECTIONS = []

# Left leg chain: pelvis -> left_ankle_roll
left_leg = [0, 1, 4, 7, 10, 14, 18]
for i in range(len(left_leg) - 1):
    SKELETON_CONNECTIONS.append((left_leg[i], left_leg[i+1]))

# Right leg chain: pelvis -> right_ankle_roll
right_leg = [0, 2, 5, 8, 11, 15, 19]
for i in range(len(right_leg) - 1):
    SKELETON_CONNECTIONS.append((right_leg[i], right_leg[i+1]))

# Torso chain: pelvis -> torso
torso = [0, 3, 6, 9]
for i in range(len(torso) - 1):
    SKELETON_CONNECTIONS.append((torso[i], torso[i+1]))

# Left arm chain: torso -> left_wrist_yaw
left_arm = [9, 12, 16, 20, 22, 24, 26, 28]
for i in range(len(left_arm) - 1):
    SKELETON_CONNECTIONS.append((left_arm[i], left_arm[i+1]))

# Right arm chain: torso -> right_wrist_yaw
right_arm = [9, 13, 17, 21, 23, 25, 27, 29]
for i in range(len(right_arm) - 1):
    SKELETON_CONNECTIONS.append((right_arm[i], right_arm[i+1]))


class CLoCFdbDebugger:
    """
    Real-time visualizer for robot body positions and velocities during policy execution.
    Designed for debugging sim2sim alignment between Isaac Lab and Unitree environments.
    """

    def __init__(
        self,
        output_dir: str,
        history_length: int = 200,
        update_interval: int = 5,
        show_velocities: bool = True,
        show_root_states: bool = True,
        show_rlobs: bool = False,
        vel_scale: float = 0.1,
        save_frequency: str = "never",  # "never", "on_close", "every_n_frames"
        save_every_n: int = 100,
        runner_name: str = "runner"
    ):
        """
        Initialize the debugger.
        
        Args:
            output_dir: Directory to save visualizations
            history_length: Number of frames to keep in history for trajectory visualization
            update_interval: Update visualization every N frames (1 = every frame)
            show_velocities: Whether to show velocity arrows
            show_root_states: Whether to show root position/rotation/velocity plots
            show_rlobs: Whether to show RLObs terms (gravity/base velocities/last action stats)
            vel_scale: Scale factor for velocity arrow length
            save_frequency: When to save frames ("never", "on_close", "every_n_frames")
            save_every_n: Save every N frames if save_frequency="every_n_frames"
            runner_name: Name of the runner (for labeling)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_length = history_length
        self.update_interval = update_interval
        self.show_velocities = show_velocities
        self.show_root_states = show_root_states
        self.show_rlobs = show_rlobs
        self.vel_scale = vel_scale
        self.save_frequency = save_frequency
        self.save_every_n = save_every_n
        self.runner_name = runner_name
        
        # Data storage
        self.frame_count = 0
        self.body_pos_history = deque(maxlen=history_length)
        self.body_vel_history = deque(maxlen=history_length) if show_velocities else None
        needs_root_pose_history = show_root_states or show_rlobs
        self.root_pos_history = deque(maxlen=history_length) if needs_root_pose_history else None
        self.root_rot_history = deque(maxlen=history_length) if needs_root_pose_history else None
        self.root_ang_vel_history = deque(maxlen=history_length) if show_root_states else None
        self.projected_gravity_history = deque(maxlen=history_length) if show_rlobs else None
        self.base_lin_vel_history = deque(maxlen=history_length) if show_rlobs else None
        self.base_ang_vel_history = deque(maxlen=history_length) if show_rlobs else None
        self.last_actions_history = deque(maxlen=history_length) if show_rlobs else None
        
        # Figure setup
        self.fig = None
        self.ax = None
        self.ax_root = None  # Second axis for root states
        self.ax_rlobs = None
        self.ax_last_action = None
        self.initialized = False
        
        # Axis limits (will be auto-adjusted)
        self.x_range = [-1.5, 1.5]
        self.y_range = [-1.5, 1.5]
        self.z_range = [-0.1, 2.0]
        
        print(f"[CLoCFdbDebugger] Initialized for {runner_name}")
        print(f"  Output dir: {self.output_dir}")
        print(f"  History length: {history_length}")
        print(f"  Update interval: {update_interval}")
        print(f"  Show velocities: {show_velocities}")
        print(f"  Show root states: {show_root_states}")
        print(f"  Show RLObs: {show_rlobs}")

    @staticmethod
    def _to_1d_numpy(value: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Convert tensor-like input into a 1D numpy array for plotting."""
        if value is None:
            return None
        arr = np.asarray(value)
        return arr.reshape(-1)

    @staticmethod
    def _quat_wxyz_to_rotmat(quat_wxyz: np.ndarray) -> np.ndarray:
        """Convert quaternion [w, x, y, z] to a rotation matrix."""
        quat = np.asarray(quat_wxyz, dtype=np.float64).reshape(-1)
        if quat.shape[0] != 4:
            return np.eye(3)

        norm = np.linalg.norm(quat)
        if norm < 1e-12:
            return np.eye(3)
        quat = quat / norm

        w, x, y, z = quat
        return np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ], dtype=np.float64)

    def _rotate_body_to_world(self, vec_body: np.ndarray, root_rot_wxyz: np.ndarray) -> np.ndarray:
        """Rotate a body-frame vector into world frame using root orientation."""
        if vec_body is None:
            return np.zeros(3, dtype=np.float64)
        vec = np.asarray(vec_body, dtype=np.float64).reshape(-1)
        if vec.shape[0] != 3:
            return np.zeros(3, dtype=np.float64)
        rot = self._quat_wxyz_to_rotmat(root_rot_wxyz)
        return rot @ vec

    def _initialize_plot(self):
        """Initialize matplotlib figure and axes (non-blocking)."""
        if self.initialized:
            return
        
        plt.ion()  # Interactive mode for non-blocking display
        
        if self.show_rlobs:
            # Left: 3D robot, Right: RLObs time-series panels.
            self.fig = plt.figure(figsize=(18, 10))
            gs = self.fig.add_gridspec(2, 2, width_ratios=[2.0, 1.0], height_ratios=[1.0, 1.0])
            self.ax = self.fig.add_subplot(gs[:, 0], projection='3d')
            self.ax_rlobs = self.fig.add_subplot(gs[0, 1])
            self.ax_last_action = self.fig.add_subplot(gs[1, 1])
        else:
            # Single 3D view for both robot skeleton and root states
            self.fig = plt.figure(figsize=(14, 12))
            self.ax = self.fig.add_subplot(111, projection='3d')
        
        self.ax.set_xlim(self.x_range)
        self.ax.set_ylim(self.y_range)
        self.ax.set_zlim(self.z_range)
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_title(f'{self.runner_name} - Robot Visualization', fontsize=14, fontweight='bold')
        self.ax.set_box_aspect([1, 1, 1])
        
        self.initialized = True
        print(f"[CLoCFdbDebugger] Plot initialized")

    def update(self, obs_frame: Dict[str, np.ndarray]):
        """
        Update visualization with new observation frame.
        
        Args:
            obs_frame: Dictionary containing:
                - 'body_pos': [30, 3] or [1, 30, 3] body positions
                - 'body_lin_vel': [30, 3] or [1, 30, 3] body linear velocities (optional)
                - 'root_pos': [3] root position (optional)
                - 'root_rot': [4] root rotation quaternion (optional)
                - 'root_ang_vel': [3] root angular velocity (optional)
        """
        # Extract and reshape data
        body_pos = obs_frame.get('body_pos')
        if body_pos is None:
            print("[CLoCFdbDebugger] Warning: No body_pos in obs_frame")
            return
        
        # Handle shape variations
        if body_pos.ndim == 3:  # [1, 30, 3]
            body_pos = body_pos[0]
        
        body_vel = None
        if self.show_velocities and 'body_lin_vel' in obs_frame:
            body_vel = obs_frame['body_lin_vel']
            if body_vel.ndim == 3:
                body_vel = body_vel[0]
        
        # Extract root states
        root_pos = self._to_1d_numpy(obs_frame.get('root_pos'))
        root_rot = self._to_1d_numpy(obs_frame.get('root_rot'))
        root_ang_vel = self._to_1d_numpy(obs_frame.get('root_ang_vel'))

        projected_gravity = self._to_1d_numpy(obs_frame.get('projected_gravity'))
        base_lin_vel = self._to_1d_numpy(obs_frame.get('base_lin_vel'))
        base_ang_vel = self._to_1d_numpy(obs_frame.get('base_ang_vel'))
        last_actions = self._to_1d_numpy(obs_frame.get('last_actions'))
        
        # Store in history
        self.body_pos_history.append(body_pos.copy())
        if self.body_vel_history is not None and body_vel is not None:
            self.body_vel_history.append(body_vel.copy())
        if self.root_pos_history is not None and root_pos is not None:
            self.root_pos_history.append(root_pos.copy())
        if self.root_rot_history is not None and root_rot is not None:
            self.root_rot_history.append(root_rot.copy())
        if self.root_ang_vel_history is not None and root_ang_vel is not None:
            self.root_ang_vel_history.append(root_ang_vel.copy())
        if self.projected_gravity_history is not None and projected_gravity is not None:
            self.projected_gravity_history.append(projected_gravity.copy())
        if self.base_lin_vel_history is not None and base_lin_vel is not None:
            self.base_lin_vel_history.append(base_lin_vel.copy())
        if self.base_ang_vel_history is not None and base_ang_vel is not None:
            self.base_ang_vel_history.append(base_ang_vel.copy())
        if self.last_actions_history is not None and last_actions is not None:
            self.last_actions_history.append(last_actions.copy())
        
        # Update visualization at specified interval
        if self.frame_count % self.update_interval == 0:
            self._update_plot()
        
        self.frame_count += 1
        
        # Save frames if requested
        if self.save_frequency == "every_n_frames" and self.frame_count % self.save_every_n == 0:
            self._save_frame()

    def _update_plot(self):
        """Update the 3D plot with current data."""
        if not self.initialized:
            self._initialize_plot()
        
        if len(self.body_pos_history) == 0:
            return
        
        # Clear axes
        self.ax.clear()
        
        # Get current frame
        body_pos = self.body_pos_history[-1]
        
        # Auto-adjust axis limits based on current data with equal scaling
        # Calculate centers and ranges for each axis
        x_center = (body_pos[:, 0].min() + body_pos[:, 0].max()) / 2
        y_center = (body_pos[:, 1].min() + body_pos[:, 1].max()) / 2
        z_center = (body_pos[:, 2].min() + body_pos[:, 2].max()) / 2
        
        x_range = body_pos[:, 0].max() - body_pos[:, 0].min()
        y_range = body_pos[:, 1].max() - body_pos[:, 1].min()
        z_range = body_pos[:, 2].max() - body_pos[:, 2].min()
        
        # Use maximum range for all axes to ensure equal scaling
        max_range = max(x_range, y_range, z_range) + 1.0  # Add padding
        
        self.x_range = [x_center - max_range/2, x_center + max_range/2]
        self.y_range = [y_center - max_range/2, y_center + max_range/2]
        self.z_range = [z_center - max_range/2, z_center + max_range/2]
        
        self.ax.set_xlim(self.x_range)
        self.ax.set_ylim(self.y_range)
        self.ax.set_zlim(self.z_range)
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_title(f'{self.runner_name} - Frame {self.frame_count}', fontsize=14, fontweight='bold')
        self.ax.set_box_aspect([1, 1, 1])
        
        # Plot body points
        self.ax.scatter(body_pos[:, 0], body_pos[:, 1], body_pos[:, 2],
                       c='blue', marker='o', s=50, alpha=0.8, label='Bodies')
        
        # Plot skeleton connections
        for i, j in SKELETON_CONNECTIONS:
            self.ax.plot([body_pos[i, 0], body_pos[j, 0]],
                        [body_pos[i, 1], body_pos[j, 1]],
                        [body_pos[i, 2], body_pos[j, 2]],
                        'b-', linewidth=2, alpha=0.6)
        
        # Highlight pelvis
        self.ax.scatter(body_pos[0, 0], body_pos[0, 1], body_pos[0, 2],
                       c='red', marker='*', s=200, alpha=1.0, label='Pelvis')
        
        # Plot velocity arrows if enabled
        if self.show_velocities and self.body_vel_history is not None and len(self.body_vel_history) > 0:
            body_vel = self.body_vel_history[-1]
            # Show velocities for every 3rd body to avoid clutter
            for i in range(0, 30, 1):
                self.ax.quiver(body_pos[i, 0], body_pos[i, 1], body_pos[i, 2],
                              body_vel[i, 0], body_vel[i, 1], body_vel[i, 2],
                              color='cyan', alpha=0.6, arrow_length_ratio=0.3,
                              length=self.vel_scale, linewidth=1.5)
        
        # Plot trajectory history (pelvis only)
        if len(self.body_pos_history) > 1:
            history_array = np.array(self.body_pos_history)
            pelvis_traj = history_array[:, 0, :]  # [history_len, 3]
            self.ax.plot(pelvis_traj[:, 0], pelvis_traj[:, 1], pelvis_traj[:, 2],
                        'r--', linewidth=1, alpha=0.4, label='Pelvis Trajectory')
        
        # Plot root states if enabled (in same axis)
        if self.show_root_states and len(self.root_pos_history) > 0:
            self._update_root_plot()

        if self.show_rlobs:
            self._draw_rlobs_vectors_3d(body_pos)

        if self.show_rlobs and self.ax_rlobs is not None and self.ax_last_action is not None:
            self._update_rlobs_plot()
        
        self.ax.legend(loc='upper right')
        
        # Refresh display
        plt.draw()
        plt.pause(0.001)

    def _draw_rlobs_vectors_3d(self, body_pos: np.ndarray):
        """Draw RLObs vectors (projected gravity, base lin vel, base ang vel) in world frame."""
        if (
            self.projected_gravity_history is None
            or self.base_lin_vel_history is None
            or self.base_ang_vel_history is None
            or len(self.projected_gravity_history) == 0
            or len(self.base_lin_vel_history) == 0
            or len(self.base_ang_vel_history) == 0
        ):
            return

        anchor = np.asarray(body_pos[0], dtype=np.float64)
        if self.root_pos_history is not None and len(self.root_pos_history) > 0:
            root_pos = np.asarray(self.root_pos_history[-1], dtype=np.float64).reshape(-1)
            if root_pos.shape[0] == 3:
                anchor = root_pos

        root_rot = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        if self.root_rot_history is not None and len(self.root_rot_history) > 0:
            rr = np.asarray(self.root_rot_history[-1], dtype=np.float64).reshape(-1)
            if rr.shape[0] == 4:
                root_rot = rr

        gravity_world = self._rotate_body_to_world(self.projected_gravity_history[-1], root_rot)
        base_lin_world = self._rotate_body_to_world(self.base_lin_vel_history[-1], root_rot)
        base_ang_world = self._rotate_body_to_world(self.base_ang_vel_history[-1], root_rot)

        # Normalize gravity to emphasize expected downward direction.
        gravity_norm = np.linalg.norm(gravity_world)
        if gravity_norm > 1e-8:
            gravity_draw = gravity_world / gravity_norm * 0.45
        else:
            gravity_draw = np.zeros(3, dtype=np.float64)

        lin_draw = base_lin_world * 0.35
        ang_draw = base_ang_world * 0.25

        self.ax.quiver(
            anchor[0], anchor[1], anchor[2],
            gravity_draw[0], gravity_draw[1], gravity_draw[2],
            color='gold', alpha=0.95, linewidth=3.0, arrow_length_ratio=0.2,
            label='projected_gravity (world)'
        )
        self.ax.quiver(
            anchor[0], anchor[1], anchor[2],
            lin_draw[0], lin_draw[1], lin_draw[2],
            color='lime', alpha=0.9, linewidth=2.5, arrow_length_ratio=0.2,
            label='base_lin_vel (world)'
        )
        self.ax.quiver(
            anchor[0], anchor[1], anchor[2],
            ang_draw[0], ang_draw[1], ang_draw[2],
            color='magenta', alpha=0.9, linewidth=2.5, arrow_length_ratio=0.2,
            label='base_ang_vel (world)'
        )

        # Label anchor point to clarify RLObs vector origin.
        self.ax.scatter(anchor[0], anchor[1], anchor[2], c='black', marker='x', s=80, alpha=0.9)

    def _update_rlobs_plot(self):
        """Plot RLObs terms and last-action stats over time."""
        self.ax_rlobs.clear()
        self.ax_last_action.clear()

        if (
            self.projected_gravity_history is None
            or self.base_lin_vel_history is None
            or self.base_ang_vel_history is None
            or len(self.projected_gravity_history) == 0
        ):
            self.ax_rlobs.text(0.5, 0.5, "RLObs not available", ha='center', va='center')
            self.ax_last_action.text(0.5, 0.5, "No action history", ha='center', va='center')
            return

        pg = np.array(self.projected_gravity_history)
        blv = np.array(self.base_lin_vel_history)
        bav = np.array(self.base_ang_vel_history)
        t = np.arange(pg.shape[0])

        self.ax_rlobs.plot(t, pg[:, 0], 'b-', linewidth=1.5, label='g_x')
        self.ax_rlobs.plot(t, pg[:, 1], 'b--', linewidth=1.5, label='g_y')
        self.ax_rlobs.plot(t, pg[:, 2], 'b:', linewidth=1.5, label='g_z')
        self.ax_rlobs.plot(t, blv[:, 0], 'g-', linewidth=1.2, label='v_x')
        self.ax_rlobs.plot(t, blv[:, 1], 'g--', linewidth=1.2, label='v_y')
        self.ax_rlobs.plot(t, blv[:, 2], 'g:', linewidth=1.2, label='v_z')
        self.ax_rlobs.plot(t, bav[:, 0], 'r-', linewidth=1.2, label='w_x')
        self.ax_rlobs.plot(t, bav[:, 1], 'r--', linewidth=1.2, label='w_y')
        self.ax_rlobs.plot(t, bav[:, 2], 'r:', linewidth=1.2, label='w_z')
        self.ax_rlobs.set_title('RLObs Components')
        self.ax_rlobs.set_xlabel('History frame')
        self.ax_rlobs.set_ylabel('Value')
        self.ax_rlobs.grid(True, alpha=0.3)
        self.ax_rlobs.legend(loc='upper right', ncol=3, fontsize=8)

        if self.last_actions_history is None or len(self.last_actions_history) == 0:
            self.ax_last_action.text(0.5, 0.5, "No last_actions", ha='center', va='center')
            return

        actions = np.array(self.last_actions_history)
        action_l2 = np.linalg.norm(actions, axis=1)
        action_max = np.max(np.abs(actions), axis=1)
        t_actions = np.arange(actions.shape[0])

        self.ax_last_action.plot(t_actions, action_l2, 'm-', linewidth=1.5, label='||last_actions||_2')
        self.ax_last_action.plot(t_actions, action_max, color='orange', linewidth=1.5, label='max |last_actions|')
        self.ax_last_action.set_title('Last Action Stats')
        self.ax_last_action.set_xlabel('History frame')
        self.ax_last_action.set_ylabel('Magnitude')
        self.ax_last_action.grid(True, alpha=0.3)
        self.ax_last_action.legend(loc='upper right', fontsize=8)

    def _update_root_plot(self):
        """Draw root state in same axis (pivot with xyz axes, angular velocity arrow, trajectory)."""
        # Get history data
        n_frames = len(self.root_pos_history)
        if n_frames == 0:
            return
        
        # Convert to arrays
        root_pos_array = np.array(self.root_pos_history)  # [n_frames, 3]
        root_rot_array = np.array(self.root_rot_history) if len(self.root_rot_history) > 0 else None
        root_ang_vel_array = np.array(self.root_ang_vel_history) if len(self.root_ang_vel_history) > 0 else None
        
        # Get current root position, rotation, and angular velocity
        current_pos = root_pos_array[-1]
        current_rot = root_rot_array[-1] if root_rot_array is not None and len(root_rot_array) > 0 else np.array([1, 0, 0, 0])  # [w, x, y, z]
        current_ang_vel = root_ang_vel_array[-1] if root_ang_vel_array is not None and len(root_ang_vel_array) > 0 else np.zeros(3)
        
        # Plot root pivot point
        self.ax.scatter(current_pos[0], current_pos[1], current_pos[2],
                       c='purple', marker='D', s=200, alpha=1.0, edgecolors='darkviolet', linewidths=2)
        
        # Convert quaternion to rotation matrix for xyz axes
        # Quaternion format: [w, x, y, z]
        w, x, y, z = current_rot[0], current_rot[1], current_rot[2], current_rot[3]
        R = np.array([
            [1 - 2*(y**2 + z**2), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x**2 + z**2), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x**2 + y**2)]
        ])
        
        # Draw xyz axes at root pivot (using rotation matrix)
        axis_length = 0.3
        x_axis = R[:, 0] * axis_length  # X axis (red)
        y_axis = R[:, 1] * axis_length  # Y axis (green)
        z_axis = R[:, 2] * axis_length  # Z axis (blue)
        
        self.ax.quiver(current_pos[0], current_pos[1], current_pos[2],
                      x_axis[0], x_axis[1], x_axis[2],
                      color='red', alpha=0.9, arrow_length_ratio=0.3, linewidth=2.5)
        self.ax.quiver(current_pos[0], current_pos[1], current_pos[2],
                      y_axis[0], y_axis[1], y_axis[2],
                      color='green', alpha=0.9, arrow_length_ratio=0.3, linewidth=2.5)
        self.ax.quiver(current_pos[0], current_pos[1], current_pos[2],
                      z_axis[0], z_axis[1], z_axis[2],
                      color='blue', alpha=0.9, arrow_length_ratio=0.3, linewidth=2.5)
        
        # Plot angular velocity as arrow
        ang_vel_magnitude = np.linalg.norm(current_ang_vel)
        if ang_vel_magnitude > 1e-6:  # Only show if non-zero
            ang_vel_scale = ang_vel_magnitude * 0.5
            self.ax.quiver(current_pos[0], current_pos[1], current_pos[2],
                          current_ang_vel[0], current_ang_vel[1], current_ang_vel[2],
                          color='orange', alpha=0.8, arrow_length_ratio=0.2,
                          length=ang_vel_scale, linewidth=3)
        
        # Plot root trajectory history
        if n_frames > 1:
            self.ax.plot(root_pos_array[:, 0], root_pos_array[:, 1], root_pos_array[:, 2],
                        'purple', linestyle='--', linewidth=2, alpha=0.5)
            
            # Add trajectory points with gradient alpha
            alphas = np.linspace(0.2, 0.8, n_frames)
            for i in range(0, n_frames, max(1, n_frames // 20)):  # Sample points to avoid clutter
                self.ax.scatter(root_pos_array[i, 0], root_pos_array[i, 1], root_pos_array[i, 2],
                               c='purple', marker='.', s=30, alpha=alphas[i])
    
    def _save_frame(self):
        """Save current frame to file."""
        if not self.initialized or self.fig is None:
            return
        
        frame_path = self.output_dir / f"frame_{self.frame_count:06d}.png"
        self.fig.savefig(frame_path, dpi=100, bbox_inches='tight')
        print(f"[CLoCFdbDebugger] Saved frame to {frame_path}")

    def close(self):
        """Clean up and close visualization."""
        if self.save_frequency == "on_close" and self.initialized:
            final_path = self.output_dir / f"final_frame_{self.runner_name}.png"
            self.fig.savefig(final_path, dpi=150, bbox_inches='tight')
            print(f"[CLoCFdbDebugger] Saved final frame to {final_path}")
        
        if self.fig is not None:
            plt.close(self.fig)
        
        print(f"[CLoCFdbDebugger] Closed (total frames: {self.frame_count})")


def debugger_worker_process(data_queue, config_dict, output_dir, runner_name):
    """
    Worker process for CLoCFdbDebugger to run in parallel with simulation.
    
    Args:
        data_queue: Queue for receiving observation data
        config_dict: Configuration dictionary for debugger
        output_dir: Output directory for visualizations
        runner_name: Name of the runner (for labeling)
    """
    try:
        # Initialize debugger
        debugger = CLoCFdbDebugger(
            output_dir=output_dir,
            history_length=config_dict.get('history_length', 200),
            update_interval=config_dict.get('update_interval', 5),
            show_velocities=config_dict.get('show_velocities', True),
            show_root_states=config_dict.get('show_root_states', True),
            show_rlobs=config_dict.get('show_rlobs', False),
            vel_scale=config_dict.get('vel_scale', 0.1),
            save_frequency=config_dict.get('save_frequency', 'never'),
            save_every_n=config_dict.get('save_every_n', 100),
            runner_name=runner_name
        )
        
        print(f"[CLoCFdbDebugger] Worker process started for {runner_name}")
        
        # Process data from queue
        while True:
            try:
                data = data_queue.get(timeout=1.0)
                
                if data is None:  # Shutdown signal
                    print(f"[CLoCFdbDebugger] Received shutdown signal")
                    break
                
                # Update visualization with new frame
                debugger.update(data)
                
            except Exception as e:
                if "Empty" not in str(e):  # Ignore queue.Empty timeout
                    print(f"[CLoCFdbDebugger] Error processing data: {e}")
                continue
        
        # Cleanup
        debugger.close()
        print(f"[CLoCFdbDebugger] Worker process ended for {runner_name}")
        
    except Exception as e:
        print(f"[CLoCFdbDebugger] Fatal error in worker process: {e}")
        import traceback
        traceback.print_exc()
    