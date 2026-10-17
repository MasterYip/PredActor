# Workstation build and launch reference

## Dependencies

Base requirements are CMake 3.20+, a C++17 compiler, Eigen3, yaml-cpp, and
threads. Optional features add LibTorch, ONNX Runtime, Unitree SDK2/CycloneDDS,
and Pinocchio.

## Supported build entry point

```bash
./build.sh --backend none
./build.sh --backend torch --download-runtime auto
./build.sh --backend onnx --download-runtime auto
./build.sh --backend torch --download-runtime auto --with-sdk2
./build.sh --backend torch --download-runtime auto --with-sdk2 --with-fk
./build.sh --clean --backend torch --download-runtime auto --with-sdk2 --with-fk
```

Key mappings are:

| build.sh flag | CMake option |
|---|---|
| `--backend torch` | `USE_TORCH=ON` |
| `--backend onnx` | `USE_ONNX=ON` |
| `--with-sdk2` | `USE_UNITREE_SDK2=ON` |
| `--with-fk` | `USE_FK=ON` |
| `--build-dir DIR` | selected CMake binary directory |
| `--cmake-arg ARG` | additional CMake configure argument |

`ENABLE_UNITREE_COMMAND_PUBLISH=ON` is not supported: configuration fails by
design. `--with-sdk2` therefore means state transport, not command transport.

## Manual CMake equivalent

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DUSE_TORCH=ON \
  -DUSE_UNITREE_SDK2=ON \
  -DUSE_FK=ON \
  -DENABLE_UNITREE_COMMAND_PUBLISH=OFF
cmake --build build -j"$(nproc)"
```

Set `CMAKE_PREFIX_PATH`, `UNITREE_SDK2_PATH`, or `ONNXRUNTIME_ROOT` only when
the automatic discovery path is insufficient. `build.sh --with-fk`
auto-detects a Python `cmeel.prefix` where possible.

## Runtime downloads

`--download-runtime auto` selects the runtime needed by the backend. The
standalone downloader is also available:

```bash
./scripts/download_inference_runtime.sh torch
./scripts/download_inference_runtime.sh onnx
./scripts/download_inference_runtime.sh all
```

The optional first positional argument is a target directory; the second is
`libtorch`, `torch`, `onnx`, or `all`. The script has no `--help` flag.

## Simulator and runtime are separate processes

`scripts/run.sh` never starts Unitree MuJoCo. The normal superproject command
for the visible simulator is:

```bash
../../deps/deploy/unitree_mujoco/simulate/build/unitree_mujoco -r g1 -i 0
```

The safe current runtime entry point is the binary directly, because it exposes
the bounded `--mode` and `--max-steps` gates:

```bash
./build/run_g1_robot --help
./build/run_g1_robot --config <deploy_config.yaml> \
  --mode receive-only --max-steps 1 --no-fsm
./build/run_g1_robot --config <deploy_config.yaml> \
  --mode no-publish --device cuda:0 --max-steps 200 --no-fsm
```

## `scripts/run.sh`

`run.sh` orchestrates the C++ runtime and optional CLIP/WBG senders in tmux or
foreground processes. It supports config/device/model, FSM, CLIP sender, WBG
sender, build directory, and Python-interpreter options. It does **not** expose
`--mode` or `--max-steps`; do not use it for the receive-only task-039 safety
gate.

Its historical examples assumed a command-capable `UnitreeEnv`. Until a
separately reviewed publisher exists, invoking `run.sh` can only lead to
offline/no-publish behavior selected by the effective deploy config.
