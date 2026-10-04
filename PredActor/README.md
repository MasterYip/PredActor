# PredActor

PredActor is an evaluation-only distribution of the predictive action diffusion
controller for Unitree G1. This repository contains source and the G1 robot
description needed by MuJoCo. Policy checkpoints, MotionCLIP weights, datasets,
experiment outputs, and other learned artifacts are deliberately not included.

## Run

From the public repository root, install [uv](https://docs.astral.sh/uv/) and
run:

```bash
uv sync --locked
uv run --locked python scripts/hf_download.py --filter checkpoints
uv run --locked predactor-eval
```

The evaluator opens `http://127.0.0.1:8765/`, chooses CUDA when available, and
falls back to CPU. Checkpoints live outside this package under the public
repository's Git-ignored `Artifacts/` directory.

This package supports local MuJoCo evaluation only. Training, IsaacLab data
collection, Unitree SDK/DDS, and hardware actuation are outside this release.
