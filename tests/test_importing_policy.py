from io import StringIO

import numpy as np
import pandas as pd

from models.constants import INTERP_GRID
from services.data import _process_filter_file
from services.importing import extract_spectral_columns, import_filter_from_csv


def test_import_column_extraction_preserves_row_alignment_and_unknown_values() -> None:
    frame = pd.DataFrame(
        {
            "wavelength": [400.0, 500.0, 600.0],
            "value": [20.0, np.nan, 80.0],
        }
    )

    wavelengths, values = extract_spectral_columns(frame, 1)

    np.testing.assert_array_equal(wavelengths, [400.0, 500.0, 600.0])
    np.testing.assert_allclose(values, [20.0, np.nan, 80.0], equal_nan=True)


def test_filter_import_preserves_raw_excursions_and_reports_diagnostics(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    upload = StringIO("400;-1\n500;\n600;120\n")
    metadata = {
        "manufacturer": "Fixture Lab",
        "filter_name": "Diagnostic Import",
        "filter_number": "IMP-1",
        "hex_color": "#123456",
    }

    success, message = import_filter_from_csv(upload, metadata, False, False)

    assert success
    assert "unit_interpretation" in message
    assert "physical_bounds_clipped" in message
    assert "nonfinite_values_preserved" in message
    output = next((tmp_path / "data" / "filters_data").rglob("*.tsv"))
    imported = pd.read_csv(output, sep="\t")
    indexed = imported.set_index("Wavelength")["Transmittance"]
    assert indexed.loc[400] == -0.01
    assert np.isnan(indexed.loc[500])
    assert indexed.loc[600] == 1.2


def test_import_rejects_nonfinite_wavelength_without_shifting_values(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    upload = StringIO("400;20\n;50\n600;80\n")
    metadata = {
        "manufacturer": "Fixture Lab",
        "filter_name": "Invalid Coordinates",
        "filter_number": "IMP-2",
        "hex_color": "#123456",
    }

    success, message = import_filter_from_csv(upload, metadata, False, False)

    assert not success
    assert "Wavelength samples must be finite" in message
    assert not (tmp_path / "data").exists()


def test_filter_import_extrapolation_mask_survives_loader_round_trip(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    upload = StringIO("400;20\n500;50\n600;80\n")
    metadata = {
        "manufacturer": "Fixture Lab",
        "filter_name": "Masked Import",
        "filter_number": "IMP-3",
        "hex_color": "#123456",
    }

    success, _ = import_filter_from_csv(upload, metadata, True, False)
    assert success
    output = next((tmp_path / "data" / "filters_data").rglob("*.tsv"))
    saved = pd.read_csv(output, sep="\t")
    assert saved.loc[saved["Wavelength"] == 399, "Extrapolated"].item()
    assert not saved.loc[saved["Wavelength"] == 400, "Extrapolated"].item()

    _, _, mask, filter_object = _process_filter_file(output)
    assert mask[INTERP_GRID == 399].item()
    assert not mask[INTERP_GRID == 400].item()
    np.testing.assert_array_equal(filter_object.extrapolated_mask, mask)
