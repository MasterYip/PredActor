from diffusion_policy.env.base_env import BaseEnv, ObsTermSpec
from importlib import import_module


def __getattr__(name):
	if name != "IsaacLabEnv":
		raise AttributeError(name)
	value = getattr(import_module(".isaaclab_env", __name__), name)
	globals()[name] = value
	return value

__all__ = [
	"BaseEnv",
	"ObsTermSpec",
	"IsaacLabEnv",
]
