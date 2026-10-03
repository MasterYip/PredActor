"""Base interface and adapters for task condition providers.

A *task condition provider* supplies external conditioning signals to a
diffusion policy during evaluation.  Examples:

- A CLIP text embedding typed interactively by the user
- A motion-reference position set via GUI sliders
- Any combination of the above via ``CompositeCondProvider``

All providers share the ``TaskCondProvider`` ABC so that ``EnvRunner`` can
treat them uniformly through a single ``inject_raw_keys`` call each step.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import torch


class TaskCondProvider(ABC):
    """Abstract base class for all task condition providers.

    Providers inject externally-sourced keys into the single-step *next_terms*
    dict every policy step.  The dict is subsequently shifted into
    ``raw_history`` by the runner, and composed into the policy conditioning
    tensor by ``TermComposer.compose_cond``.

    Lifecycle
    ---------
    ``start()``  — called once before the eval loop begins (open GUI, threads…)
    ``stop()``   — called once after the loop ends (clean up resources)
    ``inject_raw_keys(next_terms, batch_size)``
                 — called each step to write key(s) into *next_terms* in-place

    Optional legacy path
    --------------------
    ``get_task_cond(raw_history, batch_size, n_task_steps, device)``
                 — used by the old non-task_interface eval path; override only
                   if your provider cannot write through ``inject_raw_keys``.
                   Returns ``None`` by default.
    """

    def start(self) -> None:
        """Start any background threads / GUI windows needed by this provider."""
        pass

    def stop(self) -> None:
        """Stop background threads / GUI windows and release resources."""
        pass

    def inject_raw_keys(self, next_terms: dict, batch_size: int) -> None:
        """Write task condition key(s) into *next_terms* in-place.

        *next_terms* is the single-step obs dict produced by the environment
        (values shaped ``[B, 1, ...]``).  Providers append their own key(s)
        here so that ``TermComposer`` can read them when composing the
        conditioning tensor.

        The default implementation is a no-op — override in subclasses.

        Args:
            next_terms: Mutable dict mapping str → Tensor ``[B, 1, ...]``.
            batch_size: Number of parallel environments (``B``).
        """
        pass

    def get_task_cond(
        self,
        raw_history: dict,
        batch_size: int,
        n_task_steps: int,
        device=None,
    ) -> Optional[torch.Tensor]:
        """Legacy path: return ``[B, n_task_steps, D_cond]`` or ``None``.

        Prefer ``inject_raw_keys`` for new providers.  This method is called
        only by the old non-task_interface branch of the eval loop.
        """
        return None


# ---------------------------------------------------------------------------
# Built-in adapters
# ---------------------------------------------------------------------------

class ClipCondProvider(TaskCondProvider):
    """Adapter that wraps a legacy ``CLIPTeleop`` or ``CLIPInterp`` object.

    These objects expose ``get_embedding(batch_size, n_cond_steps)`` but do not
    derive from ``TaskCondProvider``.  This wrapper bridges the two interfaces
    by calling ``get_embedding`` inside ``inject_raw_keys`` and writing the
    result to ``next_terms["motion_latent"]``.

    Args:
        clip_provider: A ``CLIPTeleop`` or ``CLIPInterp`` instance.
    """

    def __init__(self, clip_provider) -> None:
        self._p = clip_provider
        self._clip_source = clip_provider

    def start(self) -> None:
        self._p.start()

    def stop(self) -> None:
        self._p.stop()

    def inject_raw_keys(self, next_terms: dict, batch_size: int) -> None:
        """Encode the current text/interpolation and store as ``motion_latent``."""
        emb = self._p.get_embedding(batch_size=batch_size, n_cond_steps=1)  # [B, 1, D]
        if next_terms:
            terms_device = next(iter(next_terms.values())).device
            emb = emb.to(terms_device)
        next_terms["motion_latent"] = emb

    def get_task_cond(self, raw_history, batch_size, n_task_steps, device):
        return self._p.get_embedding(batch_size=batch_size, n_cond_steps=n_task_steps).to(device)


class CompositeCondProvider(TaskCondProvider):
    """Fan-out provider that delegates to multiple ``TaskCondProvider`` instances.

    Each sub-provider handles its own raw-history key(s).  On each call to
    ``inject_raw_keys`` every sub-provider is invoked in order so all keys are
    populated.

    ``get_task_cond`` returns the result of the first sub-provider that returns
    a non-``None`` tensor (typically the CLIP provider).

    Args:
        providers: List of ``TaskCondProvider`` instances to combine.
    """

    def __init__(self, providers: List[TaskCondProvider]) -> None:
        self._providers: List[TaskCondProvider] = list(providers)

    # -- lifecycle --

    def start(self) -> None:
        for p in self._providers:
            p.start()

    def stop(self) -> None:
        for p in self._providers:
            p.stop()

    # -- main interface --

    def inject_raw_keys(self, next_terms: dict, batch_size: int) -> None:
        for p in self._providers:
            p.inject_raw_keys(next_terms, batch_size)

    def get_task_cond(self, raw_history, batch_size, n_task_steps, device):
        for p in self._providers:
            result = p.get_task_cond(raw_history, batch_size, n_task_steps, device)
            if result is not None:
                return result
        return None
