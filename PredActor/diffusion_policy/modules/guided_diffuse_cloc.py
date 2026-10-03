"""
Guided Diffuse-CLoC

Extends DiffuseCLoC with classifier guidance for conditional generation during inference.
Enables task-specific control (e.g., path following, joystick steering) without retraining.

The key modification is in the sampling equation:
    τ^(k-1) = α_k(τ^k - γ_k ε_θ(τ^k, O, k) - λ·∇_τ G(τ) + N(0, σ_k^2 I))
    
The gradient term -∇_τ G(τ) guides generation toward minimizing the cost function G(τ).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Union

import torch
import numpy as np

from diffusion_policy.modules.diffuse_cloc import DiffuseCLoC
from diffusion_policy.modules.classifier_guidance import (
    ClassifierGuidance,
    MultiGuidance,
    JoyStickSteeringGuidance,
    RootPathFollowingGuidance,
)
from diffusion_policy.utils.joy_teleop import JoyStick, GUIJoyStick


class GuidedDiffuseCLoC(DiffuseCLoC):
    """
    DiffuseCLoC with classifier guidance for conditional generation.
    
    Supports multiple guidance methods that can be combined:
    - JoyStickSteeringGuidance: Real-time gamepad control
    - RootPathFollowingGuidance: Follow predefined paths
    - Custom TaskSpaceGuidance: User-defined cost functions
    
    Args:
        guidance: Single guidance or list of (guidance, weight) tuples
        apply_guidance_after_step: Start applying guidance after this many steps (default: 0)
        guidance_annealing: Anneal guidance scale during sampling (default: 'none')
        **kwargs: Arguments passed to DiffuseCLoC
    
    Example:
        # Create joystick steering guidance
        joystick_guide = JoyStickSteeringGuidance(
            target_velocity=torch.tensor([1.0, 0.0, 0.0]),
            target_angular_velocity=torch.tensor([0.0, 0.0, 0.5]),
            target_height=0.9,
            guidance_scale=10.0,
        )
        
        # Create guided policy
        policy = GuidedDiffuseCLoC(
            guidance=joystick_guide,
            **diffuse_cloc_config
        )
        
        # Generate actions with guidance
        action_traj, state_traj = policy.act(observations)
    """
    
    def __init__(
        self,
        guidance: Optional[Union[ClassifierGuidance, List[tuple]]] = None,
        apply_guidance_after_step: int = 0,
        guidance_annealing: str = 'none',  # 'none', 'linear', 'quadratic'
        enable_joystick: bool = False,
        joystick_device: str = '/dev/input/js0',
        **kwargs
    ):
        super().__init__(**kwargs)
        
        # Setup guidance
        if guidance is None:
            self.guidance = None
        elif isinstance(guidance, list):
            # Multiple guidances with weights
            self.guidance = MultiGuidance(guidance, device=self.device)
        elif isinstance(guidance, ClassifierGuidance):
            self.guidance = guidance
        else:
            raise ValueError(f"Invalid guidance type: {type(guidance)}")
            
        self.apply_guidance_after_step = apply_guidance_after_step
        self.guidance_annealing = guidance_annealing
        
        # Setup joystick for teleoperation; fall back to GUI sliders if hw fails.
        self.enable_joystick = enable_joystick
        self.joystick = None
        if enable_joystick:
            try:
                hw = JoyStick(device=joystick_device, joystick_type='xbox',
                              max_linear_vel=1.5,
                              max_angular_vel=1.0,
                              min_height=0.4,
                              max_height=1.4,
                              deadzone=0.05)
                hw.start()
                if hw.is_connected():
                    self.joystick = hw
                    print("[GuidedDiffuseCLoC] Hardware joystick enabled.")
                else:
                    hw.stop()
                    raise RuntimeError("joystick device opened but not running")
            except Exception as e:
                print(f"[GuidedDiffuseCLoC] Hardware joystick unavailable ({e}); "
                      "falling back to GUI joystick.")
                gui = GUIJoyStick(max_linear_vel=1.5, max_angular_vel=1.0,
                                  min_height=0.4, max_height=1.4)
                gui.start()
                self.joystick = gui
        
    def act(
        self,
        nobs,
        guidance: Optional[ClassifierGuidance] = None,
        **kwargs,
    ):
        """
        Generate actions with classifier guidance.
        
        Args:
            nobs: (B, n_past, Do) - Past observations
            guidance: Optional guidance to override self.guidance
            **kwargs: Additional arguments (may contain guidance targets)
            
        Returns:
            action_traj: (B, H, Da) - Predicted actions
            state_traj: (B, H, Do) - Predicted states
        """
        # Use provided guidance or instance guidance
        active_guidance = guidance if guidance is not None else self.guidance
        
        # If no guidance, fall back to standard DiffuseCLoC
        if active_guidance is None:
            return super().act(nobs, **kwargs)
            
        # Store guidance for use in diffuse_step
        self._active_guidance = active_guidance
        self._guidance_kwargs = kwargs
        
        # Call parent act which will use our overridden diffuse_step
        action_traj, state_traj = super().act(nobs, **kwargs)
        
        # Clean up
        self._active_guidance = None
        self._guidance_kwargs = None
        
        return action_traj, state_traj
    
    def diffuse_step(
        self,
        nobs,
        action_traj,
        state_traj,
        action_t,
        state_t,
        i,
        **kwargs,
    ):
        """
        Single diffusion step with classifier guidance.
        
        Overrides parent method to include guidance gradient in the update:
            τ^(k-1) = α_k(τ^k - γ_k ε_θ(τ^k, O, k) - λ·∇_τ G(τ) + N(0, σ_k^2 I))
        
        Args:
            nobs: (B, n_past, Do) - Clean past observations
            action_traj: (B, H, Da) - Current noisy actions
            state_traj: (B, H, Do) - Current noisy states
            action_t: (H,) - Action noise levels
            state_t: (H,) - State noise levels
            i: int - Current denoising iteration
            **kwargs: Additional parameters
            
        Returns:
            action_traj: (B, H, Da) - Denoised actions with guidance
            state_traj: (B, H, Do) - Denoised states with guidance
        """
        # Standard diffusion step (without guidance)
        action_traj_pred, state_traj_pred = super().diffuse_step(
            nobs=nobs,
            action_traj=action_traj,
            state_traj=state_traj,
            action_t=action_t,
            state_t=state_t,
            i=i,
            **kwargs,
        )
        
        # Apply guidance if enabled and after warmup steps
        if hasattr(self, '_active_guidance') and self._active_guidance is not None and self._active_guidance.guidance_scale > 0.0:
            if i >= self.apply_guidance_after_step:
                # Compute guidance scale with optional annealing
                current_scale = self._get_annealed_scale(i, action_t.max().item())
                
                # Temporarily modify guidance scale
                original_scale = self._active_guidance.guidance_scale
                self._active_guidance.guidance_scale = current_scale
                
                try:
                    # Unnormalize predictions to real-world units for guidance computation
                    # Guidance cost functions expect unnormalized data (e.g., velocity in m/s)
                    state_traj_unnorm = self.normalizer['obs'].unnormalize((state_traj_pred @ self.emphasis_mat_inv).detach())
                    action_traj_unnorm = self.normalizer['action'].unnormalize(action_traj_pred.detach())
                    
                    # Enable gradients for guidance computation
                    state_traj_unnorm = state_traj_unnorm.requires_grad_(True)
                    action_traj_unnorm = action_traj_unnorm.requires_grad_(True)
                    
                    # Compute guidance gradients in unnormalized space
                    guidance_kwargs = self._guidance_kwargs if self._guidance_kwargs is not None else {}
                    state_grad_unnorm, action_grad_unnorm = self._active_guidance(
                        state_traj_unnorm,
                        action_traj_unnorm,
                        **guidance_kwargs
                    )
                    
                    # Normalize gradients (without offset) to match normalized space
                    # Gradients are directional changes, so only scale applies
                    state_grad = self.normalizer['obs'].normalize(state_grad_unnorm.detach(), grad=True)
                    action_grad = self.normalizer['action'].normalize(action_grad_unnorm.detach(), grad=True)
                    
                    # Apply guidance: subtract gradient (gradient descent on cost)
                    # Note: state_traj might be in emphasized space, but guidance
                    # works on emphasized space too since it's just a linear transform
                    state_grad = state_grad @ self.emphasis_mat  # Apply emphasis scaling
                    state_traj_pred = state_traj_pred - state_grad
                    action_traj_pred = action_traj_pred - action_grad
                    
                except Exception as e:
                    print(f"Warning: Guidance computation failed at step {i}: {e}")
                    # Continue without guidance on error
                    raise e
                finally:
                    # Restore original scale
                    self._active_guidance.guidance_scale = original_scale
        
        if self.enable_joystick:
            state_traj_unnorm = self.normalizer['obs'].unnormalize((state_traj_pred @ self.emphasis_mat_inv).detach())
            
            n_plan_start = self.n_past_steps
            # n_plan_start = 0
            # horizon_weight = torch.tensor([0.0]*n_plan_start + [1.0]*(state_traj_unnorm.shape[1]-n_plan_start), device=state_traj_unnorm.device)
            horizon_weight = torch.tensor([0.0]*4 + [0.2, 0.4, 0.6, 0.8] + [1.0]*12, device=state_traj_unnorm.device)

            # Get command from joystick or use default values
            if self.joystick is not None and self.joystick.is_running():
                # Read velocity command from joystick
                vx, vy, wz, height = self.joystick.get_cmd_vel()
                # Set kp and dt for joystick mode
                kp = 1.0
                dt = 0.04
                vx *= 8.0  # Scale factor for velocity
                vy *= 3.0
                wz *= 3.0
                # Optionally print command for debugging
                if i == 0:  # Print only at first diffusion step to avoid spam
                    print(f"Joy: vx={vx:5.2f} vy={vy:5.2f} wz={wz:5.2f} h={height:4.2f}")
            else:
                # Default stand-still commands (joystick connected but not active yet)
                # # Walk in +X direction
                # kp = 1.0
                # dt = 0.05
                # vx = 10.0
                # vy = 0.0
                # wz = 3.0  # BUG:there is model bias
                # height = 0.9

                # # Stance
                # kp = 1.0
                # dt = 0.02
                # vx = 0.0
                # vy = 0.0
                # wz = 0.0 
                # height = 0.9

                # Kneel down (comment out PosXY, Rot, AngVel)
                kp = 0.4
                dt = 0.02
                vx = 0.0
                vy = 0.0
                wz = 0.0 
                height = 0.4

            # Pos
            state_traj_unnorm[:, n_plan_start:, 180] = torch.linspace(0, vx*dt*(state_traj_unnorm.shape[1]-n_plan_start), 
                                                                      state_traj_unnorm.shape[1]-n_plan_start) - vx*dt*(self.n_past_steps-n_plan_start)
            state_traj_unnorm[:, n_plan_start:, 181] = torch.linspace(0, vy*dt*(state_traj_unnorm.shape[1]-n_plan_start), 
                                                                      state_traj_unnorm.shape[1]-n_plan_start) - vy*dt*(self.n_past_steps-n_plan_start)
            state_traj_unnorm[:, n_plan_start:, 182] = height
            # Rot
            state_traj_unnorm[:, n_plan_start:, 183:186] = 0.0
            # Vel
            state_traj_unnorm[:, n_plan_start:, 186] = vx
            state_traj_unnorm[:, n_plan_start:, 187] = vy
            state_traj_unnorm[:, n_plan_start:, 188] = 0.0
            # Ang Vel
            state_traj_unnorm[:, n_plan_start:, 189:191] = 0.0
            state_traj_unnorm[:, n_plan_start:, 191] = wz

            state_exp = self.normalizer['obs'].normalize((state_traj_unnorm).detach()) @ self.emphasis_mat
            err = state_exp - state_traj_pred
            state_traj_pred += kp * (err) * horizon_weight[None, :, None]
            # state_traj_pred += kp * (err)
            # print(f"err mean: {err.abs().mean().item():.4f}, err max: {err.abs().max().item():.4f}, err min: {err.abs().min().item():.4f}, err std: {err.abs().std().item():.4f}")


        return action_traj_pred, state_traj_pred
    
    def _get_annealed_scale(self, current_step: int, max_timestep: int) -> float:
        """
        Compute annealed guidance scale based on denoising progress.
        
        Annealing strategies:
        - 'none': Constant scale throughout sampling
        - 'linear': Linear decrease from initial scale to 0
        - 'quadratic': Quadratic decrease (faster decay early on)
        
        Args:
            current_step: Current iteration index
            max_timestep: Maximum noise level (typically denoising_steps - 1)
            
        Returns:
            scale: Annealed guidance scale
        """
        if self._active_guidance is None:
            return 1.0
            
        if self.guidance_annealing == 'none':
            return self._active_guidance.guidance_scale
            
        # Compute progress: 0 (start) -> 1 (end)
        progress = current_step / max(max_timestep, 1)
        
        if self.guidance_annealing == 'linear':
            # Linear annealing: scale * (1 - progress)
            factor = 1.0 - progress
        elif self.guidance_annealing == 'quadratic':
            # Quadratic annealing: scale * (1 - progress)^2
            factor = (1.0 - progress) ** 2
        else:
            factor = 1.0
            
        return self._active_guidance.guidance_scale * factor
    
    def set_guidance(self, guidance: Optional[ClassifierGuidance]):
        """
        Update the guidance method at runtime.
        
        Useful for switching between different control modes during inference.
        
        Args:
            guidance: New guidance instance or None to disable
        """
        self.guidance = guidance
        
    def add_guidance(self, guidance: ClassifierGuidance, weight: float = 1.0):
        """
        Add a guidance method to existing guidance.
        
        If current guidance is None, sets it as the new guidance.
        If current guidance exists, converts to MultiGuidance.
        
        Args:
            guidance: Guidance instance to add
            weight: Weight for the new guidance
        """
        if self.guidance is None:
            self.guidance = guidance
        elif isinstance(self.guidance, MultiGuidance):
            self.guidance.add_guidance(guidance, weight)
        else:
            # Convert single guidance to MultiGuidance
            self.guidance = MultiGuidance(
                [(self.guidance, 1.0), (guidance, weight)],
                device=self.device
            )
    
    def __del__(self):
        """Cleanup: stop joystick when object is destroyed."""
        if hasattr(self, 'joystick') and self.joystick is not None:
            self.joystick.stop()


def create_joystick_guided_policy(
    base_policy_config: dict,
    target_velocity: Optional[torch.Tensor] = None,
    target_angular_velocity: Optional[torch.Tensor] = None,
    target_height: Optional[float] = None,
    guidance_scale: float = 10.0,
    velocity_weight: float = 1.0,
    angular_weight: float = 1.0,
    height_weight: float = 1.0,
    device: str = "cuda:0",
) -> GuidedDiffuseCLoC:
    """
    Factory function to create a joystick-guided policy.
    
    Args:
        base_policy_config: DiffuseCLoC configuration dict
        target_velocity: Desired velocity [vx, vy, vz]
        target_angular_velocity: Desired angular velocity [ωx, ωy, ωz]
        target_height: Desired root height
        guidance_scale: Overall guidance strength (higher = stronger guidance)
        velocity_weight: Relative weight for velocity tracking
        angular_weight: Relative weight for angular velocity tracking
        height_weight: Relative weight for height tracking
        device: Torch device
        
    Returns:
        policy: GuidedDiffuseCLoC with joystick steering
        
    Example:
        config = {...}  # DiffuseCLoC config
        policy = create_joystick_guided_policy(
            config,
            target_velocity=torch.tensor([1.0, 0.0, 0.0]),  # Move forward at 1 m/s
            target_angular_velocity=torch.tensor([0.0, 0.0, 0.3]),  # Turn left
            target_height=0.9,
            guidance_scale=10.0,
        )
    """
    # Create joystick guidance
    joystick_guidance = JoyStickSteeringGuidance(
        target_velocity=target_velocity,
        target_angular_velocity=target_angular_velocity,
        target_height=target_height,
        velocity_weight=velocity_weight,
        angular_weight=angular_weight,
        height_weight=height_weight,
        guidance_scale=guidance_scale,
        device=device,
    )
    
    # Create guided policy
    policy = GuidedDiffuseCLoC(
        guidance=joystick_guidance,
        **base_policy_config
    )
    
    return policy


def create_path_following_policy(
    base_policy_config: dict,
    path: torch.Tensor,
    guidance_scale: float = 10.0,
    start_offset: int = 0,
    device: str = "cuda:0",
) -> GuidedDiffuseCLoC:
    """
    Factory function to create a path-following policy.
    
    Args:
        base_policy_config: DiffuseCLoC configuration dict
        path: (T, 3) - Desired root positions [x, y, z] at each timestep
        guidance_scale: Guidance strength
        start_offset: Timestep offset for path indexing
        device: Torch device
        
    Returns:
        policy: GuidedDiffuseCLoC with path following
        
    Example:
        # Create S-shaped path
        t = torch.linspace(0, 4*np.pi, 100)
        path = torch.stack([
            t / 10,  # x: linear progression
            torch.sin(t),  # y: sinusoidal
            torch.ones_like(t) * 0.9,  # z: constant height
        ], dim=-1)
        
        policy = create_path_following_policy(config, path, guidance_scale=10.0)
    """
    # Create path following guidance
    path_guidance = RootPathFollowingGuidance(
        path=path,
        start_offset=start_offset,
        guidance_scale=guidance_scale,
        device=device,
    )
    
    # Create guided policy
    policy = GuidedDiffuseCLoC(
        guidance=path_guidance,
        **base_policy_config
    )
    
    return policy
