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
