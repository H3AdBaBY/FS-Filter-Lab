from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())

import release_candidate


def test_release_allowlist_is_populated_and_excludes_local_or_planning_state() -> None:
    files = release_candidate.collect_release_files()
    assert sum(path.startswith("data/") and path.endswith(".tsv") for path in files) == 1566
    assert "data/LICENSE" in files
    assert "docs/Known-Limitations.md" in files
    assert "scripts/release_candidate.py" in files
    assert "install.bat" not in files
    assert "start.bat" not in files
    assert not any("Proposal" in path for path in files)
    assert not any(release_candidate._is_forbidden(path) for path in files)


def test_release_manifest_reconciles_every_allowlisted_file() -> None:
    files = release_candidate.collect_release_files()
    payload = json.loads(release_candidate.manifest(files, release_candidate.source_metadata()))
    assert payload["version"] == "1.0.0"
    assert payload["release_root"] == "FS-Filter-Lab-1.0.0"
    assert set(payload["files"]) == set(files)
    assert payload["source"]["data_commit"] == "a1e7a927dcd4c477aca2f7d36748532ad92fb895"


def test_offline_guard_denies_non_loopback_and_allows_loopback() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = (ROOT / "scripts/offline_guard").as_posix()
    environment["FS_FILTERLAB_ENFORCE_OFFLINE"] = "1"
    code = """
import socket
try:
    socket.getaddrinfo('example.com', 443)
except OSError as error:
    assert 'Non-loopback' in str(error)
else:
    raise AssertionError('non-loopback resolution was allowed')
assert socket.getaddrinfo('127.0.0.1', 8501)
"""
    subprocess.run([sys.executable, "-c", code], env=environment, check=True)
