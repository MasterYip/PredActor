"""Validated additive CLIP proposition terms and deterministic composition."""

from __future__ import annotations

import math
from typing import Any, Callable, Optional

import torch


MAX_INTERPOLATION_TERMS = 16
MAX_INTERPOLATION_TEXT_LENGTH = 120


def interpolation_weight_bounds(text_a: Optional[str], text_b: Optional[str]) -> tuple[float, float]:
    """Return signed direction bounds, or one-sided bounds for a zero anchor."""
    return (0.0, 1.0) if text_a is None or text_b is None else (-1.0, 1.0)


def default_weights(text_pairs: list[tuple[Optional[str], Optional[str]]]) -> list[float]:
    """Select the leading zero-to-text base; leave every signed direction neutral."""
    return [
        1.0 if index == 0 and text_a is None and text_b is not None else 0.0
        for index, (text_a, text_b) in enumerate(text_pairs)
    ]


def validate_interpolation_terms(
    terms: Any,
    *,
    max_terms: int = MAX_INTERPOLATION_TERMS,
    allow_range_metadata: bool = False,
) -> list[dict[str, Any]]:
    """Return a JSON-safe, stripped copy of an interpolation term list."""
    if not isinstance(terms, (list, tuple)) or not 1 <= len(terms) <= max_terms:
        raise ValueError(f"terms must contain 1-{max_terms} entries")

    clean = []
    for index, term in enumerate(terms):
        if not isinstance(term, dict):
            raise ValueError(f"term {index} must be an object")
        allowed = {"text_a", "text_b", "weight"}
        if allow_range_metadata:
            allowed.update({"weight_min", "weight_max", "weight_default"})
        unexpected = set(term) - allowed
        if unexpected:
            raise ValueError(f"term {index} has unexpected fields")
        endpoints = []
        for key in ("text_a", "text_b"):
            value = term.get(key)
            if value is None:
                endpoints.append(None)
                continue
            if not isinstance(value, str):
                raise ValueError(f"term {index} {key} must be text or null")
            value = value.strip()
            if not value or len(value) > MAX_INTERPOLATION_TEXT_LENGTH:
                raise ValueError(
                    f"term {index} {key} must contain 1-{MAX_INTERPOLATION_TEXT_LENGTH} characters or be null")
            endpoints.append(value)
        if endpoints[0] is None and endpoints[1] is None:
            raise ValueError(f"term {index} cannot have two null endpoints")

        weight = term.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError(f"term {index} weight must be numeric")
        weight = float(weight)
        lower, upper = interpolation_weight_bounds(endpoints[0], endpoints[1])
        if not math.isfinite(weight) or not lower <= weight <= upper:
            raise ValueError(f"term {index} weight must be finite and within [{lower:g}, {upper:g}]")
        if allow_range_metadata and ("weight_min" in term or "weight_max" in term):
            supplied_fields = set(term) & {"weight_min", "weight_max"}
            if supplied_fields != {"weight_min", "weight_max"}:
                raise ValueError(f"term {index} must provide both weight bounds")
            supplied = (term["weight_min"], term["weight_max"])
            if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in supplied):
                raise ValueError(f"term {index} weight bounds must be numeric")
            if (float(supplied[0]), float(supplied[1])) != (lower, upper):
                raise ValueError(f"term {index} weight bounds do not match its endpoints")
        if allow_range_metadata and "weight_default" in term:
            supplied_default = term["weight_default"]
            if isinstance(supplied_default, bool) or not isinstance(supplied_default, (int, float)):
                raise ValueError(f"term {index} weight default must be numeric")
            supplied_default = float(supplied_default)
            if not math.isfinite(supplied_default) or not lower <= supplied_default <= upper:
                raise ValueError(f"term {index} weight default must be finite and within [{lower:g}, {upper:g}]")
        clean.append({"text_a": endpoints[0], "text_b": endpoints[1], "weight": weight})
    return clean


def describe_interpolation_terms(
    terms: Any,
    *,
    weight_defaults: Optional[list[float]] = None,
) -> list[dict[str, Any]]:
    """Return validated terms with authoritative bounds and reset defaults."""
    clean = validate_interpolation_terms(terms, allow_range_metadata=True)
    if weight_defaults is None:
        metadata = [term.get("weight_default") for term in terms]
        if any(value is not None for value in metadata):
            if any(value is None for value in metadata):
                raise ValueError("terms must provide every weight default or none")
            weight_defaults = metadata
        else:
            weight_defaults = default_weights([(term["text_a"], term["text_b"]) for term in clean])
    if len(weight_defaults) != len(clean):
        raise ValueError(f"Expected {len(clean)} weight defaults, got {len(weight_defaults)}")

    described = []
    for index, (term, weight_default) in enumerate(zip(clean, weight_defaults)):
        lower, upper = interpolation_weight_bounds(term["text_a"], term["text_b"])
        if isinstance(weight_default, bool) or not isinstance(weight_default, (int, float)):
            raise ValueError(f"term {index} weight default must be numeric")
        weight_default = float(weight_default)
        if not math.isfinite(weight_default) or not lower <= weight_default <= upper:
            raise ValueError(f"term {index} weight default must be finite and within [{lower:g}, {upper:g}]")
        described.append({
            **term,
            "weight_min": lower,
            "weight_max": upper,
            "weight_default": weight_default,
        })
    return described


def matched_weight_defaults(
    terms: list[dict[str, Any]],
    reference_terms: list[dict[str, Any]],
) -> list[float]:
    """Return frozen defaults only for rows whose indexed endpoints still match."""
    defaults = []
    for index, term in enumerate(terms):
        reference = reference_terms[index] if index < len(reference_terms) else None
        matches = reference is not None and all(
            term[key] == reference[key] for key in ("text_a", "text_b"))
        defaults.append(float(reference["weight"]) if matches else 0.0)
    return defaults


def terms_from_pairs(
    text_pairs: list[tuple[Optional[str], Optional[str]]],
    weights: Optional[list[float]] = None,
) -> list[dict[str, Any]]:
    """Convert configured endpoint pairs and optional weights to term objects."""
    values = default_weights(text_pairs) if weights is None else list(weights)
    if len(values) != len(text_pairs):
        raise ValueError(f"Expected {len(text_pairs)} weights, got {len(values)}")
    return validate_interpolation_terms([
        {"text_a": text_a, "text_b": text_b, "weight": weight}
        for (text_a, text_b), weight in zip(text_pairs, values)
    ])


def encode_and_compose(
    terms: list[dict[str, Any]],
    encode: Callable[[str], torch.Tensor],
    *,
    cond_dim: int,
    device: str,
    normalize: bool,
) -> tuple[list[tuple[Optional[torch.Tensor], Optional[torch.Tensor]]], torch.Tensor]:
    """Encode endpoints and compute ``sum(w * (E(b) - E(a)))`` once."""
    pair_embeddings = []
    with torch.no_grad():
        final = torch.zeros(1, cond_dim, device=device)
        for term in terms:
            text_a, text_b = term["text_a"], term["text_b"]
            emb_a = encode(text_a) if text_a is not None else None
            emb_b = encode(text_b) if text_b is not None else None
            pair_embeddings.append((emb_a, emb_b))
            if emb_a is None:
                direction = emb_b
            elif emb_b is None:
                direction = -emb_a
            else:
                direction = emb_b - emb_a
            final = final + direction * term["weight"]
        if normalize:
            norm = final.norm(dim=-1, keepdim=True)
            if bool((norm > 0).item()):
                final = final / norm
    return pair_embeddings, final
