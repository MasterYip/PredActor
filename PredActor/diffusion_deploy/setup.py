from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent

setup(
    name="diffusion-deploy-manager",
    version="0.1.0",
    description="Pinned user-local deployment manager for diffusion_deploy",
    packages=find_packages("python"),
    package_dir={"": "python"},
    data_files=[("share/diffusion_deploy/deps", ["deps/platform-lock.json"])],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["diffusion-deploy=diffusion_deploy_manager.cli:main"]},
)
