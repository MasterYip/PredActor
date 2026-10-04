from __future__ import annotations

import torch
from diffusion_policy.modules.joint_diffusion import JointDiffusionActor
from diffusion_policy.utils.noise_scheduler import NoiseScheduler


class DiffusePRDP(JointDiffusionActor):
    """PRDP (Predictive-Rolling Diffusion Policy) with DDIM acceleration.

    Differences from DiffuseCLoC:
    - Uses NoiseScheduler instead of the inline generate_denoising_matrix logic.
    - Replaces DDPM Gaussian posterior sampling with a DDIM deterministic ODE step,
      enabling large timestep jumps (multi-step acceleration) without quality loss.
    - Supports real-time budget planning: given a time_limit_ms and measured step
      cost, the scheduler automatically selects a DDIM sequence that finishes before
      the deadline.
    - State emphasis projection (emphasis_mat) reused verbatim from DiffuseCLoC.
    - Rolling inference (FIFO buffer) reused verbatim from DiffuseCLoC.

    Args:
        state_emphasis:        Emphasis mode name (see ObsComposer.build_emphasis_matrix).
        ddim_eta:              DDIM stochasticity (0 = fully deterministic, 1 ≈ DDPM).
        action_schedule:       NoiseScheduler mode for actions ('from_xt_decreasing', etc.).
        state_schedule:        NoiseScheduler mode for states ('from_xt_step', etc.).
        randomize_noise_schedule: Enable rolling inference (FIFO buffer reuse).
        time_limit_ms:         Real-time budget in ms (None = no limit).
        default_step_time_ms:  Estimated model forward time per step (ms).
    """

    def __init__(
        self,
        state_emphasis: str = "same",
        ddim_eta: float = 0.0,
        action_schedule: str = "from_xt_decreasing",
        state_schedule: str = "from_xt_step",
        randomize_noise_schedule: bool = True,
        time_limit_ms: float | None = None,
        default_step_time_ms: float = 2.0,
        use_cloc_fallback: bool = False,
        data_profile=None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.state_emphasis = state_emphasis
        self.ddim_eta = ddim_eta
        self.action_schedule = action_schedule
        self.state_schedule = state_schedule
        self.randomize_noise_schedule = randomize_noise_schedule
        self.time_limit_ms = time_limit_ms
        self.default_step_time_ms = default_step_time_ms
        self.use_cloc_fallback = use_cloc_fallback
        self.data_profile = data_profile

        self.get_emphasis_projection()

    def rolling_inference_enabled(self) -> bool:
        return bool(self.randomize_noise_schedule)

    # ------------------------------------------------------------------ #
    #  DDPM_init override: also build NoiseScheduler after alphas are set  #
    # ------------------------------------------------------------------ #

    def DDPM_init(self):
        """Initialize DDPM buffers then build the NoiseScheduler."""
        super().DDPM_init()
        self._build_scheduler()

    def _build_scheduler(self):
        self.noise_scheduler = NoiseScheduler(
            denoising_steps=self.denoising_steps,
            horizon=self.horizon,
            n_past_steps=self.n_past_steps,
            alphas_cumprod=self.alphas_cumprod,
        )

    # ------------------------------------------------------------------ #
    #  Inference                                                           #
    # ------------------------------------------------------------------ #

    def act(
        self,
        nobs,
        cond=None,
        **kwargs,
    ):
        """Generate actions with rolling DDIM inference and state emphasis.

        If use_cloc_fallback=True, delegates to DiffuseCLoC.act() (original DDPM
        rolling inference) for debugging — bypasses all DDIM / NoiseScheduler logic.

        Args:
            nobs: (B, n_past, Do)          — Past observations.
            cond: (B, T_cond, cond_dim)    — Optional conditioning (e.g. motion latent).

        Returns:
            action_traj: (B, H, Da)  — Predicted action trajectory.
            state_traj:  (B, H, Do)  — Predicted state trajectory (original space).
        """
        if self.use_cloc_fallback:
            from diffusion_policy.modules.diffuse_cloc import DiffuseCLoC
            return DiffuseCLoC.act(self, nobs, cond=cond, **kwargs)
        B = nobs.shape[0]
        nobs = nobs[:, : self.n_past_steps, :]

        action_traj = torch.randn((B, self.horizon, self.action_dim), device=self.device)
        state_traj  = torch.randn((B, self.horizon, self.obs_dim),    device=self.device)

        # ---- Build DDIM schedules -----------------------------------------
        if self.randomize_noise_schedule:
            if not hasattr(self, "action_rolling_traj"):
                action_schedule = self._get_schedule("full_decreasing", is_state=False)
            else:
                action_schedule = self._get_schedule(self.action_schedule, is_state=False)
                action_traj[:, :-1] = self.action_rolling_traj

            if not hasattr(self, "state_rolling_traj"):
                state_schedule = self._get_schedule("full", is_state=True)
            else:
                state_schedule = self._get_schedule(self.state_schedule, is_state=True)
                state_traj[:, :-1] = self.state_rolling_traj
        else:
            action_schedule = self._get_schedule("full", is_state=False)
            state_schedule  = self._get_schedule("full", is_state=True)

        # Apply state emphasis projection
        nobs = nobs @ self.emphasis_mat

        # ---- Rolling chains for buffer extraction (same as DiffuseCLoC) --
        action_chain = []
        state_chain  = []

        n_steps = max(len(action_schedule), len(state_schedule))

        # Mirror CLoC: initialise prev_t = t_cur[0] + 1 (one level above start)
        prev_a_t = action_schedule[0][0].clone() + 1
        prev_s_t = state_schedule[0][0].clone() + 1

        for i in range(n_steps):
            a_t_cur, a_t_prev = action_schedule[min(i, len(action_schedule) - 1)]
            s_t_cur, s_t_prev = state_schedule[min(i, len(state_schedule) - 1)]

            if self.randomize_noise_schedule:
                # Append BEFORE the step, using prev_t — matches CLoC exactly
                action_chain.append((action_traj.clone(), prev_a_t))
                state_chain.append((state_traj.clone(), prev_s_t))

            prev_a_t = a_t_cur.clone()
            prev_s_t = s_t_cur.clone()

            action_traj, state_traj = self._ddim_step(
                nobs=nobs,
                action_traj=action_traj,
                state_traj=state_traj,
                a_t_cur=a_t_cur,
                a_t_prev=a_t_prev,
                s_t_cur=s_t_cur,
                s_t_prev=s_t_prev,
                cond=cond,
                **kwargs,
            )

        if self.randomize_noise_schedule:
            # Append final fully-denoised traj with prev_t (= last t_cur = 0)
            action_chain.append((action_traj.clone(), prev_a_t))
            state_chain.append((state_traj.clone(),   prev_s_t))

            next_a_schedule = self._get_schedule(self.action_schedule, is_state=False)
            self.action_rolling_traj = self._get_rolling_traj(action_chain, next_a_schedule)
            next_s_schedule = self._get_schedule(self.state_schedule, is_state=True)
            self.state_rolling_traj  = self._get_rolling_traj(state_chain,  next_s_schedule)

        # ---- Invert emphasis projection ----------------------------------
        state_traj = state_traj @ self.emphasis_mat_inv

        return action_traj, state_traj

    # ------------------------------------------------------------------ #
    #  Training                                                            #
    # ------------------------------------------------------------------ #

    def p_losses(self, action_traj, state_traj, cond=None):
        """Apply state emphasis before computing DDPM training loss.

        Args:
            action_traj: (B, H, Da)
            state_traj:  (B, H, Do)
            cond:        (B, T_cond, cond_dim)

        Returns:
            Same as JointDiffusionActor.p_losses.
        """
        state_traj = state_traj @ self.emphasis_mat
        return super().p_losses(action_traj, state_traj, cond=cond)

    # ------------------------------------------------------------------ #
    #  Emphasis projection (identical to DiffuseCLoC)                     #
    # ------------------------------------------------------------------ #

    def get_emphasis_projection(self):
        """Build emphasis_mat and register it (plus its pseudoinverse) as model buffers.

        If a data_profile is provided (str profile name, path, or dict), uses
        EmphMatGen.build() with the full profile for config-driven construction.
        Otherwise falls back to EmphMatGen.build_from_mode() with the legacy
        state_emphasis string for backward compatibility.
        """
        from diffusion_policy.dataset.g1_dataset import EmphMatGen, DataProfile
        state_dim = self.backbone.x_output_dim

        if self.data_profile is not None:
            profile = DataProfile.from_yaml(self.data_profile)
            obs_reflect_op = None
            emphasis_mat = EmphMatGen.build(profile, self.device, obs_reflect_op)
        else:
            emphasis_mat = EmphMatGen.build_from_mode(self.state_emphasis, state_dim, self.device)

        self.register_buffer("emphasis_mat",     emphasis_mat)
        self.register_buffer("emphasis_mat_inv", torch.linalg.pinv(emphasis_mat))

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_schedule(self, mode: str, is_state: bool):
        """Retrieve a DDIM schedule, applying real-time budget planning if set."""
        if self.time_limit_ms is not None:
            return self.noise_scheduler.plan_realtime(
                time_limit_ms=self.time_limit_ms,
                step_time_ms=self.default_step_time_ms,
                mode=mode,
                is_state=is_state,
            )
        return self.noise_scheduler.get_schedule(mode=mode, is_state=is_state)

    def _ddim_step(
        self,
        nobs,
        action_traj,
        state_traj,
        a_t_cur,
        a_t_prev,
        s_t_cur,
        s_t_prev,
        cond=None,
        **kwargs,
    ):
        """Single DDIM reverse step for joint action-state denoising.

        Inpaints past observations, runs one backbone forward to get x̂₀,
        then applies the deterministic DDIM ODE step for both streams.

        Args:
            nobs:        (B, n_past, Do)  — Clean (emphasis-projected) past obs.
            action_traj: (B, H, Da)       — Noisy actions at a_t_cur.
            state_traj:  (B, H, Do)       — Noisy states at s_t_cur.
            a_t_cur:     (H,)             — Current action noise levels.
            a_t_prev:    (H,)             — Target action noise levels (after step).
            s_t_cur:     (H,)             — Current state noise levels.
            s_t_prev:    (H,)             — Target state noise levels (after step).
            cond:        optional cond tensor.

        Returns:
            action_traj: (B, H, Da)  — Denoised actions at a_t_prev.
            state_traj:  (B, H, Do)  — Denoised states at s_t_prev.
        """
        from diffusion_policy.modules.diffusion_model import make_timesteps

        B = nobs.shape[0]
        device = self.device

        # Inpaint past positions — skip when state is denoised from condition
        if not getattr(self, 'no_state_override', False):
            state_traj[:, : self.n_past_steps] = nobs
            s_t_cur = s_t_cur.clone()
            s_t_cur[: self.n_past_steps] = 0
            s_t_prev = s_t_prev.clone()
            s_t_prev[: self.n_past_steps] = 0

        # Expand scalars to (B, H) for backbone
        a_t_b = make_timesteps(B, a_t_cur, device)
        s_t_b = make_timesteps(B, s_t_cur, device)

        # Backbone forward → predicted x̂₀
        action_pred, state_pred = self.predict_x0(
            action_traj=action_traj,
            state_traj=state_traj,
            action_t=a_t_b,
            state_t=s_t_b,
            cond=cond,
            **kwargs,
        )

        if self.denoised_clip_value is not None:
            action_pred.clamp_(-self.denoised_clip_value, self.denoised_clip_value)
            state_pred.clamp_(-self.denoised_clip_value, self.denoised_clip_value)

        # DDIM step for actions
        action_traj = self.noise_scheduler.ddim_step(
            x_t=action_traj,
            x0_pred=action_pred,
            t_cur=a_t_cur,
            t_prev=a_t_prev,
            eta=self.ddim_eta,
        )

        # DDIM step for states
        state_traj = self.noise_scheduler.ddim_step(
            x_t=state_traj,
            x0_pred=state_pred,
            t_cur=s_t_cur,
            t_prev=s_t_prev,
            eta=self.ddim_eta,
        )

        return action_traj, state_traj

    def _get_rolling_traj(self, chain, schedule):
        """Extract the FIFO rolling buffer for next inference step.

        For each future horizon position j (0 … H-2), we need the traj snapshot
        at the earliest chain step k where the noise level at position j+1 has
        dropped to exactly needed_idx[j] = t_all[0, j+1] + 1.

        This is done position-by-position (argmax of the boolean mask along K),
        which guarantees exactly H-1 outputs regardless of schedule length.

        Args:
            chain:    List[(traj, prev_t)] — length K+1 denoising history.
                      traj: (B, H, D),  prev_t: (H,) — noise level before the step.
            schedule: List[(t_cur, t_prev)] — next-step schedule (length K_next).

        Returns:
            rolled_traj: (B, H-1, D)
        """
        # (K+1, H) matrix of noise levels stored in chain
        idx = torch.stack([c[1] for c in chain])          # (K+1, H)

        # (K_next, H) matrix from next schedule's t_cur rows
        t_all = torch.stack([t_cur for t_cur, _ in schedule])  # (K_next, H)

        # For each future position j (index into H-1 positions = positions 1..H-1):
        #   needed = t_all[0, j+1] + 1
        #   pick the last chain step k where idx[k, j+1] >= needed
        needed = t_all[0, 1:] + 1   # (H-1,)  — target noise level per position

        idx_future = idx[:, 1:]      # (K+1, H-1)

        # For each position, argmax of (idx_future >= needed) along K gives the
        # LAST step where the condition holds (we want the latest valid snapshot).
        # Using (~condition).int().argmax gives the FIRST False, so we subtract 1.
        condition = idx_future >= needed   # (K+1, H-1)

        # argmax on bool finds first True; we want last True → flip K axis
        flipped = condition.flip(0)        # (K+1, H-1)
        first_true_flipped = flipped.long().argmax(dim=0)   # (H-1,)
        k_select = (idx_future.shape[0] - 1) - first_true_flipped  # (H-1,)

        # Stack traj: (B, K+1, H, D), take positions 1..H-1
        traj_stack = torch.stack([c[0] for c in chain], dim=1)  # (B, K+1, H, D)
        traj_future = traj_stack[:, :, 1:, :]                   # (B, K+1, H-1, D)

        B = traj_future.shape[0]
        D = traj_future.shape[3]
        H1 = traj_future.shape[2]

        # Gather: for each position j, pick traj_future[:, k_select[j], j, :]
        device = traj_future.device
        k_select = k_select.to(device)
        traj_future = traj_future.permute(0, 2, 1, 3)      # (B, H-1, K+1, D)
        k_idx = k_select.view(1, H1, 1, 1).expand(B, H1, 1, D)
        rolled = traj_future.gather(2, k_idx).squeeze(2)   # (B, H-1, D)
        return rolled
