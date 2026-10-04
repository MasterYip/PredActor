"""Versioned, thread-safe state owner for the evaluation web interface."""

from __future__ import annotations

import copy
import threading
import time
from collections import deque
from typing import Any

from diffusion_policy.task_provider.clip_proposition import (
    describe_interpolation_terms,
    validate_interpolation_terms,
)

PROTOCOL_VERSION = 1
_COMMANDS = {
    "pause", "resume", "set_source", "set_wbg", "set_wbg_enabled", "set_text", "set_interp",
    "set_interp_terms",
    "set_destination", "set_destination_enabled", "set_destination_config", "cancel_destination",
    "set_guidance_enabled", "set_guidance_group", "set_guidance_body", "set_guidance_term",
    "toggle_guidance_body", "reset_guidance_activation",
    "reset_simulation", "set_auto_reset",
    "set_perturb", "clear_perturb",
}
_FAST_COMMANDS = {"set_wbg", "set_interp", "set_interp_terms", "set_guidance_group", "set_guidance_body", "set_perturb"}


class ProtocolError(ValueError):
    pass


class PerturbSequenceError(ProtocolError):
    def __init__(self, current_sequence: int) -> None:
        self.current_sequence = int(current_sequence)
        super().__init__("stale perturb sequence")


class EvaluationState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._seq = 0
        self._last_command_at: dict[str, float] = {}
        self._history: deque[dict[str, Any]] = deque(maxlen=32)
        self._state = {
            "protocol": PROTOCOL_VERSION, "status": "loading", "paused": False,
            "step": 0, "fps": 0.0, "source": "web", "error": None,
            "wbg": {"enabled": True, "kp": 1.0,
                    "values": {"vx": 0.0, "vy": 0.0, "wz": 0.0, "hz": 0.75},
                    "ranges": {"vx": [-5.0, 5.0], "vy": [-4.0, 4.0],
                               "wz": [-2.0, 2.0], "hz": [0.3, 1.1], "kp": [0.0, 4.0]},
                    "activation": {"available": False, "guidances": []}},
            "text": {
                "mode": "textop", "current": "walking forward", "history": [],
                "interpolation": {"available": False, "normalize": True, "terms": []},
            },
            "joy": {"connected": False, "axes": {}, "buttons": {}, "dpad": [0.0, 0.0],
                    "motion": None, "command_error": None, "connection_error": None,
                    "device_path": None, "mapping": None},
            "destination": {"available": False, "enabled": False, "target": None,
                             "status": "unavailable", "distance": None,
                             "heading_error": None, "pose_available": False,
                             "command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}},
            "perturb": {"enabled": False, "active": False, "selected_body": None,
                        "mode": None, "generation": 0, "sequence": 0,
                        "drag": [0.0, 0.0], "force": [0.0, 0.0, 0.0],
                        "torque": [0.0, 0.0, 0.0]},
            "simulation": {"auto_reset": True, "reset_pending": False,
                           "reset_count": 0, "last_reset_reason": None},
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            result = copy.deepcopy(self._state)
            result.update(seq=self._seq, server_time=time.time())
            result["text"]["history"] = list(self._history)
            return result

    def update(self, **values: Any) -> None:
        with self._lock:
            self._state.update(values)
            self._seq += 1

    def mutate(self, section: str, **values: Any) -> None:
        with self._lock:
            self._state[section].update(values)
            self._seq += 1

    @staticmethod
    def _cancel_destination(controller: Any) -> None:
        """Cancel destination mode when the controller exposes that optional API."""
        cancel = getattr(controller, "cancel_destination_follow", None)
        if callable(cancel):
            cancel()

    @staticmethod
    def _destination_available(controller: Any) -> bool:
        return all(callable(getattr(controller, name, None)) for name in (
            "set_destination_target", "enable_destination_follow",
            "cancel_destination_follow", "destination_follow_snapshot"))

    def set_text_command(self, text: str, controller: Any, *, origin: str = "web") -> None:
        text = str(text).strip()
        if not text or len(text) > 240:
            raise ProtocolError("text must contain 1-240 characters")
        started = time.perf_counter()
        controller.set_text(text)
        item = {"mode": "textop", "text": text, "origin": origin, "status": "applied",
                "latency_ms": round((time.perf_counter() - started) * 1000.0, 2)}
        with self._lock:
            self._history.appendleft(item)
            self._state["text"].update(mode="textop", current=text)
            self._seq += 1

    def set_interpolation_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Hydrate the protocol from provider-owned interpolation state."""
        if not isinstance(snapshot, dict):
            raise ProtocolError("invalid interpolation snapshot")
        available = snapshot.get("available", False)
        normalize = snapshot.get("normalize", True)
        if not isinstance(available, bool) or not isinstance(normalize, bool):
            raise ProtocolError("invalid interpolation snapshot")
        try:
            terms = describe_interpolation_terms(snapshot.get("terms", [])) if available else []
        except ValueError as exc:
            raise ProtocolError(str(exc)) from exc
        self.mutate("text", interpolation={
            "available": available,
            "normalize": normalize,
            "terms": terms,
        })

    def apply(self, payload: dict[str, Any], controller: Any) -> dict[str, Any]:
        if not isinstance(payload, dict) or payload.get("protocol") != PROTOCOL_VERSION:
            raise ProtocolError("unsupported protocol")
        command = payload.get("command")
        if command not in _COMMANDS:
            raise ProtocolError("unknown command")
        now = time.monotonic()
        if now - self._last_command_at.get(command, 0.0) < (0.025 if command in _FAST_COMMANDS else 0.08):
            raise ProtocolError("command rate limited")
        self._last_command_at[command] = now

        if command in {"pause", "resume"}:
            paused = command == "pause"
            controller.set_paused(paused)
            self.update(paused=paused, status="paused" if paused else "running")
        elif command == "set_source":
            source = payload.get("source")
            if source not in {"web", "joystick"}:
                raise ProtocolError("source must be web or joystick")
            controller.set_source(source)
            self.update(source=source)
        elif command == "set_wbg_enabled":
            enabled = payload.get("enabled")
            if not isinstance(enabled, bool):
                raise ProtocolError("enabled must be boolean")
            controller.set_wbg_enabled(enabled)
            if not enabled:
                self._cancel_destination(controller)
            self.mutate("wbg", enabled=enabled, activation=self._activation_snapshot(controller))
            self._sync_destination(controller)
        elif command == "set_wbg":
            values = payload.get("values")
            if not isinstance(values, dict) or not values or not set(values) <= {"vx", "vy", "wz", "hz", "kp"}:
                raise ProtocolError("invalid WBG values")
            clean = {}
            for key, value in values.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ProtocolError("WBG values must be numeric")
                with self._lock:
                    lo, hi = self._state["wbg"]["ranges"][key]
                clean[key] = max(float(lo), min(float(hi), float(value)))
            controller.set_wbg_values(clean)
            # A manual slider edit is an explicit request to leave automatic
            # destination mode. The destination target is cleared and the
            # corresponding UI state is updated below.
            self._cancel_destination(controller)
            activation = self._activation_snapshot(controller)
            with self._lock:
                self._state["wbg"]["kp"] = clean.get("kp", self._state["wbg"]["kp"])
                self._state["wbg"]["values"].update({k: v for k, v in clean.items() if k != "kp"})
                self._state["wbg"]["activation"] = activation
                self._seq += 1
            self._sync_destination(controller)
        elif command == "set_destination":
            if not self._destination_available(controller):
                raise ProtocolError("destination follow unavailable")
            target = payload.get("target")
            if not isinstance(target, list) or len(target) != 3:
                raise ProtocolError("destination target must contain x, y, z")
            try:
                target = [float(value) for value in target]
            except (TypeError, ValueError) as exc:
                raise ProtocolError("destination target must be numeric") from exc
            import math
            if (not all(math.isfinite(value) for value in target)
                    or any(abs(value) > 100.0 for value in target)):
                raise ProtocolError("destination target must be finite and within +/-100 m")
            enabled = payload.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ProtocolError("destination enabled must be boolean")
            try:
                controller.set_destination_target(target)
            except (TypeError, ValueError) as exc:
                raise ProtocolError(str(exc)) from exc
            controller.enable_destination_follow(enabled)
            self._sync_destination(controller)
        elif command == "set_destination_enabled":
            if not self._destination_available(controller):
                raise ProtocolError("destination follow unavailable")
            enabled = payload.get("enabled")
            if not isinstance(enabled, bool):
                raise ProtocolError("destination enabled must be boolean")
            if enabled and self.snapshot()["destination"].get("target") is None:
                raise ProtocolError("set a destination target before enabling follow")
            controller.enable_destination_follow(enabled)
            self._sync_destination(controller)
        elif command == "set_destination_config":
            if not callable(getattr(controller, "set_destination_config", None)):
                raise ProtocolError("destination follow unavailable")
            values = payload.get("values")
            if not isinstance(values, dict) or not values:
                raise ProtocolError("destination config must be a non-empty mapping")
            try:
                controller.set_destination_config(values)
            except (TypeError, ValueError) as exc:
                raise ProtocolError(str(exc)) from exc
            self._sync_destination(controller)
        elif command == "cancel_destination":
            self._cancel_destination(controller)
            self._sync_destination(controller)
        elif command == "reset_simulation":
            controller.request_reset()
            self.mutate("simulation", reset_pending=True)
        elif command == "set_auto_reset":
            enabled = payload.get("enabled")
            if not isinstance(enabled, bool):
                raise ProtocolError("auto reset enabled must be boolean")
            controller.set_auto_reset(enabled)
            self.mutate("simulation", auto_reset=enabled)
        elif (command.startswith("set_guidance_") or
              command in {"toggle_guidance_body", "reset_guidance_activation"}):
            index = payload.get("index")
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                raise ProtocolError("guidance index must be a non-negative integer")
            if command == "set_guidance_enabled":
                enabled = payload.get("enabled")
                if not isinstance(enabled, bool):
                    raise ProtocolError("enabled must be boolean")
                controller.set_guidance_enabled(index, enabled)
            elif command == "set_guidance_group":
                name, value = payload.get("group"), payload.get("value")
                if not isinstance(name, str) or not name or isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ProtocolError("invalid guidance group update")
                controller.set_guidance_group(index, name, max(0.0, min(1.0, float(value))))
            elif command == "set_guidance_body":
                body, value = payload.get("body"), payload.get("value")
                if isinstance(body, bool) or not isinstance(body, int) or not 0 <= body < 30:
                    raise ProtocolError("body must be an integer from 0 to 29")
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ProtocolError("body intensity must be numeric")
                controller.set_guidance_body(index, body, max(0.0, min(1.0, float(value))))
            elif command == "toggle_guidance_body":
                body = payload.get("body")
                if isinstance(body, bool) or not isinstance(body, int) or not 0 <= body < 30:
                    raise ProtocolError("body must be an integer from 0 to 29")
                controller.toggle_guidance_body(index, body)
            elif command == "set_guidance_term":
                term, enabled = payload.get("term"), payload.get("enabled")
                if not isinstance(term, str) or not term or not isinstance(enabled, bool):
                    raise ProtocolError("invalid guidance term update")
                controller.set_guidance_term(index, term, enabled)
            else:
                controller.reset_guidance_activation(index)
            self.mutate("wbg", activation=self._activation_snapshot(controller))
        elif command == "set_perturb":
            controller.set_perturb_intent(payload)
            self.mutate("perturb", active=True, selected_body=payload.get("body"),
                        mode=payload.get("mode"), sequence=payload.get("seq"),
                        drag=list(payload.get("drag", [0.0, 0.0])))
        elif command == "clear_perturb":
            controller.clear_perturb()
            self.mutate("perturb", active=False, mode=None, drag=[0.0, 0.0],
                        force=[0.0, 0.0, 0.0], torque=[0.0, 0.0, 0.0])
        elif command == "set_text":
            self.set_text_command(payload.get("text", ""), controller, origin="web")
        elif command == "set_interp_terms":
            live = payload.get("live", False)
            if not isinstance(live, bool):
                raise ProtocolError("live must be boolean")
            try:
                terms = validate_interpolation_terms(payload.get("terms"))
            except ValueError as exc:
                raise ProtocolError(str(exc)) from exc
            started = time.perf_counter()
            accepted = controller.set_interp_terms(terms)
            if not isinstance(accepted, dict):
                accepted = controller.interpolation_snapshot()
            try:
                accepted_terms = describe_interpolation_terms(accepted.get("terms"))
            except (AttributeError, ValueError) as exc:
                raise ProtocolError("provider returned an invalid interpolation snapshot") from exc
            interpolation = {
                "available": True,
                "normalize": bool(accepted.get("normalize", True)),
                "terms": accepted_terms,
            }
            active = [term for term in accepted_terms if term["weight"] != 0]
            summary = " + ".join(
                f"{term['text_a'] or 'ZERO'} -> {term['text_b'] or 'ZERO'} @ {term['weight']:.2f}"
                for term in active
            ) or "zero semantic vector"
            item = {
                "mode": "interp", "text": summary, "terms": len(accepted_terms),
                "status": "applied",
                "latency_ms": round((time.perf_counter() - started) * 1000.0, 2),
            }
            with self._lock:
                if not live:
                    self._history.appendleft(item)
                self._state["text"].update(
                    mode="interp", current=summary, interpolation=interpolation)
                self._seq += 1
        else:
            text_a, text_b, weight = str(payload.get("text_a", "")).strip(), str(payload.get("text_b", "")).strip(), payload.get("weight")
            if not text_a or not text_b or len(text_a) > 120 or len(text_b) > 120:
                raise ProtocolError("interpolation texts must contain 1-120 characters")
            if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                raise ProtocolError("weight must be numeric")
            weight = max(0.0, min(1.0, float(weight))); started = time.perf_counter()
            controller.set_interp(text_a, text_b, weight)
            live = payload.get("live", False)
            if not isinstance(live, bool):
                raise ProtocolError("live must be boolean")
            item = {"mode": "interp", "text": f"{text_a} -> {text_b}", "weight": weight,
                    "status": "applied", "latency_ms": round((time.perf_counter() - started) * 1000.0, 2)}
            with self._lock:
                if not live:
                    self._history.appendleft(item)
                self._state["text"].update(mode="interp", current=item["text"], weight=weight); self._seq += 1
        return self.snapshot()

    def _activation_snapshot(self, controller: Any) -> dict[str, Any]:
        snapshot = getattr(controller, "activation_snapshot", None)
        if callable(snapshot):
            return snapshot()
        with self._lock:
            return copy.deepcopy(self._state["wbg"]["activation"])

    def _sync_destination(self, controller: Any) -> None:
        snapshot = getattr(controller, "destination_follow_snapshot", None)
        with self._lock:
            if callable(snapshot):
                value = copy.deepcopy(snapshot())
                value["available"] = True
                self._state["destination"] = value
            else:
                self._state["destination"] = {
                    "available": False, "enabled": False, "target": None,
                    "status": "unavailable", "distance": None,
                    "heading_error": None, "pose_available": False,
                    "command": {"vx": 0.0, "vy": 0.0, "wz": 0.0},
                }
            activation = getattr(controller, "activation_snapshot", None)
            if callable(activation):
                self._state["wbg"]["activation"] = copy.deepcopy(activation())
                self._state["wbg"]["enabled"] = any(
                    item.get("enabled", False)
                    for item in self._state["wbg"]["activation"].get("guidances", []))
            ranges = getattr(controller, "command_ranges", None)
            if callable(ranges):
                self._state["wbg"]["ranges"] = copy.deepcopy(ranges())
            axes = getattr(controller, "destination_axis_snapshot", None)
            if callable(axes):
                self._state["wbg"]["axis_commands"] = copy.deepcopy(axes())
                if self._state["destination"].get("enabled"):
                    for axis, record in self._state["wbg"]["axis_commands"].items():
                        self._state["wbg"]["values"][axis] = record["value"]
                    first = next(iter(self._state["wbg"]["axis_commands"].values()), {})
                    if "kp" in first:
                        self._state["wbg"]["kp"] = first["kp"]
            self._seq += 1
