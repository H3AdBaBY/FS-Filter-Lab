#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3.12}
VENV_DIR=${FS_FILTERLAB_VENV_DIR:-$REPO_ROOT/.venv}

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else "FS FilterLab requires Python 3.12")'

cd "$REPO_ROOT"
if [ ! -d data/filters_data ]; then
    if command -v git >/dev/null 2>&1 && [ -f .gitmodules ]; then
        echo "Initializing bundled spectral data..."
        git submodule update --init --recursive
    fi
fi
if [ ! -d data/filters_data ]; then
    echo "Bundled data is missing. Restore data/ or initialize the data submodule." >&2
    exit 1
fi

echo "Creating Python 3.12 environment at $VENV_DIR..."
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --disable-pip-version-check --upgrade pip
"$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -r requirements.txt

echo "Installation complete. Launch with ./run.sh"
