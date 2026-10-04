from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import numpy as np


# ---------------------------------------------------------------------------
# Per-term dropout configuration
# ---------------------------------------------------------------------------

@dataclass
class TermDropoutEntry:
    """Per-term condition dropout schedule.

    Fields mirror AdaptiveConditionDropout parameters but are applied
    independently to each named term's slice of the condition vector.
    """
    enabled: bool = True
    initial_prob: float = 0.0      # P(dropout) at step 0
    final_prob: float = 0.3        # P(dropout) after warmup
    warmup_steps: int = 100000     # Steps for linear ramp
    dropout_type: str = "null"     # 'null' | 'noise' | 'dimensions' | 'perturb'
    noise_std: float = 0.1


# ---------------------------------------------------------------------------
# Per-term condition dropout
# ---------------------------------------------------------------------------

class PerTermConditionDropout:
    """Per-term condition dropout for task-condition vectors.

    Applies independent dropout to each named term's slice of the condition
    tensor, using the same strategies as AdaptiveConditionDropout but
    configured per-term rather than globally.

    Intended to be applied BEFORE the TaskMaskGenerator mask so that
    dropout corruption of individual terms is still visible to the mask
    signal (the mask vector is appended after dropout).

    Usage (training)
    ----------------
    dropout = PerTermConditionDropout(term_configs, term_boundaries)
    ncond = dropout(ncond, training=True)   # [B, T, cond_dim]
    dropout.step()

    Usage (inference)
    -----------------
    ncond = dropout(ncond, training=False)  # no-op, returns unchanged
    """

    def __init__(
        self,
        term_configs: Dict[str, TermDropoutEntry],
        term_boundaries: List[Tuple[str, int, int]],
    ):
        """
        Args:
            term_configs:    Per-term dropout configuration, keyed by term name.
                             Terms absent from this dict are never dropped.
            term_boundaries: [(term_name, start_dim, end_dim), ...].
                             Obtained from TermComposer.cond_term_boundaries.
        """
        self.term_configs = term_configs
        self.term_boundaries = term_boundaries
        self.current_step = 0

    def set_term_boundaries(self, boundaries: List[Tuple[str, int, int]]) -> None:
        """Update term boundaries (called after dataset is created)."""
        self.term_boundaries = boundaries

    def get_dropout_prob(self, term_name: str) -> float:
        """Current P(dropout) for a term based on its linear warmup schedule."""
        cfg = self.term_configs.get(term_name)
        if cfg is None or not cfg.enabled:
            return 0.0
        if cfg.warmup_steps <= 0:
            return cfg.final_prob
        alpha = min(1.0, self.current_step / cfg.warmup_steps)
        return cfg.initial_prob + (cfg.final_prob - cfg.initial_prob) * alpha

    def __call__(
        self,
        condition: torch.Tensor,
        training: bool = True,
    ) -> torch.Tensor:
        """Apply per-term dropout to condition tensor.

        Args:
            condition: [B, cond_dim] or [B, T, cond_dim]
            training:  If False, returns condition unchanged.

        Returns:
            Condition with per-term dropout applied (in-place on a clone).
        """
        if not training or not self.term_boundaries:
            return condition

        condition_out = condition.clone()
        device = condition.device
        batch_size = condition.shape[0]

        for term_name, start, end in self.term_boundaries:
            cfg = self.term_configs.get(term_name)
            if cfg is None or not cfg.enabled:
                continue

            # "perturb" applies to ALL samples — no Bernoulli gate needed.
            # noise_std here is the TARGET L2 NORM of the perturbation vector,
            # NOT per-dimension σ.  We scale it down by √D so that
            # ‖noise‖ ≈ noise_std in expectation.
            if cfg.dropout_type == "perturb":
                target = condition_out[..., start:end]
                term_dim = end - start
                sigma_per_dim = cfg.noise_std / (term_dim ** 0.5) if term_dim > 0 else cfg.noise_std
                noise = torch.randn_like(target) * sigma_per_dim
                condition_out[..., start:end] = target + noise
                continue

            prob = self.get_dropout_prob(term_name)
            if prob <= 0.0:
                continue

            # Per-batch Bernoulli: True = this sample gets dropout applied
            drop_mask = torch.rand(batch_size, device=device) < prob  # [B]
            if not drop_mask.any():
                continue

            if cfg.dropout_type in ("null", None, "None", "zero"):
                condition_out[drop_mask, ..., start:end] = 0.0

            elif cfg.dropout_type == "noise":
                target = condition_out[drop_mask, ..., start:end]
                noise = torch.randn_like(target) * cfg.noise_std
                condition_out[drop_mask, ..., start:end] = target + noise

            elif cfg.dropout_type == "dimensions":
                term_dim = end - start
                # Independent per-dimension Bernoulli for each dropped sample
                # Handle both [B, D] and [B, T, D] cases
                target = condition_out[drop_mask, ..., start:end]  # [n_drop, ..., term_dim]
                flat = target.reshape(-1, term_dim)
                n_rows = flat.shape[0]
                dim_drop = torch.rand(n_rows, term_dim, device=device) < prob
                flat[dim_drop] = 0.0
                condition_out[drop_mask, ..., start:end] = flat.reshape(target.shape)

            else:
                raise ValueError(f"Unknown dropout_type '{cfg.dropout_type}' for term '{term_name}'")

        return condition_out

    def step(self) -> None:
        """Advance the internal step counter (call once per training step)."""
        self.current_step += 1

    def get_log_dict(self) -> dict:
        """Return per-term dropout probabilities for logging."""
        return {
            f"term_dropout/{name}_p_drop": self.get_dropout_prob(name)
            for name, _, _ in self.term_boundaries
            if name in self.term_configs
        }

    def state_dict(self) -> Dict:
        return {"current_step": self.current_step}

    def load_state_dict(self, state: Dict) -> None:
        self.current_step = state.get("current_step", 0)


# ---------------------------------------------------------------------------
# Legacy full-condition dropout (kept for backward compatibility)
# ---------------------------------------------------------------------------

class AdaptiveConditionDropout:
    """
    Adaptive Conditional Dropout for improving robustness to condition variations.

    Implements progressive dropout scheduling with multiple dropout strategies:
    - Complete dropout (null condition): Random condition set to zero
    - Gaussian noise injection: Add noise proportional to condition
    - Structured dropout: Drop individual dimensions randomly

    References:
        Ho & Salimans, "Classifier-Free Diffusion Guidance" (NeurIPS 2022)
    """

    def __init__(
        self,
        initial_prob: float = 0.1,
        final_prob: float = 0.3,
        warmup_steps: int = 50000,
        dropout_type: str = "null",
        noise_std: float = 0.1,
        seed: int = 0,
        clip_latent_dim: int = 0,
    ):
        """
        Args:
            initial_prob: Initial dropout probability
            final_prob: Final dropout probability (after warmup)
            warmup_steps: Number of steps for linear warmup
            dropout_type: Type of dropout ('null', 'noise', 'dimensions', 'perturb')
                - 'null': Set condition to zeros
                - 'noise': Add Gaussian noise to dropped samples
                - 'dimensions': Randomly drop individual dimensions
                - 'perturb': Add small Gaussian perturbation to ALL samples, ALL dims
                    (no Bernoulli gate — consistent noise, gentler than 'noise')
            noise_std: Standard deviation of Gaussian noise (for 'noise' type)
            seed: Random seed for reproducibility
            clip_latent_dim: If > 0 and cond_dim > clip_latent_dim, dropout is applied
                only to the last clip_latent_dim dims (the CLIP part), leaving the
                preceding RL observation dims untouched. Set to 0 to apply dropout
                to the full condition vector (default behaviour).
        """
        self.initial_prob = initial_prob
        self.final_prob = final_prob
        self.warmup_steps = warmup_steps
        self.dropout_type = dropout_type
        self.noise_std = noise_std
        self.current_step = 0
        self.rng = np.random.RandomState(seed)
        self.clip_latent_dim = clip_latent_dim

    def get_dropout_prob(self) -> float:
        """Get current dropout probability based on progressive schedule."""
        if self.current_step < self.warmup_steps:
            # Linear warmup from initial to final probability
            alpha = self.current_step / self.warmup_steps
            return self.initial_prob + (self.final_prob - self.initial_prob) * alpha
        else:
            return self.final_prob

    def __call__(
        self,
        condition: torch.Tensor,
        training: bool = True,
    ) -> torch.Tensor:
        """
        Apply adaptive dropout to condition tensor.

        Args:
            condition: (B, cond_dim) or (B, T_cond, cond_dim) condition tensor
            training: Whether in training mode (applies dropout) or inference mode

        Returns:
            condition: Condition tensor with dropout applied (or unchanged if not training)
        """
        if not training:
            return condition

        condition_out = condition.clone()
        cond_dim = condition_out.shape[-1]

        # Determine the slice of dims to apply dropout to.
        if self.clip_latent_dim > 0 and cond_dim > self.clip_latent_dim:
            clip_start = cond_dim - self.clip_latent_dim
            target = condition_out[..., clip_start:]
        else:
            clip_start = 0
            target = condition_out

        # "perturb" applies to ALL samples, ALL dims — no Bernoulli gate.
        # noise_std is the TARGET L2 NORM of the perturbation vector.
        if self.dropout_type == "perturb":
            drop_dim = target.shape[-1]
            sigma_per_dim = self.noise_std / (drop_dim ** 0.5) if drop_dim > 0 else self.noise_std
            noise = torch.randn_like(target) * sigma_per_dim
            if clip_start > 0:
                condition_out[..., clip_start:] = target + noise
            else:
                condition_out[:] = target + noise
            self.current_step += 1
            return condition_out

        prob = self.get_dropout_prob()
        device = condition.device
        batch_size = condition.shape[0]
        mask = torch.rand(batch_size, device=device) < prob

        if not mask.any():
            self.current_step += 1
            return condition_out

        if self.dropout_type == "null":
            if clip_start > 0:
                condition_out[mask, ..., clip_start:] = 0.0
            else:
                condition_out[mask] = 0.0

        elif self.dropout_type == "noise":
            noise = torch.randn_like(target[mask]) * self.noise_std
            if clip_start > 0:
                condition_out[mask, ..., clip_start:] = target[mask] + noise
            else:
                condition_out[mask] = target[mask] + noise

        elif self.dropout_type == "dimensions":
            drop_dim = target.shape[-1]
            dimension_mask = torch.rand((mask.sum(), drop_dim), device=device) < prob
            if clip_start > 0:
                tmp = condition_out[mask, ..., clip_start:].clone()
                tmp.reshape(-1, drop_dim)[dimension_mask] = 0.0
                condition_out[mask, ..., clip_start:] = tmp
            else:
                condition_out[mask].reshape(-1, drop_dim)[dimension_mask] = 0.0

        else:
            raise ValueError(f"Unknown dropout_type: {self.dropout_type}")

        self.current_step += 1
        return condition_out

    def state_dict(self) -> Dict:
        """Get state for checkpointing."""
        return {
            'current_step': self.current_step,
        }

    def load_state_dict(self, state: Dict) -> None:
        """Load state from checkpoint."""
        self.current_step = state.get('current_step', 0)
