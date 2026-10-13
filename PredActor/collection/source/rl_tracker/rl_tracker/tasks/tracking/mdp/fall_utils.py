"""Pure tensor helpers for DAgger physical-fall detection."""

import math

import torch


def validate_minimum_height(minimum_height: float) -> float:
    if (
        not isinstance(minimum_height, (int, float))
        or not math.isfinite(float(minimum_height))
        or not 0.0 < float(minimum_height) <= 2.0
    ):
        raise ValueError(
            "minimum_height must be finite and in (0, 2] world meters, "
            f"got {minimum_height!r}"
        )
    return float(minimum_height)


def root_height_below_mask(
    root_pos_w: torch.Tensor, minimum_height: float
) -> torch.Tensor:
    """Return a per-environment mask from articulation root world positions."""
    threshold = validate_minimum_height(minimum_height)
    if root_pos_w.ndim != 2 or root_pos_w.shape[1] != 3:
        raise ValueError(
            f"root_pos_w must have shape (num_envs, 3), got {tuple(root_pos_w.shape)}"
        )
    return root_pos_w[:, 2] < threshold
