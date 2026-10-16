#!/usr/bin/env python3
"""Generate Task082 Track B random structural models for latency only."""
import argparse
import hashlib
import json
from pathlib import Path

import torch
import torch.nn as nn
import yaml

from diffusion_deploy.tools.torch21_compat import (
    Torch21ConditionEmbeddingBackbone,
    assert_torch21_operators,
    lower_multihead_attention,
)
from diffusion_policy.backbone.transformer_codiffuse import Transformer


CANDIDATES = [
    ("b01_ff768", 256, 4, 768, 20, 2),
    ("b02_ff512", 256, 4, 512, 20, 2),
    ("b03_d192_t20", 192, 3, 768, 20, 2),
    ("b04_d192_t16", 192, 3, 512, 16, 2),
    ("b05_d192_t12", 192, 3, 512, 12, 2),
    ("b06_d128_t16", 128, 2, 512, 16, 2),
    ("b07_d128_t12", 128, 2, 256, 12, 2),
    ("b08_d128_t8", 128, 2, 256, 8, 2),
    ("b09_d128_t12_l1", 128, 2, 256, 12, 1),
    ("b10_d96_t8_l1", 96, 1, 192, 8, 1),
]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_model(dimension, heads, hidden, horizon, layers):
    model = Transformer(
        x_horizon=horizon, y_horizon=horizon,
        x_input_dim=384, x_output_dim=384,
        y_input_dim=29, y_output_dim=29,
        cond_dim=96, n_cond_steps=4, n_cond_layers=0,
        cond_causal_attn=False, n_past_steps=4,
        n_emb=dimension, n_head=heads, n_layer=layers,
        p_drop_emb=0.0, p_drop_attn=0.0, causal_attn=True,
        x_to_x_attn="full", x_to_y_attn="no_attn",
        y_to_x_attn="causal", y_to_y_attn="causal",
        cross_attn_window=None, cross_attn_mode="full",
    ).eval()
    if hidden != 4 * dimension:
        for layer in model.decoder.layers:
            layer.linear1 = nn.Linear(dimension, hidden)
            layer.linear2 = nn.Linear(hidden, dimension)
    return model


def initialize(model, seed):
    generator = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if name.endswith("weight") and parameter.ndim > 1:
                parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.02)
            elif name.endswith("weight"):
                parameter.fill_(1.0)
            else:
                parameter.zero_()


def inputs(horizon, seed):
    generator = torch.Generator().manual_seed(seed)
    return (
        torch.randn(1, horizon, 384, generator=generator),
        torch.randn(1, horizon, 29, generator=generator),
        torch.randint(20, (1, horizon), generator=generator),
        torch.randint(20, (1, horizon), generator=generator),
        torch.randn(1, 4, 96, generator=generator),
    )


def write_config(source, destination, model_path, horizon):
    payload = yaml.safe_load(source.read_text())
    payload.pop("resources", None)
    base = source.parent.resolve()
    for key in ("schedule_path", "emphasis_path"):
        path = Path(payload["model"][key])
        payload["model"][key] = str(
            path if path.is_absolute() else (base / path).resolve())
    model = payload["model"]
    model["path"] = str(model_path.resolve())
    model["n_future_steps"] = horizon - int(model["n_obs_steps"])
    model["ddim_steps"] = 5
    model["ddim_eta"] = 0.0
    model["sampler_mode"] = "scalar_ddim"
    model["use_ns_ddim"] = False
    model["attention_projection_packing"] = "self"
    model["condition_embedding_reuse"] = True
    model["ddim_precompute"] = True
    model["defer_finite_checks"] = True
    model["inference_mode"] = True
    model.setdefault("whole_body_guidance", {})["enabled"] = False
    payload.setdefault("env", {})["use_fk"] = False
    payload["env"]["urdf_path"] = ""
    destination.write_text(yaml.safe_dump(payload, sort_keys=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_dir = args.output_dir / "models"
    model_dir.mkdir()
    rows = []
    for index, (name, dimension, heads, hidden, horizon, layers) in enumerate(CANDIDATES):
        seed = 8200 + index
        torch.manual_seed(seed)
        model = make_model(dimension, heads, hidden, horizon, layers)
        initialize(model, seed)
        example = inputs(horizon, seed + 1000)
        with torch.inference_mode():
            eager = model(*example)
        path = model_dir / f"{name}.pt"
        with lower_multihead_attention(model, "self") as count:
            if count != 2 * layers:
                raise RuntimeError(f"{name}: attention replacement count {count}")
            wrapper = Torch21ConditionEmbeddingBackbone(model).eval()
            memory = wrapper.build_condition_embeddings(example[4])
            artifact = torch.jit.trace_module(
                wrapper,
                {"forward": example,
                 "build_condition_embeddings": (example[4],),
                 "forward_encoded_condition": example[:4] + (memory,)},
                check_trace=False,
            )
            encoded = artifact.build_condition_embeddings(example[4])
            actual = artifact.forward_encoded_condition(*example[:4], encoded)
            maximum = 0.0
            for lhs, rhs in zip(actual, eager):
                torch.testing.assert_close(lhs, rhs, atol=3e-6, rtol=3e-6)
                maximum = max(maximum, float((lhs - rhs).abs().max()))
            assert_torch21_operators(artifact)
            torch.jit.save(artifact, str(path))
        config = args.output_dir / f"{name}.yaml"
        write_config(args.config, config, path, horizon)
        rows.append({
            "candidate": name, "n_emb": dimension, "n_head": heads,
            "ff_hidden": hidden, "horizon": horizon, "n_layer": layers,
            "model": str(path.resolve()), "model_sha256": sha256(path),
            "config": str(config.resolve()), "config_sha256": sha256(config),
            "parameters": sum(p.numel() for p in artifact.parameters()),
            "export_parity_max_abs": maximum,
            "weight_contract": "deterministic_random_init_latency_only",
            "quality_claim": "none; retraining and policy/robot validation required",
        })
    manifest = {
        "schema": "task082-track-b-artifacts-v1", "status": "pass",
        "scope": "structural random-weight latency-only models",
        "source_config": str(args.config.resolve()),
        "source_config_sha256": sha256(args.config),
        "runtime_optimizations": ["self_qkv", "condition_embedding_reuse",
                                  "ddim_precompute", "defer_finite_checks",
                                  "inference_mode"],
        "cells": rows,
    }
    path = args.output_dir / "track_b_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "cells": len(rows),
                      "manifest": str(path)}))


if __name__ == "__main__":
    main()
