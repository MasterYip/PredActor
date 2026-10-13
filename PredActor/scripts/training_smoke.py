#!/usr/bin/env python3
"""Run one real PredActor optimization step on a generated zarr fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import torch


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    output = (args.output or ROOT / "outputs" / f"training-smoke-{stamp}").resolve()
    if output.exists():
        parser.error(f"--output must be a new path: {output}")
    output.mkdir(parents=True)
    dataset = output / "dataset" / "motion_dyed_text_t0.01.zarr"
    device = args.device
    if device == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"

    subprocess.run(
        [sys.executable, str(ROOT / "scripts/make_training_smoke_dataset.py"),
         "--output", str(dataset)], check=True)
    run_root = output / "runs"
    command = [
        sys.executable, str(ROOT / "train.py"),
        "--cfg", "g1prdp_cond_diffuse.yaml",
        "--exp_name", "release_smoke",
        f"output_dir={run_root}",
        f"dataset_dir={dataset.parent}",
        f"dataset.zarr_path={dataset.name}",
        "dataset.val_ratio=0.0",
        "dataset.symm_aug=false",
        "dataset.load_to_memory=false",
        "dataset.data_sample_rate=1.0",
        "dataset.normalizer_batch_size=16",
        "dataloader.batch_size=2",
        "dataloader.num_workers=0",
        "dataloader.prefetch_factor=null",
        "dataloader.pin_memory=false",
        "dataloader.persistent_workers=false",
        "val_dataloader.batch_size=2",
        "val_dataloader.num_workers=0",
        "val_dataloader.prefetch_factor=null",
        "val_dataloader.pin_memory=false",
        "val_dataloader.persistent_workers=false",
        f"training.device={device}",
        "training.num_epochs=1",
        "training.max_train_steps=1",
        "training.checkpoint_every=1",
        "training.save_terminal_checkpoint=true",
        "training.use_ema=false",
        "training.rollout_every=0",
        "training.val_every=0",
        "training.sample_every=0",
        "policy.actor.backbone.n_emb=64",
        "policy.actor.backbone.n_head=2",
        "policy.actor.backbone.n_layer=1",
        "logging.mode=disabled",
        "checkpoint.upload_to_wandb=false",
    ]
    env = os.environ.copy()
    env.setdefault("PREDACTOR_ROOT", str(ROOT))
    env.setdefault(
        "PREDACTOR_TEXT_CHECKPOINT",
        str(ROOT / "Artifacts/checkpoints/motionclip/g1-model-xyz-clip/checkpoint_0100.pth.tar"),
    )
    subprocess.run(command, cwd=ROOT, env=env, check=True)

    checkpoints = sorted(run_root.glob("*/checkpoints/latest.ckpt"))
    resolved = sorted(run_root.glob("*/resolved_config.yaml"))
    if len(checkpoints) != 1 or len(resolved) != 1 or checkpoints[0].stat().st_size == 0:
        raise RuntimeError("training smoke did not produce one resolved config and checkpoint")
    receipt = {
        "status": "PASS",
        "device": device,
        "dataset": str(dataset),
        "resolved_config": str(resolved[0]),
        "checkpoint": str(checkpoints[0]),
        "checkpoint_sha256": _sha256(checkpoints[0]),
        "scope": "one real optimization step with a reduced smoke-test backbone",
    }
    receipt_path = output / "training_smoke.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(f"PREDACTOR_TRAINING_SMOKE_PASS {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
