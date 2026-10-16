# Jetson Orin NX deployment reference

This document holds the long-form details behind Path C in the top-level
runbook. The supported installer is `scripts/install_g1_jp5.sh`.

## Platform lock and system boundary

The `jetson-jp5` profile requires native aarch64 Ubuntu 20.04, Jetson Linux
R35.3.1 / JetPack 5.1.1, Python 3.8, CUDA 11.4, and NVIDIA's JP5 Torch 2.1
wheel. Artifact filenames, byte sizes, and SHA-256 values are selected by
`deps/platform-lock.json`.

The installer is user-local. It never calls `sudo` or `apt`, writes `/usr` or
`/etc`, edits shell profiles, installs services, changes system/network/device
permissions, or enables command publishing. It expects the robot image to provide Python with
PyYAML, CMake, a C++17 compiler, Git, `sha256sum`, Eigen, yaml-cpp,
CycloneDDS, and the JetPack CUDA toolkit. It also checks
`/usr/local/cuda/bin/nvcc` when `nvcc` is absent from `PATH`.

## Locked dependency closure

The profile downloads or consumes cached copies of:

- NVIDIA JP5 Torch 2.1;
- official Unitree SDK2 at the lock-selected commit;
- fmt source;
- Pinocchio 2.6.21 and its aarch64 native dependency closure; and
- lock-selected Boost/URDF/FCL/eigenpy/Assimp/OctoMap/Qhull dependencies.

Downloads are resumable and accepted only after size and checksum validation.
The SDK2 build enables state transport only; CMake still forces
`ENABLE_UNITREE_COMMAND_PUBLISH=OFF`.

The current installer is PRDP-specific: it requires the backbone, diffusion
schedule, emphasis matrices, and `data_profile: g1_prdp_standard`. General
non-PRDP bundles can be exported and used on workstations, but require a
separate installer extension before using this Jetson path.

## Fresh-machine compatibility boundary

Task 039 covered noninteractive CUDA discovery, Orin `sm_87`, official SDK2,
the complete Pinocchio closure, package-owned G1 resources, Torch 2.1 operator
lowering, ARM projection, CUDA-to-host action/history boundaries, and
idempotent content-addressed installs.

This does not guarantee an arbitrary newer robot image. JetPack 6 / L4T R36,
a different Python/CUDA ABI, missing base prerequisites, another architecture,
or an unavailable locked artifact must fail at doctor/bootstrap/build. Add and
validate a new platform profile rather than bypassing the gate.

New-profile acceptance requires a clean-home install, repeat/idempotence
check, checksums, offline CPU and CUDA inference, multi-step history, and target
latency measurement. Physical-control review remains separate.

## Online and offline installs

See Path C in the top-level README for the exact commands. Offline cache input
uses lock-named archives without renaming, including:

```text
torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl
fmt-9.1.0.tar.gz
unitree_sdk2-<locked-commit>.tar.gz
pin-2.6.21-1-cp38-cp38-manylinux_2_28_aarch64.whl
# plus every runtime_dependencies entry selected by platform-lock.json
```

`--offline` turns every cache miss into an error. `--dry-run` validates the
platform and prints manager plans without creating the install tree.

## Installed layout

```text
~/CodeSpace/HoffMan/
├── PDPlanner/                         # reviewed robot-local Git worktree
├── cache/                             # checksum-addressed archives
├── build/                             # user-owned build trees
├── install/diffusion-deploy/
│   ├── deps/                          # extracted Torch and sources
│   ├── runtime/                       # fmt and cmeel prefix
│   └── releases/<git-commit>/         # immutable binary release
├── models/<name>-<sha12>/             # immutable model resources
└── logs/
```

Every binary release contains `install-manifest.json`; every model release
retains `SHA256SUMS`. The installer never overwrites an existing release and
prints exact update/rollback paths.

## Model and FK resources

The package installs the canonical G1 URDF with license and provenance.
Model installation copies the export into a new immutable model release,
rebases paths relative to `deploy_config.yaml`, copies the package URDF, and
regenerates its manifest/checksums. The source export is not modified.

The equivalent public build command is:

```bash
./build.sh --backend torch --download-runtime auto --with-sdk2 --with-fk
```

The install manager supplies the exact locked Torch, Pinocchio, SDK2, and
CycloneDDS paths for JP5.

## Optional performance mode

Power mode and clock locking are not installer actions. They require a
separate privileged, on-site decision and increase power draw and temperature.
Inspect rather than modify by default:

```bash
sudo /usr/sbin/nvpmodel -q --verbose
sudo /usr/bin/jetson_clocks --show
```

On the task-039 Orin NX, mode 0 was already MAXN. A bounded operator-approved
`jetson_clocks` test improved no-guidance DDIM-5 median warm latency from
35.15 ms to 33.68 ms (about 4.2%); it still missed the 20 ms/50 Hz target.
Post-test junction temperature was 52.7°C. Clock locking is not a substitute
for the measured latency gate and must not be silently added to startup.

## Task-039 deployment result

The robot-side immutable JP5 SDK2+FK+Torch release and `prdp_2` resources
passed checksum, offline CPU/CUDA inference, finite-action, and no-publish
checks. The no-command source and build guards remained active throughout.
That result proves runtime portability and inference, not motor control.
