from __future__ import annotations

from typing import Union, Optional, Tuple
import logging
import torch
import torch.nn as nn
from diffusion_policy.backbone.positional_embedding import SinusoidalPosEmb
from diffusion_policy.backbone.base_backbone import JointSeqBackbone

logger = logging.getLogger(__name__)

class Transformer(JointSeqBackbone):
    def __init__(self,
            n_layer: int = 6,
            n_head: int = 8,
            n_emb: int = 256,
            p_drop_emb: float = 0.1,
            p_drop_attn: float = 0.1,
            causal_attn: bool=True,
            cond_causal_attn: bool=True,
            n_cond_layers: int = 0,
            n_cond_steps: int = 1,
            x_to_x_attn: str='full',
            x_to_y_attn: str='full',
            y_to_x_attn: str='full',
            y_to_y_attn: str='full',
            cond_dim: int = 0,
            n_past_steps: int = 4,
            cross_attn_window: int | None = None,
            cross_attn_mode: str = "full",  # "full" | "state" | "action" | "no_attn"
            attention_mask_type: str = "float",
            **kwargs
        ) -> None:
        super().__init__(
            **kwargs 
        )

        # compute number of tokens for main trunk and condition encoder
        self.n_emb = n_emb
        self.cond_dim = cond_dim
        self.n_cond_steps = n_cond_steps
        if attention_mask_type not in ("float", "bool"):
            raise ValueError("attention_mask_type must be float or bool")
        self.attention_mask_type = attention_mask_type
    
        self.x_emb = nn.Linear(self.x_input_dim, n_emb//4 * 3)
        self.y_emb = nn.Linear(self.y_input_dim, n_emb//4 * 3)

        self.pos_emb = nn.Parameter(torch.zeros(1, self.horizon*2, n_emb))
        self.drop = nn.Dropout(p_drop_emb)

        # time embedding
        self.time_emb = SinusoidalPosEmb(n_emb//4)
        
        # cond encoder (optional)
        self.cond_obs_emb = None
        self.cond_pos_emb = None
        self.encoder = None
        self.decoder = None
        encoder_only = False
        
        if self.cond_dim > 0:
            # Conditioning is enabled - use encoder-decoder architecture
            self.cond_obs_emb = nn.Linear(self.cond_dim, n_emb)
            self.cond_pos_emb = nn.Parameter(torch.zeros(1, n_cond_steps, n_emb))  # Temporal condition support
            
            if n_cond_layers > 0:
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=n_emb,
                    nhead=n_head,
                    dim_feedforward=4*n_emb,
                    dropout=p_drop_attn,
                    activation='gelu',
                    batch_first=True,
                    norm_first=True
                )
                self.encoder = nn.TransformerEncoder(
                    encoder_layer=encoder_layer,
                    num_layers=n_cond_layers
                )
            else:
                self.encoder = nn.Sequential(
                    nn.Linear(n_emb, 4 * n_emb),
                    nn.Mish(),
                    nn.Linear(4 * n_emb, n_emb)
                )
            
            # Decoder with cross-attention to condition
            decoder_layer = nn.TransformerDecoderLayer(
                d_model=n_emb,
                nhead=n_head,
                dim_feedforward=4*n_emb,
                dropout=p_drop_attn,
                activation='gelu',
                batch_first=True,
                norm_first=True
            )
            self.decoder = nn.TransformerDecoder(
                decoder_layer=decoder_layer,
                num_layers=n_layer
            )
        else:
            # No conditioning - use simple encoder architecture
            decoder_layer = nn.TransformerEncoderLayer(
                d_model=n_emb,
                nhead=n_head,
                dim_feedforward=4*n_emb,
                dropout=p_drop_attn,
                activation='gelu',
                batch_first=True,
                norm_first=True
            )
            self.decoder = nn.TransformerEncoder(
                encoder_layer=decoder_layer,
                num_layers=n_layer
            )
            encoder_only = True

        def get_causal_mask(pattern, T1, T2):
            if pattern == 'full':
                return torch.ones((T1, T2), dtype=torch.bool)
            elif pattern == 'causal':
                return (torch.triu(torch.ones(T1, T2)) == 1).transpose(0, 1)
            elif pattern == 'causal-1':
                mask = (torch.triu(torch.ones(T1, T2)) == 1).transpose(0, 1)
                mask = mask.fill_diagonal_(False)
                mask[:, 4:] = False
                return mask    
            elif pattern == 'no_attn':
                return torch.zeros((T1, T2), dtype=torch.bool)
            else:  
                raise NotImplementedError

        # causal attention masks
        if cond_causal_attn and self.cond_dim > 0:
            # Causal mask for encoder (condition)
            T_cond = n_cond_steps
            temp_mask = (torch.triu(torch.ones(T_cond, T_cond)) == 1).transpose(0, 1)
            temp_mask = temp_mask.float().masked_fill(temp_mask == 0, float('-inf')).masked_fill(temp_mask == 1, float(0.0))
            self.register_buffer("encoder_mask", temp_mask)
        else:
            self.encoder_mask = None
        
        if causal_attn:
            sz = self.x_horizon + self.y_horizon
            mask = torch.ones((sz, sz), dtype=torch.bool)
            mask[::2,::2] = get_causal_mask(x_to_x_attn, self.x_horizon, self.x_horizon)
            mask[1::2,1::2] = get_causal_mask(y_to_y_attn, self.y_horizon, self.y_horizon)
            mask[::2,1::2] = get_causal_mask(x_to_y_attn, self.x_horizon, self.y_horizon)
            mask[1::2,::2] = get_causal_mask(y_to_x_attn, self.y_horizon, self.x_horizon)

            mask = mask.float().masked_fill(mask == 0, float('-inf')).masked_fill(mask == 1, float(0.0))

            self.register_buffer("mask", mask)

        else:
            self.mask = None

        # ── Windowed cross-attention mask ────────────────────────────
        self.n_past_steps = n_past_steps
        self.cross_attn_window = cross_attn_window
        self.cross_attn_mode = cross_attn_mode
        _valid_modes = ("full", "state", "action", "no_attn")
        if cross_attn_mode not in _valid_modes:
            raise ValueError(f"cross_attn_mode must be one of {_valid_modes}, got '{cross_attn_mode}'")

        _needs_cross_attn_mask = (
            self.cond_dim > 0
            and (cross_attn_window is not None or cross_attn_mode != "full")
        )
        if _needs_cross_attn_mask:
            n_target = self.x_horizon + self.y_horizon
            # Start with all cells allowing attention (0.0 = attend, -inf = block)
            mask = torch.zeros(n_target, n_cond_steps)

            # Apply window constraint
            if cross_attn_window is not None:
                max_t = n_past_steps + cross_attn_window
                for t in range(self.x_horizon):
                    if t >= max_t:
                        mask[2 * t, :] = float('-inf')       # state token
                        mask[2 * t + 1, :] = float('-inf')   # action token

            # Apply mode constraint (per-token-type gating)
            if cross_attn_mode == "state":
                # Only x (state) tokens attend: mask out y (action) tokens
                for t in range(self.y_horizon):
                    mask[2 * t + 1, :] = float('-inf')       # odd = action
            elif cross_attn_mode == "action":
                # Only y (action) tokens attend: mask out x (state) tokens
                for t in range(self.x_horizon):
                    mask[2 * t, :] = float('-inf')            # even = state
            elif cross_attn_mode == "no_attn":
                mask[:, :] = float('-inf')                    # block all

            self.register_buffer("cross_attn_mask", mask)
        else:
            self.cross_attn_mask = None

        if attention_mask_type == "bool":
            for name in ("mask", "encoder_mask", "cross_attn_mask"):
                value = getattr(self, name, None)
                if value is not None:
                    setattr(self, name, torch.isneginf(value))

        # decoder head
        self.x_ln_f = nn.LayerNorm(n_emb)
        self.x_head = nn.Linear(n_emb, self.x_output_dim)
        self.y_ln_f = nn.LayerNorm(n_emb)
        self.y_head = nn.Linear(n_emb, self.y_output_dim)
        
        # constants
        self.encoder_only = encoder_only

        # init
        self.apply(self._init_weights)
        logger.info(
            "number of parameters: %e", sum(p.numel() for p in self.parameters())
        )

    def _init_weights(self, module):
        ignore_types = (nn.Dropout, 
            SinusoidalPosEmb, 
            nn.TransformerEncoderLayer, 
            nn.TransformerDecoderLayer,
            nn.TransformerEncoder,
            nn.TransformerDecoder,
            nn.ModuleList,
            nn.Mish,
            nn.Sequential)
        if isinstance(module, (nn.Linear, nn.Embedding)):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.MultiheadAttention):
            weight_names = [
                'in_proj_weight', 'q_proj_weight', 'k_proj_weight', 'v_proj_weight']
            for name in weight_names:
                weight = getattr(module, name)
                if weight is not None:
                    torch.nn.init.normal_(weight, mean=0.0, std=0.02)
            
            bias_names = ['in_proj_bias', 'bias_k', 'bias_v']
            for name in bias_names:
                bias = getattr(module, name)
                if bias is not None:
                    torch.nn.init.zeros_(bias)
        elif isinstance(module, nn.LayerNorm):
            torch.nn.init.zeros_(module.bias)
            torch.nn.init.ones_(module.weight)
        elif isinstance(module, Transformer):
            torch.nn.init.normal_(module.pos_emb, mean=0.0, std=0.02)
            if module.cond_pos_emb is not None:
                torch.nn.init.normal_(module.cond_pos_emb, mean=0.0, std=0.02)
        elif isinstance(module, ignore_types):
            # no param
            pass
        else:
            raise RuntimeError("Unaccounted module {}".format(module))
    
    def get_optim_groups(self, weight_decay: float=1e-3):
        """
        This long function is unfortunately doing something very simple and is being very defensive:
        We are separating out all parameters of the model into two buckets: those that will experience
        weight decay for regularization and those that won't (biases, and layernorm/embedding weights).
        We are then returning the PyTorch optimizer object.
        """

        # separate out all parameters to those that will and won't experience regularizing weight decay
        decay = set()
        no_decay = set()
        whitelist_weight_modules = (torch.nn.Linear, torch.nn.MultiheadAttention)
        blacklist_weight_modules = (torch.nn.LayerNorm, torch.nn.Embedding)
        for mn, m in self.named_modules():
            for pn, p in m.named_parameters():
                fpn = "%s.%s" % (mn, pn) if mn else pn  # full param name

                if pn.endswith("bias"):
                    # all biases will not be decayed
                    no_decay.add(fpn)
                elif pn.startswith("bias"):
                    # MultiheadAttention bias starts with "bias"
                    no_decay.add(fpn)
                elif pn.endswith("weight") and isinstance(m, whitelist_weight_modules):
                    # weights of whitelist modules will be weight decayed
                    decay.add(fpn)
                elif pn.endswith("weight") and isinstance(m, blacklist_weight_modules):
                    # weights of blacklist modules will NOT be weight decayed
                    no_decay.add(fpn)

        # special case the position embedding parameter in the root GPT module as not decayed
        no_decay.add("pos_emb")
        no_decay.add("_dummy_variable")
        if self.cond_pos_emb is not None:
            no_decay.add("cond_pos_emb")

        # validate that we considered every parameter
        param_dict = {pn: p for pn, p in self.named_parameters()}
        inter_params = decay & no_decay
        union_params = decay | no_decay
        assert (
            len(inter_params) == 0
        ), "parameters %s made it into both decay/no_decay sets!" % (str(inter_params),)
        assert (
            len(param_dict.keys() - union_params) == 0
        ), "parameters %s were not separated into either decay/no_decay set!" % (
            str(param_dict.keys() - union_params),
        )

        # create the pytorch optimizer object
        optim_groups = [
            {
                "params": [param_dict[pn] for pn in sorted(list(decay))],
                "weight_decay": weight_decay,
            },
            {
                "params": [param_dict[pn] for pn in sorted(list(no_decay))],
                "weight_decay": 0.0,
            },
        ]
        return optim_groups


    def configure_optimizers(self, 
            learning_rate: float=1e-4, 
            weight_decay: float=1e-3,
            betas: Tuple[float, float]=(0.9,0.95)):
        optim_groups = self.get_optim_groups(weight_decay=weight_decay)
        optimizer = torch.optim.AdamW(
            optim_groups, lr=learning_rate, betas=betas
        )
        return optimizer

    def encode_condition(self, cond: torch.Tensor) -> torch.Tensor:
        """Encode condition once for reuse across fixed-shape DDIM steps."""
        cond_embeddings = self.cond_obs_emb(cond)
        cond_embeddings = cond_embeddings + self.cond_pos_emb[:, :cond.shape[1], :]
        cond_embeddings = self.drop(cond_embeddings)
        if isinstance(self.encoder, nn.TransformerEncoder):
            return self.encoder(src=cond_embeddings, mask=self.encoder_mask)
        return self.encoder(cond_embeddings)

    def forward(self, 
                x_input,
                y_input,
                x_timesteps,
                y_timesteps,
                cond: Optional[torch.Tensor]=None,
                cond_embeddings: Optional[torch.Tensor]=None,
                **kwargs):
        """
        x_input: (B,T,x_input_dim) - State input
        y_input: (B,T,y_input_dim) - Action input
        x_timesteps: (B,T) - State timesteps
        y_timesteps: (B,T) - Action timesteps
        cond: (B,T_cond,cond_dim) - Optional condition (e.g., motion latent)
        output: ((B,T,x_output_dim), (B,T,y_output_dim))
        """
        B, H = x_input.shape[:2]
        # time embedding
        x_timesteps = self.time_emb(x_timesteps)
        # (B,T,n_emb//4)
        y_timesteps = self.time_emb(y_timesteps)
        # (B,T,n_emb//4)

        # input embedding
        x_input = self.x_emb(x_input)  # (B,T,3*n_emb//4)
        y_input = self.y_emb(y_input)  # (B,T,3*n_emb//4)

        # Integer diffusion indices make the sinusoidal embedding FP32. Match
        # the learned projection dtype so FP16 exports do not promote the
        # concatenated tokens back to FP32 before half-precision LayerNorm.
        x_timesteps = x_timesteps.to(dtype=x_input.dtype)
        y_timesteps = y_timesteps.to(dtype=y_input.dtype)
        
        # Combine input embeddings with time embeddings
        x_embeddings = torch.cat([x_input, x_timesteps], dim=-1)  # (B,T,n_emb)
        y_embeddings = torch.cat([y_input, y_timesteps], dim=-1)  # (B,T,n_emb)
        
        # Interleave x and y tokens
        token_embeddings = x_embeddings.new_zeros((B, H*2, self.n_emb))
        token_embeddings[:,::2] = x_embeddings
        token_embeddings[:,1::2] = y_embeddings

        # Add positional embeddings
        t = token_embeddings.shape[1]
        position_embeddings = self.pos_emb[:, :t, :]
        token_embeddings = self.drop(token_embeddings + position_embeddings)
        # (B,T*2,n_emb)

        # Process with encoder-decoder (if cond) or encoder-only (if no cond)
        if self.cond_dim > 0 and (cond is not None or cond_embeddings is not None):
            if cond_embeddings is None:
                cond_embeddings = self.encode_condition(cond)
            # Decode with cross-attention to condition
            token_embeddings = self.decoder(
                tgt=token_embeddings,
                memory=cond_embeddings,
                tgt_mask=self.mask,
                memory_mask=self.cross_attn_mask,
            )
        else:
            # No conditioning - simple encoder
            token_embeddings = self.decoder(
                src=token_embeddings,
                mask=self.mask,
            )
        # (B,T*2,n_emb)
        
        # Split back into x and y
        x_output = token_embeddings[:,::2]  # (B,T,n_emb)
        y_output = token_embeddings[:,1::2]  # (B,T,n_emb)

        # Output heads
        x_output = self.x_ln_f(x_output)
        x_output = self.x_head(x_output)  # (B,T,x_output_dim)
        
        y_output = self.y_ln_f(y_output)
        y_output = self.y_head(y_output)  # (B,T,y_output_dim)

        return x_output, y_output
