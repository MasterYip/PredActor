"""BodyGroupSelector — select which body indices receive guidance by group membership."""

from __future__ import annotations


class BodyGroupSelector:
    """Selects which body indices receive guidance based on group membership.

    Args:
        groups: Dict mapping group_name → list of body indices.
        guided_groups: List of group names to guide (e.g. ``["torso", "hip"]``).
                       Bodies in groups NOT listed here are left unchanged.
    """

    def __init__(self, groups: dict[str, list[int]], guided_groups: list[str]):
        self._groups = groups
        self._guided_indices: set[int] = set()
        for g in guided_groups:
            if g not in groups:
                raise KeyError(f"Unknown body group '{g}'. Available: {list(groups.keys())}")
            self._guided_indices.update(groups[g])
        self._all_indices = set(range(30))

    @property
    def guided_indices(self) -> set[int]:
        return self._guided_indices

    def is_guided(self, body_idx: int) -> bool:
        return body_idx in self._guided_indices

    def toggle_index(self, body_idx: int) -> bool:
        """Add or remove *body_idx* from the guided set.  Returns the new state.

        Used by the DEBUG heatmap for live click-to-toggle.
        """
        if body_idx in self._guided_indices:
            self._guided_indices.discard(body_idx)
            return False
        self._guided_indices.add(body_idx)
        return True

    def reset_indices(self, groups: dict[str, list[int]], guided_groups: list[str]) -> None:
        """Rebuild ``_guided_indices`` from group definitions (DEBUG reset)."""
        self._guided_indices.clear()
        for g in guided_groups:
            self._guided_indices.update(groups[g])
