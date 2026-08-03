# FS FilterLab usage guide

## Start the application

Install once with `./install.sh` on Linux/macOS or `install.bat` on Windows.
Launch later with `./run.sh` or `start.bat`. The app is available at
<http://localhost:8501> by default.

## Named filter workflow

1. In **Filter Plotter**, choose filters under **Select filters to plot**.
2. Open **Set Filter Stack Counts** to repeat a filter from one to five times.
   A stack multiplies the selected transmissions.
3. Open **Extras** and select a **Sensor QE Profile** and **Scene Illuminant**.
   Filter transmission remains usable if either is unavailable, but dependent
   metrics, sensor response, and previews remain hidden with an explanation.
4. Use **Settings** to choose logarithmic stop view and plotted R, G, and B
   traces. Hiding a trace does not change the scientific calculation.
5. Toggle **Apply Sensor-Response Balance** above the sensor chart if wanted.
6. Enable **Show Channel Mixer** to edit the 3×3 linear mixer. Reset restores
   identity coefficients while leaving the mixer enabled.
7. Generate the PNG report only after the current controls are final. A state
   change suppresses a stale download.

The calculation order is linear sensor response, optional balance, optional
matrix mixing, then display conversion. Analytical negative or above-unity
mixer output is retained; only display pixels clamp at the display boundary.

## Advanced search

Enable **Show Advanced Search** in the sidebar.

- Manufacturer values are exact metadata values.
- Transmission bounds are inclusive percentages at an integer wavelength from
  300 through 1100 nm.
- Filters whose transmission is unknown at that wavelength are excluded from a
  numeric range and reported separately.
- Text, transmission, and rainbow sorts use deterministic tie-breakers.
- Open a result's details to select it. **Done** appends checked results to the
  primary selection without duplicates; **Cancel** leaves it unchanged.

## CSV import

Open **Settings**, then **WebPlotDigitizer .csv importers**. CSV means a numeric
comma- or semicolon-separated file with an optional single header row.
Wavelengths are nanometres.

### Filter

Columns: `wavelength_nm, transmission`. Choose whether transmission is a
`fraction` (0–1) or `percent` (0–100). Lower and upper constant extrapolation
are independent and off by default. Extrapolated samples remain masked and are
shown distinctly.

### Illuminant

Columns: `wavelength_nm, relative_power`. Values must be non-negative. The
importer explicitly peak-normalizes the serialized curve to 100. No physical
radiometric unit is inferred.

### Camera QE

Columns: `wavelength_nm, R, G, B`. Choose `fraction` or `percent`. All three
aligned channels are required. Values outside measured support remain unknown.

### Reflectance

Columns: `wavelength_nm, reflectance`. Choose `fraction` or `percent` and the
two optional extrapolation directions. Absorption input is rejected because no
approved measurement model converts it to reflectance.

The importer reports normalization, clipping, sorting, extrapolation, and
unknown-value diagnostics. Successful imports are atomically stored beneath
`user_data/`, appear after one rerun, and never overwrite bundled `data/` or an
existing identity. Use `FS_FILTERLAB_USER_DATA_DIR` to choose another local
user-data root.

## Reflector previews

The four named leaf surfaces use a fixed 2×2 order and one shared exposure. A
selected surface uses that exposure when available; otherwise its caption says
that independent auto-exposure was used. Balance and the channel mixer apply to
both preview types. RGB chart visibility does not.

Every preview is an **illustrative sensor response, not calibrated color**. It
is not a CIE colorimetric prediction, camera-profile conversion, or photograph.
Missing dependencies, invalid reflectance, empty overlap, and valid zero
response are reported rather than replaced by fabricated patches.

## Troubleshooting

- Environment missing or wrong Python: rerun the installer with Python 3.12.
- Bundled data missing: initialize the source checkout's data submodule or use
  a release archive populated with `data/`.
- Import collision: change the metadata identity; v1 does not overwrite.
- Data was changed outside the app: use **Rebuild Cache**.
- Report failed: the prior artifact is removed, so correct the stated issue and
  generate again.

## Complete verification

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate4_verification.sh
```

For release-specific platform, scientific, provenance, privacy, and
accessibility constraints, read
[Known Limitations](docs/Known-Limitations.md). Bundled-curve provenance is
described separately in [Bundled Data Provenance](docs/Data-Provenance.md).
