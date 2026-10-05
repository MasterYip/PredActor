<p align="center">
  <a href="https://masteryip.github.io/predactor.github.io/">
    <img src="docs/assets/predactor-readme-banner.svg" width="100%" alt="PredActor: predictive action diffusion for steerable onboard humanoid control. Internal future states, direct actions, CG and CFG guidance, and 50 Hz onboard execution.">
  </a>
</p>

<h1 align="center">PredActor: Predictive Action Diffusion for Steerable Onboard Humanoid Control</h1>

<p align="center">
  <a href="https://masteryip.github.io/predactor.github.io/"><img alt="Project website" src="https://img.shields.io/badge/Project_Website-E7A12B?style=for-the-badge&logo=googlechrome&logoColor=171817"></a>
  <a href="https://arxiv.org/abs/2609.24840"><img alt="arXiv paper" src="https://img.shields.io/badge/arXiv-2609.24840-B31B1B?style=for-the-badge&logo=arxiv&logoColor=white"></a>
  <a href="#demos"><img alt="Demo videos" src="https://img.shields.io/badge/Demo_Videos-7895A6?style=for-the-badge&logo=youtube&logoColor=white"></a>
  <a href="#quick-evaluation"><img alt="Evaluation code available" src="https://img.shields.io/badge/Code-Evaluation_Release-5A5A57?style=for-the-badge"></a>
  <a href="https://huggingface.co/MasterYip/PredActor_Artifacts"><img alt="Hugging Face artifacts" src="https://img.shields.io/badge/Hugging_Face-Artifacts-FFD21E?style=for-the-badge&logo=huggingface&logoColor=171817"></a>
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

Install [uv](https://docs.astral.sh/uv/), then run these commands on Linux:

```bash
git clone https://github.com/MasterYip/PredActor.git
cd PredActor
uv sync --locked
uv run --locked python scripts/hf_download.py --filter checkpoints
uv run --locked predactor-eval
```

The download command retrieves the released checkpoints from
[MasterYip/PredActor_Artifacts](https://huggingface.co/MasterYip/PredActor_Artifacts).

The last command opens `http://127.0.0.1:8765/`. It uses CUDA when available
and otherwise falls back to CPU. The locked environment targets Python 3.10
and includes the evaluator, MuJoCo, and the browser interface; Isaac Sim and
the training repositories are not required.

For a headless startup, use `uv run --locked predactor-eval --headless
--web-no-browser`. Run `uv run --locked predactor-eval --help` for optional
checkpoint, config, device, and Web UI overrides.

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
| [Paper](https://arxiv.org/abs/2609.24840) | arXiv preprint and citation |

## Citation

```bibtex
@misc{ye2026predactorpredictiveactiondiffusion,
  title={PredActor: Predictive Action Diffusion for Steerable Onboard Humanoid Control},
  author={Lei Ye and Haibo Gao and Yitang Li and Peng Xu and Zetong Jing and Junhan Sun and Fanrong Dong and Ziqi Han and Xue Wang and Jianhua Sun and Cewu Lu and Hao Zhao and Liang Ding},
  year={2026},
  eprint={2609.24840},
  archivePrefix={arXiv},
  primaryClass={cs.RO},
  url={https://arxiv.org/abs/2609.24840},
}
```

## Release scope

The public package contains the evaluation code and G1 assets required for the
MuJoCo paths above. Learned weights remain in the separate Hugging Face
artifact repository. Training, dataset generation, experiment orchestration,
IsaacLab integration, and hardware control are intentionally excluded.

## License

The contents of this repository are released under the [MIT License](LICENSE), unless noted otherwise.
