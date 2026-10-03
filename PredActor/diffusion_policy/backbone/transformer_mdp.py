from typing import Optional, Tuple
import logging
import torch
import torch.nn as nn
from diffusion_policy.backbone.base_backbone import ConditionalSeqBackbone

logger = logging.getLogger(__name__)


class TransformerMDP(ConditionalSeqBackbone):
    """Transformer backbone for next-action prediction (no diffusion noise).

    Encodes past observation tokens as memory, then decodes a fixed-length
    sequence of action tokens using learned query parameters (DETR-style).
    Optional external conditioning (e.g. CLIP motion latent) is concatenated
    with the observation tokens before encoding.

    Interface mirrors Transformer (diffusion backbone) except there is no
    ``timesteps`` argument — this backbone is used by TransActor (MDP-style
    policy) that predicts clean actions directly.

    Args:
        n_layer:           Number of Transformer decoder layers.
        n_head:            Number of attention heads.
        n_emb:             Embedding dimension.
        p_drop_emb:        Dropout on token embeddings.
        p_drop_attn:       Dropout in attention.
        n_cond_layers:     Number of Transformer encoder layers (≥1 recommended).

    Inherited from ConditionalSeqBackbone (via SequentialBackbone / BaseBackbone):
        x_input_dim  = obs_dim       (per-step observation feature size)
        x_output_dim = action_dim    (per-step action output size)
        x_horizon    = action_horizon (number of output action timesteps)
        n_cond_steps = n_obs_steps   (number of past observation tokens)
        cond_dim     = motion latent dim (0 or None = no external conditioning)
    """

    def __init__(
        self,
        n_layer: int = 4,
        n_head: int = 4,
        n_emb: int = 256,
        p_drop_emb: float = 0.1,
        p_drop_attn: float = 0.1,
        n_cond_layers: int = 4,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        T_out = self.horizon        # number of action output tokens
        T_obs = self.n_cond_steps  # number of past obs tokens
        obs_dim = self.x_input_dim
        act_dim = self.x_output_dim
        cond_dim = self.cond_dim if self.cond_dim else 0

        # --- Observation embedding ------------------------------------------
        self.obs_emb = nn.Linear(obs_dim, n_emb)
        self.obs_pos_emb = nn.Parameter(torch.zeros(1, T_obs, n_emb))

        # --- External conditioning embedding (optional) ---------------------
        self.has_cond = cond_dim > 0
        if self.has_cond:
            self.cond_emb = nn.Linear(cond_dim, n_emb)
            self.cond_pos_emb = nn.Parameter(torch.zeros(1, 1, n_emb))
        else:
            self.cond_emb = None
            self.cond_pos_emb = None

        self.drop = nn.Dropout(p_drop_emb)

        # --- Encoder (processes obs + optional external cond) ---------------
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=n_emb,
            nhead=n_head,
            dim_feedforward=4 * n_emb,
            dropout=p_drop_attn,
            activation='gelu',
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_cond_layers)

        # --- Learned action query tokens (DETR-style) -----------------------
        self.action_queries = nn.Parameter(torch.zeros(1, T_out, n_emb))

        # --- Decoder (action queries cross-attend to encoder memory) --------
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=n_emb,
            nhead=n_head,
            dim_feedforward=4 * n_emb,
            dropout=p_drop_attn,
            activation='gelu',
            batch_first=True,
            norm_first=True,
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=n_layer)

        # --- Output head ----------------------------------------------------
        self.ln_f = nn.LayerNorm(n_emb)
        self.head = nn.Linear(n_emb, act_dim)

        self.T_out = T_out
        self.T_obs = T_obs

        self.apply(self._init_weights)
        logger.info(
            "TransformerMDP parameters: %e", sum(p.numel() for p in self.parameters())
        )

    # ------------------------------------------------------------------
    # Weight initialisation
    # ------------------------------------------------------------------

    def _init_weights(self, module):
        ignore_types = (
            nn.Dropout,
            nn.TransformerEncoderLayer,
            nn.TransformerDecoderLayer,
            nn.TransformerEncoder,
            nn.TransformerDecoder,
            nn.ModuleList,
            nn.Mish,
            nn.Sequential,
        )
        if isinstance(module, (nn.Linear, nn.Embedding)):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.MultiheadAttention):
            for name in ['in_proj_weight', 'q_proj_weight', 'k_proj_weight', 'v_proj_weight']:
                weight = getattr(module, name)
                if weight is not None:
                    torch.nn.init.normal_(weight, mean=0.0, std=0.02)
            for name in ['in_proj_bias', 'bias_k', 'bias_v']:
                bias = getattr(module, name)
                if bias is not None:
                    torch.nn.init.zeros_(bias)
        elif isinstance(module, nn.LayerNorm):
            torch.nn.init.zeros_(module.bias)
            torch.nn.init.ones_(module.weight)
        elif isinstance(module, TransformerMDP):
            torch.nn.init.normal_(module.obs_pos_emb, mean=0.0, std=0.02)
            torch.nn.init.normal_(module.action_queries, mean=0.0, std=0.02)
            if module.cond_pos_emb is not None:
                torch.nn.init.normal_(module.cond_pos_emb, mean=0.0, std=0.02)
        elif isinstance(module, ignore_types):
            pass
        else:
            raise RuntimeError("Unaccounted module {}".format(module))

    # ------------------------------------------------------------------
    # Optimizer setup
    # ------------------------------------------------------------------

    def get_optim_groups(self, weight_decay: float = 1e-3):
        decay = set()
        no_decay = set()
        whitelist = (torch.nn.Linear, torch.nn.MultiheadAttention)
        blacklist = (torch.nn.LayerNorm, torch.nn.Embedding)
        for mn, m in self.named_modules():
            for pn, p in m.named_parameters():
                fpn = "%s.%s" % (mn, pn) if mn else pn
                if pn.endswith("bias") or pn.startswith("bias"):
                    no_decay.add(fpn)
                elif pn.endswith("weight") and isinstance(m, whitelist):
                    decay.add(fpn)
                elif pn.endswith("weight") and isinstance(m, blacklist):
                    no_decay.add(fpn)

        no_decay.add("obs_pos_emb")
        no_decay.add("action_queries")
        no_decay.add("_dummy_variable")
        if self.cond_pos_emb is not None:
            no_decay.add("cond_pos_emb")

        param_dict = {pn: p for pn, p in self.named_parameters()}
        inter_params = decay & no_decay
        union_params = decay | no_decay
        assert len(inter_params) == 0, \
            "parameters %s made it into both decay/no_decay sets!" % str(inter_params)
        assert len(param_dict.keys() - union_params) == 0, \
            "parameters %s were not separated into either decay/no_decay set!" % str(
                param_dict.keys() - union_params)

        return [
            {"params": [param_dict[pn] for pn in sorted(decay)], "weight_decay": weight_decay},
            {"params": [param_dict[pn] for pn in sorted(no_decay)], "weight_decay": 0.0},
        ]

    def configure_optimizers(
        self,
        learning_rate: float = 1e-4,
        weight_decay: float = 1e-3,
        betas: Tuple[float, float] = (0.9, 0.95),
    ):
        return torch.optim.AdamW(
            self.get_optim_groups(weight_decay=weight_decay),
            lr=learning_rate,
            betas=betas,
        )

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------

    def forward(
        self,
        x_input: torch.Tensor,
        cond: Optional[torch.Tensor] = None,
        **kwargs,
    ) -> torch.Tensor:
        """Encode past observations and decode action predictions.

        Args:
            x_input: (B, n_obs_steps, obs_dim) - Past observations.
            cond:    (B, T_cond, cond_dim) or dict {'obs': ..., 'motion': ...}
                     Optional external conditioning (e.g. CLIP motion latent).
                     When a dict is passed, 'motion' is used as external cond.

        Returns:
            actions: (B, horizon, action_dim) - Predicted action trajectory.
        """
        B = x_input.shape[0]

        # Embed observations
        obs_tokens = self.drop(self.obs_emb(x_input) + self.obs_pos_emb[:, :x_input.shape[1]])

        # Embed external conditioning if present
        if cond is not None and self.has_cond:
            if isinstance(cond, dict):
                motion = cond.get('motion', None)
            else:
                motion = cond

            if motion is not None:
                # motion: (B, T_m, cond_dim) or (B, 1, cond_dim)
                motion_emb = self.drop(
                    self.cond_emb(motion) +
                    self.cond_pos_emb[:, :motion.shape[1]]
                )
                memory_tokens = torch.cat([obs_tokens, motion_emb], dim=1)
            else:
                memory_tokens = obs_tokens
        else:
            memory_tokens = obs_tokens

        # Encode
        memory = self.encoder(memory_tokens)  # (B, T_obs [+ T_cond], n_emb)

        # Decode with learned action queries
        queries = self.action_queries.expand(B, -1, -1)  # (B, T_out, n_emb)
        x = self.decoder(tgt=queries, memory=memory)      # (B, T_out, n_emb)

        # Project to action space
        x = self.ln_f(x)
        x = self.head(x)  # (B, horizon, action_dim)
        return x
