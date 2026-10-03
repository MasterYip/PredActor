from __future__ import annotations
from typing import TYPE_CHECKING

import torch
from torch.distributions.normal import Normal
import numpy as np

from diffusion_policy.modules.policy_diffusion import (
    make_timesteps,
    extract,
)
from diffusion_policy.modules.diffusion_model import SequentialDiffusionModel
from diffusion_policy.modules.base_actor import BaseActor

from diffusion_policy.backbone.base_backbone import JointSeqBackbone


class JointDiffusionActor(SequentialDiffusionModel, BaseActor):
    """
    Joint-distribution diffusion over states and actions with independent noise schedules.
    Key features:
    - Separate denoising for states (x) and actions (y)
    - Temporal and joint-specific loss weighting
    - Inpainting of past observations for autoregressive control
    """
    backbone: JointSeqBackbone
    _ROLLING_STATE_ATTRS = ("action_rolling_traj", "state_rolling_traj")

    def __init__(
        self,
        action_weight_schedule="constant",
        action_denoising_steps=0,
        state_weight_schedule="constant",
        state_denoising_steps=0,
        clean_past_state=True,
        no_state_override: bool = False,  # denoise x-stream from condition, skip nobs inpainting
        state_pred_epsilon=None,
        action_pred_epsilon=None,
        n_past_steps=8,
        state_loss_scale: float = 1.0,
        sync_timesteps: bool = False,
        **kwargs,
    ):
        SequentialDiffusionModel.__init__(self, **kwargs)
        BaseActor.__init__(self, backbone=self.backbone)
        self.backbone: JointSeqBackbone

        self.horizon = max(self.backbone.x_horizon, self.backbone.y_horizon)

        self.obs_dim = self.backbone.x_output_dim
        self.n_past_steps = n_past_steps
        self.action_dim = self.backbone.y_output_dim
        self.n_future_steps = self.horizon - self.n_past_steps


        self.action_loss_weights = self.get_loss_weights(action_weight_schedule)
        self.action_denoising_steps = (
            action_denoising_steps if action_denoising_steps > 0 else self.denoising_steps
        )
        self.state_loss_weights = self.get_loss_weights(state_weight_schedule)
        self.state_denoising_steps = (
            state_denoising_steps if state_denoising_steps > 0 else self.denoising_steps
        )
        self.clean_past_state = clean_past_state  # whether past state is clean or not
        self.no_state_override = no_state_override  # denoise x-stream from condition, skip nobs inpainting
        # Ablation controls (see test/test_codiffuse_dp_ablation/)
        self.state_loss_scale = state_loss_scale  # 0.0 → action-only loss (Factor 1 ablation)
        self.sync_timesteps = sync_timesteps       # True → same t for state & action (Factor 4 ablation)
        self.backbone_call_count = 0

        if state_pred_epsilon is None:
            self.state_pred_epsilon = self.predict_epsilon
        if action_pred_epsilon is None:
            self.action_pred_epsilon = self.predict_epsilon

    def rolling_inference_enabled(self) -> bool:
        """Whether ``act`` retains a batch-shaped trajectory between calls."""
        return False

    def clear_rolling_state(self) -> None:
        """Remove actor-local rolling state before importing another env batch."""
        for name in self._ROLLING_STATE_ATTRS:
            if hasattr(self, name):
                delattr(self, name)

    def export_rolling_state(self):
        """Copy actor-local rolling trajectories for environment-keyed storage."""
        present = [hasattr(self, name) for name in self._ROLLING_STATE_ATTRS]
        if any(present) and not all(present):
            raise RuntimeError("rolling actor has a partial trajectory cache")
        if not any(present):
            return None
        return {
            "action": self.action_rolling_traj.detach().clone(),
            "state": self.state_rolling_traj.detach().clone(),
        }

    def import_rolling_state(self, state) -> None:
        """Install one microbatch's rolling trajectories into the actor."""
        if set(state) != {"action", "state"}:
            raise ValueError("rolling state must contain exactly action and state")
        action = state["action"]
        state_traj = state["state"]
        if not torch.is_tensor(action) or not torch.is_tensor(state_traj):
            raise TypeError("rolling state action/state must be tensors")
        if action.ndim < 2 or state_traj.ndim < 2:
            raise ValueError("rolling state tensors must include batch and horizon")
        if action.shape[0] != state_traj.shape[0]:
            raise ValueError("rolling action/state batches must match")
        self.clear_rolling_state()
        self.action_rolling_traj = action.detach().clone().to(self.device)
        self.state_rolling_traj = state_traj.detach().clone().to(self.device)


    def act(
        self,
        nobs,
        past_actions=None,
        cond=None,
        **kwargs,
    ):
        """
        Generate action-state trajectory from current observations via iterative denoising.
        
        Args:
            nobs: (B, n_past_steps, obs_dim) - Past observations (e.g., (B, 4, 384))
            past_actions: (B, n_past_steps-1, action_dim) - Optional past actions
            cond: (B, T_cond, cond_dim) - Optional condition (e.g., motion latent)
            
        Returns:
            action_traj: (B, horizon, action_dim) - Predicted action sequence (B, 20, 29)
            state_traj: (B, horizon, obs_dim) - Predicted state sequence (B, 20, 384)
        """
        self.backbone_call_count = 0
        B = nobs.shape[0]
        nobs = nobs[:, :self.n_past_steps, :]
        # print(nobs[0, :, 186:189])

        action_traj = torch.randn((B, self.horizon, self.action_dim), device=self.device)
        state_traj = torch.randn((B, self.horizon, self.obs_dim), device=self.device)

        # Diffusion Loop
        t_all = torch.flip(torch.arange(self.denoising_steps), dims=(0,))
        t_all = t_all.unsqueeze(1).repeat(1, self.horizon)
        action_t_all = t_all.clone()
        state_t_all = t_all.clone()

        for i in range(max(len(action_t_all), len(state_t_all))):
            action_traj, state_traj = self.diffuse_step(
                nobs=nobs,
                action_traj=action_traj,
                state_traj=state_traj,
                action_t=action_t_all[i],
                state_t=state_t_all[i],
                i=i,
                past_actions=past_actions,
                cond=cond,
                **kwargs,
            )

        return action_traj, state_traj

    def diffuse_step(
        self,
        nobs,
        action_traj,
        state_traj,
        action_t,
        state_t,
        i,
        past_actions=None,
        cond=None,
        **kwargs,
    ):
        """
        Single reverse diffusion step for joint state-action denoising.
        Inpaints past observations to maintain autoregressive consistency.
        
        Args:
            nobs: (B, n_past, Do) - Clean past observations
            action_traj: (B, H, Da) - Current noisy actions (e.g., (B, 20, 29))
            state_traj: (B, H, Do) - Current noisy states (e.g., (B, 20, 384))
            action_t: (H,) - Action noise levels per position
            state_t: (H,) - State noise levels per position
            i: int - Iteration index
            cond: (B, T_cond, cond_dim) - Optional condition
            
        Returns:
            action_traj: (B, H, Da) - Denoised actions
            state_traj: (B, H, Do) - Denoised states
        """
        device = self.device
        B, _, Do = nobs.shape

        # inpainting observation — skip when state is denoised from condition
        if not self.no_state_override:
            state_traj[:, : self.n_past_steps] = nobs
            state_t[: self.n_past_steps] = 0

        # if past_actions is not None:
        #     action_traj[:, :self.n_past_steps-1] = past_actions
        #     action_t[:self.n_past_steps-1] = 0

        action_t_b = make_timesteps(B, action_t, device)
        state_t_b = make_timesteps(B, state_t, device)

        index_b = make_timesteps(B, i, device)

        action_mu, state_mu, action_logvar, state_logvar = self.p_mean_var(
            action_traj=action_traj,
            state_traj=state_traj,
            action_t=action_t_b,
            state_t=state_t_b,
            index=index_b,
            cond=cond,
        )

        action_std = torch.exp(0.5 * action_logvar)
        state_std = torch.exp(0.5 * state_logvar)

        # no noise when t == 0
        noise = self.inference_noise(action_traj.shape, action_traj.device, action_traj.dtype)
        noise[action_t_b == 0] = 0

        action_traj = action_mu + action_std * noise

        noise = self.inference_noise(state_traj.shape, state_traj.device, state_traj.dtype)
        noise[state_t_b == 0] = 0

        state_traj = state_mu + state_std * noise

        self.distribution = Normal(action_mu, action_std)

        return action_traj, state_traj

    # ------------------------------------------------------------------
    # DDIM initialisation & step helpers
    # ------------------------------------------------------------------

    def inference_noise(self, shape, device, dtype=torch.float32):
        """Optional independent streams keep paired noise invariant to vector width."""
        generators = getattr(self, "inference_generators", None)
        if generators is None:
            return torch.randn(shape, device=device, dtype=dtype)
        if len(generators) != shape[0]:
            raise ValueError("one inference generator is required per batch row")
        return torch.cat([
            torch.randn((1, *shape[1:]), device=device, dtype=dtype, generator=generator)
            for generator in generators
        ], dim=0)

    def DDPM_init(self):
        """Extend SequentialDiffusionModel.DDPM_init to also build NoiseSchedulers.

        Two schedulers are created so that the [DEBUG] use_ns_ddim path can call
        NoiseScheduler.ddim_step for cross-validation against joint_ddim_step:
          action_noise_scheduler — n_past_steps=0  (actions have no inpainted region)
          state_noise_scheduler  — n_past_steps=n_past_steps (past obs are inpainted)
        These are only used when use_ns_ddim=True.
        """
        super().DDPM_init()
        from diffusion_policy.utils.noise_scheduler import NoiseScheduler
        self.action_noise_scheduler = NoiseScheduler(
            denoising_steps=self.denoising_steps,
            horizon=self.horizon,
            n_past_steps=0,
            alphas_cumprod=self.alphas_cumprod,
        )
        self.state_noise_scheduler = NoiseScheduler(
            denoising_steps=self.denoising_steps,
            horizon=self.horizon,
            n_past_steps=0 if self.no_state_override else self.n_past_steps,
            alphas_cumprod=self.alphas_cumprod,
        )

    def joint_ddim_step(
        self,
        action_traj,
        state_traj,
        nobs,
        a_t_cur,
        a_t_prev,
        s_t_cur,
        s_t_prev,
        eta=0.0,
        cond=None,
        **kwargs,
    ):
        """Single DDIM reverse step for joint action + state denoising.

        Uses scalar int timestep indices (same level for all horizon positions),
        matching SequentialDiffusionModel.ddim_step's approach.

        Past state positions are inpainted from nobs before the backbone forward
        and restored afterwards.

        Args:
            action_traj: (B, H, Da)
            state_traj:  (B, H, Ds)
            nobs:        (B, n_past, Ds) — clean observations (emphasis-projected).
            a_t_cur:     int — current action timestep index into alphas_cumprod.
            a_t_prev:    int — target action timestep (-1 → clean, acp_prev=1.0).
            s_t_cur:     int — current state timestep index.
            s_t_prev:    int — target state timestep (-1 → clean, acp_prev=1.0).
            eta:         float — 0=deterministic DDIM, 1≈DDPM.
            cond:        optional conditioning tensor.
        Returns:
            action_traj: (B, H, Da)
            state_traj:  (B, H, Ds)
        """
        B = action_traj.shape[0]
        device = self.device

        # Inpaint past positions in state
        state_traj = state_traj.clone()
        if not self.no_state_override:
            state_traj[:, :self.n_past_steps] = nobs

        # Build (B, H) timestep tensors
        a_t_b = torch.full((B, self.horizon), a_t_cur, device=device, dtype=torch.long)
        s_t_b = torch.full((B, self.horizon), s_t_cur, device=device, dtype=torch.long)
        s_t_b[:, :self.n_past_steps] = 0  # inpainted positions are "clean"

        # Predict x0 for both streams in one backbone forward
        action_pred, state_pred = self.predict_x0(
            action_traj, state_traj, a_t_b, s_t_b, cond=cond, **kwargs
        )

        return self.joint_ddim_step_from_predictions(
            action_traj, state_traj, nobs, a_t_cur, a_t_prev,
            s_t_cur, s_t_prev, action_pred, state_pred, eta)

    def joint_ddim_step_from_predictions(
        self, action_traj, state_traj, nobs, a_t_cur, a_t_prev,
        s_t_cur, s_t_prev, action_pred, state_pred, eta=0.0,
    ):
        """Apply scalar DDIM math to clean predictions computed by one NFE."""
        device = self.device
        if self.denoised_clip_value is not None:
            action_pred = action_pred.clamp(
                -self.denoised_clip_value, self.denoised_clip_value)
            state_pred = state_pred.clamp(
                -self.denoised_clip_value, self.denoised_clip_value)

        # Schedule, WBG and sampler boundaries stay FP32 under autocast.
        def _step(x_t, x0, t_cur_idx, t_prev_idx):
            x_t = x_t.float()
            x0 = x0.float()
            acp_t = self.alphas_cumprod[t_cur_idx].float()
            acp_p = (
                torch.ones(1, device=device, dtype=acp_t.dtype).squeeze()
                if t_prev_idx < 0
                else self.alphas_cumprod[t_prev_idx]
            )
            sqrt_acp_t  = acp_t.sqrt()
            sqrt_acp_p  = acp_p.sqrt()
            sqrt_1m_t   = (1.0 - acp_t).clamp(min=1e-8).sqrt()
            sqrt_1m_p   = (1.0 - acp_p).sqrt()
            eps_hat = (x_t - sqrt_acp_t * x0) / sqrt_1m_t
            if eta == 0.0:
                return sqrt_acp_p * x0 + sqrt_1m_p * eps_hat
            sigma_sq = (
                eta ** 2
                * (1.0 - acp_p) / (1.0 - acp_t).clamp(min=1e-8)
                * (1.0 - acp_t / acp_p.clamp(min=1e-8)).clamp(min=0.0)
            )
            sigma    = sigma_sq.sqrt()
            dir_coef = (1.0 - acp_p - sigma_sq).clamp(min=0.0).sqrt()
            noise    = torch.zeros_like(x_t) if t_cur_idx == 0 else torch.randn_like(x_t)
            return sqrt_acp_p * x0 + dir_coef * eps_hat + sigma * noise

        action_traj = _step(action_traj, action_pred, a_t_cur, a_t_prev)
        state_traj  = _step(state_traj,  state_pred,  s_t_cur, s_t_prev)

        # Restore inpainted positions (will be overwritten each step anyway)
        if not self.no_state_override:
            state_traj[:, :self.n_past_steps] = nobs

        return action_traj, state_traj

    def joint_ns_ddim_step(
        self,
        action_traj,
        state_traj,
        nobs,
        a_t_cur_vec,
        a_t_prev_vec,
        s_t_cur_vec,
        s_t_prev_vec,
        eta=0.0,
        cond=None,
        **kwargs,
    ):
        """[DEBUG] DDIM step using NoiseScheduler.ddim_step (per-position H tensors).

        Cross-validates joint_ddim_step.  Uses action_noise_scheduler and
        state_noise_scheduler built in DDPM_init().

        Args:
            a_t_cur_vec / a_t_prev_vec: (H,) long — action noise levels.
            s_t_cur_vec / s_t_prev_vec: (H,) long — state noise levels.
            Others: same as joint_ddim_step.
        """
        B = action_traj.shape[0]
        device = self.device

        state_traj = state_traj.clone()
        if not self.no_state_override:
            state_traj[:, :self.n_past_steps] = nobs

        a_t_b = make_timesteps(B, a_t_cur_vec, device)
        s_t_b = make_timesteps(B, s_t_cur_vec, device)

        action_pred, state_pred = self.predict_x0(
            action_traj, state_traj, a_t_b, s_t_b, cond=cond, **kwargs
        )

        return self.joint_ns_ddim_step_from_predictions(
            action_traj, state_traj, nobs,
            a_t_cur_vec, a_t_prev_vec, s_t_cur_vec, s_t_prev_vec,
            action_pred, state_pred, eta)

    def joint_ns_ddim_step_from_predictions(
        self, action_traj, state_traj, nobs,
        a_t_cur_vec, a_t_prev_vec, s_t_cur_vec, s_t_prev_vec,
        action_pred, state_pred, eta=0.0,
    ):
        """Apply per-position NS-DDIM math to predictions from one NFE."""

        if self.denoised_clip_value is not None:
            action_pred = action_pred.clamp(
                -self.denoised_clip_value, self.denoised_clip_value)
            state_pred = state_pred.clamp(
                -self.denoised_clip_value, self.denoised_clip_value)

        action_traj = self.action_noise_scheduler.ddim_step(
            action_traj, action_pred, a_t_cur_vec, a_t_prev_vec, eta
        )
        state_traj = self.state_noise_scheduler.ddim_step(
            state_traj, state_pred, s_t_cur_vec, s_t_prev_vec, eta
        )
        if not self.no_state_override:
            state_traj[:, :self.n_past_steps] = nobs

        return action_traj, state_traj

    def predict_x0(
       self, action_traj, state_traj, action_t, state_t, cond=None, **kwargs
    ):
        """
        Predict clean x0 from noisy trajectories using the backbone.
        
        Args:
            action_traj: (B, H, Da) - Noisy action trajectory
            state_traj: (B, H, Do) - Noisy state trajectory
            action_t: (B, H) - Action noise levels
            state_t: (B, H) - State noise levels
            cond: (B, T_cond, cond_dim) - Optional condition
            
        Returns:
            action_pred: (B, H, Da) - Predicted clean actions
            state_pred: (B, H, Do) - Predicted clean states
        """
        # action_t = action_t.clone() + 1
        # state_t = state_t.clone() + 1
        # state_t[:,:self.n_past_steps] = 0
        self.backbone_call_count += 1
        cached = getattr(self, "_cached_condition_embeddings", None)
        state_output, action_output = self.backbone.forward(
            x_input=state_traj,
            y_input=action_traj,
            x_timesteps=state_t,
            y_timesteps=action_t,
            cond=cond,
            cond_embeddings=cached,
            **kwargs, 
        )
        # action_t = action_t.clone() - 1
        # state_t = torch.clip(state_t.clone() - 1, min=0)

        if self.state_pred_epsilon:
            state_pred = self.predict_x0_from_epsilon(state_traj, state_t, state_output)
        else:
            state_pred = state_output
        
        if self.action_pred_epsilon:
            action_pred = self.predict_x0_from_epsilon(action_traj, action_t, action_output)
        else:
            action_pred = action_output
        
        return action_pred, state_pred
    
    def mean_var_from_x0(
        self, action_traj, state_traj, action_t, state_t, action_pred, state_pred, **kwargs
    ):
        """
        Compute posterior mean and variance from x0 predictions.
        Formula: μ = coef1 * x0_pred + coef2 * x_t
                 μₜ = β̃ₜ √ α̅ₜ₋₁/(1-α̅ₜ)x₀ + √ αₜ (1-α̅ₜ₋₁)/(1-α̅ₜ)xₜ

        Args:
            action_traj: (B, H, Da) - Current noisy actions
            state_traj: (B, H, Do) - Current noisy states
            action_t: (B, H) - Action noise levels
            state_t: (B, H) - State noise levels
            action_pred: (B, H, Da) - Predicted clean actions
            state_pred: (B, H, Do) - Predicted clean states
            
        Returns:
            action_mu: (B, H, Da) - Action posterior mean
            state_mu: (B, H, Do) - State posterior mean
            action_logvar: (B, H, Da) - Action log variance
            state_logvar: (B, H, Do) - State log variance
        """

        if self.denoised_clip_value is not None:
            state_pred.clamp_(-self.denoised_clip_value, self.denoised_clip_value)
            action_pred.clamp_(-self.denoised_clip_value, self.denoised_clip_value)
            
        action_mu = (
            extract(self.ddpm_mu_coef1, action_t, action_traj.shape) * action_pred
            + extract(self.ddpm_mu_coef2, action_t, action_traj.shape) * action_traj
        )
        state_mu = (
            extract(self.ddpm_mu_coef1, state_t, state_traj.shape) * state_pred
            + extract(self.ddpm_mu_coef2, state_t, state_traj.shape) * state_traj
        )
        action_logvar = extract(self.ddpm_logvar_clipped, action_t, action_traj.shape)
        state_logvar = extract(self.ddpm_logvar_clipped, state_t, state_traj.shape)

        return action_mu, state_mu, action_logvar, state_logvar
    
    def p_mean_var(
        self,
        action_traj,
        action_t,
        state_traj,
        state_t,
        index=None,
        cond=None,
    ):
        """
        Compute posterior distribution for reverse diffusion step.
        Combines x0 prediction with DDPM posterior formulas.
        
        Args:
            action_traj: (B, H, Da) - Noisy actions
            action_t: (B, H) - Action noise levels
            state_traj: (B, H, Do) - Noisy states
            state_t: (B, H) - State noise levels
            cond: (B, T_cond, cond_dim) - Optional condition
            
        Returns:
            action_mu, state_mu, action_logvar, state_logvar - Posterior parameters
        """

        action_pred, state_pred = self.predict_x0(
            action_traj=action_traj,
            state_traj=state_traj,
            action_t=action_t,
            state_t=state_t,
            cond=cond,
        )

        # with torch.enable_grad():
        #     state_pred_ = state_pred.detach().requires_grad_(True)
        #     guidance_loss = torch.nn.functional.mse_loss(state_pred_[:, self.n_past_steps:, 186:189], torch.tensor([-0.5, 0, 0.0], device=self.device), reduction="none")
        #     guidance_loss = -(guidance_loss).sum() #* torch.tensor([1,1,0], device=self.device)
        #     grad = -torch.autograd.grad(
        #         guidance_loss,
        #         state_pred_,
        #     )[0]

        # # print(grad[0,:,186:189].mean(dim=0))

        # mask = state_t < 10
        # pred_noise = self.predict_epsilon_from_x0(state_traj, state_t, state_pred)
        # pred_noise = pred_noise + 2 * grad #* mask[...,None]#* extract(self.ddpm_logvar_clipped, state_t, state_traj.shape).exp().sqrt()
        # state_pred = self.predict_x0_from_epsilon(state_traj, state_t, pred_noise)
        # print(extract(self.ddpm_logvar_clipped, state_t, state_traj.shape).exp().sqrt())
        # print(grad[0,:,186:189].mean(dim=0))

        # print(state_pred[0,:,186:189].mean(dim=0))

        # print('\n\n')


        action_mu, state_mu, action_logvar, state_logvar = self.mean_var_from_x0(
            action_traj=action_traj,
            state_traj=state_traj,
            action_t=action_t,
            state_t=state_t,
            action_pred=action_pred,
            state_pred=state_pred,
        )


        return action_mu, state_mu, action_logvar, state_logvar
    

    # --------------------------------TRAINING ----------------------------------------------
    def p_losses(
        self,
        action_traj,
        state_traj,
        cond=None,
        return_loss_components=False,
    ):
        """
        Compute joint training loss with temporal and joint-specific weighting.
        If predicting epsilon: E_{t, x0, ε} [||ε - ε_θ(√α̅ₜx0 + √(1-α̅ₜ)ε, t)||²
        Args:
            action_traj: (B, H, Da) - Ground truth actions (e.g., (B, 20, 29))
            state_traj: (B, H, Do) - Ground truth states (e.g., (B, 20, 384))
            cond: (B, 1, cond_dim) - Optional condition (e.g., motion latent)
            
        Returns:
            total_loss: scalar - Combined loss
            action_loss: scalar - Action loss component
            state_loss: scalar - State loss component
            action_pred: (B, H, Da) - Predicted actions (for logging)
            state_pred: (B, H, Do) - Predicted states (for logging)
        """
        B = action_traj.shape[0]
        device = self.device

        action_t = torch.randint(
            0, self.denoising_steps, (B, self.horizon), device=device
        ).long()

        # sync_timesteps=True: share the same noise level for state and action (Factor 4 ablation).
        # Removes the independent joint-timestep training distribution that co-contaminates gradients.
        if self.sync_timesteps:
            state_t = action_t.clone()
        else:
            state_t = torch.randint(
                0, self.denoising_steps, (B, self.horizon), device=device
            ).long()

        action_noise = torch.randn_like(action_traj, device=device)
        action_noisy = self.q_sample(
            trajectory=action_traj, t=action_t, noise=action_noise
        )

        state_noise = torch.randn_like(state_traj, device=device)
        if self.clean_past_state:
            state_t[:, : self.n_past_steps] = 0
        state_noisy = self.q_sample(trajectory=state_traj, t=state_t, noise=state_noise)

        # Reverse process
        state_pred, action_pred = self.backbone(
            x_input=state_noisy,
            y_input=action_noisy,
            x_timesteps=state_t,
            y_timesteps=action_t,
            cond=cond,
        )

        # ---------------- action loss ---------------------
        if self.action_pred_epsilon:
            action_loss = torch.nn.functional.mse_loss(action_pred, action_noise, reduction="none")

        else:
            action_loss = torch.nn.functional.mse_loss(
                action_pred, action_traj, reduction="none"
            )

        # # BUG: This should be fix for (elspider air)
        # hip_idxs = [0, 1, 2, 6, 7, 8]
        # knee_idxs = [3, 9]
        # ankle_idxs = [4, 5, 10, 11]
        
        # action_loss_scale = torch.ones(29, device=self.device) * 2 
        # action_loss_scale[...,hip_idxs]   = 6 # 4
        # action_loss_scale[...,knee_idxs]  = 6 
        # action_loss_scale[...,ankle_idxs] = 6 

        # action_loss = action_loss * 2 # times 3
        action_loss = action_loss * self.action_loss_weights.to(self.device)
        action_prediction_loss = action_loss.mean()
        action_loss = action_prediction_loss

        # ---------------- state loss ------------------------
        if self.state_pred_epsilon:
            state_loss = torch.nn.functional.mse_loss(state_pred, state_noise, reduction="none")
        else:
            state_loss = torch.nn.functional.mse_loss(state_pred, state_traj, reduction="none")

        state_loss = state_loss * self.state_loss_weights.to(self.device)
        state_loss = state_loss.mean()
        
        # velocity_loss = torch.nn.functional.mse_loss(state_pred[:, 1:, :], state_pred[:, :-1, :], reduction="none")
        # velocity_loss = velocity_loss.mean() * .1

        # state_loss += velocity_loss
                
        action_rate_mse = torch.nn.functional.mse_loss(
            action_pred[:, 1:, :], action_pred[:, :-1, :], reduction="none"
        ).mean()
        action_rate_loss = action_rate_mse * .1
        # Keep the raw prediction term independently auditable. The prior
        # in-place add aliased and mutated action_prediction_loss.
        action_loss = action_prediction_loss + action_rate_loss

        scaled_state_loss = self.state_loss_scale * state_loss
        total_loss = action_loss + scaled_state_loss
        result = (
            total_loss,
            action_loss,
            state_loss,
            action_pred,
            state_pred,
        )
        if not return_loss_components:
            return result
        return result + ({
            "action_prediction_loss": action_prediction_loss,
            "action_rate_mse": action_rate_mse,
            "action_rate_coefficient": action_rate_loss.new_tensor(0.1),
            "action_rate_loss": action_rate_loss,
            "action_loss": action_loss,
            "state_prediction_loss": state_loss,
            "state_loss_scale": state_loss.new_tensor(self.state_loss_scale),
            "scaled_state_loss": scaled_state_loss,
            "total_loss": total_loss,
            "action_loss_weights": self.action_loss_weights,
            "state_loss_weights": self.state_loss_weights,
        },)

    # -------------------------------- HELPER FUNCTIONS -----------------------------------------

    def get_loss_weights(self, loss_schedule):
        """
        Generate temporal loss weights for prioritizing recent predictions.
        
        Args:
            loss_schedule: str - Schedule type (e.g., 'constant-to-8', 'linear', 'exponential-1.0')
            loss_schedule (str): A string specifying the type of loss schedule to use.
                     Supported schedules include:
                     - 'constant-to-{n}': Sets weights to 1 for the first n steps and 0 thereafter.
                     - 'linear': Linearly decreases weights from 1 to 0 over the action steps.
                     - 'cosine': Applies a cosine function to decrease weights from 1 to 0 over the action steps.
                     - 'exponential-{temp}': Applies an exponential decay to the weights, with an optional temperature parameter.
                     - 'sigmoid': Applies a sigmoid function to decrease weights from 1 to 0 over the action steps.

        Returns:
            weights: (1, H, 1) - Loss weights per timestep position
                     e.g., for 'constant-to-8': [1,1,1,1,1,1,1,1,0,0,...,0]
        """
        weights = torch.ones((1, self.horizon, 1), device=self.device)

        if "constant-to-" in loss_schedule:
            n_pred = loss_schedule.split("constant-to-")
            if len(n_pred) == 2:
                n_pred = int(n_pred[-1])
                weights[:, n_pred + self.n_past_steps :] = 0.0
        elif "linear" == loss_schedule:
            weights[:, self.n_past_steps :] = torch.linspace(
                1, 0, self.n_future_steps, device=self.device
            ).view(1, -1, 1)
        elif "cosine" == loss_schedule:
            weights[:, self.n_past_steps :] = torch.cos(
                torch.linspace(0, torch.pi / 2, self.n_future_steps, device=self.device)
            ).view(1, -1, 1)
        elif "exponential" in loss_schedule:
            temp = loss_schedule.split("exponential-")
            if len(temp) == 2:
                temp = float(temp[-1])
            else:
                temp = 1
            weights[:, self.n_past_steps :] = torch.exp(
                -temp * torch.arange(self.n_future_steps, device=self.device)
            ).view(1, -1, 1)
        elif "sigmoid" == loss_schedule:
            weights[:, self.n_past_steps + 1 :] = 1 - (
                1
                / (
                    1
                    + torch.exp(
                        -0.5 * torch.arange(self.n_future_steps - 1, device=self.device)
                        + 3
                    )
                )
            ).view(1, -1, 1)

        if "exclude-past" in loss_schedule:
            weights[:, : self.n_past_steps] = 0.0
        return weights
