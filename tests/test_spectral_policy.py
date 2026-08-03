import numpy as np
import pytest

from models.constants import INTERP_GRID
from services.importing import interpolate_spectrum
from services.spectral_policy import infer_legacy_unit, prepare_spectrum


def _at(values: np.ndarray, wavelength: int) -> float:
    return float(values[INTERP_GRID == wavelength][0])


@pytest.mark.parametrize(
    ("maximum", "expected"),
    [(1.0, "fraction"), (1.2, "percent"), (100.0, "percent"), (101.0, "percent")],
)
def test_legacy_unit_inference_is_deterministic(maximum: float, expected: str) -> None:
    values = np.array([0.0, maximum])

    assert infer_legacy_unit(values, "transmission") == expected


def test_explicit_fraction_percent_and_qe_units_normalize_once() -> None:
    wavelengths = np.array([400.0, 500.0])
    fraction = prepare_spectrum(
        wavelengths, np.array([0.2, 0.8]), "transmission", unit="fraction"
    )
    percent = prepare_spectrum(
        wavelengths, np.array([20.0, 80.0]), "transmission", unit="percent"
    )
    qe_fraction = prepare_spectrum(
        wavelengths, np.array([0.2, 0.8]), "qe", unit="fraction"
    )

    np.testing.assert_allclose(fraction.raw_values, percent.raw_values, equal_nan=True)
    assert _at(qe_fraction.raw_values, 400) == pytest.approx(20.0)
    assert _at(qe_fraction.raw_values, 500) == pytest.approx(80.0)


def test_unsorted_samples_are_stable_sorted_and_report_the_source() -> None:
    result = prepare_spectrum(
        np.array([500.0, 400.0, 600.0]),
        np.array([0.5, 0.2, 0.8]),
        "transmission",
        unit="fraction",
        source="fixture.tsv",
    )

    assert _at(result.raw_values, 450) == pytest.approx(0.35)
    diagnostic = next(item for item in result.diagnostics if item.code == "wavelengths_sorted")
    assert diagnostic.source == "fixture.tsv"


def test_duplicate_and_nonfinite_wavelengths_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate wavelength"):
        prepare_spectrum(
            np.array([400.0, 400.0]),
            np.array([0.2, 0.3]),
            "transmission",
        )
    with pytest.raises(ValueError, match="must be finite"):
        prepare_spectrum(
            np.array([400.0, np.nan]),
            np.array([0.2, 0.3]),
            "transmission",
        )


def test_raw_excursions_are_preserved_and_physical_values_are_clipped() -> None:
    result = prepare_spectrum(
        np.array([400.0, 500.0, 600.0, 700.0, 800.0]),
        np.array([-0.1, 0.0, 0.5, 1.2, np.nan]),
        "reflectance",
        unit="fraction",
        source="excursions.tsv",
    )

    assert _at(result.raw_values, 400) == pytest.approx(-0.1)
    assert _at(result.raw_values, 700) == pytest.approx(1.2)
    assert np.isnan(_at(result.raw_values, 800))
    assert _at(result.physical_values, 400) == 0.0
    assert _at(result.physical_values, 700) == 1.0
    assert np.isnan(_at(result.physical_values, 800))
    codes = {item.code for item in result.diagnostics}
    assert {"physical_bounds_clipped", "nonfinite_values_preserved"} <= codes


def test_measured_support_is_explicit_and_outside_values_remain_unknown() -> None:
    result = prepare_spectrum(
        np.array([400.0, 500.0]),
        np.array([0.2, 0.8]),
        "transmission",
        unit="fraction",
    )

    assert not result.measured_mask[INTERP_GRID == 399].any()
    assert result.measured_mask[INTERP_GRID == 400].all()
    assert result.measured_mask[INTERP_GRID == 500].all()
    assert not result.measured_mask[INTERP_GRID == 501].any()
    assert np.isnan(_at(result.physical_values, 399))
    assert not result.extrapolated_mask.any()


def test_constant_extrapolation_is_explicit_and_masked() -> None:
    result = prepare_spectrum(
        np.array([400.0, 500.0]),
        np.array([0.2, 0.8]),
        "transmission",
        unit="fraction",
        extrapolation="constant",
    )

    assert _at(result.physical_values, 399) == pytest.approx(0.2)
    assert _at(result.physical_values, 501) == pytest.approx(0.8)
    assert result.extrapolated_mask[INTERP_GRID == 399].all()
    assert not result.extrapolated_mask[INTERP_GRID == 450].any()


def test_loader_and_importer_share_the_same_validated_interpolation() -> None:
    wavelengths = np.array([400.0, 500.0, 600.0])
    values = np.array([20.0, 50.0, 80.0])

    loaded = prepare_spectrum(wavelengths, values, "transmission").physical_values
    imported = interpolate_spectrum(
        wavelengths, values, INTERP_GRID, quantity="transmission"
    )

    np.testing.assert_allclose(imported, loaded, equal_nan=True)
