"""Task mask generator for task-condition controllability.

The task mask is a binary vector (same dim as task_condition) that selects
which terms are active. It is concatenated with the (masked) condition tensor
and fed to the policy network, allowing the network to learn to operate with
any subset of active terms.

This is distinct from AdaptiveConditionDropout, which corrupts the full
condition vector for semantic robustness. Both can coexist in training.

Public API
----------
TermMaskEntry      — per-term mask schedule config
TaskMaskGenerator  — samples and applies task masks
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch


# ---------------------------------------------------------------------------
# Per-term mask configuration
# ---------------------------------------------------------------------------

@dataclass
class TermMaskEntry:
    """Per-term mask probability schedule."""
    enabled: bool = True           # If False, term is always active (mask=1)
    initial_prob: float = 0.0      # P(mask=0) at step 0. 0 = always active initially
    final_prob: float = 0.5        # P(mask=0) after warmup
    warmup_steps: int = 100000     # Steps to linearly ramp initial_prob → final_prob
    mask_mode: str = "full_term"   # "full_term": one draw masks all dims; "bit_wise": per-dim draw


# ---------------------------------------------------------------------------
# TaskMaskGenerator
# ---------------------------------------------------------------------------

class TaskMaskGenerator:
    """Generates binary task masks for task_condition conditioning.

    Mask shape: [cond_dim]
    Value 1 = term is active (pass-through), 0 = term is masked (zeroed out).

    Usage (training)
    ----------------
    mask = gen.sample_mask(B, device)          # [B, cond_dim]
    masked_cond = gen.apply(cond, mask)        # [B, T, cond_dim], inactive dims zeroed
    mask_exp = mask.unsqueeze(1).expand_as(masked_cond)
    cond_in = torch.cat([masked_cond, mask_exp], dim=-1)  # [B, T, 2*cond_dim]
    gen.step()

    Usage (inference)
    -----------------
    mask = gen.inference_mask(['joint_pos', 'joint_vel'], device)  # [cond_dim]
    mask = mask.unsqueeze(0)                    # [1, cond_dim]
    masked_cond = gen.apply(cond, mask)
    mask_exp = mask.unsqueeze(1).expand(B, T, -1)
    cond_in = torch.cat([masked_cond, mask_exp], dim=-1)
    """

    def __init__(
        self,
        term_configs: Dict[str, TermMaskEntry],
        term_boundaries: List[Tuple[str, int, int]],
    ):
        """
        Args:
            term_configs:     Per-term training mask schedule, keyed by term name.
                              Terms absent from this dict are always active during training.
            term_boundaries:  [(term_name, start_dim, end_dim), ...].
                              Obtained from TermComposer.cond_term_boundaries.
        """
        self.term_configs = term_configs
        self.term_boundaries = term_boundaries
        self.current_step = 0
        self._cond_dim: Optional[int] = None
        self._default_infer_active: Dict[str, bool] = {}  # set by from_config
        if term_boundaries:
            self._cond_dim = term_boundaries[-1][2] if term_boundaries else 0

    @classmethod
    def from_config(cls, config: dict) -> "TaskMaskGenerator":
        """Build from a config dict (parsed from YAML).

        Expected format (under ``policy.task_mask_config``)::

            task_mask_config:
              enable: true
              mask_config_train:
                joint_pos:
                  enabled: true
                  initial_prob: 0.0
                  final_prob: 0.3
                  warmup_steps: 100000
              mask_config_infer:
                joint_pos: true
                joint_vel: true
                projected_gravity: false
        """
        term_configs: Dict[str, TermMaskEntry] = {}
        for term_name, term_cfg in config.get("mask_config_train", {}).items():
            if isinstance(term_cfg, dict):
                term_configs[term_name] = TermMaskEntry(
                    enabled=bool(term_cfg.get("enabled", True)),
                    initial_prob=float(term_cfg.get("initial_prob", 0.0)),
                    final_prob=float(term_cfg.get("final_prob", 0.5)),
                    warmup_steps=int(term_cfg.get("warmup_steps", 100000)),
                    mask_mode=str(term_cfg.get("mask_mode", "full_term")),
                )
            else:
                term_configs[term_name] = TermMaskEntry(enabled=bool(term_cfg))

        infer_active: Dict[str, bool] = {}
        for term_name, active in config.get("mask_config_infer", {}).items():
            infer_active[term_name] = bool(active)

        obj = cls(term_configs=term_configs, term_boundaries=[])
        obj._default_infer_active = infer_active
        return obj

    def set_term_boundaries(self, boundaries: List[Tuple[str, int, int]]) -> None:
        """Set term boundaries from TermComposer.cond_term_boundaries."""
        self.term_boundaries = boundaries
        self._cond_dim = boundaries[-1][2] if boundaries else 0

    @property
    def cond_dim(self) -> int:
        if self._cond_dim is None:
            raise RuntimeError("term_boundaries not set — call set_term_boundaries() first.")
        return self._cond_dim

    # ------------------------------------------------------------------
    # Probability schedule
    # ------------------------------------------------------------------

    def get_mask_prob(self, term_name: str) -> float:
        """Current P(mask=0) for the given term."""
        cfg = self.term_configs.get(term_name)
        if cfg is None or not cfg.enabled:
            return 0.0  # always active
        if cfg.warmup_steps <= 0:
            return cfg.final_prob
        alpha = min(1.0, self.current_step / cfg.warmup_steps)
        return cfg.initial_prob + (cfg.final_prob - cfg.initial_prob) * alpha

    # ------------------------------------------------------------------
    # Mask sampling
    # ------------------------------------------------------------------

    def sample_mask(self, batch_size: int, device) -> torch.Tensor:
        """Sample a binary mask [B, cond_dim] for a training batch.

        For each term, independently draws Bernoulli(1 - p_mask) per batch
        item and broadcasts to all dimensions belonging to that term.

        Returns:
            Float tensor of shape [B, cond_dim] with values in {0.0, 1.0}.
        """
        mask = torch.ones(batch_size, self.cond_dim, device=device)
        for term_name, start, end in self.term_boundaries:
            p_mask = self.get_mask_prob(term_name)
            if p_mask <= 0.0:
                continue  # always active, leave as 1
            cfg = self.term_configs.get(term_name)
            mode = cfg.mask_mode if cfg is not None else "full_term"
            if mode == "bit_wise":
                # Independent Bernoulli per dimension per batch item
                mask[:, start:end] = torch.bernoulli(
                    torch.full((batch_size, end - start), 1.0 - p_mask, device=device)
                )
            else:
                # full_term: one draw per batch item broadcast to all dims
                active = torch.bernoulli(
                    torch.full((batch_size,), 1.0 - p_mask, device=device)
                )  # [B]
                mask[:, start:end] = active.unsqueeze(1).expand(-1, end - start)
        return mask

    # ------------------------------------------------------------------
    # Inference mask
    # ------------------------------------------------------------------

    def inference_mask(
        self,
        active_terms: Optional[List[str]],
        device,
    ) -> torch.Tensor:
        """Build a deterministic mask [cond_dim] for inference.

        Priority:
          1. ``active_terms`` passed explicitly (overrides everything).
          2. ``mask_config_infer`` from YAML (default inference activation per term).
          3. All terms active (all-ones) if neither is specified.

        Args:
            active_terms: Explicit list of term names to keep active, or None
                          to fall back to the YAML-configured default.

        Returns:
            Float tensor of shape [cond_dim] with values in {0.0, 1.0}.
        """
        if active_terms is not None:
            # Explicit override: only named terms are active
            active_set = set(active_terms)
            mask = torch.zeros(self.cond_dim, device=device)
            for term_name, start, end in self.term_boundaries:
                if term_name in active_set:
                    mask[start:end] = 1.0
            return mask

        if self._default_infer_active:
            # YAML-configured default: use mask_config_infer.
            # Terms absent from the config default to inactive (False) so that
            # setting a term to false is never silently overridden by a key mismatch.
            mask = torch.zeros(self.cond_dim, device=device)
            for term_name, start, end in self.term_boundaries:
                if self._default_infer_active.get(term_name, False):
                    mask[start:end] = 1.0
            return mask

        # No inference config: all terms active
        return torch.ones(self.cond_dim, device=device)

    # ------------------------------------------------------------------
    # Apply mask
    # ------------------------------------------------------------------

    @staticmethod
    def apply(cond: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Zero inactive dims in cond.

        Args:
            cond: [B, T, cond_dim] or [B, cond_dim]
            mask: [B, cond_dim] or [1, cond_dim] or [cond_dim]

        Returns:
            cond with inactive term dims zeroed, same shape as input.
        """
        if cond.dim() == 3 and mask.dim() == 2:
            # Broadcast mask over T dimension
            mask = mask.unsqueeze(1)  # [B, 1, cond_dim]
        return cond * mask

    # ------------------------------------------------------------------
    # Step counter
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Advance the internal step counter (call once per training step)."""
        self.current_step += 1

    # ------------------------------------------------------------------
    # Checkpoint
    # ------------------------------------------------------------------

    def state_dict(self) -> dict:
        return {
            "current_step": self.current_step,
        }

    def load_state_dict(self, state: dict) -> None:
        self.current_step = state.get("current_step", 0)
        # _default_infer_active is not persisted — it is always sourced from the
        # dataset profile YAML at runtime via set_task_mask_from_profile().

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def get_log_dict(self) -> dict:
        """Return per-term mask probabilities for logging."""
        return {
            f"task_mask/{name}_p_mask": self.get_mask_prob(name)
            for name, _, _ in self.term_boundaries
        }
