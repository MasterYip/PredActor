"""
wbg_guidance_sender.py
======================
Interactive Whole-Body Guidance (WBG) UDP sender for the C++ EnvRunner.

Mirrors clip_cond_sender.py: a Python sender launches a GUI/CLI, and talks to
the C++ policy runner over UDP. The runner applies live WBG command updates
(enabled/command/kp per axis) without restarting.

Wire format (same as the C++ EnvRunner WBG receiver):
  one datagram = 9 x float32 LE in this fixed order:

      [vx_enabled, vx_command, vx_kp,
       vy_enabled, vy_command, vy_kp,
       wz_enabled, wz_command, wz_kp]

  enabled:  0.0 (disabled) or 1.0 (enabled)
  command:  m/s for vx/vy, rad/s for wz   (C++ clamps |vx|,|vy| <= 2.0 m/s, |wz| <= 2.0 rad/s)
  kp:       guidance gain                 (C++ clamps to [0, 100])

GUI vs runtime clamp note (DEPLOY-WBG-GUI-034): the interp GUI command sliders
range -5.0..5.0 and the kp slider ranges 0.0..2.0.  Commands the GUI permits
beyond +/-2.0 are still silently clamped to +/-2.0 by the C++ receiver
(whole_body_guidance.cpp ``set_live_axis``); the kp 0..2 slider range stays
within the C++ [0, 100] clamp, so only the command range is wider than the
runtime clamp.

Hardware joystick (interp, --joy): reads a Linux /dev/input/js* device via
``diffusion_policy.utils.joystick_parser.VelocityJoystick``. When present, a "Use joystick"
switch drives vx/vy/wz from the stick (already scaled to m/s and rad/s by
the exact GUI slider ranges, default +/-5.0 for all three axes). Optional
``max_linear_vel`` / ``max_angular_vel`` CLI values override joystick scaling
only. The C++ receiver still clamps all commands to +/-2.0. The ``height``
channel is dropped (the WBG UDP frame is vx/vy/wz only). Without a device, the
sliders are used unchanged.

Body indices / masks / scale / offset are NOT changeable over UDP (safety).

Usage:
  python wbg_guidance_sender.py [OPTIONS]

Modes (--mode):
  simple   Direct stdin text loop (default).  Type "vx,vy,wz", press Enter.
  teleop   Keyboard/text input thread in the background + periodic resend.
  interp   customtkinter GUI with sliders for vx/vy/wz command and kp.

Common options:
  --host IP        Target host for C++ runner       (default: 127.0.0.1)
  --port PORT      Target UDP port (wbg_udp_port)   (default: 9879)
  --mode MODE      simple | teleop | interp         (default: simple)
  --interval S     Resend interval in seconds       (default: 0.1)
  --default TEXT   Initial commands "vx,vy,wz"      (default: "0.0,0.0,0.0")
  --ui-scale N     interp GUI scale (elements+font) (default: WBG_UI_SCALE env
                   > Xft.dpi when >100% > 2.0 HiDPI default)

simple / teleop commands (at wbg>):
  <vx>,<vy>,<wz>   Set all three command values, e.g. "0.5,0.0,0.2"
  /vx <cmd>        Set vx command only
  /vy <cmd>        Set vy command only
  /wz <cmd>        Set wz command only
  /kp <value>      Set kp for all three axes
  /on              Enable all axes
  /off             Disable all axes
  /stop            Disable all axes and send once
  /status          Print current state
  /quit or /q      Exit
"""

import argparse
import os
import socket
import struct
import subprocess
import sys
import threading
import time

# Dedicated singleton lock port, distinct from the CLIP sender's lock port
# (9878) and the WBG data port (9879). Clip and WBG senders cannot collide.
_LOCK_PORT = 9880

_DEFAULT_KP = 1.0
_AXES = ("vx", "vy", "wz")
WBG_COMMAND_RANGES = {
    "vx": (-5.0, 5.0),
    "vy": (-5.0, 5.0),
    "wz": (-5.0, 5.0),
}


# ---------------------------------------------------------------------------
# Singleton guard — ensures only one WBG sender runs at a time.
# ---------------------------------------------------------------------------

def _acquire_lock():
    """Try to bind *LOCK_PORT*. Returns the lock socket on success, None if
    another sender (or stale process) already holds it."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", _LOCK_PORT))
        return s
    except OSError:
        return None


def _ensure_single_sender():
    lock = _acquire_lock()
    if lock is None:
        print(f"[wbg_guidance_sender] ERROR: Another WBG sender is already "
              f"running (port {_LOCK_PORT} is in use).", file=sys.stderr)
        print(f"  Kill it with:  fuser -k {_LOCK_PORT}/udp", file=sys.stderr)
        sys.exit(1)
    return lock


# ---------------------------------------------------------------------------
# State + UDP helpers
# ---------------------------------------------------------------------------

def _default_state(args):
    """State: axis -> [enabled(bool), command(float), kp(float)]."""
    try:
        parts = [float(x) for x in args.default.replace(";", ",").split(",")]
    except (ValueError, AttributeError):
        parts = []
    while len(parts) < 3:
        parts.append(0.0)
    return {
        "vx": [True, parts[0], _DEFAULT_KP],
        "vy": [True, parts[1], _DEFAULT_KP],
        "wz": [True, parts[2], _DEFAULT_KP],
    }


def _pack_frame(state):
    """Pack the 9-float datagram:
    [vx_en, vx_c, vx_kp, vy_en, vy_c, vy_kp, wz_en, wz_c, wz_kp]."""
    vals = []
    for axis in _AXES:
        enabled, cmd, kp = state[axis]
        vals.append(1.0 if enabled else 0.0)
        vals.append(float(cmd))
        vals.append(float(kp))
    return struct.pack("<9f", *vals)


def _send(sock, host, port, state):
    sock.sendto(_pack_frame(state), (host, port))


def _send_loop(sock, host, port, get_state, stop_event, interval):
    """Background thread: periodically fetch and send current WBG frame."""
    while not stop_event.is_set():
        try:
            st = get_state()
            if st is not None:
                _send(sock, host, port, st)
        except Exception as e:
            print(f"[wbg_guidance_sender] send_loop error: {e}")
        stop_event.wait(interval)


def _print_status(state):
    for axis in _AXES:
        enabled, cmd, kp = state[axis]
        print(f"  {axis}: enabled={1 if enabled else 0} "
              f"command={cmd:.3f} kp={kp:.3f}")


def _parse_command(text, state):
    """Handle one user command line. Returns 'quit' to exit, True otherwise."""
    text = text.strip()
    if not text:
        return True
    if text in ("/quit", "/q"):
        return "quit"
    if text == "/status":
        _print_status(state)
        return True
    if text in ("/on", "/off", "/stop"):
        enable = text != "/off" and text != "/stop"
        for a in _AXES:
            state[a][0] = enable
        print(f"[wbg_guidance_sender] All axes {'enabled' if enable else 'disabled'}.")
        return True
    if text.startswith("/kp"):
        parts = text.split()
        if len(parts) != 2:
            print("  usage: /kp <value>")
            return True
        try:
            kp = float(parts[1])
            for a in _AXES:
                state[a][2] = kp
            print(f"[wbg_guidance_sender] kp for all axes = {kp:.3f}")
        except ValueError:
            print("  invalid kp value")
        return True
    for prefix, axis in (("/vx", "vx"), ("/vy", "vy"), ("/wz", "wz")):
        if text.startswith(prefix):
            parts = text.split()
            if len(parts) != 2:
                print(f"  usage: {prefix} <value>")
                return True
            try:
                state[axis][1] = float(parts[1])
                print(f"[wbg_guidance_sender] {axis} command = {state[axis][1]:.3f}")
            except ValueError:
                print("  invalid value")
            return True
    try:
        parts = text.split(",")
        if len(parts) == 3:
            vals = [float(p) for p in parts]
            for i, a in enumerate(_AXES):
                state[a][1] = vals[i]
            print(f"[wbg_guidance_sender] commands -> "
                  f"vx={vals[0]:.3f} vy={vals[1]:.3f} wz={vals[2]:.3f}")
            return True
    except ValueError:
        pass
    print(f"[wbg_guidance_sender] Unrecognized command: '{text}'")
    return True


# ---------------------------------------------------------------------------
# Mode: simple
# ---------------------------------------------------------------------------

def run_simple(args):
    state = _default_state(args)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[wbg_guidance_sender] [simple] Sending to {args.host}:{args.port}  "
          f"interval={args.interval:.2f}s")
    print(f"[wbg_guidance_sender] initial: vx={state['vx'][1]} "
          f"vy={state['vy'][1]} wz={state['wz'][1]} kp={state['vx'][2]}")

    stop_ev = threading.Event()
    sender = threading.Thread(
        target=_send_loop,
        args=(sock, args.host, args.port, lambda: state, stop_ev, args.interval),
        daemon=True,
    )
    sender.start()
    print("[wbg_guidance_sender] Commands: 'vx,vy,wz' | /vx C /vy C /wz C | "
          "/kp K | /on /off /stop | /status | /quit (/q)")

    try:
        while True:
            if args.headless:
                time.sleep(0.5)
                continue
            try:
                line = input("wbg> ")
            except EOFError:
                break
            r = _parse_command(line, state)
            if r == "quit":
                break
            _send(sock, args.host, args.port, state)  # immediate send on change
    except KeyboardInterrupt:
        pass

    print("[wbg_guidance_sender] Shutting down...")
    stop_ev.set()
    sender.join(timeout=2.0)
    sock.close()


# ---------------------------------------------------------------------------
# Mode: teleop  (background keyboard/text input thread + periodic resend)
# ---------------------------------------------------------------------------

def run_teleop(args):
    state = _default_state(args)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[wbg_guidance_sender] [teleop] Sending to {args.host}:{args.port}  "
          f"interval={args.interval:.2f}s")
    print(f"[wbg_guidance_sender] initial: vx={state['vx'][1]} "
          f"vy={state['vy'][1]} wz={state['wz'][1]} kp={state['vx'][2]}")

    stop_ev = threading.Event()

    def input_loop():
        try:
            while not stop_ev.is_set():
                try:
                    line = input("wbg> ")
                except EOFError:
                    break
                r = _parse_command(line, state)
                if r == "quit":
                    stop_ev.set()
                    break
        except KeyboardInterrupt:
            pass

    threading.Thread(target=input_loop, daemon=True).start()
    sender = threading.Thread(
        target=_send_loop,
        args=(sock, args.host, args.port, lambda: state, stop_ev, args.interval),
        daemon=True,
    )
    sender.start()
    print("[wbg_guidance_sender] Keyboard/text input thread active. Ctrl-C to quit.")
    try:
        while not stop_ev.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    print("[wbg_guidance_sender] Shutting down...")
    stop_ev.set()
    sender.join(timeout=2.0)
    sock.close()


# ---------------------------------------------------------------------------
# UI scale resolution (HiDPI)
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


def resolve_ui_scale(cli_value, env_var, default=2.0):
    """Resolve the Tkinter GUI scale factor.

    Priority (documented in the README):
      1. ``--ui-scale`` explicit CLI value.
      2. ``env_var`` (e.g. ``WBG_UI_SCALE``) environment override.
      3. Xft.dpi auto-detection **when the display declares a scale > 100%**
         (avoids silently undoing the ×2.0 HiDPI default on an unconfigured
         96-dpi X server).
      4. ``default`` = 2.0 (the user-approved ×2.0 HiDPI default).

    The same factor scales both pixel geometry and fonts; see ``run_interp``.
    """
    if cli_value is not None:
        return max(1.0, float(cli_value))
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


# ---------------------------------------------------------------------------
# Mode: interp  (customtkinter GUI sliders for vx/vy/wz command and kp)
# ---------------------------------------------------------------------------

def _reset_controls(vars_map, enable_var, launch_cmds, launch_kp, launch_enabled=True):
    """Set the interp GUI controls back to their launch defaults.

    ``vars_map`` maps axis name (or ``"kp"``) to a settable double var
    (anything with ``.set``); ``enable_var`` is a settable bool var.  Kept free
    of any tk import so the Reset behaviour can be unit-tested without a
    display (the GUI ``reset`` closure delegates to this).
    """
    for axis in _AXES:
        vars_map[axis].set(float(launch_cmds[axis]))
    vars_map["kp"].set(float(launch_kp))
    enable_var.set(bool(launch_enabled))


def _import_joystick():
    """Import the canonical ``VelocityJoystick`` reader, or return ``None`` when it is
    not importable.

    This file lives under ``diffusion_deploy/tools/``; ``diffusion_policy`` is
    a sibling package under the PDPlanner root, so the root is derived from
    ``__file__`` and prepended to ``sys.path`` (same pattern as
    ``test/test_noise_scheduling/*.py``).  Returns ``None`` (never raises) so
    the sender still runs sliders-only when ``diffusion_policy`` is absent.
    """
    try:
        pddir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if pddir not in sys.path:
            sys.path.insert(0, pddir)
        try:
            from diffusion_policy.utils.joystick_parser import VelocityJoystick
        except ImportError:
            # Installed or source-tree standalone diffusion_deploy package.
            manager_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
            if manager_python not in sys.path:
                sys.path.insert(0, manager_python)
            from diffusion_deploy_manager.joystick_parser import VelocityJoystick
        return VelocityJoystick
    except Exception as exc:  # pragma: no cover - exercised on partial installs
        print(f"[wbg_guidance_sender] joystick support disabled: {exc}",
              file=sys.stderr)
        return None


def _joystick_command_ranges(args):
    """Ranges passed to the parser; defaults are the exact GUI slider ranges."""
    linear = abs(float(args.joy_max_linear))
    angular = abs(float(args.joy_max_angular))
    return {"vx": (-linear, linear), "vy": (-linear, linear), "wz": (-angular, angular)}


def _command_slider_specs(command_ranges):
    """Pure description consumed by tkinter; useful for exact parity tests."""
    return (
        ("vx", "vx (m/s)", *command_ranges["vx"]),
        ("vy", "vy (m/s)", *command_ranges["vy"]),
        ("wz", "wz (rad/s)", *command_ranges["wz"]),
    )


def run_interp(args):
    try:
        import customtkinter as ctk
        import tkinter as tk
    except ImportError:
        print("[wbg_guidance_sender] customtkinter is not available on this "
              "system; cannot open the interp GUI.", file=sys.stderr)
        sys.exit(1)

    # HiDPI: resolve the shared ×2.0 default (flag > env > Xft.dpi > 2.0).
    scale = resolve_ui_scale(args.ui_scale, "WBG_UI_SCALE")

    state = _default_state(args)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[wbg_guidance_sender] [interp] Sending to {args.host}:{args.port}  "
          f"interval={args.interval:.2f}s  ui_scale={scale:.1f}")

    stop_ev = threading.Event()
    sender = threading.Thread(
        target=_send_loop,
        args=(sock, args.host, args.port, lambda: state, stop_ev, args.interval),
        daemon=True,
    )
    sender.start()

    # ── Hardware joystick (optional) ──────────────────────────────────────
    # ``--joy`` tries to open the Linux joystick device.  When found, the
    # joystick drives vx/vy/wz (a "Use joystick" switch in the GUI selects it
    # over the sliders); when absent, the sliders behave exactly as before.
    joy = None
    command_ranges = _joystick_command_ranges(args)
    if getattr(args, "joy", False):
        joy_cls = _import_joystick()
        if joy_cls is not None:
            joy = joy_cls(
                device=args.joy_device,
                joystick_type=args.joy_type,
                max_linear_vel=args.joy_max_linear,
                max_angular_vel=args.joy_max_angular,
                **{f"{axis}_range": value_range for axis, value_range in command_ranges.items()},
            )
            joy.start()
            if joy.is_connected():
                print(f"[wbg_guidance_sender] [interp] joystick active "
                      f"({args.joy_device}, {args.joy_type}, "
                      f"lin={args.joy_max_linear:.2f} ang={args.joy_max_angular:.2f})")
            else:
                print("[wbg_guidance_sender] [interp] joystick unavailable — "
                      "falling back to sliders.", file=sys.stderr)
                print("[wbg_guidance_sender] reconnect remains armed; sliders "
                      "stay active until a controller connects.", file=sys.stderr)

    # customtkinter scales widget dimensions AND tuple fonts by this factor,
    # which replaces the old ``tk scaling`` + ttk font re-pointing dance.
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    ctk.set_widget_scaling(scale)

    root = ctk.CTk()
    root.title("WBG Guidance")
    root.geometry(f"{int(480 * scale)}x{int(360 * scale)}")
    print(f"[wbg_guidance_sender] [interp] GUI scaled by {scale:.1f} "
          f"(customtkinter widget scaling)")

    vars_map = {}
    labels = {}

    def make_slider(parent, label, lo, hi, default):
        frm = ctk.CTkFrame(parent, fg_color="transparent")
        frm.pack(fill="x", padx=int(8 * scale), pady=int(4 * scale))
        ctk.CTkLabel(frm, text=label, width=96, anchor="w",
                     font=("Arial", 12)).pack(side="left")
        var = tk.DoubleVar(value=default)
        ctk.CTkSlider(frm, from_=lo, to=hi, variable=var,
                      width=180).pack(side="left", fill="x", expand=True,
                                      padx=(8, 8))
        val = ctk.CTkLabel(frm, text=f"{default:.2f}", width=44, anchor="e",
                           font=("Arial", 12, "bold"))
        val.pack(side="right")
        return var, val

    # Joystick and visible sliders consume the exact same per-run table,
    # including CLI overrides.
    for axis, label, lo, hi in _command_slider_specs(command_ranges):
        vars_map[axis], labels[axis] = make_slider(root, label, lo, hi, state[axis][1])
    vars_map["kp"], labels["kp"] = make_slider(root, "kp", 0.0, 2.0, state["vx"][2])

    enable_var = tk.BooleanVar(value=True)
    ctk.CTkSwitch(root, text="Enable guidance (all axes)", variable=enable_var,
                  font=("Arial", 12)).pack(pady=(int(4 * scale), 0))

    # ── Joystick controls (only shown when hardware is present) ───────────
    joy_use_var = tk.BooleanVar(value=True)
    joy_label = None
    if joy is not None:
        ctk.CTkSwitch(root, text="Use joystick (vx/vy/wz)", variable=joy_use_var,
                      font=("Arial", 12)).pack(pady=(int(4 * scale), 0))
        joy_label = ctk.CTkLabel(root, text="joy: vx=+0.00 vy=+0.00 wz=+0.00",
                                 font=("Arial", 12, "bold"), text_color="#8ab4f8")
        joy_label.pack(anchor="w", padx=int(12 * scale))

    btn_row = ctk.CTkFrame(root, fg_color="transparent")
    btn_row.pack(fill="x", padx=int(8 * scale), pady=int(8 * scale))
    ctk.CTkButton(btn_row, text="Reset", width=90,
                  command=lambda: reset()).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row, text="Quit", width=90,
                  command=root.destroy).pack(side="left")

    # Launch-time defaults, captured once before the sync() loop starts
    # mutating ``state`` from the slider positions.
    launch_cmds = {axis: state[axis][1] for axis in _AXES}
    launch_kp = state["vx"][2]
    launch_enabled = True

    def sync_once():
        """Read the controls into ``state`` and refresh the value labels.

        When the joystick is selected, its (already scaled) vx/vy/wz replace
        the slider commands and the sliders are mirrored to show the live
        values; the ``height`` channel is dropped (the WBG UDP frame carries
        vx/vy/wz only).
        """
        connected = joy is not None and joy.is_connected()
        use_joy = connected and joy_use_var.get()
        if use_joy:
            vx, vy, wz, _height = joy.get_cmd_vel()
            state["vx"][1] = vx
            state["vy"][1] = vy
            state["wz"][1] = wz
            vars_map["vx"].set(vx)
            vars_map["vy"].set(vy)
            vars_map["wz"].set(wz)
            joy_label.configure(text=f"joy: vx={vx:+.2f} vy={vy:+.2f} wz={wz:+.2f}")
        else:
            for axis in _AXES:
                state[axis][1] = vars_map[axis].get()
            if joy_label is not None:
                status = "sliders active" if connected else "disconnected; retrying"
                joy_label.configure(text=f"joy: ({status})")
        kp = vars_map["kp"].get()
        for a in _AXES:
            state[a][2] = kp
            state[a][0] = bool(enable_var.get())
        for axis in _AXES:
            labels[axis].configure(text=f"{state[axis][1]:.2f}")
        labels["kp"].configure(text=f"{state['vx'][2]:.2f}")

    def sync():
        sync_once()
        root.after(100, sync)

    def reset():
        _reset_controls(vars_map, enable_var, launch_cmds, launch_kp, launch_enabled)
        sync_once()

    root.after(100, sync)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass

    print("[wbg_guidance_sender] Shutting down...")
    if joy is not None:
        joy.stop()
    stop_ev.set()
    sender.join(timeout=2.0)
    sock.close()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_arg_parser():
    p = argparse.ArgumentParser(
        description="WBG guidance UDP sender for the C++ EnvRunner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--mode", default="simple",
                   choices=["simple", "teleop", "interp"],
                   help="Input mode: simple (stdin) | teleop (input thread) | "
                        "interp (Tkinter GUI sliders)")
    p.add_argument("--host", default="127.0.0.1", help="Target host")
    p.add_argument("--port", type=int, default=9879, help="Target UDP port")
    p.add_argument("--interval", type=float, default=0.1,
                   help="Resend interval [s]")
    p.add_argument("--default", default="0.0,0.0,0.0",
                   help='Initial commands as "vx,vy,wz"')
    p.add_argument("--headless", action="store_true",
                   help="Simple mode: keep resending the default without reading stdin")
    p.add_argument("--ui-scale", type=float, default=None,
                   help="Interp GUI scale factor (elements + font) for HiDPI "
                        "screens. Default: WBG_UI_SCALE env, else Xft.dpi "
                        "(when >100%%), else 2.0.")
    p.add_argument("--joy", action="store_true",
                   help="Interp mode: read a hardware joystick (Linux "
                        "/dev/input/js*) for live vx/vy/wz. Falls back to "
                        "sliders when no device is found.")
    p.add_argument("--joy-device", default="/dev/input/js0",
                   help="Joystick device path (default: /dev/input/js0).")
    p.add_argument("--joy-type", default="xbox",
                   choices=["xbox", "xbox_new", "ps5", "ps4", "generic", "beitong_kp20"],
                   help="Controller type (default: xbox).")
    p.add_argument("--joy-max-linear", type=float, default=WBG_COMMAND_RANGES["vx"][1],
                   help="Joystick max linear velocity vx/vy [m/s] "
                        "(default: matches GUI, 5.0).")
    p.add_argument("--joy-max-angular", type=float, default=WBG_COMMAND_RANGES["wz"][1],
                   help="Joystick max angular velocity wz [rad/s] "
                        "(default: matches GUI, 5.0).")
    return p


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    lock_sock = _ensure_single_sender()  # held for process lifetime
    args = build_arg_parser().parse_args()
    try:
        if args.mode == "simple":
            run_simple(args)
        elif args.mode == "teleop":
            run_teleop(args)
        elif args.mode == "interp":
            run_interp(args)
        else:
            print(f"[wbg_guidance_sender] Unknown mode: {args.mode}", file=sys.stderr)
            sys.exit(1)
    finally:
        if lock_sock is not None:
            lock_sock.close()


if __name__ == "__main__":
    main()
