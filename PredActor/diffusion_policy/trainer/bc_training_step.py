"""Shared offline-BC optimizer transaction used by BC-aligned DAgger."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

import numpy as np
import torch

from diffusion_policy.utils.precision import (
    autocast_context,
    require_finite_gradients,
    require_finite_loss,
)


_NON_LOSS_KEYS = {"log", "grad_analysis", "loss_components"}


def _update_digest(digest, value: Any) -> None:
    if torch.is_tensor(value):
        tensor = value.detach().cpu().contiguous()
        digest.update(b"tensor")
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(str(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
        return
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        digest.update(b"ndarray")
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.tobytes())
        return
    if isinstance(value, np.generic):
        _update_digest(digest, value.item())
        return
    if isinstance(value, bytes):
        digest.update(b"bytes")
        digest.update(value)
        return
    if isinstance(value, Mapping):
        digest.update(b"mapping")
        for key in sorted(value, key=str):
            digest.update(str(key).encode("utf-8"))
            _update_digest(digest, value[key])
        return
    if isinstance(value, (list, tuple)):
        digest.update(type(value).__name__.encode("ascii"))
        for item in value:
            _update_digest(digest, item)
        return
    digest.update(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))


def nested_state_sha256(value: Any) -> str:
    digest = hashlib.sha256()
    _update_digest(digest, value)
    return digest.hexdigest()


def trainable_parameter_sha256(agent) -> str:
    return nested_state_sha256({
        name: parameter
        for name, parameter in agent.named_parameters()
        if parameter.requires_grad
    })


def gradient_sha256(agent) -> str:
    return nested_state_sha256({
        name: parameter.grad
        for name, parameter in agent.named_parameters()
        if parameter.requires_grad and parameter.grad is not None
    })


def gradient_metrics(agent) -> dict[str, Any]:
    squared_norm = 0.0
    tensor_count = 0
    for parameter in agent.parameters():
        if parameter.grad is None:
            continue
        gradient = parameter.grad.detach().float()
        squared_norm += float(torch.sum(gradient.square()).cpu())
        tensor_count += 1
    return {
        "gradient_norm": squared_norm**0.5,
        "gradient_tensor_count": tensor_count,
    }


def _component_record(value: torch.Tensor) -> dict[str, Any]:
    tensor = value.detach().cpu().contiguous()
    result = {
        "shape": list(tensor.shape),
        "dtype": str(tensor.dtype),
        "sha256": nested_state_sha256(tensor),
        "finite": bool(torch.isfinite(tensor).all()),
    }
    if tensor.numel() <= 256:
        result["values"] = tensor.reshape(-1).tolist()
    if tensor.numel():
        result["minimum"] = float(tensor.min())
        result["maximum"] = float(tensor.max())
    return result


def run_bc_training_step(
    *,
    agent,
    optimizers,
    schedulers,
    batch,
    local_epoch_idx: int,
    global_step: int,
    gradient_accumulate_every: int,
    precision: str,
    device: torch.device,
    grad_scaler,
    capture_audit: bool = False,
) -> dict[str, Any]:
    """Run the exact OfflineTrainer loss/backward/step/scheduler transaction."""
    accumulation = int(gradient_accumulate_every)
    if accumulation <= 0:
        raise ValueError("gradient_accumulate_every must be positive")

    audit = None
    if capture_audit:
        normalized = agent.normalizer.normalize(batch)
        audit = {
            "raw_batch_sha256": nested_state_sha256(batch),
            "normalized_batch_sha256": nested_state_sha256(normalized),
            "normalizer_sha256": nested_state_sha256(
                agent.normalizer.state_dict()
            ),
            "parameters_before_sha256": trainable_parameter_sha256(agent),
            "optimizer_before_sha256": nested_state_sha256({
                key: optimizer.state_dict()
                for key, optimizer in optimizers.items()
            }),
            "scheduler_before_sha256": nested_state_sha256({
                key: scheduler.state_dict()
                for key, scheduler in schedulers.items()
            }),
            "lr_before": {
                key: [float(value) for value in scheduler.get_last_lr()]
                for key, scheduler in schedulers.items()
            },
            "rng_before_sha256": nested_state_sha256({
                "torch_cpu": torch.get_rng_state(),
                "torch_cuda": (
                    torch.cuda.get_rng_state_all()
                    if device.type == "cuda" else []
                ),
            }),
        }

    compute_kwargs = (
        {"return_loss_components": True} if capture_audit else {}
    )
    with autocast_context(precision, device):
        loss_dicts = list(
            agent.compute_loss(batch, local_epoch_idx, **compute_kwargs)
        )

    should_step = int(global_step) % accumulation == 0
    step_log = {}
    raw_losses = {}
    component_records = {}
    prediction_records = {}
    gradient_hashes = {}
    last_raw_loss = None

    for loss_dict in loss_dicts:
        if capture_audit:
            component_records.update({
                key: _component_record(value)
                for key, value in (loss_dict.get("loss_components") or {}).items()
            })
            prediction_records.update({
                key: _component_record(value)
                for key, value in (loss_dict.get("grad_analysis") or {}).items()
            })
        for key, raw_loss in loss_dict.items():
            if key == "log":
                for log_key, value in raw_loss.items():
                    step_log[f"log/{log_key}_loss"] = float(value.item())
                continue
            if key in _NON_LOSS_KEYS:
                continue

            loss = raw_loss / accumulation
            require_finite_loss(loss, key)
            grad_scaler.scale(loss).backward()
            raw_loss_cpu = float(raw_loss.item())
            raw_losses[key] = raw_loss_cpu
            last_raw_loss = raw_loss_cpu

            if should_step:
                grad_scaler.unscale_(optimizers[key])
                require_finite_gradients(agent, key)
                if capture_audit:
                    gradient_hashes[key] = gradient_sha256(agent)
                    audit.setdefault("gradient_metrics", {})[key] = (
                        gradient_metrics(agent)
                    )
                grad_scaler.step(optimizers[key])
                optimizers[key].zero_grad()
                schedulers[key].step()

            step_log[f"{key}_loss"] = math.sqrt(raw_loss_cpu)
            step_log[f"{key}_lr"] = float(schedulers[key].get_last_lr()[0])

    if should_step:
        grad_scaler.update()
    if last_raw_loss is None:
        raise RuntimeError("agent.compute_loss produced no optimizer loss")

    if capture_audit:
        audit.update({
            "losses": raw_losses,
            "loss_components": component_records,
            "predictions": prediction_records,
            "gradient_sha256": gradient_hashes,
            "parameters_after_sha256": trainable_parameter_sha256(agent),
            "optimizer_after_sha256": nested_state_sha256({
                key: optimizer.state_dict()
                for key, optimizer in optimizers.items()
            }),
            "scheduler_after_sha256": nested_state_sha256({
                key: scheduler.state_dict()
                for key, scheduler in schedulers.items()
            }),
            "lr_after": {
                key: [float(value) for value in scheduler.get_last_lr()]
                for key, scheduler in schedulers.items()
            },
            "rng_after_sha256": nested_state_sha256({
                "torch_cpu": torch.get_rng_state(),
                "torch_cuda": (
                    torch.cuda.get_rng_state_all()
                    if device.type == "cuda" else []
                ),
            }),
            "grad_scaler_sha256": nested_state_sha256(
                grad_scaler.state_dict()
            ),
            "should_step": should_step,
        })

    return {
        "step_log": step_log,
        "raw_losses": raw_losses,
        "last_raw_loss": last_raw_loss,
        "audit": audit,
    }
