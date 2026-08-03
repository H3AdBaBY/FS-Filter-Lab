"""Classify every bundled TSV using the production dataset processors."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from services.data import (
    _process_filter_file,
    _process_illuminant_file,
    _process_qe_file,
    _process_reflector_file,
    parse_tsv_file,
)


PROCESSORS: dict[str, tuple[str, Callable[[Path], Any]]] = {
    "filters_data": ("filter", _process_filter_file),
    "QE_data": ("qe", _process_qe_file),
    "illuminants": ("illuminant", _process_illuminant_file),
    "reflectors": ("reflector", _process_reflector_file),
}


def _dataset_identity(dataset_type: str, result: Any) -> str:
    if dataset_type == "filter":
        return str(result[3])
    return str(result[0])


def _dataset_diagnostics(dataset_type: str, result: Any, display_path: str) -> list[dict[str, Any]]:
    """Extract structured production diagnostics without leaking absolute paths."""
    if dataset_type == "filter":
        diagnostics = result[3].diagnostics
    elif dataset_type == "qe":
        diagnostics = result[3]["diagnostics"]
    elif dataset_type == "illuminant":
        diagnostics = result[3].diagnostics
    elif dataset_type == "reflector":
        diagnostics = result[1].diagnostics
    else:
        diagnostics = ()

    serialized = []
    for diagnostic in diagnostics:
        item = asdict(diagnostic)
        item["source"] = display_path
        serialized.append(item)
    return serialized


def _skip_reason(dataset_type: str, path: Path) -> str:
    """Explain the explicit rejection branches in the production processors."""
    frame = parse_tsv_file(path)
    columns = set(frame.columns)

    if dataset_type == "filter":
        missing = sorted({"Wavelength", "Transmittance"} - columns)
        return f"missing required column(s): {', '.join(missing)}"
    if dataset_type == "qe":
        if "Wavelength" not in columns:
            return "missing required column: Wavelength"
        return "no R, G, or B channel column"
    if dataset_type == "illuminant":
        return "fewer than two columns"
    if dataset_type == "reflector":
        missing = sorted({"Wavelength", "Reflectance"} - columns)
        if missing:
            return f"missing required column(s): {', '.join(missing)}"
        return "fewer than two non-NaN reflectance samples"
    return "production processor returned no dataset"


def validate_datasets(data_root: Path) -> dict[str, Any]:
    """Return a deterministic, mutually exclusive classification report."""
    root = data_root.resolve()
    files = sorted(root.rglob("*.tsv"), key=lambda item: item.as_posix())
    entries: list[dict[str, str]] = []
    first_identity: dict[tuple[str, str], str] = {}
    first_digest: dict[str, str] = {}

    for path in files:
        relative = path.relative_to(root)
        folder = relative.parts[0] if relative.parts else ""
        display_path = (Path(data_root.name) / relative).as_posix()
        processor_info = PROCESSORS.get(folder)

        if processor_info is None:
            entries.append(
                {
                    "path": display_path,
                    "dataset_type": "unknown",
                    "status": "invalid",
                    "reason": f"unrecognized dataset folder: {folder}",
                }
            )
            continue

        dataset_type, processor = processor_info
        try:
            result = processor(path)
            if result is None:
                entries.append(
                    {
                        "path": display_path,
                        "dataset_type": dataset_type,
                        "status": "skipped",
                        "reason": _skip_reason(dataset_type, path),
                    }
                )
                continue

            identity = _dataset_identity(dataset_type, result)
            identity_key = (dataset_type, identity)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            duplicate_of = first_identity.get(identity_key) or first_digest.get(digest)
            if duplicate_of is not None:
                entries.append(
                    {
                        "path": display_path,
                        "dataset_type": dataset_type,
                        "status": "duplicate",
                        "reason": f"duplicates {duplicate_of} (loader identity or identical bytes)",
                    }
                )
                continue

            first_identity[identity_key] = display_path
            first_digest[digest] = display_path
            diagnostics = _dataset_diagnostics(dataset_type, result, display_path)
            entries.append(
                {
                    "path": display_path,
                    "dataset_type": dataset_type,
                    "status": "accepted",
                    "reason": "accepted by the production processor",
                    "diagnostics": diagnostics,
                }
            )
        except Exception as error:  # Match the production loader's broad failure boundary.
            entries.append(
                {
                    "path": display_path,
                    "dataset_type": dataset_type,
                    "status": "invalid",
                    "reason": f"{type(error).__name__}: {error}",
                }
            )

    status_counts = Counter(entry["status"] for entry in entries)
    by_type: dict[str, dict[str, int]] = {}
    for dataset_type in sorted({entry["dataset_type"] for entry in entries}):
        counts = Counter(
            entry["status"]
            for entry in entries
            if entry["dataset_type"] == dataset_type
        )
        by_type[dataset_type] = {
            "discovered": sum(counts.values()),
            "accepted": counts["accepted"],
            "skipped": counts["skipped"],
            "duplicate": counts["duplicate"],
            "invalid": counts["invalid"],
        }

    summary = {
        "discovered": len(entries),
        "accepted": status_counts["accepted"],
        "skipped": status_counts["skipped"],
        "duplicate": status_counts["duplicate"],
        "invalid": status_counts["invalid"],
    }
    assert summary["discovered"] == sum(
        summary[name] for name in ("accepted", "skipped", "duplicate", "invalid")
    )

    diagnostic_counts = Counter(
        diagnostic["code"]
        for entry in entries
        for diagnostic in entry.get("diagnostics", [])
    )

    return {
        "schema_version": 2,
        "data_root": data_root.as_posix(),
        "summary": summary,
        "by_type": by_type,
        "diagnostics": dict(sorted(diagnostic_counts.items())),
        "files": entries,
    }


def _print_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(
        "Dataset validation: "
        + ", ".join(f"{name}={summary[name]}" for name in summary)
    )
    for dataset_type, counts in report["by_type"].items():
        print(
            f"  {dataset_type}: "
            + ", ".join(f"{name}={counts[name]}" for name in counts)
        )

    diagnostic_files = [
        entry
        for entry in report["files"]
        if any(
            diagnostic["code"] != "unit_interpretation"
            for diagnostic in entry.get("diagnostics", [])
        )
    ]
    print(
        "Diagnostics: "
        + (", ".join(f"{name}={count}" for name, count in report["diagnostics"].items()) or "none")
    )
    if diagnostic_files:
        print("Diagnostic files:")
        for entry in diagnostic_files:
            for diagnostic in entry["diagnostics"]:
                if diagnostic["code"] == "unit_interpretation":
                    continue
                print(
                    f"  [{diagnostic['severity']}] {entry['path']}: "
                    f"{diagnostic['code']}: {diagnostic['message']}"
                )

    affected = [entry for entry in report["files"] if entry["status"] != "accepted"]
    if not affected:
        print("Affected files: none")
        return
    print("Affected files:")
    for entry in affected:
        print(f"  [{entry['status']}] {entry['path']}: {entry['reason']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for the full per-file JSON report.",
    )
    args = parser.parse_args()

    report = validate_datasets(args.data_root)
    _print_report(report)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
