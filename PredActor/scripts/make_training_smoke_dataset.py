#!/usr/bin/env python3
"""Create a deterministic, structurally valid PredActor training dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import zarr


BODY_COUNT = 30
JOINT_COUNT = 29
TEXT_DIM = 512


def _write(group, name: str, value: np.ndarray) -> None:
    chunks = (min(64, value.shape[0]), *value.shape[1:])
    group.create_dataset(name, data=value, chunks=chunks, overwrite=False)


def build(output: Path, frames: int, episodes: int, seed: int) -> None:
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if frames < 40:
        raise ValueError("--frames must be at least 40")
    if episodes < 2 or frames % episodes:
        raise ValueError("--episodes must divide --frames and be at least 2")

    rng = np.random.default_rng(seed)
    time = np.arange(frames, dtype=np.float32) / 50.0
    root_pos = np.zeros((frames, 3), dtype=np.float32)
    root_pos[:, 0] = 0.08 * time
    root_pos[:, 2] = 0.75

    root_rot = np.zeros((frames, 4), dtype=np.float32)
    root_rot[:, 3] = 1.0
    body_offsets = np.zeros((BODY_COUNT, 3), dtype=np.float32)
    body_offsets[:, 0] = np.linspace(-0.18, 0.18, BODY_COUNT, dtype=np.float32)
    body_offsets[:, 2] = np.linspace(0.0, 0.9, BODY_COUNT, dtype=np.float32)
    body_offsets[0] = 0.0
    body_pos = root_pos[:, None, :] + body_offsets[None, :, :]
    body_rot = np.zeros((frames, BODY_COUNT, 4), dtype=np.float32)
    body_rot[..., 3] = 1.0

    body_lin_vel = np.zeros((frames, BODY_COUNT, 3), dtype=np.float32)
    body_lin_vel[..., 0] = 0.08
    body_ang_vel = np.zeros((frames, BODY_COUNT, 3), dtype=np.float32)
    phase = np.linspace(0.0, np.pi, JOINT_COUNT, dtype=np.float32)
    joint_pos = 0.04 * np.sin(time[:, None] * 2.0 + phase[None, :])
    joint_vel = np.gradient(joint_pos, axis=0) * 50.0
    act = joint_pos + rng.normal(0.0, 0.002, joint_pos.shape).astype(np.float32)
    last_actions = np.concatenate((act[:1], act[:-1]), axis=0)

    projected_gravity = np.zeros((frames, 3), dtype=np.float32)
    projected_gravity[:, 2] = -1.0
    base_lin_vel = np.zeros((frames, 3), dtype=np.float32)
    base_lin_vel[:, 0] = 0.08
    base_ang_vel = np.zeros((frames, 3), dtype=np.float32)
    motion_latent = np.zeros((frames, TEXT_DIM), dtype=np.float32)
    episode_size = frames // episodes
    for index in range(episodes):
        start = index * episode_size
        end = start + episode_size
        motion_latent[start:end, index % TEXT_DIM] = 1.0

    output.parent.mkdir(parents=True, exist_ok=True)
    root = zarr.open_group(str(output), mode="w")
    data = root.create_group("data")
    meta = root.create_group("meta")
    arrays = {
        "root_pos": root_pos,
        "root_rot": root_rot,
        "body_pos": body_pos,
        "body_rot": body_rot,
        "body_lin_vel": body_lin_vel,
        "body_ang_vel": body_ang_vel,
        "joint_pos": joint_pos.astype(np.float32),
        "joint_vel": joint_vel.astype(np.float32),
        "projected_gravity": projected_gravity,
        "base_lin_vel": base_lin_vel,
        "base_ang_vel": base_ang_vel,
        "last_actions": last_actions.astype(np.float32),
        "act": act.astype(np.float32),
        "motion_latent": motion_latent,
    }
    for name, value in arrays.items():
        _write(data, name, value)
    meta.create_dataset(
        "episode_ends",
        data=np.arange(episode_size, frames + 1, episode_size, dtype=np.int64),
        chunks=(episodes,),
        overwrite=False,
    )
    print(f"PREDACTOR_SMOKE_DATASET_READY {output} {frames} frames {episodes} episodes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=64)
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    build(args.output.resolve(), args.frames, args.episodes, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
