"""Exercise and time the approved Gate 3 Streamlit vertical workflow."""

from pathlib import Path
from statistics import median
from time import perf_counter
import os
import sys

import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest


REFERENCE_FILTER = "IR Chrome (0.0, Kolari)"
REFERENCE_CAMERA = "Generic CMOS sensor"
REFERENCE_ILLUMINANT = "AM1.5_Global_REL"
EXPECTED_EFFECTIVE_TRANSMISSION = 0.2006086128216617
EXPECTED_STOPS = 2.3175445477191383
EXPECTED_COVERAGE = 0.9997590771609786

BUDGETS = {
    "uncached_load": 2.5,
    "initial_render": 1.5,
    "selection_median": 0.75,
    "selection_max": 1.5,
    "count_median": 0.75,
    "count_max": 1.5,
    "png_generation": 3.0,
}


def _timed(operation):
    started = perf_counter()
    result = operation()
    return result, perf_counter() - started


def _assert_no_exception(app: AppTest, stage: str) -> None:
    if app.exception:
        details = "; ".join(str(item.value) for item in app.exception)
        raise AssertionError(f"{stage} rendered an exception: {details}")


def _load_all():
    from services.data import (
        load_filter_collection,
        load_illuminant_collection,
        load_quantum_efficiencies,
        load_reflector_collection,
    )

    filters = load_filter_collection()
    camera_keys, qe_data, default_key = load_quantum_efficiencies()
    illuminants, illuminant_metadata = load_illuminant_collection()
    reflectors = load_reflector_collection()
    return filters, camera_keys, qe_data, default_key, illuminants, illuminant_metadata, reflectors


def _verify_inventory(cold, warm) -> None:
    cold_filters, cold_cameras, _, _, cold_illuminants, _, cold_reflectors = cold
    warm_filters, warm_cameras, _, _, warm_illuminants, _, warm_reflectors = warm
    counts = (
        len(cold_filters.filters),
        len(cold_cameras),
        len(cold_illuminants),
        len(cold_reflectors.reflectors),
    )
    if counts != (1558, 3, 1, 4):
        raise AssertionError(f"Bundled inventory changed: {counts}")
    if cold_filters.get_display_names() != warm_filters.get_display_names():
        raise AssertionError("Filter identities differ between clean and warm caches")
    if cold_cameras != warm_cameras:
        raise AssertionError("QE identities differ between clean and warm caches")
    if list(cold_illuminants) != list(warm_illuminants):
        raise AssertionError("Illuminant identities differ between clean and warm caches")
    if [item.name for item in cold_reflectors.reflectors] != [
        item.name for item in warm_reflectors.reflectors
    ]:
        raise AssertionError("Reflector identities differ between clean and warm caches")


def _rerun(app: AppTest, stage: str) -> float:
    _, elapsed = _timed(lambda: app.run(timeout=60))
    _assert_no_exception(app, stage)
    return elapsed


def _measure_selection_reruns(app: AppTest) -> list[float]:
    timings = []
    for index in range(10):
        selection = [] if index % 2 == 0 else [REFERENCE_FILTER]
        app.multiselect[0].set_value(selection)
        timings.append(_rerun(app, f"selection rerun {index + 1}"))
    app.multiselect[0].set_value([REFERENCE_FILTER])
    _rerun(app, "restore reference selection")
    return timings


def _measure_count_reruns(app: AppTest) -> list[float]:
    timings = []
    for index in range(10):
        app.number_input[0].set_value(1 if index % 2 == 0 else 2)
        timings.append(_rerun(app, f"count rerun {index + 1}"))
    if app.number_input[0].value != 2:
        raise AssertionError("Reference filter count was not retained")
    return timings


def _verify_reference_ui(app: AppTest) -> None:
    markdown = "\n".join(str(element.value) for element in app.markdown)
    required_text = (
        "2.32 stops",
        "20.1%",
        "partial coverage: 99.98%",
        "not applied; Green = 1.000",
    )
    for text in required_text:
        if text not in markdown:
            raise AssertionError(f"Reference UI is missing {text!r}")
    if len(app.get("plotly_chart")) < 2:
        raise AssertionError("Reference workflow did not render both required charts")
    if len(app.get("download_button")) != 0:
        raise AssertionError("A report download appeared before current-state generation")


def _generate_report(app: AppTest, stage: str) -> float:
    app.button[0].click()
    return _rerun(app, stage)


def _verify_export(app: AppTest, output_root: Path) -> None:
    downloads = app.get("download_button")
    if len(downloads) != 1:
        raise AssertionError(f"Expected one download action, found {len(downloads)}")
    export = app.session_state["last_export"]
    metadata = export["metadata"]
    if metadata["filter_counts"] != {REFERENCE_FILTER: 2}:
        raise AssertionError("Export filter count differs from the interactive state")
    if metadata["camera_name"] != REFERENCE_CAMERA:
        raise AssertionError("Export QE identity differs from the interactive state")
    if metadata["illuminant_name"] != REFERENCE_ILLUMINANT:
        raise AssertionError("Export illuminant identity differs from the interactive state")
    np.testing.assert_allclose(
        metadata["effective_transmission"], EXPECTED_EFFECTIVE_TRANSMISSION,
        rtol=0, atol=1e-15,
    )
    np.testing.assert_allclose(
        metadata["effective_stops"], EXPECTED_STOPS, rtol=0, atol=1e-15
    )
    np.testing.assert_allclose(
        metadata["coverage"], EXPECTED_COVERAGE, rtol=0, atol=1e-15
    )
    if metadata["balance_applied"] or metadata["mixer_enabled"]:
        raise AssertionError("Primary export unexpectedly applied balance or mixing")
    if not export["name"].endswith("Kolari 0.0 x2.png"):
        raise AssertionError(f"Export filename does not encode stack count: {export['name']}")
    if not export["bytes"].startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("Export bytes do not have a PNG signature")

    files = list(output_root.rglob("*.png"))
    if len(files) != 1:
        raise AssertionError(f"Expected one deterministic PNG, found {len(files)}")
    with Image.open(files[0]) as image:
        if image.format != "PNG" or image.width < 500 or image.height < 1000:
            raise AssertionError("Exported artifact is not a valid full-size PNG")
        if not any(low != high for low, high in image.convert("RGB").getextrema()):
            raise AssertionError("Exported artifact is blank")


def _enforce_budget(name: str, value: float) -> None:
    if value > BUDGETS[name]:
        raise AssertionError(
            f"{name} took {value:.3f}s, exceeding {BUDGETS[name]:.3f}s"
        )


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, repository_root.as_posix())
    cache_root = Path(os.environ["FS_FILTERLAB_GATE3_CACHE_DIR"])
    output_root = Path(os.environ["FS_FILTERLAB_OUTPUT_DIR"])

    from services import data as data_service

    data_service.CACHE_DIR = cache_root
    cold, uncached_load = _timed(_load_all)
    warm, _ = _timed(_load_all)
    _verify_inventory(cold, warm)

    app = AppTest.from_file((repository_root / "app.py").as_posix())
    _, initial_render = _timed(lambda: app.run(timeout=60))
    _assert_no_exception(app, "initial render")
    if "Green-channel effective light loss" in "\n".join(
        str(item.value) for item in app.markdown
    ):
        raise AssertionError("Initial no-filter state fabricated a filter metric")

    selectboxes = {item.label: item for item in app.selectbox}
    if selectboxes["Sensor QE Profile"].value != REFERENCE_CAMERA:
        raise AssertionError("Named QE profile is not the selected default")
    if selectboxes["Scene Illuminant"].value != REFERENCE_ILLUMINANT:
        raise AssertionError("Named illuminant is not the selected default")

    selection_timings = _measure_selection_reruns(app)
    count_timings = _measure_count_reruns(app)
    _verify_reference_ui(app)

    # Warm Matplotlib and font caches, then measure deterministic replacement.
    _generate_report(app, "PNG warm-up")
    _assert_no_exception(app, "PNG warm-up")
    _, png_generation = _timed(lambda: _generate_report(app, "PNG generation"))
    _verify_export(app, output_root)

    app.number_input[0].set_value(1)
    _rerun(app, "stale-download suppression")
    if app.get("download_button"):
        raise AssertionError("State change exposed a stale report download")

    measurements = {
        "uncached_load": uncached_load,
        "initial_render": initial_render,
        "selection_median": median(selection_timings),
        "selection_max": max(selection_timings),
        "count_median": median(count_timings),
        "count_max": max(count_timings),
        "png_generation": png_generation,
    }
    for name, value in measurements.items():
        _enforce_budget(name, value)
        print(f"Gate 3 timing {name}: {value:.3f}s (budget {BUDGETS[name]:.3f}s)")
    print("Gate 3 vertical workflow: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
