from __future__ import annotations

import torch
import torch.nn.functional as F

from diffusion_policy.backbone.base_backbone import ConditionalSeqBackbone
from diffusion_policy.modules.base_actor import BaseActor


class TransActor(BaseActor):
    """MDP-style actor using a TransformerMDP backbone.

    Predicts a full action trajectory directly from past observations and
    optional motion conditioning (e.g. CLIP latent).  No diffusion loop —
    a single forward pass through the backbone produces the output.

    This actor follows the same interface as DiffusionActor so that it can
    be dropped into BCAgent and cond_eval.py without changes:
    - ``act(nobs, cond)``         → used at inference time
    - ``p_losses(trajectory, cond, motion_cond)`` → used during training

    Args:
        backbone: A TransformerMDP (ConditionalSeqBackbone) instance.
    """

    backbone: ConditionalSeqBackbone

    def __init__(self, backbone: ConditionalSeqBackbone, **kwargs):
        super().__init__(backbone=backbone, **kwargs)

        self.obs_dim = backbone.x_input_dim
        self.action_dim = backbone.x_output_dim
        self.n_past_steps = backbone.n_cond_steps  # read by bc_agent.py
        self.horizon = backbone.horizon

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def act(self, nobs: torch.Tensor, cond=None) -> torch.Tensor:
        """Predict action trajectory from past observations.

        Args:
            nobs: (B, T, obs_dim) - Past observations (will be sliced to
                  n_past_steps).
            cond: (B, T_cond, cond_dim) or dict - Optional motion latent
                  (e.g. from MotionCLIP).  Forwarded directly to backbone.

        Returns:
            action_traj: (B, horizon, action_dim) - Predicted actions.
        """
        nobs = nobs[:, :self.n_past_steps]
        return self.backbone(nobs, cond=cond)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def p_losses(
        self,
        trajectory: torch.Tensor,
        cond: torch.Tensor,
        motion_cond=None,
    ) -> torch.Tensor:
        """Compute MSE loss between predicted and target action trajectory.

        Args:
            trajectory:  (B, horizon, action_dim) - Ground-truth actions.
            cond:        (B, n_past, obs_dim) - Past observations used as
                         backbone input (x_input).
            motion_cond: (B, T_cond, cond_dim) or dict - Optional motion
                         latent forwarded to the backbone as ``cond``.

        Returns:
            loss: scalar MSE loss.
        """
        pred = self.backbone(cond, cond=motion_cond)
        return F.mse_loss(pred, trajectory, reduction="mean")
