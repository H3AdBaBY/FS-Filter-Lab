#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3.12}

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else "Gate 5 release verification requires Python 3.12")'

cd "$REPO_ROOT"
exec "$PYTHON_BIN" scripts/run_gate5_release.py
