"""Zone mapping — geometric joystick→semantics configuration.

Defines region types, zone definitions, and the JoyTextMapping container
that maps a joystick (vx, vy) position to one or more active zones with
blend weights for smooth semantic transitions.

Region types
------------
``DiscRegion``      Circle around origin — stand/idle zone.
``WedgeRegion``     Pie-slice sector — directional walk/run zones.
``AnnulusRegion``   Ring band — speed bands (walk ring, run ring).
``RectangleRegion`` Axis-aligned rectangle — general-purpose zones.

Each region implements ``contains(vx, vy) → bool`` and
``signed_distance(vx, vy) → float`` (positive = inside, negative = outside).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ═══════════════════════════════════════════════════════════════════════════
# Region types
# ═══════════════════════════════════════════════════════════════════════════

class ZoneRegion:
    """Abstract base for geometric region definitions.

    Subclasses must implement ``contains(vx, vy)`` and ``signed_distance(vx, vy)``.
    """

    type: str = "base"

    def contains(self, vx: float, vy: float) -> bool:
        """Return True if (vx, vy) is strictly inside this region."""
        raise NotImplementedError

    def signed_distance(self, vx: float, vy: float) -> float:
        """Signed distance from (vx, vy) to the region boundary.

        Positive = inside the region (distance to nearest boundary).
        Negative = outside the region (negated distance to nearest boundary).
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, d: dict) -> "ZoneRegion":
        """Factory: dispatch on ``d["type"]``."""
        rtype = d["type"]
        if rtype == "disc":
            return DiscRegion(
                center=tuple(d.get("center", [0.0, 0.0])),
                radius=float(d["radius"]),
            )
        elif rtype == "wedge":
            return WedgeRegion(
                center=tuple(d.get("center", [0.0, 0.0])),
                r_min=float(d.get("r_min", 0.0)),
                r_max=float(d["r_max"]),
                theta_min=float(d.get("theta_min", -180.0)),
                theta_max=float(d.get("theta_max", 180.0)),
            )
        elif rtype == "annulus":
            return AnnulusRegion(
                center=tuple(d.get("center", [0.0, 0.0])),
                r_min=float(d.get("r_min", 0.0)),
                r_max=float(d["r_max"]),
            )
        elif rtype == "rectangle":
            return RectangleRegion(
                x_min=float(d.get("x_min", -1.0)),
                x_max=float(d.get("x_max", 1.0)),
                y_min=float(d.get("y_min", -1.0)),
                y_max=float(d.get("y_max", 1.0)),
            )
        raise ValueError(f"Unknown region type: {rtype!r}")


@dataclass
class DiscRegion(ZoneRegion):
    """Circular disc region (e.g. stand/idle zone near origin).

    A point is inside when its Euclidean distance from *center* ≤ *radius*.
    """

    center: tuple[float, float] = (0.0, 0.0)
    radius: float = 0.2
    type: str = "disc"

    def contains(self, vx: float, vy: float) -> bool:
        dx = vx - self.center[0]
        dy = vy - self.center[1]
        return math.hypot(dx, dy) <= self.radius

    def signed_distance(self, vx: float, vy: float) -> float:
        dx = vx - self.center[0]
        dy = vy - self.center[1]
        dist = math.hypot(dx, dy)
        return self.radius - dist  # positive inside, negative outside


@dataclass
class WedgeRegion(ZoneRegion):
    """Pie-slice sector: radial band + angular span.

    A point is inside when:
        r_min ≤ distance from center ≤ r_max  AND
        theta_min ≤ angle (degrees) ≤ theta_max

    Angles are specified in degrees, measured CCW from +x axis.
    """

    center: tuple[float, float] = (0.0, 0.0)
    r_min: float = 0.0
    r_max: float = 1.0
    theta_min: float = -180.0   # degrees
    theta_max: float = 180.0    # degrees
    type: str = "wedge"

    def contains(self, vx: float, vy: float) -> bool:
        r, theta = self._to_polar(vx, vy)
        if r < self.r_min or r > self.r_max:
            return False
        return self._angle_in_range(theta)

    def signed_distance(self, vx: float, vy: float) -> float:
        r, theta = self._to_polar(vx, vy)

        # Radial distances
        d_inner = r - self.r_min   # positive outside inner boundary
        d_outer = self.r_max - r   # positive inside outer boundary
        d_radial = min(d_inner, d_outer)

        # Angular distances
        d_angular = self._angular_distance(theta)

        # Overall signed distance: if both are positive → inside, min gives
        # distance to nearest boundary.  If either is negative → outside.
        return min(d_radial, d_angular)

    def _to_polar(self, vx: float, vy: float) -> tuple[float, float]:
        dx = vx - self.center[0]
        dy = vy - self.center[1]
        r = math.hypot(dx, dy)
        theta = math.degrees(math.atan2(dy, dx))
        return r, theta

    def _angle_in_range(self, theta: float) -> bool:
        """Check if *theta* (degrees) is within [theta_min, theta_max].

        Handles wrap-around: theta_min=-30, theta_max=30 → narrow forward cone.
        theta_min=150, theta_max=210 → backward cone crossing ±180.
        """
        t_min = self.theta_min
        t_max = self.theta_max
        # Normalize all to [0, 360)
        theta = theta % 360.0
        t_min = t_min % 360.0
        t_max = t_max % 360.0
        if t_min <= t_max:
            return t_min <= theta <= t_max
        else:
            # Range crosses 0°/360° boundary
            return theta >= t_min or theta <= t_max

    def _angular_distance(self, theta: float) -> float:
        """Signed angular distance from *theta* to the angular span boundaries.

        Positive = inside the angular span (degrees to nearest angular edge).
        Negative = outside (negated degrees to nearest angular edge).
        """
        t_min = self.theta_min
        t_max = self.theta_max
        theta_norm = theta % 360.0
        t_min_norm = t_min % 360.0
        t_max_norm = t_max % 360.0

        span = (t_max_norm - t_min_norm) % 360.0

        # Angular distance from theta to t_min (going CCW) and from t_max (going CW)
        d_from_min = (theta_norm - t_min_norm) % 360.0   # CCW from min to theta
        d_to_max = (t_max_norm - theta_norm) % 360.0     # CCW from theta to max

        inside = d_from_min <= span  # equivalent to theta in [min, max] CCW

        if inside:
            # Distance to nearest angular boundary
            return min(d_from_min, d_to_max)
        else:
            # Distance to nearest boundary from outside
            d_to_min = (t_min_norm - theta_norm) % 360.0  # CW to min
            d_from_max = (theta_norm - t_max_norm) % 360.0  # CCW from max
            return -min(d_to_min, d_from_max)


@dataclass
class AnnulusRegion(ZoneRegion):
    """Ring-shaped region between two concentric circles.

    A point is inside when r_min ≤ distance from center ≤ r_max.
    No angular constraint — full 360°.
    """

    center: tuple[float, float] = (0.0, 0.0)
    r_min: float = 0.0
    r_max: float = 1.0
    type: str = "annulus"

    def contains(self, vx: float, vy: float) -> bool:
        dx = vx - self.center[0]
        dy = vy - self.center[1]
        r = math.hypot(dx, dy)
        return self.r_min <= r <= self.r_max

    def signed_distance(self, vx: float, vy: float) -> float:
        dx = vx - self.center[0]
        dy = vy - self.center[1]
        r = math.hypot(dx, dy)
        d_inner = r - self.r_min    # positive outside inner boundary
        d_outer = self.r_max - r    # positive inside outer boundary
        return min(d_inner, d_outer)


@dataclass
class RectangleRegion(ZoneRegion):
    """Axis-aligned rectangular region."""

    x_min: float = -1.0
    x_max: float = 1.0
    y_min: float = -1.0
    y_max: float = 1.0
    type: str = "rectangle"

    def contains(self, vx: float, vy: float) -> bool:
        return self.x_min <= vx <= self.x_max and self.y_min <= vy <= self.y_max

    def signed_distance(self, vx: float, vy: float) -> float:
        dx_min = vx - self.x_min    # positive if inside right edge
        dx_max = self.x_max - vx    # positive if inside left edge
        dy_min = vy - self.y_min
        dy_max = self.y_max - vy
        d_x = min(dx_min, dx_max)
        d_y = min(dy_min, dy_max)
        return min(d_x, d_y)


# ═══════════════════════════════════════════════════════════════════════════
# Zone definition
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class JoyTextZone:
    """One zone in the joystick→semantics mapping.

    Each zone maps joystick position to per-pair CLIP interpolation weights,
    exactly matching the :class:`CLIPInterp` formula:
    ``final = Σ (emb_b - emb_a) * w_i``  (then L2-normalize).

    Attributes:
        name: Human-readable identifier (e.g. ``"walk_forward"``).
        priority: Resolution order — higher priority wins in overlap.
        region: Geometric region definition.
        pair_weights: Map from text-pair name → ``[min_weight, max_weight]``.
            Stick deflection (0→1 within the zone) linearly maps from
            ``min_weight`` to ``max_weight``.  Weights are in [-1, 1]
            following CLIPInterp convention.
        velocity_scale: ``[vx_min, vx_max]`` mapping for joystick magnitude → vx.
        vy_scale: Multiplier for lateral velocity (applied to raw vy).
        wz_scale: Multiplier for yaw rate (applied to raw wz).
    """

    name: str
    priority: int
    region: ZoneRegion
    pair_weights: dict[str, tuple[float, float]] = field(default_factory=dict)
    constant_text: Optional[str] = None   # explicit text for "constant" interp mode
    velocity_scale: tuple[float, float] = (0.0, 0.0)
    vy_scale: float = 0.0
    wz_scale: float = 0.0

    @classmethod
    def from_dict(cls, d: dict, text_pairs: dict[str, tuple[Optional[str], Optional[str]]]) -> "JoyTextZone":
        """Build a zone from a parsed YAML dict.

        ``pair_weights`` keys must match entries in the global *text_pairs* registry.
        Each value is ``[min_weight, max_weight]`` — the weight of that pair's
        difference vector as joystick deflection ranges from 0 to 1 within the zone.

        Args:
            d: Zone config dict.
            text_pairs: Shared text-pair registry (name → (text_a, text_b)).
        """
        # Parse pair_weights: {pair_name: [min, max]}
        pair_weights: dict[str, tuple[float, float]] = {}
        raw_weights = d.get("pair_weights", {})
        if isinstance(raw_weights, dict):
            for pair_name, weight_range in raw_weights.items():
                if pair_name not in text_pairs:
                    raise KeyError(
                        f"Zone {d.get('name', '?')!r}: pair_weights key {pair_name!r} "
                        f"not found in text_pairs registry"
                    )
                lo = float(weight_range[0]) if len(weight_range) > 0 else 0.0
                hi = float(weight_range[1]) if len(weight_range) > 1 else lo
                pair_weights[pair_name] = (lo, hi)

        return cls(
            name=d["name"],
            priority=int(d.get("priority", 0)),
            region=ZoneRegion.from_dict(d["region"]),
            pair_weights=pair_weights,
            constant_text=d.get("constant_text"),
            velocity_scale=(
                float(d.get("velocity_scale", [0.0, 0.0])[0]),
                float(d.get("velocity_scale", [0.0, 0.0])[1]),
            ),
            vy_scale=float(d.get("vy_scale", 0.0)),
            wz_scale=float(d.get("wz_scale", 0.0)),
        )

    def weight_for_pair(self, pair_name: str, progress: float) -> float:
        """Return the weight for *pair_name* at the given stick *progress* (0→1).

        Linearly interpolates between the zone's ``[min_weight, max_weight]`` range.
        Returns 0.0 if the pair is not configured for this zone.
        """
        rng = self.pair_weights.get(pair_name)
        if rng is None:
            return 0.0
        lo, hi = rng
        return lo + (hi - lo) * max(0.0, min(1.0, progress))


# ═══════════════════════════════════════════════════════════════════════════
# Mapping container
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class JoyTextMapping:
    """Complete joystick→text mapping configuration.

    Loaded from a standalone YAML file.  At runtime, :meth:`find_zones`
    maps a joystick (vx, vy) position to 0–N active zones with blend weights.

    Attributes:
        blend_width: Joystick-unit width of the blend region at zone boundaries.
            Larger values → smoother transitions but less crisp zone identity.
        zones: Ordered list of :class:`JoyTextZone` entries.
        text_pairs: Shared text-pair registry (name → (text_a, text_b)).
        vx_range: Joystick vx output range ``[min, max]``.
        vy_range: Joystick vy output range ``[min, max]``.
        wz_range: Joystick wz output range ``[min, max]``.
    """

    blend_width: float = 0.15
    interp_mode: str = "interp"       # "interp" (CLIPInterp formula) or "constant" (debug)
    zones: list[JoyTextZone] = field(default_factory=list)
    text_pairs: dict[str, tuple[Optional[str], Optional[str]]] = field(default_factory=dict)
    vx_range: tuple[float, float] = (-1.5, 1.5)
    vy_range: tuple[float, float] = (-1.0, 1.0)
    wz_range: tuple[float, float] = (-1.0, 1.0)

    # ── YAML I/O ──────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, path: str | Path) -> "JoyTextMapping":
        """Load a mapping from a YAML file.

        Expected top-level key: ``joy_text_mapping``.
        """
        path = Path(path)
        with open(path, "r") as fh:
            raw = yaml.safe_load(fh) or {}

        cfg = raw.get("joy_text_mapping", raw)
        if cfg is None:
            cfg = {}

        interp_mode = str(cfg.get("interp_mode", "interp"))
        if interp_mode not in ("interp", "constant"):
            print(f"[JoyTextMapping] Unknown interp_mode={interp_mode!r}, falling back to 'interp'")
            interp_mode = "interp"
        blend_width = float(cfg.get("blend_width", 0.15))
        vx_range = tuple(cfg.get("vx_range", [-1.5, 1.5]))
        vy_range = tuple(cfg.get("vy_range", [-1.0, 1.0]))
        wz_range = tuple(cfg.get("wz_range", [-1.0, 1.0]))

        # Parse shared text_pairs registry
        text_pairs: dict[str, tuple[Optional[str], Optional[str]]] = {}
        for name, pair in cfg.get("text_pairs", {}).items():
            a = pair[0] if len(pair) > 0 else None
            b = pair[1] if len(pair) > 1 else None
            text_pairs[name] = (a, b)

        # Parse zones
        zones: list[JoyTextZone] = []
        for zd in cfg.get("zones", []):
            zones.append(JoyTextZone.from_dict(zd, text_pairs))

        # Sort by priority (descending) — highest priority first for find_zones
        zones.sort(key=lambda z: z.priority, reverse=True)

        mapping = cls(
            blend_width=blend_width,
            interp_mode=interp_mode,
            zones=zones,
            text_pairs=text_pairs,
            vx_range=vx_range,
            vy_range=vy_range,
            wz_range=wz_range,
        )
        return mapping

    # ── Zone lookup ───────────────────────────────────────────────────────

    def find_zones(self, vx: float, vy: float) -> list[tuple[JoyTextZone, float]]:
        """Return list of ``(zone, membership_strength)`` for a joystick position.

        Membership strength is in [0, 1]:
          - 1.0 = deep inside the zone
          - 0.0 = at or beyond the blend boundary
          - Intermediate = within blend_width of a boundary

        Zones returned in priority-descending order.  The caller should
        normalise strengths across active zones.

        Args:
            vx: Joystick x-axis value (forward velocity direction).
            vy: Joystick y-axis value (lateral velocity direction).
        """
        results: list[tuple[JoyTextZone, float]] = []

        for zone in self.zones:
            dist = zone.region.signed_distance(vx, vy)
            # signed_distance: positive = inside, negative = outside
            if dist >= -self.blend_width:
                strength = max(0.0, min(1.0,
                    (dist + self.blend_width) / self.blend_width))
                if strength > 0.0:
                    results.append((zone, strength))

        # Already sorted by priority (descending) from construction
        # Sort by (priority desc, strength desc) for stable ordering
        results.sort(key=lambda item: (item[0].priority, item[1]), reverse=True)
        return results

    def get_all_unique_texts(self) -> set[str]:
        """Return the set of all non-None text strings in the global text_pairs registry.

        These are the texts that need CLIP embeddings pre-computed.
        """
        texts: set[str] = set()
        for a, b in self.text_pairs.values():
            if a is not None:
                texts.add(a)
            if b is not None:
                texts.add(b)
        return texts

    def compute_pair_weights(
        self,
        zones: list[tuple[JoyTextZone, float]],
        radial_progress: float,
    ) -> dict[str, float]:
        """Compute per-pair CLIP interpolation weights from active zones.

        For each text pair in the global registry, the weight is the
        strength-weighted blend of each active zone's contribution:

            weight[pair] = Σ (zone_strength × zone.pair_weights[pair](progress))
                           ─────────────────────────────────────────────────
                                        Σ zone_strength

        This exactly matches the CLIPInterp formula:
        ``final = Σ (emb_b - emb_a) * weight_i``.

        Args:
            zones: List of ``(zone, strength)`` from :meth:`find_zones`.
            radial_progress: Stick deflection 0→1 (distance / max_range).

        Returns:
            Dict mapping pair_name → weight in [-1, 1].
        """
        # Initialize all pairs to zero
        weights: dict[str, float] = {name: 0.0 for name in self.text_pairs}

        if not zones:
            return weights

        total_strength = sum(s for _, s in zones)
        if total_strength <= 0.0:
            return weights

        for zone, strength in zones:
            w_zone = strength / total_strength
            for pair_name, rng in zone.pair_weights.items():
                lo, hi = rng
                weight = lo + (hi - lo) * max(0.0, min(1.0, radial_progress))
                weights[pair_name] += weight * w_zone

        return weights
