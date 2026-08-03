"""Run the Streamlit application once and fail on rendered exceptions."""

from pathlib import Path
import os
import sys

from streamlit.testing.v1 import AppTest


def verify_display_policy() -> None:
    """Check black preservation and shared group exposure in the runtime stack."""
    import numpy as np

    from models.core import ReflectorCollection, ReflectorSpectrum
    from services.visualization import (
        create_single_reflectance_figure,
        prepare_rgb_for_display,
    )

    group = np.array([[[0.0, 0.5, 1.0], [0.25, 0.5, 0.75]]])
    displayed = prepare_rgb_for_display(group, auto_exposure=True)
    np.testing.assert_array_equal(displayed[0, 0], [0.0, 0.5, 1.0])
    np.testing.assert_array_equal(displayed[0, 1], [0.25, 0.5, 0.75])

    wavelengths = np.array([400.0, 500.0, 600.0])
    reflectance = np.array([0.2, 0.4, 0.6])
    mask = np.array([True, False, False])
    collection = ReflectorCollection(
        reflectors=[
            ReflectorSpectrum(
                name="Masked reflector",
                values=reflectance,
                extrapolated_mask=mask,
            )
        ],
        reflector_matrix=reflectance.reshape(1, -1),
    )
    figure = create_single_reflectance_figure(
        wavelengths, collection.reflector_matrix, collection, 0
    )
    if figure is None or len(figure.data) != 2 or figure.data[1].line.dash != "dot":
        raise AssertionError("Reflector extrapolation mask is not rendered distinctly")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, repository_root.as_posix())
    app_path = repository_root / "app.py"
    app = AppTest.from_file(app_path.as_posix())
    app.run(timeout=60)
    if app.exception:
        for exception in app.exception:
            print(exception.value)
        return 1
    verify_display_policy()
    app.multiselect[0].set_value(["IR Chrome (0.0, Kolari)"])
    app.run(timeout=60)
    if app.exception:
        for exception in app.exception:
            print(exception.value)
        return 1
    metric_text = "\n".join(element.value for element in app.markdown)
    if "partial coverage: 99.98%" not in metric_text:
        print("Partial metric coverage was not displayed with non-ambiguous precision")
        return 1
    app.number_input[0].set_value(2)
    app.run(timeout=60)
    app.button[0].click()
    app.run(timeout=60)
    if app.exception or len(app.get("download_button")) != 1:
        for exception in app.exception:
            print(exception.value)
        print("PNG export did not produce one download artifact")
        return 1
    output_root = Path(os.environ.get("FS_FILTERLAB_OUTPUT_DIR", "output"))
    exported_files = list(output_root.rglob("*.png"))
    if len(exported_files) != 1:
        print(f"Expected one exported PNG, found {len(exported_files)}")
        return 1
    from PIL import Image

    with Image.open(exported_files[0]) as exported:
        if exported.format != "PNG" or exported.width < 500 or exported.height < 1000:
            print("Exported report is not a valid full-size PNG")
            return 1
    print("Streamlit startup smoke: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
