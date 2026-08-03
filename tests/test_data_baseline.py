import numpy as np
import pytest

from models.constants import INTERP_GRID
from services import data as data_service
from services.data import _process_filter_file, cached_loader, interpolate_to_standard_grid


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
