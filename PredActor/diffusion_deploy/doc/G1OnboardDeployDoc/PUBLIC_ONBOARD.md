# Onboard G1 installation

This guide installs the deployment runtime in a user-owned directory on a
Unitree G1 Jetson. Keep the exported policy directory and its `SHA256SUMS`
file together. Use a fresh release directory for each installation.

## Copy the release

From the development computer, copy the public runtime and exported policy:

```bash
rsync -a --delete PredActor/diffusion_deploy/ \
  <user>@<robot-host>:~/CodeSpace/PredActor/diffusion_deploy/
rsync -a --delete models/my_policy/ \
  <user>@<robot-host>:~/CodeSpace/models/my_policy/
```

## JP5

On the robot, install the locked user-local runtime. The installer does not
use `sudo` or modify system directories:

```bash
cd ~/CodeSpace/PredActor/diffusion_deploy
./scripts/install_g1_jp5.sh --model-dir ~/CodeSpace/models/my_policy
```

Use `--offline` when the dependency cache has been prepared in advance.

## JP6

Check the platform lock before building, then use a publisher-disabled build
for the first validation:

```bash
cd ~/CodeSpace/PredActor/diffusion_deploy
export PYTHONPATH="$PWD/python${PYTHONPATH:+:$PYTHONPATH}"
python3 -m diffusion_deploy_manager.cli --lock deps/platform-lock.json \
  doctor --profile jetson-jp6
./build.sh --backend torch --download-runtime auto --with-sdk2 --with-fk \
  --build-dir ~/CodeSpace/build-nopublish --jobs 2
```

## Validate before control

```bash
./scripts/verify_model_resources.sh --resource-dir ~/CodeSpace/models/my_policy --require-text
(cd ~/CodeSpace/models/my_policy && sha256sum -c SHA256SUMS)
~/CodeSpace/build-nopublish/run_g1_robot \
  --config ~/CodeSpace/models/my_policy/deploy_config.yaml \
  --mode offline --validate-config --device cuda:0
```

Check the printed network interface, condition dimension, `base_lin_vel`
setting, and WBG body indices. Only then should an on-site operator enable
the control launch. Confirm the E-stop, passive/ready/running transitions,
the wired interface, and that no other controller is publishing.

See [the deployment guide](../PREDATOR_DEPLOYMENT.md) for the wired launch
command and the MuJoCo sim2sim route.
