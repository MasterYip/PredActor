"""Minimal MotionCLIP encoder runtime used by the public dyeing pipeline."""

from __future__ import annotations

from types import SimpleNamespace

import clip
import numpy as np
import torch
from torch import nn


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        encoding = torch.zeros(max_len, d_model)
        position = torch.arange(max_len, dtype=torch.float).unsqueeze(1)
        scale = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        encoding[:, 0::2] = torch.sin(position * scale)
        encoding[:, 1::2] = torch.cos(position * scale)
        self.register_buffer("pe", encoding.unsqueeze(0).transpose(0, 1))

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.dropout(value + self.pe[:value.shape[0]])


class MotionClipEncoder(nn.Module):
    """Encoder architecture matching the released G1 MotionCLIP checkpoint."""

    def __init__(self):
        super().__init__()
        latent_dim = 512
        self.muQuery = nn.Parameter(torch.randn(1, latent_dim))
        self.sigmaQuery = nn.Parameter(torch.randn(1, latent_dim))
        self.skelEmbedding = nn.Linear(30 * 3, latent_dim)
        self.sequence_pos_encoder = PositionalEncoding(latent_dim, dropout=0.1)
        layer = nn.TransformerEncoderLayer(
            d_model=latent_dim,
            nhead=4,
            dim_feedforward=1024,
            dropout=0.1,
            activation="gelu",
        )
        self.seqTransEncoder = nn.TransformerEncoder(layer, num_layers=8)

    def forward(self, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        value, labels, mask = batch["x"], batch["y"], batch["mask"]
        batch_size, joints, features, frames = value.shape
        value = value.permute(3, 0, 1, 2).reshape(frames, batch_size, joints * features)
        value = self.skelEmbedding(value)
        labels = labels - labels
        sequence = torch.cat((self.muQuery[labels][None], self.sigmaQuery[labels][None], value), dim=0)
        sequence = self.sequence_pos_encoder(sequence)
        token_mask = torch.ones((batch_size, 2), dtype=torch.bool, device=value.device)
        sequence_mask = torch.cat((token_mask, mask), dim=1)
        encoded = self.seqTransEncoder(sequence, src_key_padding_mask=~sequence_mask)
        return {"mu": encoded[0]}


class MotionClipDyeRuntime(nn.Module):
    def __init__(self, encoder: nn.Module, clip_model: nn.Module):
        super().__init__()
        self.encoder = encoder
        self.clip_model = clip_model

    @staticmethod
    def lengths_to_mask(lengths: torch.Tensor) -> torch.Tensor:
        max_len = int(lengths.max().item())
        index = torch.arange(max_len, device=lengths.device).expand(len(lengths), max_len)
        return index < lengths.unsqueeze(1)


def _checkpoint_state(path: str, device: str) -> dict[str, torch.Tensor]:
    try:
        state = torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(path, map_location=device)
    if isinstance(state, dict) and "model" in state:
        state = state["model"]
    if not isinstance(state, dict):
        raise TypeError(f"Unsupported MotionCLIP checkpoint payload: {type(state)!r}")
    return state


def _substate(state: dict[str, torch.Tensor], prefix: str) -> dict[str, torch.Tensor]:
    selected = {key[len(prefix):]: value for key, value in state.items() if key.startswith(prefix)}
    if not selected:
        raise KeyError(f"MotionCLIP checkpoint has no {prefix} weights")
    return selected


def get_motion_clip(checkpoint_path: str, device: str = "cuda", **_) -> tuple[MotionClipDyeRuntime, object]:
    """Load only the encoder and text encoder needed for dataset dyeing."""
    device_name = f"cuda:{device}" if isinstance(device, int) else str(device)
    state = _checkpoint_state(checkpoint_path, device_name)

    encoder = MotionClipEncoder().to(device_name)
    encoder.load_state_dict(_substate(state, "encoder."), strict=True)

    clip_model, _ = clip.load("ViT-B/32", device=device_name, jit=False)
    clip_model.load_state_dict(_substate(state, "clip_model."), strict=True)

    model = MotionClipDyeRuntime(encoder, clip_model).to(device_name)
    model.eval()
    config = SimpleNamespace(model=SimpleNamespace(latent_dim=512, num_frames=60))
    return model, config
