# Safety FSM & Joystick Control

> **Capability boundary:** `LowCmd` exists only in an explicit
> `--with-command-publish` build running with `--mode control`. See
> [`SAFETY_AND_CONTROL_STATUS.md`](SAFETY_AND_CONTROL_STATUS.md) before using
> any runtime command.

The `diffusion_deploy` Safety FSM provides emergency stop, fall detection, and joystick-controlled state management for the Unitree G1 robot. It runs as a **pre-step guard** inside the EnvRunner control loop — no separate threads required.

## Architecture

```
                      Joystick (/dev/input/js0)
                             │
                    ┌────────▼────────┐
                    │  JoystickReader │  (Linux joystick API, non-blocking)
                    └────────┬────────┘
                             │
         IMU quat ───► ┌────▼─────┐
                       │ DeployFSM │  (YAML-driven state machine)
                       └────┬─────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          Passive         Ready        Running
        (kp=0, limp)   (interp stand) (policy on)
```

## State Machine

```
                STARTUP
                   │
                   ▼
              ┌─────────┐
              │ PASSIVE │◄──────────┐
              │ (safe)  │           │
              └────┬────┘           │
                   │ RB            │ B (or FALL)
                   ▼               │
              ┌─────────┐          │
              │  READY  │──────────┤
              │ (interp)│  B       │
              └────┬────┘          │
                   │ START         │
                   ▼               │
              ┌─────────┐          │
              │ RUNNING │──────────┘
              │ (policy)│  B (or FALL)
              └─────────┘
```

### Default States

| State | Gains | Action | Behaviour |
|-------|-------|--------|-----------|
| **Passive** | kp=0, kd=3.0 | Track current joint positions | Robot is limp/safe. Default startup and fallback. |
| **Ready** | State kp/kd | **Smooth interpolation** to stand pose | 2-second linear ramp from current pose to stand. |
| **Running** | Deploy config Kp/Kd | Policy output | Normal diffusion inference active. |

### Default Transitions

| From | To | Trigger |
|------|----|---------|
| Passive | Ready | RB button press |
| Ready | Running | START button press |
| Ready | Passive | B button press |
| Running | Passive | B button press |
| **Any** | **Passive** | **Fall detected** (gravity tilt > limit) |

All states, transitions, gains, and interpolation are configurable via YAML.

## YAML Configuration

The FSM follows the reference config style from `temp/deploy/robots/g1_29dof/config/config.yaml`.

### Full Example

```yaml
FSM:
  _:                    # enabled states (first = initial)
    Passive:  {id: 1}
    Ready:    {id: 2}
    Running:  {id: 3, type: policy}

  Passive:
    transitions:
      Ready: RB.on_pressed
    kd: [3, 3, 3, ...]  # 29 values, MuJoCo order

  Ready:
    transitions:
      Passive: B.on_pressed
      Running: START.on_pressed
    kp: [100, 100, ...]
    kd: [2, 2, ...]
    ts: [0, 2.0]        # interpolation time stamps [s]
    qs:
      - []               # empty = capture current at entry
      - [-0.312, -0.312, 0.0, ...]  # stand pose (IsaacLab order)

  Running:
    transitions:
      Passive: B.on_pressed

  bad_orientation_limit_deg: 57.3
  auto_passive_on_fall: true
```

### State Definition Keys

| Key | Type | Description |
|-----|------|-------------|
| `id` | int | Numeric state ID (informational) |
| `type` | string | `"policy"` = runs diffusion inference. Omitted = normal state. |
| `transitions` | map[string→string] | `target_state: trigger_string` pairs |
| `kp` | float[29] | PD stiffness gains (MuJoCo order). Omitted → kp=0 (passive). |
| `kd` | float[29] | PD damping gains (MuJoCo order) |
| `ts` | float[] | Interpolation time stamps [s]. Must match `qs` length. |
| `qs` | float[][] | Joint position waypoints (IsaacLab order). `[]` = capture current. |

### Trigger String Format

```
<Button>.<event>
```

- **Button names**: `A`, `B`, `X`, `Y`, `LB`, `RB`, `BACK`, `START`, `GUIDE`, `LS`, `RS`
- **Events**:
  - `on_pressed` — rising edge (triggered once per press)
  - `pressed` — level (true while held)
  - `on_released` — falling edge (triggered once per release)

Examples: `RB.on_pressed`, `START.on_pressed`, `B.pressed`

### Interpolation

When a state has `ts` and `qs` keys:
- At state entry, `elapsed = 0`
- If `qs[i]` is empty (`[]`), the current joint positions are used for that waypoint
- Each control tick, positions are linearly interpolated: `pos = lerp(qs[i], qs[i+1], (elapsed - ts[i]) / (ts[i+1] - ts[i]))`
- Once `elapsed >= ts[-1]`, holds at the final waypoint

This matches the reference `LinearInterpolator.h` from `temp/deploy/`.

### Passive Detection

A state is considered "passive" (kp=0 in motor commands) when its `kp` field is either:
- Not specified (omitted from YAML)
- An empty list
- All zeros

The first passive state in the enabled states list becomes the **safety fallback** target.

## Fall Detection

The `SafetyValidator` computes the projected gravity vector in the robot's body frame from the IMU quaternion:

```
projected_gravity_z = 1 - 2*(qw² + qz²)
tilt_angle = |acos(-projected_gravity_z)|
```

When `tilt_angle > bad_orientation_limit_deg` (default 57.3° ≈ 1 rad), the FSM transitions to the fallback state (Passive).

## Usage

### Basic (default 3-state FSM, Xbox controller on js0)

```bash
./run_g1_robot --config config/g1_deploy_config.yaml --model models/policy.pt
```

The FSM is **enabled by default**. Robot starts in **Passive** (safe).
Press **RB** → 2s smooth stand-up, then hold. Press **START** → policy runs. Press **B** → stop.

### Custom FSM config

```bash
./run_g1_robot --config ... --fsm-config config/fsm_config.yaml
```

### Custom joystick device

```bash
./run_g1_robot --config ... --fsm-device /dev/input/js1
```

### Disable FSM

```bash
./run_g1_robot --config ... --no-fsm
```

### Override fall detection threshold

```bash
./run_g1_robot --config ... --fsm-fall-limit 45.0
```

## Files

| File | Purpose |
|------|---------|
| `include/diffusion_deploy/safety/joystick_reader.hpp` | Linux `/dev/input/jsX` device parser |
| `include/diffusion_deploy/safety/safety_validator.hpp` | Projected gravity & fall detection |
| `include/diffusion_deploy/safety/deploy_fsm.hpp` | YAML-driven FSM, `ButtonTrigger`, `LinearInterpolator`, `DeployFSM` |
| `config/fsm_config.yaml` | Reference FSM configuration |
| `examples/run_g1_robot.cpp` | Main executable (FSM wiring) |
| `src/runner/env_runner.cpp` | FSM gate + `execute_safe_step()` with interpolation |
| `src/env/unitree_env.cpp` | Safety gain override in `step()` |
| `doc/safety_fsm.md` | This document |

## Adding Custom States

The YAML format is self-defined — add any state with any name:

```yaml
FSM:
  _:
    Passive:    {id: 1}
    Ready:      {id: 2}
    Running:    {id: 3, type: policy}
    Crouch:     {id: 4}          # custom state!

  Crouch:
    transitions:
      Passive: B.on_pressed
    kp: [80, 80, ...]
    kd: [2, 2, ...]
    ts: [0, 1.5]
    qs:
      - []                     # capture current
      - [crouch_pose...]       # IsaacLab order
```

Then add transitions to/from it in other states — `Ready → Crouch: X.on_pressed`, etc.

## Troubleshooting

### "Cannot open /dev/input/js0"

The joystick is not connected. Try `--fsm-device /dev/input/js1`. FSM stays in Passive when no joystick is found.

### "Permission denied" on /dev/input/js0

```bash
sudo usermod -a -G input $USER
# Log out and back in
```

### FSM state not transitioning

1. Verify joystick with `jstest /dev/input/js0`
2. Check button names in trigger strings match your controller
3. Try `RB.on_pressed` → `RB.pressed` if edge detection isn't working

### Interpolation not smooth

- Increase `ts` duration (e.g., `[0, 3.0]` for a slower 3-second ramp)
- Check that `qs` values are in IsaacLab joint order, not MuJoCo order
