"""Deterministic viewer camera tracking with no simulation-state writes."""

from dataclasses import dataclass
import math
from typing import Optional, Sequence, Tuple

import numpy as np


def quaternion_yaw_wxyz(quaternion: Sequence[float]) -> float:
    w, x, y, z = quaternion
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


@dataclass
class CameraFollower:
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    azimuth: float = 0.0
    follow_yaw: bool = False
    smoothing_tau: float = 0.0
    _lookat: Optional[np.ndarray] = None
    _azimuth: Optional[float] = None

    def __post_init__(self) -> None:
        if len(self.offset) != 3:
            raise ValueError("camera_lookat_offset must contain exactly 3 values")
        if self.smoothing_tau < 0.0:
            raise ValueError("camera_smoothing_tau must be non-negative")

    def reset(self) -> None:
        self._lookat = None
        self._azimuth = None

    def update(self, position: Sequence[float], quaternion: Sequence[float], dt: float):
        yaw = quaternion_yaw_wxyz(quaternion)
        offset = np.asarray(self.offset, dtype=np.float64)
        if self.follow_yaw:
            c, s = math.cos(yaw), math.sin(yaw)
            offset = np.array([c * offset[0] - s * offset[1], s * offset[0] + c * offset[1], offset[2]])
        desired_lookat = np.asarray(position, dtype=np.float64) + offset
        desired_azimuth = self.azimuth + (math.degrees(yaw) if self.follow_yaw else 0.0)
        if self._lookat is None or self.smoothing_tau == 0.0 or dt <= 0.0:
            self._lookat = desired_lookat
            self._azimuth = desired_azimuth
        else:
            alpha = 1.0 - math.exp(-dt / self.smoothing_tau)
            self._lookat += alpha * (desired_lookat - self._lookat)
            delta = (desired_azimuth - self._azimuth + 180.0) % 360.0 - 180.0
            self._azimuth += alpha * delta
        return self._lookat.copy(), float(self._azimuth)
