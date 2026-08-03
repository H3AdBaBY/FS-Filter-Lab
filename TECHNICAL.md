# FS FilterLab technical overview

## Architecture boundary

FS FilterLab is a local Python 3.12 and Streamlit application. It has no hosting,
accounts, database, telemetry, RAW pipeline, or dependency on another product.
Gate 4 preserves the existing production architecture and scientific formulas.

```text
models/      immutable value objects and constants
services/    loading, policy, calculations, workflow snapshots, reports
views/       Streamlit controls and presentation
data/        bundled read-only TSV corpus
user_data/   imported TSV data, git-ignored
cache/       derived collection caches
tests/       deterministic synthetic and corpus tests
```

## Value domains

- **Raw values** are parsed numeric values and source metadata before a unit or
  normalization policy is applied.
- **Physical values** use explicit conventions: filter transmission and
  reflectance are fractions; QE is internally compatible with the existing
  percent convention; illuminants are non-negative relative power, explicitly
  peak-normalized to 100 on import.
- **Analytical values** are linear arrays on `INTERP_GRID`, 300–1100 nm in 1 nm
  steps. Unknown samples remain `NaN` unless an approved, visibly masked filter
  or reflectance extrapolation was explicitly selected. Mixer output is not
  clipped.
- **Display values** are chart percentages, labels, and preview pixels. Display
  conversion may normalize and clamp pixels but cannot mutate analytical state.

Tests capture approved current behavior and policy; they do not claim
undocumented scientific correctness.

## Data ownership and loading

`services/data_locations.py` resolves the bundled `data/` root and the user
root. `FS_FILTERLAB_USER_DATA_DIR` overrides the default `user_data/` location;
`FS_FILTERLAB_CACHE_DIR` relocates generated caches.
Loaders combine the two sources, retain provenance, report source counts, and
skip a user dataset whose stable identity duplicates an already loaded bundled
dataset. Cache metadata includes both source roots and invalidates when source
state changes.

Importers fully parse and validate before writing. They publish a temporary
same-directory file atomically only if the destination remains absent, reject
filename and identity collisions, then invalidate only the affected collection
cache. Bundled data is never an import target.

## Workflow snapshot and processing

`services/workflow.py::WorkflowSnapshot` is the single calculation-state source
for interactive plots, reflector previews, metrics, report metadata, and PNG
generation. Its stable identity prevents a stale report download after state
changes.

The approved processing path is:

```text
transmission and QE with illuminant weighting
  -> linear R/G/B sensor response
  -> optional sensor-response balance multiplier
  -> optional finite 3x3 channel mixer
  -> presentation-only channel visibility and display transform
```

Visibility filters plotted traces only. The snapshot retains all analytical
channels. Reflector previews consume the same transmission, illuminant, QE,
balance, and mixer state as the sensor chart. Preview display is illustrative
sensor response, not calibrated color.

## Application states

No filter selection is valid and does not fabricate a metric. Missing QE or
illuminant hides only dependent analysis. Missing reflector data does not block
filter analysis. Partial coverage is labeled. Numerical zero, invalid overlap,
and missing data have distinct messages. A failed report clears the prior
artifact; import publication does not leave a partial file.

## Verification

The complete command is:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate5_release.sh
```

It includes the complete Gate 4 command, then creates and verifies deterministic
populated release archives. Gate 4 itself runs:

- all deterministic `pytest` tests and the exact 1,566-file bundled audit;
- prior Streamlit and PNG smoke/vertical workflows;
- Gate 4 search, importer, processing, state, and performance interactions;
- clean-install and populated-release launcher checks;
- `pip check`.

Gate 5 additionally compares two builds of both archive forms, verifies every
manifested file/hash/mode, installs and exercises each extracted form without
Git metadata, denies non-loopback runtime sockets while checking localhost
health, and writes final candidates under ignored `dist/` only after success.

Manual browser evidence covers keyboard operation, accessible structure, and
1280 px, 768 px, and 390 px layouts. The implementation record is
`docs/Gate4-Implementation.md`.

Release dependency versions and retained license evidence are recorded in
`dependency-licenses.json` and `THIRD_PARTY_NOTICES.md`. Streamlit usage
statistics are disabled by `.streamlit/config.toml`; dependency installation
may contact the configured package index, while normal application use is
local. The authoritative release boundary is `docs/Known-Limitations.md`.
