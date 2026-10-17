"""Finalize a portable diffusion_deploy model resource directory."""

from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
from typing import Iterable, Mapping

import yaml


SCHEMA = "diffusion_deploy.resources"
SCHEMA_VERSION = 1
MANIFEST_NAME = "resource_manifest.yaml"
CHECKSUM_NAME = "SHA256SUMS"
CLIP_PATH_ENV = "DIFFUSION_DEPLOY_CLIP_PATH"


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_to_output(path: os.PathLike[str] | str,
                        output_dir: pathlib.Path) -> str:
    resolved = pathlib.Path(path).resolve()
    try:
        return resolved.relative_to(output_dir.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(
            f"runtime artifact must be inside export directory: {resolved}"
        ) from exc


def copy_runtime_resource(source: os.PathLike[str] | str,
                          output_dir: os.PathLike[str] | str,
                          relative_destination: str) -> str:
    """Copy one runtime resource and return its export-relative path."""
    source_path = pathlib.Path(source).resolve()
    output_path = pathlib.Path(output_dir).resolve()
    destination = pathlib.PurePosixPath(relative_destination)
    if destination.is_absolute() or ".." in destination.parts:
        raise ValueError(f"resource destination escapes export directory: {destination}")
    if not source_path.is_file():
        raise FileNotFoundError(f"runtime resource does not exist: {source_path}")
    target = output_path.joinpath(*destination.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source_path != target:
        shutil.copy2(source_path, target)
    return destination.as_posix()


def write_resource_manifest(
    output_dir: os.PathLike[str] | str,
    deploy_config: os.PathLike[str] | str,
    fsm_config: os.PathLike[str] | str,
    artifacts: Iterable[Mapping[str, object]],
    text_cond_dim: int,
    data_profile: str = "",
    condition_profile: str = "external",
    robot_cond_dim: int = 0,
    condition_terms: Iterable[str] = (),
    precision: str = "fp32",
    delay_action_step: float = 0,
    delay_action_step_source: str = "compatibility_default",
) -> pathlib.Path:
    """Write the versioned resource manifest and deterministic checksums."""
    if precision not in ("fp32", "fp16"):
        raise ValueError("precision must be fp32 or fp16")
    output = pathlib.Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for artifact in artifacts:
        destination = pathlib.PurePosixPath(str(artifact["path"]))
        if destination.is_absolute() or ".." in destination.parts:
            raise ValueError(f"manifest artifact escapes export directory: {destination}")
        relative_path = str(artifact["path"])
        path = output / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"manifest artifact does not exist: {path}")
        entries.append({
            "role": str(artifact["role"]),
            "path": relative_path,
            "required": bool(artifact.get("required", True)),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    entries.sort(key=lambda item: (item["role"], item["path"]))

    text_conditioned = int(text_cond_dim) > 0
    manifest = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "created_by": "diffusion_deploy.tools.export_policy",
        "runtime": {
            "deploy_config": _relative_to_output(deploy_config, output),
            "fsm_config": _relative_to_output(fsm_config, output),
            "precision": precision,
            "action_selection": {
                "delay_action_step": float(delay_action_step),
                "source": str(delay_action_step_source),
                "indexing": "zero_based:n_obs_steps-1+delay_action_step",
                "interpolation": "linear_floor_ceil",
                "terminal_strategy": "selected_endpoints_to_noise_zero",
            },
        },
        "conditioning": {
            "mode": "external_udp" if text_conditioned else "none",
            "data_profile": str(data_profile),
            "condition_profile": str(condition_profile),
            "robot_cond_dim": int(robot_cond_dim),
            "text_cond_dim": int(text_cond_dim),
            "cond_dim": int(robot_cond_dim) + int(text_cond_dim),
            "terms": [str(term) for term in condition_terms],
            "clip_encoder": {
                "bundled": False,
                "required_for_text_commands": text_conditioned,
                "path_env": CLIP_PATH_ENV if text_conditioned else "",
                "transport": "float32_udp" if text_conditioned else "none",
            },
        },
        "artifacts": entries,
        "checksum_file": CHECKSUM_NAME,
    }
    manifest_path = output / MANIFEST_NAME
    with manifest_path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(manifest, stream, sort_keys=False)

    checksum_paths = sorted(
        path for path in output.rglob("*")
        if path.is_file() and path.name != CHECKSUM_NAME
    )
    with (output / CHECKSUM_NAME).open("w", encoding="utf-8") as stream:
        for path in checksum_paths:
            stream.write(f"{_sha256(path)}  {path.relative_to(output).as_posix()}\n")
    return manifest_path
