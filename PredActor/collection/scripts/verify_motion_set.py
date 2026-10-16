#!/usr/bin/env python3
"""Verify the exact 152-motion source set used by the PDP051 paper run."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED_COUNT = 152
EXPECTED_MANIFEST_SHA256 = "0180f0034315e7159a10d0963289b3c95870534dd0e84549087ce3a11d7f63d4"


def manifest_digest(motion_set: Path) -> tuple[int, str]:
    files = sorted(motion_set.glob("*/motion.npz"))
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(motion_set).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\n")
    return len(files), digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("motion_set", type=Path, help="Directory containing the 152 motion subdirectories")
    args = parser.parse_args()

    motion_set = args.motion_set.expanduser().resolve()
    if not motion_set.is_dir():
        raise SystemExit(f"Motion set does not exist: {motion_set}")

    count, observed = manifest_digest(motion_set)
    if count != EXPECTED_COUNT or observed != EXPECTED_MANIFEST_SHA256:
        raise SystemExit(
            "Motion set does not match the PDP051/Paper g1_152fk source: "
            f"count={count} (expected {EXPECTED_COUNT}), "
            f"manifest_sha256={observed} (expected {EXPECTED_MANIFEST_SHA256})."
        )

    print(f"[INFO] Verified PDP051/Paper g1_152fk motion set: {count} files, manifest {observed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
