#!/usr/bin/env bash
set -euo pipefail

collection_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
code_root="$(cd "$collection_root/.." && pwd)"
repo_root="$(cd "$code_root/.." && pwd)"

export PYTHONPATH="$code_root:$collection_root/source/rl_tracker:$collection_root/vendor/rsl_rl-modular-normed${PYTHONPATH:+:$PYTHONPATH}"
export PREDACTOR_ASSET_ROOT="${PREDACTOR_ASSET_ROOT:-$code_root/assets}"
export PREDACTOR_MOTION_ROOT="${PREDACTOR_MOTION_ROOT:-$repo_root/Artifacts/motions}"
export PREDACTOR_TRACKER_CHECKPOINT="${PREDACTOR_TRACKER_CHECKPOINT:-$repo_root/Artifacts/checkpoints/rl_tracker/model_75000.pt}"
export PREDACTOR_RAW_DATASET="${PREDACTOR_RAW_DATASET:-$repo_root/Artifacts/dataset/g1_152fk_raw}"

"${PYTHON:-python}" "$collection_root/scripts/verify_motion_set.py" \
    "$PREDACTOR_MOTION_ROOT/g1_152fk"

cd "$collection_root"
exec bash scripts/data_collection/collect_dataset.sh \
    --checkpoint "$PREDACTOR_TRACKER_CHECKPOINT" \
    --motion_file "g1_152fk/*" \
    --output_dir "$PREDACTOR_RAW_DATASET" \
    "$@"
