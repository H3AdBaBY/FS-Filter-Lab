"""Generate deterministic runtime/test dependency license inventories."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import sys

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "dependency-licenses.json"
NOTICE_PATH = ROOT / "THIRD_PARTY_NOTICES.md"


def requirement_roots(path: Path) -> list[str]:
    roots = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        roots.append(canonicalize_name(Requirement(line).name))
    return sorted(set(roots))


def dependency_closure(roots: list[str]) -> dict[str, metadata.Distribution]:
    environment = default_environment()
    environment["extra"] = ""
    resolved: dict[str, metadata.Distribution] = {}
    pending = list(roots)
    while pending:
        name = canonicalize_name(pending.pop())
        if name in resolved:
            continue
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError as error:
            raise RuntimeError(f"Required distribution is not installed: {name}") from error
        resolved[name] = distribution
        for value in distribution.requires or []:
            requirement = Requirement(value)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            dependency = canonicalize_name(requirement.name)
            if dependency not in resolved:
                pending.append(dependency)
    return resolved


def constraints() -> dict[str, str]:
    result = {}
    for raw_line in (ROOT / "constraints-py312.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        requirement = Requirement(line)
        pins = [item.version for item in requirement.specifier if item.operator == "=="]
        if len(pins) != 1:
            raise RuntimeError(f"Constraint is not one exact pin: {line}")
        result[canonicalize_name(requirement.name)] = pins[0]
    return result


def license_files(
    distribution: metadata.Distribution, normalized_name: str
) -> list[dict[str, str]]:
    records = []
    for relative in distribution.files or []:
        lowered = relative.name.casefold()
        path_text = str(relative).casefold()
        if not (
            lowered.startswith(("license", "copying", "notice"))
            or "/licenses/" in f"/{path_text}"
        ):
            continue
        path = distribution.locate_file(relative)
        if not path.is_file():
            continue
        payload = path.read_bytes()
        records.append(
            {
                "path": str(relative).replace("\\", "/"),
                "sha256": sha256(payload).hexdigest(),
            }
        )
    override_root = ROOT / "third_party_licenses" / (
        f"{normalized_name}-{distribution.version}"
    )
    if override_root.exists():
        for path in sorted(item for item in override_root.rglob("*") if item.is_file()):
            payload = path.read_bytes()
            records.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": sha256(payload).hexdigest(),
                }
            )
    return sorted(records, key=lambda item: item["path"].casefold())


CLASSIFIER_LICENSES = {
    "Apache Software License": "Apache-2.0",
    "BSD License": "BSD-3-Clause",
    "GNU Lesser General Public License v3 or later (LGPLv3+)": "LGPL-3.0-or-later",
    "ISC License (ISCL)": "ISC",
    "MIT License": "MIT",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Python Software Foundation License": "PSF-2.0",
}


def classify_license(distribution: metadata.Distribution) -> str:
    package_metadata = distribution.metadata
    expression = (package_metadata.get("License-Expression") or "").strip()
    if expression and expression.casefold() != "unknown":
        return expression

    classifiers = [
        value.rsplit("::", 1)[-1].strip()
        for value in package_metadata.get_all("Classifier", [])
        if value.startswith("License :: OSI Approved ::")
    ]
    classified = sorted(
        {CLASSIFIER_LICENSES[value] for value in classifiers if value in CLASSIFIER_LICENSES}
    )
    if classified:
        return " OR ".join(classified)

    short_license = (package_metadata.get("License") or "").strip()
    short_map = {
        "Apache 2.0": "Apache-2.0",
        "Apache-2.0": "Apache-2.0",
        "BSD": "BSD-3-Clause",
        "BSD-3-Clause": "BSD-3-Clause",
        "ISC": "ISC",
        "MIT": "MIT",
        "MIT License": "MIT",
        "MPL-2.0": "MPL-2.0",
        "PSF": "PSF-2.0",
    }
    if short_license in short_map:
        return short_map[short_license]

    contents = []
    for relative in distribution.files or []:
        lowered = relative.name.casefold()
        if not lowered.startswith(("license", "copying")):
            continue
        path = distribution.locate_file(relative)
        if path.is_file():
            contents.append(path.read_text(encoding="utf-8", errors="replace")[:20000])
    combined = "\n".join(contents).casefold()
    signatures = (
        ("mozilla public license version 2.0", "MPL-2.0"),
        ("apache license\n                           version 2.0", "Apache-2.0"),
        ("apache license, version 2.0", "Apache-2.0"),
        ("isc license", "ISC"),
        ("python software foundation license version 2", "PSF-2.0"),
        ("mit license", "MIT"),
    )
    for signature, identifier in signatures:
        if signature in combined:
            return identifier
    if "redistribution and use in source and binary forms" in combined:
        return "BSD-3-Clause" if "neither the name" in combined else "BSD-2-Clause"
    return "UNRESOLVED"


def project_url(distribution: metadata.Distribution) -> str:
    values = distribution.metadata.get_all("Project-URL", [])
    priorities = ("source", "repository", "homepage", "documentation")
    for priority in priorities:
        for value in values:
            label, separator, url = value.partition(",")
            if separator and label.strip().casefold() == priority:
                return url.strip()
    return (distribution.metadata.get("Home-page") or "").strip()


def record(
    name: str,
    distribution: metadata.Distribution,
    direct: bool,
    expected_versions: dict[str, str],
) -> dict:
    expected = expected_versions.get(name)
    if expected is None:
        raise RuntimeError(f"Installed dependency lacks an exact constraint: {name}")
    if distribution.version != expected:
        raise RuntimeError(
            f"Constraint mismatch for {name}: installed {distribution.version}, expected {expected}"
        )
    return {
        "name": distribution.metadata.get("Name") or name,
        "normalized_name": name,
        "version": distribution.version,
        "direct": direct,
        "license": classify_license(distribution),
        "license_files": license_files(distribution, name),
        "project_url": project_url(distribution),
    }


def build_inventory() -> dict:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Dependency notices require the pinned Python 3.12 environment")
    runtime_roots = requirement_roots(ROOT / "requirements.txt")
    test_roots = requirement_roots(ROOT / "requirements-test.txt")
    runtime = dependency_closure(runtime_roots)
    test = dependency_closure(test_roots)
    expected = constraints()
    runtime_records = [
        record(name, distribution, name in runtime_roots, expected)
        for name, distribution in sorted(runtime.items())
    ]
    test_only_records = [
        record(name, distribution, name in test_roots, expected)
        for name, distribution in sorted(test.items())
        if name not in runtime
    ]
    unresolved = [
        item["normalized_name"]
        for item in runtime_records
        if item["license"] == "UNRESOLVED" or not item["license_files"]
    ]
    return {
        "schema_version": 1,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "constraints_file": "constraints-py312.txt",
        "constraints_sha256": sha256(
            (ROOT / "constraints-py312.txt").read_bytes()
        ).hexdigest(),
        "runtime": runtime_records,
        "test_only": test_only_records,
        "unresolved_runtime": sorted(unresolved),
    }


def render_notice(inventory: dict) -> str:
    lines = [
        "# Third-party notices",
        "",
        "FS FilterLab does not bundle a Python runtime or dependency wheels. The",
        "installer obtains the exact distributions constrained by",
        "`constraints-py312.txt`. Their license files remain in each installed",
        "distribution and are identified below by path and SHA-256.",
        "",
        "This is a deterministic engineering inventory, not legal advice.",
        "",
        "## Runtime dependencies",
        "",
        "| Distribution | Version | Direct | License | Installed license files |",
        "|---|---:|:---:|---|---:|",
    ]
    for item in inventory["runtime"]:
        lines.append(
            f"| {item['name']} | {item['version']} | "
            f"{'Yes' if item['direct'] else 'No'} | {item['license']} | "
            f"{len(item['license_files'])} |"
        )
    lines.extend(
        [
            "",
            "## Test-only dependencies",
            "",
            "These are used to audit the released source and are not required to",
            "run the application.",
            "",
            "| Distribution | Version | Direct | License | Installed license files |",
            "|---|---:|:---:|---|---:|",
        ]
    )
    for item in inventory["test_only"]:
        lines.append(
            f"| {item['name']} | {item['version']} | "
            f"{'Yes' if item['direct'] else 'No'} | {item['license']} | "
            f"{len(item['license_files'])} |"
        )
    lines.extend(
        [
            "",
            "The machine-readable `dependency-licenses.json` records canonical",
            "names, exact versions, project URLs, installed license-file paths, and",
            "license-file hashes. Regenerate both files only from the pinned Python",
            "3.12 environment with `python scripts/generate_dependency_notices.py`.",
            "",
        ]
    )
    return "\n".join(lines)


def serialized_outputs() -> tuple[str, str, dict]:
    inventory = build_inventory()
    json_text = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    return json_text, render_notice(inventory), inventory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="fail if committed inventories drift"
    )
    args = parser.parse_args()
    json_text, notice_text, inventory = serialized_outputs()
    if inventory["unresolved_runtime"]:
        raise SystemExit(
            "Unresolved runtime license evidence: "
            + ", ".join(inventory["unresolved_runtime"])
        )
    outputs = ((JSON_PATH, json_text), (NOTICE_PATH, notice_text))
    if args.check:
        stale = [
            path.name
            for path, content in outputs
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            raise SystemExit("Dependency notice drift: " + ", ".join(stale))
    else:
        for path, content in outputs:
            path.write_text(content, encoding="utf-8")
    print(
        f"Dependency licenses: {len(inventory['runtime'])} runtime, "
        f"{len(inventory['test_only'])} test-only, 0 unresolved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
