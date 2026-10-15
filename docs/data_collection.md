# Data collection

The collector runs the released RLTracker teacher in IsaacLab and writes the
state-action trajectories consumed by PredActor training.

## Inputs

Place the 152 retargeted motions and teacher checkpoint at these paths:

```text
Artifacts/
├── checkpoints/rl_tracker/model_75000.pt
└── motions/g1_152fk/
    ├── motion_001/motion.npz
    └── ...
```

The teacher checkpoint is a required learned artifact. It is not inferred from
the motion files or MotionCLIP checkpoint.

Download both inputs from the PredActor artifact repository:

```bash
uv run --locked python scripts/hf_download.py \
  --filter checkpoints/rl_tracker motions/g1_152fk
```

## Install

Collection uses Python 3.10, Isaac Sim 4.5.0, and Isaac Lab 2.1.0 in a separate
environment:

```bash
conda create --override-channels -c conda-forge -n predactor-collection python=3.10 -y
conda activate predactor-collection
bash PredActor/collection/install.sh
```

The installer keeps IsaacLab below `PredActor/collection/.deps/` and installs
the exported RLTracker task, RSL-RL runtime, and CUDA forward-kinematics library.
It applies `PredActor/collection/constraints.txt` throughout installation and
runs `pip check` before reporting success.

For an Aliyun Python package mirror, use:

```bash
PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
  bash PredActor/collection/install.sh
```

PyTorch and Isaac Sim still use their CUDA/NVIDIA package indexes. After a
network interruption, rerun the same installer; completed downloads and the
IsaacLab checkout are reused.

## Collect

Run the 152-motion deterministic collection from the public repository root:

```bash
bash PredActor/collection/collect_dataset.sh \
  --mode deterministic \
  --samples_per_motion 1 \
  --num_envs 16 \
  --headless
```

The wrapper resolves the motions and checkpoint from `Artifacts/` and writes
`Artifacts/dataset/g1_152fk_raw/motion.zarr`. Command-line `--checkpoint`,
`--motion_file`, and `--output_dir` values override those defaults.

The collection command is the first step of the normal reproduce flow. An
optional layout check is available when debugging an installation:

```bash
python PredActor/collection/scripts/collection_preflight.py
```

Use `--visualize` for the native Isaac Sim viewer or `--headless --livestream
2` for WebRTC. Run `bash PredActor/collection/collect_dataset.sh --help` for
the complete collection and noise options. After collection, continue with
the dyeing command in the next guide; no separate preflight step is required.
