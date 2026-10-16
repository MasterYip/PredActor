#!/usr/bin/env python3
"""Export the four fixed unified-command CLIP latents as raw float32 files."""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import pathlib
import sys

import numpy as np
import yaml

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
from clip_cond_sender import _encode_text, _load_clip


COMMANDS = (
    ("stand", "up", "stand"),
    ("walk", "right", "walk"),
    ("jog", "down", "jog"),
    ("squat down", "left", "squat_down"),
)


def fnv1a64(data: bytes) -> str:
    value = 14695981039346656037
    for byte in data:
        value ^= byte
        value = (value * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return f"fnv1a64:{value:016x}"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configure_deploy(
        deploy_config: pathlib.Path, motions: list[dict],
        joystick_source: str, joystick_device: str, joystick_mapping: str,
        telemetry_enabled: bool,
        source_checkpoint: pathlib.Path | None = None,
        wbg_max_vx: float = 5.0, wbg_max_vy: float = 5.0,
        wbg_max_wz: float = 5.0) -> None:
    """Install the typed unified-command block into a conditional PRDP bundle."""
    config = yaml.safe_load(deploy_config.read_text(encoding="utf-8")) or {}
    runner = config.setdefault("runner", {})
    model = config.setdefault("model", {})
    condition_contract = (
        runner.get("condition_profile"),
        runner.get("rlobs_cond_dim"),
        runner.get("text_cond_dim"),
        model.get("backbone_cond_dim"),
    )
    if condition_contract not in {
            ("prdp_rlobs", 96, 512, 608),
            ("g1_prdp_standard2", 93, 512, 605)}:
        raise ValueError(
            "deploy config is not a supported conditional PRDP contract: "
            "expected prdp_rlobs 96+512=608 or g1_prdp_standard2 93+512=605")
    if model.get("classifier_guidance_impl") != "reuse_x0":
        raise ValueError(
            "unified fast WBG requires model.classifier_guidance_impl=reuse_x0")
    if not model.get("no_state_override", False):
        raise ValueError("unified fast WBG requires model.no_state_override=true")
    bounds = (wbg_max_vx, wbg_max_vy, wbg_max_wz)
    if any(not math.isfinite(value) or value <= 0.0 for value in bounds):
        raise ValueError("unified WBG bounds must be finite and greater than zero")

    config_dir = deploy_config.resolve().parent
    configured_motions = []
    for motion in motions:
        path = pathlib.Path(motion["path"]).resolve()
        relative = pathlib.Path(os.path.relpath(path, config_dir))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("command latent path must remain inside the deploy bundle")
        configured_motions.append({
            **motion,
            "path": str(relative),
        })

    runner["enable_cond_udp"] = False
    runner["enable_wbg_udp"] = False
    config.setdefault("resources", {})["conditioning_mode"] = "cached_in_process"
    runner["unified_command"] = {
        "enabled": True,
        "source": joystick_source,
        "joystick_device": joystick_device,
        "joystick_mapping": joystick_mapping,
        "source_timeout_s": 0.10,
        "deadzone": 0.10,
        "dpad_debounce_ms": 150,
        "wbg": {
            "enabled": True,
            "max_vx": wbg_max_vx,
            "max_vy": wbg_max_vy,
            "max_wz": wbg_max_wz,
            "kp": 1.0,
            "controls": {
                "l2_kp_enabled": True,
                "kp_axis": "l2",
                "kp_unpressed": 1.0,
                "kp_pressed": 0.0,
                "lb_toggle_enabled": True,
                "toggle_button": "LB",
                "toggle_debounce_ms": 150,
            },
        },
        "motions": configured_motions,
        "compatibility_udp": {
            "enabled": False,
            "host": "127.0.0.1",
            "condition_port": 9877,
            "wbg_port": 9879,
        },
        "telemetry": {
            "enabled": telemetry_enabled,
            "host": "127.0.0.1",
            "port": 9880,
        },
    }
    deploy_config.write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    manifest_path = config_dir / "resource_manifest.yaml"
    checksum_path = config_dir / "SHA256SUMS"
    if not manifest_path.is_file():
        return

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    manifest.setdefault("conditioning", {})["mode"] = "cached_in_process"
    artifacts = manifest.setdefault("artifacts", [])
    artifacts[:] = [
        artifact for artifact in artifacts
        if artifact.get("role") != "deploy_config"
        and not str(artifact.get("role", "")).startswith("command_latent_")
    ]

    def artifact(role: str, path: pathlib.Path) -> dict:
        return {
            "role": role,
            "path": os.path.relpath(path.resolve(), config_dir),
            "required": True,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }

    artifacts.insert(0, artifact("deploy_config", deploy_config))
    for motion in configured_motions:
        stem = pathlib.Path(motion["path"]).stem
        artifacts.append(artifact(f"command_latent_{stem}", config_dir / motion["path"]))
    clip = manifest.setdefault("conditioning", {}).setdefault("clip_encoder", {})
    clip["required_for_text_commands"] = False
    clip["transport"] = "cached_float32_in_process"
    if source_checkpoint is not None:
        clip["cache_source_checkpoint_name"] = source_checkpoint.name
        clip["cache_source_checkpoint_sha256"] = sha256_file(source_checkpoint)

    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    checksum_artifacts = list(artifacts) + [artifact("resource_manifest", manifest_path)]
    checksum_path.write_text(
        "".join(
            f"{item['sha256']}  {item['path']}\n"
            for item in sorted(checksum_artifacts, key=lambda item: item["path"])),
        encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export four MotionCLIP-compatible text latents for the C++ command cache")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--checkpoint", required=True,
                        help="MotionCLIP checkpoint matching policy training/export")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--model", default="ViT-B/32")
    parser.add_argument("--cond-dim", type=int, default=512)
    parser.add_argument("--deploy-config", type=pathlib.Path,
                        help="Also configure this exported conditional PRDP deploy YAML")
    parser.add_argument("--joystick-source", default="auto",
                        choices=("auto", "unitree_lowstate", "joydev"))
    parser.add_argument("--joystick-device")
    parser.add_argument("--joystick-mapping", default="xbox_new",
                        choices=("xbox", "xbox_new", "ps5", "beitong_kp20"))
    parser.add_argument("--telemetry", action="store_true",
                        help="Enable read-only status telemetry on 127.0.0.1:9880")
    parser.add_argument("--wbg-max-vx", type=float, default=5.0)
    parser.add_argument("--wbg-max-vy", type=float, default=5.0)
    parser.add_argument("--wbg-max-wz", type=float, default=5.0)
    args = parser.parse_args()

    if args.cond_dim != 512:
        parser.error("the unified conditional PRDP contract requires --cond-dim 512")
    if args.joystick_device is None:
        args.joystick_device = (
            "" if args.joystick_source == "unitree_lowstate"
            else "/dev/input/js0")
    has_device = args.joystick_device not in ("", "null")
    if ((args.joystick_source == "unitree_lowstate" and has_device)
            or (args.joystick_source == "joydev" and not has_device)):
        parser.error("--joystick-source conflicts with --joystick-device")

    args.output.mkdir(parents=True, exist_ok=True)
    model, tokenizer, _ = _load_clip(args.model, args.device, args.checkpoint)
    print("motions:")
    motions = []
    for name, dpad, stem in COMMANDS:
        latent = _encode_text(model, tokenizer, name, args.device, args.cond_dim)
        latent = np.asarray(latent, dtype="<f4")
        path = args.output / f"{stem}.f32"
        path.write_bytes(latent.tobytes(order="C"))
        digest = fnv1a64(path.read_bytes())
        motions.append({
            "name": name,
            "dpad": dpad,
            "path": str(path),
            "hash": digest,
            "dim": args.cond_dim,
        })
        print(f"  - name: {name!r}")
        print(f"    dpad: {dpad}")
        print(f"    path: {path.name}")
        print(f"    hash: {digest}")
        print(f"    dim: {args.cond_dim}")
    if args.deploy_config is not None:
        configure_deploy(
            args.deploy_config, motions,
            args.joystick_source, args.joystick_device,
            args.joystick_mapping, args.telemetry,
            pathlib.Path(args.checkpoint),
            args.wbg_max_vx, args.wbg_max_vy, args.wbg_max_wz)
        print(f"Unified command config updated: {args.deploy_config}")


if __name__ == "__main__":
    main()
