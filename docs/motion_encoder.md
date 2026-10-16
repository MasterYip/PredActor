# Train the G1 motion encoder (Experimental)

The G1 MotionCLIP model maps 60-frame robot motions and text descriptions into
a shared 512-dimensional space. This guide follows the G1 XYZ training recipe
in MoDyeEnc: prepare G1-retargeted AMASS with BABEL captions, then train the
motion encoder, decoder, and text encoder for 100 epochs.

## Install

From the public repository root:

```bash
uv sync --locked
source .venv/bin/activate
cd PredActor/motion_encoder
```

Run the commands below from `PredActor/motion_encoder/`. The locked environment
includes the training and preprocessing dependencies. This XYZ path uses body
positions directly; it does not need Isaac Sim, SMPL body models, or rendered
AMASS images.

## Prepare the dataset

You need G1-retargeted AMASS trajectories and the corresponding
[BABEL](https://babel.is.tue.mpg.de/) `train.json` and `val.json` annotations.
Obtain the datasets under their respective access and license terms.
The 152 collection trajectories in `PredActor_Artifacts` are not the full
AMASS/BABEL encoder-training dataset.

Use this layout:

```text
PredActor/motion_encoder/
  data/
    g1_retargeted_amass/
      ACCAD/<subject>/<sequence>_poses_120_jpos.npz
      CMU/<subject>/<sequence>_poses_120_jpos.npz
      ...
    babel_v1.0_release/
      train.json
      val.json
```

The numeric suffix can differ, such as `_poses_30_jpos.npz`. Directory names
and original sequence names must match BABEL's `feat_p` paths. For example,
`ACCAD/<subject>/<sequence>_poses_120_jpos.npz` is matched to the annotation for
`ACCAD/<subject>/<sequence>_poses.npz`.

Each retargeted NPZ must contain:

| Field | Shape | Meaning |
|---|---|---|
| `dof_positions` | `(T, 29)` | G1 joint angles, in radians |
| `body_positions` | `(T, 30, 3)` | World-frame body positions, in metres |
| `fps` | Scalar or one-element array | Source frame rate |

The 30 bodies must follow `G1_BODY_NAMES` in
`src/datasets/g1_amass_utils.py`, with pelvis first. If `body_names` is included,
the parser checks that order. IsaacLab's body order is different and must be
remapped before using these files. Optional fields include joint velocities,
body linear/angular velocities, and body quaternion rotations `(T, 30, 4)`;
these are not used by the XYZ training input.

The upstream README links
[AMASS Retargeted for G1](https://huggingface.co/datasets/ember-lab-berkeley/AMASS_Retargeted_for_G1).
Check its file format before using it here: this parser requires the NPZ schema
above, not an arbitrary retargeted motion format. Renaming a different format
does not convert its coordinates or body ordering.

Parse the dataset:

```bash
python src/datasets/g1_amass_parser.py \
  --input_dir ./data/g1_retargeted_amass \
  --output_dir ./data/g1_amass_db \
  --dataset_name amass \
  --babel_dir ./data/babel_v1.0_release \
  --target_fps 30
```

Prepare the trajectories at 30 Hz. The parser checks the source frame rate and
skips rates more than 5 Hz from the requested rate; it is not a general
120-to-30 Hz converter. The numeric filename suffix does not determine `fps`.

For a complete annotated dataset, the parser writes:

```text
data/g1_amass_db/
  amass_30fps_train.pt
  amass_30fps_vald.pt
  amass_30fps_test.pt
```

| Split | AMASS subsets |
|---|---|
| train | BioMotionLab_NTroje, Eyes_Japan_Dataset, TotalCapture, KIT, ACCAD, CMU, MPI_Limits, TCD_handMocap, EKUT |
| vald | HumanEva, MPI_HDM05, SFU, MPI_mosh |
| test | Transitions_mocap, SSM_synced |

Only motions with matching BABEL annotations are included. Empty splits are
reported and not saved. Choose a new output directory when regenerating an
existing database. The `_db.pt` path used below is a loader placeholder: the
loader substitutes `_train.pt`, `_vald.pt`, or `_test.pt`. There is no separate
`amass_30fps_db.pt` file to create.

Check the training split:

```bash
python - <<'PY'
from src.datasets.g1_amass import G1AMASS
dataset = G1AMASS(
    datapath='./data/g1_amass_db/amass_30fps_db.pt',
    split='train', use_g1=True, num_frames=60, pose_rep='xyz')
print('Dataset size:', len(dataset))
print('Sample shape:', dataset[0]['inp'].shape)  # [30, 3, 60]
print('Caption:', dataset[0]['clip_text'])
PY
```

The loader divides sequences into 100-frame chunks and samples 60 consecutive
frames per training example. Each sample is translated by its first-frame
pelvis position. Heading and movement relative to that starting position are
retained. A sequence needs at least 100 frames to yield a training chunk.

## Train

This is the original G1 XYZ command, with 16 data-loader workers:

```bash
python -m src.train.train --modelname motionclip_transformer_rc_vel \
  --clip_text_losses cosine --pose_rep xyz \
  --clip_lambda_cosine 5.0 \
  --clip_training text \
  --lambda_vel 100 --lambda_rc 100 --lambda_rcxyz 100 \
  --jointstype vertices --batch_size 20 --num_frames 60 --num_layers 8 \
  --lr 0.0001 --glob --translation --no-vertstrans --latent_dim 512 \
  --num_epochs 100 --snapshot 10 --device 0 \
  --dataset g1_amass \
  --datapath ./data/g1_amass_db/amass_30fps_db.pt \
  --folder ./exps/g1-model-xyz-clip \
  --use_g1 --num_workers 16
```

The first run downloads OpenAI's standard `ViT-B/32` CLIP weights into the CLIP
cache (normally `~/.cache/clip`). It needs network access unless those weights
are already cached. The motion transformer starts with new weights. As in the
original implementation, `--clip_training text` then calls CLIP's parameter
initializer for its text tower and trains that tower together with the motion
model. This command does not load or fine-tune the released G1 checkpoint.

The model name selects reconstruction and velocity losses, each weighted 100.
The trainable-text branch uses symmetric text/motion cross entropy. Although
the original command includes `--clip_text_losses cosine` and
`--clip_lambda_cosine 5.0`, this branch does not use a cosine loss. Likewise,
`--lambda_rcxyz 100` does not add an XYZ loss when `rcxyz` is absent from the
model name.

The convenience script supplies the same arguments:

```bash
bash scripts/train_g1_xyz.sh
```

Or launch it from the public repository root without activating the environment:

```bash
uv run --locked bash PredActor/motion_encoder/scripts/train_g1_xyz.sh
```

For a bounded installation check on your prepared dataset, use a separate
output directory:

```bash
bash scripts/train_g1_xyz.sh \
  --folder ./exps/g1-xyz-smoke \
  --num_epochs 1 --snapshot 1 --batch_size 2 --max_steps 1
```

The smoke run checks execution, not model quality. Use at least two differently
captioned examples so the text/motion contrastive loss has distinct pairs.

Checkpoints are saved every 10 epochs. A complete run produces
`exps/g1-model-xyz-clip/checkpoint_0100.pth.tar`, along with `opt.yaml`,
`training.log`, TensorBoard events, and `training_receipt.json`. The checkpoint
contains the motion model and learned CLIP weights. These historical-format
checkpoints do not include optimizer state.

## Use the trained encoder

Pass the trained checkpoint to [data dyeing](data_dyeing.md). From the public
repository root, after collecting the trajectories:

```bash
uv run --locked python PredActor/collection/scripts/data_dyeing/data_dyeing.py \
  motionclip.checkpoint_path=PredActor/motion_encoder/exps/g1-model-xyz-clip/checkpoint_0100.pth.tar
```

Based on [MotionCLIP](https://github.com/GuyTevet/motion-clip), with the original
license retained in `PredActor/motion_encoder/LICENSE`.
