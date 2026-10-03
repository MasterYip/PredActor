"""TermResolver — maps observation term names to slice positions in the flat obs vector.

Reads a dataset profile (e.g. ``"g1_standard"``) and walks its
``observation.terms`` list, using ``TERM_DIMS`` to compute cumulative
offsets.  The result is a dict ``{term_name: (start, end)}``.
"""

from __future__ import annotations

import torch


class TermResolver:
    """Maps observation term names to their slice positions in the flat obs vector.

    Replaces the v1 ``ObsTermIndex`` with a cleaner name but identical behaviour.
    """

    def __init__(self, profile: str):
        from diffusion_policy.dataset.data_profile import DataProfile
        from diffusion_policy.dataset.term_compose import TERM_DIMS, _init_term_dims

        if TERM_DIMS.get("joint_pos") is None:
            _init_term_dims()

        dp = DataProfile.from_yaml(profile)
        self._slices: dict[str, tuple[int, int]] = {}
        offset = 0
        for term in dp.observation.terms:
            d = TERM_DIMS.get(term)
            if d is None:
                raise KeyError(f"Unknown term dimension for '{term}'")
            self._slices[term] = (offset, offset + d)
            offset += d
        self._total_dim = offset

    # ── Accessors ──────────────────────────────────────────────────────────

    def slice(self, term: str) -> tuple[int, int]:
        """Return ``(start, end)`` for *term*."""
        return self._slices[term]

    def get(self, obs: torch.Tensor, term: str) -> torch.Tensor:
        """Extract term from obs tensor ``[..., D]``."""
        s, e = self._slices[term]
        return obs[..., s:e]

    def set(self, obs: torch.Tensor, term: str, value: torch.Tensor):
        """Write *value* into *obs* at *term*'s position (in-place)."""
        s, e = self._slices[term]
        obs[..., s:e] = value

    @property
    def dim(self) -> int:
        """Total flat observation dimension."""
        return self._total_dim

    @property
    def terms(self) -> list[str]:
        """Sorted list of all term names in this profile."""
        return sorted(self._slices.keys())

    @property
    def slices(self) -> dict[str, tuple[int, int]]:
        """Read-only view of the internal slice map."""
        return dict(self._slices)
