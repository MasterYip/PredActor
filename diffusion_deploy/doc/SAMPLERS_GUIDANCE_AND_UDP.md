# Samplers, whole-body guidance, and UDP conditioning

## PRDP sampler modes

The C++ PRDP actor accepts:

- `rolling_ddpm`: full rolling DDPM schedule;
- `scalar_ddim`: scalar DDIM with `ddim_steps > 0`;
- `ns_ddim`: per-position noise-schedule DDIM; and
- `rolling_ddim`: randomized rolling schedule with DDIM jumps.

`ddim_eta: 0.0` selects deterministic DDIM. The generated config also records
action/state schedule names, `use_ns_ddim`, and
`randomize_noise_schedule`; the parser rejects inconsistent combinations.

The two WBG debug/compatibility switches are independent:

```yaml
model:
  whole_body_guidance:
    enable_zeta_comp: false
    enable_damping_comp: false
```

`false` selects the legacy single-level zeta jump handling and legacy
projected-gradient damping respectively. Missing keys default to compensated
behavior for compatibility with older exported configs.

## Whole-body guidance

C++ WBG is classifier guidance over the 192-D FK-backed G1 state. It supports
planar `vx`, `vy`, and `wz` commands in `trajectory_mode: simple`.

```yaml
model:
  sampler_mode: scalar_ddim
  ddim_steps: 5
  ddim_eta: 0.0
  whole_body_guidance:
    enabled: true
    mode: classifier
    trajectory_mode: simple
    dt: 0.02
    enable_zeta_comp: false
    enable_damping_comp: false
    vx: {enabled: true, command: 0.3, kp: 0.1, body_indices: [0, 9]}
    vy: {enabled: false, command: 0.0, kp: 0.1, body_indices: [0, 9]}
    wz: {enabled: false, command: 0.0, kp: 0.1, body_indices: [0, 9]}
env:
  control_dt: 0.02
  use_fk: true
  urdf_path: assets/g1.urdf
```

Keep WBG `dt` equal to `env.control_dt`. Commands are m/s for `vx`/`vy` and
rad/s for `wz`. C++ does not implement the Python UI's height, wrist, or
end-effector guides. `runner.reset_height` is a safety threshold, not a WBG
height command.

## WBG UDP protocol

The WBG receiver consumes nine little-endian float32 values:

```text
[vx_enabled, vx_command, vx_kp,
 vy_enabled, vy_command, vy_kp,
 wz_enabled, wz_command, wz_kp]
```

Only enable/command/gain are mutable over UDP. The C++ receiver rejects
non-finite packets and clamps velocity/yaw and gain ranges. Body indices,
masks, schedules, and trajectory mode remain fixed by YAML.

`tools/wbg_guidance_sender.py` supports simple, teleop, and slider-based interp
modes. `scripts/run.sh --wbg-udp` checks that the effective model config has
WBG enabled before starting the sender. In the current no-command build this
can change computed actions but cannot actuate a simulator or robot.

## CLIP conditioning UDP

The conditioning receiver accepts exactly `text_cond_dim` little-endian
float32 values, normally a 512-D MotionCLIP/CLIP embedding. Config keys are:

```yaml
runner:
  enable_cond_udp: true
  cond_udp_host: 127.0.0.1
  cond_udp_port: 9877
```

The optional Python sender is external to the C++ runtime. The Jetson model
bundle records that the encoder is not bundled; install/run the encoder on a
separate machine or service when text commands are required.

CLIP and WBG use separate data and singleton-lock ports and may run together.
The detailed sender CLI is available from each tool's `--help` and from
`scripts/run.sh --help`.

## Validation scope

`test_prdp_wbg`, `test_ddim_step_parity`, and `test_agent_parity` cover
gradient, DDIM-step, and actor parity/finite-output contracts. They do not
establish robot stability or authorize command publishing.
