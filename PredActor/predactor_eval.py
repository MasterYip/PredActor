#!/usr/bin/env python3
"""Run a bounded, hash-checked PredActor MuJoCo evaluation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "diffusion_policy/config_files/g1prdp_cond_diffuse.yaml"


class ProjectIsolationGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"rl_tracker", "RLTracker", "MoDyeEnc", "src"}:
            raise ImportError(f"external development-project import forbidden: {fullname}")
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_external(path: Path, expected: str, label: str) -> Path:
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise ValueError(f"{label} SHA-256 must be exactly 64 hexadecimal characters")
    resolved = path.resolve(strict=True)
    if resolved.is_relative_to(ROOT):
        raise ValueError(f"{label} must remain outside the PredActor repository")
    actual = sha256(resolved)
    if actual.lower() != expected.lower():
        raise ValueError(f"{label} SHA-256 mismatch: expected {expected.lower()}, got {actual}")
    return resolved


def state_hash(module) -> str:
    import torch

    digest = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str((value.dtype, tuple(value.shape))).encode())
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--clip-checkpoint", type=Path, required=True)
    parser.add_argument("--clip-checkpoint-sha256", required=True)
    parser.add_argument("--clip-base", type=Path, required=True)
    parser.add_argument("--clip-base-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--text", default="stand")
    parser.add_argument("--viewer", action="store_true")
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("--steps must be positive")
    if args.output.exists():
        parser.error("--output must be a new path")
    try:
        checkpoint = checked_external(args.checkpoint, args.checkpoint_sha256, "policy checkpoint")
        clip_checkpoint = checked_external(
            args.clip_checkpoint, args.clip_checkpoint_sha256, "MotionCLIP checkpoint")
        clip_base = checked_external(args.clip_base, args.clip_base_sha256, "CLIP base")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    os.environ["PREDACTOR_ROOT"] = str(ROOT)
    os.environ["PREDACTOR_TEXT_CHECKPOINT"] = str(clip_checkpoint)
    sys.meta_path.insert(0, ProjectIsolationGuard())

    import hydra
    import numpy as np
    from omegaconf import OmegaConf
    import torch

    from cond_eval import _load_eval_agent
    from diffusion_policy.task_provider import CLIPTeleop
    from diffusion_policy.utils.config_loader import load_config

    cfg = load_config(CONFIG)
    cfg.training.device = args.device
    cfg.training.seed = args.seed
    cfg.training.use_ema = False
    cfg.output_dir = str(args.output.resolve())
    cfg.dataset_dir = "unused-evaluation-only"
    cfg.logging.mode = "disabled"
    wbg_enabled = "policy.actor.whole_body_guidance_config.enabled"
    wbg_gui = "policy.actor.whole_body_guidance_config.gui.enabled"
    for path in (wbg_enabled, wbg_gui):
        if OmegaConf.select(cfg, path) is not None:
            OmegaConf.update(cfg, path, False)
    runner_cfg = cfg.env_runner
    runner_cfg.device = args.device
    runner_cfg.max_steps = args.steps
    runner_cfg.enable_debugger = False
    runner_cfg.output_dir = str(args.output.resolve())
    runner_cfg.task_cond_providers = {}
    env_cfg = runner_cfg.env.config
    env_cfg.xml_path = str(ROOT / "assets/unitree_description/mjcf/g1_act.xml")
    env_cfg.urdf_path = str(ROOT / "assets/unitree_description/urdf/g1/main.urdf")
    env_cfg.enable_viewer = args.viewer
    env_cfg.fk_device = args.device
    OmegaConf.resolve(cfg)

    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    agent = _load_eval_agent(checkpoint, payload, cfg, args.device)
    agent.set_inference_precision("fp32")
    normalizer_before = state_hash(agent.normalizer)
    for name, value in agent.state_dict().items():
        if not (torch.is_tensor(value) and value.is_floating_point()):
            continue
        if name.rsplit(".", 1)[-1] in {"mask", "encoder_mask", "memory_mask"}:
            if torch.isnan(value).any() or torch.isposinf(value).any():
                raise RuntimeError(f"invalid attention mask: {name}")
        elif not torch.isfinite(value).all():
            raise RuntimeError(f"nonfinite model state: {name}")

    provider = CLIPTeleop(
        device=args.device, checkpoint_path=str(clip_checkpoint),
        clip_model_name=str(clip_base), default_text=args.text,
        interactive_input=False)

    class FiniteObserver:
        steps = 0

        def start(self, env, policy):
            original_step = env.step

            def finite_step(action, *positional, **keywords):
                if not np.isfinite(np.asarray(action)).all():
                    raise RuntimeError("nonfinite policy action")
                return original_step(action, *positional, **keywords)

            env.step = finite_step

        def stop(self):
            pass

        def before_step(self, index):
            pass

        def after_step(self, index, env, policy):
            if not (np.isfinite(env.data.qpos).all() and np.isfinite(env.data.qvel).all()):
                raise RuntimeError("nonfinite simulator state")
            self.steps += 1

    observer = FiniteObserver()
    runner = hydra.utils.instantiate(
        runner_cfg, task_cond_provider=provider, runtime_observer=observer)
    args.output.mkdir(parents=True)
    result = runner.run(agent, cfg)
    if result is None or result["total_steps"] != args.steps or observer.steps != args.steps:
        raise RuntimeError("evaluation did not complete the requested finite steps")
    if state_hash(agent.normalizer) != normalizer_before:
        raise RuntimeError("evaluation changed the fitted normalizer")

    origins = {}
    for name, module in list(sys.modules.items()):
        if not name.startswith(("diffusion_policy", "cond_eval")):
            continue
        origin = getattr(module, "__file__", None)
        if not origin:
            continue
        resolved = Path(origin).resolve()
        if not resolved.is_relative_to(ROOT):
            raise RuntimeError(f"external project fallback: {name}: {origin}")
        origins[name] = str(resolved.relative_to(ROOT))
    report = {
        "status": "PASS",
        "scope": "bounded real MuJoCo integration smoke; not a quality or safety claim",
        "checkpoint_sha256": sha256(checkpoint),
        "clip_checkpoint_sha256": sha256(clip_checkpoint),
        "clip_base_sha256": sha256(clip_base),
        "config_sha256": sha256(CONFIG),
        "seed": args.seed,
        "text": args.text,
        "device": args.device,
        "finite_action_and_state_steps": observer.steps,
        "normalizer_sha256": normalizer_before,
        "result": result,
        "import_origins": origins,
        "torch": torch.__version__,
    }
    (args.output / "validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    OmegaConf.save(cfg, args.output / "runtime_config.yaml")
    print(f"PREDACTOR_EVAL_PASS {args.steps} steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
