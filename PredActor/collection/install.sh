#!/usr/bin/env bash
set -euo pipefail

collection_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
deps_root="$collection_root/.deps"
isaaclab_root="$deps_root/IsaacLab"
isaaclab_commit="21f7136325136ca3f6ca4e0a8125edffe5c24f7e"
constraints="$collection_root/constraints.txt"

if [ "$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "3.10" ]; then
    echo "PredActor collection requires Python 3.10." >&2
    exit 2
fi

export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-120}"
export PIP_RETRIES="${PIP_RETRIES:-10}"

pip_install() {
    python -m pip install --constraint "$constraints" "$@"
}

# flatdict's legacy build imports pkg_resources; use the pinned build tools.
pip_install pip==24.3.1 setuptools==74.1.2 wheel==0.45.1 toml==0.10.2
pip_install --no-build-isolation flatdict==4.0.1
pip_install torch==2.5.1 torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cu121
pip_install 'isaacsim[all,extscache]==4.5.0' \
    --extra-index-url https://pypi.nvidia.com

mkdir -p "$deps_root"
if [ ! -d "$isaaclab_root/.git" ]; then
    git init "$isaaclab_root"
    git -C "$isaaclab_root" remote add origin https://github.com/isaac-sim/IsaacLab.git
fi
if [ "$(git -C "$isaaclab_root" rev-parse --verify HEAD 2>/dev/null || true)" != "$isaaclab_commit" ]; then
    if [ -n "$(git -C "$isaaclab_root" status --porcelain --untracked-files=no)" ]; then
        echo "IsaacLab has local changes at $isaaclab_root; use a clean v2.1.0 checkout." >&2
        exit 2
    fi
    for attempt in 1 2 3; do
        if git -C "$isaaclab_root" fetch --depth 1 origin tag v2.1.0; then
            break
        fi
        if [ "$attempt" -eq 3 ]; then
            exit 1
        fi
        sleep 5
    done
    git -C "$isaaclab_root" checkout --detach "$isaaclab_commit"
fi
test "$(git -C "$isaaclab_root" rev-parse HEAD)" = "$isaaclab_commit"

# Collection uses these four extensions and the bundled RSL-RL runtime.
# IsaacLab's general installer also installs unrelated RL/Mimic frameworks.
pip_install --no-build-isolation \
    -e "$isaaclab_root/source/isaaclab" \
    -e "$isaaclab_root/source/isaaclab_assets" \
    -e "$isaaclab_root/source/isaaclab_tasks" \
    -e "$isaaclab_root/source/isaaclab_rl" \
    -e "$collection_root/vendor/rsl_rl-modular-normed" \
    -e "$collection_root/source/rl_tracker" \
    hydra-core zarr numba onnxscript wandb pytorch-kinematics pillow pyyaml tqdm

python -m pip check
python -c 'import onnxscript, pytorch_kinematics, torch, wandb, zarr; print("PyTorch:", torch.__version__, "CUDA:", torch.cuda.is_available())'

echo "PredActor collection environment is ready."
