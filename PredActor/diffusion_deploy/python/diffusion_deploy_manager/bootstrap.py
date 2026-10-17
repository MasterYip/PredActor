import hashlib
import json
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


class BootstrapError(RuntimeError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_target(root, name):
    target = (root / name).resolve()
    if target != root and root not in target.parents:
        raise BootstrapError(f"archive path escapes destination: {name}")
    return target


def safe_extract(archive, kind, destination, skip_safe_symlinks=False):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if kind in ("zip", "wheel"):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                _safe_target(destination, member.filename)
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise BootstrapError(f"archive link is not allowed: {member.filename}")
            bundle.extractall(destination)
        return
    if kind == "tar.gz":
        with tarfile.open(archive, "r:gz") as bundle:
            for member in bundle.getmembers():
                target = _safe_target(destination, member.name)
                if member.issym():
                    link_target = (target.parent / member.linkname).resolve()
                    if link_target != destination and destination not in link_target.parents:
                        raise BootstrapError(f"archive link escapes destination: {member.name}")
                    if skip_safe_symlinks:
                        continue
                    raise BootstrapError(f"archive link is not allowed: {member.name}")
                if member.islnk():
                    raise BootstrapError(f"archive link is not allowed: {member.name}")
            members = (member for member in bundle.getmembers()
                       if not (skip_safe_symlinks and member.issym()))
            bundle.extractall(destination, members=members)
        return
    raise BootstrapError(f"unsupported artifact kind: {kind}")


def _download(url, partial):
    partial = Path(partial)
    offset = partial.stat().st_size if partial.exists() else 0
    request = urllib.request.Request(url)
    if offset:
        request.add_header("Range", f"bytes={offset}-")
    with urllib.request.urlopen(request) as response:
        if offset and response.status != 206:
            offset = 0
        mode = "ab" if offset else "wb"
        with partial.open(mode) as stream:
            shutil.copyfileobj(response, stream, length=1024 * 1024)


def ensure_artifact(artifact_id, artifact, cache_dir, offline=False):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    final = cache_dir / f"{artifact['sha256']}-{artifact['filename']}"
    if final.is_file():
        actual_size = final.stat().st_size
        actual_sha256 = sha256_file(final)
        if actual_size == artifact["size"] and actual_sha256 == artifact["sha256"]:
            return final
        raise BootstrapError(
            f"refusing corrupt cache entry for {artifact_id}: "
            f"size={actual_size}, sha256={actual_sha256}")
    if offline:
        raise BootstrapError(f"offline cache miss: {artifact_id}")
    partial = final.with_suffix(final.suffix + ".part")
    _download(artifact["url"], partial)
    if partial.stat().st_size != artifact["size"]:
        raise BootstrapError(
            f"artifact size mismatch for {artifact_id}: {partial.stat().st_size}")
    actual = sha256_file(partial)
    if actual != artifact["sha256"]:
        partial.unlink()
        raise BootstrapError(f"artifact checksum mismatch for {artifact_id}: {actual}")
    partial.replace(final)
    return final


def profile_artifact_ids(profile):
    platform_artifacts = []
    if profile.get("unitree_sdk2_artifact"):
        platform_artifacts.append(profile["unitree_sdk2_artifact"])
    return ([profile["torch_artifact"]]
            + platform_artifacts
            + profile.get("source_dependencies", [])
            + profile.get("runtime_dependencies", []))


def fk_runtime_prefix(lock, profile_name, prefix):
    dependencies = lock["profiles"][profile_name].get("runtime_dependencies", [])
    if not dependencies:
        return None
    marker_payload = "\n".join(
        f"{item} {lock['artifacts'][item]['sha256']}" for item in dependencies) + "\n"
    digest = hashlib.sha256(marker_payload.encode("ascii")).hexdigest()
    return Path(prefix).resolve() / "runtime" / f"cmeel.prefix-{digest[:12]}"


def _merge_tree(source, destination):
    """Merge a wheel prefix, rejecting ambiguous or non-identical collisions."""
    for path in sorted(Path(source).rglob("*")):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_symlink():
            raise BootstrapError(f"dependency wheel contains unsupported symlink: {relative}")
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if not target.is_file() or sha256_file(target) != sha256_file(path):
                raise BootstrapError(f"conflicting dependency prefix file: {relative}")
            continue
        shutil.copyfile(path, target)


def seed_cache_from_directory(lock, profile_name, source_dir, cache_dir,
                              execute=False):
    """Validate lock-named artifacts and optionally add them to the cache."""
    profile = lock["profiles"][profile_name]
    artifact_ids = profile_artifact_ids(profile)
    source_dir = Path(source_dir).resolve()
    cache_dir = Path(cache_dir).resolve()
    if not source_dir.is_dir():
        raise BootstrapError(f"artifact directory not found: {source_dir}")

    planned = []
    for artifact_id in artifact_ids:
        artifact = lock["artifacts"][artifact_id]
        source = source_dir / artifact["filename"]
        if not source.is_file():
            raise BootstrapError(f"pinned artifact missing: {source}")
        if source.stat().st_size != artifact["size"]:
            raise BootstrapError(f"artifact size mismatch for {artifact_id}")
        actual = sha256_file(source)
        if actual != artifact["sha256"]:
            raise BootstrapError(f"artifact checksum mismatch for {artifact_id}: {actual}")
        destination = cache_dir / f"{actual}-{artifact['filename']}"
        if destination.exists() and sha256_file(destination) != actual:
            raise BootstrapError(f"refusing corrupt cache entry: {destination}")
        planned.append((artifact_id, source, destination, actual))

    if execute:
        cache_dir.mkdir(parents=True, exist_ok=True)
        for _, source, destination, _ in planned:
            if not destination.exists():
                shutil.copyfile(source, destination)

    return {
        "profile": profile_name,
        "source_dir": str(source_dir),
        "cache_dir": str(cache_dir),
        "execute": execute,
        "artifacts": [
            {"id": item[0], "destination": str(item[2]), "sha256": item[3]}
            for item in planned
        ],
    }


def bootstrap_profile(lock, profile_name, prefix, cache_dir, offline=False, execute=False):
    profile = lock["profiles"][profile_name]
    artifact_ids = profile_artifact_ids(profile)
    plan = {
        "profile": profile_name,
        "prefix": str(Path(prefix).resolve()),
        "cache_dir": str(Path(cache_dir).resolve()),
        "artifacts": artifact_ids,
        "execute": execute,
    }
    if not execute:
        return plan

    prefix = Path(prefix).resolve()
    deps_root = prefix / "deps"
    manifest_path = prefix / "bootstrap-manifest.json"
    installed = []
    for artifact_id in artifact_ids:
        artifact = lock["artifacts"][artifact_id]
        archive = ensure_artifact(artifact_id, artifact, cache_dir, offline=offline)
        destination = deps_root / artifact_id
        marker = destination / ".artifact-sha256"
        if marker.is_file() and marker.read_text(encoding="ascii").strip() == artifact["sha256"]:
            installed.append({"id": artifact_id, "path": str(destination), "sha256": artifact["sha256"]})
            continue
        if destination.exists():
            raise BootstrapError(f"refusing to overwrite unverified dependency: {destination}")
        deps_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".extract-", dir=str(deps_root)) as temp:
            temp_path = Path(temp)
            safe_extract(archive, artifact["kind"], temp_path,
                         skip_safe_symlinks=artifact.get("skip_safe_symlinks", False))
            temp_path.rename(destination)
        marker.write_text(artifact["sha256"] + "\n", encoding="ascii")
        installed.append({"id": artifact_id, "path": str(destination), "sha256": artifact["sha256"]})

    fk_dependencies = profile.get("runtime_dependencies", [])
    fk_prefix = fk_runtime_prefix(lock, profile_name, prefix)
    if fk_dependencies:
        partial = fk_prefix.with_name(f".{fk_prefix.name}.partial")
        if partial.exists():
            shutil.rmtree(partial)
        partial.mkdir(parents=True)
        for artifact_id in fk_dependencies:
            artifact = lock["artifacts"][artifact_id]
            wheel_root = deps_root / artifact_id / artifact["root"]
            if not wheel_root.is_dir():
                raise BootstrapError(
                    f"native wheel prefix missing for {artifact_id}: {wheel_root}")
            _merge_tree(wheel_root, partial)
        marker_payload = "\n".join(
            f"{item} {lock['artifacts'][item]['sha256']}" for item in fk_dependencies) + "\n"
        marker = fk_prefix / ".dependency-lock"
        if fk_prefix.exists():
            if not marker.is_file() or marker.read_text(encoding="ascii") != marker_payload:
                raise BootstrapError(f"refusing unverified FK runtime prefix: {fk_prefix}")
            shutil.rmtree(partial)
        else:
            partial.rename(fk_prefix)
            marker.write_text(marker_payload, encoding="ascii")
        installed.append({"id": "pinocchio-native-runtime", "path": str(fk_prefix),
                          "sha256": hashlib.sha256(marker_payload.encode("ascii")).hexdigest()})

    payload = {"schema_version": 1, "profile": profile_name, "installed": installed,
               "fk_runtime_prefix": str(fk_prefix) if fk_dependencies else None}
    prefix.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def uninstall(prefix, execute=False):
    prefix = Path(prefix).resolve()
    manifest_path = prefix / "bootstrap-manifest.json"
    if not manifest_path.is_file():
        raise BootstrapError(f"install manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = [Path(item["path"]).resolve() for item in manifest["installed"]]
    for path in paths:
        if prefix not in path.parents:
            raise BootstrapError(f"manifest path escapes prefix: {path}")
    if execute:
        for path in paths:
            if path.exists():
                shutil.rmtree(path)
        manifest_path.unlink()
    return {"prefix": str(prefix), "remove": [str(path) for path in paths], "execute": execute}
