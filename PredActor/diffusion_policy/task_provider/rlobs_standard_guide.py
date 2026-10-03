"""GUI state guide for the 192-d g1_rlobs_standard_condcodiffuse x-stream.

This guide mirrors the joystick-style root command logic used in guided
DiffuseCLoC, but wraps it as a reusable provider for CondCoDiffuseActor.
It keeps the model-predicted body_pos_local/body_lin_vel_local channels and
overrides the future root pose and root velocity channels with a command-built
target trajectory before applying a proportional correction.
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


class G1RLObsStandardGuideProvider:
    """GUI-controlled guide for the 192-d body-kinematic co-diffusion state.

    Observation layout:
      body_pos_local      [0:90]
      body_lin_vel_local  [90:180]
      root_pos_local      [180:183]
      root_rot_local      [183:186]
      root_lin_vel_local  [186:189]
      root_ang_vel_local  [189:192]
    """

    ROOT_POS_SLICE = slice(180, 183)
    ROOT_ROT_SLICE = slice(183, 186)
    ROOT_LIN_VEL_SLICE = slice(186, 189)
    ROOT_ANG_VEL_SLICE = slice(189, 192)

    def __init__(
        self,
        horizon: int = 20,
        n_past_steps: int = 4,
        ramp_steps: int = 4,
        dt: float = 0.02,
        kp_init: float = 1.0,
        vx_range: tuple = (-3.0, 3.0),
        vy_range: tuple = (-1.5, 1.5),
        wz_range: tuple = (-2.0, 2.0),
        height_range: tuple = (0.3, 1.1),
        height_init: float = 0.75,
        device: str = "cuda:0",
    ):
        self.horizon = horizon
        self.n_past_steps = n_past_steps
        self.dt = dt
        self.device = device

        self._lock = threading.Lock()
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._wz: float = 0.0
        self._height: float = height_init
        self._kp: float = kp_init

        weights = [0.0] * n_past_steps
        for i in range(ramp_steps):
            weights.append((i + 1) / (ramp_steps + 1))
        weights += [1.0] * max(0, horizon - len(weights))
        self._horizon_weight = torch.tensor(weights[:horizon], dtype=torch.float32)

        self._vx_range = vx_range
        self._vy_range = vy_range
        self._wz_range = wz_range
        self._height_range = height_range
        self._height_init = height_init
        self._kp_init = kp_init

        self._gui_thread: Optional[threading.Thread] = None
        self._root_tk = None

    def start(self) -> None:
        if not _TKINTER_AVAILABLE:
            print("[G1RLObsStandardGuide] tkinter not available; running headless.")
            return
        self._gui_thread = threading.Thread(target=self._run_gui, daemon=True)
        self._gui_thread.start()

    def stop(self) -> None:
        if self._root_tk is not None:
            try:
                self._root_tk.quit()
            except Exception:
                pass

    def get_cmd(self) -> tuple[float, float, float, float, float]:
        with self._lock:
            return self._vx, self._vy, self._wz, self._height, self._kp

    def build_target_traj(self, state_traj_unnorm: torch.Tensor) -> torch.Tensor:
        vx, vy, wz, height, _kp = self.get_cmd()
        target = state_traj_unnorm.clone()

        n_plan_start = min(self.n_past_steps, target.shape[1])
        n_plan_steps = max(target.shape[1] - n_plan_start, 0)
        if n_plan_steps == 0:
            return target

        device = target.device
        dtype = target.dtype
        pos_x = torch.linspace(0.0, vx * self.dt * n_plan_steps, n_plan_steps, device=device, dtype=dtype)
        pos_y = torch.linspace(0.0, vy * self.dt * n_plan_steps, n_plan_steps, device=device, dtype=dtype)
        offset_x = vx * self.dt * (self.n_past_steps - n_plan_start)
        offset_y = vy * self.dt * (self.n_past_steps - n_plan_start)

        target[:, n_plan_start:, 180] = pos_x - offset_x
        target[:, n_plan_start:, 181] = pos_y - offset_y
        target[:, n_plan_start:, 182] = height

        target[:, n_plan_start:, self.ROOT_ROT_SLICE] = 0.0
        target[:, n_plan_start:, 186] = vx
        target[:, n_plan_start:, 187] = vy
        target[:, n_plan_start:, 188] = 0.0
        target[:, n_plan_start:, 189:191] = 0.0
        target[:, n_plan_start:, 191] = wz

        return target

    def apply_guidance(
        self,
        state_traj_pred: torch.Tensor,
        normalizer,
        emphasis_mat: torch.Tensor,
        emphasis_mat_inv: torch.Tensor,
    ) -> torch.Tensor:
        _vx, _vy, _wz, _height, kp = self.get_cmd()
        if kp == 0.0:
            return state_traj_pred
        if normalizer is None:
            raise RuntimeError("G1RLObsStandardGuideProvider requires an obs normalizer.")

        state_traj_unnorm = normalizer.unnormalize((state_traj_pred @ emphasis_mat_inv).detach())
        target_unnorm = self.build_target_traj(state_traj_unnorm)
        state_exp = normalizer.normalize(target_unnorm.detach()) @ emphasis_mat
        err = state_exp - state_traj_pred

        w = self._horizon_weight.to(device=state_traj_pred.device, dtype=state_traj_pred.dtype)
        return state_traj_pred + kp * err * w[None, :, None]

    def _run_gui(self) -> None:
        self._root_tk = tk.Tk()
        self._root_tk.title("G1 RLObs Standard Guide")
        self._root_tk.resizable(False, False)

        def make_row(label: str, from_: float, to: float, init: float, attr: str):
            frame = tk.Frame(self._root_tk)
            frame.pack(fill="x", padx=10, pady=3)
            tk.Label(frame, text=label, width=14, anchor="w").pack(side="left")
            var = tk.DoubleVar(value=init)
            val_lbl = tk.Label(frame, text=f"{init:+.2f}", width=7, anchor="e")

            def on_change(_value, _attr=attr, _label=val_lbl, _var=var):
                val = _var.get()
                _label.config(text=f"{val:+.2f}")
                with self._lock:
                    setattr(self, f"_{_attr}", float(val))

            ttk.Scale(
                frame,
                from_=from_,
                to=to,
                variable=var,
                orient="horizontal",
                length=240,
                command=on_change,
            ).pack(side="left", padx=4)
            val_lbl.pack(side="left")

        make_row("vx (m/s)", *self._vx_range, 0.0, "vx")
        make_row("vy (m/s)", *self._vy_range, 0.0, "vy")
        make_row("wz (rad/s)", *self._wz_range, 0.0, "wz")
        make_row("height (m)", *self._height_range, self._height_init, "height")
        make_row("kp", 0.0, 2.0, self._kp_init, "kp")

        status_var = tk.StringVar(value="Ready")
        tk.Label(
            self._root_tk,
            textvariable=status_var,
            relief="sunken",
            anchor="w",
            padx=6,
            fg="gray30",
        ).pack(fill="x", side="bottom", padx=0, pady=0)

        def tick():
            with self._lock:
                vx, vy, wz, h, kp = self._vx, self._vy, self._wz, self._height, self._kp
            status_var.set(f"vx={vx:+.2f}  vy={vy:+.2f}  wz={wz:+.2f}  h={h:.2f}  kp={kp:.2f}")
            self._root_tk.after(100, tick)

        tick()
        self._root_tk.mainloop()