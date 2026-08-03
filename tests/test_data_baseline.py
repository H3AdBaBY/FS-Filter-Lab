import numpy as np
import pytest

from models.constants import INTERP_GRID, REPORT_CONFIG
from services import data as data_service
from services.data import (
    _process_filter_file,
    _process_reflector_file,
    cached_loader,
    interpolate_to_standard_grid,
)
from services.spectral_policy import prepare_spectrum


def test_interpolation_is_linear_and_nan_outside_measured_range() -> None:
    result = interpolate_to_standard_grid(
        np.array([400.0, 500.0, 600.0]),
        np.array([0.2, 0.5, 0.8]),
    )

    assert len(result) == 801
    assert np.isnan(result[INTERP_GRID == 399]).all()
    np.testing.assert_allclose(result[INTERP_GRID == 450], [0.35])
    np.testing.assert_allclose(result[INTERP_GRID == 500], [0.5])
    assert np.isnan(result[INTERP_GRID == 601]).all()


def test_filter_loader_preserves_fractional_fixture(fixture_dir) -> None:
    _, transmission, _, filter_object = _process_filter_file(
        fixture_dir / "synthetic_filter_fraction.tsv"
    )

    np.testing.assert_allclose(
        transmission[np.isin(INTERP_GRID, [400, 500, 600])],
        [0.2, 0.5, 0.8],
    )
    assert str(filter_object) == "Synthetic Fraction (SYN-F, Fixture Lab)"


def test_filter_loader_converts_percentage_fixture_by_maximum_heuristic(fixture_dir) -> None:
    _, transmission, _, _ = _process_filter_file(
        fixture_dir / "synthetic_filter_percent.tsv"
    )

    np.testing.assert_allclose(
        transmission[np.isin(INTERP_GRID, [400, 500, 600])],
        [0.2, 0.5, 0.8],
    )


def test_cache_hit_invalidation_and_corruption_are_deterministic(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "spectrum.tsv"
    source_file.write_text("Wavelength\tValue\n400\t1\n500\t2\n", encoding="utf-8")
    cache = tmp_path / "cache"
    monkeypatch.setattr(data_service, "CACHE_DIR", cache)
    calls = []

    def load_value():
        calls.append(len(calls) + 1)
        return {"generation": calls[-1]}

    assert cached_loader("fixture", source, load_value) == {"generation": 1}
    assert cached_loader("fixture", source, load_value) == {"generation": 1}
    assert calls == [1]

    source_file.write_text("Wavelength\tValue\n400\t1\n500\t3\n", encoding="utf-8")
    assert cached_loader("fixture", source, load_value) == {"generation": 2}

    (cache / "fixture.pkl").write_bytes(b"not a pickle")
    with pytest.warns(RuntimeWarning, match="cache_read_failed"):
        assert cached_loader("fixture", source, load_value) == {"generation": 3}


def test_cache_round_trip_preserves_domain_and_extrapolation_masks(
    tmp_path, monkeypatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "spectrum.tsv").write_text(
        "Wavelength\tValue\n400\t0.2\n500\t0.8\n", encoding="utf-8"
    )
    monkeypatch.setattr(data_service, "CACHE_DIR", tmp_path / "cache")
    prepared = prepare_spectrum(
        np.array([400.0, 500.0]),
        np.array([0.2, 0.8]),
        "transmission",
        unit="fraction",
        extrapolation="constant",
    )

    cached_loader("masks", source, lambda: prepared)
    restored = cached_loader("masks", source, lambda: None)

    np.testing.assert_array_equal(restored.measured_mask, prepared.measured_mask)
    np.testing.assert_array_equal(
        restored.extrapolated_mask, prepared.extrapolated_mask
    )


def test_absorption_data_is_not_accepted_as_reflectance(tmp_path) -> None:
    absorption = tmp_path / "absorption.tsv"
    absorption.write_text(
        "Wavelength\tAbsorption\tName\n400\t0.2\tFixture\n500\t0.4\t\n",
        encoding="utf-8",
    )

    assert _process_reflector_file(absorption) is None


def test_report_configuration_contains_every_renderer_font_role() -> None:
    assert {
        "filter_label",
        "section_header",
        "main_title",
        "title",
        "subtitle",
        "legend",
    } <= REPORT_CONFIG["font_sizes"].keys()
