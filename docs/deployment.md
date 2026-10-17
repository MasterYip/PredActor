# Deploying PredActor

This guide covers the complete path from a trained checkpoint to a running
PredActor controller. The source runtime is under
`PredActor/diffusion_deploy/`; learned weights are downloaded separately from
the [PredActor artifacts repository](https://huggingface.co/MasterYip/PredActor_Artifacts).

The examples use the paper deployment profile: the embedded checkpoint
configuration, the G1 body-space observation profile, FK enabled, FP32
inference, and the checkpoint's sampler. Use the same profile when reproducing
the released controller.

## 1. Export a policy

From the repository root, export a trained checkpoint with the paper profile:

```bash
uv run --locked python PredActor/diffusion_deploy/tools/export_policy.py \
  --checkpoint /absolute/path/to/latest.ckpt \
  --config checkpoint \
  --output Artifacts/deploy/my_policy \
  --mode backbone --target native --obs-profile G1 --use-fk
```

`--config checkpoint` reads the model settings saved with the checkpoint. Use
`--gui` when you want to inspect the export settings before writing the bundle.
Leave the paper defaults unchanged: `G1`, FK enabled, FP32, the checkpoint
sampler, and the WBG body mapping supplied by the checkpoint. The exporter
writes a self-contained runtime configuration next to the TorchScript model.

For a Jetson JP5 target, use `--target jetson-jp5-torch21`. The generated
bundle can be copied to the target machine after export.

Check the bundle before launching:

```bash
PredActor/diffusion_deploy/scripts/verify_model_resources.sh \
  --resource-dir Artifacts/deploy/my_policy --require-text
(cd Artifacts/deploy/my_policy && sha256sum -c SHA256SUMS)
```

## 2. Build the runtime

Build once on the workstation that will run the controller:

```bash
cd PredActor/diffusion_deploy
./build.sh --backend torch --download-runtime auto --with-sdk2 --with-fk \
  --with-command-publish --jobs 4
```

The build uses the platform lock shipped with the runtime. SDK2 is needed for
the wired and onboard paths; MuJoCo only needs the command-publishing target.

## 3. Run in Unitree MuJoCo

Start Unitree MuJoCo in one terminal. From the deployment build, start the
policy in a second terminal and keep the network interface set to `lo`:

```bash
../../deps/deploy/unitree_mujoco/simulate/build/unitree_mujoco \
  -r g1 -i 0 --camera-follow
```

```bash
PredActor/diffusion_deploy/scripts/run.sh \
  --config Artifacts/deploy/my_policy/deploy_config.yaml \
  --fsm-config Artifacts/deploy/my_policy/fsm_config.yaml \
  --device cuda:0 --mode control --unified-command \
  --command-source joydev --command-device /dev/input/js0 \
  --command-mapping xbox_new
```

For a text command channel, add `--cond-udp --clip-mode teleop` and provide
the MotionCLIP checkpoint downloaded from the artifacts repository.

## 4. Run from a wired workstation

Connect the workstation and G1 with the Unitree Ethernet link. Set
`env.network_interface` in the generated deploy YAML to that interface, then
run the controller from the repository root:

```bash
ip -br addr
PredActor/diffusion_deploy/scripts/run.sh \
  --config Artifacts/deploy/my_policy/deploy_config.yaml \
  --fsm-config Artifacts/deploy/my_policy/fsm_config.yaml \
  --device cuda:0 --mode control --unified-command \
  --command-source unitree_lowstate --build-dir PredActor/diffusion_deploy/build
```

Before enabling control, confirm the interface, E-stop, robot mode, and that
only one controller is connected. Use the read-only configuration check first:

```bash
PredActor/diffusion_deploy/scripts/run.sh \
  --config Artifacts/deploy/my_policy/deploy_config.yaml \
  --mode offline --validate-config --device cuda:0
```

## 5. Run onboard on a Jetson G1

Copy the repository and exported model bundle to the robot, then install the
locked runtime in a fresh release directory. The installer does not modify
system packages:

```bash
cd ~/PredActor/PredActor/diffusion_deploy
./scripts/install_g1_jp5.sh --model-dir ~/PredActor/Artifacts/deploy/my_policy
```

For JP6, use the [onboard installation guide](../PredActor/diffusion_deploy/doc/G1OnboardDeployDoc/PUBLIC_ONBOARD.md)
for the matching JetPack and Torch runtime. Run the offline validation command
before entering control mode, then use the robot E-stop and a single operator
while starting the controller.

## Checkpoint location

The released deployment checkpoint is maintained in
[MasterYip/PredActor_Artifacts](https://huggingface.co/MasterYip/PredActor_Artifacts).
Keep the downloaded checkpoint and exported bundle outside Git. The public
source repository contains the exporter, runtime, configuration examples, and
G1 assets; it does not embed learned weights.

To use the released deployment bundle without exporting again, download it
with the public HF manifest:

```bash
uv run --locked python scripts/hf_download.py \
  --filter checkpoints/deployment
```

The bundle is placed at
`Artifacts/deploy/pdp067_standard2_full_jp5_ddim2/`.
