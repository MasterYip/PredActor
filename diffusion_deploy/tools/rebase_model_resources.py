#!/usr/bin/env python3
"""Rebase an exported model release onto package-owned runtime resources."""

import argparse
import hashlib
import pathlib
import shutil

import yaml


EXPECTED_URDF_SHA256 = "dbc8471004e9b0b85c27a4ebc1f0d90a727c1cf7ca9ef507b805596f2004d64b"
REQUIRED_MODEL_FILES = (
    "deploy_config.yaml",
    "g1_policy_backbone.pt",
    "ddpm_schedule.pt",
    "emphasis_matrices.pt",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rebase_model_release(model_dir, urdf_source, provenance_source=None):
    model_dir = pathlib.Path(model_dir).resolve()
    urdf_source = pathlib.Path(urdf_source).resolve()
    for name in REQUIRED_MODEL_FILES:
        if not (model_dir / name).is_file():
            raise FileNotFoundError(f"required model resource missing: {name}")
    if sha256_file(urdf_source) != EXPECTED_URDF_SHA256:
        raise ValueError("canonical G1 URDF checksum mismatch")

    urdf_relative = pathlib.Path("resources/g1/main.urdf")
    urdf_target = model_dir / urdf_relative
    urdf_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(urdf_source, urdf_target)
    if provenance_source:
        provenance = pathlib.Path(provenance_source).resolve()
        shutil.copyfile(provenance, urdf_target.parent / "PROVENANCE.md")
        for name in ("LICENSE", "SOURCE_PACKAGE.xml"):
            sibling = provenance.parent / name
            if sibling.is_file():
                shutil.copyfile(sibling, urdf_target.parent / name)

    configs = sorted(model_dir.glob("deploy_config*.yaml"))
    for config_path in configs:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        model = config.setdefault("model", {})
        for key in ("path", "schedule_path", "emphasis_path"):
            value = model.get(key)
            if value:
                model[key] = pathlib.Path(str(value)).name
        env = config.setdefault("env", {})
        if not env.get("use_fk"):
            raise ValueError(f"FK model config must set env.use_fk=true: {config_path}")
        env["urdf_path"] = urdf_relative.as_posix()
        config["resources"] = {
            "schema_version": 1,
            "manifest": "resource_manifest.yaml",
            "checksum_file": "SHA256SUMS",
            "conditioning_mode": "none",
        }
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    artifacts = []
    for path in sorted(p for p in model_dir.rglob("*") if p.is_file()
                       and p.name not in ("SHA256SUMS", "resource_manifest.yaml")):
        artifacts.append({
            "path": path.relative_to(model_dir).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    manifest = {
        "schema": "diffusion_deploy.resources",
        "schema_version": 1,
        "created_by": "diffusion_deploy.tools.rebase_model_resources",
        "runtime": {"deploy_config": "deploy_config.yaml", "fsm_config": ""},
        "conditioning": {"mode": "none", "text_cond_dim": 0},
        "canonical_urdf_sha256": EXPECTED_URDF_SHA256,
        "artifacts": artifacts,
        "checksum_file": "SHA256SUMS",
    }
    (model_dir / "resource_manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    files = sorted(p for p in model_dir.rglob("*")
                   if p.is_file() and p.name != "SHA256SUMS")
    with (model_dir / "SHA256SUMS").open("w", encoding="ascii") as stream:
        for path in files:
            stream.write(f"{sha256_file(path)}  {path.relative_to(model_dir).as_posix()}\n")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--urdf-source", required=True)
    parser.add_argument("--provenance-source")
    args = parser.parse_args()
    rebase_model_release(args.model_dir, args.urdf_source, args.provenance_source)


if __name__ == "__main__":
    main()
