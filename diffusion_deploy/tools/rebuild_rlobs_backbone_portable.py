#!/usr/bin/env python3
"""Rebuild the known G1 RLObs-DP backbone as device-portable TorchScript."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import torch
from torch import nn

from diffusion_policy.backbone.transformer import Transformer


class PortableSinusoidalPosEmb(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.half_dim = dim // 2
        self.exponent = math.log(10000.0) / (self.half_dim - 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        indices = torch.arange(
            self.half_dim, dtype=x.dtype, device=x.device
        )
        frequency = torch.exp(indices * -self.exponent)
        emb = x[:, :, None] * frequency[None, None, :]
        return torch.cat((emb.sin(), emb.cos()), dim=-1)


class PortableRLObsTransformer(nn.Module):
    def __init__(self, trained: Transformer):
        super().__init__()
        self.input_emb = trained.input_emb
        self.pos_emb = trained.pos_emb
        self.drop = trained.drop
        self.time_emb = PortableSinusoidalPosEmb(128)
        self.cond_obs_emb = trained.cond_obs_emb
        self.cond_pos_emb = trained.cond_pos_emb
        self.encoder = trained.encoder
        self.decoder = trained.decoder
        self.register_buffer("mask", trained.mask)
        self.register_buffer("memory_mask", trained.memory_mask)
        self.ln_f = trained.ln_f
        self.head = trained.head

    def forward(
        self,
        sample: torch.Tensor,
        timesteps: torch.Tensor,
        cond: torch.Tensor,
    ) -> torch.Tensor:
        batch = sample.shape[0]
        time_emb = self.time_emb(timesteps)
        input_emb = self.input_emb(sample)
        cond = cond.reshape(batch, -1, 608)
        cond_embeddings = self.cond_obs_emb(cond)
        cond_steps = cond_embeddings.shape[1]
        cond_positions = self.cond_pos_emb[:, :cond_steps, :]
        memory = self.encoder(self.drop(cond_embeddings + cond_positions))
        tokens = torch.cat((input_emb, time_emb), dim=-1)
        steps = tokens.shape[1]
        positions = self.pos_emb[:, :steps, :]
        decoded = self.decoder(
            tgt=self.drop(tokens + positions),
            memory=memory,
            tgt_mask=self.mask,
            memory_mask=self.memory_mask,
        )
        return self.head(self.ln_f(decoded))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source = torch.jit.load(str(args.input), map_location="cpu").eval()
    expected = {
        "input_emb.weight": (128, 29),
        "cond_obs_emb.weight": (256, 608),
        "pos_emb": (1, 20, 256),
        "cond_pos_emb": (1, 4, 256),
        "head.weight": (29, 256),
    }
    state = source.state_dict()
    for name, shape in expected.items():
        if name not in state or tuple(state[name].shape) != shape:
            raise RuntimeError(
                f"source contract mismatch for {name}: "
                f"{tuple(state[name].shape) if name in state else 'missing'} != {shape}"
            )

    trained = Transformer(
        x_horizon=20,
        x_input_dim=29,
        x_output_dim=29,
        n_cond_steps=4,
        cond_dim=608,
        n_emb=256,
        n_head=4,
        n_layer=2,
        p_drop_emb=0.1,
        p_drop_attn=0.1,
        causal_attn=True,
        cond_causal_attn=False,
        n_cond_layers=4,
    ).eval()
    trained.load_state_dict(state, strict=True)
    portable = torch.jit.script(PortableRLObsTransformer(trained).eval())

    torch.manual_seed(20260818)
    sample = torch.randn(2, 20, 29)
    timesteps = torch.randint(0, 20, (2, 20), dtype=torch.long)
    cond = torch.randn(2, 4, 608)
    with torch.no_grad():
        reference = source(sample, timesteps, cond)
        candidate = portable(sample, timesteps, cond)
    max_abs = float((reference - candidate).abs().max())
    rmse = float((reference - candidate).square().mean().sqrt())
    if not torch.isfinite(candidate).all() or max_abs > 1e-5:
        raise RuntimeError(
            f"portable rebuild parity failed: max_abs={max_abs}, rmse={rmse}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    portable.save(str(args.output))
    reloaded = torch.jit.load(str(args.output), map_location="cpu").eval()
    with torch.no_grad():
        reload_max_abs = float((candidate - reloaded(sample, timesteps, cond)).abs().max())
    if reload_max_abs > 1e-7:
        raise RuntimeError(f"saved artifact parity failed: max_abs={reload_max_abs}")

    result = {
        "schema": 1,
        "source_sha256": sha256(args.input),
        "output_sha256": sha256(args.output),
        "source_vs_portable_max_abs": max_abs,
        "source_vs_portable_rmse": rmse,
        "portable_vs_reloaded_max_abs": reload_max_abs,
        "seed": 20260818,
        "test_shapes": {
            "sample": [2, 20, 29],
            "timesteps": [2, 20],
            "condition": [2, 4, 608],
        },
        "device_portability_change":
            "sinusoidal frequency tensor is created on timesteps.device",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
