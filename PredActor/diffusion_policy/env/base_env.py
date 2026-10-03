from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import torch


ObsTerms = Dict[str, torch.Tensor]


@dataclass(frozen=True)
class ObsTermSpec:
	"""Describes one observation term exposed by an environment."""

	name: str
	feature_dim: int
	description: str = ""


class BaseEnv(ABC):
	"""Common environment interface used by dataset composer + runners.

	Implementations can keep existing internals but should expose observations
	as a dictionary of named terms with shape [B, T, ...] compatible with
	`ObsComposer`.
	"""

	@abstractmethod
	def initialize(self):
		"""Initialize environment resources (sim, SDK, communication)."""

	@abstractmethod
	def close(self):
		"""Release environment resources."""

	@abstractmethod
	def reset(self, target_pos: Optional[np.ndarray] = None):
		"""Reset environment state and return initial observation."""

	@abstractmethod
	def step(self, action: np.ndarray, action_is_isaaclab_order: bool = False) -> Tuple[dict, float, bool, dict]:
		"""Execute one control step."""

	@abstractmethod
	def get_obs_terms(self, last_actions: Optional[np.ndarray] = None) -> ObsTerms:
		"""Return observation terms used by policy composition/normalization."""

	def get_obs(self, terms: Optional[ObsTerms] = None, last_actions: Optional[np.ndarray] = None) -> ObsTerms:
		"""Convenience accessor for callers that only need composed terms."""
		if terms is not None:
			return terms
		return self.get_obs_terms(last_actions=last_actions)

	def is_running(self) -> bool:
		"""Whether the environment runtime is still active."""
		return True

	def check_terminate(self) -> bool:
		"""Return True if the episode should be reset (e.g. robot fell).
		Default: never terminate early. Override in subclasses as needed."""
		return False

	def get_step_dt(self) -> Optional[float]:
		"""Control period used by realtime loop enforcement, when available."""
		return None

	@classmethod
	def obs_term_specs(cls) -> Dict[str, ObsTermSpec]:
		"""Optional static specs for UI/docs/debugging. Override as needed."""
		return {
			"body_pos": ObsTermSpec("body_pos", 90, "30 body positions in world/body frame layout"),
			"body_rot": ObsTermSpec("body_rot", 120, "30 body quaternions"),
			"body_lin_vel": ObsTermSpec("body_lin_vel", 90, "30 body linear velocities"),
			"body_ang_vel": ObsTermSpec("body_ang_vel", 90, "30 body angular velocities"),
			"joint_pos": ObsTermSpec("joint_pos", 29, "Joint positions in IsaacLab order"),
			"joint_vel": ObsTermSpec("joint_vel", 29, "Joint velocities in IsaacLab order"),
			"root_pos": ObsTermSpec("root_pos", 3, "Root position"),
			"root_rot": ObsTermSpec("root_rot", 4, "Root quaternion (wxyz)"),
			"projected_gravity": ObsTermSpec("projected_gravity", 3, "Gravity direction in body frame"),
			"base_lin_vel": ObsTermSpec("base_lin_vel", 3, "Base linear velocity"),
			"base_ang_vel": ObsTermSpec("base_ang_vel", 3, "Base angular velocity"),
			"last_actions": ObsTermSpec("last_actions", 29, "Previous action"),
		}

