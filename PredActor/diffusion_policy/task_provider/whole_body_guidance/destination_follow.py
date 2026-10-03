"""Conservative world-frame destination following for WBG evaluation.

The controller is deliberately independent of torch and the diffusion model.  It
turns a world-frame target and the latest root pose into body-frame velocity
commands, so the same math can be unit tested and used by the web UI.  When the
pose is unavailable, an enabled controller returns a zero command (fail closed).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
import threading
import time
from typing import Optional

MAX_TARGET_COORDINATE = 100.0
_CONFIG_FIELDS = {
    "kp_x", "kp_y", "kp_w", "kp_distance", "kp_lateral", "kp_heading",
    "vx_range", "vy_range", "wz_range", "max_vx", "max_vy", "max_wz",
    "min_forward_alignment",
    "heading_dead_zone", "arrival_radius", "rearm_radius",
}

def wrap_angle(angle: float) -> float:
    """Return *angle* in the half-open interval ``[-pi, pi)``."""
    return (float(angle) + math.pi) % (2.0 * math.pi) - math.pi


def map_target_between_root_frames(
    target,
    controller_root,
    controller_yaw,
    render_root,
    render_yaw,
) -> tuple[float, float, float]:
    """Map a controller-world target into the simulator render world.

    Deployable FK integrates its own root pose while MuJoCo renders the raw
    free-joint pose. The two world frames share the robot root as their anchor,
    so preserve the target's root-relative displacement across the frames.
    """
    points = []
    for value, name in ((target, "target"), (controller_root, "controller_root"),
                        (render_root, "render_root")):
        try:
            point = tuple(float(item) for item in value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must contain three finite numbers") from exc
        if len(point) != 3 or not all(math.isfinite(item) for item in point):
            raise ValueError(f"{name} must contain three finite numbers")
        points.append(point)
    target_point, controller_point, render_point = points
    controller_yaw = float(controller_yaw)
    render_yaw = float(render_yaw)
    if not math.isfinite(controller_yaw) or not math.isfinite(render_yaw):
        raise ValueError("root yaw values must be finite")

    dx = target_point[0] - controller_point[0]
    dy = target_point[1] - controller_point[1]
    yaw_delta = render_yaw - controller_yaw
    cos_delta, sin_delta = math.cos(yaw_delta), math.sin(yaw_delta)
    return (
        render_point[0] + cos_delta * dx - sin_delta * dy,
        render_point[1] + sin_delta * dx + cos_delta * dy,
        render_point[2] + target_point[2] - controller_point[2],
    )


def _clamp(value: float, value_range: tuple[float, float]) -> float:
    lower, upper = value_range
    return max(lower, min(upper, float(value)))


def _numeric(value, name: str) -> float:
    """Accept real numeric values while rejecting booleans and text coercion."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _output_range(value, name: str) -> tuple[float, float]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain two numeric bounds")
    try:
        lower, upper = value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain two numeric bounds") from exc
    lower, upper = _numeric(lower, name), _numeric(upper, name)
    if lower > upper:
        raise ValueError(f"{name} lower bound must be <= upper bound")
    if not lower <= 0.0 <= upper:
        raise ValueError(f"{name} must include zero")
    return lower, upper


@dataclass(frozen=True)
class DestinationFollowConfig:
    """Tunable, conservative destination-follow limits and gains."""

    # Canonical projected-distance gains. The *_distance/lateral/heading fields
    # below are accepted aliases for old YAML files and API clients.
    kp_x: float = 2.0
    kp_y: float = 0.8
    kp_w: float = 6.0
    max_vx: Optional[float] = None
    max_vy: Optional[float] = None
    max_wz: Optional[float] = None
    vx_range: Optional[tuple[float, float]] = (0.0, 8.0)
    vy_range: Optional[tuple[float, float]] = (-1.0, 1.0)
    wz_range: Optional[tuple[float, float]] = (-10.0, 10.0)
    min_forward_alignment: float = 0.25
    heading_dead_zone: float = 0.01
    arrival_radius: float = 0.30
    rearm_radius: float = 0.60
    kp_distance: Optional[float] = None
    kp_lateral: Optional[float] = None
    kp_heading: Optional[float] = None

    def __post_init__(self) -> None:
        for alias, canonical in (("kp_distance", "kp_x"),
                                 ("kp_lateral", "kp_y"),
                                 ("kp_heading", "kp_w")):
            value = getattr(self, alias)
            if value is not None:
                object.__setattr__(self, canonical, value)

        positive = {
            "kp_x": self.kp_x,
            "kp_y": self.kp_y,
            "kp_w": self.kp_w,
            "arrival_radius": self.arrival_radius,
            "rearm_radius": self.rearm_radius,
        }
        for name, value in positive.items():
            value = _numeric(value, name)
            if value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        for name in ("min_forward_alignment", "heading_dead_zone"):
            value = _numeric(getattr(self, name), name)
            if value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
        for axis in ("vx", "vy", "wz"):
            range_name, max_name = f"{axis}_range", f"max_{axis}"
            maximum = getattr(self, max_name)
            if maximum is not None:
                maximum = _numeric(maximum, max_name)
                if maximum < 0.0:
                    raise ValueError(f"{max_name} must be finite and non-negative")
                value_range = (-maximum, maximum)
            else:
                value_range = getattr(self, range_name)
                value_range = _output_range(value_range, range_name)
            object.__setattr__(self, range_name, value_range)
            object.__setattr__(self, max_name, max(abs(value_range[0]), abs(value_range[1])))
        if self.rearm_radius < self.arrival_radius:
            raise ValueError("rearm_radius must be >= arrival_radius")


@dataclass(frozen=True)
class DestinationFollowCommand:
    """One computed command and its inspectable status."""

    vx: float = 0.0
    vy: float = 0.0
    wz: float = 0.0
    status: str = "disabled"
    distance: Optional[float] = None
    heading_error: Optional[float] = None
    pose_available: bool = False

    def as_dict(self) -> dict:
        return {
            "vx": self.vx,
            "vy": self.vy,
            "wz": self.wz,
            "status": self.status,
            "distance": self.distance,
            "heading_error": self.heading_error,
            "pose_available": self.pose_available,
        }


class DestinationFollowController:
    """Thread-safe target/pose state and conservative heading-aware control.

    The target is expressed in world ``(x, y, z)`` coordinates.  Translation is
    computed in the robot's yaw-only body frame. The projected displacement
    components directly drive ``vx = dis_proj_x_dir * kp_x`` and
    ``vy = dis_proj_y_dir * kp_y``. Heading error drives ``wz = error * kp_w``
    outside a small dead zone. Arrival uses a radius plus a larger re-arm radius
    (hysteresis). The configurable ``vx_range``, ``vy_range``, and ``wz_range``
    values are the command limits; no additional fixed ceiling is applied.
    Legacy ``max_*`` values create symmetric ranges.
    """

    def __init__(self, config: DestinationFollowConfig | None = None, *, enabled: bool = False):
        self.config = config or DestinationFollowConfig()
        self._lock = threading.RLock()
        self._enabled = bool(enabled)
        self._target: Optional[tuple[float, float, float]] = None
        self._root_pos: Optional[tuple[float, float, float]] = None
        self._root_yaw: Optional[float] = None
        self._arrived = False
        self._last = DestinationFollowCommand()
        self._target_update_seq = 0
        self._pose_update_seq = 0
        self._target_updated_at_ns: Optional[int] = None
        self._pose_updated_at_ns: Optional[int] = None

    @staticmethod
    def _point(value, name: str) -> tuple[float, float, float]:
        try:
            values = tuple(float(v) for v in value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must contain three finite numbers") from exc
        if (len(values) != 3 or not all(math.isfinite(v) for v in values)
                or any(abs(v) > MAX_TARGET_COORDINATE for v in values)):
            raise ValueError(
                f"{name} must contain three finite numbers within +/-{MAX_TARGET_COORDINATE:g} m")
        return values

    def set_target(self, target) -> None:
        target = self._point(target, "target")
        with self._lock:
            self._target = target
            self._arrived = False
            self._last = DestinationFollowCommand(status="target_set")
            self._target_update_seq += 1
            self._target_updated_at_ns = time.monotonic_ns()

    def set_config(self, values: dict) -> None:
        """Atomically update finite, safety-validated runtime parameters.

        Algorithm values are not clamped to an arbitrary experiment range.
        Emitted commands are bounded by the configured per-axis ranges.
        """
        if not isinstance(values, dict) or not values:
            raise ValueError("destination config must be a non-empty mapping")
        unknown = set(values) - _CONFIG_FIELDS
        if unknown:
            raise ValueError(f"unknown destination config field(s): {', '.join(sorted(unknown))}")
        with self._lock:
            current = {name: getattr(self.config, name) for name in (
                "kp_x", "kp_y", "kp_w", "vx_range", "vy_range", "wz_range",
                "min_forward_alignment", "heading_dead_zone", "arrival_radius",
                "rearm_radius")}
            for axis in ("vx", "vy", "wz"):
                if f"{axis}_range" in values and f"max_{axis}" in values:
                    raise ValueError(f"set either {axis}_range or max_{axis}, not both")
            for name, value in values.items():
                if name.endswith("_range"):
                    current[name] = _output_range(value, name)
                    continue
                value = _numeric(value, name)
                canonical = {"kp_distance": "kp_x", "kp_lateral": "kp_y",
                             "kp_heading": "kp_w"}.get(name, name)
                if name.startswith("max_"):
                    if value < 0.0:
                        raise ValueError(f"{name} must be finite and non-negative")
                    axis = name.removeprefix("max_")
                    current[f"{axis}_range"] = (-value, value)
                else:
                    current[canonical] = value
            try:
                config = DestinationFollowConfig(**current)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            self.config = config
            # A changed arrival band must not leave an old latch active under
            # a newly configured target. The next sample recomputes status.
            self._arrived = False
            self._last = DestinationFollowCommand(status="config_updated")

    def clear_target(self) -> None:
        with self._lock:
            self._target = None
            self._arrived = False
            self._last = DestinationFollowCommand()
            self._target_update_seq += 1
            self._target_updated_at_ns = time.monotonic_ns()

    def set_enabled(self, enabled: bool) -> None:
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be boolean")
        with self._lock:
            self._enabled = enabled
            if not enabled:
                self._arrived = False
                self._last = DestinationFollowCommand()

    def cancel(self) -> None:
        """Disable following and clear the target; the next command is zero."""
        with self._lock:
            self._enabled = False
            self._target = None
            self._arrived = False
            self._last = DestinationFollowCommand()
            self._target_update_seq += 1
            self._target_updated_at_ns = time.monotonic_ns()

    def set_pose(self, root_pos=None, root_yaw=None) -> None:
        """Update the latest simulator root pose; invalid values are unavailable."""
        pose = None
        yaw = None
        try:
            if root_pos is not None:
                pose = self._point(root_pos, "root_pos")
            if root_yaw is not None and math.isfinite(float(root_yaw)):
                yaw = wrap_angle(float(root_yaw))
        except (TypeError, ValueError):
            pose, yaw = None, None
        with self._lock:
            self._root_pos, self._root_yaw = pose, yaw
            self._pose_update_seq += 1
            self._pose_updated_at_ns = time.monotonic_ns()

    def command(self) -> DestinationFollowCommand:
        """Compute one command, returning zero whenever safety prerequisites fail."""
        with self._lock:
            target, root, yaw = self._target, self._root_pos, self._root_yaw
            if not self._enabled:
                result = DestinationFollowCommand(status="disabled")
            elif target is None:
                result = DestinationFollowCommand(status="target_required")
            elif root is None or yaw is None:
                result = DestinationFollowCommand(status="waiting_for_pose")
            else:
                dx, dy = target[0] - root[0], target[1] - root[1]
                distance = math.hypot(dx, dy)
                if self._arrived:
                    if distance > self.config.rearm_radius:
                        self._arrived = False
                    else:
                        result = DestinationFollowCommand(
                            status="arrived", distance=distance, heading_error=0.0,
                            pose_available=True)
                        self._last = result
                        return result
                if distance <= self.config.arrival_radius:
                    self._arrived = True
                    result = DestinationFollowCommand(
                        status="arrived", distance=distance, heading_error=0.0,
                        pose_available=True)
                else:
                    desired_yaw = math.atan2(dy, dx)
                    heading_error = wrap_angle(desired_yaw - yaw)
                    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
                    dx_body = cos_y * dx + sin_y * dy
                    dy_body = -sin_y * dx + cos_y * dy
                    # Project world displacement into the yaw-only body frame.
                    # These components are the control signal directly; no
                    # alignment floor or normalized-distance heuristic is used.
                    dis_proj_x_dir = dx_body
                    dis_proj_y_dir = dy_body
                    vx = _clamp(dis_proj_x_dir * self.config.kp_x, self.config.vx_range)
                    vy = _clamp(dis_proj_y_dir * self.config.kp_y, self.config.vy_range)
                    wz = 0.0 if abs(heading_error) <= self.config.heading_dead_zone else _clamp(
                        heading_error * self.config.kp_w, self.config.wz_range)
                    result = DestinationFollowCommand(
                        vx=vx, vy=vy, wz=wz, status="active", distance=distance,
                        heading_error=heading_error, pose_available=True)
            self._last = result
            return result

    def snapshot(self) -> dict:
        with self._lock:
            # Recompute from the newest simulator pose so the UI status and
            # command telemetry never lag one control tick behind.
            result = self.command()
            return {
                "enabled": self._enabled,
                "target": list(self._target) if self._target is not None else None,
                "inputs": {
                    "target": list(self._target) if self._target is not None else None,
                    "root_pos": list(self._root_pos) if self._root_pos is not None else None,
                    "root_yaw": self._root_yaw,
                },
                "updates": {
                    "target_seq": self._target_update_seq,
                    "target_monotonic_ns": self._target_updated_at_ns,
                    "pose_seq": self._pose_update_seq,
                    "pose_monotonic_ns": self._pose_updated_at_ns,
                },
                "status": result.status,
                "distance": result.distance,
                "heading_error": result.heading_error,
                "pose_available": result.pose_available,
                "command": result.as_dict(),
                "config": {
                    "kp_x": self.config.kp_x,
                    "kp_y": self.config.kp_y,
                    "kp_w": self.config.kp_w,
                    # Legacy aliases remain in the payload for older UI/API
                    # clients; they mirror the canonical projected gains.
                    "kp_distance": self.config.kp_x,
                    "kp_lateral": self.config.kp_y,
                    "kp_heading": self.config.kp_w,
                    "max_vx": self.config.max_vx,
                    "max_vy": self.config.max_vy,
                    "max_wz": self.config.max_wz,
                    "vx_range": list(self.config.vx_range),
                    "vy_range": list(self.config.vy_range),
                    "wz_range": list(self.config.wz_range),
                    "min_forward_alignment": self.config.min_forward_alignment,
                    "heading_dead_zone": self.config.heading_dead_zone,
                    "arrival_radius": self.config.arrival_radius,
                    "rearm_radius": self.config.rearm_radius,
                },
                "safety_limits": {
                    "vx": list(self.config.vx_range),
                    "vy": list(self.config.vy_range),
                    "wz": list(self.config.wz_range),
                },
            }


def make_destination_guidance_class():
    """Build a status-only adapter; WBG axis guidances apply the commands."""
    from .guidance_base import GuidanceBase

    class _DestinationFollowGuidance(GuidanceBase):
        guidance_name = "destination_follow"

        def __init__(self, activation, controller: DestinationFollowController):
            super().__init__(activation)
            self.controller = controller

        def build_deltas(self, *args, **kwargs):
            return {}

        def get_cmd_summary(self):
            return self.controller.snapshot()

    return _DestinationFollowGuidance
