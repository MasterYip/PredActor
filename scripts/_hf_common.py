"""Shared utilities for the manifest-driven Hugging Face sync scripts."""

import hashlib
import os
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
DEFAULT_MANIFEST = SCRIPTS_DIR / "hf_manifest.yaml"


def load_manifest(path=None) -> dict:
    """Load and return the parsed YAML manifest."""
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. Run: pip install pyyaml")
        sys.exit(1)

    manifest_path = Path(path) if path else DEFAULT_MANIFEST
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    if "repo_id" not in data:
        print("ERROR: manifest is missing 'repo_id' field.")
        sys.exit(1)
    if data.get("repo_type", "model") not in {"model", "dataset", "space"}:
        print("ERROR: manifest repo_type must be model, dataset, or space.")
        sys.exit(1)
    if "entries" not in data or not isinstance(data["entries"], list):
        print("ERROR: manifest is missing 'entries' list.")
        sys.exit(1)

    for i, e in enumerate(data["entries"]):
        for field in ("hf_path", "local_path"):
            if field not in e:
                print(f"ERROR: entry #{i} is missing required field '{field}'.")
                sys.exit(1)
        if e.get("kind", "directory") not in {"file", "directory"}:
            print(f"ERROR: entry #{i} kind must be file or directory.")
            sys.exit(1)

    return data


def resolve_local(local_path: str, repo_root: Path) -> Path:
    """Resolve a manifest local_path (relative to repo root) to an absolute Path."""
    p = Path(local_path)
    return p.resolve() if p.is_absolute() else (repo_root / p).resolve()


def display_local(path: Path, repo_root: Path) -> str:
    """Return a stable display path, including sibling artifact directories."""
    return os.path.relpath(path, repo_root)


def entry_size(path: Path) -> int:
    """Return the byte size of a mapped file or directory tree."""
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_entry(entry: dict, local: Path) -> None:
    """Enforce optional manifest size and SHA-256 contracts."""
    checks = []
    if entry.get("kind", "directory") == "file":
        checks.append((Path("."), entry))
    for relative, contract in entry.get("files", {}).items():
        checks.append((Path(relative), contract))

    for relative, contract in checks:
        target = local if relative == Path(".") else local / relative
        if not target.is_file():
            raise RuntimeError(f"missing mapped file: {target}")
        expected_size = contract.get("size_bytes")
        if expected_size is not None and target.stat().st_size != int(expected_size):
            raise RuntimeError(
                f"size mismatch for {target}: expected {expected_size}, "
                f"found {target.stat().st_size}")
        expected_hash = contract.get("sha256")
        if expected_hash is not None:
            actual = sha256(target)
            if actual.lower() != str(expected_hash).lower():
                raise RuntimeError(
                    f"SHA-256 mismatch for {target}: expected {expected_hash}, found {actual}")


def prompt_huggingface_hub():
    """Import and return HfApi class, with a friendly install hint on failure."""
    try:
        from huggingface_hub import HfApi
        return HfApi
    except ImportError:
        print("ERROR: huggingface_hub not installed.\n"
              "  Run:  pip install huggingface_hub\n"
              "  Then: huggingface-cli login")
        sys.exit(1)


def enable_hf_transfer():
    """
    Activate hf_transfer (Rust-backed multi-part uploader).
    Must be called BEFORE importing huggingface_hub for the first time.
    Installs the package automatically if it is missing.
    """
    import os
    import subprocess

    # The env-var must be set before huggingface_hub is imported.
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

    try:
        import hf_transfer  # noqa: F401 – just check it's importable
    except ImportError:
        print("hf_transfer not found – installing…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "hf_transfer"]
        )
        print("hf_transfer installed.")
