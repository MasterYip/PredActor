# PredActor

PredActor is an evaluation-only distribution of the predictive action diffusion
controller for Unitree G1. This repository contains source and the G1 robot
description needed by MuJoCo. Policy checkpoints, MotionCLIP weights, datasets,
experiment outputs, and other learned artifacts are deliberately not included.

## Setup

Use Python 3.10 in a new environment. The versions below match the validated
runtime; a clean network installation remains a separate release gate.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r requirements-eval.txt
```

Run directly from the repository root. An editable install is unnecessary.
The supported release path is native MuJoCo evaluation; IsaacLab collection,
training, Unitree SDK/DDS, and hardware actuation are outside this distribution.

## External weights

Keep all learned weights outside this checkout. Obtain the selected policy
checkpoint, fine-tuned MotionCLIP checkpoint, and OpenAI CLIP ViT-B/32 base
weights from a source whose terms permit your use. Compute each identity before
running:

```bash
sha256sum /external/policy/latest.ckpt \
  /external/text/checkpoint_0100.pth.tar \
  /external/text/ViT-B-32.pt
```

The evaluator requires those three SHA-256 values and refuses files located
inside the repository. Only trusted checkpoints should be loaded: PyTorch
checkpoint deserialization is pickle-compatible.

## Bounded evaluation

```bash
python predactor_eval.py \
  --checkpoint /external/policy/latest.ckpt \
  --checkpoint-sha256 <64-hex-sha256> \
  --clip-checkpoint /external/text/checkpoint_0100.pth.tar \
  --clip-checkpoint-sha256 <64-hex-sha256> \
  --clip-base /external/text/ViT-B-32.pt \
  --clip-base-sha256 <64-hex-sha256> \
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
