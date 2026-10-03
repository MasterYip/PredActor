from __future__ import annotations

import torch
from diffusion_policy.modules.policy_diffusion import DiffusionActor
from diffusion_policy.modules.diffusion_model import extract


class CoDiffuseDPActor(DiffusionActor):
    """DiffusionActor backed by transformer_codiffuse.Transformer.

    x-stream: always zeros (placeholder).  x_to_y and y_to_x attention should
              be set to 'no_attn' in the config — x carries no information.
    y-stream: noisy action trajectory being denoised.
    cond:     obs + optional CLIP enter via encoder cross-attention, identical
              to DiffusionActor with transformer.Transformer.

    Only y_output is used for loss and inference.  No state trajectory, no
    rolling buffer, no joint noise schedule — this is action-only diffusion
    with the co-diffuse interleaved-token backbone as a drop-in replacement.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # SequentialDiffusionModel.__init__ sets output_dim = backbone.output_dim
        # = backbone.x_output_dim (= 1 for the zero placeholder stream).
        # Override to use the y (action) stream dimensions.
        self.output_dim = self.backbone.y_output_dim
        self.seq_shape = (self.horizon, self.output_dim)
        self.action_dim = self.output_dim
        self.x_placeholder_dim = self.backbone.x_input_dim

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_cond(self, cond):
        """Convert dict cond to tensor, mirroring transformer.Transformer.forward.

        dict format: {'obs': (B, T_past, obs_dim), 'motion': (B, T_cond, motion_dim)}

        Two modes:
        - Normal (obs has real data, dim > 1): broadcast motion to T_past and
          concatenate along the feature axis → (B, T_past, obs_dim + motion_dim).
        - Nox/placeholder (obs.shape[-1] <= 1): observation is a zero placeholder;
          all conditioning lives in motion, which is returned directly.
        """
        if not isinstance(cond, dict):
            return cond
        obs = cond['obs']                          # (B, T_past, obs_dim)
        motion = cond.get('motion', None)
        if motion is not None:
            if obs.shape[-1] <= 1:
                # Zero-placeholder obs (nox profile): cond is fully in motion.
                return motion
            T_obs = obs.shape[1]
            motion_exp = motion.expand(-1, T_obs, -1)  # (B, T_past, motion_dim)
            return torch.cat([obs, motion_exp], dim=-1)
        return obs

    def _forward_backbone(self, y_input, t_b, cond=None):
        """Run codiffuse backbone with a zero-filled x placeholder.

        Args:
            y_input: (B, H, action_dim)  noisy action trajectory
            t_b:     (B, H)              diffusion timesteps
            cond:    tensor or dict      observation conditioning

        Returns:
            y_pred:  (B, H, action_dim)  predicted noise or clean action
        """
        B, H, _ = y_input.shape
        x_zeros = torch.zeros(B, H, self.x_placeholder_dim, device=y_input.device)
        cond_tensor = self._resolve_cond(cond)
        _, y_pred = self.backbone(x_zeros, y_input, t_b, t_b, cond=cond_tensor)
        return y_pred

    # ------------------------------------------------------------------
    # Overrides — route backbone calls through y-stream
    # ------------------------------------------------------------------

    def compute_x0_pred(self, x_t, t, **kwargs):
        """Predict clean x0 from noisy x_t via codiffuse backbone (y-stream)."""
        output = self._forward_backbone(x_t, t, cond=kwargs.get('cond'))
        if self.predict_epsilon:
            x0 = self.predict_x0_from_epsilon(x_t, t, output)
        else:
            x0 = output
        if self.denoised_clip_value is not None:
            x0 = x0.clamp(-self.denoised_clip_value, self.denoised_clip_value)
        return x0

    def p_mean_var(self, x, t, index=None, **kwargs):
        """DDPM posterior mean & variance via codiffuse backbone."""
        x_pred = self.compute_x0_pred(x, t, **kwargs)
        mu = (
            extract(self.ddpm_mu_coef1, t, x.shape) * x_pred
            + extract(self.ddpm_mu_coef2, t, x.shape) * x
        )
        logvar = extract(self.ddpm_logvar_clipped, t, x.shape)
        return mu, logvar

    def p_losses(self, trajectory, cond, motion_cond=None):
        """Training loss — MSE on y-stream prediction only."""
        B = trajectory.shape[0]
        device = trajectory.device
        noise = torch.randn_like(trajectory, device=device)
        t = torch.randint(0, self.denoising_steps, (B, self.horizon), device=device).long()
        x_noisy = self.q_sample(trajectory=trajectory, t=t, noise=noise)

        final_cond = cond
        if motion_cond is not None:
            final_cond = {'obs': cond, 'motion': motion_cond}

        y_pred = self._forward_backbone(x_noisy, t, cond=final_cond)

        if self.predict_epsilon:
            return torch.nn.functional.mse_loss(y_pred, noise, reduction='mean')
        else:
            return torch.nn.functional.mse_loss(y_pred, trajectory, reduction='mean')
