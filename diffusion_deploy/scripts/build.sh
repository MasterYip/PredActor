#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
source "${SCRIPT_DIR}/common.sh"

BACKEND="none"           # none | onnx | torch
BUILD_TYPE="Release"
BUILD_DIR="${PROJECT_ROOT}/build"
BUILD_DIR_EXPLICIT=0
USE_UNITREE_SDK2="OFF"
USE_FK="OFF"
ENABLE_COMMAND_PUBLISH="OFF"
CLEAN="OFF"
JOBS="$(nproc 2>/dev/null || echo 4)"
DOWNLOAD_RUNTIME="none"  # none | onnx | torch | all | auto
EXTRA_CMAKE_ARGS=()

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --backend <none|onnx|torch>   Select inference backend (default: none)
  --with-sdk2                   Enable Unitree SDK2 compile flag
  --with-fk                     Enable Pinocchio forward kinematics (USE_FK=ON)
  --with-command-publish        Enable the rt/lowcmd motor-control path
  --build-type <type>           CMake build type (default: Release)
  --build-dir <path>            Build directory (default: ./build)
  --jobs <N>                    Parallel jobs for build (default: nproc)
  --clean                       Remove build directory before configure
  --download-runtime <mode>     none|onnx|torch|all|auto
  --cmake-arg <arg>             Extra CMake arg, repeatable
  -h, --help                    Show this help

Examples:
  ./build.sh
  ./build.sh --backend onnx --download-runtime auto
  ./build.sh --backend torch --download-runtime auto --cmake-arg -DCMAKE_PREFIX_PATH=/opt/libtorch
  ./build.sh --backend onnx --with-sdk2
  ./build.sh --backend torch --with-sdk2 --with-fk
  ./build.sh --backend torch --with-sdk2 --with-fk --with-command-publish
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend)
      BACKEND="$2"
      shift 2
      ;;
    --with-sdk2)
      USE_UNITREE_SDK2="ON"
      shift
      ;;
    --with-fk)
      USE_FK="ON"
      shift
      ;;
    --with-command-publish)
      ENABLE_COMMAND_PUBLISH="ON"
      shift
      ;;
    --build-type)
      BUILD_TYPE="$2"
      shift 2
      ;;
    --build-dir)
      BUILD_DIR="$2"
      BUILD_DIR_EXPLICIT=1
      shift 2
      ;;
    --jobs)
      JOBS="$2"
      shift 2
      ;;
    --clean)
      CLEAN="ON"
      shift
      ;;
    --download-runtime)
      DOWNLOAD_RUNTIME="$2"
      shift 2
      ;;
    --cmake-arg)
      EXTRA_CMAKE_ARGS+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      print_error "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ "${BACKEND}" != "none" && "${BACKEND}" != "onnx" && "${BACKEND}" != "torch" ]]; then
  print_error "--backend must be one of: none, onnx, torch"
  exit 1
fi

if [[ "${ENABLE_COMMAND_PUBLISH}" == "ON" && "${USE_UNITREE_SDK2}" != "ON" ]]; then
  print_error "--with-command-publish requires --with-sdk2"
  exit 1
fi

if [[ "${DOWNLOAD_RUNTIME}" == "auto" ]]; then
  DOWNLOAD_RUNTIME="${BACKEND}"
fi

# Normalize runtime alias so torch backend requests libtorch artifacts.
if [[ "${DOWNLOAD_RUNTIME}" == "torch" ]]; then
  DOWNLOAD_RUNTIME="libtorch"
fi

# JetPack has no generic aarch64 LibTorch archive. Route supported L4T tuples
# through the checksum-pinned, user-local dependency manager. Generic Linux
# amd64 keeps the legacy downloader.
JETSON_LOCKED_PROFILE=""
if [[ "${DOWNLOAD_RUNTIME}" == "libtorch" \
      && "$(uname -s)" == Linux && "$(uname -m)" == aarch64 \
      && -r /etc/nv_tegra_release ]]; then
  if grep -Eq '^# R35 \(release\), REVISION: 3\.1([,[:space:]]|$)' /etc/nv_tegra_release; then
    JETSON_LOCKED_PROFILE="jetson-jp5"
  elif grep -Eq '^# R36 \(release\), REVISION: 4\.3([,[:space:]]|$)' /etc/nv_tegra_release; then
    JETSON_LOCKED_PROFILE="jetson-jp6"
  else
    print_error "unsupported Jetson L4T tuple; no locked deployment profile"
    exit 1
  fi
fi

if [[ -n "${JETSON_LOCKED_PROFILE}" ]]; then
  LOCK="${PROJECT_ROOT}/deps/platform-lock.json"
  DEPLOY_BASE="${DIFFUSION_DEPLOY_BASE:-${HOME}/CodeSpace/HoffMan}"
  DEPLOY_PREFIX="${DIFFUSION_DEPLOY_PREFIX:-${DEPLOY_BASE}/install/diffusion-deploy}"
  DEPLOY_CACHE="${DIFFUSION_DEPLOY_CACHE:-${DEPLOY_BASE}/cache}"
  export PYTHONPATH="${PROJECT_ROOT}/python${PYTHONPATH:+:${PYTHONPATH}}"
  MANAGER=(python3 -m diffusion_deploy_manager.cli --lock "${LOCK}")
  print_info "${JETSON_LOCKED_PROFILE} detected; bootstrapping locked NVIDIA Torch and FK runtime"
  "${MANAGER[@]}" doctor --profile "${JETSON_LOCKED_PROFILE}"
  "${MANAGER[@]}" bootstrap --profile "${JETSON_LOCKED_PROFILE}" \
    --prefix "${DEPLOY_PREFIX}" --cache-dir "${DEPLOY_CACHE}" --execute
  readarray -t PROFILE_VALUES < <(python3 - "${LOCK}" "${JETSON_LOCKED_PROFILE}" <<'PY'
import json, sys
lock = json.load(open(sys.argv[1], encoding="utf-8"))
profile = lock["profiles"][sys.argv[2]]
torch_id = profile["torch_artifact"]
print(torch_id)
print(lock["artifacts"][torch_id]["root"])
print(profile["unitree_sdk2_artifact"])
print(lock["artifacts"][profile["unitree_sdk2_artifact"]]["root"])
print(profile["cuda_standard"])
print(profile["cuda_arch"])
PY
  )
  TORCH_ARTIFACT="${PROFILE_VALUES[0]}"
  TORCH_PREFIX="${DEPLOY_PREFIX}/deps/${TORCH_ARTIFACT}/${PROFILE_VALUES[1]}"
  CMEEL_PREFIX="$(python3 -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["fk_runtime_prefix"])' \
    "${DEPLOY_PREFIX}/bootstrap-manifest.json")"
  FMT_SOURCE="${DEPLOY_PREFIX}/deps/fmt-9.1.0/fmt-9.1.0"
  SPDLOG_SOURCE="${DEPLOY_PREFIX}/deps/spdlog-1.15.3/spdlog-1.15.3"
  FMT_PREFIX="${DEPLOY_PREFIX}/runtime"
  SDK2_SOURCE="${DEPLOY_PREFIX}/deps/${PROFILE_VALUES[2]}/${PROFILE_VALUES[3]}"
  if [[ ! -f "${TORCH_PREFIX}/share/cmake/Torch/TorchConfig.cmake" ]]; then
    print_error "locked Jetson Torch CMake package missing after bootstrap"
    exit 1
  fi
  if [[ ! -f "${CMEEL_PREFIX}/lib/cmake/pinocchio/pinocchioConfig.cmake" ]]; then
    print_error "locked Pinocchio CMake package missing after bootstrap"
    exit 1
  fi
  if [[ "${USE_UNITREE_SDK2}" == "ON" ]]; then
    if [[ ! -f "${SDK2_SOURCE}/lib/aarch64/libunitree_sdk2.a" \
          || ! -f "${SDK2_SOURCE}/include/unitree/idl/hg/LowState_.hpp" ]]; then
      print_error "locked G1-capable Unitree SDK2 archive missing after bootstrap"
      exit 1
    fi
  fi
  if [[ ! -f "${FMT_PREFIX}/lib/cmake/fmt/fmt-config.cmake" ]]; then
    FMT_BUILD="${DEPLOY_PREFIX}/build/fmt-9.1.0-${JETSON_LOCKED_PROFILE}"
    cmake -S "${FMT_SOURCE}" -B "${FMT_BUILD}" \
      -DCMAKE_INSTALL_PREFIX="${FMT_PREFIX}" -DFMT_TEST=OFF -DFMT_DOC=OFF -DFMT_INSTALL=ON
    cmake --build "${FMT_BUILD}" --target install -j2
  fi
  if [[ ! -f "${FMT_PREFIX}/lib/cmake/spdlog/spdlogConfig.cmake" ]]; then
    SPDLOG_BUILD="${DEPLOY_PREFIX}/build/spdlog-1.15.3-${JETSON_LOCKED_PROFILE}"
    cmake -S "${SPDLOG_SOURCE}" -B "${SPDLOG_BUILD}" \
      -DCMAKE_INSTALL_PREFIX="${FMT_PREFIX}" -DCMAKE_PREFIX_PATH="${FMT_PREFIX}" \
      -DSPDLOG_BUILD_TESTS=OFF -DSPDLOG_BUILD_EXAMPLE=OFF \
      -DSPDLOG_BUILD_BENCH=OFF
    cmake --build "${SPDLOG_BUILD}" --target install -j2
  fi
  export CMAKE_PREFIX_PATH="${TORCH_PREFIX};${FMT_PREFIX};${CMEEL_PREFIX}${CMAKE_PREFIX_PATH:+;${CMAKE_PREFIX_PATH}}"
  if [[ -z "${CUDACXX:-}" && -x /usr/local/cuda/bin/nvcc ]]; then
    export CUDACXX=/usr/local/cuda/bin/nvcc
  fi
  export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.7}"
  if [[ "${BUILD_DIR_EXPLICIT}" -eq 0 ]]; then
    SOURCE_REV="$(git -C "${PROJECT_ROOT}" rev-parse --short=12 HEAD)"
    BUILD_DIR="${DEPLOY_BASE}/build/diffusion-deploy-${SOURCE_REV}-${JETSON_LOCKED_PROFILE}-fk-sdk2"
  fi
  EXTRA_CMAKE_ARGS+=(
    "-DDEPLOY_PROFILE=${JETSON_LOCKED_PROFILE}" "-DDEPLOY_LOCK_FILE=${LOCK}"
    "-DUNITREE_SDK2_PATH=${SDK2_SOURCE}" "-DUNITREE_CYCLONEDDS_PATH=/usr/local"
    # Keep legacy FindCUDA and modern FindCUDAToolkit on the same spelling.
    # Keep the stable symlink spelling across CMake's CUDA discovery modules.
    "-DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda"
    "-DCUDA_NVCC_EXECUTABLE=/usr/local/cuda/bin/nvcc"
    "-DCUDA_TOOLKIT_INCLUDE=/usr/local/cuda/include"
    "-DCMAKE_CUDA_STANDARD=${PROFILE_VALUES[4]}"
    "-DTORCH_CUDA_ARCH_LIST=${PROFILE_VALUES[5]}"
    "-DENABLE_UNITREE_COMMAND_PUBLISH=${ENABLE_COMMAND_PUBLISH}")
  DOWNLOAD_RUNTIME="none"
fi

if [[ "${DOWNLOAD_RUNTIME}" != "none" ]]; then
  print_info "Preparing runtime dependencies (${DOWNLOAD_RUNTIME})"
  "${SCRIPT_DIR}/download_inference_runtime.sh" "${PROJECT_ROOT}/third_party/inference_runtime" "${DOWNLOAD_RUNTIME}"
fi

USE_ONNX="OFF"
USE_TORCH="OFF"
CMAKE_PREFIX_PATH_ARG=""
ONNXRUNTIME_ROOT_ARG=""

if [[ "${BACKEND}" == "onnx" ]]; then
  USE_ONNX="ON"

  if [[ -z "${ONNXRUNTIME_ROOT:-}" && -d "${PROJECT_ROOT}/third_party/inference_runtime/onnxruntime" ]]; then
    export ONNXRUNTIME_ROOT="${PROJECT_ROOT}/third_party/inference_runtime/onnxruntime"
  fi

  if [[ -n "${ONNXRUNTIME_ROOT:-}" ]]; then
    ONNXRUNTIME_ROOT_ARG="-DONNXRUNTIME_ROOT=${ONNXRUNTIME_ROOT}"
  else
    print_warning "ONNXRUNTIME_ROOT is not set. CMake will fail if ONNX is enabled and runtime is missing."
  fi
fi

if [[ "${BACKEND}" == "torch" ]]; then
  USE_TORCH="ON"

  if [[ -z "${CMAKE_PREFIX_PATH:-}" && -d "${PROJECT_ROOT}/third_party/inference_runtime/libtorch" ]]; then
    export CMAKE_PREFIX_PATH="${PROJECT_ROOT}/third_party/inference_runtime/libtorch"
  fi

  if [[ -n "${CMAKE_PREFIX_PATH:-}" ]]; then
    CMAKE_PREFIX_PATH_ARG="-DCMAKE_PREFIX_PATH=${CMAKE_PREFIX_PATH}"
  else
    print_warning "CMAKE_PREFIX_PATH is not set. CMake will fail if Torch is enabled and libtorch is missing."
  fi
fi

if [[ "${CLEAN}" == "ON" ]]; then
  print_info "Cleaning build directory: ${BUILD_DIR}"
  rm -rf "${BUILD_DIR}"
fi

# ---- Pinocchio (cmeel) prefix detection ----
# When installed via pip/conda as a cmeel wheel, pinocchio's cmake config lives
# inside the cmeel.prefix directory next to the Python package.  CMake can't
# find it unless that path is on CMAKE_PREFIX_PATH.
if [[ "${USE_FK}" == "ON" ]]; then
  CMEEL_PREFIX=""
  # Prefer the Python from the active conda/venv environment so we see the
  # packages installed there, not the base env's Python.
  PYTHON_BIN=""
  if [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
    PYTHON_BIN="${CONDA_PREFIX}/bin/python"
  elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
  else
    PYTHON_BIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
  fi
  if [[ -n "${PYTHON_BIN}" ]]; then
    CMEEL_PREFIX="$("${PYTHON_BIN}" -c \
      "import importlib.util, pathlib; \
       s = importlib.util.find_spec('cmeel'); \
       p = pathlib.Path(s.origin).parent.parent / 'cmeel.prefix' if s else None; \
       print(p if p and p.is_dir() else '')" 2>/dev/null || true)"
  fi
  # Fallback: search conda envs for a cmeel.prefix that contains pinocchio cmake config
  if [[ -z "${CMEEL_PREFIX}" ]]; then
    for _env_root in \
        "${HOME}/miniforge3/envs"/* \
        "${HOME}/miniconda3/envs"/* \
        "${HOME}/anaconda3/envs"/* \
        "/opt/conda/envs"/*; do
      _candidate="${_env_root}/lib/python3."*"/site-packages/cmeel.prefix"
      # shellcheck disable=SC2086
      for _p in ${_candidate}; do
        if [[ -f "${_p}/lib/cmake/pinocchio/pinocchioConfig.cmake" ]]; then
          CMEEL_PREFIX="${_p}"
          break 2
        fi
      done
    done
  fi
  if [[ -n "${CMEEL_PREFIX}" ]]; then
    print_info "Pinocchio cmeel prefix detected: ${CMEEL_PREFIX}"
    # Some conda packages (notably urdfdom_headers) install their CMake files
    # at the environment prefix while Pinocchio itself lives in cmeel.prefix.
    CMEEL_ENV_PREFIX="$(cd "${CMEEL_PREFIX}/../../../.." && pwd -P)"
    if [[ -n "${CMAKE_PREFIX_PATH:-}" ]]; then
      CMAKE_PREFIX_PATH="${CMAKE_PREFIX_PATH};${CMEEL_ENV_PREFIX};${CMEEL_PREFIX}"
    else
      CMAKE_PREFIX_PATH="${CMEEL_ENV_PREFIX};${CMEEL_PREFIX}"
    fi
    CMAKE_PREFIX_PATH_ARG="-DCMAKE_PREFIX_PATH=${CMAKE_PREFIX_PATH}"
  else
    print_warning "--with-fk: could not auto-detect cmeel prefix for Pinocchio."
    print_warning "  Set CMAKE_PREFIX_PATH manually if pinocchio is not found."
  fi
fi

mkdir -p "${BUILD_DIR}"

print_info "Configuring CMake"
cmake -S "${PROJECT_ROOT}" -B "${BUILD_DIR}" \
  -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
  -DUSE_ONNX="${USE_ONNX}" \
  -DUSE_TORCH="${USE_TORCH}" \
  -DUSE_UNITREE_SDK2="${USE_UNITREE_SDK2}" \
  -DUSE_FK="${USE_FK}" \
  -DENABLE_UNITREE_COMMAND_PUBLISH="${ENABLE_COMMAND_PUBLISH}" \
  ${ONNXRUNTIME_ROOT_ARG:+"${ONNXRUNTIME_ROOT_ARG}"} \
  ${CMAKE_PREFIX_PATH_ARG:+"${CMAKE_PREFIX_PATH_ARG}"} \
  "${EXTRA_CMAKE_ARGS[@]+"${EXTRA_CMAKE_ARGS[@]}"}"

print_info "Building targets"
cmake --build "${BUILD_DIR}" -j "${JOBS}"

print_success "Build complete"
print_info "Executable: ${BUILD_DIR}/run_g1_robot"
