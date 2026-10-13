# Training

The offline trainer consumes the dyed zarr dataset and writes configs, logs,
and checkpoints below `outputs/`.

## Smoke test

From the public repository root:

```bash
uv sync --locked
uv run python PredActor/scripts/training_smoke.py
```

The smoke test creates a deterministic zarr fixture, runs one optimization
step through the PredActor state-action model, and checks the checkpoint.

## Train on the 152-motion dataset

After collection and data dyeing:

```bash
uv run python PredActor/train.py \
  --cfg g1prdp_cond_diffuse.yaml \
  --exp_name predactor_bc \
  dataset_dir="$PWD/Artifacts/dataset/g1_152fk" \
  dataset.zarr_path=motion_dyed_text_t0.01.zarr \
  training.num_epochs=50 \
  training.seed=42 \
  dataloader.num_workers=16 \
  logging.mode=offline
```

Use `training.device=cpu` for CPU training or `--gpu N` to select a CUDA
device. The supported dataset fields and G1 ordering are implemented in
`PredActor/diffusion_policy/dataset/g1_dataset.py`.

The full reproduction flow is:

```text
152 retargeted motions + RLTracker teacher
  -> raw zarr collection
  -> MotionCLIP dyeing
  -> PredActor behavior-cloning training
```
