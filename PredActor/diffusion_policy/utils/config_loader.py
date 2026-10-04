from __future__ import annotations

from pathlib import Path
from typing import Set

from omegaconf import DictConfig, ListConfig, OmegaConf

# Keys that only appear in wandb-serialised configs and should be stripped.
_WANDB_ONLY_KEYS = {"_wandb", "exp_name", "output_dir"}

# Root of the config_files/ tree.  Defaults entries are resolved relative to a
# config file's own directory first, but experiment configs copied into
# ``config_files/experiments/<group>/run_*/`` still reference top-level
# defaults (``defaults/data_collection`` etc.).  When the local resolution
# misses, we fall back to this root so those configs stay loadable.
_CONFIG_FILES_ROOT = Path(__file__).resolve().parent.parent / "config_files"


def is_wandb_config(cfg: DictConfig) -> bool:
    """Return True if *cfg* is in wandb's value-wrapped format.

    Wandb serialises every top-level config key as ``{value: <actual>, ...}``.
    We detect this by checking that all non-metadata top-level values are
    DictConfigs that contain a ``value`` key.
    """
    check_keys = [k for k in cfg if k not in _WANDB_ONLY_KEYS]
    if not check_keys:
        return False
    return all(
        isinstance(cfg[k], DictConfig) and "value" in cfg[k]
        for k in check_keys
    )


def unwrap_wandb_config(raw: DictConfig) -> DictConfig:
    """Convert a wandb config.yaml (value-wrapped) into a flat DictConfig.

    Each top-level entry ``{key: {value: <v>, ...}}`` becomes ``{key: <v>}``.
    Wandb-only metadata keys are dropped.
    """
    flat: dict = {}
    for key, entry in raw.items():
        if key in _WANDB_ONLY_KEYS:
            continue
        if isinstance(entry, DictConfig) and "value" in entry:
            flat[key] = entry["value"]
        else:
            flat[key] = entry
    return OmegaConf.create(flat)


def _resolve_default_entry(entry, current_file: Path) -> Path:
    """Resolve one defaults entry into a concrete YAML path."""
    if isinstance(entry, DictConfig):
        items = list(entry.items())
        if len(items) != 1:
            raise ValueError(f"Invalid defaults entry in {current_file}: {entry}")
        group, name = items[0]
        if name is None:
            raise ValueError(f"Unsupported null defaults entry in {current_file}: {entry}")
        rel = Path(str(group)) / str(name)
    else:
        rel = Path(str(entry))

    # Skip hydra package directives and _self_.
    if str(rel) in {"_self_", "hydra"}:
        return rel

    if rel.suffix == "":
        rel = rel.with_suffix(".yaml")

    if rel.is_absolute():
        return rel

    # Primary resolution: relative to the config file's own directory.  This is
    # correct for configs living directly in config_files/ and for any run-local
    # defaults a config may carry alongside itself.
    resolved = (current_file.parent / rel).resolve()
    if resolved.exists():
        return resolved

    # Fallback: relative to the config_files/ root.  Experiment configs copied
    # into config_files/experiments/<group>/run_*/ reference top-level defaults
    # (e.g. ``defaults/data_collection``) that only exist under config_files/.
    fallback = (_CONFIG_FILES_ROOT / rel).resolve()
    if fallback.exists():
        return fallback

    # Neither found — return the primary candidate so the eventual
    # OmegaConf.load raises a clear FileNotFoundError pointing at it.
    return resolved


def _load_config_with_defaults(path: Path, stack: Set[Path]) -> DictConfig:
    path = path.resolve()
    if path in stack:
        cycle = " -> ".join([str(p) for p in [*stack, path]])
        raise RuntimeError(f"Config defaults cycle detected: {cycle}")

    stack.add(path)
    cfg = OmegaConf.load(path)

    defaults = cfg.get("defaults", None)
    if defaults is None:
        stack.remove(path)
        return cfg

    # Remove defaults key from the current config before merging.
    del cfg["defaults"]

    merged = OmegaConf.create({})
    merged_self = False

    if not isinstance(defaults, (list, ListConfig)):
        raise ValueError(f"'defaults' must be a list in {path}")

    for entry in defaults:
        resolved = _resolve_default_entry(entry, path)
        if str(resolved) == "_self_":
            merged = OmegaConf.merge(merged, cfg)
            merged_self = True
            continue

        child_cfg = _load_config_with_defaults(resolved, stack)
        merged = OmegaConf.merge(merged, child_cfg)

    if not merged_self:
        merged = OmegaConf.merge(merged, cfg)

    stack.remove(path)
    return merged


def load_config(config_path: str | Path) -> DictConfig:
    """Load a config file with lightweight Hydra-like defaults composition support."""
    return _load_config_with_defaults(Path(config_path), set())
