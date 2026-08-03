import numpy as np

from models.constants import INTERP_GRID
from services.data import _process_filter_file, interpolate_to_standard_grid


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
