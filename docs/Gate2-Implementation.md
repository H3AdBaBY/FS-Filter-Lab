# Gate 2 Scientific Policy Implementation

Status: **implemented and verified**
Owner approval: **G2-D001 through G2-D010 as written, 2026-08-03**

This gate applies the approved policies in `Gate2-Decision-Proposal.md`. It does
not claim calibrated colorimetric correctness, and it does not modify bundled
TSV source files.

## Decision status

| Decision | Implemented outcome |
|---|---|
| G2-D001 | Canonical nanometres, fractional transmission/reflectance, percent QE, relative illuminant, and diagnostic legacy-unit inference |
| G2-D002 | Stable sorting with warning, duplicate rejection, unknown-value preservation, linear 300–1100 nm interpolation, and explicit masked constant extrapolation |
| G2-D003 | Recoverable normalized raw curves plus bounded physical calculation curves and file-level clipping diagnostics |
| G2-D004 | One multiplicative stack path for single, combined, and repeated filters; exact zero and `NaN` propagation preserved |
| G2-D005 | Structured green-QE-weighted transmission/stops result with coverage, reasons, and infinite stops at exact zero |
| G2-D006 | Common-domain green-referenced balance divisors, reciprocal multipliers, and structured invalid states |
| G2-D007 | Linear unfloored RGB calculation output; visibility and exposure remain presentation operations |
| G2-D008 | Validated finite 3-by-3 linear mixer after optional balance and before presentation clipping |
| G2-D009 | Reflector output labeled illustrative sensor response; group exposure is shared and no calibrated-color claim is made |
| G2-D010 | Python 3.12 reference, exact constraints including pandas 3, writable loader copies, versioned cache envelopes, and startup smoke coverage |

## Bundled-data reconciliation

The production processors classify all **1,566** bundled TSV files:

| Dataset type | Discovered | Accepted | Skipped | Duplicate | Invalid |
|---|---:|---:|---:|---:|---:|
| Filters | 1,558 | 1,558 | 0 | 0 | 0 |
| QE profiles | 3 | 3 | 0 | 0 | 0 |
| Illuminants | 1 | 1 | 0 | 0 | 0 |
| Reflectors | 4 | 4 | 0 | 0 | 0 |
| **Total** | **1,566** | **1,566** | **0** | **0** | **0** |

The structured report contains **1,572** unit-interpretation records,
**34** physical-bound clipping records, and **63** non-finite-value records.
Every diagnostic contains the affected file and reason. Source TSVs remain
unchanged.

## Compatibility deltas

- Legacy unit inference now changes at values above 1.0 instead of above 1.5;
  no bundled file falls in the changed interval.
- Negative or above-range transmission and reflectance measurements remain in
  raw curves but calculations use clipped physical curves.
- A true zero stack stays zero. It is no longer raised to `1e-6` in the
  multi-filter path.
- Exact-zero effective transmission reports infinite stops; partial spectral
  support reports its weight coverage.
- RGB calculations no longer apply maximum normalization or the `1/255` floor.
- Invalid balance inputs return a reason rather than silently substituting
  unity values.
- pandas 3 is supported by copying loader arrays before normalization.

## Complete verification command

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate2_verification.sh
```

The command creates a clean temporary environment from the exact constraints,
runs the complete deterministic suite and bundled-data reconciliation, executes
the Streamlit application once with its test harness, runs `pip check`, and
removes the environment.

## Remaining limits

- Reflector previews are camera-response illustrations, not calibrated sRGB or
  CIE color predictions.
- Legacy imported files still infer units because the explicit-unit import UI
  is reserved for the approved later form-hardening work; the backend reports
  the inference in the success message.
- The exact constraints are the verified v1 Python 3.12 environment. Supporting
  another Python version or changing a dependency requires rerunning this gate.
