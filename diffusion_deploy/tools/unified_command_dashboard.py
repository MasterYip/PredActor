#!/usr/bin/env python3
"""Optional read-only dashboard for unified C++ command telemetry.

This process never sends a control packet. Closing it has no effect on the
runner or joystick command source.
"""
import argparse
import json
import math
import os
import socket
import sys


MOTIONS = {"stand", "walk", "jog", "squat down"}


def parse_telemetry(payload: bytes) -> dict:
    if len(payload) > 4096:
        raise ValueError("telemetry payload too large")
    message = json.loads(payload.decode("utf-8"))
    if message.get("schema") != 1:
        raise ValueError("unsupported telemetry schema")
    if not isinstance(message.get("sequence"), int) or message["sequence"] < 0:
        raise ValueError("invalid sequence")
    if not isinstance(message.get("monotonic_ms"), int):
        raise ValueError("invalid monotonic timestamp")
    if not isinstance(message.get("joystick_connected"), bool):
        raise ValueError("invalid joystick state")
    if message.get("motion") not in MOTIONS:
        raise ValueError("unexpected motion command")
    wbg = message.get("wbg")
    if not isinstance(wbg, dict) or not isinstance(wbg.get("enabled"), bool):
        raise ValueError("invalid WBG object")
    for name in ("vx_enabled", "vy_enabled", "wz_enabled"):
        if name not in wbg:
            # Schema 1 is extensible. Treat older senders as all-axis when
            # their global WBG switch is enabled.
            wbg[name] = wbg["enabled"]
        elif not isinstance(wbg[name], bool):
            raise ValueError(f"invalid WBG {name}")
    for name in ("vx", "vy", "wz", "kp"):
        value = wbg.get(name)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"invalid WBG {name}")
    return message


def format_tui_status(message: dict) -> str:
    """Format one compact status line for an SSH/headless terminal."""
    values = message["wbg"]
    joystick = "connected" if message["joystick_connected"] else "not connected"
    status = "ON" if values["enabled"] else "OFF"
    vx = "ON" if values["vx_enabled"] else "OFF"
    vy = "ON" if values["vy_enabled"] else "OFF"
    wz = "ON" if values["wz_enabled"] else "OFF"
    return (f"seq={message['sequence']} joystick={joystick} motion={message['motion']} | "
            f"WBG={status} vx={vx} {values['vx']:+.2f} "
            f"vy={vy} {values['vy']:+.2f} wz={wz} {values['wz']:+.2f} "
            f"kp={values['kp']:.2f}")


def _gui_available() -> bool:
    """Return whether a Linux session has a display for CustomTkinter."""
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def run_tui(host: str, port: int) -> None:
    """Receive telemetry without GUI dependencies, suitable for SSH sessions."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(0.5)
    print("Unified command telemetry (read-only TUI); press Ctrl-C to stop.", flush=True)
    last_state = None
    try:
        while True:
            try:
                payload, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                message = parse_telemetry(payload)
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                print(f"invalid telemetry: {exc}", flush=True)
                continue
            values = message["wbg"]
            state = (message["joystick_connected"], message["motion"],
                     values["enabled"], values["vx_enabled"], values["vy_enabled"],
                     values["wz_enabled"], values["vx"], values["vy"], values["wz"],
                     values["kp"])
            if state == last_state:
                continue
            last_state = state
            line = format_tui_status(message)
            if sys.stdout.isatty():
                sys.stdout.write("\r\033[2K" + line)
                sys.stdout.flush()
            else:
                print(line, flush=True)
    except KeyboardInterrupt:
        if sys.stdout.isatty():
            print()
        print("Telemetry listener stopped.", flush=True)
    finally:
        sock.close()


def run_gui(host: str, port: int, scale: float) -> None:
    try:
        import customtkinter as ctk
    except ImportError as exc:
        raise SystemExit("customtkinter is required for --mode gui") from exc

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.setblocking(False)

    ctk.set_widget_scaling(scale)
    root = ctk.CTk()
    root.title("Deployment command status")
    root.geometry("460x250")
    title = ctk.CTkLabel(root, text="Unified command interface", font=("", 18, "bold"))
    title.pack(anchor="w", padx=18, pady=(16, 8))
    connection = ctk.CTkLabel(root, text="waiting for telemetry", anchor="w")
    connection.pack(fill="x", padx=18, pady=3)
    motion = ctk.CTkLabel(root, text="motion: —", anchor="w")
    motion.pack(fill="x", padx=18, pady=3)
    wbg = ctk.CTkLabel(root, text="WBG: —", anchor="w")
    wbg.pack(fill="x", padx=18, pady=3)
    transport = ctk.CTkLabel(
        root, text="read-only UDP telemetry · control remains in C++", anchor="w")
    transport.pack(fill="x", padx=18, pady=(14, 3))

    def update():
        latest = None
        try:
            while True:
                latest = parse_telemetry(sock.recv(4096))
        except BlockingIOError:
            pass
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            connection.configure(text=f"invalid telemetry: {exc}")
        if latest:
            connection.configure(
                text=f"joystick: {'connected' if latest['joystick_connected'] else 'not connected'}"
                     f"   seq: {latest['sequence']}")
            motion.configure(text=f"motion: {latest['motion']}")
            values = latest["wbg"]
            status = "ENABLED" if values["enabled"] else "DISABLED"
            vx = "ON" if values["vx_enabled"] else "OFF"
            vy = "ON" if values["vy_enabled"] else "OFF"
            wz = "ON" if values["wz_enabled"] else "OFF"
            wbg.configure(text=(f"WBG {status}: vx {vx} {values['vx']:+.2f}   "
                                f"vy {vy} {values['vy']:+.2f}   "
                                f"wz {wz} {values['wz']:+.2f}   "
                                f"effective kp {values['kp']:.2f}"))
        root.after(40, update)

    def close():
        sock.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    update()
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only unified command status dashboard/listener")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9880)
    parser.add_argument("--scale", type=float, default=1.5)
    parser.add_argument("--mode", choices=("auto", "gui", "tui"), default="auto",
                        help="auto selects GUI when available, otherwise the SSH-safe TUI")
    args = parser.parse_args()

    if args.mode == "tui":
        run_tui(args.host, args.port)
        return
    if args.mode == "auto" and not _gui_available():
        print("[dashboard] no graphical display; using terminal mode", file=sys.stderr, flush=True)
        run_tui(args.host, args.port)
        return
    try:
        run_gui(args.host, args.port, args.scale)
    except SystemExit:
        if args.mode == "gui":
            raise
        print("[dashboard] customtkinter unavailable; using terminal mode", file=sys.stderr, flush=True)
        run_tui(args.host, args.port)


if __name__ == "__main__":
    main()
