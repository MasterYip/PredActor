# Data collection

The collector runs the released RLTracker teacher in IsaacLab and writes the
state-action trajectories consumed by PredActor training.

## Inputs

Place the supplied motion set and teacher checkpoint at these default paths:

```text
Artifacts/
├── checkpoints/rl_tracker/model_75000.pt
└── motions/g1_152fk/
    ├── motion_001/motion.npz
    └── ...
```

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

Run deterministic collection from the public repository root.
With the supplied 152 motions, 50 episodes per motion gives 7,600 episodes:

```bash
bash PredActor/collection/collect_dataset.sh \
  --mode deterministic \
  --samples_per_motion 50 \
  --num_envs 1000 \
  --headless
```

The output is `Artifacts/dataset/g1_152fk_raw/motion.zarr`. Command-line `--checkpoint`,
`--motion_file`, and `--output_dir` values override those defaults.

For another motion set, use `--motion_file "my_motions/*"` under
`Artifacts/motions/`. The episode target is the number of matched motions
times `--samples_per_motion`. Use the same pattern for `input.motion_pattern`
when dyeing the dataset.

Use `--visualize` for the native Isaac Sim viewer or `--headless --livestream
2` for WebRTC. Run `bash PredActor/collection/collect_dataset.sh --help` for
the complete collection and noise options.

Next, [label the collected data](data_dyeing.md), then [train PredActor](training.md).
