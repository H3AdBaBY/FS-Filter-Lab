from pathlib import Path

from scripts.validate_datasets import validate_datasets


def test_every_bundled_tsv_is_classified_and_counts_reconcile() -> None:
    report = validate_datasets(Path("data"))

    assert report["summary"] == {
        "discovered": 1566,
        "accepted": 1566,
        "skipped": 0,
        "duplicate": 0,
        "invalid": 0,
    }
    assert report["by_type"] == {
        "filter": {
            "discovered": 1558,
            "accepted": 1558,
            "skipped": 0,
            "duplicate": 0,
            "invalid": 0,
        },
        "illuminant": {
            "discovered": 1,
            "accepted": 1,
            "skipped": 0,
            "duplicate": 0,
            "invalid": 0,
        },
        "qe": {
            "discovered": 3,
            "accepted": 3,
            "skipped": 0,
            "duplicate": 0,
            "invalid": 0,
        },
        "reflector": {
            "discovered": 4,
            "accepted": 4,
            "skipped": 0,
            "duplicate": 0,
            "invalid": 0,
        },
    }
    assert len(report["files"]) == report["summary"]["discovered"]
    assert all(entry["reason"] for entry in report["files"])


def test_validator_reports_each_nonaccepted_file_with_a_reason(tmp_path) -> None:
    filters = tmp_path / "filters_data"
    filters.mkdir()
    accepted = (
        "Wavelength\tTransmittance\tFilter Number\tName\tManufacturer\n"
        "400\t0.5\tA\tAccepted\tFixture Lab\n"
        "500\t0.6\t\t\t\n"
    )
    (filters / "accepted.tsv").write_text(accepted, encoding="utf-8")
    (filters / "duplicate.tsv").write_text(accepted, encoding="utf-8")
    (filters / "skipped.tsv").write_text(
        "Wavelength\tName\n400\tMissing transmission\n",
        encoding="utf-8",
    )
    (filters / "invalid.tsv").write_text(
        "Wavelength\tTransmittance\nnot-a-number\t0.5\n",
        encoding="utf-8",
    )

    report = validate_datasets(tmp_path)

    assert report["summary"] == {
        "discovered": 4,
        "accepted": 1,
        "skipped": 1,
        "duplicate": 1,
        "invalid": 1,
    }
    affected = [entry for entry in report["files"] if entry["status"] != "accepted"]
    assert {entry["path"].split("/")[-1] for entry in affected} == {
        "duplicate.tsv",
        "skipped.tsv",
        "invalid.tsv",
    }
    assert all(entry["reason"] for entry in affected)
