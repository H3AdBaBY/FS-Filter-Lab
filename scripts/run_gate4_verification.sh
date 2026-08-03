#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3.12}

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else "Gate 4 verification requires Python 3.12")'

TEMP_ROOT=${TMPDIR:-/tmp}
TEMP_ROOT=${TEMP_ROOT%/}
WORK_ROOT=$(mktemp -d "$TEMP_ROOT/fs-filterlab-gate4.XXXXXX")
VERIFY_CACHE_ROOT=${FS_FILTERLAB_VERIFY_CACHE:-$TEMP_ROOT/fs-filterlab-gate4-dependencies}
VERIFY_PORT=${FS_FILTERLAB_VERIFY_PORT:-18504}
LAUNCH_PID=

cleanup() {
    if [ -n "$LAUNCH_PID" ]; then
        kill "$LAUNCH_PID" 2>/dev/null || true
        wait "$LAUNCH_PID" 2>/dev/null || true
    fi
    case "$WORK_ROOT" in
        "$TEMP_ROOT"/fs-filterlab-gate4.*) rm -rf -- "$WORK_ROOT" ;;
    esac
}
trap cleanup EXIT INT TERM

mkdir -p "$VERIFY_CACHE_ROOT/pip" "$VERIFY_CACHE_ROOT/matplotlib"
"$PYTHON_BIN" -m venv "$WORK_ROOT/suite-venv"
PIP_CACHE_DIR="$VERIFY_CACHE_ROOT/pip" \
"$WORK_ROOT/suite-venv/bin/python" -m pip install \
    --disable-pip-version-check \
    --quiet \
    -r "$REPO_ROOT/requirements.txt" \
    -r "$REPO_ROOT/requirements-test.txt"

cd "$REPO_ROOT"
MPLBACKEND=Agg \
MPLCONFIGDIR="$VERIFY_CACHE_ROOT/matplotlib" \
PYTHONDONTWRITEBYTECODE=1 \
FS_FILTERLAB_CACHE_DIR="$WORK_ROOT/pytest-cache" \
FS_FILTERLAB_USER_DATA_DIR="$WORK_ROOT/pytest-user-data" \
FS_FILTERLAB_OUTPUT_DIR="$WORK_ROOT/pytest-output" \
"$WORK_ROOT/suite-venv/bin/python" -m pytest

MPLBACKEND=Agg \
MPLCONFIGDIR="$VERIFY_CACHE_ROOT/matplotlib" \
PYTHONDONTWRITEBYTECODE=1 \
FS_FILTERLAB_CACHE_DIR="$WORK_ROOT/smoke-cache" \
FS_FILTERLAB_USER_DATA_DIR="$WORK_ROOT/smoke-user-data" \
FS_FILTERLAB_OUTPUT_DIR="$WORK_ROOT/smoke-output" \
"$WORK_ROOT/suite-venv/bin/python" scripts/smoke_test_app.py

MPLBACKEND=Agg \
MPLCONFIGDIR="$VERIFY_CACHE_ROOT/matplotlib" \
PYTHONDONTWRITEBYTECODE=1 \
FS_FILTERLAB_CACHE_DIR="$WORK_ROOT/gate3-app-cache" \
FS_FILTERLAB_USER_DATA_DIR="$WORK_ROOT/gate3-user-data" \
FS_FILTERLAB_OUTPUT_DIR="$WORK_ROOT/gate3-output" \
FS_FILTERLAB_GATE3_CACHE_DIR="$WORK_ROOT/gate3-cache" \
"$WORK_ROOT/suite-venv/bin/python" scripts/gate3_vertical_workflow.py

MPLBACKEND=Agg \
MPLCONFIGDIR="$VERIFY_CACHE_ROOT/matplotlib" \
PYTHONDONTWRITEBYTECODE=1 \
FS_FILTERLAB_CACHE_DIR="$WORK_ROOT/gate4-cache" \
FS_FILTERLAB_USER_DATA_DIR="$WORK_ROOT/gate4-user-data" \
FS_FILTERLAB_OUTPUT_DIR="$WORK_ROOT/gate4-output" \
"$WORK_ROOT/suite-venv/bin/python" scripts/gate4_interactions.py

PIP_CACHE_DIR="$VERIFY_CACHE_ROOT/pip" \
"$WORK_ROOT/suite-venv/bin/python" -m pip check

# Verify a populated release archive without repository metadata. All launcher
# writes remain below WORK_ROOT, never in the developer environment.
RELEASE_ROOT="$WORK_ROOT/release"
mkdir -p "$RELEASE_ROOT"
cp -R "$REPO_ROOT/." "$RELEASE_ROOT"
rm -f "$RELEASE_ROOT/.git"
rm -rf "$RELEASE_ROOT/cache" "$RELEASE_ROOT/user_data" "$RELEASE_ROOT/output" "$RELEASE_ROOT/dist"
sh -n "$RELEASE_ROOT/install.sh" "$RELEASE_ROOT/run.sh"

PIP_CACHE_DIR="$VERIFY_CACHE_ROOT/pip" \
PYTHON_BIN="$PYTHON_BIN" \
FS_FILTERLAB_VENV_DIR="$WORK_ROOT/launcher-venv" \
sh "$RELEASE_ROOT/install.sh"

MPLCONFIGDIR="$VERIFY_CACHE_ROOT/matplotlib" \
FS_FILTERLAB_VENV_DIR="$WORK_ROOT/launcher-venv" \
sh "$RELEASE_ROOT/run.sh" --check

MPLBACKEND=Agg \
MPLCONFIGDIR="$VERIFY_CACHE_ROOT/matplotlib" \
FS_FILTERLAB_CACHE_DIR="$WORK_ROOT/launcher-cache" \
FS_FILTERLAB_USER_DATA_DIR="$WORK_ROOT/launcher-user-data" \
FS_FILTERLAB_OUTPUT_DIR="$WORK_ROOT/launcher-output" \
FS_FILTERLAB_VENV_DIR="$WORK_ROOT/launcher-venv" \
sh "$RELEASE_ROOT/run.sh" \
    --server.headless true \
    --server.address 127.0.0.1 \
    --server.port "$VERIFY_PORT" \
    >"$WORK_ROOT/launcher.log" 2>&1 &
LAUNCH_PID=$!

attempt=0
while ! curl -fsS "http://127.0.0.1:$VERIFY_PORT/_stcore/health" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
        sed -n '1,200p' "$WORK_ROOT/launcher.log" >&2
        echo "Release-archive launcher exited before becoming healthy." >&2
        exit 1
    fi
    if [ "$attempt" -ge 80 ]; then
        sed -n '1,200p' "$WORK_ROOT/launcher.log" >&2
        echo "Release-archive launcher did not become healthy within 20 seconds." >&2
        exit 1
    fi
    sleep 0.25
done
kill "$LAUNCH_PID"
wait "$LAUNCH_PID" 2>/dev/null || true
LAUNCH_PID=
echo "Release-archive launcher health smoke: passed"
echo "Gate 4 complete verification: passed"
