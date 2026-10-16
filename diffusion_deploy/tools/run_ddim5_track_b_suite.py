#!/usr/bin/env python3
"""Run three ordered blocks of Task082 Track B latency-only C++ cells."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture(command):
    try:
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False)
        return {"command": command, "returncode": result.returncode,
                "output": result.stdout}
    except FileNotFoundError as error:
        return {"command": command, "returncode": 127,
                "output": f"optional command unavailable: {error.filename}\n"}


def snapshot():
    return {
        "gpu_load": capture(["cat", "/sys/devices/gpu.0/load"]),
        "processes": capture(["ps", "-eo", "pid,ppid,comm,args"]),
        "meminfo": Path("/proc/meminfo").read_text(),
    }


def assert_safe_processes(text):
    violations = []
    for line in text.splitlines()[1:]:
        fields = line.split(None, 3)
        if len(fields) < 3:
            continue
        comm = fields[2]
        if (comm.startswith("run_g1_robot") or comm.startswith("benchmark_ddim5")
                or comm in {"LowCmd", "MotionSwitcher"}):
            violations.append(line)
    if violations:
        raise RuntimeError("unsafe/co-tenant process:\n" + "\n".join(violations))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--repetitions", type=int, default=100)
    args = parser.parse_args()
    if args.warmup < 20 or args.repetitions < 100:
        raise SystemExit("warmup>=20 and repetitions>=100 required")
    payload = json.loads(args.manifest.read_text())
    if payload.get("schema") != "task082-track-b-artifacts-v1":
        raise RuntimeError("wrong Track B manifest schema")
    cells = payload["cells"]
    names = [cell["candidate"] for cell in cells]
    by_name = {cell["candidate"]: cell for cell in cells}
    blocks = [
        ("block01_forward", names, 11),
        ("block02_reverse", list(reversed(names)), 29),
        ("block03_rotated", names[5:] + names[:5], 47),
    ]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    before = snapshot()
    assert_safe_processes(before["processes"]["output"])
    (args.output_dir / "machine_before.json").write_text(
        json.dumps(before, indent=2) + "\n")
    tegra_path = args.output_dir / "tegrastats.log"
    with tegra_path.open("w") as stream:
        tegra = subprocess.Popen(["tegrastats", "--interval", "500"],
                                 stdout=stream, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        records = []
        try:
            for block, order, seed in blocks:
                for order_index, name in enumerate(order):
                    cell = by_name[name]
                    output = args.output_dir / block / name
                    command = [
                        str(args.binary), "--config", cell["config"],
                        "--candidate", name, "--output-dir", str(output),
                        "--device", args.device, "--warmup", str(args.warmup),
                        "--repetitions", str(args.repetitions),
                        "--seed", str(20260822 + seed),
                    ]
                    result = subprocess.run(
                        command, text=True, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, check=False)
                    record = {"block": block, "order_index": order_index,
                              "candidate": name, "sample_seed": seed,
                              "returncode": result.returncode,
                              "output": result.stdout}
                    records.append(record)
                    if result.returncode:
                        raise RuntimeError(json.dumps(record, indent=2))
        finally:
            if tegra.poll() is None:
                os.killpg(tegra.pid, signal.SIGTERM)
                tegra.wait(timeout=10)
    summaries = []
    for path in sorted(args.output_dir.glob("block*/*/summary.csv")):
        with path.open(newline="") as stream:
            row = next(csv.DictReader(stream))
        row["block"] = path.parents[1].name
        summaries.append(row)
    after = snapshot()
    assert_safe_processes(after["processes"]["output"])
    (args.output_dir / "machine_after.json").write_text(
        json.dumps(after, indent=2) + "\n")
    if len(summaries) != 3 * len(cells):
        raise RuntimeError("incomplete Track B summary set")
    run = {
        "schema": "task082-track-b-suite-v1", "status": "pass",
        "scope": "random-weight-latency-only-no-quality-claim-no-actuation",
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256(args.manifest),
        "binary": str(args.binary.resolve()), "binary_sha256": sha256(args.binary),
        "warmup": args.warmup, "repetitions": args.repetitions,
        "records": records, "summaries": summaries,
    }
    (args.output_dir / "track_b_run.json").write_text(
        json.dumps(run, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "cells": len(summaries)}))


if __name__ == "__main__":
    main()
