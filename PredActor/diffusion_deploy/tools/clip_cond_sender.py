"""
clip_cond_sender.py
===================
Interactive CLIP conditioning sender for the C++ EnvRunner.

Encodes text (or GUI-interpolated embeddings) with CLIP and sends the result
as a raw float32 UDP datagram to the C++ runner.

All sent embeddings are L2-normalized to unit norm (‖cond‖ = 1).

Wire format (same as EnvRunner cond receiver):
  N * float32 bytes   (N = cond_dim, default 512)

Usage:
  python clip_cond_sender.py [OPTIONS]

Modes (--mode):
  simple   Direct text input loop (default).  Type a prompt, press Enter.
  teleop   Use CLIPTeleop from diffusion_policy.utils — background input thread.
  interp   Use CLIPInterp from diffusion_policy.utils — Tkinter GUI sliders.

Common options:
  --host IP           Target host for C++ runner       (default: 127.0.0.1)
  --port PORT         Target UDP port (cond_udp_port)  (default: 9877)
  --cond-dim N        Conditioning dimension            (default: 512)
  --device DEV        CLIP inference device             (default: cpu)
  --model NAME        CLIP model name                   (default: ViT-B/32)
  --checkpoint PATH   MotionCLIP checkpoint to load fine-tuned CLIP weights from.
                      Must match the checkpoint used during training (e.g.
                      MoDyeEnc/exps/g1-model-xyz-clip/checkpoint_0100.pth.tar).
                      If omitted, uses default OpenAI CLIP weights.
  --default TEXT      Initial text prompt               (default: "walking forward")
  --interval S        Resend interval in seconds        (default: 0.1)
  --once              Encode & send once, then exit (simple mode only)

simple / teleop mode commands (at prompt>):
  <any text>    Encode and start sending that embedding
  /stop         Stop sending (send zero embedding)
  /zero         Send zero embedding once
  /quit or /q   Exit

interp mode options:
  --pairs TEXT  Comma-separated text pairs as "A:B,C:D" (default: "walking:running")
  --no-normalize  Disable final unit-norm on interpolated embedding
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import numpy as np


DEFAULT_PRECACHE_TEXTS = ("stand", "walk", "jog", "squat down")


# ---------------------------------------------------------------------------
# Singleton guard — ensures only one sender runs at a time.
# ---------------------------------------------------------------------------

_LOCK_PORT = 9878  # dedicated lock port, distinct from cond data port (9877)

def _acquire_lock() -> socket.socket | None:
    """Try to bind *LOCK_PORT*.  Returns the lock socket on success, None if
    another sender (or stale process) already holds it."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", _LOCK_PORT))
        return s
    except OSError:
        return None


def _ensure_single_sender() -> socket.socket:
    """Acquire the singleton lock or exit with a clear message."""
    lock = _acquire_lock()
    if lock is None:
        print(f"[clip_cond_sender] ERROR: Another sender is already running "
              f"(port {_LOCK_PORT} is in use).", file=sys.stderr)
        print(f"  Kill it with:  fuser -k {_LOCK_PORT}/udp", file=sys.stderr)
        sys.exit(1)
    return lock


# ---------------------------------------------------------------------------
# Utility: normalize a numpy float32 vector to unit norm
# ---------------------------------------------------------------------------

def _normalize(v: np.ndarray) -> np.ndarray:
    """Return v / ‖v‖.  Returns zeros unchanged (avoids div-by-zero)."""
    n = float(np.linalg.norm(v))
    if n < 1e-9:
        return v
    return (v / n).astype(np.float32)


# ---------------------------------------------------------------------------
# UDP helpers
# ---------------------------------------------------------------------------

def _send(sock: socket.socket, host: str, port: int, emb: np.ndarray) -> None:
    """Normalize then send float32 array over UDP."""
    emb_norm = _normalize(emb.reshape(-1).astype(np.float32))
    sock.sendto(emb_norm.tobytes(), (host, port))


def _send_loop(sock: socket.socket, host: str, port: int,
               get_emb,          # callable () -> np.ndarray | None
               stop_event: threading.Event,
               interval: float) -> None:
    """Background thread: periodically fetch and send current embedding."""
    while not stop_event.is_set():
        try:
            emb = get_emb()
            if emb is not None:
                _send(sock, host, port, emb)
        except Exception as e:
            print(f"[clip_cond_sender] send_loop error: {e}")
        stop_event.wait(interval)


def _dispatch_cached_prompt(text, cache, encode, send, clock_ns=time.monotonic_ns):
    """Resolve and synchronously send one prompt, returning latency evidence.

    The old simple-mode path only replaced a shared embedding and waited for
    the periodic thread (up to ``--interval``) before its first send. This
    function makes first delivery synchronous. Known commands are pre-cached,
    so their post-Enter path performs neither model inference nor a sleep.
    """
    read_done_ns = clock_ns()
    cache_hit = text in cache
    if cache_hit:
        embedding = cache[text]
    else:
        embedding = encode(text)
        cache[text] = embedding
    encode_done_ns = clock_ns()
    send(embedding)
    send_done_ns = clock_ns()
    return embedding, {
        "cache_hit": cache_hit,
        "read_done_ns": read_done_ns,
        "encode_done_ns": encode_done_ns,
        "send_done_ns": send_done_ns,
        "enter_to_send_ms": (send_done_ns - read_done_ns) / 1e6,
        "encode_ms": (encode_done_ns - read_done_ns) / 1e6,
        "send_ms": (send_done_ns - encode_done_ns) / 1e6,
    }


# ---------------------------------------------------------------------------
# Standalone CLIP loader (used by simple mode; teleop/interp load their own)
# ---------------------------------------------------------------------------

def _load_clip(model_name: str, device: str, checkpoint_path: str = None):
    """Load CLIP; tries openai-clip then open_clip.

    If checkpoint_path is provided, loads MotionCLIP fine-tuned CLIP weights
    on top of the base model (same as CLIPTeleop._load_clip_from_checkpoint).
    """
    try:
        import clip as openai_clip
        model, _ = openai_clip.load(model_name, device=device, jit=False)
        openai_clip.model.convert_weights(model)
        model.eval()
        print(f"[clip_cond_sender] Loaded OpenAI CLIP {model_name} on {device}")
        tokenize_fn = openai_clip.tokenize
        clip_backend = "openai"
    except Exception:
        tokenize_fn = None
        clip_backend = None
        model = None

    if model is None:
        try:
            import open_clip
            model, _, _ = open_clip.create_model_and_transforms(model_name, pretrained="openai")
            model = model.to(device).eval()
            tokenize_fn = open_clip.get_tokenizer(model_name)
            print(f"[clip_cond_sender] Loaded open_clip {model_name} on {device}")
            clip_backend = "open_clip"
        except Exception:
            pass

    if model is None:
        raise RuntimeError(
            "Neither 'clip' nor 'open_clip' could be imported.\n"
            "  pip install git+https://github.com/openai/CLIP.git\n"
            "  pip install open_clip_torch"
        )

    if checkpoint_path is not None:
        _load_clip_weights_from_checkpoint(model, checkpoint_path, device)

    model.eval()
    for p in model.parameters():
        p.requires_grad = False

    return model, tokenize_fn, clip_backend


def _load_clip_weights_from_checkpoint(clip_model, checkpoint_path: str, device: str):
    """Load MotionCLIP fine-tuned weights into an already-created CLIP model.

    Mirrors CLIPTeleop._load_clip_from_checkpoint exactly.
    """
    import torch
    print(f"[clip_cond_sender] Loading MotionCLIP CLIP weights from: {checkpoint_path}")
    try:
        state_dict = torch.load(checkpoint_path, map_location=device)
        model_state = state_dict.get("model", state_dict)

        clip_state = {
            k.replace("clip_model.", ""): v
            for k, v in model_state.items()
            if k.startswith("clip_model.")
        }

        if len(clip_state) == 0:
            print("[clip_cond_sender] Warning: No clip_model.* keys found in checkpoint. Using default CLIP weights.")
            return

        missing, unexpected = clip_model.load_state_dict(clip_state, strict=False)
        if missing:
            print(f"[clip_cond_sender] Warning: {len(missing)} missing keys when loading CLIP weights.")
        if unexpected:
            print(f"[clip_cond_sender] Warning: {len(unexpected)} unexpected keys when loading CLIP weights.")
        print(f"[clip_cond_sender] Loaded {len(clip_state)} MotionCLIP CLIP weight tensors.")
    except Exception as e:
        print(f"[clip_cond_sender] Error loading checkpoint: {e}  — using default CLIP weights.")


def _encode_text(model, tokenize_fn, text: str, device: str,
                 cond_dim: int) -> np.ndarray:
    """Encode text → float32 [cond_dim], L2-normalized."""
    import torch
    tokens = tokenize_fn([text])
    if hasattr(tokens, "to"):
        tokens = tokens.to(device)
    with torch.no_grad():
        feat = model.encode_text(tokens).float().cpu().numpy().reshape(-1)
    if len(feat) < cond_dim:
        feat = np.concatenate([feat, np.zeros(cond_dim - len(feat), dtype=np.float32)])
    else:
        feat = feat[:cond_dim]
    return _normalize(feat)


# ---------------------------------------------------------------------------
# Mode: simple
# ---------------------------------------------------------------------------

def run_simple(args) -> None:
    model, tokenize_fn, _ = _load_clip(args.model, args.device, args.checkpoint)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[clip_cond_sender] [simple] Sending to {args.host}:{args.port}  cond_dim={args.cond_dim}")

    print(f"[clip_cond_sender] Encoding default: '{args.default}'")
    emb = _encode_text(model, tokenize_fn, args.default, args.device, args.cond_dim)
    cache = {args.default: emb}
    for text in args.precache:
        if text and text not in cache:
            cache[text] = _encode_text(model, tokenize_fn, text, args.device, args.cond_dim)
    print(f"[clip_cond_sender] norm={float(np.linalg.norm(emb)):.4f}")

    if args.once:
        _send(sock, args.host, args.port, emb)
        print("[clip_cond_sender] Sent once. Exiting.")
        sock.close()
        return

    emb_ref   = [emb]
    stop_ev   = threading.Event()
    sender    = threading.Thread(
        target=_send_loop,
        args=(sock, args.host, args.port, lambda: emb_ref[0], stop_ev, args.interval),
        daemon=True,
    )
    sender.start()
    print(f"[clip_cond_sender] Sending every {args.interval:.2f}s")
    print("[clip_cond_sender] Commands: /stop  /zero  /quit (/q)")

    try:
        while True:
            if args.headless:
                time.sleep(0.5)
                continue
            try:
                line = input("prompt> ").strip()
            except EOFError:
                break

            if not line:
                continue
            if line in ("/quit", "/q"):
                break
            if line == "/stop":
                emb_ref[0] = None
                print("[clip_cond_sender] Stopped sending.")
                continue
            if line == "/zero":
                emb_ref[0] = np.zeros(args.cond_dim, dtype=np.float32)
                _send(sock, args.host, args.port, emb_ref[0])
                print("[clip_cond_sender] Sent zero embedding.")
                continue
            try:
                new_emb, timing = _dispatch_cached_prompt(
                    line, cache,
                    lambda text: _encode_text(
                        model, tokenize_fn, text, args.device, args.cond_dim),
                    lambda value: _send(sock, args.host, args.port, value))
                emb_ref[0] = new_emb
                print(f"[clip_cond_sender] Updated: '{line}'  "
                      f"norm={float(np.linalg.norm(new_emb)):.4f}  "
                      f"cache={'hit' if timing['cache_hit'] else 'miss'}  "
                      f"enter_to_send={timing['enter_to_send_ms']:.3f}ms  "
                      f"encode={timing['encode_ms']:.3f}ms")
            except Exception as e:
                print(f"[clip_cond_sender] Encoding failed: {e}")
    except KeyboardInterrupt:
        pass

    print("[clip_cond_sender] Shutting down...")
    stop_ev.set()
    sender.join(timeout=2.0)
    sock.close()


# ---------------------------------------------------------------------------
# Mode: teleop  (uses CLIPTeleop from diffusion_policy)
# ---------------------------------------------------------------------------

def run_teleop(args) -> None:
    from diffusion_policy.task_provider.clip_teleop import CLIPTeleop
    import torch

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def on_update(text, embedding, timing):
        if args.once:
            return
        arr = embedding[0].float().cpu().numpy()
        before_send = time.monotonic_ns()
        _send(sock, args.host, args.port, arr)
        after_send = time.monotonic_ns()
        enter_ns = timing.get("input_done_ns", before_send)
        print(f"[clip_cond_sender] immediate '{text}'  "
              f"cache={'hit' if timing.get('cache_hit') else 'miss'}  "
              f"enter_to_send={(after_send-enter_ns)/1e6:.3f}ms")

    teleop = CLIPTeleop(
        device=args.device,
        cond_dim=args.cond_dim,
        default_text=args.default,
        clip_model_name=args.model,
        checkpoint_path=args.checkpoint,
        precache_texts=args.precache,
        on_embedding_update=on_update,
    )
    teleop.start()

    print(f"[clip_cond_sender] [teleop] Sending to {args.host}:{args.port}  cond_dim={args.cond_dim}")

    if args.once:
        emb = teleop.get_embedding(batch_size=1, n_cond_steps=1)  # [1, 1, cond_dim]
        arr = emb[0, 0].float().cpu().numpy()
        _send(sock, args.host, args.port, arr)
        print("[clip_cond_sender] Sent once. Exiting.")
        teleop.stop()
        sock.close()
        return

    def get_emb():
        t = teleop.get_embedding(batch_size=1, n_cond_steps=1)  # [1, 1, D]
        return t[0, 0].float().cpu().numpy()

    stop_ev = threading.Event()
    sender  = threading.Thread(
        target=_send_loop,
        args=(sock, args.host, args.port, get_emb, stop_ev, args.interval),
        daemon=True,
    )
    sender.start()
    print(f"[clip_cond_sender] Sending every {args.interval:.2f}s  (CLIPTeleop input thread active)")
    print("[clip_cond_sender] Press Ctrl-C to quit.")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    print("[clip_cond_sender] Shutting down...")
    stop_ev.set()
    sender.join(timeout=2.0)
    teleop.stop()
    sock.close()


# ---------------------------------------------------------------------------
# Mode: interp  (uses CLIPInterp from diffusion_policy)
# ---------------------------------------------------------------------------

def _parse_pairs(pairs_str: str):
    """Parse "A:B,C:D" into [("A","B"),("C","D")]. 'null' -> None."""
    pairs = []
    for token in pairs_str.split(","):
        token = token.strip()
        if ":" in token:
            a, b = token.split(":", 1)
            a = a.strip() or None
            b = b.strip() or None
            pairs.append((a if a != "null" else None,
                          b if b != "null" else None))
    return pairs if pairs else [("walking", "running")]


def run_interp(args) -> None:
    from diffusion_policy.task_provider.clip_interp import CLIPInterp
    import torch

    text_pairs = _parse_pairs(args.pairs)
    normalize  = not args.no_normalize

    interp = CLIPInterp(
        text_pairs=text_pairs,
        device=args.device,
        cond_dim=args.cond_dim,
        clip_model_name=args.model,
        normalize=normalize,
        checkpoint_path=args.checkpoint,
        scale=args.scale,
    )

    # Set baseline weight so the robot receives a meaningful embedding
    # straight away.  Without this, CLIPInterp starts at w=0 → zero vector
    # which the model interprets as "no text conditioning".
    default_weight = getattr(args, 'default_weight', 1.0)
    if default_weight != 0.0 and len(text_pairs) > 0:
        weights = [0.0] * len(text_pairs)
        weights[0] = float(default_weight)
        interp.set_weights(weights)
        print(f"[clip_cond_sender] Baseline: slider[0] = {default_weight:.1f}")

    interp.start()  # opens Tkinter GUI in background thread

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[clip_cond_sender] [interp] Sending to {args.host}:{args.port}  cond_dim={args.cond_dim}")
    print(f"[clip_cond_sender] text pairs: {text_pairs}")

    if args.once:
        emb = interp.get_embedding(batch_size=1, n_cond_steps=1)
        arr = emb[0, 0].float().cpu().numpy()
        _send(sock, args.host, args.port, arr)
        print("[clip_cond_sender] Sent once. Exiting.")
        interp.stop()
        sock.close()
        return

    def get_emb():
        t = interp.get_embedding(batch_size=1, n_cond_steps=1)  # [1, 1, D]
        return t[0, 0].float().cpu().numpy()

    stop_ev = threading.Event()
    sender  = threading.Thread(
        target=_send_loop,
        args=(sock, args.host, args.port, get_emb, stop_ev, args.interval),
        daemon=True,
    )
    sender.start()
    print(f"[clip_cond_sender] Sending every {args.interval:.2f}s  (CLIPInterp GUI active)")
    print("[clip_cond_sender] Use the GUI sliders to adjust conditioning.  Ctrl-C to quit.")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    print("[clip_cond_sender] Shutting down...")
    stop_ev.set()
    sender.join(timeout=2.0)
    interp.stop()
    sock.close()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CLIP conditioning UDP sender for C++ EnvRunner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--mode",       default="simple",
                   choices=["simple", "teleop", "interp"],
                   help="Input mode: simple (text loop) | teleop (CLIPTeleop) | interp (CLIPInterp GUI)")
    p.add_argument("--host",       default="127.0.0.1", help="Target host")
    p.add_argument("--port",       type=int, default=9877, help="Target UDP port")
    p.add_argument("--cond-dim",   type=int, default=512,  help="Conditioning dimension")
    p.add_argument("--device",     default="cpu",           help="CLIP device (cpu / cuda:0)")
    p.add_argument("--model",      default="ViT-B/32",      help="CLIP model name")
    p.add_argument("--checkpoint", default=None,
                   help="Path to MotionCLIP checkpoint to load fine-tuned CLIP weights "
                        "(e.g. MoDyeEnc/exps/g1-model-xyz-clip/checkpoint_0100.pth.tar). "
                        "Must match the checkpoint used at training time. "
                        "If omitted, uses default OpenAI CLIP weights.")
    p.add_argument("--default",    default="walking forward",
                   help="Initial text prompt (simple / teleop modes)")
    p.add_argument("--interval",   type=float, default=0.1, help="Resend interval [s]")
    p.add_argument("--once",       action="store_true",     help="Send once and exit")
    p.add_argument("--headless",   action="store_true",
                   help="Simple mode: keep resending the default without reading stdin")
    p.add_argument("--precache", nargs="*", default=list(DEFAULT_PRECACHE_TEXTS),
                   help="Text commands encoded before the sender becomes ready; "
                        "defaults to stand/walk/jog/'squat down'")
    # interp-specific
    p.add_argument("--pairs",      default="walking:running",
                   help='Text pairs for interp mode, e.g. "walking:running,forward:backward"')
    p.add_argument("--no-normalize", action="store_true",
                   help="Disable CLIPInterp final unit-norm (interp mode only)")
    p.add_argument("--default-weight", type=float, default=1.0,
                   help="Initial weight for the first interp slider (default: 1.0)")
    p.add_argument("--scale", type=float, default=2.0,
                   help="GUI scale factor for hi-res screens (fonts, window size, padding)")
    return p


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    lock_sock = _ensure_single_sender()  # held for process lifetime
    args = build_arg_parser().parse_args()
    if args.mode == "simple":
        run_simple(args)
    elif args.mode == "teleop":
        run_teleop(args)
    elif args.mode == "interp":
        run_interp(args)
    else:
        print(f"[clip_cond_sender] Unknown mode: {args.mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
