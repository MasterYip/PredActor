from __future__ import annotations

import torch
from diffusion_policy.modules.diffuse_cloc import DiffuseCLoC

try:
    from diffusion_policy.task_provider.root_pos_guide import RootPosGuideProvider
except ImportError:
    RootPosGuideProvider = None


class DiffuseCPRDP(DiffuseCLoC):
    """DiffuseCLoC with GUI-driven root_pos_local guidance for PRDP profiles.

    Designed for profiles where the co-diffused state (x-stream) includes
    root_pos_local among its observation terms.  At each diffuse step the
    predicted root position (and pelvis in body_pos_local when present) is
    steered toward a target derived from velocity commands provided via an
    interactive tkinter GUI.

    Supports two profile families:

    *g1_prdp_rootpos* (3-d, backward compatible)
        observation: [root_pos_local]  — 3-d, same-type emphasis
        The entire x-stream IS root_pos_local.

    *g1_prdp_pos* (183-d base, random_symm → 366-d projected)
        observation: [root_pos_local, body_pos_local, body_lin_vel_local]
        Root-position guidance is applied to:
          - root_pos_local term (indices 0:3 in normalised space)
          - pelvis body-pos  (indices 3:6 in normalised space, body index 0)
        The same delta is applied to both so the pelvis follows the root.

    When *enable_root_pos_guide* is False this class is identical to
    DiffuseCLoC and has zero run-time overhead.
    """

    def __init__(self, enable_root_pos_guide: bool = False, **kwargs):
        super().__init__(**kwargs)

        self.enable_root_pos_guide: bool = enable_root_pos_guide
        self.root_pos_guide = None  # RootPosGuideProvider | None

        # Slice of root-related observation dimensions in the *normalised*
        # (post-emphasis_inv) state vector.  Computed from the data profile
        # so the same class works for g1_prdp_rootpos (3-d) and g1_prdp_pos
        # (183-d multi-term).
        self._root_slice = (0, 3)           # (start, end) for root_pos_local term
        self._pelvis_body_slice = None       # (start, end) for pelvis in body_pos_local
        self._root_vel_slice = None          # (start, end) for root_lin_vel_local term

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

    # ------------------------------------------------------------------
    # Root-index discovery from the data profile
    # ------------------------------------------------------------------

    def _compute_root_indices(self):
        """Walk the observation terms to find root_pos_local, pelvis, and root_lin_vel slices."""
        if self.data_profile is None:
            return  # legacy mode — assume full state is root_pos_local

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
    # Override diffuse_step to apply root_pos_local PD guidance
    # ------------------------------------------------------------------

    def diffuse_step(self, nobs, action_traj, state_traj, action_t, state_t, i, **kwargs):
        """Single reverse diffuse step with optional root_pos_local guidance.

        Args:
            nobs:         (B, n_past, obs_dim_proj) — clean past obs in projected space.
            action_traj:  (B, H, action_dim)        — current noisy actions.
            state_traj:   (B, H, obs_dim_proj)      — current noisy states in projected space.
            action_t, state_t, i: noise-schedule arguments passed to super().
            **kwargs: forwarded to super().

        Returns:
            action_traj_pred: (B, H, action_dim)
            state_traj_pred:  (B, H, obs_dim_proj)  — guided state prediction.
        """
        action_traj_pred, state_traj_pred = super().diffuse_step(
            nobs=nobs,
            action_traj=action_traj,
            state_traj=state_traj,
            action_t=action_t,
            state_t=state_t,
            i=i,
            **kwargs,
        )

        if not (self.enable_root_pos_guide and self.root_pos_guide is not None):
            return action_traj_pred, state_traj_pred

        # ---------------------------------------------------------------
        # Step 1: invert emphasis → normalised observation [B, H, D]
        #
        # For g1_prdp_rootpos (same type, 3-d):  state_norm is [B, H, 3]
        # For g1_prdp_pos (random_symm, 366→183): state_norm is [B, H, 183]
        # ---------------------------------------------------------------
        state_norm = state_traj_pred @ self.emphasis_mat_inv

        # ---------------------------------------------------------------
        # Step 2: extract root_pos_local slice from normalised state
        # ---------------------------------------------------------------
        rs, re = self._root_slice
        root_norm = state_norm[:, :, rs:re]                     # [B, H, 3]

        # ---------------------------------------------------------------
        # Step 3: derive "current" root position from last inpainted past step
        # ---------------------------------------------------------------
        last_root_norm = root_norm[:, self.n_past_steps - 1, :]       # [B, 3]

        normalizer_obs = self.normalizer['obs']
        norm_scale = normalizer_obs.params_dict['scale']
        norm_offset = normalizer_obs.params_dict['offset']

        is_multi_term = (norm_scale.shape[0] != root_norm.shape[-1])
        if is_multi_term:
            # Multi-term normalizer — extract only the root-position dims
            last_root_unnorm = (last_root_norm - norm_offset[rs:re]) / norm_scale[rs:re]
            norm_slice = (rs, re)
        else:
            # Backward-compatible: normalizer covers only root_pos_local
            last_root_unnorm = normalizer_obs.unnormalize(last_root_norm)
            norm_slice = None

        # ---------------------------------------------------------------
        # Step 4: apply PD guidance to root position
        # ---------------------------------------------------------------
        root_guided = self.root_pos_guide.apply_guidance(
            root_norm, last_root_unnorm,
            normalizer=normalizer_obs,
            norm_slice=norm_slice,
        )

        # ---------------------------------------------------------------
        # Step 5: apply delta to root_pos_local and (when present) pelvis
        # ---------------------------------------------------------------
        delta = root_guided - root_norm                          # [B, H, 3]
        state_norm[:, :, rs:re] = root_guided

        if self._pelvis_body_slice is not None:
            ps, pe = self._pelvis_body_slice
            state_norm[:, :, ps:pe] = state_norm[:, :, ps:pe] + delta

        # ---------------------------------------------------------------
        # Step 5b: apply velocity guidance to root_lin_vel_local
        # ---------------------------------------------------------------
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

        # ---------------------------------------------------------------
        # Step 6: re-project with emphasis
        # ---------------------------------------------------------------
        state_traj_pred = state_norm @ self.emphasis_mat

        return action_traj_pred, state_traj_pred
