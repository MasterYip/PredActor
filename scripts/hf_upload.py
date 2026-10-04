#!/usr/bin/env python3
"""
Upload mapped resources to the PredActor Artifacts Hugging Face model repository.
All paths and the repo ID are read from scripts/hf_manifest.yaml.

Usage:
  python scripts/hf_upload.py
  python scripts/hf_upload.py --repo MasterYip/PredActor_Artifacts
  python scripts/hf_upload.py --filter checkpoints
  python scripts/hf_upload.py --dry-run
  python scripts/hf_upload.py --hf-transfer                 # fast Rust-backed uploader
  python scripts/hf_upload.py --num-workers 4               # parallel workers (large folders)
"""

import argparse
import shutil
import sys
import os
from pathlib import Path
from _hf_common import (
    display_local, load_manifest, resolve_local, prompt_huggingface_hub,
    verify_entry,
    enable_hf_transfer,
)

# Staging dir lives inside the repo so hardlinks (same device) always work.
# The .cache/.huggingface/ subdir written by upload_large_folder persists here,
# enabling resume on interruption.
_STAGING_DIR_NAME = ".hf_upload_staging"


def _hardlink_tree(src: Path, dst: Path) -> None:
    """Recreate src's directory tree under dst using hardlinks (no data copy)."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            os.link(item, target)


def main():
    parser = argparse.ArgumentParser(description="Upload mapped PredActor artifacts to HF.")
    parser.add_argument("--manifest", default=None,
                        help="Path to manifest YAML (default: scripts/hf_manifest.yaml)")
    parser.add_argument("--repo", default=None,
                        help="Override repo_id from manifest, e.g. your-org/PredActor_Artifacts")
    parser.add_argument("--filter", nargs="+", default=None, metavar="PREFIX",
                        help="Upload only entries whose hf_path starts with one of these prefixes")
    parser.add_argument("--all", action="store_true",
                        help="Include disabled entries as well")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be uploaded without uploading")
    parser.add_argument("--token", default=None,
                        help="HF token (or set HF_TOKEN / use `huggingface-cli login`)")
    # ── speed / reliability options ──────────────────────────────────────────
    parser.add_argument("--hf-transfer", action="store_true",
                        help="Enable hf_transfer (Rust multi-part uploader, ~5-10× faster). "
                             "Installs the package automatically if missing.")
    parser.add_argument("--num-workers", type=int, default=None, metavar="N",
                        help="Parallel workers for upload_large_folder (default: cpu_count-2).")
    args = parser.parse_args()

    # Must happen before huggingface_hub is imported inside prompt_huggingface_hub().
    if args.hf_transfer:
        enable_hf_transfer()
        print("hf_transfer enabled.")

    HfApi = prompt_huggingface_hub()
    manifest = load_manifest(args.manifest)
    repo_id = args.repo or manifest["repo_id"]
    repo_type = manifest.get("repo_type", "model")
    endpoint = manifest.get("endpoint", "https://huggingface.co")
    private = bool(manifest.get("private", False))
    entries = manifest["entries"]

    if not args.all:
        entries = [e for e in entries if e.get("enabled", True)]
    if args.filter:
        entries = [e for e in entries
                   if any(e["hf_path"].startswith(p) for p in args.filter)]

    if not entries:
        print("No entries matched. Check --filter or enabled flags in hf_manifest.yaml.")
        return

    api = HfApi(endpoint=endpoint, token=args.token)

    # Ensure repo exists
    if not args.dry_run:
        try:
            api.repo_info(repo_id=repo_id, repo_type=repo_type)
        except Exception:
            visibility = "private" if private else "public"
            print(f"Creating {visibility} {repo_type} repo {repo_id} ...")
            api.create_repo(repo_id=repo_id, repo_type=repo_type, private=private)

    REPO_ROOT = Path(__file__).resolve().parents[1]
    staging_root = REPO_ROOT / _STAGING_DIR_NAME

    for entry in entries:
        hf_path = entry["hf_path"]
        local = resolve_local(entry["local_path"], REPO_ROOT)
        notes = entry.get("notes", "")

        if not local.exists():
            print(f"  [SKIP] {display_local(local, REPO_ROOT)} does not exist  ({hf_path})")
            continue

        try:
            verify_entry(entry, local)
        except RuntimeError as exc:
            print(f"  [ERROR] {exc}")
            raise SystemExit(1) from exc

        if local.is_file():
            size_gb = local.stat().st_size / 1e9
            tag = "[DRY-RUN] " if args.dry_run else ""
            print(f"  {tag}{display_local(local, REPO_ROOT)}  →  {hf_path}  ({size_gb:.4f} GB)")
            if notes:
                print(f"           {notes}")
            if args.dry_run:
                continue
            api.upload_file(
                path_or_fileobj=str(local),
                path_in_repo=hf_path,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=f"Upload {hf_path}",
            )
            print(f"           Done.")
            continue

        size_gb = sum(f.stat().st_size for f in local.rglob("*") if f.is_file()) / 1e9
        tag = "[DRY-RUN] " if args.dry_run else ""
        print(f"  {tag}{display_local(local, REPO_ROOT)}/  →  {hf_path}/  ({size_gb:.2f} GB)")
        if notes:
            print(f"           {notes}")
        if args.dry_run:
            continue

        # upload_large_folder has no path_in_repo — it uploads folder_path's
        # contents straight to the repo root.  Work around this by building a
        # hardlink tree under a persistent staging dir so the files appear at
        # the right path in the repo.  Hardlinks cost no extra disk space and
        # the .cache/ sidecar survives interruptions for resumable uploads.
        #
        # Staging layout:  <repo>/.hf_upload_staging/<slug>/<hf_path>/...files
        slug = hf_path.replace("/", "_")
        staging = staging_root / slug
        staged_dest = staging / hf_path
        print(f"           Staging hardlinks → {staging.relative_to(REPO_ROOT)} ...")
        _hardlink_tree(local, staged_dest)

        upload_kwargs = dict(repo_id=repo_id, folder_path=str(staging), repo_type=repo_type)
        if args.num_workers is not None:
            upload_kwargs["num_workers"] = args.num_workers
        if hasattr(api, "upload_large_folder"):
            api.upload_large_folder(**upload_kwargs)
        else:
            # upload_large_folder requires huggingface_hub >= 0.24; fall back to
            # upload_folder which works on all versions (no resume support).
            print("Warning: huggingface_hub version <0.25 does not support upload_large_folder; "
                  "falling back to slower upload_folder (no resume support).")
            upload_kwargs.pop("num_workers", None)
            api.upload_folder(**upload_kwargs)

        # Remove hardlinks; keep the staging dir so .cache/ survives for resume.
        shutil.rmtree(staged_dest)
        print(f"           Done.")

    print("\nAll done.")


if __name__ == "__main__":
    main()
