"""
Utilities for enforcing and measuring realtime loops.

`RealtimeLooper` keeps a moving window of loop durations to report loop rate and
realtime factor (simulated dt divided by wall-clock dt). The accompanying
`realtime_loop` decorator wraps any function that represents a single control
interval, optionally sleeping to maintain a target period.
"""

import functools
import time
from collections import deque
from typing import Callable, Optional


class RealtimeLooper:
	"""Tracks loop timing and optionally enforces a target period."""

	def __init__(
		self,
		name: str = "loop",
		window_size: int = 50,
		print_interval: float = 2.0,
		logger: Optional[Callable[[str], None]] = None,
	):
		self.name = name
		self.window_size = max(1, window_size)
		self.print_interval = max(0.0, print_interval)
		self.logger = logger or print

		self._dts = deque(maxlen=self.window_size)
		self._last_log_time = time.time()
		self._target_dt = None
		self._enforce = True

	def record(self, start_time: float, target_dt: float, enforce: bool = True) -> float:
		"""
		Record one loop iteration, optionally sleeping to meet the target period.

		Args:
			start_time: Wall-clock time captured immediately before the loop body.
			target_dt: Desired duration of a loop iteration in seconds.
			enforce: If True, sleep the remaining time to hit the target period.

		Returns:
			The actual wall-clock duration of the loop iteration (seconds).
		"""
		self._target_dt = target_dt
		self._enforce = enforce

		elapsed = time.time() - start_time
		if enforce and target_dt is not None:
			sleep_time = max(0.0, target_dt - elapsed)
			if sleep_time > 0.0:
				time.sleep(sleep_time)

		end_time = time.time()
		loop_dt = end_time - start_time
		self._dts.append(loop_dt)

		self._maybe_log(end_time)
		return loop_dt

	def _maybe_log(self, now: float) -> None:
		if self.print_interval <= 0:
			return
		if now - self._last_log_time < self.print_interval:
			return

		if not self._dts:
			return

		hz = self.current_hz
		rtf = self.realtime_factor
		min_factor = self._target_dt / max(self._dts) if self._target_dt else 0.0
		max_factor = self._target_dt / min(self._dts) if self._target_dt else 0.0
		self.logger(
			f"[{self.name}] rate: {hz:.2f} Hz | rtf: {rtf:.2f}x "
			f"(min: {min_factor:.2f}x, max: {max_factor:.2f}x)"
		)
		self._last_log_time = now

	@property
	def current_hz(self) -> float:
		if not self._dts:
			return 0.0
		mean_dt = sum(self._dts) / len(self._dts)
		return 1.0 / mean_dt if mean_dt > 0 else 0.0

	@property
	def realtime_factor(self) -> float:
		if not self._dts or not self._target_dt:
			return 0.0
		mean_dt = sum(self._dts) / len(self._dts)
		return self._target_dt / mean_dt if mean_dt > 0 else 0.0

	def snapshot(self) -> dict:
		"""Return a lightweight summary of recent timing stats."""
		return {
			"target_dt": self._target_dt,
			"enforcing": self._enforce,
			"hz": self.current_hz,
			"realtime_factor": self.realtime_factor,
		}


def _resolve_value(candidate, obj, args, kwargs):
	if callable(candidate):
		return candidate(obj, *args, **kwargs)
	if isinstance(candidate, str) and obj is not None:
		return getattr(obj, candidate, None)
	return candidate


def realtime_loop(
	expected_hz: Optional[float] = None,
	expected_dt: Optional[float] = None,
	*,
	name: str = "loop",
	window_size: int = 50,
	print_interval: float = 2.0,
	enable_attr: Optional[str] = None,
	logger: Optional[Callable[[str], None]] = None,
):
	"""
	Decorator to enforce and measure a realtime control loop.

	The target period can be provided directly (`expected_dt`), as a frequency
	(`expected_hz`), or fetched from the instance via `expected_dt`/`expected_hz`
	when passed as attribute names. Setting `enable_attr` to an attribute name on
	the bound instance allows toggling enforcement (e.g., `self.realtime_mode`).
	"""

	def decorator(func):
		looper = RealtimeLooper(name=name, window_size=window_size, print_interval=print_interval, logger=logger)

		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			obj = args[0] if args else None
			resolved_dt = _resolve_value(expected_dt, obj, args, kwargs)
			resolved_hz = _resolve_value(expected_hz, obj, args, kwargs)

			if resolved_dt is None:
				if resolved_hz:
					resolved_dt = 1.0 / resolved_hz
				else:
					raise ValueError("Either expected_dt or expected_hz must be provided to realtime_loop")

			enforce = True
			if enable_attr and obj is not None:
				enforce = bool(getattr(obj, enable_attr, True))

			start = time.time()
			result = func(*args, **kwargs)
			looper.record(start_time=start, target_dt=resolved_dt, enforce=enforce)
			return result

		wrapper._realtime_looper = looper  # Expose metrics to callers
		return wrapper

	return decorator
