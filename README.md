# FS FilterLab

FS FilterLab is a local Streamlit application for comparing optical filters,
filter stacks, camera quantum-efficiency (QE) curves, illuminants, and surface
reflectance spectra. Reflector patches are illustrative sensor responses, not
calibrated color predictions.

## Features

- Combine filters, including repeated filters, on the 300–1100 nm analysis grid.
- Inspect transmission, effective light loss, RGB sensor response, optional
  sensor-response balance, and an optional 3×3 channel mixer.
- Search filters by manufacturer, name/number, color, or transmission at a
  selected wavelength.
- Import filter, QE, illuminant, and reflectance CSV data into separate local
  user storage without modifying bundled datasets.
- Export a PNG report derived from the same workflow snapshot as the visible
  analysis.

## Install and run

Requirements: Python 3.12 and `pip`. Git is needed for a source checkout whose
data submodule has not been initialized; it is not needed for a release archive
that already contains `data/`.

On Linux or macOS:

```bash
./install.sh
./run.sh
```

On Windows:

```bat
install.bat
start.bat
```

The installer creates `.venv`, installs the pinned Python 3.12 dependency set,
and exits. The run command checks the environment and bundled data before
starting Streamlit. Open <http://localhost:8501> if a browser does not open.

Dependency installation requires package access unless the dependencies are
already cached. After installation, normal application use is local and does
not require a hosted service, account, database, telemetry, or network access.

## Basic workflow

1. Select one or more filters in the sidebar and set any repeated stack counts.
2. Choose a sensor QE profile and scene illuminant under **Extras**.
3. Inspect the transmission and sensor-response charts and effective-stop
   metric.
4. Optionally apply sensor-response balance, enable the channel mixer, select a
   reflector, or hide plotted RGB traces.
5. Generate and download the PNG report after the current state is final.

The processing order is:

`linear sensor response -> optional balance -> optional 3x3 mixer -> display`

RGB visibility changes plotted traces only. It does not change analytical
arrays, balance, mixing, metrics, or reflector-preview calculations.

## CSV imports and data ownership

Open **Settings -> WebPlotDigitizer .csv importers**. Files may use commas or
semicolons and may include one header row.

- Filter: `wavelength_nm, transmission`; choose `fraction` or `percent` and
  choose lower and upper constant extrapolation separately. Both are off by
  default.
- Illuminant: `wavelength_nm, relative_power`; values must be non-negative and
  are explicitly peak-normalized to 100.
- Camera QE: `wavelength_nm, R, G, B`; choose `fraction` or `percent`.
- Reflectance: `wavelength_nm, reflectance`; choose `fraction` or `percent` and
  choose extrapolation separately. Absorption is not converted to reflectance.

Validated imports are atomically published under the git-ignored `user_data/`
tree. Set `FS_FILTERLAB_USER_DATA_DIR` to use another local root and
`FS_FILTERLAB_CACHE_DIR` to relocate generated caches. Bundled
`data/` remains unchanged. Filename and stable display-identity collisions are
rejected rather than overwritten.

## Project structure

```text
app.py             Streamlit entry point
models/            data models and constants
services/          loading, policy, calculations, workflow, and reports
views/             Streamlit controls and presentation
data/              bundled read-only spectral data
user_data/         local imported spectral data (git-ignored)
cache/             generated collection caches
tests/             deterministic synthetic and bundled-data verification
scripts/           complete gate verification commands
```

## Verification

Run the complete Gate 4 suite from a clean Python 3.12 environment:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate4_verification.sh
```

The command creates temporary environments, cache, output, and user-data roots;
runs the scientific, dataset, search/import, processing, state, Streamlit, PNG,
performance, and launcher checks; runs `pip check`; and removes temporary state.
It reconciles all 1,566 bundled TSV files without changing them.

See [USAGE.md](USAGE.md), [TECHNICAL.md](TECHNICAL.md), and
[docs/Gate4-Implementation.md](docs/Gate4-Implementation.md) for details.

## License

MIT License. See [LICENSE](LICENSE).
