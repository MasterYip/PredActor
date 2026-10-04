"""JoyTextWBG — Joystick-driven text-conditioned whole-body guidance.

Composes three subsystems:
  - :class:`JoyStick` (or :class:`GUIJoyStick` fallback) for vx/vy/wz input
  - CLIP text encoder for semantic latent generation
  - :class:`WholeBodyGuidance` for per-axis guidance injection

At each control tick the joystick (vx, vy) position is mapped through a
:class:`JoyTextMapping` to determine which semantic zone(s) are active.
Zone text pairs are interpolated and blended to produce a CLIP ``motion_latent``
that is injected into the diffusion policy via ``inject_raw_keys``.

Usage (in eval config YAML)::

    task_cond_providers:
      joy_text_wbg:
        _target_: ...joy_text_wbg.JoyTextWBG
        mapping_path: config_files/joy_text_mappings/ps5_stand_walk_run.yaml
        clip_model_name: ViT-B/32
        clip_checkpoint: ${oc.env:HOME}/.../checkpoint_0100.pth.tar
        wbg_config:
          profile: g1_standard
          guidances:
            vx_guide: {enabled: true, range: [-1.5, 1.5]}
            ...
"""

from __future__ import annotations

import math
import threading
import time as _time
from pathlib import Path
from typing import Optional

import torch

try:
    import clip
    _CLIP_AVAILABLE = True
except ImportError:
    _CLIP_AVAILABLE = False

from diffusion_policy.task_provider.base import TaskCondProvider
from diffusion_policy.task_provider.whole_body_guidance.whole_body_guidance import WholeBodyGuidance
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.axes_vel import (
    VxGuidance, VyGuidance, VzGuidance, WzGuidance,
)
from diffusion_policy.task_provider.whole_body_guidance.guidance_types.hz_guide import HzGuidance
from diffusion_policy.utils.joy_teleop import JoyStick, GUIJoyStick
from .zone_mapping import JoyTextMapping, JoyTextZone


# ═══════════════════════════════════════════════════════════════════════════
# JoyTextWBG
# ═══════════════════════════════════════════════════════════════════════════

class JoyTextWBG(TaskCondProvider):
    """Joystick-driven text-conditioned whole-body guidance.

    Lifecycle (identical to all TaskCondProviders):
        ``start()``  → open joystick, launch GUI
        ``stop()``   → close joystick, destroy GUI
        ``inject_raw_keys(next_terms, batch_size)``
                     → called each env step; reads joystick, updates
                       guidance values and CLIP latent

    Args:
        mapping: :class:`JoyTextMapping` or path to a YAML mapping file.
        wbg: Existing :class:`WholeBodyGuidance` instance, or ``None`` to
            create one from *wbg_config*.
        wbg_config: Dict forwarded to ``WholeBodyGuidance(...)`` when *wbg*
            is ``None``.
        clip_model_name: CLIP variant (``"ViT-B/32"``, etc.).
        clip_checkpoint: Optional path to MotionCLIP fine-tuned checkpoint.
        device: Torch device for CLIP model.
        joystick_device: Linux evdev path (``/dev/input/js0``).
        joystick_type: ``"xbox"`` (default), ``"ps5"``, ``"ps4"``,
            ``"generic"``, or ``"beitong_kp20"``.
        max_linear_vel: Max linear velocity for joystick scaling (m/s).
        max_angular_vel: Max angular velocity for joystick scaling (rad/s).
        min_height: Min target height for height axis (m).
        max_height: Max target height for height axis (m).
        deadzone: Joystick deadzone threshold.
        gui_enabled: Launch the integrated GUI panel.
    """

    def __init__(
        self,
        mapping: JoyTextMapping | str | Path | None = None,
        mapping_path: str | Path | None = None,
        wbg: WholeBodyGuidance | None = None,
        wbg_config: dict | None = None,
        clip_model_name: str = "ViT-B/32",
        clip_checkpoint: str | None = None,
        device: str = "cuda:0",
        joystick_device: str = "/dev/input/js0",
        joystick_type: str = "xbox",
        max_linear_vel: float = 1.5,
        max_angular_vel: float = 1.0,
        min_height: float = 0.4,
        max_height: float = 1.4,
        deadzone: float = 0.05,
        gui_enabled: bool = True,
    ):
        if not _CLIP_AVAILABLE:
            raise ImportError(
                "CLIP is required for JoyTextWBG.  Install with: "
                "pip install git+https://github.com/openai/CLIP.git"
            )

        # ── Mapping ──────────────────────────────────────────────────────
        if mapping is None and mapping_path is not None:
            mapping = JoyTextMapping.from_yaml(mapping_path)
        if mapping is None:
            raise ValueError("Either mapping or mapping_path must be provided")
        if isinstance(mapping, (str, Path)):
            mapping = JoyTextMapping.from_yaml(mapping)
        self._mapping: JoyTextMapping = mapping

        self._device = device
        self._gui_enabled = gui_enabled

        # ── Joystick ─────────────────────────────────────────────────────
        self._joy = JoyStick(
            device=joystick_device,
            joystick_type=joystick_type,
            max_linear_vel=max_linear_vel,
            max_angular_vel=max_angular_vel,
            min_height=min_height,
            max_height=max_height,
            deadzone=deadzone,
        )
        self._use_hardware_joy = False  # set True if JoyStick.start() succeeds

        # Fallback GUI joystick (same API, tkinter sliders)
        self._gui_joy = GUIJoyStick(
            max_linear_vel=max_linear_vel,
            max_angular_vel=max_angular_vel,
            min_height=min_height,
            max_height=max_height,
        )

        # ── CLIP model ───────────────────────────────────────────────────
        print(f"[JoyTextWBG] Loading CLIP model: {clip_model_name} on {device}")
        self._clip_model, _ = clip.load(clip_model_name, device=device, jit=False)
        clip.model.convert_weights(self._clip_model)
        self._clip_model.eval()
        for p in self._clip_model.parameters():
            p.requires_grad = False

        if clip_checkpoint is not None:
            self._load_clip_checkpoint(clip_checkpoint)

        # Pre-encode all unique texts from mapping
        self._text_embeddings: dict[str, torch.Tensor] = {}
        for text in sorted(self._mapping.get_all_unique_texts()):
            self._text_embeddings[text] = self._encode_text(text)

        # Pre-compute pair diffs — CLIPInterp formula:
        #   final = normalize( Σ (emb_b - emb_a) * weight_i )
        # Diffs are RAW (NOT per-diff-normalized) — the magnitude of
        # (e_b - e_a) carries semantic distance. Only the final sum is L2-normalized.
        self._pair_diffs: dict[str, torch.Tensor] = {}
        for name, (text_a, text_b) in self._mapping.text_pairs.items():
            e_a = self._text_embeddings.get(text_a) if text_a else None
            e_b = self._text_embeddings.get(text_b) if text_b else None
            if e_a is not None and e_b is not None:
                diff = e_b - e_a
            elif e_b is not None:
                diff = e_b
            elif e_a is not None:
                diff = -e_a
            else:
                continue  # both None → skip
            self._pair_diffs[name] = diff

        # Interpolation mode — from mapping config
        self._interp_mode = self._mapping.interp_mode  # "interp" or "constant"

        # ── WholeBodyGuidance ────────────────────────────────────────────
        if wbg is not None:
            self._wbg = wbg
        elif wbg_config is not None:
            self._wbg = WholeBodyGuidance(**wbg_config)
        else:
            # Minimal default: vx, vy, wz enabled
            self._wbg = WholeBodyGuidance(
                guidances={
                    "vx_guide": {"enabled": True, "range": [-max_linear_vel, max_linear_vel]},
                    "vy_guide": {"enabled": True, "range": [-max_linear_vel, max_linear_vel]},
                    "wz_guide": {"enabled": True, "range": [-max_angular_vel, max_angular_vel]},
                },
                gui_enabled=False,  # We manage our own GUI
            )

        # ── Runtime state (thread-safe) ──────────────────────────────────
        self._lock = threading.Lock()
        self._current_latent: Optional[torch.Tensor] = None  # [1, cond_dim]
        self._active_zones: list[tuple[JoyTextZone, float]] = []
        self._current_guidance: dict[str, float] = {"vx": 0.0, "vy": 0.0, "wz": 0.0, "hz": 0.75}
        self._joystick_raw: dict[str, float] = {"vx": 0.0, "vy": 0.0, "wz": 0.0, "height": 0.75}
        self._joystick_connected: bool = False
        self._running: bool = False

        # ── GUI ──────────────────────────────────────────────────────────
        self._gui = None  # set by start()

        print(f"[JoyTextWBG] Ready — {len(self._mapping.zones)} zones, "
              f"{len(self._text_embeddings)} unique text embeddings")

    # ═════════════════════════════════════════════════════════════════════
    # TaskCondProvider interface
    # ═════════════════════════════════════════════════════════════════════

    def start(self) -> None:
        """Open joystick and launch the GUI."""
        if self._running:
            return

        # Try hardware joystick first, fall back to GUI joystick
        self._joy.start()
        self._use_hardware_joy = self._joy.is_connected()
        if not self._use_hardware_joy:
            print("[JoyTextWBG] Hardware joystick not available — using GUI joystick fallback")
            self._gui_joy.start()
        else:
            print(f"[JoyTextWBG] Hardware joystick connected")

        self._running = True

        # Launch integrated GUI on its own thread
        if self._gui_enabled:
            self._start_gui()

    def stop(self) -> None:
        """Close joystick and destroy GUI."""
        self._running = False
        self._joy.stop()
        self._gui_joy.stop()
        self._wbg.stop()
        if self._gui is not None:
            self._gui.stop()

    def inject_raw_keys(self, next_terms: dict, batch_size: int) -> None:
        """Called each environment step.

        Reads joystick, resolves zones, updates guidance values and CLIP
        latent, then writes ``motion_latent`` into *next_terms*.
        """
        if not self._running:
            return

        # 1. Read joystick
        self._read_joystick()

        # 2. Resolve zones → guidance + latent
        with self._lock:
            vx_raw = self._joystick_raw["vx"]
            vy_raw = self._joystick_raw["vy"]
            wz_raw = self._joystick_raw["wz"]
            height_raw = self._joystick_raw["height"]

        zones = self._mapping.find_zones(vx_raw, vy_raw)
        with self._lock:
            self._active_zones = zones

        vx_cmd, vy_cmd, wz_cmd = self._compute_guidance_values(zones, vx_raw, vy_raw, wz_raw)
        latent = self._compute_latent(zones)

        with self._lock:
            self._current_guidance = {"vx": vx_cmd, "vy": vy_cmd, "wz": wz_cmd, "hz": height_raw}
            self._current_latent = latent

        # 3. Push guidance values to WholeBodyGuidance
        self._set_guidance_values(vx_cmd, vy_cmd, wz_cmd, height_raw)

        # 4. Inject motion_latent into next_terms
        if next_terms:
            device = next(iter(next_terms.values())).device
            emb = latent.unsqueeze(1).expand(batch_size, 1, -1).to(device)  # [B, 1, D]
            next_terms["motion_latent"] = emb

    def get_task_cond(self, raw_history, batch_size, n_task_steps, device=None):
        """Legacy path: return [B, n_task_steps, cond_dim]."""
        with self._lock:
            latent = self._current_latent
        if latent is None:
            cond_dim = self._clip_model.text_projection.shape[1]
            latent = torch.zeros(1, cond_dim, device=self._device)
        result = latent.unsqueeze(1).expand(batch_size, n_task_steps, -1)  # [B, T, D]
        if device is not None:
            result = result.to(device)
        return result

    # ═════════════════════════════════════════════════════════════════════
    # Query API (for GUI)
    # ═════════════════════════════════════════════════════════════════════

    @property
    def mapping(self) -> JoyTextMapping:
        return self._mapping

    @property
    def wbg(self) -> WholeBodyGuidance:
        return self._wbg

    def get_active_zones(self) -> list[tuple[JoyTextZone, float]]:
        """Return list of ``(zone, strength)`` for the current joystick position."""
        with self._lock:
            return list(self._active_zones)

    def get_current_guidance(self) -> dict[str, float]:
        """Return ``{vx, vy, wz, hz}`` command values."""
        with self._lock:
            return dict(self._current_guidance)

    def get_joystick_raw(self) -> dict[str, float]:
        """Return raw joystick ``{vx, vy, wz, height}`` values."""
        with self._lock:
            return dict(self._joystick_raw)

    @property
    def joystick_connected(self) -> bool:
        return self._joy.is_connected()

    # ═════════════════════════════════════════════════════════════════════
    # Internals
    # ═════════════════════════════════════════════════════════════════════

    def _read_joystick(self) -> None:
        """Poll joystick and update cached values."""
        self._use_hardware_joy = self._joy.is_connected()
        if self._use_hardware_joy:
            vx, vy, wz, height = self._joy.get_cmd_vel()
        else:
            vx, vy, wz, height = self._gui_joy.get_cmd_vel()

        with self._lock:
            self._joystick_raw = {"vx": vx, "vy": vy, "wz": wz, "height": height}

    def _compute_guidance_values(
        self,
        zones: list[tuple[JoyTextZone, float]],
        vx_raw: float,
        vy_raw: float,
        wz_raw: float,
    ) -> tuple[float, float, float]:
        """Compute vx, vy, wz guidance values from active zones.

        Each zone contributes its scaled velocity, weighted by zone strength.
        The maximum strength across all zones is used to normalise the result
        so the dominant zone's full scale is preserved.
        """
        if not zones:
            return 0.0, 0.0, 0.0

        total_strength = sum(s for _, s in zones)
        if total_strength <= 0.0:
            return 0.0, 0.0, 0.0

        vx_total = 0.0
        vy_total = 0.0
        wz_total = 0.0

        for zone, strength in zones:
            w = strength / total_strength if total_strength > 0 else 0.0

            # vx: map raw vx through zone's velocity scale
            vx_lo, vx_hi = zone.velocity_scale
            # Compute zone-internal progress from joystick magnitude
            r = (vx_raw**2 + vy_raw**2) ** 0.5
            # Normalized progress within the zone's radial range (for wedge/annulus)
            progress = self._zone_radial_progress(zone, r)
            vx_zone = vx_lo + (vx_hi - vx_lo) * progress
            vx_zone *= (1.0 if vx_raw >= 0 else -1.0)  # preserve direction
            vx_total += vx_zone * w

            # vy: scale raw vy by zone's vy_scale
            vy_total += vy_raw * zone.vy_scale * w

            # wz: scale raw wz by zone's wz_scale
            wz_total += wz_raw * zone.wz_scale * w

        return vx_total, vy_total, wz_total

    @staticmethod
    def _zone_radial_progress(zone: JoyTextZone, r: float) -> float:
        """Compute 0→1 progress of joystick magnitude within a zone's radial range.

        For wedge and annulus regions this uses r_min/r_max.
        For disc this is 0 (no radial progress — uniform within disc).
        For rectangle this uses the distance from the origin.
        """
        from .zone_mapping import WedgeRegion, AnnulusRegion, DiscRegion

        region = zone.region
        if isinstance(region, (WedgeRegion, AnnulusRegion)):
            r_min = region.r_min
            r_max = region.r_max
            if r_max <= r_min:
                return 1.0 if r >= r_min else 0.0
            return max(0.0, min(1.0, (r - r_min) / (r_max - r_min)))
        elif isinstance(region, DiscRegion):
            # Within a disc, progress = distance relative to radius
            if region.radius <= 0:
                return 0.0
            return max(0.0, min(1.0, r / region.radius))
        else:
            # Rectangle / unknown: use radial position scaled to 1.0 max range
            return max(0.0, min(1.0, r))

    def _compute_latent(self, zones: list[tuple[JoyTextZone, float]]) -> torch.Tensor:
        """Compute CLIP latent from active zones.

        Two modes (set via ``interp_mode`` in mapping YAML):

        ``"interp"`` (default) — exact CLIPInterp formula:
            final = normalize( Σ diff_i * weight_i )
        where diff_i = emb_b - emb_a (raw, NOT per-diff-normalized) and
        weight_i in [-1, 1].  Only the final sum is L2-normalized.

        ``"constant"`` — debug mode: pick the dominant zone's strongest
        text_b embedding directly.  No interpolation.
        """
        if self._interp_mode == "constant":
            return self._compute_latent_constant(zones)

        # ── Interp mode: CLIPInterp formula ─────────────────────────────
        # Always resolve to a real embedding — the policy does not
        # understand zero vectors.  When no zones are active or all
        # weights are zero, return the "stand" embedding.
        stand = self._text_embeddings.get("stand")

        if not zones or not self._pair_diffs:
            return stand.clone() if stand is not None else self._zero_embedding()

        # Compute radial progress of the joystick for per-zone weight mapping
        vx_raw = self._joystick_raw.get("vx", 0.0)
        vy_raw = self._joystick_raw.get("vy", 0.0)
        r = math.hypot(vx_raw if vx_raw is not None else 0.0,
                       vy_raw if vy_raw is not None else 0.0)

        # Get blended per-pair weights from the mapping
        pair_weights = self._mapping.compute_pair_weights(zones, r)

        # CLIPInterp formula: sum diff_i * weight_i  (raw diffs, no per-diff norm)
        accumulated = torch.zeros(1, self._clip_model.text_projection.shape[1],
                                   device=self._device)
        for pair_name, diff in self._pair_diffs.items():
            weight = pair_weights.get(pair_name, 0.0)
            if weight != 0.0:
                accumulated = accumulated + diff * weight

        # L2-normalize the final sum.  If near-zero (all weights zero in
        # stand/idle), return raw "stand" embedding — never zero vector.
        final_norm = accumulated.norm(dim=-1, keepdim=True)
        if final_norm > 1e-6:
            accumulated = accumulated / final_norm
        elif stand is not None:
            accumulated = stand.clone()

        return accumulated

    def _compute_latent_constant(self, zones: list[tuple[JoyTextZone, float]]) -> torch.Tensor:
        """Constant mode: each zone maps to a single, fixed text embedding.

        If the zone has an explicit ``constant_text`` field in YAML, that
        embedding is used directly.  Otherwise the ``text_b`` of the dominant
        pair is used.  Falls back to "stand" when nothing matches.

        No diffs, no interpolation, no blend — pure per-zone identity.
        """
        # Always resolve to a real embedding — the policy does not
        # understand zero vectors.
        stand = self._text_embeddings.get("stand")

        if not zones:
            return stand.clone() if stand is not None else self._zero_embedding()

        zone, _strength = zones[0]

        # 1. Explicit constant_text in YAML
        if zone.constant_text and zone.constant_text in self._text_embeddings:
            return self._text_embeddings[zone.constant_text].clone()

        # 2. Derive from dominant pair: pick the pair with the largest
        #    positive max_weight → text_b is the "toward" direction
        if zone.pair_weights:
            best = max(zone.pair_weights.items(),
                       key=lambda kv: kv[1][1])  # largest max_weight
            pair_name, (_lo, hi) = best
            _text_a, text_b = self._mapping.text_pairs[pair_name]
            if text_b and text_b in self._text_embeddings:
                return self._text_embeddings[text_b].clone()

        # 3. Fallback
        return stand.clone() if stand is not None else self._zero_embedding()

    def _zero_embedding(self) -> torch.Tensor:
        """Last-resort zero embedding of the correct shape.  The policy does
        NOT understand this — it should only be reached if "stand" is also
        missing from the text registry."""
        cond_dim = self._clip_model.text_projection.shape[1]
        return torch.zeros(1, cond_dim, device=self._device)

    def _set_guidance_values(self, vx: float, vy: float, wz: float, height: float) -> None:
        """Push joystick commands to WholeBodyGuidance's per-axis instances."""
        manager = self._wbg._manager
        for g in manager.guidances:
            if isinstance(g, VxGuidance):
                g.set_value(vx)
            elif isinstance(g, VyGuidance):
                g.set_value(vy)
            elif isinstance(g, VzGuidance):
                pass  # vz not driven by joystick in current design
            elif isinstance(g, WzGuidance):
                g.set_value(wz)
            elif isinstance(g, HzGuidance):
                g.set_target(height)

    # ── CLIP helpers ──────────────────────────────────────────────────────

    def _encode_text(self, text: str) -> torch.Tensor:
        """Encode a single text string to a unit-norm embedding [1, D]."""
        tokens = clip.tokenize([text]).to(self._device)
        with torch.no_grad():
            emb = self._clip_model.encode_text(tokens).float()
        norm = emb.norm(dim=-1, keepdim=True)
        if norm > 0:
            emb = emb / norm
        return emb

    def _load_clip_checkpoint(self, checkpoint_path: str) -> None:
        print(f"[JoyTextWBG] Loading CLIP weights from: {checkpoint_path}")
        try:
            state_dict = torch.load(checkpoint_path, map_location=self._device)
            model_state = state_dict.get("model", state_dict)
            clip_state = {
                k.replace("clip_model.", ""): v
                for k, v in model_state.items()
                if k.startswith("clip_model.")
            }
            if not clip_state:
                print("[JoyTextWBG] Warning: no CLIP keys in checkpoint — using defaults")
                return
            missing, unexpected = self._clip_model.load_state_dict(clip_state, strict=False)
            if missing:
                print(f"[JoyTextWBG] Missing keys: {len(missing)}")
            if unexpected:
                print(f"[JoyTextWBG] Unexpected keys: {len(unexpected)}")
            print("[JoyTextWBG] Checkpoint CLIP weights loaded")
        except Exception as exc:
            print(f"[JoyTextWBG] Checkpoint load error: {exc} — using defaults")

    # ── GUI ───────────────────────────────────────────────────────────────

    def _start_gui(self) -> None:
        """Launch the integrated GUI panel in a background daemon thread."""
        import threading
        from .gui.joy_text_panel import JoyTextPanel

        def _run():
            self._gui = JoyTextPanel(self)
            self._gui.run()

        t = threading.Thread(target=_run, daemon=True, name="JoyTextWBG-GUI")
        t.start()

    # ── Context manager ───────────────────────────────────────────────────

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
