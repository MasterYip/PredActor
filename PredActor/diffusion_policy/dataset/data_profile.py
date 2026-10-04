"""Lightweight dataset-profile schema shared by training and deployment.

This module deliberately has no replay-buffer or zarr dependency. Runtime
features such as whole-body guidance only need the ordered term contract and
must remain usable in a minimal deployment environment.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from numbers import Real
from pathlib import Path
from typing import ClassVar, Dict, FrozenSet, List

import yaml

from diffusion_policy.trainer.cond_dropout import TermDropoutEntry


@dataclass
class EmphConfig:
    type: str = "same"
    weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class TermMaskEntry:
    enabled: bool = True
    initial_prob: float = 0.0
    final_prob: float = 0.5
    warmup_steps: int = 100000


@dataclass
class TermGroupConfig:
    terms: List[str] = field(default_factory=list)
    state_normalize: bool = False
    state_emph: EmphConfig = field(default_factory=EmphConfig)
    mask_config_train: Dict[str, TermMaskEntry] = field(default_factory=dict)
    mask_config_infer: Dict[str, bool] = field(default_factory=dict)
    dropout_config_train: Dict[str, TermDropoutEntry] = field(default_factory=dict)


@dataclass
class DataProfile:
    """Structured representation of a dataset profile YAML."""

    name: str = "G1"
    observation: TermGroupConfig = field(default_factory=TermGroupConfig)
    task_condition: TermGroupConfig = field(default_factory=TermGroupConfig)
    action_term: str = "act"

    _DROPOUT_OVERRIDE_FIELDS: ClassVar[FrozenSet[str]] = frozenset(
        {
            "enabled",
            "initial_prob",
            "final_prob",
            "warmup_steps",
            "dropout_type",
            "noise_std",
        }
    )
    _DROPOUT_TYPES: ClassVar[FrozenSet[str]] = frozenset(
        {"null", "noise", "dimensions", "perturb"}
    )

    def with_dropout_config_train_overrides(self, overrides) -> "DataProfile":
        """Return a copy with validated per-term training-dropout overrides.

        Overrides may only refine dropout entries already declared by the
        profile.  This makes command-line ablations reproducible while failing
        closed on misspelled terms, fields, or invalid values.
        """
        if overrides is None:
            return self
        if not isinstance(overrides, Mapping):
            raise TypeError("dropout_config_train_overrides must be a mapping")

        profile = copy.deepcopy(self)
        configured = profile.task_condition.dropout_config_train
        for term_name, raw_fields in overrides.items():
            if term_name not in configured:
                raise ValueError(
                    f"dropout override term {term_name!r} is not declared in "
                    f"profile {profile.name!r}; configured terms: {sorted(configured)}"
                )
            if not isinstance(raw_fields, Mapping):
                raise TypeError(f"dropout override for {term_name!r} must be a mapping")

            unknown = set(raw_fields) - self._DROPOUT_OVERRIDE_FIELDS
            if unknown:
                raise ValueError(
                    f"unknown dropout override field(s) for {term_name!r}: "
                    f"{sorted(unknown)}"
                )

            entry = configured[term_name]
            for field_name, value in raw_fields.items():
                if field_name == "enabled":
                    if type(value) is not bool:
                        raise TypeError(f"{term_name}.enabled must be a bool")
                elif field_name == "warmup_steps":
                    if type(value) is not int or value < 0:
                        raise ValueError(
                            f"{term_name}.warmup_steps must be a non-negative int"
                        )
                elif field_name in {"initial_prob", "final_prob", "noise_std"}:
                    if isinstance(value, bool) or not isinstance(value, Real):
                        raise TypeError(f"{term_name}.{field_name} must be numeric")
                    value = float(value)
                    if not math.isfinite(value):
                        raise ValueError(f"{term_name}.{field_name} must be finite")
                    if field_name == "noise_std" and value < 0.0:
                        raise ValueError(f"{term_name}.noise_std must be non-negative")
                    if field_name != "noise_std" and not 0.0 <= value <= 1.0:
                        raise ValueError(f"{term_name}.{field_name} must be in [0, 1]")
                elif field_name == "dropout_type":
                    if not isinstance(value, str) or value not in self._DROPOUT_TYPES:
                        raise ValueError(
                            f"{term_name}.dropout_type must be one of "
                            f"{sorted(self._DROPOUT_TYPES)}"
                        )
                setattr(entry, field_name, value)

        return profile

    @classmethod
    def from_dict(cls, d: dict) -> "DataProfile":
        d = d.get("data_profile", d)

        def parse_emph(e: dict) -> EmphConfig:
            return EmphConfig(type=e.get("type", "same"), weights=e.get("weights", {}))

        def parse_mask_entry(m: dict) -> TermMaskEntry:
            return TermMaskEntry(
                enabled=bool(m.get("enabled", True)),
                initial_prob=float(m.get("initial_prob", 0.0)),
                final_prob=float(m.get("final_prob", 0.5)),
                warmup_steps=int(m.get("warmup_steps", 100000)),
            )

        def parse_dropout_entry(m: dict) -> TermDropoutEntry:
            raw_type = m.get("dropout_type", "null")
            if raw_type is None:
                raw_type = "null"
            return TermDropoutEntry(
                enabled=bool(m.get("enabled", True)),
                initial_prob=float(m.get("initial_prob", 0.0)),
                final_prob=float(m.get("final_prob", 0.3)),
                warmup_steps=int(m.get("warmup_steps", 100000)),
                dropout_type=str(raw_type),
                noise_std=float(m.get("noise_std", 0.1)),
            )

        def parse_group(g: dict) -> TermGroupConfig:
            mask_train = {
                key: parse_mask_entry(value)
                for key, value in (g.get("mask_config_train", {}) or {}).items()
            }
            mask_infer = {
                key: bool(value)
                for key, value in (g.get("mask_config_infer", {}) or {}).items()
            }
            dropout_train = {
                key: parse_dropout_entry(value)
                for key, value in (g.get("dropout_config_train", {}) or {}).items()
            }
            return TermGroupConfig(
                terms=list(g.get("terms", [])),
                state_normalize=bool(g.get("state_normalize", False)),
                state_emph=parse_emph(g.get("state_emph", {})),
                mask_config_train=mask_train,
                mask_config_infer=mask_infer,
                dropout_config_train=dropout_train,
            )

        return cls(
            name=d.get("name", "G1"),
            observation=parse_group(d.get("observation", {})),
            task_condition=parse_group(d.get("task_condition", {})),
            action_term=d.get("action_term", "act"),
        )

    @classmethod
    def from_yaml(cls, path_or_dict) -> "DataProfile":
        if isinstance(path_or_dict, dict):
            return cls.from_dict(path_or_dict)
        try:
            from omegaconf import OmegaConf

            if hasattr(path_or_dict, "_metadata"):
                return cls.from_dict(OmegaConf.to_container(path_or_dict, resolve=True))
        except ImportError:
            pass
        path = Path(path_or_dict)
        if not path.suffix:
            path = Path(__file__).parent.parent / "config_files" / "defaults" / "dataset" / f"{path_or_dict}.yaml"
        with open(path, encoding="utf-8") as stream:
            return cls.from_dict(yaml.safe_load(stream))
