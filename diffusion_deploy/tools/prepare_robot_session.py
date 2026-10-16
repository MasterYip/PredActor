#!/usr/bin/env python3
"""Create target-bound deploy/FSM copies without modifying an export bundle."""

import argparse
import hashlib
import os
import pathlib
import socket
import tempfile

import yaml


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_hashes(checksum_path):
    expected = {}
    for raw_line in checksum_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        digest, name = line.split(maxsplit=1)
        expected[name.lstrip("* ")] = digest
    return expected


def _write_yaml_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.safe_dump(payload, stream, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def prepare_robot_session(model_dir, network_interface, force=False,
                          check_interface=True, simulation=False):
    model_dir = pathlib.Path(model_dir).resolve()
    deploy_source = model_dir / "deploy_config.yaml"
    fsm_source = model_dir / "fsm_config.yaml"
    checksum_path = model_dir / "SHA256SUMS"
    for required in (deploy_source, fsm_source, checksum_path):
        if not required.is_file():
            raise ValueError(f"required bundle file is missing: {required}")

    if simulation and network_interface != "lo":
        raise ValueError("simulation sessions require the loopback interface 'lo'")
    if (not network_interface or (network_interface == "lo" and not simulation)
            or network_interface.startswith("REQUIRED_")):
        raise ValueError("a concrete non-loopback network interface is required")
    if check_interface:
        try:
            socket.if_nametoindex(network_interface)
        except OSError as exc:
            raise ValueError(
                f"network interface does not exist on this host: {network_interface}"
            ) from exc

    expected = _expected_hashes(checksum_path)
    for source in (deploy_source, fsm_source):
        expected_digest = expected.get(source.name)
        if not expected_digest:
            raise ValueError(f"SHA256SUMS has no entry for {source.name}")
        actual_digest = _sha256(source)
        if actual_digest != expected_digest:
            raise ValueError(
                f"immutable bundle hash mismatch for {source.name}: "
                f"expected {expected_digest}, got {actual_digest}")

    deploy = yaml.safe_load(deploy_source.read_text(encoding="utf-8")) or {}
    fsm = yaml.safe_load(fsm_source.read_text(encoding="utf-8")) or {}
    if not isinstance(deploy.get("env"), dict):
        raise ValueError("deploy_config.yaml is missing env mapping")
    if not isinstance(fsm.get("FSM"), dict) or not isinstance(
            fsm["FSM"].get("env"), dict):
        raise ValueError("fsm_config.yaml is missing FSM.env mapping")

    deploy["env"]["network_interface"] = network_interface
    fsm["FSM"]["env"]["network_interface"] = network_interface

    deploy_target = model_dir / "deploy_config.robot.yaml"
    fsm_target = model_dir / "fsm_config.robot.yaml"
    for target in (deploy_target, fsm_target):
        if target.exists() and not force:
            raise ValueError(f"session file already exists (use --force): {target}")

    _write_yaml_atomic(deploy_target, deploy)
    _write_yaml_atomic(fsm_target, fsm)
    return {
        "deploy_config": deploy_target,
        "deploy_sha256": _sha256(deploy_target),
        "fsm_config": fsm_target,
        "fsm_sha256": _sha256(fsm_target),
        "network_interface": network_interface,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create verified robot-session configs beside an export bundle")
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--network-interface", required=True)
    parser.add_argument(
        "--simulation", action="store_true",
        help="create a MuJoCo loopback session; requires --network-interface lo")
    parser.add_argument("--force", action="store_true",
                        help="replace existing session copies")
    args = parser.parse_args()
    try:
        result = prepare_robot_session(
            args.model_dir, args.network_interface, force=args.force,
            simulation=args.simulation)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"network_interface={result['network_interface']}")
    print(f"deploy_config={result['deploy_config']}")
    print(f"deploy_sha256={result['deploy_sha256']}")
    print(f"fsm_config={result['fsm_config']}")
    print(f"fsm_sha256={result['fsm_sha256']}")


if __name__ == "__main__":
    main()
