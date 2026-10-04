# PredActor

PredActor is an evaluation-only distribution of the predictive action diffusion
controller for Unitree G1. This repository contains source and the G1 robot
description needed by MuJoCo. Policy checkpoints, MotionCLIP weights, datasets,
experiment outputs, and other learned artifacts are deliberately not included.

## Setup

Use Python 3.10 in a new environment. The versions below match the validated
runtime.

```bash
conda create -n predactor-eval python=3.10 pip -y
conda activate predactor-eval
python -m pip install --upgrade pip
python -m pip install setuptools==74.0.0
python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install --no-build-isolation -r requirements-eval.txt
```

For NVIDIA acceleration, replace the PyTorch index URL with
`https://download.pytorch.org/whl/cu121`.

Run `predactor_eval.py` directly from this `PredActor/` evaluation package
directory. An editable install is unnecessary. The supported release path is
native MuJoCo evaluation; IsaacLab collection, training, Unitree SDK/DDS, and
hardware actuation are outside this distribution.

## External weights

Keep all learned weights outside this evaluation package. From the Git checkout
root (one directory above this file), download the released policy and
fine-tuned MotionCLIP checkpoints into the Git-ignored `Artifacts/` directory:

```bash
python -m pip install huggingface_hub pyyaml
python scripts/hf_download.py --filter checkpoints
```

## Web UI evaluation

From the Git checkout root, launch the browser-based MuJoCo evaluator with the
downloaded artifacts:

```bash
export PREDACTOR_ROOT="$PWD/PredActor"
export PREDACTOR_TEXT_CHECKPOINT="$PWD/Artifacts/checkpoints/motionclip/g1-model-xyz-clip/checkpoint_0100.pth.tar"

python PredActor/cond_eval.py \
  --checkpoint "$PWD/Artifacts/checkpoints/predactor/pdp051/latest.ckpt" \
  --config g1prdp_cond_diffuse.yaml \
  --output_dir "$PWD/eval_output/web" \
  --device cpu --fk-device cpu --headless \
  --web-ui --web-host 127.0.0.1 --web-port 8765
```

The browser opens `http://127.0.0.1:8765/`. The root README documents the
optional bounded integration test and the separate OpenAI CLIP ViT-B/32 base
weight that test requires. The pinned artifact identities are:

```bash
2d963b32786f2989c6472726df9fcfe6b385590127e12e1f549a4b7d77488b2e  latest.ckpt
66a127df4958b346089b2020f2705c7456d9db0ee8b4bd9518608b708b35fc3c  checkpoint_0100.pth.tar
40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af  ViT-B-32.pt
```

The bounded evaluator requires all three SHA-256 values and refuses files
located inside the evaluation package. Only trusted checkpoints should be
loaded: PyTorch checkpoint deserialization is pickle-compatible.

## Bounded evaluation

```bash
ARTIFACTS="$(cd ../Artifacts && pwd)"
CLIP_BASE="$HOME/.cache/clip/ViT-B-32.pt"

python predactor_eval.py \
  --checkpoint "$ARTIFACTS/checkpoints/predactor/pdp051/latest.ckpt" \
  --checkpoint-sha256 2d963b32786f2989c6472726df9fcfe6b385590127e12e1f549a4b7d77488b2e \
  --clip-checkpoint "$ARTIFACTS/checkpoints/motionclip/g1-model-xyz-clip/checkpoint_0100.pth.tar" \
  --clip-checkpoint-sha256 66a127df4958b346089b2020f2705c7456d9db0ee8b4bd9518608b708b35fc3c \
  --clip-base "$CLIP_BASE" \
  --clip-base-sha256 40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af \
  --output /tmp/predactor-smoke-new \
  --steps 100 --device cpu --text stand
```

The command verifies every external input, restores the policy through the
normal evaluation loader, executes the requested number of real MuJoCo steps,
checks finite actions and simulator state, and confirms all PredActor imports
come from this tree. It prints `PREDACTOR_EVAL_PASS` only after completion.
Smoke success proves executable integration, not locomotion quality or safety.

The four retained configs are `g1prdp_cond_diffuse.yaml`,
`g1prdp_diffuse.yaml`, `g1rlobs_cond_dp.yaml`, and `g1_cond_diffuse.yaml`.
`predactor_eval.py` intentionally validates the full text-conditioned PredActor
profile only. `cond_eval.py` remains available for expert interactive use once
`PREDACTOR_ROOT`, `PREDACTOR_TEXT_CHECKPOINT`, and any device overrides are set.
