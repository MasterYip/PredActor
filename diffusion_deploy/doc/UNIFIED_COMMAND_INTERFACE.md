# Unified C++ deployment commands

## Outcome and topology

The opt-in unified interface removes Python and MotionCLIP inference from the
live joystick-to-policy path. One `JoystickReader` supplies both command paths.
It can consume either the original Unitree wireless bytes already present in
the environment's `rt/lowstate` subscriber, or a Linux joydev device:

```text
rt/lowstate wireless_remote OR /dev/input/js0
  -> C++ JoystickReader (one source)
       -> left/right sticks -> in-process DiffuseCLoCActor::apply_live_wbg()
       -> L2 pressure       -> WBG Kp (released 1.0, pressed 0.0)
       -> LB rising edge    -> WBG enabled/disabled toggle
       -> L3 rising edge    -> vx/vy guidance enabled/disabled toggle
       -> R3 rising edge    -> wz guidance enabled/disabled toggle
       -> D-pad edge        -> in-process EnvRunner text-condition tensor
       -> optional UDP compatibility packets
       -> optional versioned status telemetry -> read-only customtkinter dashboard
```

There is no mandatory sender process or window. The dashboard is not a
controller and can be started/stopped independently. Legacy
`clip_cond_sender.py`, `wbg_guidance_sender.py`, `--cond-udp`, `--wbg-udp` and
their `run.sh` flows remain available and unchanged by default.

## Fast-WBG contract audit

Current master contains the production `reuse_x0` fast classifier-guidance
mode (`model.classifier_guidance_impl: reuse_x0`). The command interface calls
`DiffuseCLoCActor::apply_live_wbg()` directly; this updates the same
`WholeBodyGuidance` live-axis state read by the denoising path. No loopback UDP
is involved unless `compatibility_udp.enabled` is explicitly set.

This does not enable WBG in an incompatible checkpoint: the deploy config must
already contain `model.whole_body_guidance.enabled: true`. For the intended
fast path it must also carry the valid `reuse_x0` contract and
`no_state_override` profile accepted by the existing parser.

## Latent cache contract

Runtime never imports Python or executes CLIP. Exactly four startup resources
are required and fully read before control begins:

| D-pad edge | Command | File contract |
|---|---|---|
| Up | `stand` | raw little-endian float32 |
| Right | `walk` | raw little-endian float32 |
| Down | `jog` | raw little-endian float32 |
| Left | `squat down` | raw little-endian float32 |

Each entry declares `dim` and `fnv1a64:<16 hex>` over the exact file bytes.
Missing files, wrong byte counts, non-finite values, duplicate directions,
wrong names/order, or hash mismatches fail closed during runner construction.
The typed `motions` sequence is the extension point for a future selector with
more inputs; the current four-way D-pad contract deliberately accepts exactly
these four commands.

Generate resources once, using the same MotionCLIP checkpoint used by the
policy:

```bash
cd diffusion_deploy
python tools/export_unified_command_latents.py \
  --checkpoint /absolute/path/to/checkpoint_0100.pth.tar \
  --output models/my_policy/command_latents \
  --device cpu
```

Copy the emitted `motions:` entries into the block shown in
`config/unified_command_example.yaml`. Paths are resolved relative to the
deploy YAML.

The generated `wbg.controls` block explicitly selects semantic `l2` and `LB`.
The stock Unitree controller exposes L2 as a digital trigger (`released = 1.0`
Kp, `pressed = 0.0` Kp). L2 pressure is normalized from Linux joydev trigger ranges, including the
common signed `-32767` rest to `32767` pressed convention; a missing initial
axis event is treated safely as unpressed. LB uses rising-edge debounce, so
holding it never repeats. When disabled, the direct fast-WBG actor frame
disables all three axes and reports effective Kp `0`; sticks and L2 continue
updating so the next LB press restores current, not cached, input. Omitting
`wbg.controls` preserves legacy fixed `wbg.kp` behavior and no LB toggle.
L3 and R3 use the same edge/debounce state machine: L3 masks `vx` and `vy`
together, while R3 masks `wz`. The per-axis mask is passed through the live WBG
frame and is honored by both sequential and stacked gradient implementations.
Unitree LowState's `f1` and `f2` buttons are used as aliases for the same L3/R3
semantic slots that Linux joydev supplies directly.

## Launch

Set `runner.text_cond_dim: 512`, copy the `runner.unified_command` fields into
the exported deploy YAML, and enable the block. Then use one process:

```bash
./scripts/run.sh \
  --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml \
  --mode offline \
  --unified-command \
  --command-device /dev/input/js0 \
  --command-mapping xbox_new \
  --record-csv models/my_policy/eval_output/demo_01.csv
```

`--record-csv PATH` is optional. When enabled, one row per control tick is
written with the policy observation history, raw robot observation terms, the
action sent to the environment, the active motion/text label and latent,
command source, FSM state, and WBG values. Parent directories are created and
the stream is flushed on graceful shutdown. Without this flag the recorder is
not constructed and the normal loop performs no recording work.

`--unified-command` is mutually exclusive with the legacy `--cond-udp` and
`--wbg-udp` receivers, preventing two writers. It defaults off. The command
interface reuses the FSM's `JoystickReader` when the FSM is active, so FSM,
WBG and text selection do not open or parse the device separately.

`runner.unified_command.source` accepts `unitree_lowstate`, `joydev`, or
`auto`. `auto` preserves old configs: empty/`null` `joystick_device` selects
LowState, while a device path selects joydev. For the Unitree source, the FSM
reader must also be external; contradictory source/device ownership fails at
config or construction time. LowState age is checked against
`source_timeout_s`; missing, invalid, or stale input selects `stand`, zeros and
disables WBG, and reports the controller disconnected. D-pad and button edges
are computed once in the shared reader, so a held button cannot retrigger.

To visualize or inspect status only, set `telemetry.enabled: true` and run the
listener. The terminal mode is the direct-SSH path and has no GUI dependency:

```bash
python tools/unified_command_dashboard.py --host 127.0.0.1 --port 9880 --mode tui
```

`--mode auto` selects the CustomTkinter window when a display and dependency
are available, otherwise it falls back to the same terminal listener. The
listener is read-only and does not send control packets.

The JSON telemetry schema remains version `1` and carries sequence, monotonic
time, joystick connection, current motion/hash, global and per-axis WBG enabled
states, and effective Kp. It contains no control endpoint. `compatibility_udp.enabled: true`
separately emits the legacy raw
512-float condition and 9-float WBG packets for debugging/compatibility.

## Legacy CLIP Enter-to-send latency

The old simple sender replaced a shared embedding after encoding and waited
for the periodic loop; this added up to `--interval` (100 ms by default) after
encoding. It now sends synchronously on command update. `stand`, `walk`, `jog`
and `squat down` are pre-encoded before the sender reports ready, and both
simple and teleop paths immediately send from their cache. Arbitrary new text
still pays unavoidable CLIP inference once, but its UDP send occurs immediately
after encoding rather than on the next periodic tick. Each update prints
`enter_to_send`, cache hit/miss, and encode time.

The deterministic monotonic-clock benchmark measured the old 100 ms periodic
path at **99.045 ms p50 / 99.133 ms p99** (10 changes). The synchronous cached
path measured **0.0024 ms p50 / 0.0036 ms p99 / 0.0095 ms max** (1,000 changes),
passing its 5 ms p99 gate. The fake-encoder regression separately verifies that
an uncached prompt sends immediately after its unavoidable encode. These are
host software measurements, not physical robot latency claims.

## Remaining physical gates

- Confirm the actual controller appears as the selected mapping and D-pad axes.
- Verify exported hashes and semantic equivalence to the training MotionCLIP.
- Run a subscriber/inference-only observation of selected condition and WBG
  state before enabling control.
- Validate WBG ranges, command semantics and behavior on the robot under the
  normal deployment safety procedure. This task performs no DDS or actuation.
