"""Build and verify deterministic FS FilterLab populated source archives."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tarfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "RELEASE-MANIFEST.json"
SCHEMA_VERSION = 1

ROOT_FILES = (
    ".streamlit/config.toml",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "TECHNICAL.md",
    "THIRD_PARTY_NOTICES.md",
    "USAGE.md",
    "VERSION",
    "app.py",
    "constraints-py312.txt",
    "dependency-licenses.json",
    "install.sh",
    "pytest.ini",
    "requirements-test.txt",
    "requirements.txt",
    "run.sh",
)
TRACKED_PREFIXES = (
    "models/",
    "scripts/",
    "services/",
    "tests/",
    "third_party_licenses/",
    "views/",
)
RELEASE_DOCS = (
    "docs/Data-Provenance.md",
    "docs/Gate1-Baseline.md",
    "docs/Gate2-Implementation.md",
    "docs/Gate2-Review.md",
    "docs/Gate3-Implementation.md",
    "docs/Gate4-Implementation.md",
    "docs/Gate5-Implementation.md",
    "docs/Known-Limitations.md",
    "docs/Release-Checklist.md",
)
FORBIDDEN_PARTS = {
    ".git",
    ".github",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "cache",
    "dist",
    "output",
    "user_data",
}


def _run_git(arguments: list[str], cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def assert_clean_source() -> None:
    status = _run_git(["status", "--porcelain", "--untracked-files=normal"])
    if status:
        raise RuntimeError("Release candidates require a clean source tree")
    data_status = _run_git(["status", "--porcelain"], cwd=ROOT / "data")
    if data_status:
        raise RuntimeError("Release candidates require a clean bundled-data tree")


def version() -> str:
    value = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not value or any(character not in "0123456789." for character in value):
        raise RuntimeError(f"Invalid release VERSION: {value!r}")
    return value


def release_root_name() -> str:
    return f"FS-Filter-Lab-{version()}"


def _tracked_files() -> list[str]:
    values = _run_git(
        ["ls-files", "--cached", "--others", "--exclude-standard"]
    ).splitlines()
    return sorted(
        value
        for value in values
        if value in ROOT_FILES
        or value in RELEASE_DOCS
        or value.startswith(TRACKED_PREFIXES)
    )


def collect_release_files() -> dict[str, bytes]:
    selected = set(_tracked_files())
    required = set(ROOT_FILES) | set(RELEASE_DOCS)
    missing = sorted(required - selected)
    if missing:
        raise RuntimeError("Release allowlist entries are not tracked: " + ", ".join(missing))

    files: dict[str, bytes] = {}
    for relative in sorted(selected):
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Release input is not a regular file: {relative}")
        files[relative] = path.read_bytes()

    data_root = ROOT / "data"
    if not (data_root / "filters_data").is_dir():
        raise RuntimeError("Populated bundled data is required")
    for path in sorted(data_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_dir():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if ".git" in PurePosixPath(relative).parts:
            continue
        if path.is_symlink():
            raise RuntimeError(f"Bundled data contains a symlink: {relative}")
        files[relative] = path.read_bytes()

    forbidden = sorted(path for path in files if _is_forbidden(path))
    if forbidden:
        raise RuntimeError("Forbidden release inputs: " + ", ".join(forbidden))
    tsv_count = sum(path.startswith("data/") and path.endswith(".tsv") for path in files)
    if tsv_count != 1566:
        raise RuntimeError(f"Expected 1,566 bundled TSV files, found {tsv_count:,}")
    return dict(sorted(files.items()))


def _is_forbidden(relative: str) -> bool:
    path = PurePosixPath(relative)
    if any(part in FORBIDDEN_PARTS for part in path.parts):
        return True
    if any(part.startswith(".gate5-publish-") for part in path.parts):
        return True
    return path.suffix in {".pyc", ".pyo"} or path.name in {".DS_Store"}


def _mode(relative: str) -> int:
    executable = relative in {"install.sh", "run.sh"} or relative.startswith("scripts/")
    return 0o755 if executable else 0o644


def source_metadata() -> dict[str, object]:
    epoch = int(_run_git(["show", "-s", "--format=%ct", "HEAD"]))
    return {
        "application_commit": _run_git(["rev-parse", "HEAD"]),
        "data_commit": _run_git(["rev-parse", "HEAD"], cwd=ROOT / "data"),
        "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "constraints_sha256": sha256((ROOT / "constraints-py312.txt").read_bytes()).hexdigest(),
        "source_date_epoch": epoch,
    }


def manifest(files: dict[str, bytes], metadata: dict[str, object]) -> bytes:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "version": version(),
        "release_root": release_root_name(),
        "source": metadata,
        "files": {
            relative: {
                "mode": f"{_mode(relative):04o}",
                "sha256": sha256(content).hexdigest(),
                "size": len(content),
            }
            for relative, content in files.items()
        },
        "manifest_note": f"{MANIFEST_NAME} describes every other regular file and excludes itself.",
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _directories(paths: list[str]) -> list[str]:
    directories = {release_root_name()}
    for relative in paths:
        current = PurePosixPath(release_root_name())
        for part in PurePosixPath(relative).parts[:-1]:
            current /= part
            directories.add(current.as_posix())
    return sorted(directories, key=lambda value: (value.count("/"), value))


def _zip_timestamp(epoch: int) -> tuple[int, int, int, int, int, int]:
    value = datetime.fromtimestamp(max(epoch, 315532800), tz=timezone.utc)
    return (value.year, value.month, value.day, value.hour, value.minute, value.second)


def _write_zip(path: Path, files: dict[str, bytes], epoch: int) -> None:
    timestamp = _zip_timestamp(epoch)
    with zipfile.ZipFile(path, "w") as archive:
        for directory in _directories(list(files)):
            info = zipfile.ZipInfo(directory + "/", timestamp)
            info.create_system = 3
            info.external_attr = (stat.S_IFDIR | 0o755) << 16
            archive.writestr(info, b"")
        for relative, content in files.items():
            info = zipfile.ZipInfo(f"{release_root_name()}/{relative}", timestamp)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | _mode(relative)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def _write_tar_gz(path: Path, files: dict[str, bytes], epoch: int) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for directory in _directories(list(files)):
                    info = tarfile.TarInfo(directory)
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    info.mtime = epoch
                    archive.addfile(info)
                for relative, content in files.items():
                    info = tarfile.TarInfo(f"{release_root_name()}/{relative}")
                    info.size = len(content)
                    info.mode = _mode(relative)
                    info.mtime = epoch
                    archive.addfile(info, io.BytesIO(content))


def build_candidates(output_dir: Path, require_clean: bool = True) -> dict[str, str]:
    if require_clean:
        assert_clean_source()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = collect_release_files()
    metadata = source_metadata()
    files[MANIFEST_NAME] = manifest(files, metadata)
    files = dict(sorted(files.items()))
    basename = release_root_name()
    outputs = {
        f"{basename}.tar.gz": output_dir / f"{basename}.tar.gz",
        f"{basename}.zip": output_dir / f"{basename}.zip",
    }
    epoch = int(metadata["source_date_epoch"])
    _write_tar_gz(outputs[f"{basename}.tar.gz"], files, epoch)
    _write_zip(outputs[f"{basename}.zip"], files, epoch)
    return {name: sha256(path.read_bytes()).hexdigest() for name, path in outputs.items()}


def _safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise RuntimeError(f"Unsafe archive member: {name}")
    return path


def extract_and_verify(archive_path: Path, destination: Path) -> Path:
    expected_root = release_root_name()
    if destination.exists():
        raise RuntimeError(f"Extraction destination already exists: {destination}")
    destination.mkdir(parents=True)
    archive_files: dict[str, tuple[bytes, int]] = {}

    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                member = _safe_member(info.filename)
                if info.is_dir():
                    (destination / Path(*member.parts)).mkdir(parents=True, exist_ok=True)
                    continue
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise RuntimeError(f"ZIP symlink is not allowed: {info.filename}")
                if member.as_posix() in archive_files:
                    raise RuntimeError(f"Duplicate archive member: {info.filename}")
                payload = archive.read(info)
                mode = (info.external_attr >> 16) & 0o777
                archive_files[member.as_posix()] = (payload, mode)
    else:
        with tarfile.open(archive_path, "r:gz") as archive:
            for info in archive.getmembers():
                member = _safe_member(info.name)
                if info.isdir():
                    (destination / Path(*member.parts)).mkdir(parents=True, exist_ok=True)
                    continue
                if not info.isfile():
                    raise RuntimeError(f"Unsupported archive member type: {info.name}")
                if member.as_posix() in archive_files:
                    raise RuntimeError(f"Duplicate archive member: {info.name}")
                extracted = archive.extractfile(info)
                if extracted is None:
                    raise RuntimeError(f"Cannot read archive member: {info.name}")
                archive_files[member.as_posix()] = (extracted.read(), info.mode & 0o777)

    roots = {PurePosixPath(path).parts[0] for path in archive_files}
    if roots != {expected_root}:
        raise RuntimeError(f"Archive roots differ from {expected_root}: {sorted(roots)}")
    prefixed_manifest = f"{expected_root}/{MANIFEST_NAME}"
    if prefixed_manifest not in archive_files:
        raise RuntimeError("Release manifest is missing")
    manifest_payload = json.loads(archive_files[prefixed_manifest][0])
    if manifest_payload["version"] != version() or manifest_payload["release_root"] != expected_root:
        raise RuntimeError("Release manifest identity mismatch")

    expected = manifest_payload["files"]
    actual_names = {
        path.removeprefix(expected_root + "/")
        for path in archive_files
        if path != prefixed_manifest
    }
    if actual_names != set(expected):
        raise RuntimeError("Archive file set does not match the release manifest")
    for relative, record in expected.items():
        payload, mode = archive_files[f"{expected_root}/{relative}"]
        if len(payload) != record["size"] or sha256(payload).hexdigest() != record["sha256"]:
            raise RuntimeError(f"Manifest hash or size mismatch: {relative}")
        if f"{mode:04o}" != record["mode"]:
            raise RuntimeError(f"Manifest mode mismatch: {relative}")
        if _is_forbidden(relative):
            raise RuntimeError(f"Forbidden archive path: {relative}")

    for archived, (payload, mode) in archive_files.items():
        target = destination / Path(*PurePosixPath(archived).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        target.chmod(mode)
    extracted_root = destination / expected_root
    if len(list((extracted_root / "data").rglob("*.tsv"))) != 1566:
        raise RuntimeError("Extracted bundled TSV count is not 1,566")
    if any((extracted_root / part).exists() for part in (".git", ".gitmodules", "dist", "user_data", "cache", "output")):
        raise RuntimeError("Extracted candidate contains forbidden local state")
    return extracted_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--output-dir", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("archive", type=Path)
    verify.add_argument("--extract-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        hashes = build_candidates(args.output_dir)
        for name, digest in hashes.items():
            print(f"{digest}  {name}")
    else:
        root = extract_and_verify(args.archive, args.extract_dir)
        print(f"Verified release tree: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
