# Evaluation

From the public repository root, install the locked environment and download
the published checkpoints:

```bash
uv sync --locked
uv run --locked python scripts/hf_download.py --filter checkpoints
uv run --locked predactor-eval
```

The last command opens the browser viewer at `http://127.0.0.1:8765/`. See the
repository README for evaluator options and the artifact repository layout.

## Evaluate your trained model

Use the run directory printed by training in place of `<run-directory>`:

```bash
run_dir="outputs/<run-directory>"
uv run --locked predactor-eval \
  --checkpoint "$run_dir/checkpoints/latest.ckpt" \
  --config "$run_dir/resolved_config.yaml" \
  --output_dir "$run_dir/eval" \
  --web-ui
```

The saved config selects the matching policy and text encoder. Add
`--web-perturb` for mouse perturbations, `--web-port 8766` to use another port,
or `--headless --web-no-browser` when launching over SSH.
