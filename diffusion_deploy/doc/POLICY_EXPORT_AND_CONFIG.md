# Policy export and configuration reference

## Canonical exporter

`tools/export_policy.py` reconstructs the Python agent from a checkpoint and
exports the reliable C++ backbone path plus a single runtime YAML. The common
form is:

```bash
PYTHONNOUSERSITE=1 PYTHONPATH=.. python tools/export_policy.py \
  --checkpoint /absolute/path/to/latest.ckpt \
  --config checkpoint \
  --output models/my_policy \
  --mode backbone
```

`--config checkpoint` is the default. Use a mutable YAML only for an explicit,
reviewed override.

## Important options

| Option | Meaning |
|---|---|
| `--target native` | normal export (default) |
| `--target jetson-jp5-torch21` | lower fused operators for JP5 Torch 2.1 |
| `--obs-profile PROFILE` | override derived `G1`, `G1_RLObs`, etc. |
| `--use-fk` / `--no-use-fk` | override FK derivation |
| `--urdf-path PATH` | source URDF copied into the export directory |
| `--deploy-config NAME` | generated runtime YAML filename |
| `--wbg-config PATH` | override WBG configuration serialized into the runtime YAML |
| `--gui` | open the optional customtkinter editor before export |
| `--write-actor-config` | write a debug compatibility dump; not a runtime input |
| `--write-normalizer-stats` | write a debug stats dump; not a runtime input |
| `--stats-only` | emit stats only; not a deployable bundle |

Run `python tools/export_policy.py --help` for the source-of-truth interface.
`--mode full_loop` is an experimental lazy JIT fallback; `backbone` is the
supported complete C++ resource contract.

## Exported resource contract

The exporter writes `deploy_config.yaml`, `fsm_config.yaml`, the policy
backbone, diffusion schedule, PRDP/DiffuseCLoC emphasis matrices when needed,
the optional G1 URDF, `resource_manifest.yaml`, and `SHA256SUMS`.

The manifest records schema `diffusion_deploy.resources` version 1. A
text-conditioned bundle records `external_udp`; the CLIP encoder is deliberately
not bundled. The sender must provide exactly `text_cond_dim` little-endian
float32 values.

## Actor types

| Python actor | C++ actor type | Required artifacts |
|---|---|---|
| action diffusion | `diffusion` | backbone + schedule |
| joint state/action diffusion | `joint_diffusion` | backbone + schedule |
| DiffuseCLoC | `diffuse_cloc` | backbone + schedule + emphasis matrices |
| PRDP | `prdp` | backbone + schedule + emphasis matrices |
| legacy full loop | `torch` | full-loop TorchScript; experimental |

## Generated deploy YAML

The runtime reads only the generated deploy YAML. Its main blocks are:

```yaml
model:
  backend: torch
  actor_type: prdp
  path: g1_policy_backbone.pt
  schedule_path: ddpm_schedule.pt
  emphasis_path: emphasis_matrices.pt
  obs_dim: 192
  action_dim: 29
  n_obs_steps: 4
  n_future_steps: 16
  obs_profile: G1
  data_profile: g1_prdp_standard
  sampler_mode: rolling_ddpm

env:
  execution_mode: offline
  network_interface: lo
  control_dt: 0.02
  use_fk: true
  urdf_path: assets/g1.urdf

runner:
  delay_action_step: 0
  max_steps: 200
  realtime_mode: true
  enable_cond_udp: false
  enable_wbg_udp: false

normalization:
  obs: {mode: scale_offset, scale: [...], offset: [...]}
  action: {mode: scale_offset, scale: [...], offset: [...]}
  cond: {mode: scale_offset, scale: [...], offset: [...]}
```

The exporter keeps some flat legacy actor names while also writing the newer
nested `backbone` block. `config_parser.cpp` cross-checks aliases and rejects
dimension, sampler, profile, or attention-contract drift.

For `data_profile: g1_prdp_standard2`, the exporter and runtime require the
non-aliased condition profile of the same name: a 93-D robot prefix
(`joint_pos`, `joint_vel`, `projected_gravity`, `base_ang_vel`, `last_actions`)
plus 512-D `text_cond`, for `backbone.cond_dim: 605`. `base_lin_vel` is not
packed. A profile name, runner schema, manifest schema, or dimension mismatch
is a hard error.

`runner.delay_action_step` is a signed real-valued offset. The zero-based
selection coordinate is `n_obs_steps - 1 + delay_action_step`. Integral
coordinates preserve direct indexing exactly. Fractional coordinates use
deterministic linear interpolation: `lower=floor(coordinate)`,
`upper=ceil(coordinate)`, and `alpha=coordinate-lower`. With four observations,
`0.5` blends indices 3/4 (the delay-0/delay-1 outputs), while `-0.5` blends
indices 2/3 (the delay-1/delay-0 outputs). An explicit base index 4 plus delay 1
still selects index 5 exactly.

Interpolation is allowed only when both configured action-schedule endpoints
have terminal noise level exactly 0. The current rolling H20 raw terminal row
is `[0,1,...,19]`; task070 now overrides only the selected endpoint transition
on the final denoising iteration. Integral delay pins one endpoint to clean;
fractional delay pins floor and ceil to clean, then interpolates. The existing
final backbone prediction is reused, so this adds no network evaluation.
Runtime logs lower/upper indices, terminal levels, and alpha before its loop;
clean-partial and partial-partial pairs fail closed.

With base index 3, the range-valid signed delay interval is `[-3, 15]` (selected
coordinates 0–18). Delay 0 pins index3, delay1 pins index4, `-0.5` pins indices
2/3, and `0.5` pins indices3/4. Values outside the interval fail without
clamping. This intentionally changes rolling delay-0 and delay-1 output from
the earlier partially noisy selection, which did not satisfy the original
noise-0 requirement. Old checkpoint configs without the field resolve to
`0.0`; the exporter records the float and its source in the manifest.

## Normalization

The exporter copies the checkpoint normalizer's scale/offset directly:

```text
normalize:   y = x * scale + offset
denormalize: x = (y - offset) / scale
```

Do not copy values into `config/g1_deploy_config.yaml`; use the generated
config beside the exported resources.

## Observation profiles

| Profile | Dim | Contents | FK |
|---|---:|---|---|
| `G1_RLObs` | 96 | joints, projected gravity, base velocities, last action | no |
| `G1` | 192 | body position/velocity plus root terms | yes |
| `G1_EE` | 198 | `G1` plus end-effector offset | yes |
| `G1_Q` | 70 | root and joint-space terms | no |

Without FK, body-space profiles contain invalid zero placeholders for most
bodies. Build with `--with-fk`, keep `env.use_fk: true`, and use the exported
canonical G1 URDF.

## FK dependencies on a workstation

`pip install pin` provides Pinocchio through a cmeel prefix. Some environments
also need `urdfdom_headers` from conda-forge. `build.sh --with-fk` detects the
cmeel prefix; otherwise pass it via `CMAKE_PREFIX_PATH` or `--cmake-arg`.

The Jetson installer uses its own checksum-pinned Pinocchio closure and
package-owned URDF; do not apply workstation dependency recipes to the robot.
