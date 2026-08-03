#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR=${FS_FILTERLAB_VENV_DIR:-$REPO_ROOT/.venv}

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Python environment not found at $VENV_DIR. Run ./install.sh first." >&2
    exit 1
fi
if [ ! -d "$REPO_ROOT/data/filters_data" ]; then
    echo "Bundled filter data is missing. Restore data/ before launching." >&2
    exit 1
fi

"$VENV_DIR/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else "FS FilterLab requires Python 3.12")'
"$VENV_DIR/bin/python" -c 'import streamlit, numpy, pandas, plotly, matplotlib'

if [ "${1:-}" = "--check" ]; then
    echo "FS FilterLab launcher check: passed"
    exit 0
fi

cd "$REPO_ROOT"
exec "$VENV_DIR/bin/python" -m streamlit run app.py "$@"
