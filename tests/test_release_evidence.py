from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tomllib

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


ROOT = Path(__file__).resolve().parents[1]


def _requirement_roots(path: Path) -> set[str]:
    roots = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            roots.add(canonicalize_name(Requirement(line).name))
    return roots


def test_release_version_and_privacy_configuration_are_explicit() -> None:
    assert (ROOT / "VERSION").read_text(encoding="utf-8") == "1.0.0\n"
    config = tomllib.loads(
        (ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
    )
    assert config["browser"]["gatherUsageStats"] is False


def test_release_documentation_uses_one_authoritative_limitation_record() -> None:
    required = {
        "CHANGELOG.md",
        "THIRD_PARTY_NOTICES.md",
        "docs/Data-Provenance.md",
        "docs/Known-Limitations.md",
        "docs/Release-Checklist.md",
    }
    assert all((ROOT / relative).is_file() for relative in required)
    for relative in ("README.md", "USAGE.md", "CHANGELOG.md"):
        assert "Known-Limitations.md" in (ROOT / relative).read_text(encoding="utf-8")
    decision_path = ROOT / "docs/Gate5-Decision-Proposal.md"
    if decision_path.exists():
        decision = decision_path.read_text(encoding="utf-8")
        assert "Approved for Gate 5A and Gate 5B implementation" in decision
        assert "does not authorize a tag" in decision
    checklist = (ROOT / "docs/Release-Checklist.md").read_text(encoding="utf-8")
    assert "Publication authority: **Not granted**" in checklist


def test_runtime_dependency_inventory_is_complete_and_pinned() -> None:
    inventory = json.loads(
        (ROOT / "dependency-licenses.json").read_text(encoding="utf-8")
    )
    assert inventory["unresolved_runtime"] == []
    assert inventory["constraints_sha256"] == sha256(
        (ROOT / "constraints-py312.txt").read_bytes()
    ).hexdigest()
    runtime = inventory["runtime"]
    assert {item["normalized_name"] for item in runtime if item["direct"]} == (
        _requirement_roots(ROOT / "requirements.txt")
    )
    assert all(item["license"] != "UNRESOLVED" for item in runtime)
    assert all(item["license_files"] for item in runtime)


def test_dependency_inventory_has_not_drifted() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_dependency_notices.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_installed_runtime_matches_the_committed_inventory() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_dependency_notices.py",
            "--runtime-check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_bundled_license_and_vendor_notices_are_retained() -> None:
    assert (ROOT / "LICENSE").is_file()
    assert (ROOT / "data/LICENSE").is_file()
    expected_vendor_notices = {
        "Chroma Filters",
        "Hoya",
        "Lee Filters",
        "MidOpt",
        "Omega",
        "Schott",
    }
    actual = {
        path.parent.name
        for path in (ROOT / "data/filters_data").glob("*/LICENSE.md")
    }
    assert actual == expected_vendor_notices
