from __future__ import annotations
from typing import TYPE_CHECKING

import torch
from torch.distributions.normal import Normal
from diffusion_policy.modules.joint_diffusion import JointDiffusionActor
from diffusion_policy.modules.diffusion_model import make_timesteps
from diffusion_policy.utils.noise_scheduler import StepSpec

try:
    from diffusion_policy.task_provider.root_pos_guide import RootPosGuideProvider
except ImportError:
    RootPosGuideProvider = None

count = 0
class DiffuseCLoC(JointDiffusionActor):
    """
    DiffuseCLoC: Joint diffusion with rolling inference and state emphasis.
    Key features:
    - Rolling buffer: FIFO trajectory buffer for smooth online inference
    - State emphasis: Projection matrix to emphasize global features (root, velocity)
    - Flexible noise schedules: Custom denoising patterns for efficiency
    """

    def __init__(self,
                 state_emphasis='same', randomize_noise_schedule=True,
                 data_profile=None,
                 emphasis_projection_seed: int | None = None,
                 ddim_steps=None, ddim_eta=0.0,
                 use_ns_ddim=False,  # [DEBUG] use NoiseScheduler.ddim_step instead of joint_ddim_step
                 ns_ddim_fifo: bool = False,
                 classifier_guidance_impl: str = "reuse_x0",
                 cache_condition_encoding: bool = False,
                 enable_root_pos_guide: bool = False,
                 whole_body_guidance_config: dict = None,
                 **kwargs):
        super().__init__(**kwargs)

        self.state_emphasis = state_emphasis
        self.randomize_noise_schedule = randomize_noise_schedule
        self.data_profile = data_profile
        self.emphasis_projection_seed = emphasis_projection_seed
        self.ddim_steps = ddim_steps
        self.ddim_eta = ddim_eta
        self.use_ns_ddim = use_ns_ddim  # [DEBUG]
        self.ns_ddim_fifo = bool(ns_ddim_fifo)
        if classifier_guidance_impl not in ("duplicate_backbone", "reuse_x0"):
            raise ValueError(
                "classifier_guidance_impl must be duplicate_backbone or reuse_x0")
        self.classifier_guidance_impl = classifier_guidance_impl
        self.cache_condition_encoding = bool(cache_condition_encoding)
        self.get_emphasis_projection()

        self.action_schedule = 'from_xT_decreasing'
        # PROBLEM: why not using from_xT_decreasing
        self.state_schedule = 'from_xT_step'

        # ── Root-position guidance (legacy) ──
        self.enable_root_pos_guide: bool = enable_root_pos_guide
        self.root_pos_guide = None  # RootPosGuideProvider | None

        # ── Whole-body guidance (term-based, kinematic model) ──
        self.whole_body_guidance = None
        # Retain the raw config so exporters (export_policy.py) can serialize
        # the C++ deploy-config WBG block without re-loading the Hydra YAML.
        self.whole_body_guidance_config = whole_body_guidance_config
        if whole_body_guidance_config is not None and whole_body_guidance_config.get('enabled', False):
            # Import the concrete WBG runtime directly. The package initializer
            # also exposes optional JoyText/CLIP providers, which are not a
            # dependency of numeric WBG and are absent on minimal edge targets.
            from diffusion_policy.task_provider.whole_body_guidance.whole_body_guidance import (
                WholeBodyGuidance,
            )
            wbc = whole_body_guidance_config
            self.whole_body_guidance = WholeBodyGuidance(
                profile=wbc.get('profile', data_profile or 'g1_standard'),
                guidances=wbc.get('guidances'),
                horizon=self.horizon,
                n_past_steps=self.n_past_steps,
                dt=0.02,
                kp_init=wbc.get('kp_init', 1.0),
                vx_range=tuple(wbc.get('vx_range', [-5.0, 5.0])),
                vy_range=tuple(wbc.get('vy_range', [-4.0, 4.0])),
                vz_range=tuple(wbc.get('vz_range', [-2.0, 2.0])),
                wz_range=tuple(wbc.get('wz_range', [-2.0, 2.0])),
                gui_enabled=wbc.get('gui', {}).get('enabled', True),
                mode=wbc.get('mode', 'simple'),
                body_groups_config=wbc.get('body_groups'),
                guidance_mode=wbc.get('guidance_mode', 'classifier'),
                enable_zeta_comp=wbc.get('enable_zeta_comp', True),
                enable_damping_comp=wbc.get('enable_damping_comp', True),
                denoising_steps=self.denoising_steps,
                destination_follow_config=wbc.get('destination_follow_config'),
            )
            print(f"[DiffuseCLoC] WholeBodyGuidance enabled: {wbc}")

        # Default root indices for standard G1 192-d FK observation layout:
        #   body_pos_local [0:90], body_lin_vel_local [90:180],
        #   root_pos_local [180:183], root_rot_local [183:186],
        #   root_lin_vel_local [186:189], root_ang_vel_local [189:192]
        self._root_slice = (180, 183)
        self._pelvis_body_slice = (0, 3)
        self._root_vel_slice = None          # set by _compute_root_indices when present

        if enable_root_pos_guide:
            if RootPosGuideProvider is None:
                raise ImportError(
                    "RootPosGuideProvider could not be imported — "
                    "ensure diffusion_policy.task_provider.root_pos_guide is available."
                )
            self.root_pos_guide = RootPosGuideProvider(
                horizon=self.horizon,
                n_past_steps=self.n_past_steps,
            )
            # GUI is started lazily on the first apply_guidance() call (inference only).
            self._compute_root_indices()

    def rolling_inference_enabled(self) -> bool:
        if self.ddim_steps is not None and self.use_ns_ddim:
            return bool(self.ns_ddim_fifo)
        return bool(self.randomize_noise_schedule)

    def _ns_ddim_fifo_warm_start(
        self,
        fresh_noise: torch.Tensor,
        clean_fifo: torch.Tensor,
        initial_t: torch.Tensor,
    ) -> torch.Tensor:
        """Re-noise a shifted clean NS-DDIM plan at the normal initial level.

        The stateless the validated reference NS-DDIM path starts every horizon position from
        fresh Gaussian noise.  The explicit FIFO mode preserves the previous
        clean prediction for positions 1..H-1, shifts it left by one control
        tick, and samples q(x_t | x_0) at the *same* initial NS-DDIM timestep.
        The final horizon position remains fresh.  With no cache this method is
        not called, so the first policy call is bit-identical to the validated reference.
        """
        expected = fresh_noise[:, :-1].shape
        if clean_fifo.shape != expected:
            raise RuntimeError(
                f"NS-DDIM FIFO shape mismatch: expected {expected}, got {clean_fifo.shape}")
        t = initial_t[:-1].to(device=fresh_noise.device, dtype=torch.long)
        alpha = self.alphas_cumprod[t].to(dtype=fresh_noise.dtype).view(1, -1, 1)
        warm = alpha.sqrt() * clean_fifo.to(
            device=fresh_noise.device, dtype=fresh_noise.dtype)
        warm = warm + (1.0 - alpha).clamp_min(0.0).sqrt() * fresh_noise[:, :-1]
        result = fresh_noise.clone()
        result[:, :-1] = warm
        return result

    # ═════════════════════════════════════════════════════════════════════════
    # Hooks — overridable by subclasses (GuidedDiffuseCLoC, DiffuseCPRDP, ...)
    # ═════════════════════════════════════════════════════════════════════════

    def _init_trajectories(self, nobs: torch.Tensor):
        """Return initial noise + projected observations.

        Returns:
            (action_traj, state_traj, nobs_proj)
        """
        B = nobs.shape[0]
        nobs = nobs[:, :self.n_past_steps, :]
        a = self.inference_noise((B, self.horizon, self.action_dim), self.device)
        s = self.inference_noise((B, self.horizon, self.obs_dim), self.device)
        nobs_proj = nobs @ self.emphasis_mat
        return a, s, nobs_proj

    def _apply_classifier_guidance(
        self,
        a_traj: torch.Tensor,
        s_traj: torch.Tensor,
        a_t,
        s_t,
        cond,
        s_t_prev=None,
    ) -> torch.Tensor:
        """Deprecated two-forward classifier-guidance replay.

        Called only when ``classifier_guidance_impl=duplicate_backbone``. It uses
        :class:`WholeBodyGuidance` in classifier mode.

        Subclasses (e.g. ``GuidedDiffuseCLoC``) can override to inject
        additional guidance terms (joystick steering, path following, etc.).

        Returns:
            Modified ``s_traj`` tensor.
        """
        if self.whole_body_guidance is None:
            return s_traj
        if self.whole_body_guidance.guidance_mode != "classifier":
            return s_traj
        with torch.no_grad():
            _, sp = self.predict_x0(
                action_traj=a_traj, state_traj=s_traj,
                action_t=make_timesteps(a_traj.shape[0], a_t, a_traj.device),
                state_t=make_timesteps(s_traj.shape[0], s_t, s_traj.device),
                cond=cond,
            )
        g = self.whole_body_guidance.compute_cost_gradient(sp, self.emphasis_mat_inv)
        z = self.whole_body_guidance.get_zeta(s_t, s_t_prev).to(s_traj.device)
        return s_traj - z[None, :, None] * g

    def _ddim_step(
        self,
        a_traj: torch.Tensor,
        s_traj: torch.Tensor,
        nobs_proj: torch.Tensor,
        step: StepSpec,
        cond,
        **kwargs,
    ):
        """Single DDIM denoising step — dispatches scalar vs. per-position.

        Subclasses can override to inject post-denoising logic (e.g. joystick
        PD in ``GuidedDiffuseCLoC``).
        """
        # Detect per-position vs scalar from the StepSpec
        if isinstance(step.a_t_cur, (int, float)):
            return self.joint_ddim_step(
                a_traj, s_traj, nobs_proj,
                int(step.a_t_cur), int(step.a_t_prev),
                int(step.s_t_cur), int(step.s_t_prev),
                self.ddim_eta, cond=cond, **kwargs,
            )
        else:
            return self.joint_ns_ddim_step(
                a_traj, s_traj, nobs_proj,
                step.a_t_cur, step.a_t_prev,
                step.s_t_cur, step.s_t_prev,
                self.ddim_eta, cond=cond, **kwargs,
            )

    def _apply_post_step_guidance(
        self,
        a_traj: torch.Tensor,
        s_traj: torch.Tensor,
        step: StepSpec,
        cond,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Post-denoising guidance hook — called AFTER each DDIM step.

        Default: no-op.  Override in subclasses to add joystick PD, path
        following, or other guidance that operates on the cleaner x0.
        """
        return a_traj, s_traj

    def _reuse_x0_guided_ddim_step(
        self, a_traj, s_traj, nobs_proj, step, cond,
    ):
        """Apply classifier WBG to one x0 prediction and reuse that NFE."""
        batch, horizon = a_traj.shape[:2]
        state_input = s_traj.clone()
        if not self.no_state_override:
            state_input[:, :self.n_past_steps] = nobs_proj
        a_t = torch.full(
            (batch, horizon), step.a_t_cur,
            device=a_traj.device, dtype=torch.long)
        s_t = torch.full(
            (batch, horizon), step.s_t_cur,
            device=s_traj.device, dtype=torch.long)
        # Match joint_ddim_step exactly: past-state positions carry clean-time
        # embeddings even when no_state_override leaves their values denoised.
        s_t[:, :self.n_past_steps] = 0
        s_prev = torch.full_like(s_t, step.s_t_prev)
        action_pred, state_pred = self.predict_x0(
            a_traj, state_input, a_t, s_t, cond=cond)
        gradient = self.whole_body_guidance.compute_cost_gradient(
            state_pred.float(), self.emphasis_mat_inv.float())
        zeta = self.whole_body_guidance.get_zeta(s_t, s_prev).to(
            device=state_pred.device, dtype=torch.float32)
        guided_state_pred = state_pred.float() - zeta[..., None] * gradient.float()
        return self.joint_ddim_step_from_predictions(
            a_traj, state_input, nobs_proj, step.a_t_cur, step.a_t_prev,
            step.s_t_cur, step.s_t_prev, action_pred, guided_state_pred,
            self.ddim_eta)

    def _reuse_x0_guided_ns_ddim_step(
        self, a_traj, s_traj, nobs_proj,
        a_t_cur, a_t_prev, s_t_cur, s_t_prev, cond,
    ):
        """Guide one x0 prediction and reuse it for one NS-DDIM step."""
        batch = a_traj.shape[0]
        state_input = s_traj.clone()
        if not self.no_state_override:
            state_input[:, :self.n_past_steps] = nobs_proj
        a_t = make_timesteps(batch, a_t_cur, a_traj.device)
        s_t = make_timesteps(batch, s_t_cur, s_traj.device)
        s_prev = make_timesteps(batch, s_t_prev, s_traj.device)
        action_pred, state_pred = self.predict_x0(
            a_traj, state_input, a_t, s_t, cond=cond)
        gradient = self.whole_body_guidance.compute_cost_gradient(
            state_pred.float(), self.emphasis_mat_inv.float())
        zeta = self.whole_body_guidance.get_zeta(s_t, s_prev).to(
            device=state_pred.device, dtype=torch.float32)
        guided_state_pred = state_pred.float() - zeta[..., None] * gradient.float()
        return self.joint_ns_ddim_step_from_predictions(
            a_traj, state_input, nobs_proj,
            a_t_cur, a_t_prev, s_t_cur, s_t_prev,
            action_pred, guided_state_pred, self.ddim_eta)

    def _reuse_x0_guided_ddpm_step(
        self, a_traj, s_traj, nobs_proj, action_t, state_t, cond,
    ):
        """Apply one DDPM update from a single classifier-guided x0 prediction."""
        batch = a_traj.shape[0]
        state_input = s_traj.clone()
        state_t_input = state_t.clone()
        if not self.no_state_override:
            state_input[:, :self.n_past_steps] = nobs_proj
            state_t_input[:self.n_past_steps] = 0

        action_t_b = make_timesteps(batch, action_t, a_traj.device)
        state_t_b = make_timesteps(batch, state_t_input, s_traj.device)
        action_pred, state_pred = self.predict_x0(
            a_traj, state_input, action_t_b, state_t_b, cond=cond)
        gradient = self.whole_body_guidance.compute_cost_gradient(
            state_pred.float(), self.emphasis_mat_inv.float())
        zeta = self.whole_body_guidance.get_zeta(state_t_input, None).to(
            device=state_pred.device, dtype=torch.float32)
        guided_state_pred = state_pred.float() - zeta[None, :, None] * gradient.float()
        action_mu, state_mu, action_logvar, state_logvar = self.mean_var_from_x0(
            action_traj=a_traj,
            state_traj=state_input,
            action_t=action_t_b,
            state_t=state_t_b,
            action_pred=action_pred,
            state_pred=guided_state_pred,
        )
        action_noise = self.inference_noise(
            a_traj.shape, a_traj.device, a_traj.dtype)
        action_noise[action_t_b == 0] = 0
        state_noise = self.inference_noise(
            state_input.shape, state_input.device, state_input.dtype)
        state_noise[state_t_b == 0] = 0
        return (
            action_mu + torch.exp(0.5 * action_logvar) * action_noise,
            state_mu + torch.exp(0.5 * state_logvar) * state_noise,
        )

    def _post_process(self, s_traj: torch.Tensor) -> torch.Tensor:
        """Unproject + apply PD guidance + root_pos_guide (shared by all paths)."""
        s_traj = s_traj @ self.emphasis_mat_inv
        if self.whole_body_guidance is not None and \
           self.whole_body_guidance.guidance_mode == "pd":
            s_unnorm = self.normalizer['obs'].unnormalize(s_traj)
            self.whole_body_guidance.apply(s_unnorm, step=self.denoising_steps - 1)
            s_traj = self.normalizer['obs'].normalize(s_unnorm) @ self.emphasis_mat
        elif self.enable_root_pos_guide and self.root_pos_guide is not None:
            s_traj = self._apply_root_pos_guidance(s_traj)
        return s_traj

    # ═════════════════════════════════════════════════════════════════════════
    # act — orchestrates the hooks above
    # ═════════════════════════════════════════════════════════════════════════

    def act(
        self,
        nobs,
        cond=None,
        **kwargs,
    ):
        """Generate actions with rolling inference and state emphasis projection."""
        self.backbone_call_count = 0
        self._cached_condition_embeddings = None
        if self.cache_condition_encoding and cond is not None:
            if not hasattr(self.backbone, "encode_condition"):
                raise RuntimeError("backbone does not support cached condition encoding")
            self._cached_condition_embeddings = self.backbone.encode_condition(cond)
        a_traj, s_traj, nobs_proj = self._init_trajectories(nobs)

        # ═════════════════════════════════════════════════════════════════
        # DDIM path — three scheduling options
        # ═════════════════════════════════════════════════════════════════
        if self.ddim_steps is not None:
            import time
            T = self.denoising_steps
            _t0 = time.perf_counter()

            # ── Option 1: NS (NoiseScheduler) per-position DDIM ──────────
            if self.use_ns_ddim:
                ns_a = self.action_noise_scheduler
                ns_s = self.state_noise_scheduler
                a_full = ns_a.get_schedule("full")
                s_full = ns_s.get_schedule("full")
                if self.ddim_steps < T:
                    a_idx = ns_a._uniform_indices(len(a_full), self.ddim_steps)
                    a_sub = [a_full[i] for i in a_idx]
                    a_sched = [(tc, a_sub[i + 1][0].clone() if i + 1 < len(a_sub) else tp)
                               for i, (tc, tp) in enumerate(a_sub)]
                    s_idx = ns_s._uniform_indices(len(s_full), self.ddim_steps)
                    s_sub = [s_full[i] for i in s_idx]
                    s_sched = [(tc, s_sub[i + 1][0].clone() if i + 1 < len(s_sub) else tp)
                               for i, (tc, tp) in enumerate(s_sub)]
                else:
                    a_sched = a_full
                    s_sched = s_full

                if self.ns_ddim_fifo:
                    action_cached = hasattr(self, 'action_rolling_traj')
                    state_cached = hasattr(self, 'state_rolling_traj')
                    if action_cached != state_cached:
                        raise RuntimeError("NS-DDIM FIFO has a partial trajectory cache")
                    if action_cached:
                        a_traj = self._ns_ddim_fifo_warm_start(
                            a_traj, self.action_rolling_traj, a_sched[0][0])
                        s_traj = self._ns_ddim_fifo_warm_start(
                            s_traj, self.state_rolling_traj, s_sched[0][0])

                _has_guidance = (
                    self.whole_body_guidance is not None
                    and self.whole_body_guidance.guidance_mode == "classifier"
                )
                for (a_tc, a_tp), (s_tc, s_tp) in zip(a_sched, s_sched):
                    if _has_guidance and self.classifier_guidance_impl == "reuse_x0":
                        a_traj, s_traj = self._reuse_x0_guided_ns_ddim_step(
                            a_traj, s_traj, nobs_proj,
                            a_tc, a_tp, s_tc, s_tp, cond)
                    else:
                        s_traj = self._apply_classifier_guidance(
                            a_traj, s_traj, a_tc, s_tc, cond, s_tp)
                        a_traj, s_traj = self.joint_ns_ddim_step(
                            a_traj, s_traj, nobs_proj,
                            a_tc, a_tp, s_tc, s_tp,
                            self.ddim_eta, cond=cond, **kwargs,
                        )

                if self.ns_ddim_fifo:
                    self.action_rolling_traj = a_traj[:, 1:].detach().clone()
                    self.state_rolling_traj = s_traj[:, 1:].detach().clone()

                _dt = 1000 * (time.perf_counter() - _t0)
                # print(f"[CLoC DDIM-NS] steps={len(a_sched)}, total={_dt:.2f}ms, "
                #       f"per_step={_dt / max(len(a_sched), 1):.2f}ms")

            # ── Option 2: Rolling per-position DDIM ──────────────────────
            elif self.randomize_noise_schedule:
                action_chain: list = []
                state_chain: list = []
                ns_a = self.action_noise_scheduler
                ns_s = self.state_noise_scheduler

                # Always use configured schedules for chain building so that
                # rolling buffer extraction (which also uses configured
                # schedules) can match the columns it expects.
                action_t_all = ns_a.get_denoising_matrix(self.action_schedule)
                if hasattr(self, 'action_rolling_traj'):
                    a_traj[:, :-1] = self.action_rolling_traj

                state_t_all = ns_s.get_denoising_matrix(self.state_schedule, is_state=True)
                if hasattr(self, 'state_rolling_traj'):
                    s_traj[:, :-1] = self.state_rolling_traj

                full_len = len(action_t_all)
                state_len = len(state_t_all)
                # Iterate max(action,state) rows so the warm-start rolling
                # buffer stays full-length (H-1). The action-length iteration
                # leaves the STATE buffer one short on the second call when the
                # state schedule is longer than the action schedule — C++ does
                # the same (see DiffuseCLoCActor::act rolling_ddim branch).
                total_steps = max(full_len, state_len)
                if self.ddim_steps < T:
                    ddim_idx = torch.linspace(0, total_steps - 1, self.ddim_steps).round().long()
                    ddim_idx = sorted({int(i) for i in ddim_idx.tolist()})
                else:
                    ddim_idx = list(range(total_steps))

                prev_action_t = action_t_all[0].clone() + 1
                prev_state_t = state_t_all[0].clone() + 1

                for step_i, full_i in enumerate(ddim_idx):
                    action_t = action_t_all[min(full_i, full_len - 1)]
                    if full_i > state_len - 1:
                        state_t = prev_state_t.clone()
                        zero_pos = torch.nonzero(state_t == 0)
                        if len(zero_pos) > 0:
                            last_zero = zero_pos[-1, -1].item()
                            if last_zero + 1 < state_t.shape[0]:
                                state_t[last_zero + 1:] -= 1
                    else:
                        state_t = state_t_all[full_i]

                    action_chain.append((a_traj.clone(), prev_action_t))
                    state_chain.append((s_traj.clone(), prev_state_t))
                    prev_action_t = action_t.clone()
                    prev_state_t = state_t.clone()

                    a_t_prev = action_t_all[min(full_i + 1, full_len - 1)]
                    s_t_prev = state_t_all[min(full_i + 1, state_len - 1)]
                    if step_i == len(ddim_idx) - 1:
                        a_t_prev = a_t_prev.clone()
                        for endpoint in getattr(
                            self, "_action_selection_clean_endpoints", ()):
                            a_t_prev[endpoint] = -1
                    _has_guidance = (
                        self.whole_body_guidance is not None
                        and self.whole_body_guidance.guidance_mode == "classifier"
                    )
                    if _has_guidance and self.classifier_guidance_impl == "reuse_x0":
                        a_traj, s_traj = self._reuse_x0_guided_ns_ddim_step(
                            a_traj, s_traj, nobs_proj,
                            action_t, a_t_prev, state_t, s_t_prev, cond)
                    else:
                        s_traj = self._apply_classifier_guidance(
                            a_traj, s_traj, action_t, state_t, cond, s_t_prev)
                        a_traj, s_traj = self.joint_ns_ddim_step(
                            a_traj, s_traj, nobs_proj,
                            action_t, a_t_prev, state_t, s_t_prev,
                            self.ddim_eta, cond=cond, **kwargs,
                        )

                # Post-diffusion rolling buffer save
                _last_i = ddim_idx[-1]
                action_chain.append((a_traj.clone(),
                    action_t_all[min(_last_i, full_len - 1)].clone()))
                state_chain.append((s_traj.clone(),
                    state_t_all[min(_last_i, state_len - 1)].clone()))
                action_t_all_new = ns_a.get_denoising_matrix(self.action_schedule)
                self.action_rolling_traj = ns_a.get_rolling_traj(action_chain, action_t_all_new)
                state_t_all_new = ns_s.get_denoising_matrix(self.state_schedule, is_state=True)
                self.state_rolling_traj = ns_s.get_rolling_traj(state_chain, state_t_all_new)

                _dt = 1000 * (time.perf_counter() - _t0)
                print(f"[CLoC DDIM-rolling] steps={len(ddim_idx)}, total={_dt:.2f}ms, "
                      f"per_step={_dt / max(len(ddim_idx), 1):.2f}ms")

            # ── Option 3: Uniform-t DDIM (fast path, default) ────────────
            else:
                schedule = self.action_noise_scheduler.build_uniform_ddim_steps(
                    self.ddim_steps)
                _has_guidance = (
                    self.whole_body_guidance is not None
                    and self.whole_body_guidance.guidance_mode == "classifier"
                )
                for step in schedule:
                    if _has_guidance and self.classifier_guidance_impl == "reuse_x0":
                        a_traj, s_traj = self._reuse_x0_guided_ddim_step(
                            a_traj, s_traj, nobs_proj, step, cond)
                    else:
                        if _has_guidance:
                            _a_t = torch.full((a_traj.shape[1],), step.a_t_cur, device=a_traj.device)
                            _s_t = torch.full((s_traj.shape[1],), step.s_t_cur, device=s_traj.device)
                            _s_t_prev = torch.full_like(_s_t, step.s_t_prev)
                            s_traj = self._apply_classifier_guidance(
                                a_traj, s_traj, _a_t, _s_t, cond, _s_t_prev)
                        a_traj, s_traj = self._ddim_step(
                            a_traj, s_traj, nobs_proj, step, cond, **kwargs)
                    a_traj, s_traj = self._apply_post_step_guidance(
                        a_traj, s_traj, step, cond)

                _dt = 1000 * (time.perf_counter() - _t0)
                print(f"[CLoC DDIM] steps={len(schedule)}, total={_dt:.2f}ms, "
                      f"per_step={_dt / max(len(schedule), 1):.2f}ms")

            s_traj = self._post_process(s_traj)
            return a_traj, s_traj
        # -----------------------------------------------------------------

        # ═════════════════════════════════════════════════════════════════
        # DDPM path (only reached when ddim_steps is None)
        # ═════════════════════════════════════════════════════════════════
        action_chain = []
        state_chain = []

        if self.randomize_noise_schedule:
            # Always use configured schedules for chain building so that
            # rolling buffer extraction (which also uses configured
            # schedules) can match the columns it expects.
            action_t_all = self.generate_denoising_matrix(self.action_schedule)
            if hasattr(self, 'action_rolling_traj'):
                a_traj[:, :-1] = self.action_rolling_traj

            state_t_all = self.generate_denoising_matrix(self.state_schedule, is_state=True)
            if hasattr(self, 'state_rolling_traj'):
                s_traj[:, :-1] = self.state_rolling_traj
        else:
            action_t_all = self.generate_denoising_matrix("full")
            state_t_all = self.generate_denoising_matrix("full", is_state=True)

        prev_action_t = action_t_all[0].clone() + 1
        prev_state_t = state_t_all[0].clone() + 1
        nobs = nobs_proj  # already projected above

        total_steps = max(len(action_t_all), len(state_t_all))
        for i in range(total_steps):
            action_t = action_t_all[min(i, len(action_t_all)-1)]
            if i == total_steps - 1:
                action_t = action_t.clone()
                for endpoint in getattr(
                    self, "_action_selection_clean_endpoints", ()):
                    action_t[endpoint] = 0
            if i > len(state_t_all)-1:
                state_t = prev_state_t.clone()
                state_t[torch.nonzero(state_t==0)[-1,-1]+1:] -= 1
            else:
                state_t = state_t_all[i]

            if self.randomize_noise_schedule:
                action_chain.append((a_traj.clone(), prev_action_t))
                state_chain.append((s_traj.clone(), prev_state_t))
            prev_action_t = action_t.clone()
            prev_state_t = state_t.clone()

            a_traj, s_traj = self.diffuse_step(
                nobs=nobs,
                action_traj=a_traj,
                state_traj=s_traj,
                action_t=action_t,
                state_t=state_t,
                i=i,
                cond=cond,
                **kwargs,
            )

        if self.randomize_noise_schedule:
            action_chain.append((a_traj.clone(), action_t.clone()))
            state_chain.append((s_traj.clone(), state_t.clone()))

            action_t_all = self.generate_denoising_matrix(self.action_schedule)
            self.action_rolling_traj = self.get_rolling_traj(action_chain, action_t_all)
            state_t_all = self.generate_denoising_matrix(self.state_schedule, is_state=True)
            self.state_rolling_traj = self.get_rolling_traj(state_chain, state_t_all)

        # -----------------------------------------------------------------

        s_traj = s_traj @ self.emphasis_mat_inv

        return a_traj, s_traj

    def p_mean_var(
        self,
        action_traj,
        action_t,
        state_traj,
        state_t,
        index=None,
        cond=None,
    ):
        """Identical to parent, no modifications needed except cond pass-through."""

        action_pred, state_pred = self.predict_x0(
            action_traj=action_traj,
            state_traj=state_traj,
            action_t=action_t,
            state_t=state_t,
            cond=cond,
        )


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
        Apply state emphasis before computing loss in projected space.
        
        Args:
            action_traj: (B, H, Da) - Actions (B, 20, 29)
            state_traj: (B, H, Do) - States (B, 20, 384)
            cond: (B, T_cond, cond_dim) - Optional condition (e.g., motion latent)
            
        Returns:
            Same as JointDiffusionActor.p_losses
        """
        state_traj = state_traj @ self.emphasis_mat
        return super().p_losses(
            action_traj,
            state_traj,
            cond=cond,
            return_loss_components=return_loss_components,
        )


# -------------------------------- HELPER FUNCTIONS -----------------------------------------

    def get_rolling_traj(self, chain, t_all):
        """
        Extract rolling buffer from denoising chain based on noise schedule.
        Maintains FIFO buffer of partially denoised trajectories.
        
        Args:
            chain: List[(traj, t)] - Denoising history
                   traj: (B, H, D), t: (H,)
            t_all: (K, H) - Target noise schedule
            
        Returns:
            rolled_traj: (B, H-1, D) - Partially denoised trajectories for next step
        """
        traj = torch.stack([c[0] for c in chain], dim=1)[:,:,1:,:] # shape = (B,K,T,A_dim) K = denoising_length
        idx = torch.stack([c[1] for c in chain])[:,1:] # shape = (K,T)
        needed_idx = t_all[0,:-1] + 1
        mask = idx == needed_idx
        mask = torch.logical_xor(mask, (mask.roll(-1,0) == mask) & (mask))
        traj = traj[:,mask]
        return traj
    
    def generate_denoising_matrix(self, schedule, is_state=False, **kwargs):
        """
        Generate noise schedule matrix for flexible denoising patterns.
        
        Args:
            schedule: str - Schedule type ('full', 'full_decreasing', 'from_xT_decreasing', 'from_xT_step')
            is_state: bool - Whether schedule is for states (affects n_future_steps)
            
        Returns:
            t_all: (K, H) - Noise levels per (iteration, position)
            
        Examples for the decreasing_matrix: https://github.com/user-attachments/assets/965ef0a1-049a-446c-8912-22e8cbc50e7b
        """
        
        def decreasing_matrix(start_value, is_state, step_size=1, all_clear=False):
            """
            Create decreasing noise schedule matrix.
            
            Args:
                start_value: int - Starting noise level
                is_state: bool - Affects horizon calculation
                step_size: int - Decrement step size
                
            Returns:
                matrix: (K, H) - Noise schedule
                n: int - Padding size
            """
            if step_size == 1:
                if is_state:
                    end = start_value + self.n_future_steps
                else:
                    end = start_value + self.n_future_steps + 1
            else:
                end = self.denoising_steps + step_size
                
            first_row = torch.arange(start_value, end, step_size)
            # if all_clear:
            #     # first_row = torch.arange(end-1, start_value-1, -1)
            #     m = end
            m = start_value + 1
            decrement_column = -torch.arange(m).view(m, 1)
            
            # Broadcast the first row and decrement_column to generate the entire matrix
            action_t_all = first_row + decrement_column
            action_t_all = torch.clip(action_t_all, 0, self.denoising_steps - 1)
            n = self.horizon - action_t_all.shape[1]
            return action_t_all, n
        
        if schedule == "full":
            action_t_all = torch.flip(torch.arange(self.denoising_steps), dims=(0,))
            action_t_all = action_t_all.unsqueeze(1).repeat(1, self.horizon)
        elif schedule == "full_decreasing":
            action_t_all, n = decreasing_matrix(self.denoising_steps - 1, is_state=is_state)
            action_t_all = torch.cat([action_t_all[:,0:1].repeat(1,n), action_t_all], dim=-1)
        elif "from_xT_decreasing" in schedule:
            if is_state:
                start = max(self.denoising_steps - self.n_future_steps, 0)
            else:
                start = max(self.denoising_steps - 8 - 1, 0)
            action_t_all, n = decreasing_matrix(start, is_state=is_state, **kwargs)
            action_t_all = torch.cat([action_t_all[:,0:1].repeat(1,n), action_t_all], dim=-1)
        elif "from_xT_step" in schedule:
            # if is_state:
            #     start = max(self.denoising_steps - self.n_past_steps-1, 0)
            # else:
            #     start = max(self.denoising_steps - self.n_past_steps-1, 0)
            # action_t_all, n = decreasing_matrix(start, is_state=is_state, **kwargs)
            # action_t_all = torch.cat([action_t_all[:,0:1].repeat(1,n), action_t_all], dim=-1)
            start = 14
            action_t_all, n = decreasing_matrix(start, is_state=is_state, step_size=10, **kwargs)
            action_t_all = torch.cat([action_t_all[:,0:1].repeat(1,n), action_t_all], dim=-1)
        return action_t_all

    def get_emphasis_projection(self):
        """Build emphasis_mat and register it (plus its pseudoinverse) as model buffers.

        If a data_profile is provided (str profile name, path, or dict), uses
        EmphMatGen.build() with the full profile for config-driven construction.
        Otherwise falls back to EmphMatGen.build_from_mode() with the legacy
        state_emphasis string for backward compatibility.
        """
        from diffusion_policy.dataset.g1_dataset import EmphMatGen, DataProfile
        from diffusion_policy.dataset.state_emph import build_profile_emphasis_projection
        state_dim = self.backbone.x_output_dim

        if self.data_profile is not None:
            profile = DataProfile.from_yaml(self.data_profile)
            obs_reflect_op = None  # random_symm needs it; build will raise if needed but missing
            emphasis_mat = build_profile_emphasis_projection(
                profile,
                self.device,
                obs_reflect_op,
                seed=self.emphasis_projection_seed,
            )
        else:
            emphasis_mat = EmphMatGen.build_from_mode(self.state_emphasis, state_dim, self.device)

        self.register_buffer('emphasis_mat', emphasis_mat)
        self.register_buffer('emphasis_mat_inv', torch.linalg.pinv(emphasis_mat))

    # ------------------------------------------------------------------
    # Root-index discovery from the data profile
    # ------------------------------------------------------------------

    def _compute_root_indices(self):
        """Walk observation terms to find root_pos_local, pelvis, and root_lin_vel slices.

        When *data_profile* is provided, the indices are derived from the
        ordered observation term list.  Otherwise the defaults (standard
        G1 192-d FK layout: root at 180:183, pelvis at 0:3) are kept.
        """
        if self.data_profile is None:
            return  # keep the G1 192-d defaults set in __init__

        from diffusion_policy.dataset.g1_dataset import DataProfile
        from diffusion_policy.dataset.term_compose import TERM_DIMS, _init_term_dims

        if TERM_DIMS.get("joint_pos") is None:
            _init_term_dims()

        profile = DataProfile.from_yaml(self.data_profile)
        idx = 0
        root_found = False
        for term in profile.observation.terms:
            dim = TERM_DIMS.get(term)
            if dim is None:
                dim = 3  # fallback for terms not in static registry
            if term == "root_pos_local":
                self._root_slice = (idx, idx + dim)
                root_found = True
            elif term == "body_pos_local":
                # Pelvis is body index 0 → first 3 dims of body_pos_local
                self._pelvis_body_slice = (idx, idx + 3)
            elif term == "root_lin_vel_local":
                self._root_vel_slice = (idx, idx + dim)
            idx += dim

        if not root_found:
            raise ValueError(
                f"enable_root_pos_guide=True but observation terms "
                f"{profile.observation.terms} do not include 'root_pos_local'."
            )

    # ------------------------------------------------------------------
    # Root-position guidance helpers
    # ------------------------------------------------------------------

    def _apply_root_pos_guidance(self, state_norm: torch.Tensor) -> torch.Tensor:
        """Apply root_pos_guidance to a normalised (post-emphasis_inv) state.

        Args:
            state_norm: [B, H, D] — state trajectory in normalised original space.

        Returns:
            state_norm with root_pos_local (and pelvis when present) steered
            toward the GUI-commanded target, and root_lin_vel_local steered
            toward the commanded velocity.
        """
        if not (self.enable_root_pos_guide and self.root_pos_guide is not None):
            return state_norm

        rs, re = self._root_slice
        root_norm = state_norm[:, :, rs:re]                       # [B, H, 3]
        last_root_norm = root_norm[:, self.n_past_steps - 1, :]   # [B, 3]

        normalizer_obs = self.normalizer['obs']
        norm_scale = normalizer_obs.params_dict['scale']
        norm_offset = normalizer_obs.params_dict['offset']

        is_multi_term = (norm_scale.shape[0] != root_norm.shape[-1])
        if is_multi_term:
            last_root_unnorm = (last_root_norm - norm_offset[rs:re]) / norm_scale[rs:re]
            norm_slice = (rs, re)
        else:
            last_root_unnorm = normalizer_obs.unnormalize(last_root_norm)
            norm_slice = None

        root_guided = self.root_pos_guide.apply_guidance(
            root_norm, last_root_unnorm,
            normalizer=normalizer_obs,
            norm_slice=norm_slice,
        )

        delta = root_guided - root_norm                        # [B, H, 3]
        state_norm[:, :, rs:re] = root_guided

        if self._pelvis_body_slice is not None:
            ps, pe = self._pelvis_body_slice
            state_norm[:, :, ps:pe] = state_norm[:, :, ps:pe] + delta

        # Velocity guidance for root_lin_vel_local
        if self._root_vel_slice is not None:
            vs, ve = self._root_vel_slice
            vel_norm = state_norm[:, :, vs:ve]                     # [B, H, 3]
            last_vel_norm = vel_norm[:, self.n_past_steps - 1, :]  # [B, 3]

            if is_multi_term:
                last_vel_unnorm = (last_vel_norm - norm_offset[vs:ve]) / norm_scale[vs:ve]
                vel_norm_slice = (vs, ve)
            else:
                last_vel_unnorm = normalizer_obs.unnormalize(last_vel_norm)
                vel_norm_slice = None

            vel_guided = self.root_pos_guide.apply_vel_guidance(
                vel_norm, last_vel_unnorm,
                normalizer=normalizer_obs,
                norm_slice=vel_norm_slice,
            )
            state_norm[:, :, vs:ve] = vel_guided

        return state_norm

    # ------------------------------------------------------------------
    # Override diffuse_step to inject root_pos_local PD guidance
    # ------------------------------------------------------------------

    def diffuse_step(self, nobs, action_traj, state_traj, action_t, state_t, i, **kwargs):
        """Single reverse diffuse step with optional guidance.

        Classifier mode: guide the step's single x0 prediction before sampling.
        PD mode (legacy): PD correction on clean x0 AFTER denoising.
        """
        has_classifier_guidance = (
            self.whole_body_guidance is not None
            and self.whole_body_guidance.guidance_mode == "classifier"
        )
        if has_classifier_guidance and self.classifier_guidance_impl == "reuse_x0":
            action_traj_pred, state_traj_pred = self._reuse_x0_guided_ddpm_step(
                action_traj, state_traj, nobs, action_t, state_t,
                kwargs.get("cond"))
        else:
            # Explicit historical replay applies guidance to the noisy state,
            # then executes the backbone again inside the denoising step.
            if has_classifier_guidance:
                # predict_x0 returns (action_pred, state_pred).
                with torch.no_grad():
                    _, state_pred = self.predict_x0(
                        action_traj=action_traj, state_traj=state_traj,
                        action_t=make_timesteps(action_traj.shape[0], action_t, action_traj.device),
                        state_t=make_timesteps(state_traj.shape[0], state_t, state_traj.device),
                        cond=kwargs.get('cond'),
                    )
                grad_proj = self.whole_body_guidance.compute_cost_gradient(
                    state_pred, self.emphasis_mat_inv)
                zeta = self.whole_body_guidance.get_zeta(state_t).to(state_traj.device)
                state_traj = state_traj - zeta[None, :, None] * grad_proj

            action_traj_pred, state_traj_pred = super().diffuse_step(
                nobs=nobs,
                action_traj=action_traj,
                state_traj=state_traj,
                action_t=action_t,
                state_t=state_t,
                i=i,
                **kwargs,
            )

        # ── Whole-body guidance (legacy PD mode) ──
        if self.whole_body_guidance is not None and \
           self.whole_body_guidance.guidance_mode == "pd":
            state_norm = state_traj_pred @ self.emphasis_mat_inv
            state_unnorm = self.normalizer['obs'].unnormalize(state_norm)
            self.whole_body_guidance.apply(state_unnorm, step=i)
            state_norm = self.normalizer['obs'].normalize(state_unnorm)
            state_traj_pred = state_norm @ self.emphasis_mat
            return action_traj_pred, state_traj_pred

        # ── Legacy root-position guidance ──
        if self.enable_root_pos_guide and self.root_pos_guide is not None:
            state_norm = state_traj_pred @ self.emphasis_mat_inv
            state_norm = self._apply_root_pos_guidance(state_norm)
            state_traj_pred = state_norm @ self.emphasis_mat

        return action_traj_pred, state_traj_pred

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def set_normalizer(self, normalizer):
        """Forward normalizer to parent and to WholeBodyGuidance for grad computation."""
        super().set_normalizer(normalizer)
        if self.whole_body_guidance is not None:
            try:
                self.whole_body_guidance.set_normalizer(normalizer)
            except Exception:
                pass  # normalizer may not be fully set up yet

    def __del__(self):
        """Stop the root_pos_guide GUI thread on destruction."""
        guide = getattr(self, "root_pos_guide", None)
        if guide is not None:
            try:
                guide.stop()
            except Exception:
                pass
