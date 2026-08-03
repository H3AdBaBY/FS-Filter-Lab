#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else "Gate 1 requires Python 3.10 or newer")'

TEMP_ROOT=${TMPDIR:-/tmp}
TEMP_ROOT=${TEMP_ROOT%/}
VENV_DIR=$(mktemp -d "$TEMP_ROOT/fs-filterlab-gate1.XXXXXX")
TEST_CACHE_ROOT=${FS_FILTERLAB_TEST_CACHE:-$TEMP_ROOT/fs-filterlab-gate1-cache}
mkdir -p "$TEST_CACHE_ROOT/pip" "$TEST_CACHE_ROOT/matplotlib"
cleanup() {
    case "$VENV_DIR" in
        "$TEMP_ROOT"/fs-filterlab-gate1.*) rm -rf -- "$VENV_DIR" ;;
    esac
}
trap cleanup EXIT INT TERM

"$PYTHON_BIN" -m venv "$VENV_DIR/venv"
PIP_CACHE_DIR="$TEST_CACHE_ROOT/pip" \
"$VENV_DIR/venv/bin/python" -m pip install \
    --disable-pip-version-check \
    --quiet \
    -r "$REPO_ROOT/requirements-test.txt"

cd "$REPO_ROOT"
MPLBACKEND=Agg \
MPLCONFIGDIR="$TEST_CACHE_ROOT/matplotlib" \
PYTHONDONTWRITEBYTECODE=1 \
"$VENV_DIR/venv/bin/python" -m pytest
