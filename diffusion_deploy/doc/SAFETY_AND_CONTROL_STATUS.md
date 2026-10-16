# Safety and control status

## Current capability

In a normal build:

- `ENABLE_UNITREE_COMMAND_PUBLISH` defaults OFF;
- `UnitreeEnv` creates state subscribers only;
- the compiled binary excludes the guarded `ChannelPublisher`, `rt/lowcmd`,
  `Write`, and MotionSwitcher path;
- `receive-only` accepts one state snapshot and rejects `step()`;
- `no-publish` may compute and transform actions, then discards them; and
- safety counters must remain `publisher_constructions=0`,
  `shutdown_calls=0`, and `publish_calls=0`.

Thus a normal `run_g1_robot` binary cannot control the simulator or motors.
The filename alone is not a safety guarantee: always verify build provenance
and the source guard for the exact binary.

## Safe validation modes

| Mode | DDS state | Model inference | Action publication |
|---|---|---|---|
| `offline` | no | yes | impossible |
| `receive-only` | yes | no | impossible; `step()` rejected |
| `no-publish` | yes | yes | impossible; action discarded |
| `control` | yes | yes | enabled only in the explicit publishing build |

Receive-only benchmark tasks must never initialize a command publisher,
publish `LowCmd`, invoke MotionSwitcher, change robot mode, or request motor
control.

## Explicit control-capable build

`build.sh --with-sdk2 --with-command-publish` compiles the `LowCmd`, CRC, G1
MotionSwitcher, and DDS write path. The publisher is used only when the runner
also receives `--mode control`; all other execution modes retain their
non-publishing behavior.

## Physical-control gate

Physical control remains a separate authorization boundary. Its review must
cover single-controller ownership, fresh/valid state and command
watchdogs, CRC and bounds, torque/orientation/deadline gates, dead-man and
E-stop behavior, passive fallback on all exits, measured realtime performance,
closed-loop simulation, suspended hardware, and an on-site operator.

Do not use `--mode control` without the reviewed FSM configuration and an
on-site operator controlling the E-stop.

## Operator language

- “Build passed” means compilation only.
- “Offline inference passed” means model/resource/runtime compatibility only.
- “Receive-only passed” means DDS state feedback and zero-publish invariants.
- “No-publish passed” means feedback-to-action computation without actuation.
- None of those statements authorize motor commands.
