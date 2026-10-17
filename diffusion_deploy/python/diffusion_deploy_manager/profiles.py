import json
import os
import platform
import re
import shutil
import sys
from pathlib import Path


class ProfileError(RuntimeError):
    pass


def discover_cuda_compiler(path_value=None, fixed_candidates=None):
    """Find nvcc without changing the machine or the caller's PATH."""
    path_value = os.environ.get("PATH", "") if path_value is None else path_value
    candidates = []
    discovered = shutil.which("nvcc", path=path_value)
    if discovered:
        candidates.append(Path(discovered))
    candidates.extend(Path(item) for item in (
        fixed_candidates if fixed_candidates is not None
        else ("/usr/local/cuda/bin/nvcc",)
    ))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            # Keep JetPack's stable /usr/local/cuda path. Resolving that symlink
            # to /usr/local/cuda-X.Y makes Caffe2 report two conflicting CUDA
            # installs even though both paths name the same toolkit.
            return Path(os.path.abspath(candidate))
    raise ProfileError(
        "nvcc not found in PATH or /usr/local/cuda/bin/nvcc; JetPack CUDA toolkit is required")


def default_lock_path():
    candidates = [
        Path(__file__).resolve().parents[2] / "deps" / "platform-lock.json",
        Path(sys.argv[0]).resolve().parents[1] / "share" / "diffusion_deploy" / "deps" / "platform-lock.json",
        Path(sys.prefix) / "share" / "diffusion_deploy" / "deps" / "platform-lock.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ProfileError("platform-lock.json not found; pass --lock explicitly")


def load_lock(path=None):
    lock_path = Path(path) if path else default_lock_path()
    with lock_path.open("r", encoding="utf-8") as stream:
        lock = json.load(stream)
    if lock.get("schema_version") != 1:
        raise ProfileError("unsupported platform lock schema")
    return lock_path.resolve(), lock


def _os_release(path=Path("/etc/os-release")):
    values = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
    return values


def _l4t_release(path=Path("/etc/nv_tegra_release")):
    if not path.is_file():
        return None
    match = re.search(r"R(\d+)\s+\(release\),\s+REVISION:\s*([\d.]+)",
                      path.read_text(encoding="utf-8", errors="replace"))
    return f"{match.group(1)}.{match.group(2)}" if match else None


def detect_tuple(os_release_path=Path("/etc/os-release"), l4t_path=Path("/etc/nv_tegra_release")):
    os_release = _os_release(os_release_path)
    return {
        "system": platform.system(),
        "architecture": platform.machine(),
        "os_id": os_release.get("ID"),
        "os_version": os_release.get("VERSION_ID"),
        "l4t_release": _l4t_release(l4t_path),
        "python": f"{platform.python_version_tuple()[0]}.{platform.python_version_tuple()[1]}",
    }


def propose_profile(lock, detected):
    candidates = []
    for name, profile in lock["profiles"].items():
        keys = ("system", "architecture", "os_id", "os_version")
        if all(profile.get(key) == detected.get(key) for key in keys):
            expected_l4t = profile.get("l4t_release")
            if expected_l4t is None or expected_l4t == detected.get("l4t_release"):
                candidates.append(name)
    return candidates[0] if len(candidates) == 1 else None


def require_profile(lock, name, detected=None, strict=True):
    if not name or name not in lock["profiles"]:
        raise ProfileError("explicit --profile must name a locked profile")
    profile_spec = lock["profiles"][name]
    if strict:
        detected = detected or detect_tuple()
        keys = ["system", "architecture", "os_id", "os_version", "l4t_release", "python"]
        mismatch = {key: (profile_spec.get(key), detected.get(key)) for key in keys
                    if profile_spec.get(key) != detected.get(key)}
        if mismatch:
            raise ProfileError(f"profile tuple mismatch: {mismatch}")
    return profile_spec
