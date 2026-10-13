#!/usr/bin/env bash
set -euo pipefail

collection_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
deps_root="$collection_root/.deps"
isaaclab_root="$deps_root/IsaacLab"

if [ "$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "3.10" ]; then
    echo "PredActor collection requires Python 3.10." >&2
    exit 2
fi

python -m pip install torch==2.5.1 torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cu121
python -m pip install --upgrade pip
python -m pip install 'isaacsim[all,extscache]==4.5.0' \
    --extra-index-url https://pypi.nvidia.com

mkdir -p "$deps_root"
if [ ! -d "$isaaclab_root/.git" ]; then
    git clone --branch v2.1.0 --depth 1 \
        https://github.com/isaac-sim/IsaacLab.git "$isaaclab_root"
fi
bash "$isaaclab_root/isaaclab.sh" -i

python -m pip uninstall rsl_rl_lib -y
python -m pip install -e "$collection_root/vendor/rsl_rl-modular-normed"
python -m pip install -e "$collection_root/source/rl_tracker"
python -m pip install hydra-core==1.3.2 zarr==2.18.3 numba==0.63.1 \
    onnxscript 'wandb>=0.19' pillow pyyaml tqdm

echo "PredActor collection environment is ready."
