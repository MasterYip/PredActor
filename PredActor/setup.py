from setuptools import find_packages
from distutils.core import setup

setup(
  name = "diffusion_policy",
  version="1.0.1",
  packages = find_packages(),
  install_requires=["diffusers", "huggingface_hub==0.23",
                    "numpy==1.26.4",
                    "dill", "torch", 
                    "zarr", "hydra.core", 
                    "wandb", "seaborn",
                    "numba", "tqdm", "scipy",
                    "pin", "mujoco", "mujoco-python-viewer",
                    "pytorch-kinematics", "customtkinter",
                    "fastapi", "uvicorn"],
)
