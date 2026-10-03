"""GuidanceActivationSet — per-guidance activation configuration.

Each :class:`GuidanceBase` instance owns one of these.  It encapsulates
everything the guidance needs to know about what it activates: which
observation terms, which body groups, its gain, and its enable state.
This replaces the monolithic shared state from v1.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GuidanceActivationSet:
    """Encapsulates what a guidance type activates: terms, body groups, and gain.

    Each guidance instance gets its own ``GuidanceActivationSet``, making
    guidance types independently configurable from YAML and independently
    toggleable from the GUI.

    Attributes:
        guided_terms: Which observation terms this guidance writes to
            (e.g. ``["root_pos_local", "body_pos_local"]``).
        guided_body_groups: Which body groups receive guidance
            (e.g. ``["torso", "hip"]``).
        group_intensities: Per-group intensity 0.0–1.0 (populated from
            ``guided_body_groups`` at construction time).
        body_intensity_overrides: Per-body override dict set by heatmap
            click-to-toggle (body_idx → intensity).
        kp: Proportional gain for this guidance type (0 = no correction).
        enabled: Master enable/disable switch.
        disabled_terms: Terms temporarily disabled via debug-panel checkboxes.
    """

    guided_terms: list[str]
    guided_body_groups: list[str]
    group_intensities: dict[str, float] = field(default_factory=dict)
    body_intensity_overrides: dict[int, float] = field(default_factory=dict)
    kp: float = 1.0
    enabled: bool = True
    disabled_terms: set[str] = field(default_factory=set)

    @property
    def effective_terms(self) -> set[str]:
        """Guided terms minus any disabled via debug checkboxes."""
        return set(self.guided_terms) - self.disabled_terms

    def build_body_intensity(self, all_groups: dict[str, list[int]]) -> list[float]:
        """Convert per-group intensities + per-body overrides to a per-body weight list.

        Group intensities are applied first (max wins across overlapping
        groups), then per-body overrides replace the group-derived value
        for individual bodies.

        Args:
            all_groups: Group definitions (e.g. ``G1_BODY_GROUPS``).

        Returns:
            ``list[float]`` of length 30, one weight per G1 body.
        """
        weights = [0.0] * 30
        for gname, indices in all_groups.items():
            w = self.group_intensities.get(gname, 0.0)
            for idx in indices:
                if w > weights[idx]:
                    weights[idx] = w
        # Per-body overrides take precedence (set by clicking heatmap cells)
        for idx, val in self.body_intensity_overrides.items():
            weights[idx] = val
        return weights

    def reset_overrides(self) -> None:
        """Clear all per-body overrides and disabled terms."""
        self.body_intensity_overrides.clear()
        self.disabled_terms.clear()
