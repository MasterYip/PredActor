#!/usr/bin/env bash
set -euo pipefail

BUILD_DIR=""
OUTPUT_DIR=""
TARGET_ARCH="$(uname -m)"
ASSETS=()

usage() {
  cat <<USAGE
Usage: $(basename "$0") --build-dir DIR --output DIR [options]

Installs a relocatable diffusion_deploy tree and writes SHA256SUMS.
The output directory must not already exist.

Options:
  --asset SOURCE:RELATIVE_DEST  Copy an exported asset into the bundle (repeatable)
  --target-arch ARCH            Require installed ELF files to match ARCH
  -h, --help                    Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-dir) BUILD_DIR="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --asset) ASSETS+=("$2"); shift 2 ;;
    --target-arch) TARGET_ARCH="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERROR] unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$BUILD_DIR" && -d "$BUILD_DIR" ]] || { echo "[ERROR] valid --build-dir required" >&2; exit 2; }
[[ -n "$OUTPUT_DIR" ]] || { echo "[ERROR] --output required" >&2; exit 2; }
[[ ! -e "$OUTPUT_DIR" ]] || { echo "[ERROR] output already exists: $OUTPUT_DIR" >&2; exit 2; }

mkdir -p "$OUTPUT_DIR"
cmake --install "$BUILD_DIR" --prefix "$OUTPUT_DIR"

for spec in "${ASSETS[@]}"; do
  source_path="${spec%%:*}"
  relative_dest="${spec#*:}"
  [[ "$source_path" != "$spec" && -f "$source_path" ]] || {
    echo "[ERROR] --asset must be an existing SOURCE:RELATIVE_DEST pair: $spec" >&2
    exit 2
  }
  [[ "$relative_dest" != /* && "$relative_dest" != *".."* ]] || {
    echo "[ERROR] asset destination must stay inside bundle: $relative_dest" >&2
    exit 2
  }
  install -D -m 0644 "$source_path" "$OUTPUT_DIR/$relative_dest"
done

while IFS= read -r -d '' candidate; do
  description="$(file -b "$candidate")"
  if [[ "$description" == *ELF* ]]; then
    case "$TARGET_ARCH" in
      aarch64|arm64) [[ "$description" == *ARM\ aarch64* ]] || { echo "[ERROR] non-aarch64 ELF: $candidate: $description" >&2; exit 1; } ;;
      x86_64|amd64) [[ "$description" == *x86-64* ]] || { echo "[ERROR] non-x86_64 ELF: $candidate: $description" >&2; exit 1; } ;;
      *) echo "[ERROR] unsupported --target-arch: $TARGET_ARCH" >&2; exit 2 ;;
    esac
  fi
  host_arch="$(uname -m)"
  if [[ "$TARGET_ARCH" == "$host_arch"
        || ( "$TARGET_ARCH" == "arm64" && "$host_arch" == "aarch64" )
        || ( "$TARGET_ARCH" == "amd64" && "$host_arch" == "x86_64" ) ]]; then
    ldd_output="$(ldd "$candidate" 2>&1 || true)"
    if [[ "$ldd_output" == *"not found"* ]]; then
      echo "[ERROR] unresolved shared library for $candidate:" >&2
      echo "$ldd_output" >&2
      exit 1
    fi
  fi
done < <(find "$OUTPUT_DIR" -type f -print0)

(
  cd "$OUTPUT_DIR"
  find . -type f ! -name SHA256SUMS -print0 \
    | sort -z \
    | xargs -0 sha256sum > SHA256SUMS
)

echo "[PASS] bundle created: $OUTPUT_DIR"
echo "[INFO] target architecture checked: $TARGET_ARCH"
echo "[INFO] verify with: (cd '$OUTPUT_DIR' && sha256sum -c SHA256SUMS)"
