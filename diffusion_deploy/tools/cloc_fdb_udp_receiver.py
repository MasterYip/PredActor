"""
cloc_fdb_udp_receiver.py
========================
Receives robot-state UDP datagrams from the C++ EnvRunnerDebug and feeds
them to CLoCFdbDebugger for real-time visualization.

Wire format (matches EnvRunnerDebug::send_debug_udp):
  4B   magic = 0xDBD10001  (little-endian uint32)
  4B   frame_index         (little-endian uint32)
  4B   n_fields            (little-endian uint32)
  per field:
    64B  name              (null-padded ASCII)
    4B   n_floats          (little-endian uint32)
    n_floats * 4B  values  (little-endian float32)

Usage:
  python cloc_fdb_udp_receiver.py [OPTIONS]

  --host IP         Bind host           (default: 0.0.0.0)
  --port PORT       Bind port           (default: 9878)
  --output-dir DIR  Visualizer output   (default: /tmp/cloc_fdb_vis)
  --no-vis          Disable matplotlib visualization (just print stats)
  --show-vel        Show velocity arrows in 3D view
  --show-rlobs      Show RLObs time-series panel
  --history N       Visualization history length (default: 200)
  --update-every N  Refresh plot every N frames   (default: 5)
"""

import argparse
import numpy as np
import socket
import struct
import sys
import time
from pathlib import Path

DEBUG_UDP_MAGIC    = 0xDBD10001
FIELD_NAME_LEN     = 64
HEADER_FMT         = "<III"      # magic, frame_idx, n_fields
HEADER_SIZE        = struct.calcsize(HEADER_FMT)
FIELD_HEADER_FMT   = f"<{FIELD_NAME_LEN}sI"
FIELD_HEADER_SIZE  = struct.calcsize(FIELD_HEADER_FMT)


def unpack_datagram(data: bytes):
    """
    Unpack a binary robot-state datagram.

    Returns:
        (frame_idx: int, fields: dict[str, np.ndarray]) or None on error.
    """
    if len(data) < HEADER_SIZE:
        return None

    magic, frame_idx, n_fields = struct.unpack_from(HEADER_FMT, data, 0)
    if magic != DEBUG_UDP_MAGIC:
        print(f"[receiver] Bad magic: 0x{magic:08X}", file=sys.stderr)
        return None

    fields = {}
    offset = HEADER_SIZE
    for _ in range(n_fields):
        if offset + FIELD_HEADER_SIZE > len(data):
            break
        name_raw, n_floats = struct.unpack_from(FIELD_HEADER_FMT, data, offset)
        offset += FIELD_HEADER_SIZE

        name = name_raw.rstrip(b"\x00").decode("ascii", errors="replace")
        byte_count = n_floats * 4
        if offset + byte_count > len(data):
            break

        values = np.frombuffer(data, dtype=np.float32,
                               count=n_floats, offset=offset).copy()
        offset += byte_count
        fields[name] = values

    return frame_idx, fields


def reshape_obs(fields: dict) -> dict:
    """
    Reshape flat field arrays into the shapes expected by CLoCFdbDebugger.update().
    """
    obs = {}

    # body_pos: flat [30*3] → [30, 3]
    if "body_pos" in fields and fields["body_pos"].size == 90:
        obs["body_pos"] = fields["body_pos"].reshape(30, 3)

    # body_lin_vel: flat [30*3] → [30, 3]
    if "body_lin_vel" in fields and fields["body_lin_vel"].size == 90:
        obs["body_lin_vel"] = fields["body_lin_vel"].reshape(30, 3)

    # scalars / small vectors — pass through as-is
    for key in ("root_pos", "root_rot", "root_ang_vel",
                "projected_gravity", "base_lin_vel", "base_ang_vel",
                "last_actions", "joint_pos", "joint_vel"):
        if key in fields:
            obs[key] = fields[key]

    return obs


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Receive robot-state UDP from C++ EnvRunnerDebug and visualize")
    p.add_argument("--host",         default="0.0.0.0",       help="Bind host")
    p.add_argument("--port",         type=int, default=9878,   help="Bind port")
    p.add_argument("--output-dir",   default="/tmp/cloc_fdb_vis", help="Visualizer output dir")
    p.add_argument("--no-vis",       action="store_true",       help="Disable matplotlib")
    p.add_argument("--show-vel",     action="store_true",       help="Show velocity arrows")
    p.add_argument("--show-rlobs",   action="store_true",       help="Show RLObs panel")
    p.add_argument("--history",      type=int, default=200,     help="History length")
    p.add_argument("--update-every", type=int, default=5,       help="Plot update interval")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()

    # ---- Socket ----
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    sock.bind((args.host, args.port))
    sock.settimeout(1.0)
    print(f"[receiver] Listening on {args.host}:{args.port}")

    # ---- Visualizer ----
    debugger = None
    if not args.no_vis:
        # Import from the PDPlanner diffusion_policy package
        import importlib.util, os

        cloc_path = Path(__file__).resolve().parent.parent.parent / \
                    "diffusion_policy" / "utils" / "cloc_fdb_debugger.py"
        if not cloc_path.exists():
            # Try relative to CWD
            cloc_path = Path("../diffusion_policy/utils/cloc_fdb_debugger.py")

        if cloc_path.exists():
            spec = importlib.util.spec_from_file_location("cloc_fdb_debugger", cloc_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            CLoCFdbDebugger = mod.CLoCFdbDebugger
        else:
            # Assume it's importable on the path
            from diffusion_policy.utils.cloc_fdb_debugger import CLoCFdbDebugger

        debugger = CLoCFdbDebugger(
            output_dir      = args.output_dir,
            history_length  = args.history,
            update_interval = args.update_every,
            show_velocities = args.show_vel,
            show_root_states= True,
            show_rlobs      = args.show_rlobs,
            save_frequency  = "on_close",
            runner_name     = f"EnvRunnerDebug (UDP :{args.port})",
        )
        print(f"[receiver] CLoCFdbDebugger initialized. Output: {args.output_dir}")
    else:
        print("[receiver] Visualization disabled (--no-vis).")

    # ---- Stats ----
    frame_count   = 0
    t_last_report = time.time()

    print("[receiver] Waiting for datagrams... (Ctrl-C to quit)")
    try:
        while True:
            try:
                data, addr = sock.recvfrom(131072)
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break

            result = unpack_datagram(data)
            if result is None:
                continue

            frame_idx, raw_fields = result
            frame_count += 1

            obs = reshape_obs(raw_fields)

            if debugger is not None and "body_pos" in obs:
                debugger.update(obs)

            # Periodic stats to stdout
            now = time.time()
            if now - t_last_report >= 5.0:
                fps = frame_count / (now - t_last_report + 1e-9)
                print(f"[receiver] frame={frame_idx}  fps≈{fps:.1f}"
                      f"  fields={list(raw_fields.keys())}")
                frame_count   = 0
                t_last_report = now

    except KeyboardInterrupt:
        pass

    print("[receiver] Shutting down...")
    if debugger is not None:
        debugger.close()
    sock.close()
    print("[receiver] Done.")


if __name__ == "__main__":
    main()
