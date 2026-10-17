#!/usr/bin/env bash
set -euo pipefail

RESOURCE_DIR=""
REQUIRE_TEXT=false

usage() {
  echo "Usage: $(basename "$0") --resource-dir DIR [--require-text]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-dir) RESOURCE_DIR="$2"; shift 2 ;;
    --require-text) REQUIRE_TEXT=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERROR] unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -d "$RESOURCE_DIR" ]] || { echo "[ERROR] valid --resource-dir required" >&2; exit 2; }
RESOURCE_DIR="$(cd "$RESOURCE_DIR" && pwd -P)"
MANIFEST="$RESOURCE_DIR/resource_manifest.yaml"

[[ -f "$MANIFEST" ]] || { echo "[ERROR] missing resource_manifest.yaml" >&2; exit 1; }
DEPLOY_REL="$(sed -n '/^runtime:/,/^[^ ]/s/^[[:space:]]*deploy_config:[[:space:]]*//p' "$MANIFEST" | head -1)"
DEPLOY_CONFIG="$RESOURCE_DIR/${DEPLOY_REL:-deploy_config.yaml}"
[[ "$DEPLOY_REL" != /* && "$DEPLOY_REL" != *".."* ]] || {
  echo "[ERROR] deploy config path escapes resource directory" >&2; exit 1;
}
[[ -f "$DEPLOY_CONFIG" ]] || { echo "[ERROR] missing deploy_config.yaml" >&2; exit 1; }
[[ -f "$RESOURCE_DIR/SHA256SUMS" ]] || { echo "[ERROR] missing SHA256SUMS" >&2; exit 1; }
if grep -Eq '  (\.\./|/)' "$RESOURCE_DIR/SHA256SUMS"; then
  echo "[ERROR] checksum entry escapes resource directory" >&2
  exit 1
fi

grep -Eq '^schema: diffusion_deploy\.resources$' "$MANIFEST" || {
  echo "[ERROR] unsupported resource manifest schema" >&2; exit 1;
}
grep -Eq '^schema_version: 1$' "$MANIFEST" || {
  echo "[ERROR] unsupported resource manifest version" >&2; exit 1;
}

# Runtime paths must remain relocatable. Check only known path-valued keys.
if grep -Eq '^[[:space:]]+(path|schedule_path|emphasis_path|urdf_path|deploy_config|fsm_config):[[:space:]]*"?/' \
    "$MANIFEST" "$DEPLOY_CONFIG"; then
  echo "[ERROR] absolute runtime path found" >&2
  exit 1
fi

(cd "$RESOURCE_DIR" && sha256sum -c SHA256SUMS)

TEXT_DIM="$(sed -n 's/^[[:space:]]*text_cond_dim:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$MANIFEST" | head -1)"
TEXT_TRANSPORT="$(sed -n '/^[[:space:]]*clip_encoder:/,/^[[:space:]]*artifacts:/s/^[[:space:]]*transport:[[:space:]]*//p' "$MANIFEST" | head -1)"
if [[ "$REQUIRE_TEXT" == true && "${TEXT_DIM:-0}" -gt 0 && "$TEXT_TRANSPORT" != "cached_float32_in_process" ]]; then
  CLIP_PATH="${DIFFUSION_DEPLOY_CLIP_PATH:-}"
  [[ -n "$CLIP_PATH" ]] || {
    echo "[ERROR] text commands require external DIFFUSION_DEPLOY_CLIP_PATH" >&2; exit 1;
  }
  [[ -e "$CLIP_PATH" ]] || {
    echo "[ERROR] DIFFUSION_DEPLOY_CLIP_PATH does not exist: $CLIP_PATH" >&2; exit 1;
  }
fi

echo "[PASS] model resources verified: $RESOURCE_DIR"
if [[ "${TEXT_DIM:-0}" -gt 0 ]]; then
  if [[ "$TEXT_TRANSPORT" == "cached_float32_in_process" ]]; then
    echo "[INFO] text conditioning uses validated in-process float32 caches"
  else
    echo "[INFO] text conditioning uses an external float32 UDP sender; CLIP is not bundled"
  fi
fi
