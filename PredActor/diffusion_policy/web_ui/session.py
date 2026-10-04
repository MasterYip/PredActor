"""Evaluation-loop observer and local FastAPI server."""

from __future__ import annotations

import hashlib
import math
import struct
import threading
import time
import webbrowser
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from diffusion_policy.task_provider.whole_body_guidance.destination_follow import (
    map_target_between_root_frames,
)
from .state import EvaluationState, PerturbSequenceError, ProtocolError


@dataclass(frozen=True)
class WebCameraConfig:
    """Authoritative browser-camera settings resolved against the MuJoCo model."""

    enabled: bool = True
    body_name: str = "pelvis"
    follow_yaw: bool = False
    lookat_offset: tuple[float, float, float] = (0.0, 0.0, 0.04)
    smoothing_tau: float = 0.15

    def __post_init__(self):
        if not isinstance(self.body_name, str) or not self.body_name:
            raise ValueError("camera body_name must be a non-empty string")
        try:
            offset = tuple(float(value) for value in self.lookat_offset)
        except (TypeError, ValueError) as exc:
            raise ValueError("camera lookat_offset must contain three numbers") from exc
        if len(offset) != 3 or not all(math.isfinite(value) for value in offset):
            raise ValueError("camera lookat_offset must contain three finite numbers")
        tau = float(self.smoothing_tau)
        if not math.isfinite(tau) or tau < 0.0:
            raise ValueError("camera smoothing_tau must be finite and non-negative")
        object.__setattr__(self, "enabled", bool(self.enabled))
        object.__setattr__(self, "follow_yaw", bool(self.follow_yaw))
        object.__setattr__(self, "lookat_offset", offset)
        object.__setattr__(self, "smoothing_tau", tau)


class EvaluationWebSession:
    _DPAD_MOTIONS = {
        "up": "stand",
        "right": "walk",
        "down": "jog",
        "left": "squat down",
    }

    def __init__(self, provider=None, host="127.0.0.1", port=8765, open_browser=True,
                 joystick=None, perturb_enabled=False, perturb_max_force=120.0,
                 perturb_max_torque=30.0, perturb_timeout=0.18, camera_config=None):
        self.provider, self.host, self.port = provider, host, int(port)
        self.open_browser, self.joystick = bool(open_browser), joystick
        self.state, self.wbg = EvaluationState(), None
        self._paused, self._snapshot_lock = threading.Event(), threading.Lock()
        self._snapshot, self._snapshot_seq, self._last_step_at = b"", 0, None
        self._server = self._thread = None
        self._original_enabled: dict[int, bool] = {}
        self._configured_kp: dict[int, float] = {}
        self._joy_initialized = False
        self._lb_previous = False
        self._lb_last_toggle_at = float("-inf")
        self._dpad_latched = False
        self.model_manifest = None
        self.model_files: dict[str, Path] = {}
        self.perturb_enabled = bool(perturb_enabled)
        self.perturb_max_force = self._positive_limit(perturb_max_force, "perturb_max_force")
        self.perturb_max_torque = self._positive_limit(perturb_max_torque, "perturb_max_torque")
        self.perturb_timeout = self._positive_limit(perturb_timeout, "perturb_timeout")
        self._env = None
        self._reset_requested = threading.Event()
        self._reset_lock = threading.Lock()
        self._auto_reset = True
        self._perturb_lock = threading.Lock()
        self._perturb_intent = None
        self._perturb_last_seq = 0
        self._perturb_applied_body = None
        if camera_config is not None and not isinstance(camera_config, WebCameraConfig):
            raise TypeError("camera_config must be a WebCameraConfig")
        self.camera_config = camera_config or WebCameraConfig()

    @staticmethod
    def _positive_limit(value, name):
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
        return value

    def launch(self) -> None:
        from .server import build_app
        import uvicorn
        self._server = uvicorn.Server(uvicorn.Config(build_app(self), host=self.host, port=self.port, log_level="warning"))
        self._thread = threading.Thread(target=self._server.run, name="cond-eval-web", daemon=True)
        self._thread.start()
        url = f"http://{self.host}:{self.port}"
        print(f"[WebUI] {url}")
        if self.open_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    def start(self, env, bc_agent) -> None:
        self._env = env
        self._prepare_model_manifest(env)
        self.wbg = getattr(getattr(bc_agent, "actor", None), "whole_body_guidance", None)
        if self.wbg is not None:
            self.wbg.runtime_telemetry_enabled = True
            for guidance in self.wbg._manager.guidances:
                self._original_enabled[id(guidance)] = bool(guidance.activation.enabled)
                self._configured_kp[id(guidance)] = float(guidance.activation.kp)
        if self.joystick is not None:
            ranges = self.command_ranges()
            configure_ranges = getattr(self.joystick, "set_command_ranges", None)
            if callable(configure_ranges):
                configure_ranges({"vx": ranges["vx"], "vy": ranges["vy"],
                                  "wz": ranges["wz"], "height": ranges["hz"]})
            self.joystick.start()
            if self.wbg is not None:
                self.wbg.set_joystick_source(self.joystick, owned=False)
            self.state.mutate("joy", mapping=self.joystick_mapping_snapshot(),
                              device_path=self._joystick_device_path(),
                              connection_error=self._joystick_connection_error())
            if self.joystick.is_connected():
                self.state.update(source="joystick")
        master_enabled = bool(self.wbg and any(self._original_enabled.values()))
        self.state.mutate("wbg", enabled=master_enabled, ranges=self.command_ranges(),
                          activation=self.activation_snapshot())
        self._sync_destination_state()
        self.state.mutate("perturb", enabled=self.perturb_enabled)
        provider = self._raw_provider()
        interpolation_snapshot = getattr(provider, "get_interpolation_snapshot", None)
        if callable(interpolation_snapshot):
            snapshot = interpolation_snapshot()
            self.state.set_interpolation_snapshot(snapshot)
            if snapshot.get("available"):
                active = [term for term in snapshot["terms"] if term["weight"] != 0]
                summary = " + ".join(
                    f"{term['text_a'] or 'ZERO'} -> {term['text_b'] or 'ZERO'} @ {term['weight']:.2f}"
                    for term in active
                ) or "zero semantic vector"
                self.state.mutate("text", mode="interp", current=summary)
        get_current_text = getattr(provider, "get_current_text", None)
        if callable(get_current_text):
            current_text = get_current_text()
            if current_text:
                self.state.mutate("text", current=current_text)
                if current_text in self._DPAD_MOTIONS.values():
                    self.state.mutate("joy", motion=current_text)
        self.state.update(status="running")

    def stop(self) -> None:
        if self.wbg is not None:
            self.cancel_destination_follow()
        self.clear_perturb()
        self._clear_applied_wrench()
        self.state.update(status="stopped")
        if self.joystick is not None:
            self.joystick.stop()
        if self._server is not None:
            self._server.should_exit = True

    def before_step(self, _step: int) -> bool:
        while self._paused.is_set():
            if self._reset_requested.is_set():
                return self.consume_reset_request()
            time.sleep(0.02)
        state = self.state.snapshot()
        if self.wbg is not None and self.joystick is not None and state["source"] == "joystick":
            self.state.mutate("wbg", values=self.wbg.update_joystick())
        if self.joystick is not None:
            raw, mapping = self.joystick.get_cmd(), self.joystick.mapping
            logical_axes = {axis.logical: round(float(raw["axes"].get(number, 0.0)), 4)
                            for number, axis in mapping.axes.items()}
            buttons = {button.logical: bool(raw["buttons"].get(number, 0))
                       for number, button in mapping.buttons.items()}
            connected = self.joystick.is_connected()
            dpad = [logical_axes.get("dpad_x", 0), logical_axes.get("dpad_y", 0)]
            self.state.mutate("joy", connected=connected, axes=logical_axes,
                              buttons=buttons, dpad=dpad,
                              device_path=self._joystick_device_path(),
                              connection_error=self._joystick_connection_error())
            self._apply_joystick_controls(logical_axes, buttons, connected)
        self._sync_destination_state()
        return self.consume_reset_request()

    def request_reset(self) -> None:
        if self._env is None:
            raise RuntimeError("simulation is not ready")
        self._reset_requested.set()

    def consume_reset_request(self) -> bool:
        requested = self._reset_requested.is_set()
        if requested:
            self._reset_requested.clear()
        return requested

    def set_auto_reset(self, enabled: bool) -> None:
        with self._reset_lock:
            self._auto_reset = bool(enabled)

    def auto_reset_enabled(self) -> bool:
        with self._reset_lock:
            return self._auto_reset

    def _joystick_connection_error(self):
        error = getattr(self.joystick, "last_error", None) if self.joystick is not None else None
        return str(error) if error else None

    def _joystick_device_path(self):
        if self.joystick is None:
            return None
        return getattr(self.joystick, "active_device", getattr(self.joystick, "device", "unknown"))

    @staticmethod
    def _finite_vector(value, name, length=3):
        if not isinstance(value, list) or len(value) != length:
            raise ProtocolError(f"{name} must contain {length} numbers")
        try:
            clean = np.asarray(value, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ProtocolError(f"{name} must be numeric") from exc
        if not np.all(np.isfinite(clean)):
            raise ProtocolError(f"{name} must be finite")
        return clean

    def set_perturb_intent(self, payload, *, now=None):
        if not self.perturb_enabled or self._env is None:
            raise ProtocolError("simulation perturbation is disabled")
        seq, body, mode = payload.get("seq"), payload.get("body"), payload.get("mode")
        nbody = int(getattr(getattr(self._env, "model", None), "nbody", 0))
        if isinstance(seq, bool) or not isinstance(seq, int) or seq <= 0:
            raise ProtocolError("perturb sequence must be a positive integer")
        if isinstance(body, bool) or not isinstance(body, int) or not 0 < body < nbody:
            raise ProtocolError("perturb body must be a dynamic body id")
        model = self._env.model
        body_mass = getattr(model, "body_mass", None)
        body_weldid = getattr(model, "body_weldid", None)
        if ((body_mass is not None and float(body_mass[body]) <= 0) or
                (body_weldid is not None and int(body_weldid[body]) == 0)):
            raise ProtocolError("perturb body is static")
        if mode not in {"force", "torque"}:
            raise ProtocolError("perturb mode must be force or torque")
        drag = self._finite_vector(payload.get("drag"), "drag", 2)
        if np.linalg.norm(drag) > 1.000001:
            raise ProtocolError("perturb drag exceeds normalized range")
        hit = self._finite_vector(payload.get("hit"), "hit")
        if np.linalg.norm(hit) > 100.0:
            raise ProtocolError("perturb hit point is out of range")
        right = self._finite_vector(payload.get("camera_right"), "camera_right")
        up = self._finite_vector(payload.get("camera_up"), "camera_up")
        forward = self._finite_vector(payload.get("camera_forward"), "camera_forward")
        basis = [right, up, forward]
        if any(not 0.8 <= np.linalg.norm(axis) <= 1.2 for axis in basis):
            raise ProtocolError("camera basis vectors must be normalized")
        basis = [axis / np.linalg.norm(axis) for axis in basis]
        if max(abs(float(np.dot(basis[i], basis[j]))) for i in range(3) for j in range(i)) > 0.2:
            raise ProtocolError("camera basis vectors must be orthogonal")
        with self._perturb_lock:
            if seq <= self._perturb_last_seq:
                raise PerturbSequenceError(self._perturb_last_seq)
            self._perturb_last_seq = seq
            self._perturb_intent = {"seq": seq, "body": body, "mode": mode,
                                    "drag": drag, "hit": hit, "right": basis[0],
                                    "up": basis[1], "forward": basis[2],
                                    "at": time.monotonic() if now is None else float(now)}

    def perturb_sequence(self):
        with self._perturb_lock:
            return self._perturb_last_seq

    @staticmethod
    def _force_at_point(force, hit, center):
        return np.cross(np.asarray(hit) - np.asarray(center), np.asarray(force))

    @staticmethod
    def _cap_vector(vector, limit):
        norm = float(np.linalg.norm(vector))
        return vector if norm <= limit or norm == 0 else vector * (limit / norm)

    def before_env_step(self, *, now=None):
        env = self._env
        if env is None or getattr(env, "data", None) is None:
            return
        now = time.monotonic() if now is None else float(now)
        with self._perturb_lock:
            intent = self._perturb_intent
        if intent is None:
            self._clear_applied_wrench()
            return
        if now - intent["at"] > self.perturb_timeout:
            self.clear_perturb()
            self._clear_applied_wrench()
            return
        body = intent["body"]
        if self._perturb_applied_body is not None and self._perturb_applied_body != body:
            env.data.xfrc_applied[self._perturb_applied_body, :] = 0.0
        drag, right, up = intent["drag"], intent["right"], intent["up"]
        wrench = np.zeros(6, dtype=np.float64)
        if intent["mode"] == "force":
            force = self._cap_vector((right * drag[0] - up * drag[1]) * self.perturb_max_force,
                                     self.perturb_max_force)
            center = np.asarray(env.data.xpos[body], dtype=np.float64)
            torque = self._cap_vector(self._force_at_point(force, intent["hit"], center),
                                      self.perturb_max_torque)
            wrench[:3], wrench[3:] = force, torque
        else:
            wrench[3:] = self._cap_vector((-right * drag[1] + up * drag[0]) * self.perturb_max_torque,
                                          self.perturb_max_torque)
        env.data.xfrc_applied[body, :] = wrench
        self._perturb_applied_body = body
        self.state.mutate("perturb", active=True, selected_body=body,
                          mode=intent["mode"], sequence=intent["seq"],
                          drag=intent["drag"].tolist(), force=wrench[:3].tolist(),
                          torque=wrench[3:].tolist())

    def clear_perturb(self):
        with self._perturb_lock:
            self._perturb_intent = None
        if self.state.snapshot()["perturb"]["active"]:
            self.state.mutate("perturb", active=False, mode=None, drag=[0.0, 0.0],
                              force=[0.0, 0.0, 0.0], torque=[0.0, 0.0, 0.0])

    def _clear_applied_wrench(self):
        if (self._env is not None and getattr(self._env, "data", None) is not None and
                self._perturb_applied_body is not None):
            self._env.data.xfrc_applied[self._perturb_applied_body, :] = 0.0
        self._perturb_applied_body = None

    def on_reset(self, reason="automatic"):
        if self.wbg is not None:
            self.cancel_destination_follow()
        self._sync_destination_state()
        self.clear_perturb()
        self._clear_applied_wrench()
        generation = self.state.snapshot()["perturb"]["generation"] + 1
        self.state.mutate("perturb", generation=generation, active=False, mode=None)
        simulation = self.state.snapshot()["simulation"]
        reset_count = simulation["reset_count"] + (reason != "initial")
        self.state.mutate("simulation", auto_reset=self.auto_reset_enabled(),
                          reset_pending=False, reset_count=reset_count,
                          last_reset_reason=None if reason == "initial" else reason)

    def after_reset(self, step: int, env) -> None:
        self._last_step_at = None
        self.state.update(step=step, fps=0.0)
        if getattr(env, "data", None) is not None:
            self._build_snapshot(env, step, time.perf_counter())

    @staticmethod
    def _trigger_pressure(value) -> float | None:
        if value is None:
            return 0.0
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return None
        return max(0.0, min(1.0, (float(value) + 1.0) * 0.5))

    def joystick_mapping_snapshot(self) -> dict | None:
        if self.joystick is None:
            return None
        mapping = self.joystick.mapping
        return {
            "name": mapping.name,
            "active_commands": ["dpad_x", "dpad_y", "l2", "l1"],
            "axes": [{"logical": axis.logical, "label": axis.label}
                     for _, axis in sorted(mapping.axes.items())],
            "buttons": [{"logical": button.logical, "label": button.label}
                        for _, button in sorted(mapping.buttons.items())],
        }

    @staticmethod
    def _dpad_motion(dx, dy) -> tuple[str | None, bool]:
        values = (dx, dy)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or
               not math.isfinite(value) for value in values):
            return None, True
        horizontal = -1 if dx <= -0.5 else 1 if dx >= 0.5 else 0
        vertical = -1 if dy <= -0.5 else 1 if dy >= 0.5 else 0
        active = bool(horizontal or vertical)
        if bool(horizontal) == bool(vertical):
            return None, active
        direction = ("left" if horizontal < 0 else "right") if horizontal else (
            "up" if vertical < 0 else "down")
        return EvaluationWebSession._DPAD_MOTIONS[direction], True

    def _apply_joystick_controls(self, axes: dict, buttons: dict, connected: bool,
                                 *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else float(now)
        lb_pressed = bool(buttons.get("l1", False))
        motion, dpad_active = self._dpad_motion(axes.get("dpad_x", 0.0),
                                                axes.get("dpad_y", 0.0))
        if not connected:
            self._joy_initialized = False
            self._lb_previous = False
            self._dpad_latched = False
            return

        first_sample = not self._joy_initialized
        self._joy_initialized = True
        source_is_joystick = self.state.snapshot()["source"] == "joystick"
        pressure = self._trigger_pressure(axes.get("l2"))
        command_error = None

        if source_is_joystick:
            requested_kp = 0.0 if pressure is None else 1.0 - pressure
            enabled = self.state.snapshot()["wbg"]["enabled"]
            if (not first_sample and lb_pressed and not self._lb_previous and
                    now - self._lb_last_toggle_at >= 0.15):
                enabled = not enabled
                self._lb_last_toggle_at = now
                self.set_wbg_enabled(enabled)
                self.state.mutate("wbg", enabled=enabled,
                                  activation=self.activation_snapshot())
            effective_kp = requested_kp if enabled else 0.0
            if abs(effective_kp - self.state.snapshot()["wbg"]["kp"]) > 1e-6:
                self.set_wbg_values({"kp": effective_kp})
                self.state.mutate("wbg", kp=effective_kp,
                                  activation=self.activation_snapshot())
            if pressure is None:
                command_error = "invalid L2 axis value"

            if not first_sample and dpad_active and not self._dpad_latched and motion:
                try:
                    self.state.set_text_command(motion, self, origin="joystick")
                    self.state.mutate("joy", motion=motion)
                except Exception as exc:
                    command_error = str(exc)

        self._lb_previous = lb_pressed
        self._dpad_latched = dpad_active
        self.state.mutate("joy", command_error=command_error)

    def after_step(self, step: int, env, _agent) -> None:
        now = time.perf_counter()
        fps = 0.0 if self._last_step_at is None else 1.0 / max(now - self._last_step_at, 1e-6)
        self._last_step_at = now
        self.state.update(step=step + 1, fps=round(fps, 1))
        if self.wbg is not None:
            self._sync_destination_state()
            self.state.mutate('wbg', telemetry=getattr(self.wbg, 'runtime_telemetry', {}))
        if getattr(env, "data", None) is not None:
            self._build_snapshot(env, step + 1, now)

    def _prepare_model_manifest(self, env) -> None:
        import mujoco
        xml_path = Path(env.config.xml_path).resolve()
        xml_bytes = xml_path.read_bytes()
        root = ET.fromstring(xml_bytes)
        compiler = root.find("compiler")
        mesh_dir = (xml_path.parent / (compiler.get("meshdir", "") if compiler is not None else "")).resolve()
        mesh_names = [node.get("file") for node in root.findall("./asset/mesh") if node.get("file")]
        self.model_files = {"model.xml": xml_path}
        for name in mesh_names:
            path = (mesh_dir / name).resolve()
            if path.parent != mesh_dir or not path.is_file():
                raise RuntimeError(f"invalid model asset: {name}")
            self.model_files[f"mesh/{name}"] = path
        files, aggregate = [], hashlib.sha256()
        for name, path in self.model_files.items():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            aggregate.update(f"{name}:{digest}\n".encode())
            files.append({"name": name, "sha256": digest, "bytes": path.stat().st_size,
                          "url": f"/api/model/{name}?sha256={digest}"})
        model = env.model
        root_pose = self._root_pose_manifest(model, mujoco)
        self.model_manifest = {
            "protocol": 1, "kind": "model_handshake", "python_mujoco": mujoco.__version__,
            "wasm_mujoco": "3.12.0", "model_sha256": hashlib.sha256(xml_bytes).hexdigest(),
            "asset_sha256": aggregate.hexdigest(), "nq": model.nq, "nv": model.nv,
            "nmocap": model.nmocap, "nuserdata": model.nuserdata, "header_bytes": 80,
            "snapshot_hz": round(1.0 / env.config.control_dt), "files": files,
            "root_pose": root_pose,
            "camera": self._camera_manifest(root_pose),
            "perturb": {"enabled": self.perturb_enabled,
                        "max_force": self.perturb_max_force,
                        "max_torque": self.perturb_max_torque,
                        "deadman_ms": round(self.perturb_timeout * 1000.0)},
        }

    def _root_pose_manifest(self, model, mujoco_module) -> dict:
        """Resolve root interpolation addresses independently of camera following."""
        config = self.camera_config
        manifest = {
            "schema": 1,
            "available": False,
            "body_name": config.body_name,
            "body_id": None,
            "position_qpos_adr": None,
            "quaternion_qpos_adr": None,
            "unavailable_reason": None,
        }
        body_id = int(mujoco_module.mj_name2id(
            model, mujoco_module.mjtObj.mjOBJ_BODY, config.body_name))
        if body_id < 0:
            manifest["unavailable_reason"] = "body_not_found"
            return manifest
        manifest["body_id"] = body_id

        try:
            joint_start = int(model.body_jntadr[body_id])
            joint_count = int(model.body_jntnum[body_id])
            free_type = getattr(mujoco_module.mjtJoint.mjJNT_FREE, "value",
                                mujoco_module.mjtJoint.mjJNT_FREE)
            free_joints = [joint_id for joint_id in range(joint_start, joint_start + joint_count)
                           if int(model.jnt_type[joint_id]) == int(free_type)]
        except (AttributeError, IndexError, TypeError, ValueError):
            free_joints = []
        if len(free_joints) != 1:
            manifest["unavailable_reason"] = "body_has_no_free_joint"
            return manifest

        position_adr = int(model.jnt_qposadr[free_joints[0]])
        if position_adr < 0 or position_adr + 7 > int(model.nq):
            manifest["unavailable_reason"] = "invalid_free_joint_qpos_address"
            return manifest
        manifest.update(
            available=True,
            position_qpos_adr=position_adr,
            quaternion_qpos_adr=position_adr + 3,
            unavailable_reason=None,
        )
        return manifest

    def _camera_manifest(self, root_pose: dict) -> dict:
        """Describe follow behavior while leaving root interpolation independent."""
        config = self.camera_config
        enabled = config.enabled and root_pose["available"]
        if not config.enabled:
            unavailable_reason = "disabled"
        else:
            unavailable_reason = None if enabled else root_pose["unavailable_reason"]
        return {
            "schema": 1,
            "enabled": enabled,
            "follow_yaw": enabled and config.follow_yaw,
            "lookat_offset": list(config.lookat_offset),
            "smoothing_tau": config.smoothing_tau,
            "unavailable_reason": unavailable_reason,
        }

    def _build_snapshot(self, env, seq: int, monotonic: float) -> None:
        data, model = env.data, env.model
        header = struct.pack(
            "<4sHHIIddIIII32s", b"MJS1", 1, 80, seq, 0, monotonic,
            float(data.time), model.nq, model.nv, model.nmocap,
            model.nuserdata, bytes.fromhex(self.model_manifest["model_sha256"]),
        )
        arrays = [self._display_qpos(data.qpos), data.qvel, data.mocap_pos.reshape(-1),
                  data.mocap_quat.reshape(-1), data.userdata]
        packet = header + b"".join(np.asarray(array, dtype="<f8").tobytes(order="C") for array in arrays)
        with self._snapshot_lock:
            self._snapshot, self._snapshot_seq = packet, seq

    def _display_qpos(self, qpos):
        """Return a browser-only root pose expressed in the controller frame."""
        if self.wbg is None or self.model_manifest is None:
            return qpos
        snapshot_fn = getattr(self.wbg, "destination_follow_snapshot", None)
        root_pose = self.model_manifest.get("root_pose", {})
        position_address = root_pose.get("position_qpos_adr")
        quaternion_address = root_pose.get("quaternion_qpos_adr")
        if not callable(snapshot_fn) or position_address is None or quaternion_address is None:
            return qpos
        destination = snapshot_fn()
        inputs = destination.get("inputs", {})
        controller_root = inputs.get("root_pos")
        controller_yaw = inputs.get("root_yaw")
        if not destination.get("enabled", False) or controller_root is None or controller_yaw is None:
            return qpos
        try:
            display = np.asarray(qpos, dtype=np.float64).copy()
            root = np.asarray(controller_root, dtype=np.float64)
            quaternion = display[quaternion_address:quaternion_address + 4]
            if root.shape != (3,) or quaternion.shape != (4,) or not np.isfinite(root).all():
                return qpos
            display[position_address:position_address + 3] = root
            display[quaternion_address:quaternion_address + 4] = self._quaternion_with_yaw(
                quaternion, controller_yaw)
            return display
        except (IndexError, TypeError, ValueError):
            return qpos

    @staticmethod
    def _quaternion_with_yaw(quaternion, yaw):
        """Preserve the simulated roll/pitch while replacing world yaw."""
        qw, qx, qy, qz = (float(value) for value in quaternion)
        norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
        yaw = float(yaw)
        if not math.isfinite(norm) or norm <= 1e-12 or not math.isfinite(yaw):
            raise ValueError("root orientation must be finite")
        qw, qx, qy, qz = (value / norm for value in (qw, qx, qy, qz))
        roll = math.atan2(2.0 * (qw * qx + qy * qz),
                          1.0 - 2.0 * (qx * qx + qy * qy))
        pitch = math.asin(max(-1.0, min(1.0, 2.0 * (qw * qy - qz * qx))))
        cy, sy = math.cos(yaw / 2.0), math.sin(yaw / 2.0)
        cp, sp = math.cos(pitch / 2.0), math.sin(pitch / 2.0)
        cr, sr = math.cos(roll / 2.0), math.sin(roll / 2.0)
        return np.array([
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ], dtype=np.float64)

    def snapshot_packet(self):
        with self._snapshot_lock:
            return self._snapshot_seq, self._snapshot

    def set_paused(self, paused: bool) -> None:
        if paused:
            self.clear_perturb()
            self._clear_applied_wrench()
        self._paused.set() if paused else self._paused.clear()

    def set_source(self, source: str) -> None:
        if source == "joystick" and self.joystick is None:
            raise RuntimeError("joystick unavailable")
        if source == "joystick" and self.wbg is not None:
            self.cancel_destination_follow()
        if source == 'web' and self.wbg is not None and self.state.snapshot()['source'] == 'joystick':
            for guidance in self.wbg._manager.guidances:
                guidance.activation.kp = self._configured_kp.get(id(guidance), guidance.activation.kp)

    def set_wbg_enabled(self, enabled: bool) -> None:
        if not enabled and self.wbg is not None:
            self.cancel_destination_follow()
        if self.wbg is not None:
            for guidance in self.wbg._manager.guidances:
                manual_axis = guidance.guidance_name.lower() in {'vx', 'vy', 'wz', 'hz'}
                guidance.activation.enabled = enabled and (manual_axis or self._original_enabled.get(id(guidance), False))

    def command_ranges(self) -> dict[str, list[float]]:
        ranges = {"vx": [-5.0, 5.0], "vy": [-4.0, 4.0], "wz": [-2.0, 2.0],
                  "hz": [0.3, 1.1], "kp": [0.0, 4.0]}
        if self.wbg is None:
            return ranges
        for guidance in self.wbg._manager.guidances:
            name = guidance.guidance_name.lower()
            if name.startswith(("vx", "vy", "wz")) and hasattr(guidance, "value_range"):
                key = name[:2]
                ranges[key] = [float(value) for value in guidance.value_range]
            elif name.startswith("hz") and hasattr(guidance, "z_range"):
                ranges["hz"] = [float(value) for value in guidance.z_range]
        destination = self.destination_follow_snapshot()
        if destination.get("enabled"):
            for axis in ("vx", "vy", "wz"):
                ranges[axis] = list(destination["config"][axis + "_range"])
        return ranges

    def activation_snapshot(self) -> dict:
        if self.wbg is None:
            return {"available": False, "guidances": []}
        G1_BODY_GROUPS, _BODY_ABBR, _G1_BODY_NAMES = self._body_metadata()
        profile_terms = list(getattr(getattr(self.wbg, "_term_resolver", None),
                                     "terms", []))
        result = []
        manager = self.wbg._manager
        with manager._lock:
            for index, guidance in enumerate(manager.guidances):
                activation = guidance.activation
                weights = activation.build_body_intensity(G1_BODY_GROUPS)
                result.append({
                    "index": index, "name": guidance.guidance_name,
                    "enabled": bool(activation.enabled), "kp": float(activation.kp),
                    "groups": [{"name": name, "value": float(value)}
                               for name, value in sorted(activation.group_intensities.items())],
                    "terms": [{"name": name,
                               "guided": name in activation.guided_terms,
                               "enabled": (name in activation.guided_terms and
                                           name not in activation.disabled_terms)}
                              for name in (profile_terms or activation.guided_terms)],
                    "bodies": [{"index": body, "name": _G1_BODY_NAMES[body],
                                "label": _BODY_ABBR[body], "weight": float(weights[body]),
                                "override": body in activation.body_intensity_overrides}
                               for body in range(30)],
                })
        return {"available": True, "guidances": result}

    @staticmethod
    def _body_metadata():
        from diffusion_policy.task_provider.whole_body_guidance.body_groups import (
            G1_BODY_GROUPS, _BODY_ABBR, _G1_BODY_NAMES,
        )
        return G1_BODY_GROUPS, _BODY_ABBR, _G1_BODY_NAMES

    def _guidance(self, index: int):
        if self.wbg is None or not 0 <= index < len(self.wbg._manager.guidances):
            raise RuntimeError("guidance unavailable")
        return self.wbg._manager.guidances[index]

    def set_guidance_enabled(self, index: int, enabled: bool) -> None:
        guidance = self._guidance(index)
        with self.wbg._manager._lock:
            guidance.activation.enabled = enabled
            self._original_enabled[id(guidance)] = enabled

    def set_guidance_group(self, index: int, group: str, value: float) -> None:
        guidance = self._guidance(index)
        with self.wbg._manager._lock:
            if group not in guidance.activation.group_intensities:
                raise RuntimeError(f"unknown guidance group: {group}")
            guidance.activation.group_intensities[group] = value

    def set_guidance_body(self, index: int, body: int, value: float) -> None:
        guidance = self._guidance(index)
        with self.wbg._manager._lock:
            guidance.activation.body_intensity_overrides[body] = value

    def toggle_guidance_body(self, index: int, body: int) -> None:
        """Mirror DebugPanel's click-to-toggle and redundant-override removal."""
        guidance = self._guidance(index)
        G1_BODY_GROUPS, _, _ = self._body_metadata()
        with self.wbg._manager._lock:
            activation = guidance.activation
            group_value = max(
                (activation.group_intensities.get(name, 0.0)
                 for name, indices in G1_BODY_GROUPS.items() if body in indices),
                default=0.0,
            )
            current = activation.body_intensity_overrides.get(body, group_value)
            value = 0.0 if current > 0.0 else 1.0
            if abs(value - group_value) < 0.001:
                activation.body_intensity_overrides.pop(body, None)
            else:
                activation.body_intensity_overrides[body] = value

    def set_guidance_term(self, index: int, term: str, enabled: bool) -> None:
        guidance = self._guidance(index)
        with self.wbg._manager._lock:
            profile_terms = set(getattr(getattr(self.wbg, "_term_resolver", None),
                                        "terms", guidance.activation.guided_terms))
            if term not in profile_terms:
                raise RuntimeError(f"unknown guidance term: {term}")
            if enabled:
                guidance.activation.disabled_terms.discard(term)
            else:
                guidance.activation.disabled_terms.add(term)

    def reset_guidance_activation(self, index: int) -> None:
        guidance = self._guidance(index)
        with self.wbg._manager._lock:
            activation = guidance.activation
            G1_BODY_GROUPS, _, _ = self._body_metadata()
            for group in G1_BODY_GROUPS:
                activation.group_intensities[group] = (
                    1.0 if group in activation.guided_body_groups else 0.0)
            activation.reset_overrides()

    def set_wbg_values(self, values: dict[str, float]) -> None:
        if self.wbg is None:
            return
        destination_snapshot = getattr(self.wbg, "destination_follow_snapshot", None)
        if callable(destination_snapshot) and destination_snapshot().get("enabled", False):
            self.cancel_destination_follow()
        kp = values.get("kp")
        for guidance in self.wbg._manager.guidances:
            if kp is not None:
                guidance.activation.kp = kp
            name = guidance.guidance_name.lower()
            key = next((item for item in ("vx", "vy", "wz", "hz") if name.startswith(item)), None)
            if key not in values:
                continue
            if key == "hz" and hasattr(guidance, "set_target"):
                guidance.set_target(values[key])
            elif hasattr(guidance, "set_value"):
                guidance.set_value(values[key])

    def set_destination_target(self, target) -> None:
        if self.wbg is None or not callable(getattr(self.wbg, "set_destination_target", None)):
            raise ProtocolError("destination follow unavailable")
        self.wbg.set_destination_target(target)

    def set_destination_config(self, values: dict) -> None:
        if self.wbg is None or not callable(getattr(self.wbg, "set_destination_config", None)):
            raise ProtocolError("destination follow unavailable")
        self.wbg.set_destination_config(values)
        self._sync_destination_state()

    def enable_destination_follow(self, enabled: bool) -> None:
        if self.wbg is None or not callable(getattr(self.wbg, "enable_destination_follow", None)):
            raise ProtocolError("destination follow unavailable")
        if enabled and self.state.snapshot()['source'] == 'joystick':
            # Destination control owns the axes; an idle joystick must not zero its gain.
            self.state.update(source='web')
            for guidance in self.wbg._manager.guidances:
                guidance.activation.kp = self._configured_kp.get(id(guidance), guidance.activation.kp)
        self.wbg.enable_destination_follow(enabled)
        destination_guidance = getattr(self.wbg, "_destination_guidance", None)
        if destination_guidance is not None:
            self._original_enabled[id(destination_guidance)] = bool(enabled)

    def cancel_destination_follow(self) -> None:
        if self.wbg is not None:
            cancel = getattr(self.wbg, "cancel_destination_follow", None)
            if not callable(cancel):
                return
            cancel()
        destination_guidance = getattr(self.wbg, "_destination_guidance", None) if self.wbg is not None else None
        if destination_guidance is not None:
            self._original_enabled[id(destination_guidance)] = False
        self._sync_destination_state()

    def destination_follow_snapshot(self) -> dict:
        if self.wbg is None:
            return {"available": False, "enabled": False, "target": None,
                    "status": "unavailable", "command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}}
        snapshot_fn = getattr(self.wbg, "destination_follow_snapshot", None)
        if not callable(snapshot_fn):
            return {"available": False, "enabled": False, "target": None,
                    "status": "unavailable", "command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}}
        snapshot = snapshot_fn()
        snapshot["available"] = True
        snapshot["render_target"] = self._destination_render_target(snapshot)
        snapshot["display_target"] = self._destination_display_target(snapshot)
        return snapshot

    def _destination_display_target(self, destination: dict):
        """Select the target for the frame used by the browser snapshot."""
        root_pose = (self.model_manifest or {}).get("root_pose", {})
        inputs = destination.get("inputs", {})
        if (destination.get("enabled", False) and inputs.get("root_pos") is not None
                and inputs.get("root_yaw") is not None
                and root_pose.get("position_qpos_adr") is not None
                and root_pose.get("quaternion_qpos_adr") is not None):
            return destination.get("target")
        return destination.get("render_target", destination.get("target"))

    def _destination_render_target(self, destination: dict):
        target = destination.get("target")
        inputs = destination.get("inputs", {})
        controller_root = inputs.get("root_pos")
        controller_yaw = inputs.get("root_yaw")
        root_pose = (self.model_manifest or {}).get("root_pose", {})
        position_address = root_pose.get("position_qpos_adr")
        quaternion_address = root_pose.get("quaternion_qpos_adr")
        qpos = getattr(getattr(self._env, "data", None), "qpos", None)
        if (target is None or controller_root is None or controller_yaw is None
                or position_address is None or quaternion_address is None or qpos is None):
            return target
        try:
            render_root = qpos[position_address:position_address + 3]
            qw, qx, qy, qz = (float(value) for value in qpos[
                quaternion_address:quaternion_address + 4])
            render_yaw = math.atan2(
                2.0 * (qw * qz + qx * qy),
                1.0 - 2.0 * (qy * qy + qz * qz),
            )
            return list(map_target_between_root_frames(
                target,
                controller_root,
                controller_yaw,
                render_root,
                render_yaw,
            ))
        except (IndexError, TypeError, ValueError):
            return target

    def _sync_destination_state(self) -> None:
        # Reuse the protocol state's atomic snapshot helper so activation
        # manager telemetry changes with the destination lifecycle as well.
        self.state._sync_destination(self)

    def destination_axis_snapshot(self) -> dict:
        snapshot = getattr(self.wbg, "destination_axis_snapshot", None)
        return snapshot() if callable(snapshot) else {}

    def set_text(self, text: str) -> None:
        provider = self._raw_provider()
        if provider is None or not hasattr(provider, "set_text"):
            raise ProtocolError("This policy has no text-conditioning provider; text commands are not supported")
        provider.set_text(text)

    def set_interp(self, text_a: str, text_b: str, weight: float) -> None:
        provider = self._raw_provider()
        if provider is None or not hasattr(provider, "set_interpolation"):
            raise ProtocolError("interpolation provider unavailable")
        provider.set_interpolation(text_a, text_b, weight)

    def set_interp_terms(self, terms: list[dict]) -> dict:
        """Apply a complete additive proposition snapshot to the CLIP provider."""
        provider = self._raw_provider()
        setter = getattr(provider, "set_interpolation_terms", None)
        if not callable(setter):
            raise ProtocolError("multi-axis interpolation provider unavailable")
        return setter(terms)

    def interpolation_snapshot(self) -> dict:
        provider = self._raw_provider()
        snapshot = getattr(provider, "get_interpolation_snapshot", None)
        if not callable(snapshot):
            return {"available": False, "normalize": True, "terms": []}
        return snapshot()

    def _raw_provider(self):
        provider = self.provider
        if hasattr(provider, "_providers"):
            provider = next((p for p in provider._providers if hasattr(p, "_clip_source")), provider)
        return getattr(provider, "_clip_source", provider)
