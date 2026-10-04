"""Trainable condition compressor for reducing CLIP embedding dimensionality.

Placed in BCAgent before dropout and task mask, the compressor is trained
end-to-end via backpropagation from the diffusion loss.  It is fully
independent of the backbone architecture.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class CondCompressor(nn.Module):
    """Trainable MLP that compresses condition vectors before they enter the backbone.

    Operates on the last dimension: ``[B, T_cond, input_dim] → [B, T_cond, output_dim]``.
    Built as a simple MLP: ``Linear → Activation → … → Linear``.

    Args:
        input_dim:   Raw condition dimension (e.g., 512 for CLIP ViT-B/32).
        output_dim:  Compressed dimension (e.g., 64).  Fully configurable.
        hidden_dim:  Hidden-layer size.  Defaults to ``max(output_dim, 2 * input_dim // 3)``.
        num_layers:  Number of Linear layers (≥ 2).
        activation:  ``"mish"`` | ``"relu"`` | ``"gelu"``.
        dropout:     Dropout probability between layers (default 0.0).
    """

    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        hidden_dim: int | None = None,
        num_layers: int = 2,
        activation: str = "mish",
        dropout: float = 0.0,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim

        if hidden_dim is None:
            hidden_dim = max(output_dim, 2 * input_dim // 3)

        act_map = {"mish": nn.Mish, "relu": nn.ReLU, "gelu": nn.GELU}
        if activation not in act_map:
            raise ValueError(f"Unknown activation '{activation}'. Choose from {list(act_map.keys())}.")
        act_cls = act_map[activation]

        layers: list[nn.Module] = []
        in_dim = input_dim
        for i in range(num_layers):
            # All layers except the last go to hidden_dim; last layer outputs output_dim.
            out_dim = hidden_dim if i < num_layers - 1 else output_dim
            layers.append(nn.Linear(in_dim, out_dim))
            # Activation after every layer except the last.
            if i < num_layers - 1:
                layers.append(act_cls())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_dim = out_dim

        self.mlp = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Compress condition tensor.

        Args:
            x: ``[B, T_cond, input_dim]`` — normalized condition vector.

        Returns:
            ``[B, T_cond, output_dim]`` — compressed condition.
        """
        return self.mlp(x)
