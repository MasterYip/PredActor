# PredActor deployment quickstart

The public source package places the runtime at `PredActor/diffusion_deploy/`.
Export a policy from a trained checkpoint before building:

```bash
cd PredActor/diffusion_deploy
PYTHONNOUSERSITE=1 PYTHONPATH=.. python tools/export_policy.py \
  --checkpoint /path/to/checkpoint.ckpt --config checkpoint \
  --output models/my_policy --mode backbone --target native \
  --obs-profile G1 --no-use-fk --deploy-config deploy_config.yaml --gui
./build.sh --backend torch --download-runtime auto --with-sdk2 --with-fk \
  --with-command-publish --jobs 4
```

The GUI should retain the checkpoint's G1, FK-disabled, FP32 and DDIM-2 settings. The
paper profile uses pelvis-only `vx` guidance and no `base_lin_vel`.

For MuJoCo, keep the interface set to `lo` and run:

```bash
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode control --unified-command --command-source joydev \
  --command-device /dev/input/js0 --command-mapping xbox_new
```

For a wired G1, validate first and then replace `offline` with `control` and
use `--command-source unitree_lowstate`:

```bash
./scripts/run.sh --config models/my_policy/deploy_config.yaml \
  --fsm-config models/my_policy/fsm_config.yaml --device cuda:0 \
  --mode offline --validate-config
```

Onboard installation is documented in
[Onboard Installation Guide](../PredActor/diffusion_deploy/doc/G1OnboardDeployDoc/PUBLIC_ONBOARD.md).
Checkpoint artifacts are published separately at
[MasterYip/PredActor_Artifacts](https://huggingface.co/MasterYip/PredActor_Artifacts).
