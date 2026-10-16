#!/usr/bin/env python3
"""Validate the exported data-collection layout before launching Isaac Sim."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import yaml


COLLECTION_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = COLLECTION_ROOT.parent
REPO_ROOT = CODE_ROOT.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=REPO_ROOT / "Artifacts/checkpoints/rl_tracker/model_75000.pt",
    )
    parser.add_argument(
        "--motion-root",
        type=Path,
        default=REPO_ROOT / "Artifacts/motions/g1_152fk",
    )
    parser.add_argument("--allow-missing-artifacts", action="store_true")
    args = parser.parse_args()

    required = [
        CODE_ROOT / "train.py",
        CODE_ROOT / "diffusion_policy/utils/replay_buffer.py",
        CODE_ROOT / "assets/unitree_description/urdf/g1/main.urdf",
        COLLECTION_ROOT / "scripts/data_collection/data_collection.py",
        COLLECTION_ROOT / "scripts/data_collection/data_collection.yaml",
        COLLECTION_ROOT / "source/rl_tracker/rl_tracker/tasks/tracking/config/g1/diffusion_env_cfg.py",
        COLLECTION_ROOT / "vendor/rsl_rl-modular-normed/rsl_rl/runners/on_policy_runner.py",
    ]
    missing_code = [str(path) for path in required if not path.is_file()]
    config_path = COLLECTION_ROOT / "scripts/data_collection/data_collection.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["task"]["name"] != "Isaac-PegasusMoDye-DataCollection-G1-v0":
        raise RuntimeError("collection task registration drift")

    motion_files = sorted(args.motion_root.glob("*/motion.npz"))
    missing_artifacts = []
    if not args.checkpoint.is_file():
        missing_artifacts.append(str(args.checkpoint))
    if not motion_files:
        missing_artifacts.append(f"{args.motion_root}/*/motion.npz")

    report = {
        "status": "PASS" if not missing_code and (not missing_artifacts or args.allow_missing_artifacts) else "FAIL",
        "python": sys.version.split()[0],
        "task": config["task"]["name"],
        "asset_root": os.environ.get("PREDACTOR_ASSET_ROOT", str(CODE_ROOT / "assets")),
        "code_missing": missing_code,
        "artifact_missing": missing_artifacts,
        "motion_count": len(motion_files),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
