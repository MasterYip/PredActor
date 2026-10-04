#!/usr/bin/env python3
"""
Download mapped resources from the PredActor Artifacts Hugging Face repository.
All paths and the repo ID are read from scripts/hf_manifest.yaml.

Usage:
  python scripts/hf_download.py
  python scripts/hf_download.py --repo MasterYip/PredActor_Artifacts
  python scripts/hf_download.py --filter checkpoints
  python scripts/hf_download.py --filter checkpoints/predactor
  python scripts/hf_download.py --list
  python scripts/hf_download.py --dry-run
  python scripts/hf_download.py --no-skip-download
  python scripts/hf_download.py --full       # re-download entire folder (old behavior)
"""

import argparse
import shutil
import sys
from pathlib import Path
from _hf_common import (
    display_local, entry_size, load_manifest, resolve_local,
    prompt_huggingface_hub, verify_entry,
)


def _check_entry(api, repo_id: str, repo_type: str, entry: dict, local: Path):
    """
    Compare HF repo contents against the local directory by filename + size.

    Returns:
        (status, missing_hf_paths)

        status:
          "ok"       — all HF files are present locally with matching sizes
          "partial"  — local dir exists but some files are missing or size-mismatched
          "absent"   — local dir does not exist at all

        missing_hf_paths:
          list of HF repo paths (str) that need to be downloaded
    """
    hf_path = entry["hf_path"]
    kind = entry.get("kind", "directory")
    if kind == "file":
        try:
            info = api.repo_info(repo_id=repo_id, repo_type=repo_type, files_metadata=True)
            remote = next((item for item in info.siblings if item.rfilename == hf_path), None)
        except Exception:
            return "absent", []
        if remote is None:
            return "absent", []
        if not local.is_file():
            return "absent", [hf_path]
        remote_size = getattr(remote, "size", None)
        if remote_size is not None and local.stat().st_size != remote_size:
            return "partial", [hf_path]
        return "ok", []

    # Build {repo_path: size} from HF — RepoFile has .size; RepoFolder does not.
    try:
        hf_files = {
            item.path: item.size
            for item in api.list_repo_tree(
                repo_id=repo_id,
                repo_type=repo_type,
                path_in_repo=hf_path,
                recursive=True,
            )
            if getattr(item, "size", None) is not None   # files only
        }
    except Exception:
        # list_repo_tree not available in older huggingface_hub — fall back to absent
        return "absent", []

    if not local.exists():
        return "absent", list(hf_files.keys())

    missing = []
    for hf_repo_path, hf_size in hf_files.items():
        # hf_repo_path is relative to repo root, e.g. "checkpoints/pdplanner/latest.ckpt"
        # local equivalent: local / (hf_repo_path relative to hf_path)
        rel = Path(hf_repo_path).relative_to(hf_path)
        local_file = local / rel
        if not local_file.exists():
            missing.append(hf_repo_path)
        elif hf_size is not None and local_file.stat().st_size != hf_size:
            missing.append(hf_repo_path)

    if missing:
        return "partial", missing
    return "ok", []


def _download_files(repo_id: str, repo_type: str, endpoint: str,
                    hf_repo_paths: list[str], local: Path,
                    hf_path_prefix: str, kind: str, token=None) -> None:
    """Download individual files from HF into their correct local paths."""
    from huggingface_hub import hf_hub_download

    for hf_repo_path in hf_repo_paths:
        rel = Path(hf_repo_path).relative_to(hf_path_prefix)
        dest = local if kind == "file" else local / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = hf_hub_download(
            repo_id=repo_id,
            repo_type=repo_type,
            filename=hf_repo_path,
            token=token,
            endpoint=endpoint,
        )
        shutil.copy2(tmp, dest)
        print(f"      ↳ {rel}")


def _download_full(api, repo_id: str, repo_type: str, hf_path: str,
                   local: Path, staging_root: Path, token=None) -> None:
    """Download the entire hf_path subtree via snapshot_download (original behavior)."""
    staging_dir = staging_root / hf_path
    staging_dir.mkdir(parents=True, exist_ok=True)
    api.snapshot_download(
        repo_id=repo_id,
        repo_type=repo_type,
        allow_patterns=[f"{hf_path}/**", f"{hf_path}/*"],
        local_dir=str(staging_root),
        token=token,
    )
    staged = staging_dir
    if not staged.exists():
        print(f"    [WARN] Nothing downloaded for {hf_path}")
        return

    local.mkdir(parents=True, exist_ok=True)
    for item in staged.iterdir():
        dest = local / item.name
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        shutil.move(str(item), str(dest))


def main():
    parser = argparse.ArgumentParser(description="Download mapped PredActor artifacts from HF.")
    parser.add_argument("--manifest", default=None,
                        help="Path to manifest YAML (default: scripts/hf_manifest.yaml)")
    parser.add_argument("--repo", default=None,
                        help="Override repo_id from manifest")
    parser.add_argument("--filter", nargs="+", default=None, metavar="PREFIX",
                        help="Download only entries whose hf_path starts with one of these prefixes")
    parser.add_argument("--all", action="store_true",
                        help="Include disabled entries as well")
    parser.add_argument("--list", action="store_true",
                        help="List manifest entries with local presence status and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be downloaded without downloading")
    parser.add_argument("--no-skip-download", action="store_true",
                        help="Re-download even if all local files are already up to date")
    parser.add_argument("--full", action="store_true",
                        help="Re-download entire entry folder via snapshot_download "
                             "instead of fetching only missing/changed files (old behavior)")
    parser.add_argument("--token", default=None,
                        help="HF token (or set HF_TOKEN / use `huggingface-cli login`)")
    args = parser.parse_args()

    HfApi = prompt_huggingface_hub()
    manifest = load_manifest(args.manifest)
    repo_id = args.repo or manifest["repo_id"]
    repo_type = manifest.get("repo_type", "model")
    endpoint = manifest.get("endpoint", "https://huggingface.co")
    entries = manifest["entries"]

    if not args.all:
        entries = [e for e in entries if e.get("enabled", True)]
    if args.filter:
        entries = [e for e in entries
                   if any(e["hf_path"].startswith(p) for p in args.filter)]

    REPO_ROOT = Path(__file__).resolve().parents[1]

    if args.list:
        print(f"Manifest entries  [{repo_id}]\n{'='*62}")
        all_entries = load_manifest(args.manifest)["entries"]
        for e in all_entries:
            local = resolve_local(e["local_path"], REPO_ROOT)
            enabled = "on " if e.get("enabled", True) else "off"
            if local.exists():
                size_gb = entry_size(local) / 1e9
                local_str = f"✓ {size_gb:.1f} GB"
            else:
                local_str = "✗ not present"
            mapping = display_local(local, REPO_ROOT)
            print(f"  [{enabled}]  {e['hf_path']:<42}  ↔  {mapping:<68} {local_str}")
        return

    if not entries:
        print("No entries matched. Check --filter or enabled flags in hf_manifest.yaml.")
        return

    api = HfApi(endpoint=endpoint, token=args.token)

    for entry in entries:
        hf_path = entry["hf_path"]
        local = resolve_local(entry["local_path"], REPO_ROOT)
        kind = entry.get("kind", "directory")
        tag = "[DRY-RUN] " if args.dry_run else ""
        suffix = "/" if kind == "directory" else ""
        print(f"  {tag}{hf_path}{suffix}  →  {display_local(local, REPO_ROOT)}{suffix}")

        if args.no_skip_download or args.full:
            # Force full re-download — skip the file-level check
            status, missing = "absent", []
        else:
            status, missing = _check_entry(api, repo_id, repo_type, entry, local)

        if status == "ok":
            try:
                verify_entry(entry, local)
            except RuntimeError as exc:
                print(f"    [INVALID] {exc}")
                status = "partial"
                if kind == "file":
                    missing = [hf_path]
                else:
                    missing = [f"{hf_path}/{path}" for path in entry.get("files", {})]

        if status == "ok":
            print(f"    [SKIP] All files present and sizes match.")
            continue

        if status == "partial":
            print(f"    [PARTIAL] {len(missing)} file(s) missing or changed:")
            for p in missing:
                print(f"      - {Path(p).relative_to(hf_path)}")
        else:
            print(f"    [ABSENT] Local directory not found — downloading all files.")

        if args.dry_run:
            continue

        use_full = args.full or args.no_skip_download or not missing
        if use_full:
            # --full / --no-skip-download, or list_repo_tree unavailable (missing=[])
            if kind == "file":
                _download_files(
                    repo_id, repo_type, endpoint, [hf_path], local,
                    hf_path, kind, token=args.token)
            else:
                staging_root = REPO_ROOT / ".hf_cache"
                _download_full(
                    api, repo_id, repo_type, hf_path, local,
                    staging_root, token=args.token)
        else:
            _download_files(
                repo_id, repo_type, endpoint, missing, local,
                hf_path, kind, token=args.token)

        verify_entry(entry, local)
        print(f"    Done → {display_local(local, REPO_ROOT)}")

    print("\nAll done.")


if __name__ == "__main__":
    main()
