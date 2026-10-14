# Fine-tune the G1 motion encoder

The motion encoder maps a 60-frame G1 trajectory to a 512-dimensional CLIP
embedding. Fine-tuning updates the original MotionCLIP transformer encoder and
decoder, while keeping the released ViT-B/32 text encoder frozen.

## Install and download

Run from the public repository root. The regular locked environment contains
all dependencies for this stage; an Isaac Sim installation is not needed.

```bash
uv sync --locked
uv run --locked python scripts/hf_download.py --filter checkpoints/motionclip motions/g1_152fk
```

## Prepare motion and text pairs

Provide a JSON list of annotations. Each item supplies an NPZ motion and a text
caption describing that motion. Paths are relative to the annotation file.
For a segment-specific caption, include `start_frame` and `end_frame` (exclusive)
in the source frame rate. A caption without bounds applies to the entire motion.

```json
[
  {
    "motion": "motions/my_walk/motion.npz",
    "text": "walk forward",
    "body_order": "isaaclab"
  }
]
```

The filename above is an example: point it at your own annotated motion.
The released 152 trajectories can be used as motion inputs, but do not include
the BABEL text annotations used for original encoder training. Supply captions
for fine-tuning; the script does not infer them from filenames. A full AMASS/BABEL
training corpus requires the corresponding dataset access and annotations.

Each NPZ needs `fps` and either `body_pos_w` or `body_positions`, with shape
`[T, 30, 3]`, in metres. Set `body_order` to `isaaclab` for the released collection
trajectories or `motionclip` for semantic G1 body order. When `body_names` is
present, names determine the order. The canonical names are in
`PredActor/motion_encoder/src/datasets/g1_amass_utils.py`.

```bash
uv run --locked python PredActor/motion_encoder/prepare_data.py \
  --annotations Artifacts/encoder_annotations.json \
  --output Artifacts/dataset/motion_encoder/train.npz
```

Preparation reorders the 30 bodies, linearly resamples positions to 30 Hz, and
extracts 60-frame windows with a 30-frame stride. Each window is translated by
its first-frame pelvis position, matching the original G1 xyz loader. The
trajectory's heading and root movement are retained. Segments shorter than
60 resampled frames are rejected. The adjacent JSON receipt records input
hashes, captions, and preprocessing settings.

## Fine-tune

```bash
uv run --locked python PredActor/motion_encoder/finetune.py \
  --data Artifacts/dataset/motion_encoder/train.npz \
  --init-checkpoint Artifacts/checkpoints/motionclip/g1-model-xyz-clip/checkpoint_0100.pth.tar \
  --output Artifacts/runs/motion_encoder/finetune \
  --epochs 50 --batch-size 20 --num-workers 16 --device cuda
```

The learning rate is `1e-4` with AdamW. The original xyz reconstruction,
xyz-space reconstruction, and velocity losses each have weight 100; text cosine
loss has weight 1. This is text-supervised fine-tuning. It does not use the
rendered-image supervision from the original MotionCLIP training recipe.

For an installation smoke test, add `--epochs 1 --batch-size 2 --max-steps 2`
and choose a separate output directory. A successful run prints
`MOTION_ENCODER_FINETUNE_PASS` and writes losses, configuration, a receipt, and
`checkpoint.pth.tar`. A short smoke run demonstrates execution, not training
quality.

`--init-checkpoint` loads model weights and starts a new optimizer. New
fine-tuning checkpoints also contain optimizer state and support `--resume`
after a complete epoch:

```bash
uv run --locked python PredActor/motion_encoder/finetune.py \
  --data Artifacts/dataset/motion_encoder/train.npz \
  --resume Artifacts/runs/motion_encoder/finetune/checkpoint.pth.tar \
  --output Artifacts/runs/motion_encoder/continued --epochs 100 --num-workers 16
```

The original released checkpoint contains weights only. A smoke checkpoint
stopped part-way through an epoch can initialize weights, but cannot resume
the optimizer. Use a new output directory for each invocation.

## Use the encoder for data dyeing

The saved checkpoint includes the frozen CLIP state and can be passed directly
to the collection dyeing command:

```bash
uv run --locked python PredActor/collection/scripts/data_dyeing/data_dyeing.py \
  motionclip.checkpoint_path=Artifacts/runs/motion_encoder/finetune/checkpoint.pth.tar
```

## Source mapping

`MoDyeEnc/finetune.py`, `prepare_data.py`, and the selected `src/` modules map
into `PredActor/motion_encoder/`. The transformer, reconstruction and CLIP
losses are the original source implementation. The guide maps from the
PDPlanner distribution overlay to root `docs/motion_encoder.md`.

Root `pyproject.toml`, `uv.lock`, README, artifact download tools, and artifacts
remain public-repository owned. The encoder uses their existing locked
`torch`, `clip`, `numpy`, and `tqdm` dependencies. The additive export has no
installation or configuration changes for evaluation or collection.

Maintainers export an explicit committed MoDyeEnc revision:

```bash
python tools/dist_export.py --source . --ref <pdplanner-commit> \
  --profile motion_encoder --project-source <modyeenc-checkout> \
  --project-ref <modyeenc-commit> --output <new-payload-directory> \
  --evidence-dir <new-evidence-directory>
```

Sync `motion_encoder/` to public `PredActor/motion_encoder/` and `docs/` to
public root `docs/`, using the generated checksums. This additive profile owns
only those encoder paths; collection and evaluation come from their own
profiles. Keep export manifests outside the public payload.

The implementation is based on [MotionCLIP](https://github.com/GuyTevet/motion-clip).
Its MIT license is retained at `PredActor/motion_encoder/LICENSE`.
