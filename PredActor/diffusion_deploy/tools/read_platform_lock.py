#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def cmake_quote(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    lock_path = Path(args.lock).resolve()
    payload = lock_path.read_bytes()
    lock = json.loads(payload)
    if lock.get("schema_version") != 1 or args.profile not in lock.get("profiles", {}):
        raise SystemExit("invalid platform lock or profile")
    profile = lock["profiles"][args.profile]
    values = {
        "DIFFUSION_DEPLOY_LOCK_SHA256": hashlib.sha256(payload).hexdigest(),
        "DIFFUSION_DEPLOY_LOCK_PROFILE": args.profile,
        "DIFFUSION_DEPLOY_EXPECTED_ARCH": profile["architecture"],
        "DIFFUSION_DEPLOY_EXPECTED_TORCH": profile["torch_cmake_version"],
        "DIFFUSION_DEPLOY_EXPECTED_CXX11_ABI": profile["cxx11_abi"],
    }
    output = Path(args.output)
    output.write_text("".join(
        f'set({key} "{cmake_quote(value)}")\n' for key, value in values.items()),
        encoding="utf-8")


if __name__ == "__main__":
    main()
