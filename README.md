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
> Evaluation, data collection, MotionCLIP labeling, and BC training code are
> available. The diffusion-deploy source and release runbooks are included;
> deployed policy packages are supplied separately.

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

## Deployment

The `diffusion_deploy/` directory contains the C++ runtime, exporter, G1
assets, platform lock, and launch scripts. The short release guide covers the
paper-default policy export and the three supported paths:

- [MuJoCo sim2sim](docs/deployment.md#a-mujoco-sim2sim)
- [wired workstation to G1](docs/deployment.md#b-wired-workstation-deployment)
- [onboard Jetson G1](docs/deployment.md#c-onboard-g1-deployment)

The latest deployment reference is the Task165 PDP067 Standard2 full DDIM-2
package. Its 605-D condition excludes `base_lin_vel`; the package and learned
graph are external to this source repository and must be checked by SHA-256
before installation.

## Reproduce collection and training

Download the default set of 152 G1 motion trajectories, RLTracker checkpoint,
and G1 MotionCLIP checkpoint:

```bash
uv run --locked python scripts/hf_download.py --filter checkpoints motions/g1_152fk
```

```bash
# IsaacLab collection environment
conda create --override-channels -c conda-forge -n predactor-collection python=3.10 -y
conda activate predactor-collection
bash PredActor/collection/install.sh

# Collect 7,600 episodes from the 152 motions
bash PredActor/collection/collect_dataset.sh \
  --mode deterministic --samples_per_motion 50 --num_envs 1000 --headless

# Return to the repository uv environment, dye the collected trajectories, then train
conda deactivate
uv run python PredActor/collection/scripts/data_dyeing/data_dyeing.py

# Train the text-conditioned policy
uv run python PredActor/train.py \
  --cfg g1prdp_cond_diffuse.yaml --exp_name predactor_bc \
  dataset_dir="$PWD/Artifacts/dataset/g1_152fk" \
  dataset.zarr_path=motion_dyed_text_t0.01.zarr \
  training.num_epochs=50 training.seed=42 dataloader.num_workers=16 \
  logging.mode=offline
```

To train the condition-free PRDP baseline on the same collected/dyed zarr:

```bash
uv run python PredActor/train.py \
  --cfg g1prdp_diffuse.yaml --exp_name predactor_bc_unconditional \
  dataset_dir="$PWD/Artifacts/dataset/g1_152fk" \
  dataset.zarr_path=motion_dyed_text_t0.01.zarr \
  training.seed=42 dataloader.num_workers=16 \
  logging.mode=offline
```

`g1prdp_diffuse.yaml` does not use the text latent at inference; the same dyed
zarr is used so both runs share the collection and dataset layout.

Artifact placement and environment details are in the
[collection](docs/data_collection.md),
[data dyeing](docs/data_dyeing.md),
[training](docs/training.md), and
[motion encoder](docs/motion_encoder.md) guides.

## Evaluate your trained model

Set `run_dir` to the directory printed by training:

```bash
run_dir="outputs/<run-directory>"
uv run --locked predactor-eval \
  --checkpoint "$run_dir/checkpoints/latest.ckpt" \
  --config "$run_dir/resolved_config.yaml" \
  --output_dir "$run_dir/eval" \
  --web-ui
```

Open `http://127.0.0.1:8765/` to control the model. Add `--web-perturb` for
mouse perturbations or `--web-port 8766` to use another port.

## Train the motion encoder (Experimental)

Train G1 MotionCLIP with the original G1 xyz recipe: G1-retargeted AMASS motions,
BABEL labels, and a trainable CLIP text encoder. Follow the
[motion encoder guide](docs/motion_encoder.md) to prepare the training database,
then run from the repository root:

```bash
uv run --locked bash PredActor/motion_encoder/scripts/train_g1_xyz.sh
```

This runs 100 epochs with 16 data-loader workers and writes
`PredActor/motion_encoder/exps/g1-model-xyz-clip/checkpoint_0100.pth.tar`.
It does not initialize from the released MotionCLIP checkpoint.

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

**Release checklist**

- [x] **Evaluation:** browser-based MuJoCo evaluation, G1 assets, and published checkpoints.
- [x] **Data collection and labeling:** IsaacLab motion collection and MotionCLIP dataset labeling tools.
- [x] **BC training:** behavior-cloning training code, configurations, and reproducibility smoke test.
- [ ] **DAgger:** interactive data aggregation and policy refinement pipeline.
- [x] **Deployment:** diffusion-deploy source, G1 assets, export tooling, and runbooks.

## Demos

Each result is independently playable below. Visit the
[project website](https://masteryip.github.io/predactor.github.io/#evidence)
for the complete gallery.

### Hardware

<table>
  <tr>
    <td width="50%" valign="top">
      <strong>Text control</strong><br>
      <sub>Walk, squat down, and return to walking.</sub><br>
      <video src="https://github.com/user-attachments/assets/f6c25169-5c14-49c9-9bb2-50a9151432a8" controls width="100%"></video>
    </td>
    <td width="50%" valign="top">
      <strong>Behavior transitions</strong><br>
      <sub>Walk, accelerate to a jog, and transition into a squat.</sub><br>
      <video src="https://github.com/user-attachments/assets/6cf29b10-9150-48df-8241-320124bc0b95" controls width="100%"></video>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <strong>Physical interaction</strong><br>
      <sub>Walk and stand commands under external interference.</sub><br>
      <video src="https://github.com/user-attachments/assets/f39231c8-96c7-4a8d-b239-d23ac460a5e4" controls width="100%"></video>
    </td>
    <td width="50%" valign="top">
      <strong>Outdoor pathway</strong><br>
      <sub>Outdoor locomotion on the physical G1.</sub><br>
      <video src="https://github.com/user-attachments/assets/04141756-978a-4b25-9a8f-237cfa1c7ca4" controls width="100%"></video>
    </td>
  </tr>
</table>

### Simulation

<table>
  <tr>
    <td width="50%" valign="top">
      <strong>Joystick steering</strong><br>
      <sub>Directional steering with text-selected locomotion modes.</sub><br>
      <video src="https://github.com/user-attachments/assets/f5735ad1-efa1-4036-ab3f-709727daff5b" controls width="100%"></video>
    </td>
    <td width="50%" valign="top">
      <strong>Text and joystick</strong><br>
      <sub>Text-selected behavior with simultaneous directional control.</sub><br>
      <video src="https://github.com/user-attachments/assets/909137a3-0800-43ca-a00c-18b6c40ef026" controls width="100%"></video>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <strong>Text control</strong><br>
      <sub>Behavior selection and transitions from text commands.</sub><br>
      <video src="https://github.com/user-attachments/assets/2355d8a0-aa95-4ab2-a45f-3bc75c4f46a9" controls width="100%"></video>
    </td>
    <td width="50%" valign="top">
      <strong>Semantic interpolation</strong><br>
      <sub>Continuous control between semantic motion endpoints.</sub><br>
      <video src="https://github.com/user-attachments/assets/9e5e946b-ea85-479d-9d83-70b9a7a5012c" controls width="100%"></video>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <strong>Target tracking</strong><br>
      <sub>Classifier-guided destination following.</sub><br>
      <video src="https://github.com/user-attachments/assets/5d2b4f99-d7cf-42b3-ab70-202e107910fc" controls width="100%"></video>
    </td>
    <td width="50%" valign="top">
      <strong>Disturbance response</strong><br>
      <sub>Recovery behavior under external perturbations.</sub><br>
      <video src="https://github.com/user-attachments/assets/4752669d-dcc1-481b-8b8f-c40b8f5c2fd9" controls width="100%"></video>
    </td>
  </tr>
</table>

## Acknowledgements

We thank the authors of the following open-source projects:

- [diffusion_implementation](https://github.com/WhoKnowsssss/diffusion_implementation) by WhoKnowsssss, which provides the diffusion training framework.
- [TextOp](https://github.com/TeleHuman/TextOp), which provides the RL tracker training framework and pretrained tracker checkpoint.
- [MotionCLIP](https://github.com/GuyTevet/motion-clip), which provides the motion encoder foundation.

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

## License

The contents of this repository are released under the [MIT License](LICENSE), unless noted otherwise.

## Contact & Community

- **Discord:** [Join the PredActor community](https://discord.gg/3ZsNAvzxZy) for discussion and project updates.
- **X:** [@MasterYip3](https://x.com/MasterYip3) for author updates and project news.

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <strong>PredActor WeChat group</strong><br><br>
      <a href="docs/assets/community/wechat-group-20261020.png"><img src="docs/assets/community/wechat-group-20261020.png" width="240" alt="PredActor WeChat discussion group QR code, valid through October 20, 2026"></a><br>
      <sub>Valid through October 20, 2026.</sub>
    </td>
    <td width="50%" align="center" valign="top">
      <strong>Contact Author</strong><br><br>
      <a href="docs/assets/community/wechat-contact.png"><img src="docs/assets/community/wechat-contact.png" width="240" alt="Author WeChat contact QR code"></a><br>
      <sub>Direct contact with the author.</sub>
    </td>
  </tr>
</table>

Scan a QR code with WeChat, or click it to view the full-size image. If the group QR code has expired or the group is full, contact the author on WeChat.
