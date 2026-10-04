"""JoyTextWBG — Joystick-driven text-conditioned whole-body guidance.

Combines joystick input with CLIP text-embedding interpolation and per-axis
whole-body guidance into a single :class:`TaskCondProvider`.
"""

from .zone_mapping import (
    JoyTextMapping,
    JoyTextZone,
    ZoneRegion,
    DiscRegion,
    WedgeRegion,
    AnnulusRegion,
    RectangleRegion,
)
from .joy_text_wbg import JoyTextWBG

__all__ = [
    "JoyTextWBG",
    "JoyTextMapping",
    "JoyTextZone",
    "ZoneRegion",
    "DiscRegion",
    "WedgeRegion",
    "AnnulusRegion",
    "RectangleRegion",
]
