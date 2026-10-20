# PredActor deployment

This is the public deployment guide for a trained PredActor policy. It covers
export, workstation builds, Unitree MuJoCo sim2sim, a wired G1, and an onboard
G1. The runtime reads the generated `deploy_config.yaml`; keep that file,
`fsm_config.yaml`, the model files, `resource_manifest.yaml`, and
`SHA256SUMS` together.

The released checkpoint and optional deployment bundles are distributed from
the [PredActor artifacts repository](https://huggingface.co/MasterYip/PredActor_Artifacts).

## 1. Export a policy

Run the exporter in the Python environment used to train or evaluate the
checkpoint. The checkpoint-embedded configuration is the default. For the
paper PRDP profile, use the G1 observation contract with FK disabled:

```bash
cd /path/to/PegasusMoDye/PDPlanner/diffusion_deploy
PYTHONNOUSERSITE=1 PYTHONPATH=.. python tools/export_policy.py \
  --checkpoint /absolute/path/to/checkpoint.ckpt \
  --config checkpoint \
  --output models/my_policy \
  --mode backbone --target native --obs-profile G1 --no-use-fk \
  --deploy-config deploy_config.yaml --gui
```

The GUI is optional. Before exporting, check the checkpoint's actor type,
DDIM/PRDP sampler, FP32 precision, text-condition dimension, WBG mapping,
`use_fk: false`, and the generated network interface. Do not replace the
embedded configuration with an unrelated training YAML.

For a Jetson JP5 target, replace `--target native` with
`--target jetson-jp5-torch21`. The exporter writes a complete resource
directory; do not copy only the backbone file.

Verify the bundle before using it:

```bash
diffusion_deploy/scripts/verify_model_resources.sh \
  --resource-dir diffusion_deploy/models/my_policy --require-text
(cd diffusion_deploy/models/my_policy && sha256sum -c SHA256SUMS)
```

## 2. Build the runtime

Initialize the pinned deployment dependencies once:

```bash
cd /path/to/PredActor/PredActor/diffusion_deploy
./scripts/init_deploy_deps.sh
```

On a workstation with LibTorch:

```bash
./build.sh --backend torch --download-runtime auto --with-sdk2 --jobs 4
```

The PRDP release does not need forward kinematics. Add `--with-fk` only for a
checkpoint whose exported observation profile explicitly requires FK. The
build needs CMake 3.20+, a C++17 compiler, Eigen3, yaml-cpp, threads, CUDA
and LibTorch. `--with-sdk2` enables Unitree state transport; the simulator
and wired paths additionally require the corresponding Unitree DDS runtime.

## 3. MuJoCo sim2sim

Start Unitree MuJoCo in one terminal. The simulator is a separate process:

```bash
cd /path/to/PredActor/PredActor/diffusion_deploy
./deps/unitree_mujoco/simulate/build/unitree_mujoco -r g1 -i 0 --camera-follow
```

Keep `env.network_interface: lo` in the generated deploy YAML. In a second
terminal, connect a local Xbox-compatible joystick at `/dev/input/js0` and
launch the unified interface:

```bash
cd /path/to/PredActor/PredActor/diffusion_deploy
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode control --unified-command --command-source joydev \
  --command-device /dev/input/js0 --command-mapping xbox_new
```

Use `--mode offline --validate-config` first when checking a new bundle.

## 4. Wired G1

Set `env.network_interface` in `deploy_config.yaml` to the dedicated G1
Ethernet interface, then confirm the interface and model resources:

```bash
cd /path/to/PredActor/PredActor/diffusion_deploy
ip -br addr
./scripts/verify_model_resources.sh --resource-dir models/my_policy --require-text
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode offline --validate-config
```

After the offline check passes, connect the Unitree remote through LowState
and enable control:

```bash
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode control --unified-command --command-source unitree_lowstate
```

Confirm the robot is in the expected FSM state, the E-stop is reachable, and
no other controller is publishing before using `--mode control`.

## 5. Onboard G1

Copy `PredActor/diffusion_deploy` and the exported model directory to a fresh
user-owned release directory on the Jetson. Then install the locked runtime:

```bash
cd ~/CodeSpace/PredActor/diffusion_deploy
./scripts/install_g1_jp5.sh --model-dir ~/CodeSpace/models/my_policy
```

For JetPack 6, use the matching JP6 image and the same package-owned source;
the installer must not overwrite an existing release. Run the resource and
offline validation checks before enabling the robot:

```bash
./scripts/verify_model_resources.sh --resource-dir ~/CodeSpace/models/my_policy --require-text
RELEASE=~/CodeSpace/PredActor/install/diffusion-deploy/releases/<source-commit>
"$RELEASE/bin/run_g1_robot" \
  --config ~/CodeSpace/models/my_policy/deploy_config.yaml \
  --mode offline --validate-config --device cuda:0
```

Once the operator has checked the network interface, FSM, E-stop, and model
hashes, use the same unified-command launch as the wired path, with
`--command-source unitree_lowstate`.

## Unified joystick interface

The unified interface is one in-process command reader. It accepts either a
Linux joydev device or the Unitree wireless bytes already present in LowState;
it does not require a GUI or a Python sender.

| Control | Action |
|---|---|
| Left stick | `vx` (forward/back) and `vy` (left/right) guidance |
| Right stick horizontal | `wz` yaw guidance |
| D-pad Up/Right/Down/Left | select `stand`, `walk`, `jog`, `squat down` |
| LB rising edge | toggle whole-body guidance |
| L2 | switch configured WBG Kp between released and pressed values |
| L3 rising edge | enable/disable `vx` and `vy` together |
| R3 rising edge | enable/disable `wz` |

Configure bounds, deadzone, mapping, and source in the exported YAML. The
values are used directly; for example:

```yaml
runner:
  unified_command:
    enabled: true
    source: joydev
    joystick_device: /dev/input/js0
    joystick_mapping: xbox_new
    deadzone: 0.10
    wbg:
      max_vx: 5.0
      max_vy: 5.0
      max_wz: 5.0
```

For an SSH-only session, the read-only status listener can use its terminal
fallback:

```bash
python tools/unified_command_dashboard.py --host 127.0.0.1 --port 9880 --mode tui
```

Add `--record-csv path/to/commands.csv` to `run.sh` when a per-tick record of
the selected motion, joystick input, WBG values, observation, and action is
needed. The unified mode is mutually exclusive with the legacy `--cond-udp`
and `--wbg-udp` sender modes.

## Troubleshooting

- A missing or stale joystick source selects `stand`, zeros guidance, and
  reports the controller disconnected.
- A checksum or manifest mismatch means the model directory must be copied
  again; do not edit generated resources in place.
- If the build reports missing LibTorch, set `CMAKE_PREFIX_PATH` or rerun
  `./build.sh --download-runtime auto`.
- For SSH operation, use the TUI listener; the deployment runtime itself has
  no display dependency.
