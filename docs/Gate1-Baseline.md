# Gate 1 Scientific Compatibility Baseline

This baseline records the pinned application's current numerical behavior. It is
not a claim that the behavior is scientifically correct or colorimetrically
calibrated. Gate 1 changes no production formulas, bundled datasets, UI, or
architecture.

## Complete command

Run the deterministic baseline and bundled-data audit from a clean temporary
virtual environment:

```bash
bash scripts/run_gate1_baseline.sh
```

The runner requires Python 3.10 or newer, installs `requirements-test.txt`, runs
all tests, and removes its temporary environment. The focused test requirements
contain only pytest and the NumPy/Pandas dependencies of the scientific and TSV
loading modules; the UI stack is not started. Set `PYTHON_BIN` when the desired
interpreter is not named `python3`.

To print the dataset audit independently, with an optional full per-file JSON
artifact:

```bash
python -m scripts.validate_datasets --json-output output/gate1-datasets.json
```

## Pinned bundled-data reconciliation

Validated against data submodule `a1e7a927dcd4c477aca2f7d36748532ad92fb895`
with Python 3.12.13 and pandas 2.3.3.

| Dataset type | Discovered | Accepted | Skipped | Duplicate | Invalid |
|---|---:|---:|---:|---:|---:|
| Filters | 1,558 | 1,558 | 0 | 0 | 0 |
| QE profiles | 3 | 3 | 0 | 0 | 0 |
| Illuminants | 1 | 1 | 0 | 0 | 0 |
| Reflectors | 4 | 4 | 0 | 0 | 0 |
| **Total** | **1,566** | **1,566** | **0** | **0** | **0** |

No affected files were found: every discovered TSV was accepted, and no file
was skipped, duplicated by loader identity or identical bytes, or invalid. The
validator emits the affected file and reason whenever any non-accepted category
is present. The pytest assertion makes inventory drift visible.

## Captured compatibility behavior

- The canonical grid contains 801 samples from 300 through 1100 nm.
- Linear interpolation returns `NaN` outside the measured wavelength range.
- A filter is treated as percentage input only when its maximum exceeds 1.5.
- Stacks multiply wavelength-by-wavelength; repeated selections exponentiate a
  filter by multiplication. A `NaN` in any member propagates at that wavelength.
- The multi-filter presentation path clips finite results to `[1e-6, 1]`; the
  single-filter and active-transmission paths do not apply that clip.
- Effective transmission is weighted by illuminant times QE. Zero transmission
  is clipped to `1e-6`, producing a finite stop value; all-zero weights return
  `NaN` metrics.
- RGB response divides QE by 100, divides by the stored white-balance value,
  normalizes the display matrix by its maximum, then floors display components
  at `1/255`.
- White-balance values are integrated channel-response ratios relative to green.
- Channel mixing is a direct 3-by-3 linear transform. Reflector previews use the
  four exact leaf names, calculate white balance first, and return uncalibrated
  RGB-like response values before UI normalization.

## Proposed scientific and compatibility decisions

These items require approval before Gate 2 changes behavior:

1. Define explicit input units and replace or confirm the `max > 1.5`
   fraction/percentage heuristic, including values between 1.0 and 1.5.
2. Define sorting, duplicate-wavelength, non-finite-input, extrapolation, and
   out-of-range policies before replacing the current direct `numpy.interp` use.
3. Decide whether single, active, and stacked transmissions should share one
   clipping and `NaN` policy.
4. Decide whether true zero transmission should mean infinite stops rather than
   the current finite `-log2(1e-6)` result.
5. Confirm QE units and whether effective-stop weighting should use one channel,
   a combined sensor response, or another documented reference.
6. Confirm white-balance semantics and naming: current values are response ratios
   to green and are later used as divisors.
7. Decide whether hidden/zero RGB display channels should remain visible at the
   `1/255` floor, and whether normalization should occur before or after mixing.
8. Define clipping/normalization for negative or above-range channel-mixer
   outputs.
9. Label reflector colors as illustrative unless a calibrated colorimetric
   transform, output color space, adaptation model, and display mapping are
   approved.
10. Approve supported Python/dependency versions. The application uses Python
    3.10 union syntax despite older README guidance, and pandas 3 makes 1,480
    percentage-valued filters fail at the existing in-place normalization step.
    Gate 1 therefore constrains only the test environment to pandas `<3`; it does
    not change the production loader or release dependency policy.
