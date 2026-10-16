#!/usr/bin/env python3
"""
CLIP semantic interpolation sender for C++ diffusion_deploy EnvRunner.

Sends a UDP stream of CLIP embeddings computed by the GUI-driven
CLIPInterp task-condition provider.  This is the deployment counterpart
of the ``clip_interp`` section inside the checkpoint config
(e.g. ``g1_cond_diffuse.yaml``).

Usage
-----
  python clip_interp_sender.py [OPTIONS]

Options
-------
  --host IP            C++ runner host            (default: 127.0.0.1)
  --port PORT          C++ cond_udp_port          (default: 9877)
  --cond-dim N         Conditioning dimension      (default: 512)
  --device DEV         CLIP inference device       (default: cpu)
  --model NAME         CLIP model name             (default: ViT-B/32)
  --checkpoint PATH    MotionCLIP checkpoint with fine-tuned CLIP weights
  --pairs TEXT         Comma-separated text pairs
                       e.g. "stand still:walk,walk:run,slow:fast"
                       Use "null" for the zero-vector sentinel.
  --normalize / --no-normalize
                       L2-normalize the final summed embedding (default: on)
  --interval S         Resend interval in seconds  (default: 0.1)
  --default-weight     Weight of the first slider at startup (default: 1.0)

How it works
------------
- A Tkinter GUI window opens with one slider per text pair.
- Each slider controls a weight **w** in [-1, 1].
- The sent embedding is:  sum( (e2 - e1) * w )  with optional normalization.
- The first slider defaults to **1.0** so the robot receives a meaningful
  embedding immediately (matching the common ``(null, "stand still")`` pattern).
"""

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
from typing import Optional

import numpy as np

# Reuse the singleton guard from clip_cond_sender (same lock port).
_LOCK_PORT = 9878


# ---------------------------------------------------------------------------
# UI scale resolution (HiDPI) — mirrors tools/wbg_guidance_sender.py so the
# two sender GUIs scale identically (elements + font, ×2.0 default).
# ---------------------------------------------------------------------------

def _detect_xft_dpi_scale():
    """Return a scale factor from Xft.dpi (dpi/96) when the X server declares
    it, else None.  Only meaningful on X11; Wayland has no Xft.dpi."""
    if not os.environ.get("DISPLAY"):
        return None
    try:
        out = subprocess.run(["xrdb", "-query"], capture_output=True,
                             text=True, timeout=2.0).stdout or ""
    except Exception:
        return None
    for line in out.splitlines():
        if line.strip().lower().startswith("xft.dpi"):
            try:
                dpi = float(line.split(":", 1)[1].strip())
            except (ValueError, IndexError):
                continue
            if dpi > 0:
                return round(max(1.0, dpi / 96.0), 2)
    return None


def resolve_ui_scale(cli_value, legacy_value, env_var, default=2.0):
    """Resolve the CLIP interp GUI scale factor.

    Priority (documented in the README):
      1. ``--ui-scale`` explicit CLI value.
      2. ``--scale`` legacy alias (kept for back-compat).
      3. ``env_var`` (``CLIP_INTERP_UI_SCALE``) environment override.
      4. Xft.dpi auto-detection when the display declares a scale > 100%.
      5. ``default`` = 2.0 (user-approved ×2.0 HiDPI default).

    The resolved factor is passed to ``CLIPInterp(scale=...)``, which multiplies
    window geometry, padding, and fonts by it.
    """
    if cli_value is not None:
        return max(1.0, float(cli_value))
    if legacy_value is not None:
        return max(1.0, float(legacy_value))
    env = os.environ.get(env_var)
    if env:
        try:
            return max(1.0, float(env))
        except ValueError:
            pass
    detected = _detect_xft_dpi_scale()
    if detected is not None and detected > 1.05:
        return detected
    return default


def _acquire_lock() -> socket.socket | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", _LOCK_PORT))
        return s
    except OSError:
        return None


def _ensure_single_sender() -> socket.socket:
    lock = _acquire_lock()
    if lock is None:
        print(f"[clip_interp_sender] ERROR: Another sender is already running "
              f"(port {_LOCK_PORT} is in use).", file=sys.stderr)
        print(f"  Kill it with:  fuser -k {_LOCK_PORT}/udp", file=sys.stderr)
        sys.exit(1)
    return lock


# ---------------------------------------------------------------------------
# UDP helpers
# ---------------------------------------------------------------------------

def _normalize(v: np.ndarray) -> np.ndarray:
    """L2-normalize *v* to unit norm; returns zeros unchanged."""
    n = float(np.linalg.norm(v))
    if n < 1e-9:
        return v
    return (v / n).astype(np.float32)


def _send(sock: socket.socket, host: str, port: int, emb: np.ndarray) -> None:
    emb_f32 = _normalize(emb.reshape(-1).astype(np.float32))
    sock.sendto(emb_f32.tobytes(), (host, port))


# ---------------------------------------------------------------------------
# InterpSender — thin wrapper around CLIPInterp with baseline weight support
# ---------------------------------------------------------------------------

class InterpSender:
    """Wraps ``CLIPInterp`` for deployment UDP streaming.

    On construction the first slider weight is set to *default_weight* so the
    robot receives a meaningful embedding right away (instead of the all-zeros
    that CLIPInterp produces when every slider is at zero).
    """

    def __init__(
        self,
        text_pairs: list,
        host: str = "127.0.0.1",
        port: int = 9877,
        cond_dim: int = 512,
        device: str = "cpu",
        clip_model_name: str = "ViT-B/32",
        checkpoint_path: Optional[str] = None,
        normalize: bool = True,
        default_weight: float = 1.0,
        interval: float = 0.1,
        scale: float = 1.0,
    ):
        self._host = host
        self._port = port
        self._interval = interval
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Import here so --help is fast even without CLIP installed.
        from diffusion_policy.task_provider.clip_interp import CLIPInterp

        self._interp = CLIPInterp(
            text_pairs=text_pairs,
            device=device,
            cond_dim=cond_dim,
            clip_model_name=clip_model_name,
            normalize=normalize,
            checkpoint_path=checkpoint_path,
            scale=scale,
        )

        # Monkey-patch so every embedding update wakes the sender immediately.
        self._changed = threading.Event()
        self._orig_update = self._interp._update_embedding
        self._interp._update_embedding = self._patched_update

        # Apply baseline weight to the first slider so we never send zeros.
        if default_weight != 0.0 and len(text_pairs) > 0:
            weights = [0.0] * len(text_pairs)
            weights[0] = float(default_weight)
            self._interp.set_weights(weights)
            print(f"[InterpSender] Baseline: slider[0] = {default_weight:.1f}")

        # Trigger an initial send.
        self._changed.set()

        # Start the Tkinter GUI in a background daemon thread.
        self._interp.start()

        self._stop_event = threading.Event()
        self._sender_thread: Optional[threading.Thread] = None

    def _patched_update(self) -> None:
        self._orig_update()
        self._changed.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin streaming the current interpolation embedding over UDP."""
        if self._sender_thread is not None:
            return

        self._stop_event.clear()
        self._sender_thread = threading.Thread(
            target=self._send_loop, daemon=True
        )
        self._sender_thread.start()
        print(f"[InterpSender] Streaming on change to {self._host}:{self._port}"
              f"  (heartbeat {self._interval:.2f}s)")
        print("[InterpSender] Use the GUI sliders to adjust conditioning.")

    def stop(self) -> None:
        """Stop streaming and close resources."""
        self._stop_event.set()
        if self._sender_thread is not None:
            self._sender_thread.join(timeout=2.0)
        self._interp.stop()
        try:
            self._sock.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_embedding(self) -> np.ndarray:
        t = self._interp.get_embedding(batch_size=1, n_cond_steps=1)
        return t[0, 0].float().cpu().numpy()

    def _send_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                emb = self._get_embedding()
                _send(self._sock, self._host, self._port, emb)
            except Exception as exc:
                print(f"[InterpSender] send error: {exc}")
            self._changed.wait(self._interval)
            self._changed.clear()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_pairs(pairs_str: str) -> list:
    """Parse ``"A:B,C:D"`` into ``[(A,B), (C,D)]``.  ``"null"`` → ``None``."""
    pairs = []
    for token in pairs_str.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            a, b = token.split(":", 1)
            a = a.strip() or None
            b = b.strip() or None
            pairs.append((a if a != "null" else None,
                          b if b != "null" else None))
    return pairs or [(None, "stand still")]


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CLIP semantic-interpolation UDP sender for C++ EnvRunner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--host",         default="127.0.0.1", help="Target host")
    p.add_argument("--port",         type=int, default=9877, help="Target UDP port")
    p.add_argument("--cond-dim",     type=int, default=512,  help="Conditioning dimension")
    p.add_argument("--device",       default="cpu",          help="CLIP device (cpu / cuda:0)")
    p.add_argument("--model",        default="ViT-B/32",      help="CLIP model name")
    p.add_argument("--checkpoint",   default=None,
                   help="Path to MotionCLIP checkpoint for fine-tuned CLIP weights")
    p.add_argument("--pairs",        default="null:stand still,stand still:walk,walk:run,turn left:turn right,slow:fast,stand still:squat down,put down hand:raise hand over head",
                   help='Text pairs, e.g. "stand:walk,slow:fast"')
    p.add_argument("--normalize",    action="store_true", default=True,
                   help="L2-normalize final embedding (default)")
    p.add_argument("--no-normalize", dest="normalize", action="store_false",
                   help="Disable final norm")
    p.add_argument("--interval",     type=float, default=0.1, help="Resend interval [s]")
    p.add_argument("--default-weight", type=float, default=1.0,
                   help="Initial value for the first slider (default: 1.0)")
    p.add_argument("--ui-scale", type=float, default=None,
                   help="Interp GUI scale factor (elements + font) for HiDPI "
                        "screens. Default: CLIP_INTERP_UI_SCALE env, else Xft.dpi "
                        "(when >100%%), else 2.0.")
    p.add_argument("--scale", type=float, default=None,
                   help="Deprecated alias of --ui-scale (kept for back-compat).")
    return p


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    lock_sock = _ensure_single_sender()  # held for process lifetime
    args = build_arg_parser().parse_args()

    text_pairs = _parse_pairs(args.pairs)
    print(f"[clip_interp_sender] {len(text_pairs)} text pairs loaded")

    # HiDPI: shared ×2.0 default for the interp GUI (elements + font).
    ui_scale = resolve_ui_scale(args.ui_scale, args.scale, "CLIP_INTERP_UI_SCALE")
    print(f"[clip_interp_sender] interp GUI scale = {ui_scale:.1f}")

    sender = InterpSender(
        text_pairs=text_pairs,
        host=args.host,
        port=args.port,
        cond_dim=args.cond_dim,
        device=args.device,
        clip_model_name=args.model,
        checkpoint_path=args.checkpoint,
        normalize=args.normalize,
        default_weight=args.default_weight,
        interval=args.interval,
        scale=ui_scale,
    )
    sender.start()

    print("[clip_interp_sender] Press Ctrl-C to quit.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    print("\n[clip_interp_sender] Shutting down...")
    sender.stop()
    print("[clip_interp_sender] Done.")


if __name__ == "__main__":
    main()
