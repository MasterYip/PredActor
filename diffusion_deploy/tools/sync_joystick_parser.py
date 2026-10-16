#!/usr/bin/env python3
"""Check or refresh the standalone deploy copy of the canonical joystick parser."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEPLOY_ROOT = Path(__file__).resolve().parents[1]
PDPLANNER_ROOT = DEPLOY_ROOT.parent
SOURCE = PDPLANNER_ROOT / "diffusion_policy" / "utils" / "joystick_parser.py"
TARGET = DEPLOY_ROOT / "python" / "diffusion_deploy_manager" / "joystick_parser.py"


def in_sync() -> bool:
    return SOURCE.read_bytes() == TARGET.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="refresh the generated standalone copy")
    args = parser.parse_args()
    if args.write:
        shutil.copyfile(SOURCE, TARGET)
    if not in_sync():
        print(f"out of sync: {TARGET} must be generated from {SOURCE}")
        return 1
    print(f"joystick parser parity PASS: {SOURCE} == {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
