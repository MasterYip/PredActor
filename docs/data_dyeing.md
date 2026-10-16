# MotionCLIP data dyeing

Data dyeing attaches one 512-dimensional text-aligned MotionCLIP latent to each
collected frame. The public runtime loads only the encoder and CLIP text model
needed for this step.

Place the released MotionCLIP checkpoint at:

```text
Artifacts/checkpoints/motionclip/g1-model-xyz-clip/checkpoint_0100.pth.tar
```

After collection, run from the public repository root:

```bash
uv run python PredActor/collection/scripts/data_dyeing/data_dyeing.py
```

The default configuration reads:

```text
Artifacts/dataset/g1_152fk_raw/motion.zarr
Artifacts/motions/g1_152fk/*/motion.npz
```

and writes:

```text
Artifacts/dataset/g1_152fk/motion_dyed_text_t0.01.zarr
```

Paths can be overridden with Hydra values such as
`input.zarr_path=/path/to/motion.zarr` and
`output.zarr_path=/path/to/dyed.zarr`. The released profile uses the original
motions for encoding, 60-frame windows, 30 Hz target sampling, `xyz` poses,
and text-alignment temperature `0.01`.
