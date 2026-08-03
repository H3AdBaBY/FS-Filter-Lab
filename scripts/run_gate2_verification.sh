#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else "Gate 2 verification requires Python 3.12")'

TEMP_ROOT=${TMPDIR:-/tmp}
TEMP_ROOT=${TEMP_ROOT%/}
VENV_DIR=$(mktemp -d "$TEMP_ROOT/fs-filterlab-gate2.XXXXXX")
VERIFY_CACHE_ROOT=${FS_FILTERLAB_VERIFY_CACHE:-$TEMP_ROOT/fs-filterlab-gate2-cache}
mkdir -p "$VERIFY_CACHE_ROOT/pip" "$VERIFY_CACHE_ROOT/matplotlib"
cleanup() {
    case "$VENV_DIR" in
        "$TEMP_ROOT"/fs-filterlab-gate2.*) rm -rf -- "$VENV_DIR" ;;
    esac
}
trap cleanup EXIT INT TERM

"$PYTHON_BIN" -m venv "$VENV_DIR/venv"
PIP_CACHE_DIR="$VERIFY_CACHE_ROOT/pip" \
"$VENV_DIR/venv/bin/python" -m pip install \
    --disable-pip-version-check \
    --quiet \
    -r "$REPO_ROOT/requirements.txt" \
    -r "$REPO_ROOT/requirements-test.txt"

cd "$REPO_ROOT"
MPLBACKEND=Agg \
MPLCONFIGDIR="$VERIFY_CACHE_ROOT/matplotlib" \
PYTHONDONTWRITEBYTECODE=1 \
"$VENV_DIR/venv/bin/python" -m pytest

MPLBACKEND=Agg \
MPLCONFIGDIR="$VERIFY_CACHE_ROOT/matplotlib" \
PYTHONDONTWRITEBYTECODE=1 \
FS_FILTERLAB_OUTPUT_DIR="$VENV_DIR/output" \
"$VENV_DIR/venv/bin/python" scripts/smoke_test_app.py

"$VENV_DIR/venv/bin/python" -m pip check
