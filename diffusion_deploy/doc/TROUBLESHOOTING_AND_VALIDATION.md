# Troubleshooting and validation

## Common build/config failures

- **LibTorch not found:** use `--download-runtime auto` or provide its CMake
  prefix.
- **ONNX Runtime not found:** use the runtime downloader or set
  `ONNXRUNTIME_ROOT`.
- **Pinocchio not found:** build with `--with-fk` in the Python environment
  containing `pin`, or pass its `cmeel.prefix` through `CMAKE_PREFIX_PATH`.
- **urdfdom_headers not found:** install it in the workstation environment;
  the Jetson installer has a separate locked closure.
- **Timeout waiting for state:** verify simulator/robot availability, DDS
  transport, and the exact interface (`lo` for MuJoCo; dedicated NIC for G1).
- **Action dimension mismatch:** policy and config must both use the G1 29-DoF
  contract.
- **Wrong/zero body state:** body-space profiles require a `USE_FK=ON` build,
  `use_fk: true`, and a valid exported URDF.
- **Profile tuple mismatch / offline cache miss / checksum failure:** stop;
  never bypass the Jetson platform lock or substitute an unpinned artifact.

## Interface and command discovery

```bash
./build.sh --help
./scripts/run.sh --help
./scripts/install_g1_jp5.sh --help
python tools/export_policy.py --help
./build/run_g1_robot --help
```

`download_inference_runtime.sh` uses positional arguments rather than a help
flag: `./scripts/download_inference_runtime.sh [target_dir]
[libtorch|torch|onnx|all]`.

The compiled runner help is authoritative for runtime flags. The source guard
is authoritative for command capability.

## Shell/source safety checks

```bash
bash -n build.sh scripts/*.sh
bash test/test_unitree_no_publish_source.sh .
python test/test_deploy_manager.py
python test/test_g1_urdf_resource.py
```

The compile gate proves that a normal build excludes command publication and
that CMake accepts `ENABLE_UNITREE_COMMAND_PUBLISH=ON` only with
`USE_UNITREE_SDK2=ON`; use `--with-sdk2 --with-command-publish`.

## Resource and packaging checks

```bash
./scripts/verify_model_resources.sh --resource-dir models/my_policy
(cd models/my_policy && sha256sum -c SHA256SUMS)
bash test/test_model_resource_isolation.sh .
bash test/test_jp5_build_routing.sh .
bash test/test_unitree_sdk2_discovery.sh . /tmp/diffusion-deploy-sdk2-test
```

Text-conditioned readiness can request the stronger resource check after
configuring the external encoder path:

```bash
export DIFFUSION_DEPLOY_CLIP_PATH=/path/to/clip/resources
./scripts/verify_model_resources.sh \
  --resource-dir models/my_cond_policy --require-text
```

The C++ runtime does not consume that environment variable; it confirms that
the separate sender has an encoder resource.

## Numerical tests

The tree includes normalizer, config-parser, actor parity, PRDP contract, WBG
gradient, UDP, and DDIM-step tests. Build-generated binaries live under the
selected CMake build directory. Fixture generators generally need the
PDPlanner Python environment and `PYTHONPATH=..`.

Numerical parity or finite actions are model/runtime checks only. They are not
closed-loop stability or physical-control evidence.

## Historical diagnostics

Long-running observations and older debug prompts remain in
[`debug_log.md`](debug_log.md). Treat them as historical context; current
interfaces and source guards take precedence.
