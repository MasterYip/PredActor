"""Root-position and root-velocity local trajectory guide with GUI velocity commands.

Provides planned future root_pos_local and root_lin_vel_local target trajectories
(3-d each: x, y, z) for the x-stream of co-diffusion actors.  A tkinter GUI
exposes independent settings blocks for position guidance and linear-velocity
guidance, each with its own enable checkbox, vx/vy sliders, and PD gain.

The position target trajectory, built in unnormalized physical space, is:

    target_x[t] = current_x + vx * dt * t
    target_y[t] = current_y + vy * dt * t
    target_z[t] = height

The velocity target is a constant [vx, vy, 0] across all horizon steps.

During diffusion sampling the x-stream is pulled toward the target with a
proportional correction:

    x_guided[t] = x_const[t] + kp * (target[t] - x_const[t]) * w[t]

where w[t] is a horizon weight ramp (0 for past steps, ramps to 1 over the
first few future steps, then holds at 1).

Standalone test::

    python -c "
    from diffusion_policy.task_provider.root_pos_guide import RootPosGuideProvider
    g = RootPosGuideProvider(); g.start()
    import time; time.sleep(30); g.stop()
    "
"""

from __future__ import annotations

import threading
from typing import Optional

import torch

try:
    import tkinter as tk
    from tkinter import ttk

    _TKINTER_AVAILABLE = True
except ImportError:
    _TKINTER_AVAILABLE = False


class RootPosGuideProvider:
    """GUI-controlled cmd-vel → future root_pos_local / root_lin_vel_local target.

    Two independent guidance modes, each with its own enable checkbox and settings:

    * Root Pos Guide — steers root_pos_local toward a position ramp built from
      vx, vy, height.  Has its own kp gain and z_guide toggle.
    * Root Lin Vel Guide — steers root_lin_vel_local toward the commanded
      [vx, vy, 0].  Has its own kp gain.

    Args:
        horizon:      Diffusion horizon (number of steps, e.g. 20).
        n_past_steps: Past observation steps; guidance weight is 0 here.
        ramp_steps:   Number of steps after n_past_steps over which the weight
                      ramps linearly from 0 to 1.  Remaining steps use w=1.
        dt:           Simulation time step per diffusion horizon step (s).
        kp_init:      Initial proportional gain for both modes (0 = off, 1 = fully guided).
        vx_range:     (min, max) for vx sliders (m/s).
        vy_range:     (min, max) for vy sliders (m/s).
        wz_range:     (min, max) for wz slider (rad/s, display only).
        height_range: (min, max) for height slider (m).
        height_init:  Initial height target (m).
        z_guide:      Whether to apply z-direction height guidance.  When False
                      the target uses the robot's current z position instead.
        device:       PyTorch device string.
    """

    def __init__(
        self,
        horizon: int = 20,
        n_past_steps: int = 4,
        ramp_steps: int = 4,
        dt: float = 0.02,
        kp_init: float = 1.0,
        vx_range: tuple = (-30.0, 30.0),
        vy_range: tuple = (-20.0, 20.0),
        wz_range: tuple = (-10.0, 10.0),
        height_range: tuple = (0.3, 1.1),
        height_init: float = 0.75,
        z_guide: bool = True,
        device: str = "cuda:0",
    ):
        self.horizon = horizon
        self.n_past_steps = n_past_steps
        self.dt = dt
        self.device = device

        # ── shared command state (written by GUI thread, read by inference thread) ──
        self._lock = threading.Lock()
        self._wz: float = 0.0

        # Position guidance state
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._height: float = height_init
        self._z_guide: bool = z_guide
        self._pos_guide_enabled: bool = True
        self._kp_pos: float = kp_init

        # Velocity guidance state (independent from position)
        self._vx_vel: float = 0.0
        self._vy_vel: float = 0.0
        self._vel_guide_enabled: bool = True
        self._kp_vel: float = kp_init

        # ── horizon weight: 0 for past, ramp, then 1 ──
        weights: list[float] = [0.0] * n_past_steps
        for i in range(ramp_steps):
            weights.append((i + 1) / ramp_steps)
        weights += [1.0] * max(0, horizon - len(weights))
        self._horizon_weight: torch.Tensor = torch.tensor(weights[:horizon], dtype=torch.float32)

        # ── GUI config ──
        self._vx_range = vx_range
        self._vy_range = vy_range
        self._wz_range = wz_range
        self._height_range = height_range
        self._height_init = height_init
        self._kp_init = kp_init

        self._gui_thread: Optional[threading.Thread] = None
        self._root_tk = None
        self._gui_started: bool = False

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    def _ensure_gui(self) -> None:
        """Lazily start the GUI on the first inference call (never during training)."""
        if self._gui_started:
            return
        self._gui_started = True
        self.start()

    def start(self) -> None:
        """Launch the GUI window in a daemon background thread."""
        if not _TKINTER_AVAILABLE:
            print("[RootPosGuide] tkinter not available — running headless (no GUI).")
            return
        self._gui_thread = threading.Thread(target=self._run_gui, daemon=True)
        self._gui_thread.start()

    def stop(self) -> None:
        """Destroy the GUI window if it is running."""
        if self._root_tk is not None:
            try:
                self._root_tk.quit()
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    # Command accessors
    # ──────────────────────────────────────────────────────────────────────────

    def get_cmd(self) -> tuple[float, float, float, float, float, bool]:
        """Return (vx, vy, wz, height, kp_pos, z_guide) thread-safely."""
        with self._lock:
            return self._vx, self._vy, self._wz, self._height, self._kp_pos, self._z_guide

    def get_vel_cmd(self) -> tuple[float, float]:
        """Return (vx_vel, vy_vel) thread-safely."""
        with self._lock:
            return self._vx_vel, self._vy_vel

    def get_kp_vel(self) -> float:
        """Return kp_vel thread-safely."""
        with self._lock:
            return self._kp_vel

    # ──────────────────────────────────────────────────────────────────────────
    # Trajectory building
    # ──────────────────────────────────────────────────────────────────────────

    def build_target_traj(
        self,
        last_pos_unnorm: torch.Tensor,  # [B, 3] — current root_pos_local (physical)
        normalizer=None,                # SingleFieldLinearNormalizer for 'obs' key
        norm_slice=None,                # optional (start, end) slice into normalizer dims
    ) -> torch.Tensor:
        """Build target root_pos_local trajectory in *normalized* space.

        Args:
            last_pos_unnorm: [B, 3] — current root_pos_local in physical units.
            normalizer:      If provided (``actor.normalizer['obs']``), the
                             target is normalized before returning.  When the
                             normalizer covers a multi-term obs vector, pass
                             *norm_slice* to index only the root-position dims.
            norm_slice:      Optional ``(start, end)`` tuple.  If given, only
                             the normalizer stats for that slice are used.

        Returns:
            target: [B, H, 3] — planned trajectory, normalized if *normalizer*
                    is given, otherwise in physical units.
        """
        vx, vy, _wz, height, _kp, z_guide = self.get_cmd()
        B = last_pos_unnorm.shape[0]
        H = self.horizon
        device = last_pos_unnorm.device

        # Steps relative to the "present" (index n_past_steps - 1).
        # Past steps get t=0 so the target sits at the current position;
        # future steps ramp forward from the present.
        rel_steps = torch.arange(H, dtype=torch.float32, device=device) - (self.n_past_steps - 1)
        rel_steps = rel_steps.clamp(min=0)

        target = torch.zeros(B, H, 3, device=device)
        # x: advance forward at vx m/s from current position
        target[:, :, 0] = last_pos_unnorm[:, 0:1] + vx * self.dt * rel_steps[None, :]
        # y: lateral at vy m/s from current position
        target[:, :, 1] = last_pos_unnorm[:, 1:2] + vy * self.dt * rel_steps[None, :]
        # z: commanded height (when z_guide is on), otherwise keep robot's current z
        target[:, :, 2] = height if z_guide else last_pos_unnorm[:, 2:3]

        if normalizer is not None:
            flat = target.reshape(B * H, 3)
            if norm_slice is not None:
                s, e = norm_slice
                scale = normalizer.params_dict['scale'][s:e]
                offset = normalizer.params_dict['offset'][s:e]
                flat_norm = flat * scale + offset
            else:
                flat_norm = normalizer.normalize(flat)
            target = flat_norm.reshape(B, H, 3)

        return target

    def apply_guidance(
        self,
        x_const: torch.Tensor,         # [B, H, 3] — current tiled x-stream (normalized)
        last_pos_unnorm: torch.Tensor,  # [B, 3] — current root_pos_local in physical units
        normalizer=None,
        norm_slice=None,               # optional (start, end) slice into normalizer dims
    ) -> torch.Tensor:
        """Apply PD correction: pull x_const toward target trajectory.

        x_guided[t] = x_const[t] + kp * (target[t] - x_const[t]) * w[t]

        Args:
            x_const:          [B, H, 3] — tiled constant x-stream (normalized).
            last_pos_unnorm:  [B, 3]    — physical current root position.
            normalizer:       SingleFieldLinearNormalizer for 'obs' to normalize target.
            norm_slice:       Optional (start, end) for multi-term normalizer dims.

        Returns:
            x_guided: [B, H, 3]
        """
        self._ensure_gui()
        _vx, _vy, _wz, _height, kp_pos, _z_guide = self.get_cmd()
        if kp_pos == 0.0 or not self._pos_guide_enabled:
            return x_const

        target = self.build_target_traj(last_pos_unnorm, normalizer=normalizer,
                                         norm_slice=norm_slice)

        w = self._horizon_weight.to(x_const.device)   # [H]
        err = target - x_const                         # [B, H, 3]
        return x_const + kp_pos * err * w[None, :, None]

    def build_vel_target(
        self,
        last_vel_unnorm: torch.Tensor,  # [B, 3] — current root_lin_vel_local (physical)
        normalizer=None,                # SingleFieldLinearNormalizer for 'obs' key
        norm_slice=None,                # optional (start, end) slice into normalizer dims
    ) -> torch.Tensor:
        """Build target root_lin_vel_local trajectory in *normalized* space.

        The velocity target is a constant [vx_vel, vy_vel, 0] across all horizon steps.
        """
        vx_vel, vy_vel = self.get_vel_cmd()
        B = last_vel_unnorm.shape[0]
        H = self.horizon
        device = last_vel_unnorm.device

        target = torch.zeros(B, H, 3, device=device)
        target[:, :, 0] = vx_vel
        target[:, :, 1] = vy_vel
        target[:, :, 2] = 0.0

        if normalizer is not None:
            flat = target.reshape(B * H, 3)
            if norm_slice is not None:
                s, e = norm_slice
                scale = normalizer.params_dict['scale'][s:e]
                offset = normalizer.params_dict['offset'][s:e]
                flat_norm = flat * scale + offset
            else:
                flat_norm = normalizer.normalize(flat)
            target = flat_norm.reshape(B, H, 3)

        return target

    def apply_vel_guidance(
        self,
        x_const_vel: torch.Tensor,       # [B, H, 3] — current root_lin_vel_local (normalized)
        last_vel_unnorm: torch.Tensor,   # [B, 3] — current root_lin_vel_local in physical units
        normalizer=None,
        norm_slice=None,                 # optional (start, end) slice into normalizer dims
    ) -> torch.Tensor:
        """Apply PD correction to root_lin_vel_local: pull toward commanded [vx_vel, vy_vel, 0].

        x_guided[t] = x_const[t] + kp_vel * (target[t] - x_const[t]) * w[t]
        """
        self._ensure_gui()
        kp_vel = self.get_kp_vel()
        if kp_vel == 0.0 or not self._vel_guide_enabled:
            return x_const_vel

        target = self.build_vel_target(last_vel_unnorm, normalizer=normalizer,
                                       norm_slice=norm_slice)

        w = self._horizon_weight.to(x_const_vel.device)  # [H]
        err = target - x_const_vel                        # [B, H, 3]
        return x_const_vel + kp_vel * err * w[None, :, None]

    # ──────────────────────────────────────────────────────────────────────────
    # GUI
    # ──────────────────────────────────────────────────────────────────────────

    def _run_gui(self) -> None:
        self._root_tk = tk.Tk()
        self._root_tk.title("Root Pos + Vel Guide")
        self._root_tk.resizable(False, False)

        def _make_slider(parent, label, from_, to, init, attr):
            """Create a labelled slider row, return (var, val_lbl)."""
            frame = tk.Frame(parent)
            frame.pack(fill="x", padx=10, pady=2)
            tk.Label(frame, text=label, width=5, anchor="w").pack(side="left")
            var = tk.DoubleVar(value=init)
            val_lbl = tk.Label(frame, text=f"{init:+.2f}", width=7, anchor="e")

            def _on_change(v, _attr=attr, _lbl=val_lbl, _var=var):
                val = _var.get()
                _lbl.config(text=f"{val:+.2f}")
                with self._lock:
                    setattr(self, f"_{_attr}", float(val))

            ttk.Scale(
                frame, from_=from_, to=to, variable=var,
                orient="horizontal", length=220,
                command=_on_change,
            ).pack(side="left", padx=4)
            val_lbl.pack(side="left")
            return var

        def _make_checkbox(parent, label, init, attr):
            """Create a labelled checkbox row, return var."""
            frame = tk.Frame(parent)
            frame.pack(fill="x", padx=10, pady=2)
            tk.Label(frame, text=label, width=14, anchor="w").pack(side="left")
            var = tk.BooleanVar(value=init)

            def _on_toggle(_var=var, _attr=attr):
                with self._lock:
                    setattr(self, f"_{_attr}", bool(_var.get()))

            tk.Checkbutton(frame, variable=var, command=_on_toggle).pack(side="left")
            return var

        # ======================================================================
        # Section 1 — Root Pos Guide
        # ======================================================================
        sep1 = tk.Frame(self._root_tk, height=2, bd=1, relief="sunken")
        sep1.pack(fill="x", padx=6, pady=(6, 2))

        pos_header = tk.Frame(self._root_tk)
        pos_header.pack(fill="x", padx=10, pady=2)
        tk.Label(pos_header, text="Root Pos Guide", font=("TkDefaultFont", 10, "bold"),
                 anchor="w").pack(side="left")
        _make_checkbox(pos_header, "", True, "pos_guide_enabled")

        _make_slider(self._root_tk, "vx", *self._vx_range, 0.0, "vx")
        _make_slider(self._root_tk, "vy", *self._vy_range, 0.0, "vy")
        _make_slider(self._root_tk, "h", *self._height_range, self._height_init, "height")
        _make_slider(self._root_tk, "kp", 0.0, 2.0, self._kp_init, "kp_pos")

        _make_checkbox(self._root_tk, "z guide", self._z_guide, "z_guide")

        # ======================================================================
        # Section 2 — Root Lin Vel Guide
        # ======================================================================
        sep2 = tk.Frame(self._root_tk, height=2, bd=1, relief="sunken")
        sep2.pack(fill="x", padx=6, pady=(8, 2))

        vel_header = tk.Frame(self._root_tk)
        vel_header.pack(fill="x", padx=10, pady=2)
        tk.Label(vel_header, text="Root Lin Vel Guide", font=("TkDefaultFont", 10, "bold"),
                 anchor="w").pack(side="left")
        _make_checkbox(vel_header, "", True, "vel_guide_enabled")

        _make_slider(self._root_tk, "vx", *self._vx_range, 0.0, "vx_vel")
        _make_slider(self._root_tk, "vy", *self._vy_range, 0.0, "vy_vel")
        _make_slider(self._root_tk, "kp", 0.0, 2.0, self._kp_init, "kp_vel")

        # ======================================================================
        # Shared — wz (display only)
        # ======================================================================
        sep3 = tk.Frame(self._root_tk, height=2, bd=1, relief="sunken")
        sep3.pack(fill="x", padx=6, pady=(8, 2))

        wz_header = tk.Frame(self._root_tk)
        wz_header.pack(fill="x", padx=10, pady=2)
        tk.Label(wz_header, text="Shared", font=("TkDefaultFont", 10, "bold"),
                 anchor="w").pack(side="left")

        _make_slider(self._root_tk, "wz", *self._wz_range, 0.0, "wz")

        # ======================================================================
        # Status bar
        # ======================================================================
        status_var = tk.StringVar(value="Ready")
        tk.Label(
            self._root_tk,
            textvariable=status_var,
            relief="sunken",
            anchor="w",
            padx=6,
            fg="gray30",
        ).pack(fill="x", side="bottom", padx=0, pady=(4, 0))

        def _tick():
            with self._lock:
                pg = self._pos_guide_enabled
                vg = self._vel_guide_enabled
                vx, vy, wz = self._vx, self._vy, self._wz
                vx_v, vy_v = self._vx_vel, self._vy_vel
                h, kp_p, zg = self._height, self._kp_pos, self._z_guide
                kp_v = self._kp_vel
            status_var.set(
                f"pos={pg}  vx={vx:+.1f} vy={vy:+.1f} h={h:.2f} kp={kp_p:.2f} zg={zg} | "
                f"vel={vg}  vx={vx_v:+.1f} vy={vy_v:+.1f} kp={kp_v:.2f} | "
                f"wz={wz:+.1f}"
            )
            self._root_tk.after(100, _tick)

        _tick()
        self._root_tk.mainloop()
