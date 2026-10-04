#!/usr/bin/env python3
"""
Manage the manifest-configured PredActor Artifacts Hugging Face repository.

Commands:
  status   Print local size vs. remote presence for every manifest entry
  ls       List files/folders in the HF repo (optionally under a subfolder)
  delete   Delete a path from the HF repo
  tag      Create a version tag on the HF repo
  readme   Push/update the repo README card
  graph    Print the commit history graph (git-log style, with branch/tag refs)
  show     Show one commit's message + the files it changed (vs its parent)

Usage:
  python scripts/hf_manage.py status
  python scripts/hf_manage.py ls [--path data/]
  python scripts/hf_manage.py delete --path data/g1_152_obsnoise [--yes]
  python scripts/hf_manage.py tag --name v1.0 [--message "Initial release"]
  python scripts/hf_manage.py readme
  python scripts/hf_manage.py graph [-n 20] [--date]
  python scripts/hf_manage.py show 7d00b839 [--against a88c9bae]
  python scripts/hf_manage.py --repo MasterYip/PredActor_Artifacts status
"""

import argparse
import sys
from pathlib import Path
from _hf_common import (
    display_local, entry_size, load_manifest, resolve_local,
    prompt_huggingface_hub,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_TYPE = "model"

def cmd_status(api, repo_id, manifest):
    print(f"Sync status  [{repo_id}]\n{'='*64}")
    try:
        remote_files = set(api.list_repo_files(repo_id=repo_id, repo_type=REPO_TYPE))
    except Exception as exc:
        print(f"  ERROR reading remote tree: {exc}")
        return
    for e in manifest["entries"]:
        local = resolve_local(e["local_path"], REPO_ROOT)
        enabled = "on " if e.get("enabled", True) else "off"
        if local.exists():
            size_gb = entry_size(local) / 1e9
            local_str = f"✓ {size_gb:.1f} GB"
        else:
            local_str = "✗ not present"
        notes = f"  # {e['notes']}" if e.get("notes") else ""
        mapping = display_local(local, REPO_ROOT)
        hf_path = e["hf_path"]
        if e.get("kind", "directory") == "file":
            remote = hf_path in remote_files
        else:
            prefix = hf_path.rstrip("/") + "/"
            remote = any(path.startswith(prefix) for path in remote_files)
        remote_str = "remote: ✓" if remote else "remote: ✗"
        print(f"  [{enabled}]  {hf_path:<42}  {remote_str}  local: {mapping} ({local_str}){notes}")


def cmd_ls(api, repo_id, path_in_repo):
    print(f"Contents of {repo_id}/{path_in_repo or '(root)'}")
    try:
        items = api.list_repo_tree(repo_id=repo_id, repo_type=REPO_TYPE,
                                    path_in_repo=path_in_repo)
        for item in items:
            kind = "D" if item.__class__.__name__ == "RepoFolder" else "F"
            size = getattr(item, "size", None)
            size_str = f"  {size/1e6:.1f} MB" if size else ""
            print(f"  [{kind}] {item.path}{size_str}")
    except Exception as e:
        print(f"  ERROR: {e}")


def cmd_delete(api, repo_id, path_in_repo, yes):
    if not yes:
        ans = input(f"Delete '{path_in_repo}' from {repo_id}? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted.")
            return
    print(f"Deleting {path_in_repo} ...")
    try:
        from huggingface_hub import CommitOperationDelete
        items = list(api.list_repo_tree(repo_id=repo_id, repo_type=REPO_TYPE,
                                         path_in_repo=path_in_repo, recursive=True))
        files = [i.path for i in items if getattr(i, "type", "") != "directory"]
        if not files:
            print("  No files found.")
            return
        api.create_commit(
            repo_id=repo_id, repo_type=REPO_TYPE,
            commit_message=f"Delete {path_in_repo}",
            operations=[CommitOperationDelete(path_in_repo=fp) for fp in files],
        )
        print(f"  Deleted {len(files)} file(s).")
    except Exception as e:
        print(f"  ERROR: {e}")


def cmd_tag(api, repo_id, tag, message):
    print(f"Creating tag '{tag}' on {repo_id} ...")
    try:
        api.create_tag(repo_id=repo_id, repo_type=REPO_TYPE,
                        tag=tag, tag_message=message or f"Release {tag}")
        print(f"  Tag '{tag}' created.")
    except Exception as e:
        print(f"  ERROR: {e}")


def cmd_readme(api, repo_id, from_file=None):
    print(f"Updating README for {repo_id} ...")
    try:
        from huggingface_hub import CommitOperationAdd
        source = Path(from_file) if from_file else REPO_ROOT / "Artifacts" / "README.md"
        content = source.read_bytes()
        print(f"  Using content from {source}")
        api.create_commit(
            repo_id=repo_id, repo_type=REPO_TYPE,
            commit_message="Update README card",
            operations=[CommitOperationAdd(path_in_repo="README.md",
                                           path_or_fileobj=content)],
        )
        print("  README updated.")
    except Exception as e:
        print(f"  ERROR: {e}")


def _repo_tree(api, repo_id, revision):
    """Return {path: RepoFile} for every file in the repo at a revision."""
    snapshot = {}
    items = api.list_repo_tree(repo_id=repo_id, repo_type=REPO_TYPE,
                               revision=revision, recursive=True)
    for item in items:
        if getattr(item, "blob_id", None) is not None:  # files only
            snapshot[item.path] = item
    return snapshot


def _file_size(item):
    """Real size of a file: LFS blob size when present, else the pointer size."""
    lfs = getattr(item, "lfs", None)
    if lfs is not None and getattr(lfs, "size", None) is not None:
        return lfs.size
    return getattr(item, "size", 0)


def _diff_trees(old, new):
    """Classify file paths between two tree snapshots into (added, removed, modified)."""
    added = [p for p in new if p not in old]
    removed = [p for p in old if p not in new]
    modified = [p for p in old if p in new and old[p].blob_id != new[p].blob_id]
    return added, removed, modified


def _resolve_commit(api, repo_id, prefix):
    """Resolve a full/abbreviated commit sha to a GitCommitInfo, or None."""
    commits = api.list_repo_commits(repo_id=repo_id, repo_type=REPO_TYPE)
    for c in commits:
        if c.commit_id == prefix or c.commit_id.startswith(prefix):
            return c
    return None


def cmd_graph(api, repo_id, max_count, show_date):
    print(f"Commit graph  [{repo_id}]\n{'='*64}")
    try:
        commits = api.list_repo_commits(repo_id=repo_id, repo_type=REPO_TYPE)
        refs = api.list_repo_refs(repo_id=repo_id, repo_type=REPO_TYPE)
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    # Map each target commit -> human decorations (branch names + tags).
    deco = {}
    for b in refs.branches:
        deco.setdefault(b.target_commit, []).append(b.name)
    for t in refs.tags:
        deco.setdefault(t.target_commit, []).append(f"tag: {t.name}")

    try:
        head_sha = api.repo_info(repo_id=repo_id, repo_type=REPO_TYPE).sha
    except Exception:
        head_sha = None

    if max_count:
        commits = commits[:max_count]

    for c in commits:
        sha = c.commit_id[:7]
        refnames = list(deco.get(c.commit_id, []))
        if head_sha and c.commit_id == head_sha:
            refnames = [("HEAD -> " + r) if not r.startswith(("HEAD", "tag:")) else r
                        for r in refnames]
            if not any(r.startswith("HEAD") for r in refnames):
                refnames.insert(0, "HEAD")
        title = c.title or (c.message.splitlines()[0] if c.message else "(no title)")
        author = c.authors[0] if c.authors else "?"
        line = f"* {sha}"
        if refnames:
            line += " (" + ", ".join(refnames) + ")"
        if show_date:
            line += "  " + c.created_at.strftime("%Y-%m-%d %H:%M")
        line += f"  [{author}] {title}"
        print(line)


def cmd_show(api, repo_id, commit, against):
    print(f"Commit details  [{repo_id}]\n{'='*64}")
    try:
        target = _resolve_commit(api, repo_id, commit)
    except Exception as e:
        print(f"  ERROR: {e}")
        return
    if target is None:
        print(f"  ERROR: no commit matching '{commit}'")
        return

    print(f"commit {target.commit_id}")
    print(f"Author: {', '.join(target.authors) or '?'}")
    print(f"Date:   {target.created_at}")
    print()
    msg = target.message or target.title or ""
    for line in msg.splitlines():
        print(f"    {line}")

    # Parent = explicit --against, else the next (older) commit in the list.
    if against:
        parent = against
        parent_label = against
    else:
        commits = api.list_repo_commits(repo_id=repo_id, repo_type=REPO_TYPE)
        idx = next((i for i, c in enumerate(commits)
                    if c.commit_id == target.commit_id), None)
        if idx is None or idx + 1 >= len(commits):
            parent = None
            parent_label = "(initial commit — no parent)"
        else:
            parent = commits[idx + 1].commit_id
            parent_label = parent[:7]

    try:
        old = _repo_tree(api, repo_id, parent) if parent else {}
        new = _repo_tree(api, repo_id, target.commit_id)
    except Exception as e:
        print(f"\n  ERROR diffing trees: {e}")
        return

    added, removed, modified = _diff_trees(old, new)
    print(f"\nChanged files vs {parent_label}  "
          f"({len(added)} added, {len(modified)} modified, {len(removed)} deleted)")
    if not (added or removed or modified):
        print("  (no file changes)")
        return

    rows = ([(p, "A", new[p]) for p in sorted(added)]
            + [(p, "M", new[p]) for p in sorted(modified)]
            + [(p, "D", old[p]) for p in sorted(removed)])
    for path, kind, item in rows:
        size_mb = _file_size(item) / 1e6
        print(f"  {kind}  {path:<64}  {size_mb:>10.2f} MB")
    print("\n  (file-level diff only — the Hub API does not expose line diffs.)")


def main():
    parser = argparse.ArgumentParser(description="Manage the PredActor Artifacts HF repo.")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--token", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show local vs. remote sync status")

    ls_p = sub.add_parser("ls", help="List files in HF repo")
    ls_p.add_argument("--path", default="")

    del_p = sub.add_parser("delete", help="Delete a path from the HF repo")
    del_p.add_argument("--path", required=True)
    del_p.add_argument("--yes", action="store_true")

    tag_p = sub.add_parser("tag", help="Create a version tag")
    tag_p.add_argument("--name", required=True)
    tag_p.add_argument("--message", default="")

    readme_p = sub.add_parser("readme", help="Push/update the repo README card")
    readme_p.add_argument(
        "--from-file", default=None, metavar="PATH",
        help="Use this markdown file as README "
             "(default: Artifacts/README.md from the sync layout)."
    )

    graph_p = sub.add_parser("graph", help="Print the commit history graph")
    graph_p.add_argument("-n", "--max-count", type=int, default=None,
                         help="Limit to the most recent N commits")
    graph_p.add_argument("--date", action="store_true",
                         help="Show commit timestamp")

    show_p = sub.add_parser("show", help="Show one commit's message + changed files")
    show_p.add_argument("commit", help="Full or abbreviated commit sha")
    show_p.add_argument("--against", default=None, metavar="REV",
                        help="Diff against this revision instead of the commit's "
                             "parent (accepts sha/branch/tag)")

    args = parser.parse_args()

    HfApi = prompt_huggingface_hub()
    manifest = load_manifest(args.manifest)
    repo_id = args.repo or manifest["repo_id"]
    global REPO_TYPE
    REPO_TYPE = manifest.get("repo_type", "model")
    endpoint = manifest.get("endpoint", "https://huggingface.co")
    api = HfApi(endpoint=endpoint, token=args.token)

    if args.command == "status":
        cmd_status(api, repo_id, manifest)
    elif args.command == "ls":
        cmd_ls(api, repo_id, args.path)
    elif args.command == "delete":
        cmd_delete(api, repo_id, args.path, args.yes)
    elif args.command == "tag":
        cmd_tag(api, repo_id, args.name, args.message)
    elif args.command == "readme":
        cmd_readme(api, repo_id, from_file=getattr(args, "from_file", None))
    elif args.command == "graph":
        cmd_graph(api, repo_id, args.max_count, args.date)
    elif args.command == "show":
        cmd_show(api, repo_id, args.commit, args.against)


if __name__ == "__main__":
    main()
