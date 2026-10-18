import contextlib
import hashlib
import json
import math
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as functional


TARGET = "jetson-jp5-torch21"
TARGET_TORCH = "2.1.0a0+41361538.nv23.06"
FORBIDDEN_OPERATORS = {"aten::scaled_dot_product_attention"}


def parity_tolerances(precision):
    """Return the numerical export gate recorded in compatibility metadata."""
    if precision == "fp32":
        return 3e-6, 3e-6
    if precision == "fp16":
        return 3e-3, 3e-3
    raise ValueError(f"unsupported compatibility precision: {precision!r}")


class Torch21MultiheadAttention(nn.Module):
    """Inference-equivalent MHA expressed with Torch 2.1 primitive operators."""

    PROJECTION_STRATEGIES = {"separate", "packed_self", "packed_cross"}

    def __init__(self, source, projection_strategy="separate"):
        super().__init__()
        if not source.batch_first or not source._qkv_same_embed_dim:
            raise ValueError("Torch 2.1 lowering requires batch_first packed-QKV MHA")
        if source.bias_k is not None or source.bias_v is not None or source.add_zero_attn:
            raise ValueError("Torch 2.1 lowering does not support bias_k/bias_v/add_zero_attn")
        if projection_strategy not in self.PROJECTION_STRATEGIES:
            raise ValueError(f"unsupported attention projection strategy: {projection_strategy!r}")
        self.embed_dim = source.embed_dim
        self.num_heads = source.num_heads
        self.head_dim = source.head_dim
        self.batch_first = True
        self.dropout = source.dropout
        self.projection_strategy = projection_strategy
        self.in_proj_weight = source.in_proj_weight
        self.in_proj_bias = source.in_proj_bias
        self.out_proj = source.out_proj

    def _project(self, value, start, end):
        weight = self.in_proj_weight[start:end]
        bias = self.in_proj_bias[start:end] if self.in_proj_bias is not None else None
        return functional.linear(value, weight, bias)

    def forward(self, query, key, value, key_padding_mask=None, need_weights=True,
                attn_mask=None, average_attn_weights=True, is_causal=False):
        batch, target_len, _ = query.shape
        source_len = key.shape[1]
        if self.projection_strategy == "packed_self":
            if not torch.jit.is_tracing() and (query is not key or query is not value):
                raise ValueError("packed_self requires identical query/key/value tensors")
            q, k, v = functional.linear(
                query, self.in_proj_weight, self.in_proj_bias).chunk(3, dim=-1)
        elif self.projection_strategy == "packed_cross":
            if not torch.jit.is_tracing() and key is not value:
                raise ValueError("packed_cross requires identical key/value tensors")
            q = self._project(query, 0, self.embed_dim)
            kv = functional.linear(
                key,
                self.in_proj_weight[self.embed_dim:3 * self.embed_dim],
                (self.in_proj_bias[self.embed_dim:3 * self.embed_dim]
                 if self.in_proj_bias is not None else None),
            )
            k, v = kv.chunk(2, dim=-1)
        else:
            q = self._project(query, 0, self.embed_dim)
            k = self._project(key, self.embed_dim, 2 * self.embed_dim)
            v = self._project(value, 2 * self.embed_dim, 3 * self.embed_dim)
        q = q.reshape(batch, target_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.reshape(batch, source_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.reshape(batch, source_len, self.num_heads, self.head_dim).transpose(1, 2)

        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        if is_causal:
            causal = torch.ones(target_len, source_len, dtype=torch.bool,
                                device=scores.device).triu(1)
            scores = scores.masked_fill(causal, float("-inf"))
        if attn_mask is not None:
            mask = attn_mask
            if mask.dim() == 2:
                mask = mask.unsqueeze(0).unsqueeze(0)
            elif mask.dim() == 3:
                mask = mask.reshape(batch, self.num_heads, target_len, source_len)
            if mask.dtype == torch.bool:
                scores = scores.masked_fill(mask, float("-inf"))
            else:
                scores = scores + mask.to(dtype=scores.dtype)
        if key_padding_mask is not None:
            padding = key_padding_mask[:, None, None, :]
            if padding.dtype == torch.bool:
                scores = scores.masked_fill(padding, float("-inf"))
            else:
                scores = scores + padding.to(dtype=scores.dtype)

        probabilities = torch.softmax(scores, dim=-1)
        probabilities = torch.dropout(probabilities, self.dropout, self.training)
        output = torch.matmul(probabilities, v)
        output = output.transpose(1, 2).reshape(batch, target_len, self.embed_dim)
        output = self.out_proj(output)
        if not need_weights:
            return output, None
        weights = probabilities.mean(dim=1) if average_attn_weights else probabilities
        return output, weights


class Torch21ConditionEmbeddingBackbone(nn.Module):
    """Stateless exact-weight wrapper that exposes per-call condition reuse.

    C++ builds the encoded condition once at the policy boundary, then supplies
    it to all five DDIM backbone evaluations. Unlike the projected-K/V
    cache, this keeps the native decoder graph and has no cross-call identity or
    tensor-version bookkeeping.
    """

    def __init__(self, source):
        super().__init__()
        self.source = source

    def forward(self, x_input, y_input, x_timesteps, y_timesteps, cond):
        return self.source(x_input, y_input, x_timesteps, y_timesteps, cond)

    def build_condition_embeddings(self, cond):
        return self.source.encode_condition(cond)

    def forward_encoded_condition(self, x_input, y_input, x_timesteps,
                                  y_timesteps, condition_embeddings):
        return self.source(x_input, y_input, x_timesteps, y_timesteps,
                           None, condition_embeddings)


@contextlib.contextmanager
def lower_multihead_attention(module, projection_packing="none"):
    if projection_packing not in {"none", "self", "cross", "all"}:
        raise ValueError(f"unsupported projection packing: {projection_packing!r}")
    replacements = []
    for parent_path, parent in module.named_modules():
        for name, child in list(parent._modules.items()):
            if isinstance(child, nn.MultiheadAttention):
                full_name = f"{parent_path}.{name}" if parent_path else name
                strategy = "separate"
                if name == "self_attn" and projection_packing in {"self", "all"}:
                    strategy = "packed_self"
                elif name == "multihead_attn" and projection_packing in {"cross", "all"}:
                    strategy = "packed_cross"
                elif (projection_packing != "none"
                      and name not in {"self_attn", "multihead_attn"}):
                    raise ValueError(
                        "projection packing requires decoder attention names; "
                        f"got {full_name!r}")
                lowered = Torch21MultiheadAttention(child, strategy)
                lowered.train(child.training)
                parent._modules[name] = lowered
                replacements.append((parent, name, child))
    try:
        yield len(replacements)
    finally:
        for parent, name, child in replacements:
            parent._modules[name] = child


def operator_inventory(scripted):
    return sorted(torch.jit.export_opnames(scripted))


def assert_torch21_operators(scripted):
    operators = operator_inventory(scripted)
    forbidden = sorted(FORBIDDEN_OPERATORS.intersection(operators))
    if forbidden:
        raise RuntimeError(f"Torch 2.1 export contains forbidden operators: {forbidden}")
    return operators


def write_compatibility_manifest(scripted, actor_path, output_path, profile,
                                 parity=None, input_schema=None,
                                 profile_resolution=None, contract=None):
    operators = assert_torch21_operators(scripted)
    operator_payload = json.dumps(operators, separators=(",", ":")).encode("utf-8")
    actor_bytes = Path(actor_path).read_bytes()
    payload = {
        "schema_version": 1,
        "format": "torchscript-manual-sdpa-v1",
        "profile": profile,
        "producer_torch": torch.__version__,
        "target_torch": TARGET_TORCH,
        "actor_sha256": hashlib.sha256(actor_bytes).hexdigest(),
        "operator_sha256": hashlib.sha256(operator_payload).hexdigest(),
        "operators": operators,
        "forbidden_operators": sorted(FORBIDDEN_OPERATORS),
        "parity": parity or {},
        "input_schema": input_schema or [],
        "profile_resolution": profile_resolution or {},
        "contract": contract or {},
    }
    Path(output_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
    return payload
