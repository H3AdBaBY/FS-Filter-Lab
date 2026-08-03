"""Run the approved Gate 5 local release-candidate verification matrix."""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import release_candidate


ROOT = Path(__file__).resolve().parents[1]
DEPENDENCY_CACHE = Path(
    os.environ.get("FS_FILTERLAB_GATE5_DEPENDENCY_CACHE", "/private/tmp/fs-filterlab-gate5-dependencies")
)


def _run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    environment: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=True,
        text=True,
        capture_output=capture,
    )


def _environment(**values: Path | str) -> dict[str, str]:
    result = os.environ.copy()
    result.update({name: str(value) for name, value in values.items()})
    return result


def _wait_for_health(process: subprocess.Popen[str], port: int, log_path: Path) -> None:
    url = f"http://127.0.0.1:{port}/_stcore/health"
    for _ in range(160):
        if process.poll() is not None:
            raise RuntimeError(
                "Candidate launcher exited before health check:\n"
                + log_path.read_text(encoding="utf-8", errors="replace")[:10000]
            )
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(
        "Candidate launcher did not become healthy:\n"
        + log_path.read_text(encoding="utf-8", errors="replace")[:10000]
    )


def _verify_extracted_candidate(
    release_root: Path,
    work_root: Path,
    label: str,
    port: int,
) -> None:
    if (release_root / ".git").exists() or (release_root / ".gitmodules").exists():
        raise RuntimeError(f"{label} unexpectedly contains Git metadata")
    venv = work_root / f"{label}-venv"
    common = _environment(
        PYTHON_BIN=sys.executable,
        PIP_CACHE_DIR=DEPENDENCY_CACHE / "pip",
        MPLCONFIGDIR=DEPENDENCY_CACHE / "matplotlib",
        FS_FILTERLAB_VENV_DIR=venv,
    )
    _run(["sh", "install.sh"], cwd=release_root, environment=common)
    _run(["sh", "run.sh", "--check"], cwd=release_root, environment=common)
    python = venv / "bin/python"
    _run([str(python), "-m", "pip", "check"], cwd=release_root, environment=common)
    _run(
        [str(python), "scripts/generate_dependency_notices.py", "--runtime-check"],
        cwd=release_root,
        environment=common,
    )
    validation = _run(
        [str(python), "scripts/validate_datasets.py"],
        cwd=release_root,
        environment=common,
        capture=True,
    )
    expected = "Dataset validation: discovered=1566, accepted=1566, skipped=0, duplicate=0, invalid=0"
    if expected not in validation.stdout:
        raise RuntimeError(f"{label} dataset reconciliation changed:\n{validation.stdout}")
    print(validation.stdout, end="", flush=True)

    runtime = common.copy()
    runtime.update(
        {
            "PYTHONPATH": str(release_root / "scripts/offline_guard"),
            "FS_FILTERLAB_ENFORCE_OFFLINE": "1",
            "MPLBACKEND": "Agg",
            "MPLCONFIGDIR": str(DEPENDENCY_CACHE / "matplotlib"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "FS_FILTERLAB_CACHE_DIR": str(work_root / f"{label}-cache"),
            "FS_FILTERLAB_USER_DATA_DIR": str(work_root / f"{label}-user-data"),
            "FS_FILTERLAB_OUTPUT_DIR": str(work_root / f"{label}-output"),
            "FS_FILTERLAB_GATE3_CACHE_DIR": str(work_root / f"{label}-gate3-cache"),
        }
    )
    denial_code = (
        "import socket\n"
        "try: socket.getaddrinfo('example.com', 443)\n"
        "except OSError as error: assert 'Non-loopback' in str(error)\n"
        "else: raise AssertionError('non-loopback access was allowed')\n"
    )
    _run([str(python), "-c", denial_code], cwd=release_root, environment=runtime)

    log_path = work_root / f"{label}-streamlit.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                "sh",
                "run.sh",
                "--server.headless",
                "true",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                str(port),
            ],
            cwd=release_root,
            env=runtime,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_for_health(process, port, log_path)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    print(f"{label} offline localhost health: passed")

    gate3_runtime = runtime.copy()
    gate3_runtime.update(
        {
            "FS_FILTERLAB_CACHE_DIR": str(work_root / f"{label}-gate3-app-cache"),
            "FS_FILTERLAB_USER_DATA_DIR": str(work_root / f"{label}-gate3-user-data"),
            "FS_FILTERLAB_OUTPUT_DIR": str(work_root / f"{label}-gate3-output"),
        }
    )
    _run(
        [str(python), "scripts/gate3_vertical_workflow.py"],
        cwd=release_root,
        environment=gate3_runtime,
    )
    gate4_runtime = runtime.copy()
    gate4_runtime.update(
        {
            "FS_FILTERLAB_CACHE_DIR": str(work_root / f"{label}-gate4-cache"),
            "FS_FILTERLAB_USER_DATA_DIR": str(work_root / f"{label}-gate4-user-data"),
            "FS_FILTERLAB_OUTPUT_DIR": str(work_root / f"{label}-gate4-output"),
        }
    )
    _run(
        [str(python), "scripts/gate4_interactions.py"],
        cwd=release_root,
        environment=gate4_runtime,
    )
    print(f"{label} extracted candidate workflow: passed")


def _publish_candidates(
    source_dir: Path,
    hashes: dict[str, str],
    metadata: dict[str, object],
) -> Path:
    publish_dir = Path(tempfile.mkdtemp(prefix=".gate5-publish-", dir=ROOT))
    for name in sorted(hashes):
        shutil.copy2(source_dir / name, publish_dir / name)
    checksum_text = "".join(f"{hashes[name]}  {name}\n" for name in sorted(hashes))
    (publish_dir / "SHA256SUMS").write_text(checksum_text, encoding="utf-8")
    evidence = {
        "schema_version": 1,
        "version": release_candidate.version(),
        "source": metadata,
        "build_environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "archive_builder_schema": release_candidate.SCHEMA_VERSION,
        },
        "archives": {
            name: {"sha256": hashes[name], "verified_extracted": True}
            for name in sorted(hashes)
        },
        "gate4_complete": True,
        "dependency_licenses_unresolved": 0,
        "bundled_tsv": {
            "discovered": 1566,
            "accepted": 1566,
            "skipped": 0,
            "duplicate": 0,
            "invalid": 0,
        },
        "offline_non_loopback_denied": True,
        "manual_keyboard_voiceover": "pending",
        "publication_authority": "not_granted",
    }
    (publish_dir / "release-evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    final_dir = ROOT / "dist"
    backup = ROOT / ".gate5-dist-backup"
    if backup.exists():
        shutil.rmtree(backup)
    try:
        if final_dir.exists():
            final_dir.replace(backup)
        publish_dir.replace(final_dir)
    except Exception:
        if not final_dir.exists() and backup.exists():
            backup.replace(final_dir)
        raise
    if backup.exists():
        shutil.rmtree(backup)
    return final_dir


def main() -> int:
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Gate 5 release verification requires Python 3.12")
    release_candidate.assert_clean_source()
    DEPENDENCY_CACHE.mkdir(parents=True, exist_ok=True)
    (DEPENDENCY_CACHE / "pip").mkdir(exist_ok=True)
    (DEPENDENCY_CACHE / "matplotlib").mkdir(exist_ok=True)

    gate4_environment = _environment(
        PYTHON_BIN=sys.executable,
        FS_FILTERLAB_VERIFY_CACHE=DEPENDENCY_CACHE,
    )
    _run(["bash", "scripts/run_gate4_verification.sh"], environment=gate4_environment)

    with tempfile.TemporaryDirectory(prefix="fs-filterlab-gate5-") as temporary:
        work_root = Path(temporary)
        audit_venv = work_root / "audit-venv"
        _run([sys.executable, "-m", "venv", str(audit_venv)])
        audit_python = audit_venv / "bin/python"
        audit_environment = _environment(PIP_CACHE_DIR=DEPENDENCY_CACHE / "pip")
        _run(
            [
                str(audit_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--quiet",
                "-r",
                "requirements.txt",
                "-r",
                "requirements-test.txt",
            ],
            environment=audit_environment,
        )
        _run(
            [str(audit_python), "scripts/generate_dependency_notices.py", "--check"],
            environment=audit_environment,
        )

        build_one = work_root / "build-one"
        build_two = work_root / "build-two"
        hashes_one = release_candidate.build_candidates(build_one)
        hashes_two = release_candidate.build_candidates(build_two)
        if hashes_one != hashes_two:
            raise RuntimeError(
                f"Consecutive candidate builds differ: {hashes_one!r} != {hashes_two!r}"
            )
        print("Consecutive archive hashes: identical")

        archives = sorted(hashes_one)
        for index, name in enumerate(archives):
            first_extract = work_root / f"extract-{index + 1}"
            second_extract = work_root / f"confirm-{index + 1}"
            release_root = release_candidate.extract_and_verify(build_one / name, first_extract)
            release_candidate.extract_and_verify(build_two / name, second_extract)
            _verify_extracted_candidate(
                release_root,
                work_root,
                "tar" if name.endswith(".tar.gz") else "zip",
                18601 + index,
            )

        metadata = release_candidate.source_metadata()
        final_dir = _publish_candidates(build_one, hashes_one, metadata)
    print(f"Gate 5 local candidates published to {final_dir}")
    print("Gate 5A/Gate 5B automated verification: passed")
    print("Gate 5C manual accessibility and publication approvals: pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
