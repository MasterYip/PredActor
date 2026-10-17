#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEPLOY_ROOT}/../.." && pwd)"

cd "${REPO_ROOT}"
git submodule update --init --recursive \
  PredActor/diffusion_deploy/deps/unitree_mujoco \
  PredActor/diffusion_deploy/deps/mujoco \
  PredActor/diffusion_deploy/deps/unitree_sdk2 \
  PredActor/diffusion_deploy/deps/cyclonedds \
  PredActor/diffusion_deploy/deps/unitree_sdk2_python

# Unitree MuJoCo expects MuJoCo at simulate/mujoco. Keep this link local to
# the checkout so no ~/.mujoco or PegasusMoDye path is required.
MUJOCO_LINK="${DEPLOY_ROOT}/deps/unitree_mujoco/simulate/mujoco"
MUJOCO_TARGET="../../mujoco"
if [[ -d "${DEPLOY_ROOT}/deps/unitree_mujoco/simulate" ]]; then
  if [[ -e "${MUJOCO_LINK}" && ! -L "${MUJOCO_LINK}" ]]; then
    echo "Refusing to replace non-symlink ${MUJOCO_LINK}" >&2
    exit 2
  fi
  ln -sfn "${MUJOCO_TARGET}" "${MUJOCO_LINK}"
fi

echo "Deployment submodules are ready under ${DEPLOY_ROOT}/deps."
