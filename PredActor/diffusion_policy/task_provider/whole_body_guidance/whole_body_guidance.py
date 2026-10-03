"""WholeBodyGuidance v2 — thin facade with per-axis guidance decomposition.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from typing import Optional

import torch

from .term_resolver import TermResolver
from .body_groups import G1_BODY_GROUPS, DEBUG
from .guidance_activation_set import GuidanceActivationSet
from .guidance_activation_manager import GuidanceActivationManager
from .guidance_types.vel_based import VelBasedGuidance
from .guidance_types.pos_based import PosBasedGuidance
from .guidance_types.point_reach import PointReachGuidance
from .guidance_types.axes_vel import VxGuidance, VyGuidance, VzGuidance, WzGuidance
from .guidance_types.hz_guide import HzGuidance
from .guidance_types.wrist_guide import WristGuidance
from .destination_follow import (
    DestinationFollowConfig,
    DestinationFollowController,
    make_destination_guidance_class,
)
from .gui.gui_manager import GuiManager
from .gui.joystick_handle import JoystickHandle



def _to_plain(v):
    """Convert omegaconf/nested config values to plain Python types."""
    if hasattr(v, '_to_plain_dict'):
        return v
    # plain dicts / omegaconf DictConfig → recurse
    if isinstance(v, Mapping):
        if isinstance(v, dict):
            return {k: _to_plain(v2) for k, v2 in v.items()}
        return {k: _to_plain(v[k]) for k in v}
    # omegaconf ListConfig → plain list
    if hasattr(v, '__iter__') and not isinstance(v, (str, bytes, tuple)):
        try:
            return [_to_plain(item) for item in v]
        except Exception:
            pass
    return v

# ── Default guided terms per guidance type ────────────────────────────────
# Each per-axis guidance sets only the terms it actually modifies.
_AXIS_VEL_TERMS = [
    "body_pos_local", "body_lin_vel_local",
    "root_pos_local", "root_lin_vel_local",
]
_WZ_TERMS = [
    "body_pos_local", "body_lin_vel_local",
    "root_rot_local", "root_ang_vel_local",
]
_HZ_TERMS = ["root_pos_local", "body_pos_local"]
_WRIST_TERMS = ["body_pos_local"]
_FULL_KINEMATIC_TERMS = [
    "body_pos_local", "body_lin_vel_local",
    "root_pos_local", "root_lin_vel_local",
    "root_rot_local", "root_ang_vel_local",
]

# ── Default guided body groups ──────────────────────────────────────────
# vx guidance intentionally targets ONLY pelvis + torso_link (bodies {0, 9})
# to match the C++ deploy WBG; all other axes keep the full torso set.
_DEFAULT_GROUPS = ["torso"]
_DEFAULT_VX_GROUPS = ["pelvis_torso"]

# ── v1 → per-axis decomposition ──────────────────────────────────────────
_V1_DECOMPOSE = {
    "wholebody_pos_vel_guide": ["vx_guide", "vy_guide", "vz_guide", "wz_guide"],
    "root_posvel_guide":       ["vx_guide", "vy_guide"],
    "wholebody_pos_guide":     ["hz_guide"],
    "point_reach_guide":       ["point_reach"],
}


class WholeBodyGuidance:
    """Term-aware composite guidance with per-axis independence.

    v2: Each DOF (vx, vy, vz, wz, hz, left_wrist, right_wrist) is an
    independent :class:`GuidanceBase` with its own activation set, kp gain,
    body groups, and enable switch.  The manager sums deltas so superposition
    is mathematically clean.
    """

    def __init__(
        self,
        profile: str = "g1_standard",
        guidances: list[dict] | dict | None = None,
        horizon: int = 20,
        n_past_steps: int = 4,
        dt: float = 0.02,
        kp_init: float = 1.0,
        vx_range: tuple = (-5.0, 5.0),
        vy_range: tuple = (-4.0, 4.0),
        wz_range: tuple = (-2.0, 2.0),
        vz_range: tuple = (-2.0, 2.0),
        gui_enabled: bool = True,
        mode: str = "simple",
        body_groups_config: dict | None = None,
        guidance_mode: str = "classifier",
        denoising_steps: int = 20,
        enable_zeta_comp: bool = True,
        enable_damping_comp: bool = True,
        joystick=None,  # optional hardware JoyStick source (additive, opt-in)
        destination_follow_config: dict | None = None,
    ):
        if mode not in ("simple", "integration"):
            raise ValueError(f"mode must be 'simple' or 'integration', got '{mode}'")
        if guidance_mode not in ("classifier", "pd"):
            raise ValueError(f"guidance_mode must be 'classifier' or 'pd', got '{guidance_mode}'")

        self._term_resolver = TermResolver(profile)
        self._kp_init = kp_init
        self._v1_ranges = (vx_range, vy_range, vz_range, wz_range)
        self._v1_body_groups = body_groups_config

        # Hardware joystick command source (see set_joystick_source /
        # enable_joystick).  ``hz`` stays ``None`` until a joystick tick (or an
        # hz guidance target) provides an absolute height.
        self._joystick = joystick
        self._joystick_owned = False
        self._joystick_command = {"vx": 0.0, "vy": 0.0, "wz": 0.0, "hz": None}

        guidance_instances = self._build_guidances(guidances, kp_init)

        # Destination follow is always available as a disabled guidance. This
        # keeps the web UI usable with both legacy point-reach configs and the
        # current per-axis configs without changing checkpoint tensor shapes.
        destination_cfg = _to_plain(destination_follow_config or {})
        destination_enabled = bool(destination_cfg.pop("enabled", False))
        try:
            destination_controller_cfg = DestinationFollowConfig(**destination_cfg)
        except TypeError as exc:
            raise ValueError(f"invalid destination_follow_config: {exc}") from exc
        self.destination_follow = DestinationFollowController(
            destination_controller_cfg, enabled=destination_enabled)
        destination_activation = self._make_activation(
            {"enabled": destination_enabled, "kp": kp_init,
             "guided_terms": [], "body_groups": {"guided": []}}, kp_init,
            guidance_key="destination_follow")
        DestinationGuidance = make_destination_guidance_class()
        self._destination_guidance = DestinationGuidance(
            destination_activation, self.destination_follow)
        guidance_instances.append(self._destination_guidance)
        self._destination_saved_axis_state: dict[int, tuple[bool, float]] | None = None
        self._destination_batch_active = False
        self._destination_axis_update_seq = 0
        self._destination_axis_updated_at_ns: int | None = None

        self._manager = GuidanceActivationManager(
            guidances=guidance_instances,
            mode=mode,
            guidance_mode=guidance_mode,
            denoising_steps=denoising_steps,
            dt=dt,
            n_past_steps=n_past_steps,
            horizon=horizon,
            enable_zeta_comp=enable_zeta_comp,
            enable_damping_comp=enable_damping_comp,
            kp_init=kp_init,
        )
        if destination_enabled:
            self.enable_destination_follow(True)

        self._gui_enabled = gui_enabled
        # Small handle so the GUI can drive the joystick source without
        # holding a reference to this whole facade.
        self._joy_handle = JoystickHandle(self)
        self._gui = GuiManager(
            self._manager,
            term_resolver=self._term_resolver,
            gui_enabled=gui_enabled,
            joystick=self._joy_handle,
            destination_follow_owner=self,
        )

        if DEBUG:
            self._print_debug_summary()

        if gui_enabled:
            self._gui.start()

    # ── Config parsing ────────────────────────────────────────────────────

    def _build_guidances(
        self,
        guidances_config,
        kp_init: float,
    ) -> list:
        """Parse v1 or v2 config into a flat list of GuidanceBase instances."""
        v2 = self._normalize_config(guidances_config)
        vx_r, vy_r, vz_r, wz_r = self._v1_ranges
        instances: list = []

        # Per-guidance default terms — each guidance only modifies a subset
        # of the observation.  Using _FULL_KINEMATIC_TERMS everywhere is
        # harmless (extra terms are skipped in compute_gradient) but clutters
        # the debug-panel term list.
        _DEFAULT_TERMS = {
            "vx_guide": _AXIS_VEL_TERMS,
            "vy_guide": _AXIS_VEL_TERMS,
            "vz_guide": _AXIS_VEL_TERMS,
            "wz_guide": _WZ_TERMS,
            "hz_guide": _HZ_TERMS,
            "left_wrist_guide": _WRIST_TERMS,
            "right_wrist_guide": _WRIST_TERMS,
            "point_reach": _FULL_KINEMATIC_TERMS,
        }

        for key, cfg in v2.items():
            # Always instantiate every configured guidance — the user can
            # enable / disable from the GUI Activation Manager.  Skipping
            # them here would mean they never appear in the GUI at all.
            enabled_in_config = bool(cfg.get("enabled", True))

            # Inject the correct default guided_terms for this guidance type
            # if not explicitly specified in the config.
            if "guided_terms" not in cfg:
                cfg["guided_terms"] = _DEFAULT_TERMS.get(key, _FULL_KINEMATIC_TERMS)

            activation = self._make_activation(cfg, kp_init, guidance_key=key)
            # Override the activation's enabled flag from the dataclass
            # default so the user sees their configured intent on startup.
            activation.enabled = enabled_in_config

            if key == "vx_guide":
                instances.append(VxGuidance(activation,
                    value_range=tuple(cfg.get("range", list(vx_r)))))
            elif key == "vy_guide":
                instances.append(VyGuidance(activation,
                    value_range=tuple(cfg.get("range", list(vy_r)))))
            elif key == "vz_guide":
                instances.append(VzGuidance(activation,
                    value_range=tuple(cfg.get("range", list(vz_r)))))
            elif key == "wz_guide":
                instances.append(WzGuidance(activation,
                    value_range=tuple(cfg.get("range", list(wz_r)))))
            elif key == "hz_guide":
                instances.append(HzGuidance(activation,
                    z_range=tuple(cfg.get("z_range", [0.3, 1.1])),
                    z_init=cfg.get("z_init", 0.75)))
            elif key == "left_wrist_guide":
                instances.append(WristGuidance(activation, side="left",
                    dx_range=tuple(cfg.get("dx_range", [-0.5, 0.5])),
                    dy_range=tuple(cfg.get("dy_range", [-0.5, 0.5])),
                    dz_range=tuple(cfg.get("dz_range", [-0.3, 0.3]))))
            elif key == "right_wrist_guide":
                instances.append(WristGuidance(activation, side="right",
                    dx_range=tuple(cfg.get("dx_range", [-0.5, 0.5])),
                    dy_range=tuple(cfg.get("dy_range", [-0.5, 0.5])),
                    dz_range=tuple(cfg.get("dz_range", [-0.3, 0.3]))))
            elif key == "point_reach":
                instances.append(PointReachGuidance(activation,
                    vx_range=tuple(cfg.get("vx_range", list(vx_r))),
                    vy_range=tuple(cfg.get("vy_range", list(vy_r))),
                    vz_range=tuple(cfg.get("vz_range", list(vz_r))),
                    wz_range=tuple(cfg.get("wz_range", list(wz_r))),
                    kp_pos=cfg.get("kp_pos", 2.0),
                    target_x_range=tuple(cfg.get("target_x_range", [-3.0, 3.0])),
                    target_y_range=tuple(cfg.get("target_y_range", [-3.0, 3.0])),
                    target_z_range=tuple(cfg.get("target_z_range", [0.0, 2.0])),
                    target_init=tuple(cfg.get("target_init", [0.0, 0.0, 0.8]))))
            else:
                print(f"[WholeBodyGuidance] Unknown guidance key '{key}', skipping")

        return instances

    def _normalize_config(self, guidances_config) -> dict:
        """Convert v1 list format to v2 dict format.

        Accepts plain ``dict``, ``omegaconf.DictConfig`` (a ``Mapping``),
        or v1-style ``list[dict]``.
        """
        if guidances_config is None:
            return {"vx_guide": {"enabled": False}}

        # Already v2 dict/Mapping format (keys like "vx_guide", "hz_guide", etc.)
        is_mapping = isinstance(guidances_config, Mapping)
        if is_mapping:
            # Check if any key looks like a v2 guidance key
            v2_keys = {"vx_guide", "vy_guide", "vz_guide", "wz_guide",
                       "hz_guide", "left_wrist_guide", "right_wrist_guide",
                       "point_reach", "vel_guidance", "pos_guidance"}
            cfg_keys = set(k for k in guidances_config
                          if isinstance(k, str) and not k.startswith("_"))
            if cfg_keys & v2_keys:
                return {k: _to_plain(v) for k, v in guidances_config.items()}
            # Fall through: may be an omegaconf dict that is actually v1

        # v1 list format: [{type: "wholebody_pos_vel_guide", terms: [...]}]
        if (isinstance(guidances_config, (list, tuple))
                and len(guidances_config) > 0):
            first = guidances_config[0]
            if not isinstance(first, dict) or "type" not in first:
                return {"vx_guide": {"enabled": False}}

            v2: dict = {}
            default_groups = (self._v1_body_groups or {}).get("guided", _DEFAULT_GROUPS)
            vx_r, vy_r, vz_r, wz_r = self._v1_ranges

            for gc in guidances_config:
                gtype = gc["type"]
                terms = gc.get("terms", _FULL_KINEMATIC_TERMS)

                if gtype == "point_reach_guide":
                    v2["point_reach"] = {
                        "enabled": True, "kp": self._kp_init, "kp_pos": 2.0,
                        "vx_range": list(vx_r), "vy_range": list(vy_r),
                        "vz_range": list(vz_r), "wz_range": list(wz_r),
                        "target_init": [0.0, 0.0, 0.8],
                        "guided_terms": terms, "body_groups": {"guided": default_groups},
                    }
                elif gtype in ("wholebody_pos_guide",):
                    v2["hz_guide"] = {
                        "enabled": True, "kp": self._kp_init,
                        "z_init": 0.75, "z_range": [0.3, 1.1],
                        "guided_terms": terms if terms else _HZ_TERMS,
                        "body_groups": {"guided": default_groups},
                    }
                else:
                    # wholebody_pos_vel_guide, root_posvel_guide → decompose
                    for axis_key in _V1_DECOMPOSE.get(gtype, ["vx_guide", "vy_guide", "vz_guide", "wz_guide"]):
                        if axis_key == "point_reach":
                            continue  # handled above
                        rng = {"vx_guide": vx_r, "vy_guide": vy_r,
                               "vz_guide": vz_r, "wz_guide": wz_r}.get(axis_key, vx_r)
                        axis_terms = _WZ_TERMS if axis_key == "wz_guide" else (_AXIS_VEL_TERMS if terms == _FULL_KINEMATIC_TERMS else terms)
                        axis_groups = (self._v1_body_groups or {}).get(
                            "guided", _DEFAULT_VX_GROUPS if axis_key == "vx_guide"
                            else _DEFAULT_GROUPS)
                        v2[axis_key] = {
                            "enabled": True, "kp": self._kp_init,
                            "range": list(rng),
                            "guided_terms": axis_terms,
                            "body_groups": {"guided": axis_groups},
                        }

            return v2

        return {"vx_guide": {"enabled": False}}

    def _make_activation(self, cfg: dict, kp_init: float,
                         guidance_key: Optional[str] = None) -> GuidanceActivationSet:
        """Build a GuidanceActivationSet from a single guidance config block.

        When no body group is configured explicitly, ``vx_guide`` defaults to
        the ``pelvis_torso`` group (bodies ``{0, 9}`` only) to match the C++
        deploy WBG; every other guidance defaults to the full ``torso`` group.
        """
        bg_cfg = cfg.get("body_groups", {})
        if isinstance(bg_cfg, Mapping) and "guided" in bg_cfg:
            guided_groups = list(bg_cfg["guided"])
        else:
            default = _DEFAULT_VX_GROUPS if guidance_key == "vx_guide" else _DEFAULT_GROUPS
            guided_groups = list((self._v1_body_groups or {}).get("guided", default))

        guided_terms = cfg.get("guided_terms", _FULL_KINEMATIC_TERMS)
        if hasattr(guided_terms, '__iter__') and not isinstance(guided_terms, str):
            guided_terms = list(guided_terms)
        else:
            guided_terms = list(_FULL_KINEMATIC_TERMS)

        return GuidanceActivationSet(
            guided_terms=guided_terms,
            guided_body_groups=guided_groups,
            group_intensities={
                g: (1.0 if g in guided_groups else 0.0)
                for g in sorted(G1_BODY_GROUPS.keys())
            },
            kp=float(cfg.get("kp", kp_init)),
            enabled=bool(cfg.get("enabled", True)),
        )

    # ── Public API (identical to v1) ──────────────────────────────────────

    @property
    def guidance_mode(self) -> str:
        return self._manager.guidance_mode

    @property
    def mode(self) -> str:
        return self._manager.mode

    def compute_cost_gradient(
        self, state_norm: torch.Tensor, emphasis_mat_inv: torch.Tensor,
    ) -> torch.Tensor:
        gradient = self._manager.compute_cost_gradient(
            state_norm, emphasis_mat_inv, self._term_resolver)
        if getattr(self, 'runtime_telemetry_enabled', False):
            self._telemetry_gradient = gradient.detach()
            self._telemetry_calls = getattr(self, '_telemetry_calls', 0) + 1
        return gradient

    def get_zeta(
        self,
        state_t: torch.Tensor,
        state_t_prev: torch.Tensor | None = None,
    ) -> torch.Tensor:
        zeta = self._manager.get_zeta(state_t, state_t_prev)
        if (getattr(self, 'runtime_telemetry_enabled', False)
                and getattr(self, '_telemetry_calls', 0) % 25 == 1
                and hasattr(self, '_telemetry_gradient')):
            gradient = self._telemetry_gradient
            delta = gradient * zeta.to(gradient.device)[..., None]
            self.runtime_telemetry = {
                'gradient_calls': self._telemetry_calls,
                'gradient_l2': float(gradient.float().norm().item()),
                'guided_state_delta_l2': float(delta.float().norm().item()),
                'finite': bool(torch.isfinite(delta).all().item()),
            }
        return zeta

    def apply(self, state_unnorm: torch.Tensor, step: int) -> None:
        self._ensure_gui()
        self._manager.apply_pd(state_unnorm, self._term_resolver)

    def set_normalizer(self, normalizer) -> None:
        self._manager.set_normalizer(normalizer)

    def set_world_body_pos(
        self, pelvis_pos=None, left_wrist_pos=None, right_wrist_pos=None,
        root_yaw=0.0, root_pos=None,
    ) -> None:
        pr = self._manager.get_point_reach_guidance()
        if pr is not None:
            pr.set_world_body_pos(pelvis_pos, left_wrist_pos, right_wrist_pos, root_yaw, root_pos)
        self.destination_follow.set_pose(root_pos, root_yaw)
        self._sync_destination_axis_commands()

    def get_point_target(self) -> dict:
        pr = self._manager.get_point_reach_guidance()
        if pr is not None:
            return pr.get_point_target()
        return {"x": 0.0, "y": 0.0, "z": 0.0, "has_world_data": False}

    # ── World-frame destination follow ───────────────────────────────────

    def set_destination_target(self, target) -> None:
        self.destination_follow.set_target(target)
        self._sync_destination_axis_commands()

    def set_destination_config(self, values: dict) -> None:
        """Update destination-follow gains/limits through the runtime UI."""
        self.destination_follow.set_config(values)
        self._sync_destination_axis_commands()

    def enable_destination_follow(self, enabled: bool = True) -> None:
        """Route auto-follow through the configured WBG velocity axes."""
        if enabled and self._destination_saved_axis_state is None:
            axes = self._destination_axes()
            self._destination_saved_axis_state = {
                id(g): (bool(g.activation.enabled), g.get_value()) for g in axes
            }
            for guidance in axes:
                guidance.activation.enabled = True
        self.destination_follow.set_enabled(enabled)
        self._destination_guidance.activation.enabled = bool(enabled)
        if enabled:
            self._sync_destination_axis_commands()
        else:
            self.clear_destination_batch_commands()
            self._restore_destination_axis_state()

    def set_destination_batch_commands(self, commands) -> None:
        """Route vector benchmark commands through the configured WBG axes."""
        if self.mode != "simple":
            raise RuntimeError("destination batch commands require simple guidance mode")
        if (not isinstance(commands, torch.Tensor)
                or commands.ndim != 2 or commands.shape[1] != 3):
            raise ValueError("destination batch command must have shape [num_envs, 3]")
        if not self._destination_guidance.activation.enabled:
            self.enable_destination_follow(True)
        for guidance in self._destination_axes():
            column = (0 if isinstance(guidance, VxGuidance)
                      else 1 if isinstance(guidance, VyGuidance) else 2)
            guidance.set_batch_value(commands[:, column])
        self._destination_batch_active = True

    def clear_destination_batch_commands(self) -> None:
        for guidance in self._destination_axes():
            guidance.clear_batch_value()
        self._destination_batch_active = False
        self._sync_destination_axis_commands()

    def cancel_destination_follow(self) -> None:
        """Cancel and clear auto-follow without changing manual axis settings."""
        self.destination_follow.cancel()
        self._destination_guidance.activation.enabled = False
        self.clear_destination_batch_commands()
        self._restore_destination_axis_state()

    def _destination_axes(self) -> list:
        return [g for g in self._manager.guidances
                if isinstance(g, (VxGuidance, VyGuidance, WzGuidance))]

    def _sync_destination_axis_commands(self) -> None:
        if not self._destination_guidance.activation.enabled or self._destination_batch_active:
            return
        command = self.destination_follow.command()
        for guidance in self._destination_axes():
            if isinstance(guidance, VxGuidance):
                guidance.set_value(command.vx)
            elif isinstance(guidance, VyGuidance):
                guidance.set_value(command.vy)
            else:
                guidance.set_value(command.wz)
        self._destination_axis_update_seq += 1
        self._destination_axis_updated_at_ns = time.monotonic_ns()

    def _restore_destination_axis_state(self) -> None:
        if self._destination_saved_axis_state is None:
            return
        for guidance in self._destination_axes():
            saved = self._destination_saved_axis_state.get(id(guidance))
            if saved is not None:
                guidance.activation.enabled, value = saved
                guidance.set_value(value)
        self._destination_saved_axis_state = None

    def destination_follow_snapshot(self) -> dict:
        return self.destination_follow.snapshot()

    def destination_axis_snapshot(self) -> dict:
        """Expose the exact velocity-axis values consumed by WBG.

        Controller limits and the ranges displayed by the GUI are separate
        concepts.  This snapshot intentionally reports both, so benchmark
        evidence can prove whether a command was changed after the destination
        controller routed it into the WBG axes.
        """
        result = {}
        for guidance in self._destination_axes():
            axis = (
                "vx" if isinstance(guidance, VxGuidance)
                else "vy" if isinstance(guidance, VyGuidance)
                else "wz"
            )
            result[axis] = {
                "value": guidance.get_effective_value(),
                "configured_range": tuple(float(value) for value in guidance.value_range),
                "configured_range_role": "manual_slider_only",
                "active_range": (tuple(getattr(self.destination_follow.config, axis + "_range"))
                                 if self._destination_guidance.activation.enabled
                                 else tuple(guidance.value_range)),
                "enabled": bool(guidance.activation.enabled),
                "kp": float(guidance.activation.kp),
                "update_seq": self._destination_axis_update_seq,
                "updated_at_monotonic_ns": self._destination_axis_updated_at_ns,
            }
        return result

    def get_cmd(self) -> tuple:
        """Composite command: velocities from active vx/vy/vz/wz guidances."""
        if self._destination_guidance.activation.enabled:
            command = self.destination_follow.command()
            return command.vx, command.vy, 0.0, command.wz, self._kp_init, True
        vx = vy = vz = wz = 0.0
        enabled = False
        for g in self._manager.guidances:
            if isinstance(g, VxGuidance):
                vx = g.get_value()
                enabled = enabled or g.activation.enabled
            elif isinstance(g, VyGuidance):
                vy = g.get_value()
                enabled = enabled or g.activation.enabled
            elif isinstance(g, VzGuidance):
                vz = g.get_value()
                enabled = enabled or g.activation.enabled
            elif isinstance(g, WzGuidance):
                wz = g.get_value()
                enabled = enabled or g.activation.enabled
        return vx, vy, vz, wz, self._kp_init, enabled

    def get_composite_command(self) -> tuple:
        """Composite command incl. hz: ``(vx, vy, vz, wz, hz, kp, enabled)``.

        Parallel accessor to :meth:`get_cmd` (which keeps its 6-tuple
        signature) — adds the current hz target so joystick consumers can see
        the full ``{vx, vy, wz, hz}`` command.  ``hz`` is ``None`` when no
        :class:`HzGuidance` is configured.
        """
        vx, vy, vz, wz, kp, enabled = self.get_cmd()
        hz = None
        for g in self._manager.guidances:
            if isinstance(g, HzGuidance):
                hz = g.get_target()
                break
        return vx, vy, vz, wz, hz, kp, enabled

    # ── Hardware joystick source (additive, opt-in) ──────────────────────

    def set_joystick_source(self, joy, owned: bool = False) -> None:
        """Attach an external ``JoyStick`` instance, or ``None`` to detach.

        When set, :meth:`update_joystick` reads ``get_cmd_vel()`` each tick and
        drives vx/vy/wz (``set_value``) and hz (``set_target``) directly,
        bypassing the text-zone mapping.  ``owned=True`` makes :meth:`stop`
        close the joystick; an external instance (``owned=False``) is left to
        its owner so the non-joystick command path is never disturbed.
        """
        self._joystick = joy
        self._joystick_owned = bool(owned)

    def enable_joystick(
        self,
        device: str = "/dev/input/js0",
        joystick_type: str = "xbox",
        max_linear_vel: float = 1.5,
        max_angular_vel: float = 1.0,
        min_height: float = 0.4,
        max_height: float = 1.2,
        deadzone: float = 0.10,
    ) -> bool:
        """Open a hardware joystick and start using it as the command source.

        Shares the ``JoyStick`` instantiation convention with ``JoyTextWBG``
        and the deploy sender. Returns ``True`` once the fail-safe reader and
        reconnect supervisor are armed; use :meth:`is_joystick_connected` to
        distinguish a currently open device. Guidance remains unchanged until
        a device connects.

        ``deadzone`` (default 0.10) zeroes stick deflection below the
        threshold so a released stick reads exactly 0.0 despite drift.
        """
        from diffusion_policy.utils.joy_teleop import JoyStick
        ranges = {
            "vx": (-max_linear_vel, max_linear_vel),
            "vy": (-max_linear_vel, max_linear_vel),
            "wz": (-max_angular_vel, max_angular_vel),
            "height": (min_height, max_height),
        }
        for guidance in self._manager.guidances:
            if isinstance(guidance, VxGuidance):
                ranges["vx"] = tuple(guidance.value_range)
            elif isinstance(guidance, VyGuidance):
                ranges["vy"] = tuple(guidance.value_range)
            elif isinstance(guidance, WzGuidance):
                ranges["wz"] = tuple(guidance.value_range)
            elif isinstance(guidance, HzGuidance):
                ranges["height"] = tuple(guidance.z_range)
        joy = JoyStick(
            device=device,
            joystick_type=joystick_type,
            max_linear_vel=max_linear_vel,
            max_angular_vel=max_angular_vel,
            min_height=min_height,
            max_height=max_height,
            deadzone=deadzone,
            vx_range=ranges["vx"],
            vy_range=ranges["vy"],
            wz_range=ranges["wz"],
            height_range=ranges["height"],
        )
        joy.start()
        self.set_joystick_source(joy, owned=True)
        return joy.is_running()

    def update_joystick(self) -> dict:
        """Read the joystick once and apply it to the guidance instances.

        vx/vy/wz → per-axis ``set_value`` (re-mapped onto each guidance's
        ``value_range``); hz → :meth:`HzGuidance.set_target` (the joystick
        height axis is already an absolute height within
        [min_height, max_height]).  Returns the last applied
        ``{"vx","vy","wz","hz"}``.
        """
        joy = self._joystick
        if joy is None:
            return self.get_joystick_command()
        connected_fn = getattr(joy, "is_connected", None) or getattr(joy, "is_running", None)
        connected = bool(connected_fn and connected_fn())
        if not connected:
            return self.get_joystick_command()
        vx, vy, wz, height = joy.get_cmd_vel()
        self._apply_joystick(vx, vy, wz, height)
        return self.get_joystick_command()

    def get_joystick_command(self) -> dict:
        """Last applied joystick command ``{"vx","vy","wz","hz"}`` (copied)."""
        return dict(self._joystick_command)

    def is_joystick_connected(self) -> bool:
        """True when a joystick source is attached and currently running."""
        joy = self._joystick
        if joy is None:
            return False
        connected_fn = getattr(joy, "is_connected", None) or getattr(joy, "is_running", None)
        return bool(connected_fn and connected_fn())

    def _apply_joystick(self, vx: float, vy: float, wz: float, height: float) -> None:
        """Push a joystick ``(vx, vy, wz, height)`` sample into the guidances.

        The canonical parser receives each configured guidance range, so its
        output already uses the same units and endpoints as the tkinter
        sliders (defaults: vx ±5, vy ±4, wz ±2). These values are clamped once
        more at the guidance boundary. Legacy external joystick sources that
        do not expose ``command_ranges`` retain the historical max-based
        rescaling path. Height is clamped to the configured ``HzGuidance``
        range.
        """
        joy = self._joystick
        command_ranges = getattr(joy, "command_ranges", None)
        lin_max = float(getattr(joy, "max_linear_vel", None) or 1.5)
        ang_max = float(getattr(joy, "max_angular_vel", None) or 1.0)

        scaled = {"vx": float(vx), "vy": float(vy), "wz": float(wz), "hz": float(height)}
        for g in self._manager.guidances:
            if isinstance(g, VxGuidance):
                scaled["vx"] = (self._clamp_to_range(vx, g.value_range) if command_ranges
                                else self._scale_axis_to_range(vx, lin_max, g.value_range))
                g.set_value(scaled["vx"])
            elif isinstance(g, VyGuidance):
                scaled["vy"] = (self._clamp_to_range(vy, g.value_range) if command_ranges
                                else self._scale_axis_to_range(vy, lin_max, g.value_range))
                g.set_value(scaled["vy"])
            elif isinstance(g, WzGuidance):
                scaled["wz"] = (self._clamp_to_range(wz, g.value_range) if command_ranges
                                else self._scale_axis_to_range(wz, ang_max, g.value_range))
                g.set_value(scaled["wz"])
            elif isinstance(g, HzGuidance):
                scaled["hz"] = self._clamp_to_range(height, g.z_range)
                g.set_target(scaled["hz"])
        self._joystick_command = scaled

    @staticmethod
    def _clamp_to_range(value: float, value_range) -> float:
        lo, hi = map(float, value_range)
        return max(lo, min(hi, float(value)))

    @staticmethod
    def _scale_axis_to_range(value: float, joy_max: float, value_range) -> float:
        """Map a joystick axis value onto a guidance's ``value_range``.

        ``value`` is expected within ``[-joy_max, joy_max]``; it is normalized
        to [-1, 1] and mapped onto ``[value_range[0], value_range[1]]`` with 0
        kept at 0 (neutral → exactly 0.0).  Asymmetric ranges map each side to
        its own limit.
        """
        lo, hi = float(value_range[0]), float(value_range[1])
        if not joy_max or joy_max <= 0:
            return float(value)
        norm = max(-1.0, min(1.0, float(value) / joy_max))
        if norm >= 0:
            return norm * hi
        return norm * (-lo)

    def _ensure_gui(self) -> None:
        self._gui.start()

    def start(self) -> None:
        self._gui.start()

    def stop(self) -> None:
        if self._joystick_owned and self._joystick is not None:
            try:
                self._joystick.stop()
            except Exception:
                pass
            self._joystick = None
            self._joystick_owned = False
        self._manager.stop()
        self._gui.stop()

    @property
    def _has_point_reach(self) -> bool:
        return self._manager.has_point_reach

    @property
    def _has_destination_follow(self) -> bool:
        """Whether the always-present destination-follow adapter can receive pose data."""
        return self._destination_guidance is not None

    def _print_debug_summary(self) -> None:
        names = [g.guidance_name for g in self._manager.guidances]
        print(f"[WholeBodyGuidance v2] guidances=({len(names)}) {names}  "
              f"point_reach={self._has_point_reach}  mode={self.mode}")
