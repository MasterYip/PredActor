#!/usr/bin/env python3
"""Generate exact-weight Task082 artifacts/config matrix from Task073 backbone.

The input TorchScript module is immutable.  A Python production architecture is
reconstructed, loaded strictly from its state dict, lowered, parity checked on
three seeds, and serialized with stateless condition-embedding entry points.
"""
import argparse
import hashlib
import json
from pathlib import Path

import torch
import yaml

from diffusion_deploy.tools.torch21_compat import (
    Torch21ConditionEmbeddingBackbone,
    assert_torch21_operators,
    lower_multihead_attention,
)
from diffusion_policy.backbone.transformer_codiffuse import Transformer


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def production_model():
    return Transformer(
        x_horizon=20, y_horizon=20, x_input_dim=384, x_output_dim=384,
        y_input_dim=29, y_output_dim=29, cond_dim=96, n_cond_steps=4,
        n_cond_layers=0, cond_causal_attn=False, n_past_steps=4,
        n_emb=256, n_head=4, n_layer=2, p_drop_emb=0.0, p_drop_attn=0.0,
        causal_attn=True, x_to_x_attn="full", x_to_y_attn="no_attn",
        y_to_x_attn="causal", y_to_y_attn="causal",
        cross_attn_window=None, cross_attn_mode="full",
    ).eval()


def inputs(seed):
    generator = torch.Generator().manual_seed(seed)
    return (
        torch.randn(1, 20, 384, generator=generator),
        torch.randn(1, 20, 29, generator=generator),
        torch.randint(20, (1, 20), generator=generator),
        torch.randint(20, (1, 20), generator=generator),
        torch.randn(1, 4, 96, generator=generator),
    )


def maximum_error(actual, expected):
    maximum = 0.0
    for lhs, rhs in zip(actual, expected):
        if not torch.isfinite(lhs).all():
            raise RuntimeError("nonfinite exported output")
        torch.testing.assert_close(lhs, rhs, atol=3e-6, rtol=3e-6)
        maximum = max(maximum, float((lhs - rhs).abs().max()))
    return maximum


def absolute_resources(payload, source_config):
    base = source_config.parent.resolve()
    payload.pop("resources", None)
    for key in ("schedule_path", "emphasis_path"):
        value = Path(payload["model"][key])
        payload["model"][key] = str(
            value if value.is_absolute() else (base / value).resolve())
    payload.setdefault("env", {})["use_fk"] = False
    payload["env"]["urdf_path"] = ""


def write_config(source_config, destination, model_path, switches):
    payload = yaml.safe_load(source_config.read_text())
    absolute_resources(payload, source_config)
    model = payload["model"]
    model["path"] = str(model_path.resolve())
    model["ddim_steps"] = 5
    model["ddim_eta"] = 0.0
    model["sampler_mode"] = "scalar_ddim"
    model["use_ns_ddim"] = False
    model["attention_projection_packing"] = "self"
    # Task073's accepted latency anchor is actor-only.  Disable WBG in the
    # serialized config before C++ parser validation instead of relying on the
    # benchmark to mutate it after load (too late for the FK/WBG contract gate).
    model.setdefault("whole_body_guidance", {})["enabled"] = False
    for name in ("condition_embedding_reuse", "ddim_precompute",
                 "defer_finite_checks", "inference_mode"):
        model[name] = bool(switches.get(name, False))
    destination.write_text(yaml.safe_dump(payload, sort_keys=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    immutable = torch.jit.load(str(args.checkpoint), map_location="cpu").eval()
    state = immutable.state_dict()
    examples = [inputs(seed) for seed in (11, 29, 47)]
    with torch.inference_mode():
        references = [immutable(*values) for values in examples]

    model = production_model()
    incompatible = model.load_state_dict(state, strict=False)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise RuntimeError(f"state mismatch: {incompatible}")
    artifact_path = args.output_dir / "exact_self_condition_reuse.pt"
    with lower_multihead_attention(model, "self") as count:
        if count != 4:
            raise RuntimeError(f"expected four attention modules, got {count}")
        wrapper = Torch21ConditionEmbeddingBackbone(model).eval()
        memory = wrapper.build_condition_embeddings(examples[0][4])
        artifact = torch.jit.trace_module(
            wrapper,
            {
                "forward": examples[0],
                "build_condition_embeddings": (examples[0][4],),
                "forward_encoded_condition": examples[0][:4] + (memory,),
            },
            check_trace=False,
        )
        maximum = 0.0
        with torch.inference_mode():
            for values, reference in zip(examples, references):
                encoded = artifact.build_condition_embeddings(values[4])
                output = artifact.forward_encoded_condition(*values[:4], encoded)
                maximum = max(maximum, maximum_error(output, reference))
        assert_torch21_operators(artifact)
        torch.jit.save(artifact, str(artifact_path))

    candidates = {
        "task073_self_reference": {},
        "condition_reuse": {"condition_embedding_reuse": True},
        "ddim_precompute": {"ddim_precompute": True},
        "defer_finite": {"defer_finite_checks": True},
        "inference_mode": {"inference_mode": True},
        "task082_all": {
            "condition_embedding_reuse": True,
            "ddim_precompute": True,
            "defer_finite_checks": True,
            "inference_mode": True,
        },
    }
    rows = []
    for candidate, switches in candidates.items():
        config = args.output_dir / f"{candidate}.yaml"
        write_config(args.config, config, artifact_path, switches)
        rows.append({
            "candidate": candidate,
            "config": str(config.resolve()),
            "config_sha256": sha256(config),
            **switches,
        })
    manifest = {
        "schema": "task082-exact-artifacts-v1",
        "status": "pass",
        "scope": "exact Task073 architecture and immutable state dict",
        "immutable_checkpoint": str(args.checkpoint.resolve()),
        "immutable_checkpoint_sha256": sha256(args.checkpoint),
        "artifact": str(artifact_path.resolve()),
        "artifact_sha256": sha256(artifact_path),
        "parity_seeds": [11, 29, 47],
        "parity_atol": 3e-6,
        "parity_rtol": 3e-6,
        "parity_max_abs": maximum,
        "candidates": rows,
    }
    path = args.output_dir / "artifact_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "manifest": str(path)}))


if __name__ == "__main__":
    main()
