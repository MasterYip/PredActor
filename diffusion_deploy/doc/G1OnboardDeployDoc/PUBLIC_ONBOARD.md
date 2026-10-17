# Onboard G1 installation

This page is the public installation guide for a user-owned G1 Jetson release.
It does not contain a robot address, SSH key, or a control command for a
particular machine. Keep the policy resource directory and its checksum file
together, and install into a fresh directory under the robot user's home.

## 1. Copy the release and policy package

On the development computer, copy the committed `diffusion_deploy` tree and
the externally supplied exported model directory to the robot. Do not copy a
training checkpoint in place of an exported resource bundle.

```bash
rsync -a --delete diffusion_deploy/ <user>@<robot-host>:~/CodeSpace/PegasusMoDye/diffusion_deploy/
rsync -a --delete models/my_policy/ <user>@<robot-host>:~/CodeSpace/models/my_policy/
```

## 2. JP5 Orin

The installer is user-local and uses the locked runtime profile. It refuses a
wrong CPU/JetPack tuple and never calls `sudo` or edits system directories:

```bash
ssh <user>@<robot-host>
cd ~/CodeSpace/PegasusMoDye/diffusion_deploy
./scripts/install_g1_jp5.sh --model-dir ~/CodeSpace/models/my_policy
```

For a disconnected robot, seed the installer cache on the host and add
`--offline`. See `deps/platform-lock.json` for the exact package hashes.

## 3. JP6 Orin

Use the same layout and run the locked platform manager from the checked-out
tree. The manager installs dependencies below `~/CodeSpace` and the build is
publisher-disabled until an operator explicitly enables the control build:

```bash
cd ~/CodeSpace/PegasusMoDye/diffusion_deploy
export PYTHONPATH="$PWD/python${PYTHONPATH:+:$PYTHONPATH}"
python3 -m diffusion_deploy_manager.cli --lock deps/platform-lock.json doctor --profile jetson-jp6
./build.sh --backend torch --download-runtime auto --with-sdk2 --with-fk --build-dir ~/CodeSpace/build-nopublish --jobs 2
```

The exact JP6 Torch wheel, CUDA tuple, Pinocchio closure, and SDK2 source are
the ones recorded in `deps/platform-lock.json`. If the doctor fails, stop and
resolve the platform mismatch instead of forcing a near match.

## 4. Read-only validation

Verify the package before starting any process that opens DDS:

```bash
./scripts/verify_model_resources.sh --resource-dir ~/CodeSpace/models/my_policy --require-text
(cd ~/CodeSpace/models/my_policy && sha256sum -c SHA256SUMS)
~/CodeSpace/build-nopublish/run_g1_robot \
  --config ~/CodeSpace/models/my_policy/deploy_config.yaml \
  --mode offline --validate-config --device cuda:0
```

The command must report configuration validation without initializing the
environment or DDS. Check `base_lin_vel`, `data_profile`, condition dimension,
WBG body indices, and network interface in the printed configuration.

## 5. Operator handoff

Physical control is deliberately a separate, operator-held step. Before using
the control build, an on-site operator confirms the correct G1 Ethernet
interface, E-stop, passive/ready/running FSM transitions, one controller, and
the exact policy/package hashes. Do not run the control command during
installation, from an unattended SSH session, or while another controller is
active. The launch form is documented in `../PREDATOR_DEPLOYMENT.md`.
