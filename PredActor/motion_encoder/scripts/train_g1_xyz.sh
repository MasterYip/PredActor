#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
"${PYTHON:-python}" -m src.train.train \
  --modelname motionclip_transformer_rc_vel \
  --clip_text_losses cosine --pose_rep xyz --clip_lambda_cosine 5.0 \
  --clip_training text --lambda_vel 100 --lambda_rc 100 --lambda_rcxyz 100 \
  --jointstype vertices --batch_size 20 --num_frames 60 --num_layers 8 \
  --lr 0.0001 --glob --translation --no-vertstrans --latent_dim 512 \
  --num_epochs 100 --snapshot 10 --device 0 --dataset g1_amass \
  --datapath ./data/g1_amass_db/amass_30fps_db.pt \
  --folder ./exps/g1-model-xyz-clip --use_g1 --num_workers 16 "$@"
