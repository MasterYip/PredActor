# Production layer profiling

`benchmark_production_profile` is an inference-only diagnostic target for the
actual `DiffusionAgent -> DiffuseCLoCActor -> TorchScript` deployment path. It
does not construct an environment or runner and does not link any DDS,
publisher, FSM, `LowCmd`, or `MotionSwitcher` entry point.

The benchmark intentionally has two measurement passes:

1. An uninstrumented actor baseline uses synchronized CPU wall time and CUDA
   events after warmup. This is the end-to-end performance anchor.
2. A Kineto pass exports raw operators/kernels and invokes the exact scripted
   submodules for decoder layer 0/1, self/cross attention, both MLP projections,
   GELU, all norms, residual add, embeddings, condition encoder, final norms,
   and output heads. These standalone probes explain component cost but are not
   additive estimates of end-to-end latency.

The profiler writes `baseline_timing.csv`, `run_summary.csv`,
`kineto_events.csv`, `kineto_trace.json`, and `torchscript_module_dump.txt`.
The analyzer produces component, attention, NFE, nested actor-span, and
per-call residual tables plus JSON and a diagnostic figure. The residual is
`actor_total` minus the disjoint condition-encoding, backbone, scheduler, and
WBG child spans. Raw events and the separate baseline remain canonical if an
aggregate looks surprising.

## Build

```bash
cmake -S . -B build-profile \
  -DCMAKE_BUILD_TYPE=Release -DUSE_TORCH=ON -DUSE_ONNX=OFF
cmake --build build-profile --target benchmark_production_profile -j2
```

## Run

Use the exact resolved production config and record its SHA-256 alongside the
model, schedule, emphasis matrix, binary, and source revision.

```bash
./build-profile/benchmark_production_profile \
  --config /absolute/path/deploy_config.yaml \
  --output-dir /absolute/path/task073-run \
  --device cuda:0 --precision fp32 \
  --warmup 20 --repetitions 100 \
  --profile-repetitions 10 --micro-warmup 5 --micro-repetitions 20 \
  --seed 73

python3 tools/analyze_production_profile.py \
  --events /absolute/path/task073-run/kineto_events.csv \
  --timing /absolute/path/task073-run/baseline_timing.csv \
  --output-dir /absolute/path/task073-analysis
```

Record `tegrastats`, power mode, clocks, process occupancy, Torch/CUDA/L4T
versions, shapes, precision, DDIM steps, warmup/repetitions, and before/after
thermal state. Benchmark sequentially and report profiler perturbation as
`profiled_mean_wall_ms / baseline_wall_p50_ms`; never substitute instrumented
latency for the uninstrumented baseline.

## Interpretation boundaries

- Exact submodule probes use the deployed TorchScript parameters and C++
  runtime, not an eager Python reconstruction.
- A microcomponent CUDA time can exceed its share of the full layer because
  isolated launches lose overlap and allocator/cache context.
- Q/K/V and output projection attribution uses the ordered GEMM groups inside
  each exact attention marker. `kineto_events.csv` preserves the raw linked
  correlation IDs for audit.
- `actor_total`, `agent_total`, backbone, scheduler, and WBG spans are nested
  and inclusive. Do not add them or combine their medians. The residual table
  subtracts disjoint child spans within each call before summarizing.
- Architectural changes such as fewer layers/width or a lower MLP ratio require
  matched training and policy-quality evaluation. They are not safe runtime
  toggles.
