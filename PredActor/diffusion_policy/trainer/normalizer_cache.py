"""Helpers for saving and loading LinearNormalizer statistics to/from YAML.

The on-disk format is identical to the one produced by export_policy.py:

    normalization:
      obs:
        mode: scale_offset
        scale: [...]
        offset: [...]
      action:
        mode: scale_offset
        ...

Usage
-----
    from diffusion_policy.trainer.normalizer_cache import (
        try_load_normalizer_cache,
        save_normalizer_cache,
    )

    cache_path = zarr_path.parent / "normalizer_stats.yaml"
    normalizer = try_load_normalizer_cache(cache_path)
    if normalizer is None:
        normalizer = <fit as normal>
        save_normalizer_cache(normalizer, cache_path)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import yaml

from diffusion_policy.trainer.normalizer import LinearNormalizer


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _normalizer_to_stats_dict(normalizer: LinearNormalizer) -> dict:
    stats: dict = {}
    for key in normalizer.params_dict:
        params = normalizer.params_dict[key]
        try:
            scale  = params["scale"].detach().cpu().tolist()
            offset = params["offset"].detach().cpu().tolist()
            stats[key] = {"mode": "scale_offset", "scale": scale, "offset": offset}
        except Exception:
            pass
    return stats


def _normalizer_from_stats_dict(stats: dict) -> LinearNormalizer:
    normalizer = LinearNormalizer()
    for key, entry in stats.items():
        scale  = torch.tensor(entry["scale"],  dtype=torch.float32)
        offset = torch.tensor(entry["offset"], dtype=torch.float32)
        normalizer.params_dict[key] = nn.ParameterDict({
            "scale":  nn.Parameter(scale,  requires_grad=False),
            "offset": nn.Parameter(offset, requires_grad=False),
            "input_stats": nn.ParameterDict({
                "min": nn.Parameter(offset.clone(), requires_grad=False),
                "max": nn.Parameter(offset.clone(), requires_grad=False),
            }),
        })
    return normalizer


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def try_load_normalizer_cache(cache_path: Path) -> Optional[LinearNormalizer]:
    """Return a LinearNormalizer loaded from *cache_path* if it exists, else None."""
    if not cache_path.exists():
        return None
    try:
        with open(cache_path) as f:
            doc = yaml.safe_load(f)
        stats = doc.get("normalization", doc)
        normalizer = _normalizer_from_stats_dict(stats)
        print(f"[normalizer_cache] Loaded from {cache_path}")
        return normalizer
    except Exception as e:
        print(f"[normalizer_cache] Warning: could not load cache ({e}), re-fitting.")
        return None


def save_normalizer_cache(normalizer: LinearNormalizer, cache_path: Path) -> None:
    """Serialize *normalizer* to *cache_path* as a YAML file."""
    try:
        stats = _normalizer_to_stats_dict(normalizer)
        with open(cache_path, "w") as f:
            yaml.dump({"normalization": stats}, f, default_flow_style=None)
        print(f"[normalizer_cache] Saved to {cache_path}")
    except Exception as e:
        print(f"[normalizer_cache] Warning: could not save cache: {e}")
