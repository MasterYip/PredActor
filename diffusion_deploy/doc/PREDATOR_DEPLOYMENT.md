# PredActor deployment release

This is the short release runbook for the C++ `diffusion_deploy` library. The
longer references remain authoritative for the platform lock and safety gates:
[policy export](POLICY_EXPORT_AND_CONFIG.md), [workstation build](WORKSTATION_BUILD.md),
and [onboard deployment](G1OnboardDeployDoc/PUBLIC_ONBOARD.md).

The public deploy profile is a minimal runtime export. It contains the C++
runtime, exporter and GUI, platform bootstrap, launch/install scripts, G1
asset, and these runbooks. It omits historical tests and benchmarks, old
deployment records, experiment utilities, build/cache directories, and all
learned or compiled model files. Re-run the `deploy` profile from the source
commit whenever this surface changes; do not copy files from an old public
checkout by hand.

## Default policy and provenance

The latest deployed policy is **PDP067 Standard2 full r1**, package
`pdp067_standard2_full_jp5_ddim2`. It is the full D256/H4/L2 PRDP
policy, with FP32 NS-DDIM2 (two backbone forwards), packed attention,
condition-embedding reuse, DDIM precomputation, and `reuse_x0` guidance.
Its condition is 93 robot dimensions plus 512 text dimensions (605 total) and
does **not** contain `base_lin_vel`. The deployed checkpoint SHA-256 is:

```text
ef3fa1d65b7e1ec408e24506ca0610da34ed1c392eac648d46ecab9a193cc0a0
```

The package's WBG contract uses pelvis-only `vx` (`[0]`); `vy` and `wz` use
the recorded Standard2 body set. Do not infer a deployment contract from a
generic training YAML.

## Export a policy

Run this in the PDPlanner Python environment. `--config checkpoint` is the
default and reads the immutable configuration embedded in the checkpoint.
The output directory must be new or an explicitly reviewed empty directory.

```bash
cd /path/to/PegasusMoDye/PDPlanner/diffusion_deploy
PYTHONNOUSERSITE=1 PYTHONPATH=.. python tools/export_policy.py \
  --checkpoint /absolute/path/to/checkpoints/latest.ckpt \
  --config checkpoint \
  --output models/my_policy \
  --mode backbone \
  --target native \
  --obs-profile G1 \
  --use-fk \
  --deploy-config deploy_config.yaml \
  --gui
```

For the JP5 Torch 2.1 target, replace `--target native` with
`--target jetson-jp5-torch21`. The paper deployment defaults are FP32,
`G1`, FK enabled, `reuse_x0`, and the checkpoint's sampler; the exporter
records them in `deploy_config.yaml` and `resource_manifest.yaml`.

### GUI review

The optional `--gui` editor opens the extracted checkpoint settings before
writing files. Review these fields and leave them unchanged for the paper
profile: actor type (`prdp`), `obs_profile=G1`, `data_profile=g1_prdp_standard2`,
condition dimension 605, FP32, DDIM steps 2/NS-DDIM, `reuse_x0`, attention
packing `all`, condition reuse enabled, FK enabled, and WBG body indices
`vx=[0]`, `vy/wz=[0,3,4,5,6,7,8,9]`. Do not add `base_lin_vel` or replace the
embedded config with a generic profile. Use **Export** only after checking the
output path and the generated network interface (`lo` for simulation).

Verify the resulting bundle before launch:

```bash
./scripts/verify_model_resources.sh --resource-dir models/my_policy --require-text
(cd models/my_policy && sha256sum -c SHA256SUMS)
```

## A. MuJoCo sim2sim

Build the command-publishing workstation target once:

```bash
cd /path/to/PegasusMoDye/PDPlanner/diffusion_deploy
./build.sh --backend torch --download-runtime auto --with-sdk2 --with-fk \
  --with-command-publish --jobs 4
```

In one terminal start Unitree MuJoCo from the superproject:

```bash
../../deps/deploy/unitree_mujoco/simulate/build/unitree_mujoco -r g1 -i 0 --camera-follow
```

In a second terminal, run the exported policy. Keep `env.network_interface: lo`
for this path:

```bash
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode control --unified-command --command-source joydev \
  --command-device /dev/input/js0 --command-mapping xbox_new
```

For a text-conditioned bundle without cached command latents, append
`--cond-udp --clip-mode teleop --clip-default stand --clip-checkpoint
/absolute/path/to/motionclip.pth.tar`.

## B. Wired workstation deployment

Use the same build and exported resources as Path A. Do not start MuJoCo.
Set `env.network_interface` in the generated deploy YAML to the dedicated G1
Ethernet interface, verify it, and then run:

```bash
ip -br addr
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode control --unified-command --command-source unitree_lowstate \
  --build-dir build
```

The command publishes motor control. Keep the area clear, confirm one active
controller, and use the robot E-stop. RB enters Ready, X enters Running, and B
returns to Passive. `--mode offline --validate-config` is the read-only check.

## C. Onboard G1 deployment

The supported human installation is additive and user-owned. It requires a
fresh release directory, a matching JetPack profile, and a verified model
bundle. On a JP5 Orin, copy the repository and exported model directory to the
robot, then run the installer (no `sudo`, no system package edits):

```bash
cd ~/CodeSpace/PegasusMoDye/diffusion_deploy
./scripts/install_g1_jp5.sh --model-dir ~/CodeSpace/models/my_policy
```

For JP6 use the locked procedure in
`G1OnboardDeployDoc/PUBLIC_ONBOARD.md`; it installs the pinned Torch/CUDA/Pinocchio
closure below a fresh `~/CodeSpace` release root. After installation, run the
read-only gate first:

```bash
~/CodeSpace/PredActor/install/diffusion-deploy/releases/<commit>/bin/run_g1_robot \
  --config ~/CodeSpace/PredActor/models/my_policy/deploy_config.yaml \
  --mode offline --validate-config --device cuda:0
```

Only after the on-site operator confirms the E-stop, robot mode, interface,
resource hashes, and a single controller should the held control command be
used. Do not run it during provisioning or unattended.

## External checkpoint rule

`diffusion_deploy` exports learned graphs from an explicit checkpoint but does
not add checkpoints to the public Git tree. Keep the deployed checkpoint/package
in the private artifact store or a separately permissioned artifact repository,
verify its SHA-256, and copy the resulting resource directory to the target
machine. The public source export contains code, configs, documentation, and
licensed G1 assets only.
