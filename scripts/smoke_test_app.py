"""Run the Streamlit application once and fail on rendered exceptions."""

from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest


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
    print("Streamlit startup smoke: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
