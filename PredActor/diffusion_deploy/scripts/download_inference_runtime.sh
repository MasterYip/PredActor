#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
source "${SCRIPT_DIR}/common.sh"

TARGET_DIR="${PROJECT_ROOT}/third_party/inference_runtime"
DOWNLOAD_TARGET="all"

if [[ $# -ge 1 ]]; then
  if [[ "$1" == "libtorch" || "$1" == "torch" || "$1" == "onnx" || "$1" == "all" ]]; then
    DOWNLOAD_TARGET="$1"
  else
    TARGET_DIR="$1"
    if [[ $# -ge 2 ]]; then
      DOWNLOAD_TARGET="$2"
    fi
  fi
fi

mkdir -p "${TARGET_DIR}"
OS_TYPE="$(uname -s)"
ARCH_TYPE="$(uname -m)"

LIBTORCH_VERSION="${LIBTORCH_VERSION:-2.5.1}"
ONNXRUNTIME_VERSION="1.22.0"
LIBTORCH_DIR="${TARGET_DIR}/libtorch"
ONNXRUNTIME_DIR="${TARGET_DIR}/onnxruntime"

is_libtorch_valid() {
  [[ -d "${LIBTORCH_DIR}/include" && -d "${LIBTORCH_DIR}/lib" ]] || return 1
  [[ -f "${LIBTORCH_DIR}/build-version" ]] || return 1

  local installed_version
  installed_version="$(tr -d '\r\n' < "${LIBTORCH_DIR}/build-version")"
  [[ "${installed_version}" == "${LIBTORCH_VERSION}" \
    || "${installed_version}" == "${LIBTORCH_VERSION}"+* ]]
}

is_onnxruntime_valid() {
  [[ -d "${ONNXRUNTIME_DIR}/include" && -d "${ONNXRUNTIME_DIR}/lib" ]]
}

download_file() {
  local url="$1"
  local output="$2"

  if has_cmd curl; then
    curl -L --progress-bar -o "${output}" "${url}"
  elif has_cmd wget; then
    wget --show-progress -O "${output}" "${url}"
  else
    print_error "curl or wget is required"
    exit 1
  fi
}

download_libtorch() {
  local url=""
  local archive_name=""

  case "${OS_TYPE}" in
    Darwin)
      if [[ "${ARCH_TYPE}" == "arm64" ]]; then
        url="https://download.pytorch.org/libtorch/cpu/libtorch-macos-arm64-${LIBTORCH_VERSION}.zip"
        archive_name="libtorch-macos-arm64-${LIBTORCH_VERSION}.zip"
      else
        url="https://download.pytorch.org/libtorch/cpu/libtorch-macos-x86_64-${LIBTORCH_VERSION}.zip"
        archive_name="libtorch-macos-x86_64-${LIBTORCH_VERSION}.zip"
      fi
      ;;
    Linux)
      if [[ "${ARCH_TYPE}" == "aarch64" ]]; then
        print_error "Generic Linux aarch64 LibTorch binary is not provided by this script."
        print_error "Use a platform-specific package (for example Jetson install flow)."
        exit 1
      fi
      url="https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-${LIBTORCH_VERSION}%2Bcpu.zip"
      archive_name="libtorch-cxx11-abi-shared-with-deps-${LIBTORCH_VERSION}+cpu.zip"
      ;;
    *)
      print_error "Unsupported OS for LibTorch: ${OS_TYPE}"
      exit 1
      ;;
  esac

  local archive_path="${TARGET_DIR}/${archive_name}"
  local tmp="${TARGET_DIR}/tmp_libtorch"

  print_info "Downloading LibTorch ${LIBTORCH_VERSION}"
  download_file "${url}" "${archive_path}"

  rm -rf "${tmp}" "${LIBTORCH_DIR}"
  mkdir -p "${tmp}"
  unzip -o -q "${archive_path}" -d "${tmp}"

  if [[ -d "${tmp}/libtorch" ]]; then
    mv "${tmp}/libtorch" "${LIBTORCH_DIR}"
  else
    print_error "Unexpected LibTorch archive layout"
    exit 1
  fi

  rm -rf "${tmp}" "${archive_path}"
  print_success "LibTorch installed at ${LIBTORCH_DIR}"
}

download_onnxruntime() {
  local url=""
  local archive_name=""

  case "${OS_TYPE}" in
    Darwin)
      if [[ "${ARCH_TYPE}" == "arm64" ]]; then
        url="https://github.com/microsoft/onnxruntime/releases/download/v${ONNXRUNTIME_VERSION}/onnxruntime-osx-arm64-${ONNXRUNTIME_VERSION}.tgz"
        archive_name="onnxruntime-osx-arm64-${ONNXRUNTIME_VERSION}.tgz"
      else
        url="https://github.com/microsoft/onnxruntime/releases/download/v${ONNXRUNTIME_VERSION}/onnxruntime-osx-x86_64-${ONNXRUNTIME_VERSION}.tgz"
        archive_name="onnxruntime-osx-x86_64-${ONNXRUNTIME_VERSION}.tgz"
      fi
      ;;
    Linux)
      if [[ "${ARCH_TYPE}" == "aarch64" ]]; then
        url="https://github.com/microsoft/onnxruntime/releases/download/v${ONNXRUNTIME_VERSION}/onnxruntime-linux-aarch64-${ONNXRUNTIME_VERSION}.tgz"
        archive_name="onnxruntime-linux-aarch64-${ONNXRUNTIME_VERSION}.tgz"
      else
        url="https://github.com/microsoft/onnxruntime/releases/download/v${ONNXRUNTIME_VERSION}/onnxruntime-linux-x64-${ONNXRUNTIME_VERSION}.tgz"
        archive_name="onnxruntime-linux-x64-${ONNXRUNTIME_VERSION}.tgz"
      fi
      ;;
    *)
      print_error "Unsupported OS for ONNX Runtime: ${OS_TYPE}"
      exit 1
      ;;
  esac

  local archive_path="${TARGET_DIR}/${archive_name}"
  local tmp="${TARGET_DIR}/tmp_onnx"

  print_info "Downloading ONNX Runtime ${ONNXRUNTIME_VERSION}"
  download_file "${url}" "${archive_path}"

  rm -rf "${tmp}" "${ONNXRUNTIME_DIR}"
  mkdir -p "${tmp}"
  tar -xzf "${archive_path}" -C "${tmp}"

  local extracted
  extracted="$(find "${tmp}" -maxdepth 1 -type d -name "onnxruntime-*" | head -n 1)"
  if [[ -z "${extracted}" || ! -d "${extracted}" ]]; then
    print_error "Unexpected ONNX Runtime archive layout"
    exit 1
  fi

  mv "${extracted}" "${ONNXRUNTIME_DIR}"
  rm -rf "${tmp}" "${archive_path}"
  print_success "ONNX Runtime installed at ${ONNXRUNTIME_DIR}"
}

case "${DOWNLOAD_TARGET}" in
  torch)
    DOWNLOAD_TARGET="libtorch"
    ;;
esac

case "${DOWNLOAD_TARGET}" in
  libtorch)
    if ! is_libtorch_valid; then
      download_libtorch
    else
      print_success "LibTorch already present: ${LIBTORCH_DIR}"
    fi
    ;;
  onnx)
    if ! is_onnxruntime_valid; then
      download_onnxruntime
    else
      print_success "ONNX Runtime already present: ${ONNXRUNTIME_DIR}"
    fi
    ;;
  all)
    if ! is_libtorch_valid; then
      download_libtorch
    else
      print_success "LibTorch already present: ${LIBTORCH_DIR}"
    fi

    if ! is_onnxruntime_valid; then
      download_onnxruntime
    else
      print_success "ONNX Runtime already present: ${ONNXRUNTIME_DIR}"
    fi
    ;;
  *)
    print_error "Usage: $0 [target_dir] [libtorch|torch|onnx|all] or $0 [libtorch|torch|onnx|all]"
    exit 1
    ;;
esac

print_success "Inference runtimes are ready"
