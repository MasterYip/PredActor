# Architecture and package layout

`diffusion_deploy` mirrors the Python `diffusion_policy` inference path in C++.
It is laid out like a ROS package but is ROS-independent at runtime.

## Runtime flow

```text
DDS/offline state
  -> UnitreeEnv / ObsTerms
  -> ObsComposer + observation history + normalizer
  -> DiffusionAgent
  -> TorchActor / DiffusionActor / JointDiffusionActor / DiffuseCLoCActor
  -> action denormalization and host-side action transform
  -> current build: discard action (no command publisher)
```

External text conditioning and WBG commands enter through separate UDP
receivers. Pinocchio FK is optional at build time and mandatory for body-space
profiles that consume full body position/velocity.

## Package layout

```text
diffusion_deploy/
├── CMakeLists.txt, build.sh, setup.py
├── config/                     # templates and WBG/FSM examples
├── deps/platform-lock.json     # locked Jetson platform artifacts
├── examples/run_g1_robot.cpp   # runtime entry point
├── include/diffusion_deploy/
│   ├── actor/                  # Torch/ONNX/diffusion actors
│   ├── agent/                  # actor + normalizer wrapper
│   ├── env/                    # state acquisition and action transform
│   ├── guidance/               # PRDP whole-body guidance
│   ├── obs/                    # observation terms/composition
│   ├── runner/                 # bounded/realtime inference loop
│   ├── safety/                 # FSM, joystick, validators
│   └── utils/                  # config, history, math, FK
├── python/diffusion_deploy_manager/  # JP5 doctor/bootstrap/build/install CLI
├── resources/g1/               # canonical URDF, license, provenance
├── scripts/                    # build, run, install, verify, bundle helpers
├── tools/                      # exporter and conditioning utilities
└── test/                       # parser, parity, safety, packaging tests
```

## Python/C++ correspondence

| Python concept | C++ implementation |
|---|---|
| environment state | `UnitreeEnv`, `ObsTerms` |
| profile normalization | `ObsComposer`, `Normalizer` |
| rolling observation buffer | `ObsHistory` |
| policy wrapper | `DiffusionAgent` |
| diffusion/PRDP actor | `DiffusionActor`, `JointDiffusionActor`, `DiffuseCLoCActor` |
| G1 FK | `G1ForwardKinematics` |
| evaluation loop | `EnvRunner` |

## Execution modes

- `offline`: synthetic/offline state; no DDS initialization.
- `receive-only`: initialize state subscribers, validate one snapshot, and
  reject `step()`.
- `no-publish`: receive state and execute policy/action transforms while the
  transformed action is discarded.

There is deliberately no `publish` mode. See
[Safety and control status](SAFETY_AND_CONTROL_STATUS.md).
