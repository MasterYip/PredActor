import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from .bootstrap import (BootstrapError, bootstrap_profile, fk_runtime_prefix,
                        seed_cache_from_directory, sha256_file, uninstall)
from .profiles import ProfileError, detect_tuple, load_lock, propose_profile, require_profile


def _print(payload):
    print(json.dumps(payload, indent=2, sort_keys=True))


def _source_root(value):
    root = Path(value).resolve() if value else Path(__file__).resolve().parents[2]
    if not (root / "CMakeLists.txt").is_file():
        raise RuntimeError("--source must identify the diffusion_deploy source root")
    return root


def _dependency_root(prefix, lock, artifact_id):
    artifact = lock["artifacts"][artifact_id]
    return Path(prefix).resolve() / "deps" / artifact_id / artifact["root"]


def _run(command, execute, env=None):
    rendered = [str(item) for item in command]
    if execute:
        subprocess.run(rendered, check=True, env=env)
    return rendered


def command_doctor(args, lock_path, lock):
    detected = detect_tuple()
    proposed = propose_profile(lock, detected)
    selected = None
    if args.profile:
        selected = require_profile(lock, args.profile, detected=detected, strict=True)
    _print({"lock": str(lock_path), "detected": detected, "proposed_profile": proposed,
            "selected_profile": args.profile, "profile": selected})


def command_bootstrap(args, lock, profile):
    require_profile(lock, profile, strict=not args.skip_tuple_check)
    result = bootstrap_profile(lock, profile, args.prefix, args.cache_dir,
                               offline=args.offline, execute=args.execute)
    _print(result)


def command_seed_cache(args, lock, profile):
    require_profile(lock, profile, strict=not args.skip_tuple_check)
    _print(seed_cache_from_directory(
        lock, profile, args.artifact_dir, args.cache_dir, execute=args.execute))


def command_build(args, lock_path, lock, profile):
    spec = require_profile(lock, profile, strict=not args.skip_tuple_check)
    source = _source_root(args.source)
    prefix = Path(args.prefix).resolve()
    build_dir = Path(args.build_dir).resolve()
    runtime_prefix = prefix / "runtime"
    fmt_ids = [item for item in spec["source_dependencies"]
               if item.startswith("fmt-")]
    if len(fmt_ids) != 1:
        raise RuntimeError("profile must lock exactly one fmt source artifact")
    fmt_id = fmt_ids[0]
    fmt_source = _dependency_root(prefix, lock, fmt_id)
    spdlog_ids = [item for item in spec["source_dependencies"]
                  if item.startswith("spdlog-")]
    if len(spdlog_ids) != 1:
        raise RuntimeError("profile must lock exactly one spdlog source artifact")
    spdlog_id = spdlog_ids[0]
    spdlog_source = _dependency_root(prefix, lock, spdlog_id)
    torch_root = _dependency_root(prefix, lock, spec["torch_artifact"])
    if args.execute:
        for required in (fmt_source / "CMakeLists.txt", spdlog_source / "CMakeLists.txt",
                         torch_root / "share" / "cmake" / "Torch"):
            if not required.exists():
                raise RuntimeError(f"bootstrap dependency missing: {required}")

    commands = []
    fmt_build = prefix / "build" / f"{fmt_id}-{profile}"
    commands.append(_run([
        "cmake", "-S", fmt_source, "-B", fmt_build,
        f"-DCMAKE_INSTALL_PREFIX={runtime_prefix}", "-DFMT_TEST=OFF",
        "-DFMT_DOC=OFF", "-DFMT_INSTALL=ON"], args.execute))
    commands.append(_run(["cmake", "--build", fmt_build, "--target", "install", "-j2"], args.execute))

    spdlog_build = prefix / "build" / f"{spdlog_id}-{profile}"
    commands.append(_run([
        "cmake", "-S", spdlog_source, "-B", spdlog_build,
        f"-DCMAKE_INSTALL_PREFIX={runtime_prefix}", f"-DCMAKE_PREFIX_PATH={runtime_prefix}",
        "-DSPDLOG_BUILD_TESTS=OFF", "-DSPDLOG_BUILD_EXAMPLE=OFF",
        "-DSPDLOG_BUILD_BENCH=OFF",
    ], args.execute))
    commands.append(_run([
        "cmake", "--build", spdlog_build, "--target", "install", "-j2"], args.execute))

    fk_prefix = fk_runtime_prefix(lock, profile, prefix)
    if args.execute and not (fk_prefix / "lib" / "cmake" / "pinocchio").is_dir():
        raise RuntimeError(f"locked Pinocchio CMake package missing: {fk_prefix}")
    prefix_path = f"{torch_root};{runtime_prefix};{fk_prefix}"
    sdk2_id = spec.get("unitree_sdk2_artifact")
    configure = [
        "cmake", "-S", source, "-B", build_dir,
        f"-DDEPLOY_PROFILE={profile}", f"-DDEPLOY_LOCK_FILE={lock_path}",
        f"-DCMAKE_PREFIX_PATH={prefix_path}", "-DUSE_TORCH=ON", "-DUSE_FK=ON",
        "-DENABLE_UNITREE_COMMAND_PUBLISH=OFF", "-DEDGE_MINIMAL=ON",
        f"-DUSE_UNITREE_SDK2={'ON' if sdk2_id else 'OFF'}",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    if sdk2_id:
        sdk2_root = _dependency_root(prefix, lock, sdk2_id)
        if args.execute and not sdk2_root.is_dir():
            raise RuntimeError(f"locked Unitree SDK2 source missing: {sdk2_root}")
        configure.extend([
            f"-DUNITREE_SDK2_PATH={sdk2_root}",
            f"-DUNITREE_CYCLONEDDS_PATH={spec['unitree_sdk2_root']}",
        ])
    if spec.get("cuda_arch"):
        configure.extend([
            f"-DCMAKE_CUDA_STANDARD={spec.get('cuda_standard', 14)}",
            f"-DTORCH_CUDA_ARCH_LIST={spec['cuda_arch']}",
        ])
    commands.append(_run(configure, args.execute))
    commands.append(_run(["cmake", "--build", build_dir, "-j2"], args.execute))
    _print({"profile": profile, "execute": args.execute, "commands": commands,
            "build_dir": str(build_dir)})


def _git_commit(source):
    return subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()


def command_install(args, lock_path, lock, profile):
    require_profile(lock, profile, strict=not args.skip_tuple_check)
    source = _source_root(args.source)
    commit = _git_commit(source)
    release = Path(args.prefix).resolve() / "releases" / commit
    if release.exists():
        raise RuntimeError(f"release already exists: {release}")
    command = ["cmake", "--install", str(Path(args.build_dir).resolve()),
               "--prefix", str(release)]
    if not args.execute:
        _print({"profile": profile, "execute": False, "commit": commit,
                "release": str(release), "command": command})
        return
    subprocess.run(command, check=True)
    files = []
    for path in sorted(item for item in release.rglob("*") if item.is_file()):
        files.append({"path": path.relative_to(release).as_posix(),
                      "sha256": sha256_file(path), "size": path.stat().st_size})
    lock_sha = hashlib.sha256(Path(lock_path).read_bytes()).hexdigest()
    manifest = {"schema_version": 1, "profile": profile, "commit": commit,
                "platform_lock_sha256": lock_sha, "files": files}
    manifest_path = release / "install-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    _print({"profile": profile, "execute": True, "commit": commit,
            "release": str(release), "manifest": str(manifest_path)})


def command_verify(args):
    release = Path(args.release).resolve()
    manifest_path = release / "install-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for item in manifest["files"]:
        path = (release / item["path"]).resolve()
        if release not in path.parents or not path.is_file() or sha256_file(path) != item["sha256"]:
            failures.append(item["path"])
    if failures:
        raise RuntimeError(f"release verification failed: {failures}")
    _print({"release": str(release), "profile": manifest["profile"],
            "commit": manifest["commit"], "verified_files": len(manifest["files"])})


def parser():
    result = argparse.ArgumentParser(prog="diffusion-deploy")
    result.add_argument("--lock")
    sub = result.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--profile")

    for name in ("bootstrap", "build", "install", "seed-cache"):
        command = sub.add_parser(name)
        command.add_argument("--profile", required=True)
        command.add_argument("--execute", action="store_true",
                             help="perform writes; omitted means dry-run")
        command.add_argument("--skip-tuple-check", action="store_true",
                             help=argparse.SUPPRESS)
        if name == "seed-cache":
            command.add_argument("--artifact-dir", required=True)
            command.add_argument("--cache-dir", required=True)
        elif name == "bootstrap":
            command.add_argument("--prefix", required=True)
            command.add_argument("--cache-dir", required=True)
            command.add_argument("--offline", action="store_true")
        else:
            command.add_argument("--prefix", required=True)
            command.add_argument("--source")
            command.add_argument("--build-dir", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--release", required=True)

    remove = sub.add_parser("uninstall")
    remove.add_argument("--prefix", required=True)
    remove.add_argument("--execute", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        lock_path, lock = load_lock(args.lock)
        if args.command == "doctor":
            command_doctor(args, lock_path, lock)
        elif args.command == "bootstrap":
            command_bootstrap(args, lock, args.profile)
        elif args.command == "seed-cache":
            command_seed_cache(args, lock, args.profile)
        elif args.command == "build":
            command_build(args, lock_path, lock, args.profile)
        elif args.command == "install":
            command_install(args, lock_path, lock, args.profile)
        elif args.command == "verify":
            command_verify(args)
        elif args.command == "uninstall":
            _print(uninstall(args.prefix, execute=args.execute))
    except (BootstrapError, ProfileError, RuntimeError, OSError,
            subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
