# Deployment dependencies

The deployment tree keeps its external runtime sources as pinned Git
submodules. From the repository root, initialize them with:

```bash
PredActor/diffusion_deploy/scripts/init_deploy_deps.sh
```

The submodules are:

- `unitree_mujoco`: Unitree G1 MuJoCo simulator and robot MJCF assets;
- `mujoco`: MuJoCo headers and runtime used by the simulator;
- `unitree_sdk2`: C++ DDS SDK used by MuJoCo and wired/onboard control;
- `cyclonedds`: DDS implementation source used by the Unitree SDK;
- `unitree_sdk2_python`: optional Python simulator/inspection bindings.

The C++ deployment build can use the local SDK checkout. The pinned platform
lock remains available for Jetson bootstrap builds and reproducible binary
runtime downloads.
