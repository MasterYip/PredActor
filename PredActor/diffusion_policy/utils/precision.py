"""Typed mixed-precision contracts shared by training and inference."""

from __future__ import annotations

from contextlib import nullcontext

import torch


SUPPORTED_PRECISIONS = ("fp32", "fp16")


def normalize_precision(value: str | None) -> str:
    precision = "fp32" if value is None else str(value).lower()
    if precision not in SUPPORTED_PRECISIONS:
        raise ValueError(
            f"precision must be one of {SUPPORTED_PRECISIONS}, got {value!r}"
        )
    return precision


def validate_precision_device(precision: str, device: torch.device | str) -> torch.device:
    precision = normalize_precision(precision)
    resolved = torch.device(device)
    if precision == "fp16":
        if resolved.type != "cuda":
            raise ValueError("fp16 requires a CUDA device; CPU fp16 is unsupported")
        if not torch.cuda.is_available():
            raise RuntimeError("fp16 requested but CUDA is unavailable")
    return resolved


def autocast_context(precision: str, device: torch.device | str):
    resolved = validate_precision_device(precision, device)
    if normalize_precision(precision) == "fp16":
        return torch.autocast(device_type="cuda", dtype=torch.float16)
    return nullcontext()


def make_grad_scaler(precision: str, device: torch.device | str):
    validate_precision_device(precision, device)
    return torch.cuda.amp.GradScaler(enabled=normalize_precision(precision) == "fp16")


def require_finite_loss(loss: torch.Tensor, label: str) -> None:
    if not bool(torch.isfinite(loss.detach()).all()):
        raise FloatingPointError(f"non-finite {label} under mixed-precision contract")


def require_finite_gradients(module: torch.nn.Module, label: str) -> None:
    bad = [name for name, parameter in module.named_parameters()
           if parameter.grad is not None and not bool(torch.isfinite(parameter.grad).all())]
    if bad:
        preview = ", ".join(bad[:5])
        raise FloatingPointError(f"non-finite {label} gradients: {preview}")
