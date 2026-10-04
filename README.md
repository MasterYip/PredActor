<p align="center">
  <a href="https://masteryip.github.io/predactor.github.io/">
    <img src="docs/assets/predactor-readme-banner.svg" width="100%" alt="PredActor: predictive action diffusion for steerable onboard humanoid control. Internal future states, direct actions, CG and CFG guidance, and 50 Hz onboard execution.">
  </a>
</p>

<h1 align="center">PredActor: Predictive Action Diffusion for Steerable Onboard Humanoid Control</h1>

<p align="center">
  <a href="https://masteryip.github.io/predactor.github.io/"><img alt="Project website" src="https://img.shields.io/badge/Project_Website-E7A12B?style=for-the-badge&logo=googlechrome&logoColor=171817"></a>
  <a href="#demos"><img alt="Demo videos" src="https://img.shields.io/badge/Demo_Videos-7895A6?style=for-the-badge&logo=youtube&logoColor=white"></a>
  <a href="#quick-evaluation"><img alt="Evaluation code available" src="https://img.shields.io/badge/Code-Evaluation_Release-5A5A57?style=for-the-badge"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/License-MIT-ECECEA?style=for-the-badge&labelColor=2F2F2D&color=ECECEA"></a>
</p>

<p align="center">
  <img src="docs/assets/institution-strip.svg" width="100%" alt="Harbin Institute of Technology, Shanghai Innovation Institute, RoboParty Lab, Tsinghua University, Shanghai Jiao Tong University, HexLab, and SFTR">
</p>

> [!IMPORTANT]
> This release supports browser-based and bounded MuJoCo evaluation of the
> published PDP051 checkpoint. Training, IsaacLab data collection, and robot
> deployment are not part of the public evaluation interface.

## Quick evaluation

The supported path uses Python 3.10 on Linux. It runs directly from the
checkout and does not require Isaac Sim, RLTracker, training data, or an
editable package install.

```bash
git clone https://github.com/MasterYip/PredActor.git
cd PredActor

conda create -n predactor-eval python=3.10 pip -y
conda activate predactor-eval
python -m pip install --upgrade pip
python -m pip install setuptools==74.0.0
python -m pip install torch==2.5.1 torchvision==0.20.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install --no-build-isolation -r PredActor/requirements-eval.txt
```

For NVIDIA acceleration, replace the PyTorch index URL with
`https://download.pytorch.org/whl/cu121`.

Download the PredActor and fine-tuned MotionCLIP checkpoints from the public
[artifact repository](https://huggingface.co/MasterYip/PredActor_Artifacts).
The helper recreates the published layout under the Git-ignored
`./Artifacts/` directory and verifies the checkpoint byte sizes and SHA-256
identities.

```bash
python scripts/hf_download.py --filter checkpoints
```

Launch the browser-based MuJoCo evaluation from the repository root:

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

The command opens `http://127.0.0.1:8765/` automatically. `--headless`
disables the native MuJoCo window; simulation and rendering still run in the
browser. On an NVIDIA system, use `--device cuda:0 --fk-device cuda:0` for GPU
inference.

The local-to-remote directory map is explicit in
[`scripts/hf_manifest.yaml`](scripts/hf_manifest.yaml). Maintainers can inspect
the map and remote state or preview an upload without changing the Hub:

```bash
python scripts/hf_download.py --list
python scripts/hf_manage.py status
python scripts/hf_upload.py --dry-run
```

For a finite command-line integration check, also download the OpenAI CLIP
ViT-B/32 base weights used by the bounded evaluator:

```bash
python - <<'PY'
from pathlib import Path
import clip

cache = Path.home() / ".cache" / "clip"
clip.load("ViT-B/32", device="cpu", download_root=str(cache))
print(cache / "ViT-B-32.pt")
PY
```

Then run the bounded headless smoke test:

```bash
ARTIFACTS="$PWD/Artifacts"
CLIP_BASE="$HOME/.cache/clip/ViT-B-32.pt"
cd PredActor

python predactor_eval.py \
  --checkpoint "$ARTIFACTS/checkpoints/predactor/pdp051/latest.ckpt" \
  --checkpoint-sha256 2d963b32786f2989c6472726df9fcfe6b385590127e12e1f549a4b7d77488b2e \
  --clip-checkpoint "$ARTIFACTS/checkpoints/motionclip/g1-model-xyz-clip/checkpoint_0100.pth.tar" \
  --clip-checkpoint-sha256 66a127df4958b346089b2020f2705c7456d9db0ee8b4bd9518608b708b35fc3c \
  --clip-base "$CLIP_BASE" \
  --clip-base-sha256 40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af \
  --output "/tmp/predactor-smoke-$(date +%s)" \
  --steps 100 --device cpu --text stand
```

Success ends with `PREDACTOR_EVAL_PASS 100 steps` and writes
`validation.json` plus the resolved runtime config beneath the selected output
directory. This is an integration smoke test, not a locomotion-quality or
robot-safety claim. Add `--viewer`, increase `--steps`, and select an available
CUDA device for an interactive MuJoCo run.

## Overview

**PredActor** augments action diffusion with an internal future-state trajectory for look-ahead guidance while retaining direct action execution. Within a joint state-action formulation, it predicts future states and actions from proprioceptive history and optional task context. Unlike a generator-tracker pipeline, predicted states remain inside the policy rather than becoming motion references for a separate tracker. Unlike action-only diffusion, the policy provides an explicit future-state trajectory for guidance.

This representation supports two complementary steering mechanisms: **classifier guidance (CG)** applies test-time objectives to predicted states, and **classifier-free guidance (CFG)** strengthens learned behavior conditions, including text commands. The selected action is sent directly to the joint controller; policy observations require only proprioception, not externally estimated full-body states.

For onboard execution, rolling denoising and computation-preserving runtime optimizations support **50 Hz control on a Unitree G1's Jetson Orin NX**. The measured complete callback takes **16.790 ms median and 19.383 ms p95**, both below the 20 ms control period. Across simulation and physical-robot evaluation, demonstrations cover text commands, disturbance response, joystick steering, and semantic interpolation.

## Project preview

<p align="center">
  <a href="https://masteryip.github.io/predactor.github.io/">
    <img src="./docs/assets/predactor-preview.png" width="100%" alt="PredActor humanoid control project preview">
  </a>
</p>

### At a glance

- **Predictive direct control:** jointly predicts future states and actions, keeps states internal, and executes the selected action without a separate motion-reference tracker.
- **Proprioceptive inputs:** conditions on onboard proprioceptive history without requiring externally estimated full-body states as policy inputs.
- **CG and CFG steering:** combines test-time objectives on predicted states with learned behavior conditioning.
- **Rolling onboard inference:** reuses the denoising horizon across control ticks and optimizes runtime for 50 Hz operation on Jetson Orin NX.
- **Simulation and hardware evidence:** demonstrates commands, transitions, steering, and disturbance response.

## Demos

Click any preview to open the corresponding MP4 video. Videos are hosted by the public project website and are not duplicated in this repository.

<p align="center">
  <a href="https://masteryip.github.io/predactor.github.io/static/videos/hoffman-mujoco-comprehensive.mp4">
    <img src="https://masteryip.github.io/predactor.github.io/static/videos/posters/hoffman-mujoco-comprehensive.jpg" width="100%" alt="Comprehensive PredActor simulation demo">
  </a>
</p>

<p align="center"><strong>Comprehensive simulation</strong><br><sub>Text commands, joystick steering, external interference, and semantic interpolation in one sequence.</sub></p>

<table>
  <tr>
    <td width="50%" align="center">
      <a href="https://masteryip.github.io/predactor.github.io/static/videos/hoffman-behavioral-reaction.mp4"><img src="https://masteryip.github.io/predactor.github.io/static/videos/posters/hoffman-behavioral-reaction.jpg" width="100%" alt="PredActor hardware reaction demo"></a><br>
      <strong>Hardware · Physical interaction</strong><br>
      <sub>Walk and stand commands under external interference.</sub>
    </td>
    <td width="50%" align="center">
      <a href="https://masteryip.github.io/predactor.github.io/static/videos/hoffman-text-walk-squat-walk.mp4"><img src="https://masteryip.github.io/predactor.github.io/static/videos/posters/hoffman-text-walk-squat-walk.jpg" width="100%" alt="PredActor walk squat walk hardware demo"></a><br>
      <strong>Hardware · Text control</strong><br>
      <sub>Walk, squat down, and return to walking.</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <a href="https://masteryip.github.io/predactor.github.io/static/videos/hoffman-text-walk-jog-squat.mp4"><img src="https://masteryip.github.io/predactor.github.io/static/videos/posters/hoffman-text-walk-jog-squat.jpg" width="100%" alt="PredActor walk jog squat hardware demo"></a><br>
      <strong>Hardware · Behavior transitions</strong><br>
      <sub>Walk, accelerate to a jog, and transition into a squat.</sub>
    </td>
    <td width="50%" align="center">
      <a href="https://masteryip.github.io/predactor.github.io/static/videos/hoffman-joystick-steering.mp4"><img src="https://masteryip.github.io/predactor.github.io/static/videos/posters/hoffman-joystick-steering.jpg" width="100%" alt="PredActor joystick steering simulation demo"></a><br>
      <strong>Simulation · Joystick steering</strong><br>
      <sub>Directional steering with text-selected locomotion modes.</sub>
    </td>
  </tr>
</table>

## Resources

| Resource | Description |
| --- | --- |
| [Project website](https://masteryip.github.io/predactor.github.io/) | Method overview, figures, authorship, and the complete demo gallery |
| [Public repository](https://github.com/MasterYip/PredActor) | MuJoCo evaluation code and release updates |
| [Evaluation artifacts](https://huggingface.co/MasterYip/PredActor_Artifacts) | Hash-pinned PDP051 policy and G1 MotionCLIP checkpoints |
| [Demo collection](https://masteryip.github.io/predactor.github.io/#evidence) | Simulation and hardware evidence in the browser |
| Paper and citation | Coming soon |

## Release scope

The public package contains the evaluation code and G1 assets required for the
MuJoCo paths above. Learned weights remain in the separate Hugging Face
artifact repository. Training, dataset generation, experiment orchestration,
IsaacLab integration, and hardware control are intentionally excluded.

## License

The contents of this repository are released under the [MIT License](LICENSE), unless noted otherwise.
