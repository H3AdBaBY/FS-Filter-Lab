from pathlib import Path
from types import SimpleNamespace

import numpy as np

from models.core import ChannelMixerSettings
from services import data as data_service
from services.app_operations import generate_application_report
from services.data import (
    load_filter_collection,
    load_illuminant_collection,
    load_quantum_efficiencies,
    load_reflector_collection,
)
from services.workflow import build_workflow_snapshot
from views.state import handle_app_actions


REFERENCE_FILTER = "IR Chrome (0.0, Kolari)"
REFERENCE_CAMERA = "Generic CMOS sensor"
REFERENCE_ILLUMINANT = "AM1.5_Global_REL"


def _load_bundled_data(cache_dir: Path, monkeypatch):
    monkeypatch.setattr(data_service, "CACHE_DIR", cache_dir)
    filters = load_filter_collection()
    camera_keys, qe_data, default_key = load_quantum_efficiencies()
    illuminants, illuminant_metadata = load_illuminant_collection()
    reflectors = load_reflector_collection()
    return {
        "filter_collection": filters,
        "camera_keys": camera_keys,
        "qe_data": qe_data,
        "default_key": default_key,
        "illuminants": illuminants,
        "illuminant_metadata": illuminant_metadata,
        "reflector_collection": reflectors,
    }


def _reference_state(data):
    return SimpleNamespace(
        selected_filters=[REFERENCE_FILTER],
        filter_multipliers={REFERENCE_FILTER: 2},
        current_qe=data["qe_data"][REFERENCE_CAMERA],
        selected_camera=REFERENCE_CAMERA,
        illuminant=data["illuminants"][REFERENCE_ILLUMINANT],
        illuminant_name=REFERENCE_ILLUMINANT,
        apply_white_balance=False,
        channel_mixer=ChannelMixerSettings(),
        rgb_channels_visibility={"R": True, "G": True, "B": True},
        target_profile=None,
        last_export={},
    )


def test_named_workflow_freezes_approved_gate3_results(tmp_path, monkeypatch) -> None:
    data = _load_bundled_data(tmp_path / "cache", monkeypatch)
    snapshot = build_workflow_snapshot(
        _reference_state(data), data["filter_collection"]
    )

    assert snapshot.selected_filters == (REFERENCE_FILTER,)
    assert snapshot.expanded_filters == (REFERENCE_FILTER, REFERENCE_FILTER)
    assert snapshot.filter_counts == ((REFERENCE_FILTER, 2),)
    assert len(snapshot.selected_indices) == 2
    assert snapshot.selected_indices[0] == snapshot.selected_indices[1]
    assert snapshot.camera_name == REFERENCE_CAMERA
    assert snapshot.illuminant_name == REFERENCE_ILLUMINANT
    assert snapshot.diagnostics == ()
    assert snapshot.effective_result.available
    np.testing.assert_allclose(
        snapshot.effective_result.effective_transmission,
        0.2006086128216617,
        rtol=0,
        atol=1e-15,
    )
    np.testing.assert_allclose(
        snapshot.effective_result.effective_stops,
        2.3175445477191383,
        rtol=0,
        atol=1e-15,
    )
    np.testing.assert_allclose(
        snapshot.effective_result.coverage,
        0.9997590771609786,
        rtol=0,
        atol=1e-15,
    )
    np.testing.assert_allclose(
        [snapshot.balance_result.balance_divisors[channel] for channel in "RGB"],
        [0.19374828429823737, 1.0, 1.9813636440172737],
        rtol=0,
        atol=1e-14,
    )
    for channel in "RGB":
        np.testing.assert_allclose(
            snapshot.channel_responses[channel],
            snapshot.active_transmission * snapshot.current_qe[channel],
            equal_nan=True,
        )


def test_clean_and_warm_cache_inventory_and_workflow_are_identical(
    tmp_path, monkeypatch
) -> None:
    cache_dir = tmp_path / "cache"
    cold = _load_bundled_data(cache_dir, monkeypatch)
    cold_snapshot = build_workflow_snapshot(
        _reference_state(cold), cold["filter_collection"]
    )
    warm = _load_bundled_data(cache_dir, monkeypatch)
    warm_snapshot = build_workflow_snapshot(
        _reference_state(warm), warm["filter_collection"]
    )

    assert len(cold["filter_collection"].filters) == 1558
    assert len(cold["camera_keys"]) == 3
    assert len(cold["illuminants"]) == 1
    assert len(cold["reflector_collection"].reflectors) == 4
    assert cold["filter_collection"].get_display_names() == warm[
        "filter_collection"
    ].get_display_names()
    assert cold["camera_keys"] == warm["camera_keys"]
    assert list(cold["illuminants"]) == list(warm["illuminants"])
    assert [item.name for item in cold["reflector_collection"].reflectors] == [
        item.name for item in warm["reflector_collection"].reflectors
    ]
    assert cold_snapshot.identity == warm_snapshot.identity
    np.testing.assert_array_equal(
        cold_snapshot.active_transmission,
        warm_snapshot.active_transmission,
    )
    for channel in "RGB":
        np.testing.assert_array_equal(
            cold_snapshot.channel_responses[channel],
            warm_snapshot.channel_responses[channel],
        )


def test_report_artifact_carries_the_same_snapshot_state(
    tmp_path, monkeypatch
) -> None:
    from PIL import Image

    data = _load_bundled_data(tmp_path / "cache", monkeypatch)
    state = _reference_state(data)
    snapshot = build_workflow_snapshot(state, data["filter_collection"])
    monkeypatch.setenv("FS_FILTERLAB_OUTPUT_DIR", str(tmp_path / "output"))

    assert generate_application_report(
        state,
        data["filter_collection"],
        REFERENCE_CAMERA,
        snapshot,
    )
    export = state.last_export
    assert export["workflow_identity"] == snapshot.identity
    assert export["metadata"] == snapshot.report_metadata()
    assert "Kolari 0.0 x2" in export["name"]
    assert export["bytes"].startswith(b"\x89PNG\r\n\x1a\n")

    exported_files = list((tmp_path / "output").rglob("*.png"))
    assert len(exported_files) == 1
    with Image.open(exported_files[0]) as image:
        assert image.format == "PNG"
        assert image.width >= 500
        assert image.height >= 1000
        extrema = image.convert("RGB").getextrema()
        assert any(low != high for low, high in extrema)


def test_failed_report_generation_clears_stale_export(
    tmp_path, monkeypatch
) -> None:
    data = _load_bundled_data(tmp_path / "cache", monkeypatch)
    state = _reference_state(data)
    state.last_export = {"bytes": b"stale", "name": "stale.png"}
    snapshot = build_workflow_snapshot(state, data["filter_collection"])
    monkeypatch.setattr(
        "services.app_operations.generate_report_png_v2", lambda **kwargs: {}
    )

    assert not generate_application_report(
        state,
        data["filter_collection"],
        REFERENCE_CAMERA,
        snapshot,
    )
    assert state.last_export == {}


def test_failed_report_action_is_actionable_and_clears_stale_export(
    monkeypatch,
) -> None:
    state = SimpleNamespace(last_export={"bytes": b"stale"})
    messages = []
    monkeypatch.setattr(
        "views.state.generate_application_report", lambda **kwargs: False
    )
    monkeypatch.setattr("views.state.handle_error", messages.append)

    handle_app_actions(
        {"generate_report": REFERENCE_CAMERA},
        state,
        {"filter_collection": object()},
        workflow_snapshot=object(),
    )

    assert state.last_export == {}
    assert messages == ["Failed to generate report. Check console for details."]
