#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Receive-only task-055 benchmark. It never publishes robot commands.

  run_g1_feedback_benchmark.sh capture BINARY CONFIG OUTPUT_DIR INTERFACE [SAMPLES]
  run_g1_feedback_benchmark.sh replay  BINARY CONFIG CAPTURE_DIR RUN_DIR [DEVICE]
  run_g1_feedback_benchmark.sh replay-rlobs BINARY CONFIG CAPTURE_DIR RUN_DIR [DEVICE]
  run_g1_feedback_benchmark.sh analyze PYTHON RUN_DIR REPORT_DIR

Capture and replay are intentionally separate. Replay initializes no DDS and
never sends generated actions to the robot.
EOF
}

[[ $# -ge 1 ]] || { usage; exit 2; }
mode="$1"; shift

case "${mode}" in
  capture)
    [[ $# -ge 4 ]] || { usage; exit 2; }
    binary="$1"; config="$2"; output="$3"; interface="$4"; samples="${5:-128}"
    exec "${binary}" --phase capture --config "${config}" --output "${output}" \
      --network-interface "${interface}" --samples "${samples}" --interval-ms 20
    ;;
  replay)
    [[ $# -ge 4 ]] || { usage; exit 2; }
    binary="$1"; config="$2"; capture="$3"; run_dir="$4"; device="${5:-cuda:0}"
    mkdir -p "${run_dir}"
    for guidance in disabled enabled; do
      for steps in 0 1 2 3 5 8 10 20; do
        if [[ "${steps}" == 0 ]]; then sampler=ddpm20; else sampler=ddim${steps}; fi
        out="${run_dir}/${sampler}-${guidance}"
        "${binary}" --phase replay --config "${config}" --capture "${capture}" \
          --output "${out}" --ddim-steps "${steps}" --guidance "${guidance}" \
          --device "${device}" --seed 20260818 --warmup 8
      done
    done
    ;;
  replay-rlobs)
    [[ $# -ge 4 ]] || { usage; exit 2; }
    binary="$1"; config="$2"; capture="$3"; run_dir="$4"; device="${5:-cuda:0}"
    mkdir -p "${run_dir}"
    for steps in 0 1 2 3 5 8 10 20; do
      if [[ "${steps}" == 0 ]]; then sampler=ddpm20; else sampler=ddim${steps}; fi
      out="${run_dir}/${sampler}-disabled"
      "${binary}" --phase replay --config "${config}" --capture "${capture}" \
        --output "${out}" --ddim-steps "${steps}" --guidance disabled \
        --motion-cond zero --device "${device}" --seed 20260818 --warmup 8
    done
    ;;
  analyze)
    [[ $# -eq 3 ]] || { usage; exit 2; }
    exec "$1" "$(cd "$(dirname "$0")/.." && pwd)/tools/analyze_g1_feedback_benchmark.py" \
      --run-dir "$2" --output "$3"
    ;;
  *) usage; exit 2 ;;
esac
