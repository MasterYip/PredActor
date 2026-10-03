from __future__ import annotations
from typing import Tuple, Union

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import time
# import einops
from torch.distributions.normal import Normal
from diffusion_policy.backbone.base_backbone import ConditionalSeqBackbone
from diffusion_policy.modules.diffusion_model import SequentialDiffusionModel, make_timesteps, extract, cosine_beta_schedule
from diffusion_policy.utils.noise_scheduler import NoiseScheduler

from diffusion_policy.modules.base_actor import BaseActor

class DiffusionActor(SequentialDiffusionModel, BaseActor):
    """ 
    This Module implements a Conditional Diffusion Model for sequential data, 
    which is used in Diffusion Policy
    """
    backbone: ConditionalSeqBackbone
    def __init__(
        self,
        ddim_eta: float = 0.0,
        ddim_steps: int = None,
        use_ns_ddim: bool = False,  # [DEBUG] use NoiseScheduler.ddim_step instead of self.ddim_step
        **kwargs,
    ):
        SequentialDiffusionModel.__init__(self, **kwargs)
        BaseActor.__init__(self, backbone=self.backbone)

        self.obs_dim = self.backbone.cond_dim
        self.n_past_steps = self.backbone.n_cond_steps
        self.action_dim = self.output_dim
        self.n_future_steps = self.horizon - self.n_past_steps

        self.ddim_eta = ddim_eta
        self.ddim_steps = ddim_steps
        self.use_ns_ddim = use_ns_ddim  # [DEBUG]

    def DDPM_init(self):
        """Initialize DDPM buffers and build NoiseScheduler for DDIM."""
        super().DDPM_init()
        # n_past_steps for NoiseScheduler = 0: the action trajectory has NO inpainted
        # region. (backbone.n_cond_steps is the observation conditioning length, not a
        # part of the diffused trajectory.)
        self.noise_scheduler = NoiseScheduler(
            denoising_steps=self.denoising_steps,
            horizon=self.horizon,
            n_past_steps=0,
            alphas_cumprod=self.alphas_cumprod,
        )

    def act(self, nobs, cond=None):
        """
        Generate actions from observations with optional motion conditioning.
        
        Args:
            nobs: (B, n_past, obs_dim) - Past observations
            cond: (B, n_cond, cond_dim) - Optional motion latent conditioning (e.g., from MotionCLIP)
            
        Returns:
            action_traj: (B, horizon, action_dim) - Predicted actions
        """
        # clip nobs shape
        B = nobs.shape[0]
        nobs = nobs[:,:self.n_past_steps]
        
        # Stack observation and motion condition
        # The backbone expects cond to include both obs and optional motion_cond
        final_cond = nobs
        if cond is not None:
            # Concatenate along the sequence dimension: (B, n_past + n_cond, dim)
            # Note: obs and cond may have different feature dimensions, handled by backbone
            final_cond = {'obs': nobs, 'motion': cond}
        
        trajectory = torch.randn((B, *self.seq_shape), device=self.device)

        if self.ddim_steps is not None and self.ddim_steps < self.denoising_steps:
            # Build sub-sampled timestep sequence in descending order.
            # Each step jumps from t to the next sampled t (not just t-1), and the
            # final step uses t_prev=-1 which forces the output to exactly x0_pred.
            T = self.denoising_steps
            if self.ddim_steps >= T:
                timesteps = list(range(T - 1, -1, -1))  # full: [T-1, ..., 0]
            else:
                idx = torch.linspace(0, T - 1, self.ddim_steps).round().long()
                timesteps = sorted({int(i) for i in idx.tolist()}, reverse=True)


            if self.use_ns_ddim:
                # [DEBUG] NoiseScheduler path — uses per-position (H,) timestep tensors
                # and NoiseScheduler.ddim_step, to cross-validate against self.ddim_step.
                schedule = self.noise_scheduler.get_schedule('full')
                if self.ddim_steps < len(schedule):
                    indices = self.noise_scheduler._uniform_indices(len(schedule), self.ddim_steps)
                    sub = [schedule[i] for i in indices]
                    # Restitch: t_prev[i] = t_cur[i+1] to form a valid DDIM chain
                    schedule = []
                    for i, (tc, tp) in enumerate(sub):
                        tp = sub[i + 1][0].clone() if i + 1 < len(sub) else tp
                        schedule.append((tc, tp))
                _t0 = time.perf_counter()
                for t_cur, t_prev in schedule:
                    t_b = make_timesteps(B, t_cur, self.device)
                    x0 = self.compute_x0_pred(trajectory, t_b, cond=final_cond)
                    trajectory = self.noise_scheduler.ddim_step(trajectory, x0, t_cur, t_prev, self.ddim_eta)
                _dt = 1000 * (time.perf_counter() - _t0)
                print(f"[DDIM-NS] steps={len(schedule)}, total={_dt:.2f}ms, per_step={_dt/len(schedule):.2f}ms")
            else:
                # _t0 = time.perf_counter()
                for i, t in enumerate(timesteps):
                    # t_prev = next step's noise level, or -1 on the last step (→ x0_pred)
                    t_prev = timesteps[i + 1] if i + 1 < len(timesteps) else -1
                    trajectory = self.ddim_step(trajectory, t, t_prev, self.ddim_eta, cond=final_cond)
                # _dt = 1000 * (time.perf_counter() - _t0)
                # print(f"[DDIM] steps={len(timesteps)}, total={_dt:.2f}ms, per_step={_dt/len(timesteps):.2f}ms")
        else:
            # DDPM path (default)
            t_all = torch.flip(torch.arange(self.denoising_steps), dims=(0,))
            t_all = t_all.unsqueeze(1).repeat(1, self.horizon)

            for i, t in enumerate(t_all):
                trajectory = self.diffuse_step(trajectory, t, i, cond=final_cond)

        return trajectory

    def p_losses(
        self,
        trajectory,
        cond,
        motion_cond=None,
    ):
        """
        Compute diffusion loss with optional motion conditioning.
        If predicting epsilon: E_{t, x0, ε} [||ε - ε_θ(√α̅ₜx0 + √(1-α̅ₜ)ε, t)||²

        Args:
            trajectory: (B, horizon, action_dim) - Action trajectory to denoise
            cond: (B, n_past, obs_dim) - Past observations as conditioning
            motion_cond: (B, n_cond, cond_dim) - Optional motion latent (e.g., from MotionCLIP)
            
        Returns:
            loss: MSE loss between predicted and target (noise or trajectory)
        """

        # Forward process
        B = trajectory.shape[0]
        device = trajectory.device
        noise = torch.randn_like(trajectory, device=device)

        # diffusion sampling
        t = torch.randint(
            0, self.denoising_steps, (B, self.horizon), device=device
        ).long()
        
        x_noisy = self.q_sample(trajectory=trajectory, t=t, noise=noise)
        
        # Stack observation and motion condition
        # The backbone expects cond to include both obs and optional motion_cond
        final_cond = cond
        if motion_cond is not None:
            # Pass both as dict for backbone to handle
            final_cond = {'obs': cond, 'motion': motion_cond}
        
        # Reverse process
        x_pred = self.backbone(x_noisy, t, cond=final_cond)

        if self.predict_epsilon:
            return torch.nn.functional.mse_loss(x_pred, noise, reduction="mean")
        else:
            return torch.nn.functional.mse_loss(x_pred, trajectory, reduction="mean")


class MatchedActionDiffusionActor(DiffusionActor):
    """Action-only ablation with the Full actor's action-side objective.

    This actor retains the ordinary single diffused trajectory from
    :class:`DiffusionActor`. Observation history and task conditioning meet only
    at the transformer's conditioning boundary; no state trajectory is created,
    denoised, predicted, or returned.
    """

    def __init__(
        self,
        data_profile,
        raw_observation_dim: int = 192,
        observation_dim: int = 384,
        emphasis_projection_seed: int | None = None,
        action_weight_schedule: str = "constant-to-8",
        action_rate_coefficient: float = 0.1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        from diffusion_policy.dataset.data_profile import DataProfile
        from diffusion_policy.dataset.state_emph import build_profile_emphasis_projection

        profile = DataProfile.from_yaml(data_profile)
        history_projection = build_profile_emphasis_projection(
            profile,
            self.device,
            seed=emphasis_projection_seed,
        )
        expected_shape = (int(raw_observation_dim), int(observation_dim))
        if tuple(history_projection.shape) != expected_shape:
            raise ValueError(
                f"history projection shape {tuple(history_projection.shape)} "
                f"does not match expected {expected_shape}"
            )
        self.register_buffer("history_projection", history_projection)
        self.raw_obs_dim = int(raw_observation_dim)
        self.obs_dim = int(observation_dim)
        self.data_profile = data_profile
        self.emphasis_projection_seed = emphasis_projection_seed
        self.action_weight_schedule = action_weight_schedule
        self.action_rate_coefficient = float(action_rate_coefficient)
        self.register_buffer(
            "action_loss_weights",
            self._make_action_loss_weights(action_weight_schedule),
            persistent=True,
        )

    def _make_action_loss_weights(self, loss_schedule: str) -> torch.Tensor:
        weights = torch.ones((1, self.horizon, 1), device=self.device)
        if loss_schedule.startswith("constant-to-"):
            n_pred = int(loss_schedule.removeprefix("constant-to-"))
            weights[:, n_pred + self.n_past_steps:] = 0.0
        elif loss_schedule != "constant":
            raise ValueError(
                "MatchedActionDiffusionActor supports only 'constant' and "
                "'constant-to-N' action schedules"
            )
        return weights

    def _project_history(self, observation: torch.Tensor) -> torch.Tensor:
        if observation.shape[-1] != self.raw_obs_dim:
            raise ValueError(
                f"expected raw observation width {self.raw_obs_dim}, "
                f"got {observation.shape[-1]}"
            )
        return observation @ self.history_projection

    def act(self, nobs, cond=None):
        return super().act(self._project_history(nobs), cond=cond)

    def p_losses(self, trajectory, cond, motion_cond=None):
        B = trajectory.shape[0]
        noise = torch.randn_like(trajectory)
        t = torch.randint(
            0, self.denoising_steps, (B, self.horizon), device=trajectory.device
        ).long()
        action_noisy = self.q_sample(trajectory=trajectory, t=t, noise=noise)

        projected_history = self._project_history(cond)
        final_cond = projected_history
        if motion_cond is not None:
            final_cond = {'obs': projected_history, 'motion': motion_cond}
        action_pred = self.backbone(action_noisy, t, cond=final_cond)

        target = noise if self.predict_epsilon else trajectory
        prediction_loss = torch.nn.functional.mse_loss(
            action_pred, target, reduction="none"
        )
        prediction_loss = (prediction_loss * self.action_loss_weights).mean()
        action_rate_mse = torch.nn.functional.mse_loss(
            action_pred[:, 1:, :], action_pred[:, :-1, :], reduction="none"
        ).mean()
        return prediction_loss + self.action_rate_coefficient * action_rate_mse
