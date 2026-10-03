"""Motion reference teleoperation interface.

A tkinter GUI exposes slider groups for one or more 3-D vector task-condition
terms (e.g. ``ref_root_lin_vel_local``, ``ref_root_ang_vel_local``).  Each
term gets its own labelled row of three sliders.  At every policy step each
term's current value is injected directly into ``next_terms`` so that
``TermComposer.compose_cond()`` picks it up as a pre-computed key.

Configuration is driven by a ``terms`` list — each entry is a dict with:

.. code-block:: yaml

    terms:
      - name: ref_root_lin_vel_local
        label: "Root Lin Vel"
        dim_labels: ["vx", "vy", "vz"]
        ranges: [[-3.0, 3.0], [-3.0, 3.0], [-1.0, 1.0]]
        inits: [0.0, 0.0, 0.0]
      - name: ref_root_ang_vel_local
        label: "Root Ang Vel"
        dim_labels: ["wx", "wy", "wz"]
        ranges: [[-2.0, 2.0], [-2.0, 2.0], [-2.0, 2.0]]
        inits: [0.0, 0.0, 0.0]

**Backward-compatible single-term usage** — if ``terms`` is not provided the
old ``x_range`` / ``y_range`` / ``z_range`` / ``z_init`` parameters are still
accepted and internally converted to a single ``ref_root_lin_vel_local`` term.

Standalone test::

    python moref_teleop.py
"""

import threading
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from diffusion_policy.task_provider.base import TaskCondProvider

try:
    import tkinter as tk
    from tkinter import ttk  # noqa: F401 — imported for side-effects in subclasses
    _TKINTER_AVAILABLE = True
except ImportError:
    _TKINTER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _default_terms(x_range, y_range, z_range, z_init):
    """Convert old-style (x/y/z_range + z_init) to a single-term terms list."""
    return [
        {
            "name": "ref_root_lin_vel_local",
            "label": "Motion Reference Position",
            "dim_labels": ["X", "Y", "Z"],
            "ranges": [list(x_range), list(y_range), list(z_range)],
            "inits": [0.0, 0.0, float(z_init)],
        }
    ]


class MoRefTeleop(TaskCondProvider):
    """GUI slider-based multi-term 3-D vector task-condition provider.

    Each entry in *terms* produces three sliders (one per spatial dimension).
    At every ``inject_raw_keys`` call the current slider value for each term
    is written into *next_terms* under the term's ``name`` key as a tensor of
    shape ``[B, 1, 3]``, ready to be consumed directly by
    ``TermComposer.compose_cond()``.

    Args:
        terms: List of term-descriptor dicts.  Each dict must have:
            * ``name``       — raw-key name injected into next_terms.
            * ``label``      — section heading displayed in the GUI.
            * ``dim_labels`` — list of 3 axis labels (e.g. ``["vx","vy","vz"]``).
            * ``ranges``     — list of 3 ``[min, max]`` pairs.
            * ``inits``      — list of 3 initial values.
        resolution: Slider step resolution (default 0.01).
        window_title: Title of the GUI window.
        x_range, y_range, z_range, z_init: *Deprecated* — kept for backward
            compatibility when only a single position term is needed.
    """

    def __init__(
        self,
        terms: Optional[List[dict]] = None,
        resolution: float = 0.01,
        window_title: str = "Motion Reference Control",
        # ---- deprecated single-term params (backward compat) ----
        x_range: Tuple[float, float] = (-5.0, 5.0),
        y_range: Tuple[float, float] = (-5.0, 5.0),
        z_range: Tuple[float, float] = (0.0, 1.5),
        x_init: float = 0.0,
        y_init: float = 0.0,
        z_init: float = 0.0,
    ):
        if terms is None:
            terms = _default_terms(x_range, y_range, z_range, z_init)

        self._terms: List[dict] = terms
        self.resolution = resolution
        self.window_title = window_title

        self._lock = threading.Lock()
        # Current value for each term: list of np.ndarray(3,)
        self._values: List[np.ndarray] = [
            np.array(t.get("inits", [0.0, 0.0, 0.0]), dtype=np.float32)
            for t in self._terms
        ]

        self._root: Optional[tk.Tk] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # TaskCondProvider interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch the GUI in a background daemon thread."""
        if not _TKINTER_AVAILABLE:
            print("[MoRefTeleop] tkinter unavailable — running headless; "
                  "values fixed at initial values.")
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_gui, daemon=True,
                                        name="MoRefTeleop-GUI")
        self._thread.start()
        time.sleep(0.3)  # let the window appear

    def stop(self) -> None:
        """Close the GUI window and join the background thread."""
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

    def inject_raw_keys(self, next_terms: dict, batch_size: int) -> None:
        """Inject each term's current 3-D value (shape ``[B, 1, 3]``) into *next_terms*."""
        device = next(iter(next_terms.values())).device if next_terms else torch.device("cpu")
        with self._lock:
            vals = [v.copy() for v in self._values]
        for term_cfg, val in zip(self._terms, vals):
            ref = torch.from_numpy(val).float().unsqueeze(0).unsqueeze(0)  # [1, 1, 3]
            ref = ref.expand(batch_size, 1, 3).clone().to(device)
            next_terms[term_cfg["name"]] = ref

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_value(self, term_idx: int = 0) -> np.ndarray:
        """Return the current value of term *term_idx* as a ``(3,)`` float32 array."""
        with self._lock:
            return self._values[term_idx].copy()

    def set_value(self, term_idx: int, x: float, y: float, z: float) -> None:
        """Programmatically set the value of term *term_idx*."""
        with self._lock:
            self._values[term_idx][:] = [x, y, z]

    # Backward-compat aliases for single-term usage
    def get_ref_pos(self) -> np.ndarray:
        return self.get_value(0)

    def set_ref_pos(self, x: float, y: float, z: float) -> None:
        self.set_value(0, x, y, z)

    # ------------------------------------------------------------------
    # Internal GUI
    # ------------------------------------------------------------------

    def _run_gui(self) -> None:
        self._root = tk.Tk()
        self._root.title(self.window_title)
        self._root.resizable(False, False)

        pad = dict(padx=10, pady=3)

        # Per-term slider state
        self._tk_vars: List[List[tk.DoubleVar]] = []   # [term_idx][dim_idx]
        self._tk_lbls: List[List[tk.Label]] = []

        row = 0
        for ti, term_cfg in enumerate(self._terms):
            label     = term_cfg.get("label", term_cfg["name"])
            dim_labels = term_cfg.get("dim_labels", ["X", "Y", "Z"])
            ranges    = term_cfg.get("ranges", [[-5.0, 5.0]] * 3)
            inits     = term_cfg.get("inits", [0.0, 0.0, 0.0])

            # Section heading
            tk.Label(self._root, text=label,
                     font=("Helvetica", 11, "bold")).grid(
                row=row, column=0, columnspan=2, pady=(8, 2), sticky="w", padx=10)
            row += 1

            term_vars: List[tk.DoubleVar] = []
            term_lbls: List[tk.Label] = []
            for di, (dlbl, rng, init_val) in enumerate(zip(dim_labels, ranges, inits)):
                var = tk.DoubleVar(value=float(init_val))
                lbl = tk.Label(self._root, text=self._fmt(dlbl, init_val), width=16, anchor="w")
                slider = tk.Scale(
                    self._root, variable=var,
                    from_=float(rng[0]), to=float(rng[1]),
                    resolution=self.resolution, orient=tk.HORIZONTAL,
                    length=300, showvalue=False,
                    command=lambda v, _ti=ti, _di=di, _dl=dlbl: self._on_change(_ti, _di, _dl, float(v)),
                )
                lbl.grid(row=row, column=0, **pad)
                slider.grid(row=row, column=1, **pad)
                row += 1
                term_vars.append(var)
                term_lbls.append(lbl)

            self._tk_vars.append(term_vars)
            self._tk_lbls.append(term_lbls)

        # Reset button
        tk.Button(self._root, text="Reset All", command=self._on_reset,
                  width=12).grid(row=row, column=0, columnspan=2, pady=(6, 4))
        row += 1

        # Status bar
        self._status_var = tk.StringVar(value=self._status_text())
        tk.Label(self._root, textvariable=self._status_var, font=("Courier", 9),
                 fg="#333333", relief=tk.SUNKEN, anchor="w", padx=6).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))

        self._root.after(200, self._refresh_status)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    # ------------------------------------------------------------------
    # GUI callbacks
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt(axis: str, val: float) -> str:
        return f"{axis}:  {val:+.3f}"

    def _status_text(self) -> str:
        parts = []
        with self._lock:
            for term_cfg, val in zip(self._terms, self._values):
                name = term_cfg.get("label", term_cfg["name"])
                parts.append(f"{name}: ({val[0]:+.2f}, {val[1]:+.2f}, {val[2]:+.2f})")
        return "  |  ".join(parts)

    def _on_change(self, term_idx: int, dim_idx: int, dlbl: str, val: float) -> None:
        with self._lock:
            self._values[term_idx][dim_idx] = val
        self._tk_lbls[term_idx][dim_idx].config(text=self._fmt(dlbl, val))

    def _on_reset(self) -> None:
        with self._lock:
            for ti, term_cfg in enumerate(self._terms):
                inits = term_cfg.get("inits", [0.0, 0.0, 0.0])
                self._values[ti][:] = inits
        for ti, term_cfg in enumerate(self._terms):
            inits = term_cfg.get("inits", [0.0, 0.0, 0.0])
            dim_labels = term_cfg.get("dim_labels", ["X", "Y", "Z"])
            for di, (dlbl, v) in enumerate(zip(dim_labels, inits)):
                self._tk_vars[ti][di].set(float(v))
                self._tk_lbls[ti][di].config(text=self._fmt(dlbl, v))

    def _refresh_status(self) -> None:
        if self._root is None:
            return
        self._status_var.set(self._status_text())
        self._root.after(200, self._refresh_status)

    def _on_close(self) -> None:
        self._running = False
        if self._root is not None:
            self._root.quit()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

def _main() -> None:
    print("MoRefTeleop standalone test — move sliders, watch values (Ctrl+C to exit)\n")
    moref = MoRefTeleop(
        terms=[
            {
                "name": "ref_root_lin_vel_local",
                "label": "Root Lin Vel",
                "dim_labels": ["vx", "vy", "vz"],
                "ranges": [[-3.0, 3.0], [-3.0, 3.0], [-1.0, 1.0]],
                "inits": [0.0, 0.0, 0.0],
            },
            {
                "name": "ref_root_ang_vel_local",
                "label": "Root Ang Vel",
                "dim_labels": ["wx", "wy", "wz"],
                "ranges": [[-2.0, 2.0], [-2.0, 2.0], [-2.0, 2.0]],
                "inits": [0.0, 0.0, 0.0],
            },
        ]
    )
    moref.start()
    try:
        while True:
            lv = moref.get_value(0)
            av = moref.get_value(1)
            print(f"\r  linvel=({lv[0]:+.2f},{lv[1]:+.2f},{lv[2]:+.2f})"
                  f"  angvel=({av[0]:+.2f},{av[1]:+.2f},{av[2]:+.2f})", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        moref.stop()


if __name__ == "__main__":
    _main()

