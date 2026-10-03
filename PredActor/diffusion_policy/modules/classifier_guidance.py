"""
Classifier Guidance for Diffuse-CLoC

Implements classifier guidance to enable conditional generation during inference
without retraining. Uses the gradient of cost functions to guide the diffusion
process toward desired behaviors.

Mathematical Foundation:
    The conditional score function is decomposed as:
    ∇_τ log p(τ | τ*) = ∇_τ log p(τ) + ∇_τ log p(τ* | τ)
    
    Where the conditional probability is: p(τ* | τ) ∝ exp(-G(τ))
    Leading to: ∇_τ log p(τ* | τ) = -∇_τ G(τ)

Sampling Equation:
    τ^(k-1) = α_k(τ^k - γ_k ε_θ(τ^k, O, k) - λ·∇_τ G(τ) + N(0, σ_k^2 I))
    
    where λ is the guidance scale controlling the strength of guidance.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Callable
from abc import ABC, abstractmethod

import torch
import torch.nn as nn
import numpy as np


class ClassifierGuidance(ABC):
    """
    Base class for classifier guidance methods.
    
    Encapsulates the logic for computing gradients of cost functions with respect
    to the trajectory. Supports multiple guidance strategies that can be combined
    during inference.
    
    Args:
        guidance_scale: Scaling factor λ for the gradient (default: 1.0)
        device: Torch device for computation
    """
    
    def __init__(
        self,
        guidance_scale: float = 1.0,
        device: str = "cuda:0",
    ):
        self.guidance_scale = guidance_scale
        self.device = device
        
    @abstractmethod
    def compute_cost(
        self,
        state_traj: torch.Tensor,
        action_traj: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        """
        Compute the cost function G(τ) for the given trajectory.
        
        Args:
            state_traj: (B, H, Do) - State trajectory
            action_traj: (B, H, Da) - Action trajectory
            **kwargs: Additional parameters (e.g., targets, timesteps)
            
        Returns:
            cost: (B,) - Scalar cost for each batch element
        """
        pass
    
    def compute_gradient(
        self,
        state_traj: torch.Tensor,
        action_traj: torch.Tensor,
        **kwargs
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute the gradient ∇_τ G(τ) using autograd.
        
        Args:
            state_traj: (B, H, Do) - State trajectory (requires_grad=True)
            action_traj: (B, H, Da) - Action trajectory (requires_grad=True)
            **kwargs: Additional parameters for cost computation
            
        Returns:
            state_grad: (B, H, Do) - Gradient w.r.t. states
            action_grad: (B, H, Da) - Gradient w.r.t. actions
        """
        # CRITICAL: Enable gradients even if in no_grad() context (e.g., during eval)
        # This is necessary because guidance needs gradients even during inference
        with torch.enable_grad():
            # Ensure gradients are enabled
            if not state_traj.requires_grad:
                state_traj = state_traj.detach().requires_grad_(True)
            if not action_traj.requires_grad:
                action_traj = action_traj.detach().requires_grad_(True)
                
            # Compute cost (with gradient tracking enabled)
            cost = self.compute_cost(state_traj, action_traj, **kwargs)
            
            # Sum over batch for gradient computation
            total_cost = cost.sum()
        # Compute gradients using autograd
        # Use allow_unused=True because action_traj might not be in the graph
        state_grad = torch.autograd.grad(
            total_cost, state_traj, retain_graph=True, create_graph=False, allow_unused=True
        )[0]
        
        action_grad = torch.autograd.grad(
            total_cost, action_traj, retain_graph=False, create_graph=False, allow_unused=True
        )[0]
        
        # Handle None gradients (when tensor not used in computation)
        if state_grad is None:
            state_grad = torch.zeros_like(state_traj)
        if action_grad is None:
            action_grad = torch.zeros_like(action_traj)
        
        # Apply guidance scale
        state_grad = self.guidance_scale * state_grad
        action_grad = self.guidance_scale * action_grad
        
        return state_grad, action_grad
    
    def __call__(
        self,
        state_traj: torch.Tensor,
        action_traj: torch.Tensor,
        **kwargs
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Convenience method to compute guidance gradients.
        
        Returns:
            state_grad: (B, H, Do) - Guidance gradient for states
            action_grad: (B, H, Da) - Guidance gradient for actions
        """
        return self.compute_gradient(state_traj, action_traj, **kwargs)


class TaskSpaceGuidance(ClassifierGuidance):
    """
    Task space guidance using squared error cost.
    
    Cost Function:
        G^ts(τ) = Σ_{t'∈T} ||P_x(s_{t'}) - g_{t'}||²
        
    Where:
        - T is the set of keyframe timesteps
        - g_{t'} is the target at timestep t'
        - P_x(·) maps state to task space
    
    Gradient:
        ∇_τ G^ts(τ) = Σ_{t'∈T} 2(P_x(s_{t'}) - g_{t'}) · ∂P_x/∂s · ∂s/∂τ
    
    Args:
        projection_fn: Function P_x(s) that maps state to task space
        target_fn: Function that returns target g for given timestep
        keyframe_timesteps: List of timesteps to apply guidance (default: all)
        guidance_scale: Scaling factor for the gradient
        device: Torch device
    """
    
    def __init__(
        self,
        projection_fn: Callable[[torch.Tensor], torch.Tensor],
        target_fn: Callable[[int], Optional[torch.Tensor]],
        keyframe_timesteps: Optional[List[int]] = None,
        guidance_scale: float = 1.0,
        device: str = "cuda:0",
    ):
        super().__init__(guidance_scale=guidance_scale, device=device)
        self.projection_fn = projection_fn
        self.target_fn = target_fn
        self.keyframe_timesteps = keyframe_timesteps
        
    def compute_cost(
        self,
        state_traj: torch.Tensor,
        action_traj: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        """
        Compute task space tracking cost.
        
        Args:
            state_traj: (B, H, Do) - State trajectory
            action_traj: (B, H, Da) - Action trajectory (unused here)
            **kwargs: May contain 'targets' key with precomputed targets
            
        Returns:
            cost: (B,) - Squared error cost for each batch
        """
        B, H, Do = state_traj.shape
        
        # Determine which timesteps to evaluate
        if self.keyframe_timesteps is None:
            timesteps = range(H)
        else:
            timesteps = self.keyframe_timesteps
            
        total_cost = None
        
        for t in timesteps:
            # Project state to task space: (B, Do) -> (B, task_dim)
            task_space_state = self.projection_fn(state_traj[:, t])
            
            # Get target for this timestep
            if 'targets' in kwargs and t in kwargs['targets']:
                target = kwargs['targets'][t]
            else:
                target = self.target_fn(t)
                
            if target is not None:
                # Ensure target is on correct device and has batch dimension
                if isinstance(target, np.ndarray):
                    target = torch.from_numpy(target).to(self.device)
                if target.dim() == 1:
                    target = target.unsqueeze(0).expand(B, -1)
                    
                # Squared error: ||P_x(s) - g||²
                error = task_space_state - target
                cost_t = (error ** 2).sum(dim=-1)  # Sum over task dimensions
                total_cost = cost_t if total_cost is None else total_cost + cost_t        
        # Return zero cost if no valid costs computed
        if total_cost is None:
            total_cost = torch.zeros(B, device=self.device)                
        return total_cost


class JoyStickSteeringGuidance(TaskSpaceGuidance):
    """
    Gamepad controller steering guidance.
    
    Enables real-time character steering using gamepad inputs by guiding
    root velocity, angular velocity, and height.
    
    Task Space Components:
        - Root linear velocity (vx, vy, vz): [186:189] in G1 state
        - Root angular velocity (ωx, ωy, ωz): [189:192] in G1 state
        - Root height (z): [182] in G1 state
    
    Args:
        target_velocity: (3,) - Desired root velocity [vx, vy, vz]
        target_angular_velocity: (3,) - Desired angular velocity [ωx, ωy, ωz]
        target_height: float - Desired root height
        velocity_weight: Weight for velocity tracking (default: 1.0)
        angular_weight: Weight for angular velocity tracking (default: 1.0)
        height_weight: Weight for height tracking (default: 1.0)
        guidance_scale: Overall guidance strength
        apply_to_future_only: Only apply guidance to future timesteps (default: True)
        n_past_steps: Number of past steps to skip (default: 4)
        device: Torch device
    """
    
    def __init__(
        self,
        target_velocity: Optional[torch.Tensor] = None,
        target_angular_velocity: Optional[torch.Tensor] = None,
        target_height: Optional[float] = None,
        velocity_weight: float = 1.0,
        angular_weight: float = 1.0,
        height_weight: float = 1.0,
        guidance_scale: float = 1.0,
        apply_to_future_only: bool = True,
        n_past_steps: int = 4,
        device: str = "cuda:0",
    ):
        
        target_velocity = torch.tensor(target_velocity, device=device) if target_velocity is not None else None
        target_angular_velocity = torch.tensor(target_angular_velocity, device=device) if target_angular_velocity is not None else None

        # Define projection function for root dynamics
        def root_projection(state: torch.Tensor) -> torch.Tensor:
            """
            Extract root dynamics from G1 state.
            
            Args:
                state: (B, 384) - Full G1 state
                
            Returns:
                root_state: (B, 7) - [vel_x, vel_y, vel_z, ang_x, ang_y, ang_z, height]
            """
            B = state.shape[0]
            root_vel = state[:, 186:189]  # Linear velocity
            root_ang = state[:, 189:192]  # Angular velocity  
            root_height = state[:, 182:183]  # Z position
            return torch.cat([root_vel, root_ang, root_height], dim=-1)
        
        # Define target function
        def root_target(t: int) -> Optional[torch.Tensor]:
            """Return combined target vector."""
            targets = []
            if target_velocity is not None:
                targets.append(target_velocity * velocity_weight)
            else:
                targets.append(torch.zeros(3, device=device))
                
            if target_angular_velocity is not None:
                targets.append(target_angular_velocity * angular_weight)
            else:
                targets.append(torch.zeros(3, device=device))
                
            if target_height is not None:
                targets.append(torch.tensor([target_height * height_weight], device=device))
            else:
                targets.append(torch.zeros(1, device=device))
                
            return torch.cat(targets)
        
        # Determine keyframe timesteps
        if apply_to_future_only:
            # Only apply to future steps, not past observations
            keyframe_timesteps = None  # Will be handled in compute_cost
        else:
            keyframe_timesteps = None  # Apply to all timesteps
            
        super().__init__(
            projection_fn=root_projection,
            target_fn=root_target,
            keyframe_timesteps=keyframe_timesteps,
            guidance_scale=guidance_scale,
            device=device,
        )
        
        self.apply_to_future_only = apply_to_future_only
        self.n_past_steps = n_past_steps
        self.velocity_weight = velocity_weight
        self.angular_weight = angular_weight
        self.height_weight = height_weight
        
    def compute_cost(
        self,
        state_traj: torch.Tensor,
        action_traj: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        """
        Compute steering cost, optionally only for future timesteps.
        
        Args:
            state_traj: (B, H, Do) - State trajectory
            action_traj: (B, H, Da) - Action trajectory
            **kwargs: Additional parameters
            
        Returns:
            cost: (B,) - Steering tracking cost
        """
        B, H, Do = state_traj.shape
        
        # Determine timesteps to apply guidance
        if self.apply_to_future_only:
            start_t = self.n_past_steps
        else:
            start_t = 0
            
        total_cost = None
        
        for t in range(start_t, H):
            # Project to root dynamics
            root_state = self.projection_fn(state_traj[:, t])
            target = self.target_fn(t)
            
            if target is not None:
                if target.dim() == 1:
                    target = target.unsqueeze(0).expand(B, -1)
                    
                # Weighted squared error
                error = root_state - target
                cost_t = (error ** 2).sum(dim=-1)
                total_cost = cost_t if total_cost is None else total_cost + cost_t
        
        # Return zero cost if no valid costs computed
        if total_cost is None:
            total_cost = torch.zeros(B, device=self.device)
                
        return total_cost
    
    def update_targets(
        self,
        target_velocity: Optional[torch.Tensor] = None,
        target_angular_velocity: Optional[torch.Tensor] = None,
        target_height: Optional[float] = None,
    ):
        """
        Update steering targets in real-time (e.g., from gamepad input).
        
        Args:
            target_velocity: New desired velocity [vx, vy, vz]
            target_angular_velocity: New desired angular velocity [ωx, ωy, ωz]
            target_height: New desired height
        """
        # Rebuild target function with new values
        def root_target(t: int) -> Optional[torch.Tensor]:
            targets = []
            if target_velocity is not None:
                targets.append(target_velocity * self.velocity_weight)
            else:
                targets.append(torch.zeros(3, device=self.device))
                
            if target_angular_velocity is not None:
                targets.append(target_angular_velocity * self.angular_weight)
            else:
                targets.append(torch.zeros(3, device=self.device))
                
            if target_height is not None:
                targets.append(torch.tensor([target_height * self.height_weight], device=self.device))
            else:
                targets.append(torch.zeros(1, device=self.device))
                
            return torch.cat(targets)
        
        self.target_fn = root_target


class RootPathFollowingGuidance(TaskSpaceGuidance):
    """
    Root path following guidance.
    
    Guides the character to follow a predefined root position trajectory,
    enabling complex path following behaviors (e.g., "S" shaped paths).
    
    Task Space:
        - Root position (x, y, z): [180:183] in G1 state
    
    Args:
        path: (T, 3) - Desired root positions at each timestep
        start_offset: Timestep offset for path indexing (default: 0)
        guidance_scale: Guidance strength
        apply_to_future_only: Only guide future steps (default: True)
        n_past_steps: Number of past steps (default: 4)
        interpolate: Interpolate path for smoother following (default: True)
        device: Torch device
    """
    
    def __init__(
        self,
        path: torch.Tensor,
        start_offset: int = 0,
        guidance_scale: float = 1.0,
        apply_to_future_only: bool = True,
        n_past_steps: int = 4,
        interpolate: bool = True,
        device: str = "cuda:0",
    ):
        # Define projection function for root position
        def root_position_projection(state: torch.Tensor) -> torch.Tensor:
            """
            Extract root position from G1 state.
            
            Args:
                state: (B, 384) - Full G1 state
                
            Returns:
                root_pos: (B, 3) - Root position [x, y, z]
            """
            return state[:, 180:183]
        
        # Store path
        if isinstance(path, np.ndarray):
            path = torch.from_numpy(path).to(device)
        self.path = path.to(device)
        self.start_offset = start_offset
        self.interpolate = interpolate
        
        # Define target function that indexes into path
        def path_target(t: int) -> Optional[torch.Tensor]:
            """Return target position from path at timestep t."""
            path_idx = t + self.start_offset
            if path_idx < 0 or path_idx >= len(self.path):
                return None
            return self.path[path_idx]
        
        super().__init__(
            projection_fn=root_position_projection,
            target_fn=path_target,
            keyframe_timesteps=None,
            guidance_scale=guidance_scale,
            device=device,
        )
        
        self.apply_to_future_only = apply_to_future_only
        self.n_past_steps = n_past_steps
        
    def compute_cost(
        self,
        state_traj: torch.Tensor,
        action_traj: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        """
        Compute path following cost.
        
        Args:
            state_traj: (B, H, Do) - State trajectory
            action_traj: (B, H, Da) - Action trajectory
            **kwargs: Additional parameters
            
        Returns:
            cost: (B,) - Path following cost
        """
        B, H, Do = state_traj.shape
        
        # Determine timesteps to apply guidance
        if self.apply_to_future_only:
            start_t = self.n_past_steps
        else:
            start_t = 0
            
        total_cost = None
        
        for t in range(start_t, H):
            # Get target from path
            path_idx = t + self.start_offset
            if path_idx < 0 or path_idx >= len(self.path):
                continue
                
            # Project to root position
            root_pos = self.projection_fn(state_traj[:, t])
            target = self.path[path_idx]
            
            if target.dim() == 1:
                target = target.unsqueeze(0).expand(B, -1)
                
            # Squared error
            error = root_pos - target
            cost_t = (error ** 2).sum(dim=-1)
            total_cost = cost_t if total_cost is None else total_cost + cost_t
        
        # Return zero cost if no valid costs computed
        if total_cost is None:
            total_cost = torch.zeros(B, device=self.device)
            
        return total_cost
    
    def update_path(self, new_path: torch.Tensor, start_offset: int = 0):
        """
        Update the reference path for dynamic path changes.
        
        Args:
            new_path: (T, 3) - New path to follow
            start_offset: New timestep offset
        """
        if isinstance(new_path, np.ndarray):
            new_path = torch.from_numpy(new_path).to(self.device)
        self.path = new_path.to(self.device)
        self.start_offset = start_offset
        
        # Update target function
        def path_target(t: int) -> Optional[torch.Tensor]:
            path_idx = t + self.start_offset
            if path_idx < 0 or path_idx >= len(self.path):
                return None
            return self.path[path_idx]
        
        self.target_fn = path_target


class MultiGuidance(ClassifierGuidance):
    """
    Combines multiple guidance methods with individual weights.
    
    Total Cost:
        G_total = Σ_i λ_i G_i(τ)
    
    Args:
        guidances: List of (guidance, weight) tuples
        device: Torch device
    """
    
    def __init__(
        self,
        guidances: List[Tuple[ClassifierGuidance, float]],
        device: str = "cuda:0",
    ):
        super().__init__(guidance_scale=1.0, device=device)
        self.guidances = guidances
        
    def compute_cost(
        self,
        state_traj: torch.Tensor,
        action_traj: torch.Tensor,
        **kwargs
    ) -> torch.Tensor:
        """
        Compute combined cost from all guidance methods.
        
        Returns:
            cost: (B,) - Weighted sum of all costs
        """
        B = state_traj.shape[0]
        total_cost = None
        
        for guidance, weight in self.guidances:
            cost = guidance.compute_cost(state_traj, action_traj, **kwargs)
            weighted_cost = weight * cost
            total_cost = weighted_cost if total_cost is None else total_cost + weighted_cost
        
        # Return zero cost if no guidances or all returned None
        if total_cost is None:
            total_cost = torch.zeros(B, device=self.device)
            
        return total_cost
    
    def add_guidance(self, guidance: ClassifierGuidance, weight: float = 1.0):
        """Add a new guidance method to the combination."""
        self.guidances.append((guidance, weight))
        
    def remove_guidance(self, index: int):
        """Remove a guidance method by index."""
        self.guidances.pop(index)
