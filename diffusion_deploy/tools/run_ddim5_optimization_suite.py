#!/usr/bin/env python3
"""Run randomized/reversed Task082 C++/LibTorch Orin blocks."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


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
        raise SystemExit("warmup>=20 and repetitions>=100 are required")
    payload = json.loads(args.manifest.read_text())
    candidates = {row["candidate"]: row for row in payload["candidates"]}
    canonical = list(candidates)
    blocks = [
        ("block01_forward", canonical, 11),
        ("block02_reverse", list(reversed(canonical)), 29),
        ("block03_rotated", canonical[3:] + canonical[:3], 47),
    ]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    machine_before = {
        "nvidia_smi": capture([
            "nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,"
            "memory.used,memory.total", "--format=csv,noheader"]),
        "gpu_load": capture(["cat", "/sys/devices/gpu.0/load"]),
        "processes": capture(["ps", "-eo", "pid,ppid,comm,args"]),
    }
    (args.output_dir / "machine_before.json").write_text(
        json.dumps(machine_before, indent=2) + "\n")
    process_text = machine_before["processes"]["output"]
    forbidden = []
    for line in process_text.splitlines()[1:]:
        fields = line.split(None, 3)
        if len(fields) < 3:
            continue
        comm = fields[2]
        if (comm.startswith("run_g1_robot")
                or comm.startswith("benchmark_ddim5")
                or comm in {"LowCmd", "MotionSwitcher"}):
            forbidden.append(line)
    if forbidden:
        raise RuntimeError(
            "unsafe/co-tenant target process detected before benchmark:\n"
            + "\n".join(forbidden))
    nvidia_output = machine_before["nvidia_smi"]["output"]
    if machine_before["nvidia_smi"]["returncode"] == 0 and nvidia_output.strip():
        try:
            utilization = int(nvidia_output.split(",")[2].strip().rstrip(" %"))
            if utilization > 15:
                raise RuntimeError(
                    f"GPU utilization is already {utilization}%; refusing contended run")
        except (IndexError, ValueError):
            pass
    tegra_log = (args.output_dir / "tegrastats.log").open("w")
    tegra = subprocess.Popen(["tegrastats", "--interval", "500"],
                             stdout=tegra_log, stderr=subprocess.STDOUT,
                             start_new_session=True)
    results = []
    try:
        for block, order, seed in blocks:
            for order_index, candidate in enumerate(order):
                cell = args.output_dir / block / candidate
                command = [
                    str(args.binary),
                    "--config", candidates[candidate]["config"],
                    "--reference-config",
                    candidates["task073_self_reference"]["config"],
                    "--candidate", candidate,
                    "--output-dir", str(cell),
                    "--device", args.device,
                    "--warmup", str(args.warmup),
                    "--repetitions", str(args.repetitions),
                    "--seed", str(20260822 + seed),
                ]
                started = time.time()
                result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, check=False)
                record = {
                    "block": block, "order_index": order_index,
                    "candidate": candidate, "seed": seed,
                    "returncode": result.returncode,
                    "elapsed_s": time.time() - started,
                    "output": result.stdout,
                }
                results.append(record)
                if result.returncode:
                    raise RuntimeError(json.dumps(record, indent=2))
    finally:
        if tegra.poll() is None:
            os.killpg(tegra.pid, signal.SIGTERM)
            tegra.wait(timeout=10)
        tegra_log.close()
    summaries = []
    for path in sorted(args.output_dir.glob("block*/*/summary.csv")):
        with path.open(newline="") as stream:
            row = next(csv.DictReader(stream))
        row["block"] = path.parents[1].name
        summaries.append(row)
    machine_after = {
        "nvidia_smi": capture([
            "nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,"
            "memory.used,memory.total", "--format=csv,noheader"]),
        "gpu_load": capture(["cat", "/sys/devices/gpu.0/load"]),
        "processes": capture(["ps", "-eo", "pid,ppid,comm,args"]),
    }
    (args.output_dir / "machine_after.json").write_text(
        json.dumps(machine_after, indent=2) + "\n")
    run = {
        "schema": "task082-ddim5-suite-v1", "status": "pass",
        "scope": "inference-only-no-DDS-no-FSM-no-publisher-no-actuation",
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256(args.manifest),
        "binary": str(args.binary.resolve()), "binary_sha256": sha256(args.binary),
        "device": args.device, "warmup": args.warmup,
        "repetitions": args.repetitions, "blocks": results,
        "summaries": summaries,
    }
    (args.output_dir / "suite_run.json").write_text(
        json.dumps(run, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "cells": len(results),
                      "output": str(args.output_dir)}))


if __name__ == "__main__":
    main()
