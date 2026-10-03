from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F
from diffusion_policy.modules.policy_diffusion import DiffusionActor
from diffusion_policy.modules.diffusion_model import extract, make_timesteps

try:
    from diffusion_policy.task_provider.root_pos_guide import RootPosGuideProvider
except ImportError:
    RootPosGuideProvider = None

try:
    from diffusion_policy.task_provider.rlobs_standard_guide import G1RLObsStandardGuideProvider
except ImportError:
    G1RLObsStandardGuideProvider = None


class CondCoDiffuseActor(DiffusionActor):
    """Co-diffusion actor: jointly denoises x (root_pos_local) and y (actions).

    Both x and y streams are independently noised during training and jointly
    denoised during inference, mirroring JointDiffusionActor semantics but using
    the transformer_codiffuse backbone (with x_to_y:no_attn / y_to_x:causal).

    bc_agent interface — same as JointDiffusionActor:
      p_losses(action_traj, state_traj, cond):
          action_traj = [B, H, action_dim]         — ground-truth actions
          state_traj  = [B, H, x_input_dim]        — full obs trajectory (root_pos_local)
          cond        = [B, n_task_steps, cond_dim] — task condition (rlobs + CLIP)
      act(nobs, cond):
          nobs = [B, n_past, x_input_dim]          — past observations → x inpainting
          cond = [B, n_cond, cond_dim]             — task condition → encoder
    """

    def __init__(
        self,
        enable_root_pos_guide: bool = False,
        state_emphasis: str = "same",
        data_profile=None,
        **kwargs,
    ):
        self.state_emphasis = state_emphasis
        self.data_profile = data_profile
        super().__init__(**kwargs)
        # Base class sets output_dim = backbone.output_dim = backbone.x_output_dim.
        # Override to use the y (action) stream.
        self.output_dim = self.backbone.y_output_dim
        self.seq_shape = (self.horizon, self.output_dim)
        self.action_dim = self.output_dim
        self.x_input_dim = self.backbone.x_input_dim
        self._init_emphasis_projection()

        # [DEBUG] Root-position guidance via GUI velocity commands.
        # Set enable_root_pos_guide: true in the YAML (or actor config) to open the
        # GUI window automatically when the actor is instantiated.
        self.enable_root_pos_guide: bool = enable_root_pos_guide
        self.root_pos_guide: Any = None
        if enable_root_pos_guide:
            self.root_pos_guide = self._build_state_guide()
            self.root_pos_guide.start()  # opens the tkinter GUI in a background thread

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _init_emphasis_projection(self) -> None:
        from diffusion_policy.dataset.g1_dataset import DataProfile, EmphMatGen

        state_dim = self.backbone.x_output_dim
        if self.data_profile is not None:
            profile = DataProfile.from_yaml(self.data_profile)
            emphasis_mat = EmphMatGen.build(profile, self.device, obs_reflect_op=None)
        else:
            emphasis_mat = EmphMatGen.build_from_mode(self.state_emphasis, state_dim, self.device)

        self.register_buffer("emphasis_mat", emphasis_mat)
        self.register_buffer("emphasis_mat_inv", torch.linalg.pinv(emphasis_mat))

    def _build_state_guide(self):
        if self.x_input_dim == 3:
            if RootPosGuideProvider is None:
                raise ImportError("RootPosGuideProvider could not be imported.")
            guide_cls = RootPosGuideProvider
        elif self.x_input_dim == 192:
            if G1RLObsStandardGuideProvider is None:
                raise ImportError("G1RLObsStandardGuideProvider could not be imported.")
            guide_cls = G1RLObsStandardGuideProvider
        else:
            raise ValueError(
                f"Root-position guidance is only implemented for x_input_dim 3 or 192, got {self.x_input_dim}."
            )

        return guide_cls(
            horizon=self.horizon,
            n_past_steps=self.n_past_steps,
        )

    def _apply_root_pos_guidance(self, x_traj: torch.Tensor) -> torch.Tensor:
        if not (self.enable_root_pos_guide and self.root_pos_guide is not None):
            return x_traj
        if self.normalizer is None:
            raise RuntimeError("CondCoDiffuseActor guidance requires a fitted obs normalizer.")

        normalizer_obs = self.normalizer["obs"]
        if self.x_input_dim == 3:
            state_norm = x_traj @ self.emphasis_mat_inv
            last_index = max(self.n_past_steps - 1, 0)
            last_norm = state_norm[:, last_index, :]
            last_unnorm = normalizer_obs.unnormalize(last_norm)
            state_norm_guided = self.root_pos_guide.apply_guidance(
                state_norm,
                last_unnorm,
                normalizer=normalizer_obs,
            )
            return state_norm_guided @ self.emphasis_mat

        return self.root_pos_guide.apply_guidance(
            x_traj,
            normalizer=normalizer_obs,
            emphasis_mat=self.emphasis_mat,
            emphasis_mat_inv=self.emphasis_mat_inv,
        )

    def _resolve_cond(self, cond):
        """Convert dict cond to tensor."""
        if not isinstance(cond, dict):
            return cond
        obs = cond['obs']
        motion = cond.get('motion', None)
        if motion is not None:
            T_obs = obs.shape[1]
            motion_exp = motion.expand(-1, T_obs, -1)
            return torch.cat([obs, motion_exp], dim=-1)
        return obs

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def p_losses(self, action_traj, state_traj, cond=None):
        """Co-diffusion training loss — independent noise on x and y.

        Matches JointDiffusionActor's p_losses signature so bc_agent can route
        CondCoDiffuseActor through the same branch.

        Args:
            action_traj: [B, H, action_dim]          — ground-truth joint actions
            state_traj:  [B, H, x_input_dim]         — ground-truth root_pos_local
            cond:        [B, n_task_steps, cond_dim] — task condition (rlobs + CLIP)
        Returns:
            (total_loss, action_loss, state_loss, action_pred, state_pred)
        """
        state_traj = state_traj @ self.emphasis_mat

        B = action_traj.shape[0]
        device = action_traj.device

        # --- Action (y) noise ---
        action_noise = torch.randn_like(action_traj, device=device)
        action_t = torch.randint(0, self.denoising_steps, (B, self.horizon), device=device).long()
        y_noisy = self.q_sample(trajectory=action_traj, t=action_t, noise=action_noise)

        # --- State (x) noise — past n_past_steps remain clean (inpainting) ---
        x_noise = torch.randn_like(state_traj, device=device)
        state_t = torch.randint(0, self.denoising_steps, (B, self.horizon), device=device).long()
        state_t[:, :self.n_past_steps] = 0
        x_noisy = self.q_sample(trajectory=state_traj, t=state_t, noise=x_noise)

        cond_tensor = self._resolve_cond(cond)
        x_pred, y_pred = self.backbone(x_noisy, y_noisy, state_t, action_t, cond=cond_tensor)

        if self.predict_epsilon:
            action_loss = F.mse_loss(y_pred, action_noise, reduction='mean')
            state_loss = F.mse_loss(x_pred, x_noise, reduction='mean')
        else:
            action_loss = F.mse_loss(y_pred, action_traj, reduction='mean')
            state_loss = F.mse_loss(x_pred, state_traj, reduction='mean')

        return action_loss + state_loss, action_loss, state_loss, y_pred, x_pred

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def act(self, nobs, cond=None):
        """Joint inference: denoise x (root_pos_local) and y (actions) simultaneously.

        Args:
            nobs: [B, n_past, x_input_dim]  — past observations, inpainted into x
            cond: [B, n_cond, cond_dim]     — task condition → encoder
        Returns:
            y_traj: [B, H, action_dim]
        """
        B = nobs.shape[0]
        nobs = nobs[:, :self.n_past_steps]
        nobs_proj = nobs @ self.emphasis_mat

        y_traj = torch.randn((B, self.horizon, self.action_dim), device=self.device)
        x_traj = torch.randn((B, self.horizon, self.x_input_dim), device=self.device)

        cond_tensor = self._resolve_cond(cond)

        t_all = torch.flip(torch.arange(self.denoising_steps), dims=(0,))
        t_all = t_all.unsqueeze(1).repeat(1, self.horizon)

        for t in t_all:
            # Inpaint clean past observations into x
            x_traj[:, :self.n_past_steps] = nobs_proj

            t_b = make_timesteps(B, t, self.device)       # [B, H] — y timesteps
            x_t_b = t_b.clone()
            x_t_b[:, :self.n_past_steps] = 0              # past x steps are clean

            x_pred, y_pred = self.backbone(x_traj, y_traj, x_t_b, t_b, cond=cond_tensor)

            if self.predict_epsilon:
                x0_y = self.predict_x0_from_epsilon(y_traj, t_b, y_pred)
                x0_x = self.predict_x0_from_epsilon(x_traj, x_t_b, x_pred)
            else:
                x0_y, x0_x = y_pred, x_pred

            if self.denoised_clip_value is not None:
                x0_y = x0_y.clamp(-self.denoised_clip_value, self.denoised_clip_value)
                x0_x = x0_x.clamp(-self.denoised_clip_value, self.denoised_clip_value)

            # DDPM posterior step for y
            y_mu = (extract(self.ddpm_mu_coef1, t_b, y_traj.shape) * x0_y
                    + extract(self.ddpm_mu_coef2, t_b, y_traj.shape) * y_traj)
            y_std = (0.5 * extract(self.ddpm_logvar_clipped, t_b, y_traj.shape)).exp()
            noise = torch.randn_like(y_traj)
            noise[t_b == 0] = 0
            y_traj = y_mu + y_std * noise

            # DDPM posterior step for x
            x_mu = (extract(self.ddpm_mu_coef1, x_t_b, x_traj.shape) * x0_x
                    + extract(self.ddpm_mu_coef2, x_t_b, x_traj.shape) * x_traj)
            x_std = (0.5 * extract(self.ddpm_logvar_clipped, x_t_b, x_traj.shape)).exp()
            noise = torch.randn_like(x_traj)
            noise[x_t_b == 0] = 0
            x_traj = x_mu + x_std * noise

            x_traj = self._apply_root_pos_guidance(x_traj)

        return y_traj

    def __del__(self):
        guide = getattr(self, "root_pos_guide", None)
        if guide is not None:
            try:
                guide.stop()
            except Exception:
                pass
