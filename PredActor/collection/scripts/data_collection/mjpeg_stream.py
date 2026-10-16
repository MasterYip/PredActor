"""
MJPEG streaming server for headless Isaac Sim data collection.

Captures the viewport swapchain to a temp file (the only approach that
works reliably from a non-Kit thread), then converts to JPEG in memory.
A dedicated background thread runs capture continuously; HTTP clients
only read the latest frame — no per-client capture overhead.

Set MJPEG_PORT env var to change the port (default 39200).
Set MJPEG_QUALITY to change JPEG quality (default 50, range 10–95).
"""

import io
import os
import sys
import threading
import time
import json
import tempfile
import atexit
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# Shared state — capture thread writes, HTTP handlers read
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
_state = {
    "latest_jpeg": None,
    "capture_ok": False,
    "frame_w": 0,
    "frame_h": 0,
    "frame_bytes": 0,
    "serial": 0,
    "errors": 0,
}

JPEG_QUALITY = int(os.environ.get("MJPEG_QUALITY", "50"))
_VIDEO_FPS = float(os.environ.get("MJPEG_RECORD_FPS", "30"))
_video_proc = None
_video_lock = threading.Lock()


def _start_mp4_recorder():
    """Record captured viewport JPEGs to a real H.264 MP4 when requested."""
    global _video_proc
    output = os.environ.get("MJPEG_RECORD_PATH", "").strip()
    if not output:
        return None
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _video_proc = subprocess.Popen(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "image2pipe", "-vcodec", "mjpeg", "-framerate", str(_VIDEO_FPS),
                "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(output_path),
            ],
            stdin=subprocess.PIPE,
        )
        print(f"[MJPEG] MP4 recording enabled: {output_path} @ {_VIDEO_FPS:g} fps")
    except Exception as exc:
        _video_proc = None
        print(f"[MJPEG] MP4 recorder unavailable: {exc}")
    return _video_proc


def _record_mp4_frame(jpeg):
    if _video_proc is None or _video_proc.stdin is None:
        return
    try:
        with _video_lock:
            _video_proc.stdin.write(jpeg)
            _video_proc.stdin.flush()
    except (BrokenPipeError, OSError):
        pass


def record_rgb_frame(rgb):
    """Encode an Isaac rgb_array frame and append it to the requested MP4."""
    if rgb is None or _video_proc is None:
        return
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.fromarray(rgb[:, :, :3]).convert("RGB").save(buf, format="JPEG", quality=85)
        _record_mp4_frame(buf.getvalue())
    except Exception as exc:
        print(f"[MJPEG] rgb_array frame encode failed: {exc}")


def _stop_mp4_recorder():
    global _video_proc
    if _video_proc is None:
        return
    try:
        with _video_lock:
            if _video_proc.stdin is not None:
                _video_proc.stdin.close()
            _video_proc.wait(timeout=10)
    except Exception:
        try:
            _video_proc.kill()
        except Exception:
            pass
    finally:
        _video_proc = None


atexit.register(_stop_mp4_recorder)


def _store(jpeg, w=0, h=0):
    with _state_lock:
        _state["latest_jpeg"] = jpeg
        _state["frame_w"] = w
        _state["frame_h"] = h
        _state["frame_bytes"] = len(jpeg) if jpeg else 0
        _state["serial"] += 1
        _state["capture_ok"] = True


def _read():
    with _state_lock:
        return (
            _state["latest_jpeg"],
            _state["capture_ok"],
            _state["frame_w"],
            _state["frame_h"],
            _state["frame_bytes"],
            _state["serial"],
        )


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class _MJPEGHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def do_GET(self):
        if self.path == "/stream":
            self._serve_stream()
        elif self.path == "/":
            self._serve_viewer()
        elif self.path == "/health":
            _, ok, w, h, sz, serial = _read()
            self._serve_json({
                "status": "ok",
                "capture": "live" if ok else "initializing",
                "frame_dims": f"{w}x{h}",
                "frame_size": sz,
                "serial": serial,
            })
        else:
            self.send_error(404)

    def _serve_viewer(self):
        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Isaac Sim Viewer</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#111;display:flex;flex-direction:column;align-items:center;
     justify-content:center;min-height:100vh;font-family:monospace;color:#ccc}
h2{margin:10px 0;font-weight:400;font-size:16px}
img{max-width:95vw;max-height:85vh;border:2px solid #333;border-radius:4px}
#status{font-size:12px;color:#888;margin-top:8px}
</style></head><body>
<h2>Isaac Sim &mdash; Live Viewport</h2>
<img src="/stream" alt="Stream" id="stream" />
<p id="status">Connecting...</p>
<script>
var img=document.getElementById('stream'),st=document.getElementById('status'),last=Date.now();
img.onload=function(){st.textContent='Live '+new Date().toLocaleTimeString();last=Date.now()}
img.onerror=function(){st.textContent='Waiting...'}
setInterval(function(){
var s=Math.round((Date.now()-last)/1000);
if(s>3)st.textContent='No frames in '+s+'s'
},1500)
</script>
</body></html>"""
        self._send_html(html)

    def _serve_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        last_serial = -1
        no_frame_sleep = 0.02
        try:
            while True:
                jpeg, ok, _, _, _, serial = _read()
                if jpeg is None or serial == last_serial:
                    time.sleep(no_frame_sleep)
                    # Back off if still no frames after many attempts
                    no_frame_sleep = min(no_frame_sleep + 0.005, 0.1)
                    continue
                no_frame_sleep = 0.02
                last_serial = serial
                try:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError, OSError):
                    return
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _serve_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------------------
# Placeholder frame (until first live frame is captured)
# ---------------------------------------------------------------------------
def _placeholder():
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (960, 540), (25, 25, 30))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Isaac Sim — Starting Up", fill=(200, 200, 200))
        draw.text((20, 50), "Rendering initializing...", fill=(150, 150, 150))
        draw.text((20, 80), f"Time: {time.strftime('%H:%M:%S')}", fill=(120, 120, 120))
        draw.text((20, 500), "Check: tail -f /tmp/dc_viewer.log", fill=(100, 100, 100))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=30)
        return buf.getvalue()
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Capture engine — file-based swapchain capture (known to work)
# ---------------------------------------------------------------------------

def _build_file_capture():
    """Set up file-based swapchain capture. Returns (capture_fn, info_dict) or None."""
    try:
        from omni.kit.renderer_capture import acquire_renderer_capture_interface
    except Exception as e:
        print(f"[MJPEG] renderer_capture import: {e}")
        return None

    try:
        iface = acquire_renderer_capture_interface()
        if iface is None:
            print("[MJPEG] acquire_renderer_capture_interface -> None")
            return None
        iface.startup()
    except Exception as e:
        print(f"[MJPEG] renderer_capture startup: {e}")
        return None

    try:
        import omni.appwindow
        factory = omni.appwindow.acquire_app_window_factory_interface()
        app_window = factory.get_default_window() if factory else None
        print(f"[MJPEG] app_window={app_window}")
    except Exception as e:
        print(f"[MJPEG] app window: {e}")
        app_window = None

    # Use ASYNC mode — we poll for the file.
    # Sync mode can block forever if the renderer isn't producing frames yet.
    try:
        iface.set_capture_sync(False, app_window)
        print("[MJPEG] async capture mode")
    except Exception as e:
        print(f"[MJPEG] async mode: {e}")

    tmpdir = tempfile.mkdtemp(prefix="mjpeg_")
    path = os.path.join(tmpdir, "frame.jpg")
    print(f"[MJPEG] capture path={path}")

    def _capture():
        """Returns (jpeg_bytes, width, height) or (None, 0, 0)."""
        try:
            # Remove stale file so we can detect a fresh write
            if os.path.exists(path):
                os.remove(path)
            iface.capture_next_frame_swapchain(path, app_window)
            # Async — poll for the file (renderer writes it on next frame)
            for _ in range(100):  # up to 1s
                if os.path.exists(path) and os.path.getsize(path) > 500:
                    with open(path, "rb") as f:
                        data = f.read()
                    try:
                        from PIL import Image
                        img = Image.open(io.BytesIO(data))
                        w, h = img.size
                        # Resize if larger than 1280 wide for faster streaming
                        if w > 1280:
                            ratio = 1280.0 / w
                            img = img.resize((1280, int(h * ratio)), Image.LANCZOS)
                            w, h = img.size
                        img = img.convert("RGB")
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
                        return buf.getvalue(), w, h
                    except Exception:
                        from PIL import Image
                        img = Image.open(io.BytesIO(data))
                        w, h = img.size
                        if w > 1280:
                            ratio = 1280.0 / w
                            img = img.resize((1280, int(h * ratio)), Image.LANCZOS)
                            w, h = img.size
                        img = img.convert("RGB")
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
                        return buf.getvalue(), w, h
                time.sleep(0.005)
        except Exception:
            pass
        return None, 0, 0

    # Quick test
    jpeg, w, h = _capture()
    if jpeg and len(jpeg) > 500:
        print(f"[MJPEG] Test capture OK: {w}x{h} {len(jpeg)} bytes")
    else:
        sz = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"[MJPEG] Test capture: sz={sz} (renderer may not be ready yet, will keep trying)")
    return _capture


# ---------------------------------------------------------------------------
# Start everything
# ---------------------------------------------------------------------------

def start_mjpeg_server(port=39200):
    """Start MJPEG HTTP server + continuous capture thread.

    Call from the Kit main thread AFTER SimulationApp has started and
    extensions are loaded.
    """
    # Store placeholder initially
    ph = _placeholder()
    if ph is not None:
        _store(ph)

    _start_mp4_recorder()

    # Start HTTP server
    try:
        server = HTTPServer(("0.0.0.0", port), _MJPEGHandler)
    except OSError as e:
        print(f"[MJPEG] Cannot bind port {port}: {e}")
        return None
    server.timeout = 1
    t = threading.Thread(target=server.serve_forever, daemon=True, name="mjpeg-http")
    t.start()
    print(f"[MJPEG] HTTP server on :{port}")

    # Set up capture (must happen on the main Kit thread for extension access)
    print("[MJPEG] Setting up capture engine...")
    capturer = _build_file_capture()
    if capturer is None:
        print("[MJPEG] Capture setup failed — serving placeholder only")
        return server

    _store(None)  # clear placeholder flag
    print("[MJPEG] Starting continuous capture loop...")

    def _capture_loop():
        while True:
            try:
                jpeg, w, h = capturer()
                if jpeg and len(jpeg) > 500:
                    _store(jpeg, w, h)
                    _record_mp4_frame(jpeg)
            except Exception:
                pass
            # Minimal sleep — the sync capture already blocks per-frame

    t2 = threading.Thread(target=_capture_loop, daemon=True, name="mjpeg-cap")
    t2.start()
    print(f"[MJPEG] Viewer ready at http://0.0.0.0:{port}")
    return server
