"""Task condition provider package.

Defines the common ``TaskCondProvider`` interface and concrete implementations
for conditioning a diffusion policy at evaluation time.

Available providers
-------------------
``TaskCondProvider``    Base interface — all providers inherit from this.
``ClipCondProvider``    Wraps CLIPTeleop or CLIPInterp (adapter for legacy classes).
``CompositeCondProvider``   Fan-out over multiple providers.
``CLIPTeleop``          Text-typed interactive CLIP embedding via stdin.
``CLIPInterp``          GUI slider-based semantic interpolation between CLIP embeddings.
``MoRefTeleop``         GUI slider-based motion reference root-position provider.
"""

from diffusion_policy.task_provider.base import (
    TaskCondProvider,
    ClipCondProvider,
    CompositeCondProvider,
)
from importlib import import_module


_LAZY_PROVIDERS = {
    "CLIPTeleop": (".clip_teleop", "CLIPTeleop"),
    "CLIPInterp": (".clip_interp", "CLIPInterp"),
    "MoRefTeleop": (".moref_teleop", "MoRefTeleop"),
    "G1RLObsStandardGuideProvider": (
        ".rlobs_standard_guide", "G1RLObsStandardGuideProvider"),
    "JoyTextWBG": (".whole_body_guidance.joy_text_wbg", "JoyTextWBG"),
}


def __getattr__(name):
    if name not in _LAZY_PROVIDERS:
        raise AttributeError(name)
    module_name, attribute = _LAZY_PROVIDERS[name]
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value

__all__ = [
    "TaskCondProvider",
    "ClipCondProvider",
    "CompositeCondProvider",
    "CLIPTeleop",
    "CLIPInterp",
    "MoRefTeleop",
    "G1RLObsStandardGuideProvider",
    "JoyTextWBG",
]
