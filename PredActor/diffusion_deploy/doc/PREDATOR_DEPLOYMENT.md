# PredActor deployment

This guide covers the paper deployment profile for the Unitree G1. The
exporter creates a self-contained policy directory; learned weights are kept
outside the source repository.

## Export

Run from `diffusion_deploy` in the PDPlanner checkout:

```bash
PYTHONNOUSERSITE=1 PYTHONPATH=.. python tools/export_policy.py \
  --checkpoint /path/to/checkpoint.ckpt --config checkpoint \
  --output models/my_policy --mode backbone --target native \
  --obs-profile G1 --no-use-fk --deploy-config deploy_config.yaml --gui
```

For the Jetson JP5 Torch 2.1 runtime, use `--target jetson-jp5-torch21`.
In the GUI, keep the checkpoint settings: `G1`, FK disabled, FP32, DDIM-2,
`reuse_x0`, packed attention, and the checkpoint's condition dimension. The G1
paper profile does not use `base_lin_vel`; its WBG `vx` body is `pelvis` (`[0]`).
Verify the bundle:

```bash
./scripts/verify_model_resources.sh --resource-dir models/my_policy --require-text
(cd models/my_policy && sha256sum -c SHA256SUMS)
```

## Build

On a Linux workstation with LibTorch and the Unitree SDK available:

```bash
./build.sh --backend torch --download-runtime auto --with-sdk2 --with-fk \
  --with-command-publish --jobs 4
```

## MuJoCo sim2sim

Start Unitree MuJoCo in one terminal, then run the policy in another. Set the
generated network interface to `lo` for this route:

```bash
../../deps/deploy/unitree_mujoco/simulate/build/unitree_mujoco -r g1 -i 0 --camera-follow
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode control --unified-command --command-source joydev \
  --command-device /dev/input/js0 --command-mapping xbox_new
```

## Wired G1

Connect the workstation to the robot Ethernet interface, set that interface
in `deploy_config.yaml`, and validate it before enabling control:

```bash
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode offline --validate-config
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode control --unified-command --command-source unitree_lowstate
```

Only one controller may publish commands. Keep the E-stop accessible and
perform the first launch with an operator present.

## Onboard G1

Copy the exported `diffusion_deploy` tree and policy directory into a fresh
directory under the robot user's home. On JP5, install the locked user-local
runtime with:

```bash
./scripts/install_g1_jp5.sh --model-dir ~/CodeSpace/models/my_policy
```

For JP6, follow [the onboard installation guide](G1OnboardDeployDoc/PUBLIC_ONBOARD.md).
It checks the JetPack profile, installs dependencies below the user's home,
and starts with the same `--mode offline --validate-config` gate before any
control command.

## Checkpoint artifacts

Download published evaluation artifacts from
[MasterYip/PredActor_Artifacts](https://huggingface.co/MasterYip/PredActor_Artifacts).
Place the downloaded checkpoint in the exporter input path, export it locally,
and keep the generated resource directory together with `SHA256SUMS`. The
public source tree never contains learned checkpoint files.
