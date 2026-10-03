"""WholeBodyGuidance v2 — per-axis term-based whole-body guidance for co-diffusion.

Package structure::

    whole_body_guidance/
        body_groups.py              # G1 body constants
        body_selector.py            # BodyGroupSelector
        term_resolver.py            # TermResolver (was ObsTermIndex)
        kinematic_utils.py          # _build_simple_target, _build_target_trajectory
        guidance_activation_set.py  # GuidanceActivationSet dataclass
        guidance_base.py            # GuidanceBase ABC (delta-based)
        guidance_types/
            axes_vel.py             # VxGuidance, VyGuidance, VzGuidance, WzGuidance
            hz_guide.py             # HzGuidance (z-height)
            wrist_guide.py          # WristGuidance (per-side end-effector)
            vel_based.py            # VelBasedGuidance (backward-compat composite)
            pos_based.py            # PosBasedGuidance (backward-compat composite)
            point_reach.py          # PointReachGuidance
        guidance_activation_manager.py  # GuidanceActivationManager
        gui/                        # CustomTkinter GUI layer
        whole_body_guidance.py      # Thin WholeBodyGuidance facade
"""

from .whole_body_guidance import WholeBodyGuidance
from .term_resolver import TermResolver
from .body_selector import BodyGroupSelector
from .body_groups import G1_BODY_GROUPS, DEBUG
from .guidance_base import GuidanceBase
from .guidance_activation_set import GuidanceActivationSet
from .guidance_activation_manager import GuidanceActivationManager
from .guidance_types import (
    VelBasedGuidance, PosBasedGuidance, PointReachGuidance,
    VxGuidance, VyGuidance, VzGuidance, WzGuidance,
    HzGuidance, WristGuidance,
)
from importlib import import_module


_LAZY_JOY_TEXT = {
    "JoyTextWBG": (".joy_text_wbg", "JoyTextWBG"),
    "JoyTextMapping": (".joy_text_wbg", "JoyTextMapping"),
    "JoyTextZone": (".joy_text_wbg", "JoyTextZone"),
    "DiscRegion": (".joy_text_wbg.zone_mapping", "DiscRegion"),
    "WedgeRegion": (".joy_text_wbg.zone_mapping", "WedgeRegion"),
    "AnnulusRegion": (".joy_text_wbg.zone_mapping", "AnnulusRegion"),
    "RectangleRegion": (".joy_text_wbg.zone_mapping", "RectangleRegion"),
}


def __getattr__(name):
    if name not in _LAZY_JOY_TEXT:
        raise AttributeError(name)
    module_name, attribute = _LAZY_JOY_TEXT[name]
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value
