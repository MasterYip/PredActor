#!/usr/bin/env bash
# run.sh
# ======
# Launch the full deployment session:
#   1. run_g1_robot   — C++ inference + robot control loop
#   2. clip_cond_sender.py     — interactive CLIP conditioning sender  [if --cond-udp]
#   3. wbg_guidance_sender.py  — interactive WBG guidance sender       [if --wbg-udp]
#
# The processes are started in separate tmux windows (if tmux is available)
# or sequentially in the foreground (fallback).
#
# Usage:
#   ./scripts/run.sh --config /path/to/deploy_config.yaml [OPTIONS]
#
# Required:
#   --config PATH         deploy_config.yaml produced by export_policy.py
#
# Runner options (forwarded to run_g1_robot):
#   --device DEV          cpu | cuda:0          (default: cpu)
#   --model PATH          override model path from config
#   --mode MODE           offline | receive-only | no-publish | control
#   --record-csv PATH     enable CSV and override fsm_config.yaml output path
#
# Conditioning options:
#   --cond-udp            enable CLIP conditioning via UDP
#                         also enables --enable-cond-udp in the config runner section
#   --cond-port PORT      UDP port for conditioning           (default: 9877)
#   --cond-host IP        host to bind the conditioning recv  (default: 127.0.0.1)
#   --cond-dim N          conditioning dimension              (default: 512)
#   --clip-mode MODE      simple | teleop | interp            (default: simple)
#   --clip-model NAME     CLIP model name                     (default: ViT-B/32)
#   --clip-device DEV     CLIP device                         (default: cpu)
#   --clip-checkpoint PATH  MotionCLIP checkpoint for fine-tuned CLIP weights
#   --clip-default TEXT   initial text prompt                 (default: "walking forward")
#   --clip-interval S     resend interval in seconds          (default: 0.1)
#   --clip-pairs PAIRS    text pairs for interp mode e.g. "walking:running,forward:backward"
#   --clip-ui-scale N     interp GUI scale factor (elements+font)  (default: 2.0)
#   --no-clip             start runner without launching clip_cond_sender.py
#
# WBG (interactive whole-body guidance) options:
#   --wbg-udp             enable interactive WBG commands via UDP
#                         injects enable_wbg_udp: true into the config runner
#                         block and launches wbg_guidance_sender.py
#   --wbg-host IP         host to bind the WBG receiver        (default: 127.0.0.1)
#   --wbg-port PORT       UDP port for WBG commands            (default: 9879)
#   --wbg-mode MODE       simple | teleop | interp             (default: simple)
#   --wbg-default TEXT    initial commands "vx,vy,wz"          (default: "0.0,0.0,0.0")
#   --wbg-interval S      resend interval in seconds           (default: 0.1)
#   --wbg-ui-scale N      interp GUI scale factor (elements+font)  (default: 2.0)
#   --joy                 interp mode: read a hardware joystick for vx/vy/wz
#                         (falls back to sliders when no device is found)
#   --joy-device PATH     joystick device path                 (default: /dev/input/js0)
#   --joy-type TYPE       xbox | ps5 | ps4 | generic | beitong_kp20 (default: xbox)
#   --joy-max-linear V    max linear velocity vx/vy [m/s]      (default: 5.0, GUI range)
#   --joy-max-angular W   max angular velocity wz [rad/s]      (default: 5.0, GUI range)
#   --no-wbg              start runner without launching wbg_guidance_sender.py
#
# Unified C++ commands (independent replacement path; configured in YAML):
#   --unified-command     enable runner.unified_command; launches no sender GUI
#   --command-source NAME auto | unitree_lowstate | joydev
#   --command-device PATH override the configured local joystick device
#   --command-mapping MAP xbox | xbox_new | ps5 | beitong_kp20
#   --validate-config     validate config/CLI contract and exit before env/DDS
#
# Other:
#   --build-dir DIR       path to cmake build dir    (default: <deploy_root>/build)
#   --python PATH         python interpreter         (default: python3)
#   -h, --help            show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# scripts/ -> diffusion_deploy/
DEPLOY_ROOT="$(dirname "${SCRIPT_DIR}")"
TOOLS_DIR="${DEPLOY_ROOT}/tools"
BUILD_DIR="${DEPLOY_ROOT}/build"
PYTHON="${PYTHON:-python3}"

# ---- Defaults ----
CONFIG=""
DEVICE="cpu"
MODEL_OVERRIDE=""
EXECUTION_MODE=""

COND_UDP=0
COND_PORT="9877"
COND_HOST="127.0.0.1"
COND_DIM="512"

FSM_CONFIG=""
FSM_DEVICE=""
FSM_JOY_MAPPING=""
NO_FSM=0

CLIP_MODE=""
CLIP_MODEL=""
CLIP_DEVICE=""
CLIP_CHECKPOINT=""
CLIP_DEFAULT=""
CLIP_INTERVAL=""
CLIP_PAIRS=""
NO_CLIP=0

WBG_UDP=0
WBG_HOST="127.0.0.1"
WBG_PORT="9879"
WBG_MODE=""
WBG_DEFAULT=""
WBG_INTERVAL=""
WBG_UI_SCALE=""
WBG_JOY=0
WBG_JOY_DEVICE=""
WBG_JOY_TYPE=""
WBG_JOY_MAX_LINEAR=""
WBG_JOY_MAX_ANGULAR=""
NO_WBG=0
CLIP_UI_SCALE=""
UNIFIED_COMMAND=0
COMMAND_SOURCE=""
COMMAND_DEVICE=""
COMMAND_MAPPING=""
VALIDATE_CONFIG=0
RECORD_CSV=""

# ---- Parse args ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)         CONFIG="$2";         shift 2 ;;
    --device)         DEVICE="$2";         shift 2 ;;
    --model)          MODEL_OVERRIDE="$2"; shift 2 ;;
    --mode)           EXECUTION_MODE="$2"; shift 2 ;;
    --cond-udp)       COND_UDP=1;          shift   ;;
    --cond-port)      COND_PORT="$2";      shift 2 ;;
    --cond-host)      COND_HOST="$2";      shift 2 ;;
    --cond-dim)       COND_DIM="$2";       shift 2 ;;
    --fsm-config)     FSM_CONFIG="$2";       shift 2 ;;
    --fsm-device)     FSM_DEVICE="$2";       shift 2 ;;
    --fsm-joy-mapping) FSM_JOY_MAPPING="$2"; shift 2 ;;
    --no-fsm)         NO_FSM=1;            shift   ;;
    --clip-mode)      CLIP_MODE="$2";       shift 2 ;;
    --clip-model)     CLIP_MODEL="$2";      shift 2 ;;
    --clip-device)    CLIP_DEVICE="$2";     shift 2 ;;
    --clip-checkpoint) CLIP_CHECKPOINT="$2"; shift 2 ;;
    --clip-default)   CLIP_DEFAULT="$2";    shift 2 ;;
    --clip-interval)  CLIP_INTERVAL="$2";   shift 2 ;;
    --clip-pairs)     CLIP_PAIRS="$2";      shift 2 ;;
    --no-clip)        NO_CLIP=1;           shift   ;;
    --wbg-udp)        WBG_UDP=1;           shift   ;;
    --wbg-host)       WBG_HOST="$2";       shift 2 ;;
    --wbg-port)       WBG_PORT="$2";       shift 2 ;;
    --wbg-mode)       WBG_MODE="$2";       shift 2 ;;
    --wbg-default)    WBG_DEFAULT="$2";    shift 2 ;;
    --wbg-interval)   WBG_INTERVAL="$2";   shift 2 ;;
    --wbg-ui-scale)   WBG_UI_SCALE="$2";   shift 2 ;;
    --joy)            WBG_JOY=1;           shift   ;;
    --joy-device)     WBG_JOY_DEVICE="$2"; shift 2 ;;
    --joy-type)       WBG_JOY_TYPE="$2";   shift 2 ;;
    --joy-max-linear) WBG_JOY_MAX_LINEAR="$2"; shift 2 ;;
    --joy-max-angular) WBG_JOY_MAX_ANGULAR="$2"; shift 2 ;;
    --clip-ui-scale)  CLIP_UI_SCALE="$2";  shift 2 ;;
    --no-wbg)         NO_WBG=1;            shift   ;;
    --unified-command) UNIFIED_COMMAND=1;   shift   ;;
    --command-source) COMMAND_SOURCE="$2"; shift 2 ;;
    --command-device) COMMAND_DEVICE="$2"; shift 2 ;;
    --command-mapping) COMMAND_MAPPING="$2"; shift 2 ;;
    --record-csv)     RECORD_CSV="$2"; shift 2 ;;
    --validate-config) VALIDATE_CONFIG=1; shift ;;
    --build-dir)      BUILD_DIR="$2";      shift 2 ;;
    --python)         PYTHON="$2";         shift 2 ;;
    -h|--help)
      sed -n '2,65p' "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "[run.sh] Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "$UNIFIED_COMMAND" -eq 1 && ( "$COND_UDP" -eq 1 || "$WBG_UDP" -eq 1 ) ]]; then
  echo "[run.sh] Error: --unified-command is independent from --cond-udp/--wbg-udp" >&2
  exit 1
fi

if [[ -z "$CONFIG" ]]; then
  echo "[run.sh] Error: --config is required." >&2
  exit 1
fi

RUNNER="${BUILD_DIR}/run_g1_robot"
if [[ ! -x "${RUNNER}" ]]; then
  echo "[run.sh] Error: run_g1_robot not found at ${RUNNER}" >&2
  echo "  Control build: ./build.sh --backend torch --with-sdk2 --with-command-publish" >&2
  exit 1
fi

CLIP_SCRIPT="${TOOLS_DIR}/clip_cond_sender.py"
WBG_SCRIPT="${TOOLS_DIR}/wbg_guidance_sender.py"

# Serialize an argv array into one shell command without losing argument
# boundaries. tmux send-keys and terminal-emulator bash -c APIs accept a
# string rather than argv, so array[*] is unsafe for prompts/paths that
# contain whitespace or shell metacharacters.
shell_join() {
  local out="" arg quoted
  for arg in "$@"; do
    printf -v quoted '%q' "${arg}"
    out+="${out:+ }${quoted}"
  done
  printf '%s' "${out}"
}

# ---- Inject enable_wbg_udp + host/port into the config runner block ----
# Produces "${CONFIG}.wbg.yaml" when the keys are not already present. The
# C++ runner reads these keys from the runner: YAML block; CLI flags are also
# passed below as an override, so the launch works even if injection is skipped.
make_wbg_config() {
  local src="$1" dst="$2" host="$3" port="$4"
  "${PYTHON}" - "$src" "$dst" "$host" "$port" <<'PYEOF'
import re, sys
src, dst, host, port = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
s = open(src).read()
if "enable_wbg_udp" in s:
    open(dst, "w").write(s)          # already present; CLI flags override below
    sys.exit(0)
flow = 'enable_wbg_udp: true, wbg_udp_host: "%s", wbg_udp_port: %s, ' % (host, port)
new = re.sub(r"(runner:)\s*\{", r"\1 {%s" % flow, s, count=1)
if new == s:
    block = 'runner:\n  enable_wbg_udp: true\n  wbg_udp_host: "%s"\n  wbg_udp_port: %s' % (host, port)
    new = re.sub(r"(?m)^runner:\s*$", block, s, count=1)
open(dst, "w").write(new)
PYEOF
}

# ---- Guard: --wbg-udp requires model.whole_body_guidance.enabled=true ----
# The C++ actor constructs WholeBodyGuidance ONLY from the model.whole_body_guidance
# YAML block. If the block is absent (e.g. the deploy config was exported from a
# checkpoint/actor without whole_body_guidance_config), --wbg-udp still binds the
# receiver but every command is a silent no-op. Fail loudly instead.
check_wbg_enabled() {
  local cfg="$1"
  "${PYTHON}" - "$cfg" <<'PYEOF' || return 1
import sys
import yaml
cfg = sys.argv[1]
try:
    d = yaml.safe_load(open(cfg)) or {}
except Exception as e:
    print(f"[run.sh] WBG guard: cannot parse config {cfg}: {e}", file=sys.stderr)
    sys.exit(2)
w = d.get("model", {}).get("whole_body_guidance")
if not w or not w.get("enabled"):
    print(f"[run.sh] ERROR: --wbg-udp requires model.whole_body_guidance.enabled=true", file=sys.stderr)
    print(f"  Config '{cfg}' has NO enabled whole_body_guidance block.", file=sys.stderr)
    print("  WBG UDP would bind the receiver but the actor would ignore every command (silent no-op).", file=sys.stderr)
    print("  Fix: re-export a WBG-enabled deploy config, e.g.", file=sys.stderr)
    print("    python tools/export_policy.py --checkpoint <ckpt> --config checkpoint \\", file=sys.stderr)
    print("      --output models/prdp --mode backbone --obs-profile G1 --use-fk \\", file=sys.stderr)
    print("      --urdf-path <g1/main.urdf> --wbg-config config/prdp_wbg_actor_config.yaml", file=sys.stderr)
    print("  or add a model.whole_body_guidance block to the config manually.", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
PYEOF
}

# ---- Build runner command ----
RUNNER_CMD=("${RUNNER}"
  --config "${CONFIG}"
  --device "${DEVICE}"
)
[[ -n "$MODEL_OVERRIDE" ]] && RUNNER_CMD+=(--model "${MODEL_OVERRIDE}")
[[ -n "$EXECUTION_MODE" ]] && RUNNER_CMD+=(--mode "${EXECUTION_MODE}")
[[ -n "$FSM_CONFIG"       ]] && RUNNER_CMD+=(--fsm-config "${FSM_CONFIG}")
[[ -n "$FSM_DEVICE"       ]] && RUNNER_CMD+=(--fsm-device "${FSM_DEVICE}")
[[ -n "$FSM_JOY_MAPPING"  ]] && RUNNER_CMD+=(--fsm-joy-mapping "${FSM_JOY_MAPPING}")
[[ "$NO_FSM" -eq 1        ]] && RUNNER_CMD+=(--no-fsm)
[[ "$WBG_UDP" -eq 1       ]] && RUNNER_CMD+=(--wbg-udp --wbg-host "${WBG_HOST}" --wbg-port "${WBG_PORT}")
[[ "$UNIFIED_COMMAND" -eq 1 ]] && RUNNER_CMD+=(--unified-command)
[[ -n "$COMMAND_SOURCE"    ]] && RUNNER_CMD+=(--command-source "${COMMAND_SOURCE}")
[[ -n "$COMMAND_DEVICE"    ]] && RUNNER_CMD+=(--command-device "${COMMAND_DEVICE}")
[[ -n "$COMMAND_MAPPING"   ]] && RUNNER_CMD+=(--command-mapping "${COMMAND_MAPPING}")
[[ -n "$RECORD_CSV"        ]] && RUNNER_CMD+=(--record-csv "${RECORD_CSV}")
[[ "$VALIDATE_CONFIG" -eq 1 ]] && RUNNER_CMD+=(--validate-config)

# ---- Build CLIP sender command ----
CLIP_CMD=("${PYTHON}"
  "${CLIP_SCRIPT}"
  --host   "${COND_HOST}"
  --port   "${COND_PORT}"
  --cond-dim "${COND_DIM}"
)
[[ -n "$CLIP_MODE" ]]         && CLIP_CMD+=(--mode        "${CLIP_MODE}")
[[ -n "$CLIP_MODEL" ]]        && CLIP_CMD+=(--model       "${CLIP_MODEL}")
[[ -n "$CLIP_DEVICE" ]]       && CLIP_CMD+=(--device      "${CLIP_DEVICE}")
[[ -n "$CLIP_CHECKPOINT" ]]   && CLIP_CMD+=(--checkpoint  "${CLIP_CHECKPOINT}")
[[ -n "$CLIP_DEFAULT" ]]      && CLIP_CMD+=(--default     "${CLIP_DEFAULT}")
[[ -n "$CLIP_INTERVAL" ]]     && CLIP_CMD+=(--interval    "${CLIP_INTERVAL}")
[[ -n "$CLIP_PAIRS" ]]        && CLIP_CMD+=(--pairs       "${CLIP_PAIRS}")
[[ -n "$CLIP_UI_SCALE" ]]     && CLIP_CMD+=(--scale       "${CLIP_UI_SCALE}")

# ---- Build WBG sender command ----
WBG_CMD=("${PYTHON}"
  "${WBG_SCRIPT}"
  --host   "${WBG_HOST}"
  --port   "${WBG_PORT}"
)
[[ -n "$WBG_MODE" ]]     && WBG_CMD+=(--mode     "${WBG_MODE}")
[[ -n "$WBG_DEFAULT" ]]  && WBG_CMD+=(--default  "${WBG_DEFAULT}")
[[ -n "$WBG_INTERVAL" ]] && WBG_CMD+=(--interval "${WBG_INTERVAL}")
[[ -n "$WBG_UI_SCALE" ]] && WBG_CMD+=(--ui-scale "${WBG_UI_SCALE}")
[[ "$WBG_JOY" -eq 1 ]]          && WBG_CMD+=(--joy)
[[ -n "$WBG_JOY_DEVICE" ]]      && WBG_CMD+=(--joy-device "${WBG_JOY_DEVICE}")
[[ -n "$WBG_JOY_TYPE" ]]        && WBG_CMD+=(--joy-type "${WBG_JOY_TYPE}")
[[ -n "$WBG_JOY_MAX_LINEAR" ]]  && WBG_CMD+=(--joy-max-linear "${WBG_JOY_MAX_LINEAR}")
[[ -n "$WBG_JOY_MAX_ANGULAR" ]] && WBG_CMD+=(--joy-max-angular "${WBG_JOY_MAX_ANGULAR}")

# ---- Inject WBG UDP keys into the runner config (best effort) ----
if [[ "$WBG_UDP" -eq 1 && "$NO_WBG" -eq 0 ]]; then
  WBG_CONFIG="${CONFIG}.wbg.yaml"
  if make_wbg_config "${CONFIG}" "${WBG_CONFIG}" "${WBG_HOST}" "${WBG_PORT}"; then
    # Prefer the injected config so the runner: block records the keys.
    # RUNNER_CMD layout: [0]=runner [1]=--config [2]=config-path ...
    RUNNER_CMD[2]="${WBG_CONFIG}"
  fi
  # Fail fast if the effective config has no WBG enabled — the receiver would
  # otherwise run but be a silent no-op (DEPLOY-PRDP-WBG-HP-003 user bug).
  if ! check_wbg_enabled "${RUNNER_CMD[2]}"; then
    exit 1
  fi
fi

# ---- Summary ----
echo "[run.sh] Config  : ${RUNNER_CMD[2]}"
echo "[run.sh] Runner  : ${RUNNER_CMD[*]}"
if [[ "$COND_UDP" -eq 1 && "$NO_CLIP" -eq 0 ]]; then
  echo "[run.sh] CLIP    : ${CLIP_CMD[*]}"
fi
if [[ "$WBG_UDP" -eq 1 && "$NO_WBG" -eq 0 ]]; then
  echo "[run.sh] WBG     : ${WBG_CMD[*]}"
fi
if [[ -n "$RECORD_CSV" ]]; then
  echo "[run.sh] Record  : ${RECORD_CSV}"
fi

if [[ "$UNIFIED_COMMAND" -eq 1 ]]; then
  echo "[run.sh] Unified C++ conditioning + direct fast WBG — no sender processes."
  exec "${RUNNER_CMD[@]}"
elif [[ "$COND_UDP" -eq 0 && "$WBG_UDP" -eq 0 ]]; then
  # ---- No conditioning / no WBG: run C++ runner directly ----
  echo "[run.sh] No conditioning and no WBG — running run_g1_robot directly."
  exec "${RUNNER_CMD[@]}"
fi

# ---- With conditioning: need two processes ----
if command -v tmux &>/dev/null; then
  # ── tmux layout ──────────────────────────────────────────────
  SESSION="run_g1_$$"
  tmux new-session -d -s "${SESSION}" -x 220 -y 50

  # Window 0: C++ runner
  RUNNER_SHELL_CMD="$(shell_join "${RUNNER_CMD[@]}")"
  tmux send-keys -t "${SESSION}:0" "${RUNNER_SHELL_CMD}" Enter
  tmux rename-window -t "${SESSION}:0" "runner"

  # Window 1: CLIP sender
  if [[ "$COND_UDP" -eq 1 && "$NO_CLIP" -eq 0 ]]; then
    if [[ ! -f "${CLIP_SCRIPT}" ]]; then
      echo "[run.sh] Warning: clip_cond_sender.py not found at ${CLIP_SCRIPT}" >&2
    else
      # Kill any stale sender holding the lock port (port 9878).
      # The sender binds 9878 as a singleton guard; fuser -k clears it.
      fuser -k 9878/udp &>/dev/null || true
      tmux new-window -t "${SESSION}" -n "clip"
      CLIP_SHELL_CMD="$(shell_join "${CLIP_CMD[@]}")"
      tmux send-keys  -t "${SESSION}:clip" "${CLIP_SHELL_CMD}" Enter
    fi
  fi

  # Window 2: WBG sender
  if [[ "$WBG_UDP" -eq 1 && "$NO_WBG" -eq 0 ]]; then
    if [[ ! -f "${WBG_SCRIPT}" ]]; then
      echo "[run.sh] Warning: wbg_guidance_sender.py not found at ${WBG_SCRIPT}" >&2
    else
      # Clear stale WBG lock (port 9880) before launching the sender.
      fuser -k 9880/udp &>/dev/null || true
      tmux new-window -t "${SESSION}" -n "wbg"
      WBG_SHELL_CMD="$(shell_join "${WBG_CMD[@]}")"
      tmux send-keys  -t "${SESSION}:wbg" "${WBG_SHELL_CMD}" Enter
    fi
  fi

  echo ""
  echo "[run.sh] Started tmux session '${SESSION}'."
  echo "  Attach :  tmux attach -t ${SESSION}"
  echo "  Kill all: tmux kill-session -t ${SESSION}"
  tmux attach -t "${SESSION}"

else
  # ── Fallback: no tmux ─────────────────────────────────────────
  # For modes that need interactive stdin (teleop), spawn the sender in a new
  # terminal emulator window so it gets its own tty. For simple/interp/background
  # modes fall back to a background process.
  echo "[run.sh] tmux not found."

  CLIP_PID=""
  WBG_PID=""

  # Launch one sender: script, then its command array.
  # teleop mode needs its own tty; simple/interp can run in the background.
  launch_sender() {
    local script="$1"; shift
    local cmd=("$@")
    local needs_tty=0
    local simple_mode=1
    local i
    for ((i=0;i<${#cmd[@]};i++)); do
      if [[ "${cmd[$i]}" == "--mode" ]]; then
        simple_mode=0
        if [[ "${cmd[$i+1]:-}" == "simple" ]]; then
          simple_mode=1
        elif [[ "${cmd[$i+1]:-}" == "teleop" ]]; then
          needs_tty=1
        fi
      fi
    done
    # Background simple mode has no controlling stdin. Keep the initial
    # command/prompt alive until run.sh terminates it instead of treating EOF
    # as an interactive quit.
    if [[ "$simple_mode" -eq 1 ]]; then
      cmd+=(--headless)
    fi
    if [[ ! -f "${script}" ]]; then
      echo "[run.sh] Warning: $(basename "${script}") not found at ${script}" >&2
      return
    fi
    if [[ "$needs_tty" -eq 1 ]]; then
      local shell_cmd
      shell_cmd="$(shell_join "${cmd[@]}")"
      if command -v gnome-terminal &>/dev/null; then
        gnome-terminal -- bash -c "${shell_cmd}; read -p 'Press Enter to close'" &
      elif command -v xterm &>/dev/null; then
        xterm -title "$(basename "${script}")" -e bash -c "${shell_cmd}; read -p 'Press Enter to close'" &
      elif command -v konsole &>/dev/null; then
        konsole --noclose -e bash -c "${shell_cmd}" &
      elif command -v xfce4-terminal &>/dev/null; then
        xfce4-terminal --hold -e bash -c "${shell_cmd}" &
      else
        echo "[run.sh] Warning: no terminal emulator found; falling back to background process." >&2
        "${cmd[@]}" &
      fi
    else
      "${cmd[@]}" &
    fi
    echo "[run.sh] $(basename "${script}") started (PID $!)."
  }

  if [[ "$COND_UDP" -eq 1 && "$NO_CLIP" -eq 0 ]]; then
    fuser -k 9878/udp &>/dev/null || true
    launch_sender "${CLIP_SCRIPT}" "${CLIP_CMD[@]}"
    CLIP_PID=$!
  fi

  if [[ "$WBG_UDP" -eq 1 && "$NO_WBG" -eq 0 ]]; then
    fuser -k 9880/udp &>/dev/null || true
    launch_sender "${WBG_SCRIPT}" "${WBG_CMD[@]}"
    WBG_PID=$!
  fi

  cleanup() {
    [[ -n "${CLIP_PID}" ]] && kill "${CLIP_PID}" 2>/dev/null || true
    [[ -n "${WBG_PID}"  ]] && kill "${WBG_PID}"  2>/dev/null || true
  }
  trap cleanup INT TERM

  "${RUNNER_CMD[@]}"
  cleanup
fi
