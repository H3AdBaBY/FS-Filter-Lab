"""Exercise and time the approved Gate 4 Streamlit parity workflow."""

from io import StringIO
import os
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

from PIL import Image
from streamlit.testing.v1 import AppTest


REFERENCE_FILTER = "IR Chrome (0.0, Kolari)"
REFERENCE_CAMERA = "Generic CMOS sensor"
REFERENCE_ILLUMINANT = "AM1.5_Global_REL"

BUDGETS = {
    "advanced_search_median": 0.25,
    "advanced_search_max": 0.75,
    "balance_rerun_median": 0.25,
    "balance_rerun_max": 0.75,
    "mixer_rerun_median": 0.25,
    "mixer_rerun_max": 0.75,
    "surface_rerun_median": 0.25,
    "surface_rerun_max": 0.75,
    "import_backend": 1.0,
    "warm_initial_render": 3.0,
}


def _timed(operation):
    started = perf_counter()
    result = operation()
    return result, perf_counter() - started


def _assert_no_exception(app: AppTest, stage: str) -> None:
    if app.exception:
        details = "; ".join(str(item.value) for item in app.exception)
        raise AssertionError(f"{stage} rendered an exception: {details}")


def _rerun(app: AppTest, stage: str) -> float:
    _, elapsed = _timed(lambda: app.run(timeout=60))
    _assert_no_exception(app, stage)
    return elapsed


def _element(elements, label: str):
    matches = [item for item in elements if item.label == label]
    if len(matches) != 1:
        raise AssertionError(f"Expected one {label!r} control, found {len(matches)}")
    return matches[0]


def _button(app: AppTest, label: str):
    return _element(app.button, label)


def _checkbox(app: AppTest, label: str):
    return _element(app.checkbox, label)


def _selectbox(app: AppTest, label: str):
    return _element(app.selectbox, label)


def _multiselect(app: AppTest, label: str):
    return _element(app.multiselect, label)


def _slider(app: AppTest, label: str):
    return _element(app.slider, label)


def _toggle(app: AppTest, label: str):
    return _element(app.toggle, label)


def _load_all():
    from services.data import (
        load_filter_collection,
        load_illuminant_collection,
        load_quantum_efficiencies,
        load_reflector_collection,
    )

    filters = load_filter_collection()
    cameras, qe_data, default_camera = load_quantum_efficiencies()
    illuminants, illuminant_metadata = load_illuminant_collection()
    reflectors = load_reflector_collection()
    return (
        filters,
        cameras,
        qe_data,
        default_camera,
        illuminants,
        illuminant_metadata,
        reflectors,
    )


def _measure_search(filter_collection) -> list[float]:
    from models.constants import INTERP_GRID
    from views.forms import (
        filter_by_trans_at_wavelength,
        sort_by_trans_at_wavelength,
    )

    timings = []
    for _ in range(10):
        started = perf_counter()
        filtered, values, _ = filter_by_trans_at_wavelength(
            filter_collection.df,
            INTERP_GRID,
            filter_collection.filter_matrix,
            550,
            0.0,
            1.0,
        )
        sorted_results = sort_by_trans_at_wavelength(filtered, values)
        if len(sorted_results) > len(filter_collection.filters):
            raise AssertionError("Advanced search returned an impossible count")
        timings.append(perf_counter() - started)
    return timings


def _verify_importer_controls(app: AppTest) -> None:
    _button(app, "📊 WebPlotDigitizer .csv importers").click()
    _rerun(app, "open four importers")
    labels = [item.label for item in app.get("file_uploader")]
    expected = [
        "Upload CSV (Wavelength nm, Transmittance)",
        "Upload CSV (Wavelength nm, Relative Power)",
        "Upload CSV (Wavelength nm, R, G, B)",
        "Upload CSV (Wavelength nm, Reflectance)",
    ]
    if labels != expected:
        raise AssertionError(f"Importer labels changed: {labels}")
    _button(app, "✖️ Close Importers").click()
    _rerun(app, "close four importers")


def _open_kolari_search(app: AppTest, stage: str) -> None:
    _checkbox(app, "Show Advanced Search").set_value(True)
    _rerun(app, f"open {stage} advanced search")
    _multiselect(app, "Manufacturer").set_value(["Kolari"])
    _button(app, "🔄 Apply").click()
    _rerun(app, f"apply {stage} Kolari search")


def _verify_search_merge_and_cancel(repository_root: Path) -> None:
    # AppTest retains removed dynamic-widget nodes after a terminal st.rerun, so
    # Done and Cancel are intentionally exercised as separate terminal sessions.
    cancel_app = AppTest.from_file((repository_root / "app.py").as_posix())
    cancel_app.run(timeout=60)
    _assert_no_exception(cancel_app, "cancel-search initial render")
    _open_kolari_search(cancel_app, "cancel")
    other = "Iridium +30nm (Iridium +30nm, Kolari)"
    _toggle(cancel_app, f"Show details for {other}").set_value(True)
    _rerun(cancel_app, "open cancel candidate")
    _checkbox(cancel_app, f"Select {other}").set_value(True)
    _button(cancel_app, "✖ Cancel").click()
    _rerun(cancel_app, "cancel advanced-search result")
    if _multiselect(cancel_app, "Select filters to plot").value:
        raise AssertionError("Cancel changed the primary filter selection")

    done_app = AppTest.from_file((repository_root / "app.py").as_posix())
    done_app.run(timeout=60)
    _assert_no_exception(done_app, "Done-search initial render")
    _open_kolari_search(done_app, "Done")
    _toggle(done_app, f"Show details for {REFERENCE_FILTER}").set_value(True)
    _rerun(done_app, "open reference search result")
    _checkbox(done_app, f"Select {REFERENCE_FILTER}").set_value(True)
    _button(done_app, "✅ Done").click()
    _rerun(done_app, "merge advanced-search result")
    if _multiselect(done_app, "Select filters to plot").value != [REFERENCE_FILTER]:
        raise AssertionError("Done did not merge the checked search result")
    if _checkbox(done_app, "Show Advanced Search").value:
        raise AssertionError("Advanced search did not close after Done")


def _measure_checkbox_reruns(
    app: AppTest, label: str, prefix: str
) -> list[float]:
    timings = []
    for index in range(10):
        _checkbox(app, label).set_value(index % 2 == 0)
        timings.append(_rerun(app, f"{prefix} rerun {index + 1}"))
    return timings


def _measure_mixer_reruns(app: AppTest) -> list[float]:
    timings = []
    for index in range(10):
        _slider(app, "Blue→Red").set_value(1.0 if index % 2 == 0 else 0.75)
        timings.append(_rerun(app, f"mixer rerun {index + 1}"))
    return timings


def _measure_surface_reruns(app: AppTest) -> list[float]:
    timings = []
    for index in range(10):
        _selectbox(app, "Surface Reflectance Spectrum").set_value(
            0 if index % 2 == 0 else "None"
        )
        timings.append(_rerun(app, f"surface rerun {index + 1}"))
    return timings


def _configure_processing_matrix(app: AppTest):
    _checkbox(app, "Apply Sensor-Response Balance").set_value(True)
    _rerun(app, "enable sensor-response balance")
    _checkbox(app, "Show Channel Mixer").set_value(True)
    _rerun(app, "enable identity mixer")
    _button(app, "Reset").click()
    _rerun(app, "reset enabled mixer to identity")
    identity_text = "\n".join(str(item.value) for item in app.markdown)
    if "Channel Mixer: Identity (no mixing)" not in identity_text:
        raise AssertionError("Enabled identity mixer was not labeled")

    # R/B swap plus finite negative and above-unity terms; analytical clipping
    # behavior is asserted independently in the deterministic unit suite.
    for label, value in (
        ("Red→Red", 0.0),
        ("Blue→Red", 1.0),
        ("Red→Blue", 1.0),
        ("Blue→Blue", 0.0),
        ("Green→Red", -0.25),
        ("Green→Blue", 1.25),
    ):
        _slider(app, label).set_value(value)
        _rerun(app, f"set {label}")

    _checkbox(app, "G Channel").set_value(False)
    _checkbox(app, "B Channel").set_value(False)
    _rerun(app, "hide plotted green and blue channels")


def _verify_previews_and_export(app: AppTest, output_root: Path) -> None:
    _selectbox(app, "Surface Reflectance Spectrum").set_value(0)
    _rerun(app, "final shared-exposure surface")
    captions = [str(item.value) for item in app.caption]
    if len(app.get("image")) != 2:
        raise AssertionError("Vegetation and selected-surface previews were not rendered")
    if not any("not calibrated color" in value for value in captions):
        raise AssertionError("Preview calibration limitation is missing")
    if not any("Shared comparison exposure" in value for value in captions):
        raise AssertionError("Selected surface did not use shared exposure")

    _button(app, "📄 Generate Report (PNG)").click()
    _rerun(app, "Gate 4 PNG generation")
    if len(app.get("download_button")) != 1:
        raise AssertionError("Current Gate 4 state did not expose one report download")
    export = app.session_state["last_export"]
    metadata = export["metadata"]
    if not metadata["balance_applied"] or not metadata["mixer_enabled"]:
        raise AssertionError("Report metadata omitted balance or mixer state")
    if metadata["mixer_identity"]:
        raise AssertionError("Custom mixer was mislabeled as identity")
    visibility = dict(metadata["workflow_identity"][5])
    if visibility != {"R": True, "G": False, "B": False}:
        raise AssertionError(f"Report visibility differs from UI: {visibility}")
    if not export["bytes"].startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("Gate 4 report is not a PNG")
    files = list(output_root.rglob("*.png"))
    if len(files) != 1:
        raise AssertionError(f"Expected one Gate 4 PNG, found {len(files)}")
    with Image.open(files[0]) as image:
        if image.format != "PNG" or image.width < 500 or image.height < 1000:
            raise AssertionError("Gate 4 PNG is not a valid full-size report")
        if not any(low != high for low, high in image.convert("RGB").getextrema()):
            raise AssertionError("Gate 4 PNG is blank")


def _measure_import_backend(user_root: Path) -> float:
    from services.importing import import_filter_from_csv

    rows = ["Wavelength,Transmittance"]
    rows.extend(f"{wavelength},50" for wavelength in range(300, 1101))
    upload = StringIO("\n".join(rows))
    upload.name = "gate4-performance.csv"
    metadata = {
        "manufacturer": "Gate Four Fixture",
        "filter_name": "Normal 801 Sample",
        "filter_number": "G4-PERF",
        "hex_color": "#666666",
    }
    (success, message), elapsed = _timed(
        lambda: import_filter_from_csv(
            upload, metadata, False, False, "percent"
        )
    )
    if not success:
        raise AssertionError(f"Normal importer failed: {message}")
    files = list(user_root.rglob("*.tsv"))
    if len(files) != 1:
        raise AssertionError(f"Importer published {len(files)} files instead of one")
    return elapsed


def _enforce(name: str, value: float) -> None:
    budget = BUDGETS[name]
    if value > budget:
        raise AssertionError(f"{name} took {value:.3f}s, exceeding {budget:.3f}s")
    print(f"Gate 4 timing {name}: {value:.3f}s (budget {budget:.3f}s)")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, repository_root.as_posix())
    output_root = Path(os.environ["FS_FILTERLAB_OUTPUT_DIR"])
    user_root = Path(os.environ["FS_FILTERLAB_USER_DATA_DIR"])

    loaded = _load_all()  # Populate the temporary cache before warm render.
    filters, cameras, _, default_camera, illuminants, _, reflectors = loaded
    inventory = (len(filters.filters), len(cameras), len(illuminants), len(reflectors.reflectors))
    if inventory != (1558, 3, 1, 4):
        raise AssertionError(f"Bundled inventory changed: {inventory}")
    if default_camera != REFERENCE_CAMERA or REFERENCE_ILLUMINANT not in illuminants:
        raise AssertionError("Named Gate 4 dependencies changed")

    search_timings = _measure_search(filters)
    app = AppTest.from_file((repository_root / "app.py").as_posix())
    _, warm_initial_render = _timed(lambda: app.run(timeout=60))
    _assert_no_exception(app, "warm initial render")
    if app.error:
        raise AssertionError(f"Initial state rendered errors: {[x.value for x in app.error]}")
    if "Green-channel effective light loss" in "\n".join(
        str(item.value) for item in app.markdown
    ):
        raise AssertionError("No-filter state fabricated a filter metric")

    _verify_importer_controls(app)
    _verify_search_merge_and_cancel(repository_root)
    _multiselect(app, "Select filters to plot").set_value([REFERENCE_FILTER])
    _rerun(app, "select reference filter after search terminals")

    _selectbox(app, "Sensor QE Profile").set_value("None")
    _rerun(app, "missing QE state")
    if not any("Select a Sensor QE Profile" in str(item.value) for item in app.info):
        raise AssertionError("Missing QE did not render its actionable state")
    _selectbox(app, "Sensor QE Profile").set_value(REFERENCE_CAMERA)
    _rerun(app, "restore named QE")

    balance_timings = _measure_checkbox_reruns(
        app, "Apply Sensor-Response Balance", "balance"
    )
    _checkbox(app, "Apply Sensor-Response Balance").set_value(True)
    _rerun(app, "retain balance enabled")
    _checkbox(app, "Show Channel Mixer").set_value(True)
    _rerun(app, "open mixer for timing")
    mixer_timings = _measure_mixer_reruns(app)
    surface_timings = _measure_surface_reruns(app)

    _configure_processing_matrix(app)
    _verify_previews_and_export(app, output_root)
    import_backend = _measure_import_backend(user_root)

    measurements = {
        "advanced_search_median": median(search_timings),
        "advanced_search_max": max(search_timings),
        "balance_rerun_median": median(balance_timings),
        "balance_rerun_max": max(balance_timings),
        "mixer_rerun_median": median(mixer_timings),
        "mixer_rerun_max": max(mixer_timings),
        "surface_rerun_median": median(surface_timings),
        "surface_rerun_max": max(surface_timings),
        "import_backend": import_backend,
        "warm_initial_render": warm_initial_render,
    }
    for name, value in measurements.items():
        _enforce(name, value)
    print("Gate 4 search/import/processing/state interactions: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
