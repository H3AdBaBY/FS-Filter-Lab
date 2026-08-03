from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

from models.constants import INTERP_GRID
from services import data as data_service
from services.data import (
    load_filter_collection,
    load_illuminant_collection,
    load_quantum_efficiencies,
    load_reflector_collection,
)
from services.importing import (
    import_filter_from_csv,
    import_illuminant_from_csv,
    import_qe_from_csv,
    import_reflectance_absorption_from_csv,
)
from views.forms import (
    filter_by_trans_at_wavelength,
    sort_by_text_field,
    sort_by_trans_at_wavelength,
)


def _upload(text: str, name: str) -> StringIO:
    upload = StringIO(text)
    upload.name = name
    return upload


def _configure_import_root(tmp_path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    user_root = tmp_path / "user_data"
    monkeypatch.setenv("FS_FILTERLAB_USER_DATA_DIR", str(user_root))
    monkeypatch.setattr(data_service, "CACHE_DIR", tmp_path / "cache")
    return user_root


def test_search_excludes_unknown_samples_and_uses_stable_ties() -> None:
    frame = pd.DataFrame(
        {
            "Filter Number": ["2", "1", "1"],
            "Filter Name": ["Beta", "alpha", "Alpha"],
            "Manufacturer": ["Lab", "Zed", "Able"],
            "Hex Color": ["#0000ff", "#ff0000", "#00ff00"],
        },
        index=[0, 1, 2],
    )
    matrix = np.full((3, len(INTERP_GRID)), np.nan)
    sample = int(np.where(INTERP_GRID == 550)[0][0])
    matrix[:, sample] = [0.5, np.nan, 0.5]

    filtered, values, unknown = filter_by_trans_at_wavelength(
        frame, INTERP_GRID, matrix, 550, 0.5, 0.5
    )
    assert list(filtered.index) == [0, 2]
    np.testing.assert_array_equal(values, [0.5, 0.5])
    assert unknown == 1
    assert list(sort_by_trans_at_wavelength(filtered, values).index) == [2, 0]
    assert list(sort_by_text_field(frame, "Filter Name").index) == [2, 1, 0]


def test_all_four_importers_publish_to_user_data_and_reload(
    tmp_path, monkeypatch
) -> None:
    user_root = _configure_import_root(tmp_path, monkeypatch)

    # Cache an empty collection first; the successful import must invalidate it.
    assert not load_filter_collection().filters
    filter_meta = {
        "manufacturer": "Fixture Lab",
        "filter_name": "Gate Four Filter",
        "filter_number": "G4-F",
        "hex_color": "#123456",
    }
    success, _ = import_filter_from_csv(
        _upload("Wavelength,Transmittance\n400,20\n500,50\n600,80\n", "filter.csv"),
        filter_meta,
        False,
        False,
        "percent",
    )
    assert success

    success, illuminant_message = import_illuminant_from_csv(
        _upload("400;1\n500;2\n600;1\n", "illuminant.csv"),
        "Gate Four Illuminant",
    )
    assert success
    assert "peak normalized to 100" in illuminant_message

    success, _ = import_qe_from_csv(
        _upload(
            "400;10;20;30\n500;20;30;40\n600;30;40;50\n",
            "qe.csv",
        ),
        "Fixture",
        "Gate Four Camera",
        "percent",
    )
    assert success

    reflector_meta = {
        "name": "Gate Four Surface",
        "data_type": "Reflectance",
        "category": "Other",
        "description": "Fixture surface",
    }
    success, _ = import_reflectance_absorption_from_csv(
        _upload("400;20\n500;40\n600;60\n", "surface.csv"),
        reflector_meta,
        False,
        False,
        "percent",
    )
    assert success

    filters = load_filter_collection()
    cameras, qe_data, _ = load_quantum_efficiencies()
    illuminants, metadata = load_illuminant_collection()
    reflectors = load_reflector_collection()
    assert filters.get_display_names() == [
        "Gate Four Filter (G4-F, Fixture Lab)"
    ]
    assert cameras == ["Fixture Gate Four Camera"]
    assert set(qe_data[cameras[0]]) == {"R", "G", "B"}
    assert list(illuminants) == ["Gate Four Illuminant"]
    assert metadata["Gate Four Illuminant"] == "Gate Four Illuminant"
    assert [item.name for item in reflectors.reflectors] == ["Gate Four Surface"]
    assert len(list(user_root.rglob("*.tsv"))) == 4
    assert not (tmp_path / "data").exists()


def test_import_collision_never_overwrites_existing_user_data(
    tmp_path, monkeypatch
) -> None:
    user_root = _configure_import_root(tmp_path, monkeypatch)
    meta = {
        "manufacturer": "Fixture Lab",
        "filter_name": "Collision",
        "filter_number": "G4-C",
        "hex_color": "#123456",
    }
    first = _upload("400;20\n500;50\n600;80\n", "first.csv")
    assert import_filter_from_csv(first, meta, False, False, "percent")[0]
    output = next(user_root.rglob("*.tsv"))
    original = output.read_bytes()

    second = _upload("400;10\n500;10\n600;10\n", "second.csv")
    success, message = import_filter_from_csv(
        second, meta, False, False, "percent"
    )
    assert not success
    assert "never overwrite" in message
    assert output.read_bytes() == original
    assert len(list(user_root.rglob("*.tsv"))) == 1


def test_import_requires_units_rejects_absorption_and_leaves_no_partial_file(
    tmp_path, monkeypatch
) -> None:
    user_root = _configure_import_root(tmp_path, monkeypatch)
    filter_meta = {
        "manufacturer": "Fixture Lab",
        "filter_name": "Needs Unit",
        "filter_number": "G4-U",
        "hex_color": "#123456",
    }
    success, message = import_filter_from_csv(
        _upload("400;0.2\n500;0.5\n600;0.8\n", "unit.csv"),
        filter_meta,
        False,
        False,
    )
    assert not success
    assert "Explicit transmission unit is required" in message

    absorption = {
        "name": "Not Reflectance",
        "data_type": "Absorption",
        "category": "Other",
        "description": "",
    }
    success, message = import_reflectance_absorption_from_csv(
        _upload("400;0.2\n500;0.5\n600;0.8\n", "absorption.csv"),
        absorption,
        False,
        False,
        "fraction",
    )
    assert not success
    assert "no conversion measurement model" in message
    assert not user_root.exists()
