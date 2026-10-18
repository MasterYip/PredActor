#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(dirname "${SCRIPT_DIR}")"
LOCK="${SOURCE_ROOT}/deps/platform-lock.json"
PROFILE="jetson-jp5"
BASE="${HOME}/CodeSpace/PredActor"
PREFIX=""
CACHE=""
BUILD_DIR=""
MODEL_SOURCE=""
MODEL_NAME="policy"
ARTIFACT_DIR=""
OFFLINE=0
DRY_RUN=0
SKIP_SMOKE=0

usage() {
  cat <<'EOF'
User-local, no-publish installer for diffusion_deploy on G1 JetPack 5.

Usage:
  ./scripts/install_g1_jp5.sh --model-dir PATH [options]

Options:
  --base PATH          User-owned root (default: ~/CodeSpace/PredActor)
  --model-dir PATH     Exported model resource directory to verify and install
  --model-name NAME    Stable model label (default: policy)
  --artifact-dir PATH  Seed cache from pinned wheel/source archives in PATH
  --offline            Disable all dependency downloads; require cache hits
  --dry-run            Validate platform and print the plan without writes
  --skip-smoke         Install without model verification/offline inference
  -h, --help           Show this help

This installer never uses sudo, apt, /usr, /etc, systemd, ldconfig, or robot
command channels. The CMake publish lock is always forced OFF.
EOF
}

die() { printf '[install_g1_jp5] ERROR: %s\n' "$*" >&2; exit 2; }
log() { printf '[install_g1_jp5] %s\n' "$*"; }

while (($#)); do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --model-dir) MODEL_SOURCE="$2"; shift 2 ;;
    --model-name) MODEL_NAME="$2"; shift 2 ;;
    --artifact-dir) ARTIFACT_DIR="$2"; shift 2 ;;
    --offline) OFFLINE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --skip-smoke) SKIP_SMOKE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

BASE="$(realpath -m "${BASE}")"
case "${BASE}/" in
  "$(realpath -m "${HOME}")"/*) ;;
  *) die "--base must remain below the invoking user's home directory" ;;
esac
PREFIX="${BASE}/install/diffusion-deploy"
CACHE="${BASE}/cache"
BUILD_DIR="${BASE}/build/diffusion-deploy-${PROFILE}"

[[ "$(uname -s)" == Linux ]] || die "requires Linux"
[[ "$(uname -m)" == aarch64 ]] || die "requires aarch64; found $(uname -m)"
[[ -r /etc/nv_tegra_release ]] || die "Jetson L4T release file is missing"
grep -Eq '^# R35 \(release\), REVISION: 3\.1([,[:space:]]|$)' /etc/nv_tegra_release \
  || die "requires Jetson Linux R35.3.1 (JetPack 5.1.1)"
for command in python3 cmake c++ git sha256sum; do
  command -v "${command}" >/dev/null 2>&1 || die "required command missing: ${command}"
done

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
[[ "${PYTHON_VERSION}" == 3.8 ]] || die "requires Python 3.8; found ${PYTHON_VERSION}"
export PYTHONPATH="${SOURCE_ROOT}/python${PYTHONPATH:+:${PYTHONPATH}}"
MANAGER=(python3 -m diffusion_deploy_manager.cli --lock "${LOCK}")

# Non-interactive JetPack shells often omit CUDA from PATH. Set CUDACXX only
# for this process tree; never edit shell profiles or system configuration.
CUDACXX="$(python3 -c 'from diffusion_deploy_manager.profiles import discover_cuda_compiler; print(discover_cuda_compiler())')" \
  || die "unable to discover the locked JetPack CUDA compiler"
export CUDACXX
log "using CUDA compiler ${CUDACXX} (per-process CUDACXX)"

log "running locked platform doctor"
"${MANAGER[@]}" doctor --profile "${PROFILE}"

if [[ -z "${MODEL_SOURCE}" && "${SKIP_SMOKE}" -eq 0 ]]; then
  die "--model-dir is required unless --skip-smoke is explicitly used"
fi
if [[ -n "${MODEL_SOURCE}" ]]; then
  MODEL_SOURCE="$(realpath -m "${MODEL_SOURCE}")"
  [[ -d "${MODEL_SOURCE}" ]] || die "model resource directory not found: ${MODEL_SOURCE}"
  [[ -f "${MODEL_SOURCE}/deploy_config.yaml" ]] || die "deploy_config.yaml missing from model resource directory"
  for resource in g1_policy_backbone.pt ddpm_schedule.pt emphasis_matrices.pt; do
    [[ -f "${MODEL_SOURCE}/${resource}" ]] \
      || die "required model resource missing: ${resource}"
  done
  if grep -Rqs 'g1_prdp_standard_notext' "${MODEL_SOURCE}"; then
    die "obsolete g1_prdp_standard_notext profile found; re-export with g1_prdp_standard"
  fi
  grep -Eq 'data_profile:[[:space:]]*g1_prdp_standard([[:space:]#]|$)' \
    "${MODEL_SOURCE}/deploy_config.yaml" \
    || die "deploy config must use data_profile: g1_prdp_standard"
  if [[ -f "${MODEL_SOURCE}/SHA256SUMS" ]]; then
    (cd "${MODEL_SOURCE}" && sha256sum -c SHA256SUMS)
  fi
fi
[[ "${MODEL_NAME}" =~ ^[A-Za-z0-9._-]+$ ]] || die "--model-name contains unsafe characters"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  log "DRY RUN: base=${BASE} prefix=${PREFIX} cache=${CACHE} build=${BUILD_DIR}"
  log "DRY RUN: CUDACXX=${CUDACXX}; model source=${MODEL_SOURCE:-none}"
  if [[ -n "${ARTIFACT_DIR}" ]]; then
    "${MANAGER[@]}" seed-cache --profile "${PROFILE}" \
      --artifact-dir "${ARTIFACT_DIR}" --cache-dir "${CACHE}"
  fi
  "${MANAGER[@]}" bootstrap --profile "${PROFILE}" --prefix "${PREFIX}" \
    --cache-dir "${CACHE}" $([[ "${OFFLINE}" -eq 1 ]] && printf '%s' --offline)
  "${MANAGER[@]}" build --profile "${PROFILE}" --prefix "${PREFIX}" \
    --build-dir "${BUILD_DIR}" --source "${SOURCE_ROOT}"
  "${MANAGER[@]}" install --profile "${PROFILE}" --prefix "${PREFIX}" \
    --build-dir "${BUILD_DIR}" --source "${SOURCE_ROOT}"
  exit 0
fi

umask 077
mkdir -p "${BASE}" "${CACHE}" "${BASE}/build" "${BASE}/install" "${BASE}/logs"

if [[ -n "${ARTIFACT_DIR}" ]]; then
  log "seeding checksum-pinned cache from ${ARTIFACT_DIR}"
  "${MANAGER[@]}" seed-cache --profile "${PROFILE}" \
    --artifact-dir "${ARTIFACT_DIR}" --cache-dir "${CACHE}" --execute
fi

BOOTSTRAP=("${MANAGER[@]}" bootstrap --profile "${PROFILE}" --prefix "${PREFIX}" \
  --cache-dir "${CACHE}" --execute)
[[ "${OFFLINE}" -eq 1 ]] && BOOTSTRAP+=(--offline)
"${BOOTSTRAP[@]}"
"${MANAGER[@]}" build --profile "${PROFILE}" --prefix "${PREFIX}" \
  --build-dir "${BUILD_DIR}" --source "${SOURCE_ROOT}" --execute

COMMIT="$(git -C "${SOURCE_ROOT}" rev-parse HEAD)"
RELEASE="${PREFIX}/releases/${COMMIT}"
if [[ -e "${RELEASE}" ]]; then
  log "release already exists; verifying instead of overwriting"
  "${MANAGER[@]}" verify --release "${RELEASE}"
else
  "${MANAGER[@]}" install --profile "${PROFILE}" --prefix "${PREFIX}" \
    --build-dir "${BUILD_DIR}" --source "${SOURCE_ROOT}" --execute
fi
"${MANAGER[@]}" verify --release "${RELEASE}"

MODEL_DIR=""
if [[ -n "${MODEL_SOURCE}" ]]; then
  MODEL_HASH_FILES=(deploy_config.yaml g1_policy_backbone.pt ddpm_schedule.pt emphasis_matrices.pt)
  [[ ! -f "${MODEL_SOURCE}/deploy_config.yaml.wbg.yaml" ]] \
    || MODEL_HASH_FILES+=(deploy_config.yaml.wbg.yaml)
  MODEL_DIGEST="$(cd "${MODEL_SOURCE}" && sha256sum "${MODEL_HASH_FILES[@]}" \
    | sha256sum | awk '{print $1}')"
  MODEL_DIR="${BASE}/models/${MODEL_NAME}-${MODEL_DIGEST:0:12}"
  if [[ -e "${MODEL_DIR}" ]]; then
    [[ -d "${MODEL_DIR}" ]] || die "model install path exists but is not a directory: ${MODEL_DIR}"
    log "model release already exists; verifying instead of overwriting"
  else
    mkdir -p "${BASE}/models"
    MODEL_PARTIAL="${MODEL_DIR}.partial.$$"
    [[ ! -e "${MODEL_PARTIAL}" ]] || die "stale model staging path exists: ${MODEL_PARTIAL}"
    mkdir "${MODEL_PARTIAL}"
    cp -a "${MODEL_SOURCE}/." "${MODEL_PARTIAL}/"
    # Export candidates may intentionally be immutable. cp -a also copies the
    # source directory mode onto MODEL_PARTIAL, so reopen only this private
    # staging tree while paths and manifests are generated.
    find "${MODEL_PARTIAL}" -type d -exec chmod u+rwx {} +
    find "${MODEL_PARTIAL}" -type f -exec chmod u+rw {} +
    python3 "${SOURCE_ROOT}/tools/rebase_model_resources.py" \
      --model-dir "${MODEL_PARTIAL}" \
      --urdf-source "${RELEASE}/share/diffusion_deploy/resources/g1/main.urdf" \
      --provenance-source "${RELEASE}/share/diffusion_deploy/resources/g1/PROVENANCE.md"
    find "${MODEL_PARTIAL}" -type f -exec chmod 0400 {} +
    find "${MODEL_PARTIAL}" -type d -exec chmod 0500 {} +
    mv "${MODEL_PARTIAL}" "${MODEL_DIR}"
  fi
  (cd "${MODEL_DIR}" && sha256sum -c SHA256SUMS)
fi

if [[ "${SKIP_SMOKE}" -eq 0 ]]; then
  VERIFY="${RELEASE}/share/diffusion_deploy/scripts/verify_model_resources.sh"
  [[ -x "${VERIFY}" ]] || die "model verifier missing from release"
  "${VERIFY}" --resource-dir "${MODEL_DIR}"
  (cd "${MODEL_DIR}" && sha256sum -c SHA256SUMS)
  log "running one-step Offline/NoPublish inference smoke"
  TORCH_LIB="${PREFIX}/deps/torch-jetson-jp5-2.1/torch/lib"
  FK_LIB="${PREFIX}/runtime/cmeel.prefix-20c033f8605c/lib"
  export LD_LIBRARY_PATH="${TORCH_LIB}:${FK_LIB}:${PREFIX}/runtime/lib:/usr/local/cuda/lib64:/usr/local/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
  "${RELEASE}/bin/run_g1_robot" --config "${MODEL_DIR}/deploy_config.yaml" \
    --mode offline --device cuda:0 --max-steps 1 --no-fsm
fi

log "PASS: immutable release ${RELEASE}"
[[ -z "${MODEL_DIR}" ]] || log "PASS: immutable model resources ${MODEL_DIR}"
log "Rollback: select a prior verified release path; no current symlink was changed."
log "ReceiveOnly is documented but is not entered automatically by this installer."
