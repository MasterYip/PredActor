"""Joystick command adapters for WBG.

Hardware event parsing is canonicalized in ``joystick_parser.py``.  This
module preserves the historical ``JoyStick`` import and the GUI fallback.
"""

import threading
import time
from typing import Dict, Optional, Tuple

try:
    import tkinter as tk
    _TKINTER_AVAILABLE = True
except ImportError:
    _TKINTER_AVAILABLE = False

from diffusion_policy.utils.joystick_parser import VelocityJoystick

JoyStick = VelocityJoystick

class GUIJoyStick:
    """
    Software joystick that exposes the same interface as JoyStick but uses
    tkinter sliders instead of a hardware device.

    Intended as an automatic fallback when the hardware joystick cannot be
    opened.  The window shows four sliders:

        Vx  — forward/backward velocity  [-max_linear_vel, +max_linear_vel]
        Vy  — left/right velocity         [-max_linear_vel, +max_linear_vel]
        Wz  — yaw rate                    [-max_angular_vel, +max_angular_vel]
        Height — target root height       [min_height, max_height]

    The sliders snap back to zero (or mid-height) when you double-click the
    slider label button to the left of each track.

    Args:
        max_linear_vel:  Maximum linear velocity in m/s (default 1.5).
        max_angular_vel: Maximum angular velocity in rad/s (default 1.0).
        min_height:      Minimum target height in m (default 0.4).
        max_height:      Maximum target height in m (default 1.4).

    Usage (identical to JoyStick)::

        joy = GUIJoyStick()
        joy.start()
        vx, vy, wz, height = joy.get_cmd_vel()
        joy.stop()
    """

    def __init__(
        self,
        max_linear_vel: float = 1.5,
        max_angular_vel: float = 1.0,
        min_height: float = 0.4,
        max_height: float = 1.4,
    ):
        self.max_linear_vel = max_linear_vel
        self.max_angular_vel = max_angular_vel
        self.min_height = min_height
        self.max_height = max_height

        self._height_mid = (min_height + max_height) / 2.0
        self._lock = threading.Lock()
        self._vx = 0.0
        self._vy = 0.0
        self._wz = 0.0
        self._height = self._height_mid

        self._running = False
        self._root = None
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public interface (mirrors JoyStick)
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch the GUI window in a background daemon thread."""
        if not _TKINTER_AVAILABLE:
            print("[GUIJoyStick] tkinter unavailable — commands fixed at zero.")
            self._running = True
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_gui, daemon=True,
                                        name="GUIJoyStick")
        self._thread.start()
        time.sleep(0.3)  # let the window appear
        print("[GUIJoyStick] GUI joystick window opened (hardware joystick unavailable).")

    def stop(self) -> None:
        """Close the GUI and stop the background thread."""
        self._running = False
        if self._root is not None:
            try:
                self._root.quit()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._root = None

    def is_running(self) -> bool:
        return self._running

    def get_cmd_vel(self) -> Tuple[float, float, float, float]:
        """Return (vx, vy, wz, height) — same signature as JoyStick."""
        with self._lock:
            return self._vx, self._vy, self._wz, self._height

    def get_cmd(self) -> Dict:
        vx, vy, wz, height = self.get_cmd_vel()
        return {'vx': vx, 'vy': vy, 'wz': wz, 'height': height,
                'timestamp': time.time()}

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    # ------------------------------------------------------------------
    # Internal GUI
    # ------------------------------------------------------------------

    def _run_gui(self) -> None:
        self._root = tk.Tk()
        self._root.title("GUI Joystick (hardware not found)")
        self._root.resizable(False, False)

        # DoubleVars for each axis
        var_vx = tk.DoubleVar(value=0.0)
        var_vy = tk.DoubleVar(value=0.0)
        var_wz = tk.DoubleVar(value=0.0)
        var_h  = tk.DoubleVar(value=self._height_mid)

        tk.Label(self._root, text="GUI Joystick  (no hardware joystick)",
                 font=("Helvetica", 12, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(10, 6), padx=12)

        specs = [
            # (label,  var,    from_,                 to_,                  default,           update_fn)
            ("Vx (m/s)",  var_vx, -self.max_linear_vel,  self.max_linear_vel,  0.0,               lambda v: self._set("vx",  float(v))),
            ("Vy (m/s)",  var_vy, -self.max_linear_vel,  self.max_linear_vel,  0.0,               lambda v: self._set("vy",  float(v))),
            ("Wz (r/s)",  var_wz, -self.max_angular_vel, self.max_angular_vel, 0.0,               lambda v: self._set("wz",  float(v))),
            ("Height (m)", var_h, self.min_height,        self.max_height,      self._height_mid,  lambda v: self._set("h",   float(v))),
        ]

        pad = dict(padx=10, pady=5)
        self._value_labels = []

        for row, (name, var, lo, hi, default, cmd) in enumerate(specs, start=1):
            # Reset button double-click → snap back to default
            def _make_reset(v, d, fn):
                def _reset(_event=None):
                    v.set(d)
                    fn(d)
                return _reset

            btn = tk.Button(self._root, text=name, width=12, anchor="w",
                            relief=tk.FLAT, font=("Helvetica", 10))
            btn.bind("<Double-Button-1>", _make_reset(var, default, cmd))
            btn.grid(row=row, column=0, **pad)

            slider = tk.Scale(self._root, variable=var,
                              from_=lo, to=hi,
                              resolution=0.01, orient=tk.HORIZONTAL,
                              length=320, showvalue=False,
                              command=cmd)
            slider.grid(row=row, column=1, **pad)

            lbl = tk.Label(self._root, text=f"{default:+.2f}", width=8,
                           font=("Courier", 10), anchor="e")
            lbl.grid(row=row, column=2, **pad)
            self._value_labels.append((var, lbl))

        # Status bar
        self._status_var = tk.StringVar(value=self._status_text())
        tk.Label(self._root, textvariable=self._status_var,
                 font=("Courier", 9), fg="#444", relief=tk.SUNKEN,
                 anchor="w", padx=6).grid(
            row=len(specs) + 1, column=0, columnspan=3,
            sticky="ew", padx=10, pady=(2, 8))

        tk.Label(self._root, text="Double-click label to reset to 0",
                 font=("Helvetica", 8), fg="#777").grid(
            row=len(specs) + 2, column=0, columnspan=3, pady=(0, 6))

        self._root.after(200, self._refresh)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    def _set(self, axis: str, val: float) -> None:
        with self._lock:
            if axis == "vx":
                self._vx = val
            elif axis == "vy":
                self._vy = val
            elif axis == "wz":
                self._wz = val
            elif axis == "h":
                self._height = val

    def _status_text(self) -> str:
        with self._lock:
            return (f"vx={self._vx:+.2f}  vy={self._vy:+.2f}  "
                    f"wz={self._wz:+.2f}  h={self._height:.2f}")

    def _refresh(self) -> None:
        if not self._running or self._root is None:
            return
        # Update value labels
        if hasattr(self, '_value_labels'):
            for var, lbl in self._value_labels:
                lbl.config(text=f"{var.get():+.2f}")
        self._status_var.set(self._status_text())
        self._root.after(100, self._refresh)

    def _on_close(self) -> None:
        self._running = False
        self._root.quit()


def test_joystick():
    """Test joystick input."""
    print("Testing JoyStick...")
    print("Press Ctrl+C to exit")
    
    joy = JoyStick(joystick_type='xbox')
    joy.start()
    
    if not joy.is_running():
        print("Failed to start joystick")
        return
    
    try:
        while True:
            vx, vy, wz, height = joy.get_cmd_vel()
            print(f"\rVx: {vx:6.2f} m/s | Vy: {vy:6.2f} m/s | Wz: {wz:6.2f} rad/s | Height: {height:5.2f} m", end='')
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        joy.stop()


if __name__ == '__main__':
    test_joystick()
