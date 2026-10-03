"""
CLoC Trajectory Analyzer for visualizing and debugging DiffuseCLoC inference.
Provides real-time visualization of observations, predicted actions, and states.
"""

import numpy as np
import torch
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, Rectangle
from collections import deque
import time
from typing import Dict, List, Optional, Tuple, Any

class CLoCAnalyzer:
    """
    Real-time analyzer for DiffuseCLoC trajectories during inference.
    
    Features:
    - Live trajectory visualization
    - Action/state prediction analysis
    - Velocity and command tracking
    - Performance metrics
    - Episode state monitoring
    """
    
    def __init__(
        self,
        n_obs_steps: int = 4,
        horizon: int = 20,
        history_length: int = 200,
        update_interval: int = 10,
        save_plots: bool = False,
        output_dir: str = "./analysis_plots/",
        selected_dims: Optional[Dict[str, List[int]]] = None
    ):
        """
        Initialize CLoC analyzer.
        
        Args:
            n_obs_steps: Observation history length
            horizon: Prediction horizon
            history_length: Number of timesteps to keep in memory
            update_interval: Update visualization every N steps
            save_plots: Whether to save plot frames
            output_dir: Directory for saved plots
            selected_dims: Dictionary specifying which dimensions to visualize
                          e.g., {'obs': [0,1,2], 'action': [0,1], 'state': [180,181,182]}
        """
        self.n_obs_steps = n_obs_steps
        self.horizon = horizon
        self.history_length = history_length
        self.update_interval = update_interval
        self.save_plots = save_plots
        self.output_dir = output_dir
        
        # Default dimension selection for G1 robot
        if selected_dims is None:
            self.selected_dims = {
                'obs': [180, 181, 182, 183, 184, 185],  # Root pos + lin vel
                'action': [0, 1, 2, 3, 4, 5],          # Hip joints
                'state': [180, 181, 182, 183, 184, 185] # Root pos + lin vel
            }
        else:
            self.selected_dims = selected_dims
        
        # Data storage
        self.reset_data()
        
        # Visualization setup
        self.setup_visualization()
        
        # Performance tracking
        self.perf_metrics = {
            'inference_times': deque(maxlen=100),
            'action_magnitudes': deque(maxlen=100),
            'velocity_tracking': deque(maxlen=100),
            'step_count': 0,
            'episode_count': 0
        }
        
    def reset_data(self):
        """Reset all stored trajectory data."""
        self.trajectory_data = {
            'timestamps': deque(maxlen=self.history_length),
            'observations': deque(maxlen=self.history_length),
            'actions_executed': deque(maxlen=self.history_length),
            'actions_predicted': deque(maxlen=self.history_length),
            'states_predicted': deque(maxlen=self.history_length),
            'rewards': deque(maxlen=self.history_length),
            'env_commands': deque(maxlen=self.history_length),
            'robot_velocities': deque(maxlen=self.history_length)
        }
        
    def setup_visualization(self):
        """Setup matplotlib figures and axes for visualization."""
        plt.ion()  # Interactive mode
        
        # Create subplots
        self.fig, self.axes = plt.subplots(2, 3, figsize=(18, 12))
        self.fig.suptitle('DiffuseCLoC Trajectory Analysis', fontsize=16)
        
        # Subplot titles and configurations
        subplot_configs = [
            ('Observation History', 'obs'),
            ('Action Trajectories', 'action'),
            ('State Predictions', 'state'),
            ('Robot Velocities', 'velocity'),
            ('Performance Metrics', 'metrics'),
            ('Episode Progress', 'episode')
        ]
        
        self.subplot_info = {}
        for i, (title, key) in enumerate(subplot_configs):
            row, col = i // 3, i % 3
            ax = self.axes[row, col]
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            self.subplot_info[key] = {'ax': ax, 'lines': {}}
            
        plt.tight_layout()
        
    def analyze_step(
        self,
        step_idx: int,
        obs_history: torch.Tensor,
        action_traj: torch.Tensor,
        state_traj: torch.Tensor,
        executed_action: torch.Tensor,
        reward: float,
        env_info: Dict[str, Any],
        inference_time: float
    ):
        """
        Analyze a single step of policy execution.
        
        Args:
            step_idx: Current step index
            obs_history: (B, n_obs_steps, obs_dim) - Observation history
            action_traj: (B, horizon, action_dim) - Predicted action trajectory
            state_traj: (B, horizon, state_dim) - Predicted state trajectory
            executed_action: (B, action_dim) - Actually executed action
            reward: Current step reward
            env_info: Environment information dict
            inference_time: Time taken for policy inference (seconds)
        """
        # Convert to numpy for analysis (use first env)
        obs_np = obs_history[0].cpu().numpy()  # (n_obs_steps, obs_dim)
        action_traj_np = action_traj[0].cpu().numpy()  # (horizon, action_dim)
        state_traj_np = state_traj[0].cpu().numpy()  # (horizon, state_dim)
        executed_action_np = executed_action[0].cpu().numpy()  # (action_dim,)
        
        # Store data
        self.trajectory_data['timestamps'].append(step_idx)
        self.trajectory_data['observations'].append(obs_np[-1])  # Current obs
        self.trajectory_data['actions_executed'].append(executed_action_np)
        self.trajectory_data['actions_predicted'].append(action_traj_np)
        self.trajectory_data['states_predicted'].append(state_traj_np)
        self.trajectory_data['rewards'].append(reward)
        
        # Extract environment-specific info
        cmd_vel = env_info.get('commands', np.zeros(3))
        robot_vel = self._extract_robot_velocity(obs_np[-1])
        
        self.trajectory_data['env_commands'].append(cmd_vel)
        self.trajectory_data['robot_velocities'].append(robot_vel)
        
        # Update performance metrics
        self._update_performance_metrics(
            inference_time, executed_action_np, robot_vel, cmd_vel
        )
        
        # Visualize periodically
        if step_idx % self.update_interval == 0:
            self._update_visualization()
            
        # Print diagnostics
        if step_idx % 50 == 0:
            self._print_diagnostics(step_idx)
            
    def _extract_robot_velocity(self, obs: np.ndarray) -> np.ndarray:
        """Extract robot linear velocity from observation."""
        # For G1 robot, linear velocity is typically at dims 183:186
        if len(obs) >= 186:
            return obs[183:186]  # [vx, vy, vz]
        else:
            return np.zeros(3)
            
    def _update_performance_metrics(
        self,
        inference_time: float,
        action: np.ndarray,
        robot_vel: np.ndarray,
        cmd_vel: np.ndarray
    ):
        """Update performance tracking metrics."""
        self.perf_metrics['inference_times'].append(inference_time)
        self.perf_metrics['action_magnitudes'].append(np.linalg.norm(action))
        
        # Velocity tracking error
        if len(cmd_vel) >= 2 and len(robot_vel) >= 2:
            vel_error = np.linalg.norm(robot_vel[:2] - cmd_vel[:2])
            self.perf_metrics['velocity_tracking'].append(vel_error)
        
        self.perf_metrics['step_count'] += 1
        
    def _update_visualization(self):
        """Update all visualization subplots."""
        if len(self.trajectory_data['timestamps']) < 2:
            return
            
        try:
            self._plot_observation_history()
            self._plot_action_trajectories()
            self._plot_state_predictions()
            self._plot_velocity_tracking()
            self._plot_performance_metrics()
            self._plot_episode_progress()
            
            plt.pause(0.01)  # Brief pause for rendering
            
        except Exception as e:
            print(f"Visualization update failed: {e}")
            
    def _plot_observation_history(self):
        """Plot observation history for selected dimensions."""
        ax = self.subplot_info['obs']['ax']
        ax.clear()
        ax.set_title('Observation History (Selected Dims)')
        
        if len(self.trajectory_data['observations']) < 2:
            return
            
        # Get recent observations
        recent_obs = list(self.trajectory_data['observations'])[-50:]
        obs_array = np.array(recent_obs)  # (timesteps, obs_dim)
        
        # Plot selected dimensions
        for i, dim in enumerate(self.selected_dims['obs'][:6]):  # Limit to 6 dims
            if dim < obs_array.shape[1]:
                ax.plot(obs_array[:, dim], label=f'dim_{dim}', alpha=0.7)
                
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Time Steps (recent 50)')
        
    def _plot_action_trajectories(self):
        """Plot predicted vs executed actions."""
        ax = self.subplot_info['action']['ax']
        ax.clear()
        ax.set_title('Action Trajectories')
        
        if len(self.trajectory_data['actions_executed']) < 2:
            return
            
        # Plot executed actions (history)
        executed = np.array(list(self.trajectory_data['actions_executed'])[-30:])
        for i, dim in enumerate(self.selected_dims['action'][:4]):
            if dim < executed.shape[1]:
                ax.plot(executed[:, dim], 'o-', label=f'exec_dim_{dim}', alpha=0.7)
        
        # Plot current prediction (future)
        if len(self.trajectory_data['actions_predicted']) > 0:
            current_pred = self.trajectory_data['actions_predicted'][-1]
            x_pred = np.arange(len(executed), len(executed) + len(current_pred))
            
            for i, dim in enumerate(self.selected_dims['action'][:4]):
                if dim < current_pred.shape[1]:
                    ax.plot(x_pred, current_pred[:, dim], '--', 
                           label=f'pred_dim_{dim}', alpha=0.5)
        
        ax.axvline(x=len(executed)-1, color='red', linestyle=':', alpha=0.5, 
                  label='Current Time')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
    def _plot_state_predictions(self):
        """Plot state predictions and root position trajectory."""
        ax = self.subplot_info['state']['ax']
        ax.clear()
        ax.set_title('State Predictions (Root Position)')
        
        if len(self.trajectory_data['states_predicted']) < 2:
            return
            
        # Plot root position trajectory (XY plane)
        observations = list(self.trajectory_data['observations'])[-50:]
        if len(observations) > 0:
            obs_array = np.array(observations)
            if obs_array.shape[1] >= 183:
                # Plot historical root positions
                ax.plot(obs_array[:, 180], obs_array[:, 181], 'b-o', 
                       markersize=2, label='Historical', alpha=0.7)
                
                # Plot current position
                current_pos = obs_array[-1, 180:182]
                ax.plot(current_pos[0], current_pos[1], 'ro', markersize=8, 
                       label='Current')
                
                # Plot predicted trajectory
                if len(self.trajectory_data['states_predicted']) > 0:
                    pred_states = self.trajectory_data['states_predicted'][-1]
                    if pred_states.shape[1] >= 183:
                        pred_x = pred_states[:, 180] + current_pos[0]
                        pred_y = pred_states[:, 181] + current_pos[1]
                        ax.plot(pred_x, pred_y, 'g--', alpha=0.6, label='Predicted')
        
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
        
    def _plot_velocity_tracking(self):
        """Plot velocity command vs actual velocity."""
        ax = self.subplot_info['velocity']['ax']
        ax.clear()
        ax.set_title('Velocity Tracking')
        
        if len(self.trajectory_data['robot_velocities']) < 2:
            return
            
        # Get recent data
        robot_vels = np.array(list(self.trajectory_data['robot_velocities'])[-50:])
        cmd_vels = np.array(list(self.trajectory_data['env_commands'])[-50:])
        
        time_steps = np.arange(len(robot_vels))
        
        # Plot X and Y velocities
        ax.plot(time_steps, robot_vels[:, 0], 'b-', label='Robot Vx', alpha=0.7)
        ax.plot(time_steps, robot_vels[:, 1], 'g-', label='Robot Vy', alpha=0.7)
        
        if len(cmd_vels) == len(robot_vels) and cmd_vels.shape[1] >= 2:
            ax.plot(time_steps, cmd_vels[:, 0], 'b--', label='Cmd Vx', alpha=0.5)
            ax.plot(time_steps, cmd_vels[:, 1], 'g--', label='Cmd Vy', alpha=0.5)
        
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Time Steps')
        ax.set_ylabel('Velocity (m/s)')
        
    def _plot_performance_metrics(self):
        """Plot performance metrics."""
        ax = self.subplot_info['metrics']['ax']
        ax.clear()
        ax.set_title('Performance Metrics')
        
        metrics = self.perf_metrics
        
        # Create text summary
        text_lines = []
        
        if len(metrics['inference_times']) > 0:
            avg_time = np.mean(list(metrics['inference_times']))
            text_lines.append(f"Inference Time: {avg_time*1000:.1f}ms")
            
        if len(metrics['action_magnitudes']) > 0:
            avg_action = np.mean(list(metrics['action_magnitudes']))
            text_lines.append(f"Action Magnitude: {avg_action:.3f}")
            
        if len(metrics['velocity_tracking']) > 0:
            avg_vel_error = np.mean(list(metrics['velocity_tracking']))
            text_lines.append(f"Vel Tracking Error: {avg_vel_error:.3f}m/s")
            
        text_lines.append(f"Steps: {metrics['step_count']}")
        text_lines.append(f"Episodes: {metrics['episode_count']}")
        
        # Display text
        for i, line in enumerate(text_lines):
            ax.text(0.05, 0.9 - i*0.15, line, transform=ax.transAxes, fontsize=10)
            
        # Simple performance plots
        if len(metrics['velocity_tracking']) > 10:
            vel_errors = list(metrics['velocity_tracking'])
            ax.plot(vel_errors[-30:], alpha=0.7, label='Vel Error')
            ax.legend()
            
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
    def _plot_episode_progress(self):
        """Plot episode progress and rewards."""
        ax = self.subplot_info['episode']['ax']
        ax.clear()
        ax.set_title('Episode Progress')
        
        if len(self.trajectory_data['rewards']) < 2:
            return
            
        rewards = list(self.trajectory_data['rewards'])
        
        # Plot reward history
        ax.plot(rewards[-100:], alpha=0.7, label='Rewards')
        
        # Plot cumulative reward
        cumulative = np.cumsum(rewards[-100:])
        ax2 = ax.twinx()
        ax2.plot(cumulative, 'r--', alpha=0.5, label='Cumulative')
        
        ax.set_xlabel('Steps')
        ax.set_ylabel('Reward')
        ax2.set_ylabel('Cumulative Reward')
        ax.legend(loc='upper left')
        ax2.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
    def _print_diagnostics(self, step_idx: int):
        """Print diagnostic information."""
        print(f"\n--- CLoC Analysis Step {step_idx} ---")
        
        if len(self.trajectory_data['observations']) > 0:
            current_obs = self.trajectory_data['observations'][-1]
            
            # Root position and velocity
            if len(current_obs) >= 186:
                root_pos = current_obs[180:183]
                root_vel = current_obs[183:186]
                print(f"Root Position: [{root_pos[0]:.2f}, {root_pos[1]:.2f}, {root_pos[2]:.2f}]")
                print(f"Root Velocity: [{root_vel[0]:.2f}, {root_vel[1]:.2f}, {root_vel[2]:.2f}]")
                
        if len(self.trajectory_data['actions_executed']) > 0:
            current_action = self.trajectory_data['actions_executed'][-1]
            action_norm = np.linalg.norm(current_action)
            print(f"Action Magnitude: {action_norm:.3f}")
            
        # Performance summary
        if len(self.perf_metrics['inference_times']) > 0:
            avg_time = np.mean(list(self.perf_metrics['inference_times']))
            print(f"Avg Inference Time: {avg_time*1000:.1f}ms")
            
        if len(self.perf_metrics['velocity_tracking']) > 0:
            avg_error = np.mean(list(self.perf_metrics['velocity_tracking']))
            print(f"Avg Velocity Error: {avg_error:.3f}m/s")
            
    def episode_reset(self):
        """Called when episode resets."""
        self.perf_metrics['episode_count'] += 1
        print(f"\n=== Episode {self.perf_metrics['episode_count']} Reset ===")
        
        # Optionally save episode data
        if self.save_plots:
            self._save_episode_summary()
            
    def _save_episode_summary(self):
        """Save episode summary plots."""
        if not hasattr(self, 'fig'):
            return
            
        import os
        os.makedirs(self.output_dir, exist_ok=True)
        
        filename = f"episode_{self.perf_metrics['episode_count']:03d}_analysis.png"
        filepath = os.path.join(self.output_dir, filename)
        
        self.fig.savefig(filepath, dpi=150, bbox_inches='tight')
        print(f"Saved analysis plot: {filepath}")
        
    def get_diagnostic_summary(self) -> Dict[str, Any]:
        """Get comprehensive diagnostic summary."""
        summary = {
            'total_steps': self.perf_metrics['step_count'],
            'total_episodes': self.perf_metrics['episode_count']
        }
        
        if len(self.perf_metrics['inference_times']) > 0:
            times = list(self.perf_metrics['inference_times'])
            summary['inference_time'] = {
                'mean': float(np.mean(times)),
                'std': float(np.std(times)),
                'max': float(np.max(times))
            }
            
        if len(self.perf_metrics['action_magnitudes']) > 0:
            actions = list(self.perf_metrics['action_magnitudes'])
            summary['action_magnitude'] = {
                'mean': float(np.mean(actions)),
                'std': float(np.std(actions)),
                'max': float(np.max(actions))
            }
            
        if len(self.perf_metrics['velocity_tracking']) > 0:
            vel_errors = list(self.perf_metrics['velocity_tracking'])
            summary['velocity_tracking_error'] = {
                'mean': float(np.mean(vel_errors)),
                'std': float(np.std(vel_errors)),
                'max': float(np.max(vel_errors))
            }
            
        return summary
        
    def close(self):
        """Clean up visualization."""
        plt.ioff()
        if hasattr(self, 'fig'):
            plt.close(self.fig)


# Training Problem Diagnosis Functions

def diagnose_training_issues(analyzer: CLoCAnalyzer) -> Dict[str, str]:
    """
    Analyze common training issues based on collected data.
    
    Returns:
        Dictionary of detected issues and recommendations
    """
    issues = {}
    
    # Get diagnostic summary
    summary = analyzer.get_diagnostic_summary()
    
    # Check inference speed
    if 'inference_time' in summary:
        avg_time = summary['inference_time']['mean']
        if avg_time > 0.1:  # > 100ms
            issues['slow_inference'] = (
                f"Inference time is {avg_time*1000:.1f}ms. "
                "Consider reducing model size or using GPU acceleration."
            )
    
    # Check action magnitude
    if 'action_magnitude' in summary:
        avg_action = summary['action_magnitude']['mean']
        if avg_action < 0.01:
            issues['weak_actions'] = (
                f"Action magnitude is very low ({avg_action:.4f}). "
                "Robot may not be moving due to weak policy outputs. "
                "Check action scaling and training convergence."
            )
        elif avg_action > 5.0:
            issues['excessive_actions'] = (
                f"Action magnitude is very high ({avg_action:.2f}). "
                "May cause instability or unrealistic movements."
            )
    
    # Check velocity tracking
    if 'velocity_tracking_error' in summary:
        avg_error = summary['velocity_tracking_error']['mean']
        if avg_error > 0.5:
            issues['poor_tracking'] = (
                f"Velocity tracking error is high ({avg_error:.2f}m/s). "
                "Robot is not following commands properly. "
                "Check policy training and normalization."
            )
    
    return issues


def print_training_recommendations():
    """Print comprehensive recommendations for training issues."""
    
    recommendations = """
    
    =================================================================
    TRAINING ISSUE DIAGNOSIS & SOLUTIONS
    =================================================================
    
    COMMON PROBLEMS & SOLUTIONS:
    
    1. ROBOT NOT MOVING (Action magnitude < 0.01):
       - Check action normalization: actions should be in reasonable range
       - Verify learning rate: try increasing to 2e-4 or 5e-4
       - Check gradient flow: ensure no vanishing gradients
       - Examine loss convergence: action loss should decrease
       - Try reducing denoising steps from 20 to 10 for faster convergence
       
    2. ROBOT MOVING SLOWLY:
       - Check action scaling in environment
       - Verify PD controller gains are appropriate
       - Check if actions are being clipped too aggressively
       - Examine temporal action weighting in loss function
       - Try emphasizing earlier action predictions more
       
    3. POOR VELOCITY TRACKING:
       - Check command velocity scaling and normalization
       - Verify root velocity features are correctly extracted
       - Increase weight on velocity-related losses
       - Check character frame normalization
       - Try longer observation history (n_obs_steps > 4)
       
    4. TRAINING INSTABILITY:
       - Reduce learning rate to 5e-5
       - Increase EMA decay to 0.9995
       - Use gradient clipping (max_norm=1.0)
       - Check for NaN values in loss
       - Try reducing model size (n_emb=128, n_layer=1)
       
    5. SLOW CONVERGENCE:
       - Increase batch size if possible
       - Use learning rate warmup (10k steps)
       - Check data quality and diversity
       - Try curriculum learning (simple to complex)
       - Reduce denoising steps to 10-15
    
    CONFIGURATION ADJUSTMENTS:
    
    # For non-moving robot:
    policy.actor.denoising_steps: 10
    optimizer.learning_rate: 0.0002
    training.gradient_accumulate_every: 2
    
    # For slow robot:
    policy.actor.action_weight_schedule: "constant-to-4"  # Reduce from 8
    policy.actor.clean_past_action: true  # Keep more action history
    
    # For poor tracking:
    policy.actor.n_past_steps: 6  # Increase observation history
    policy.actor.state_emphasis: "random_emph_symm"  # Emphasize global states
    
    DEBUGGING STEPS:
    
    1. Check action statistics in dataset vs predictions
    2. Verify normalization is applied correctly
    3. Monitor gradient norms during training
    4. Compare policy outputs with expert demonstrations
    5. Test with smaller model first (proof of concept)
    
    =================================================================
    """
    
    print(recommendations)