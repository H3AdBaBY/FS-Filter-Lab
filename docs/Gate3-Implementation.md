# Gate 3 Vertical Workflow Implementation

Status: **Implemented and verified**

Approved decisions: `G3-D001` through `G3-D008`

Approval date: 2026-08-03

Scope: FS FilterLab only

## Outcome

The approved named workflow now resolves one deterministic snapshot after the
Streamlit controls are read. Interactive metrics, charts, report calculations,
and export metadata consume that same snapshot. No scientific formula or
bundled TSV was changed.

## Named workflow

- Filter: `IR Chrome (0.0, Kolari)`
- Count: `2`
- QE: `Generic CMOS sensor`
- Illuminant: `AM1.5_Global_REL`
- Target: none
- Sensor-response balance: not applied
- Channel mixer: disabled identity
- Visible channels: R, G, and B

Frozen compatibility outputs remain:

- Green-QE-weighted transmission: `0.2006086128216617`
- Green-channel effective stops: `2.3175445477191383`
- Weight coverage: `0.9997590771609786` (`99.98%` displayed)
- Balance divisors: R `0.19374828429823737`, G `1.0`, B
  `1.9813636440172737`
- Balance multipliers: R `5.1613360274235855`, G `1.0`, B
  `0.5047029115627004`

These values capture compatibility with the pinned bundled data. They do not
claim undocumented external calibration or scientific correctness.

## Implemented behavior

- Stable display identities resolve the named filter, QE, and illuminant.
- Repeated filters expand to repeated matrix indices while the report labels
  the stack as count two.
- One workflow snapshot supplies transmission, effective metric, balance,
  channel responses, identities, diagnostics, and report metadata.
- The initial no-filter state does not display a fabricated filter metric.
- Selection and count survive reruns.
- The interactive and report states both leave balance and mixing unapplied for
  the primary workflow, while displaying calculated balance information as
  `not applied`.
- Report filenames deterministically include the repeated-filter count.
- A state change suppresses an earlier report download until matching output is
  available.
- Regeneration clears old bytes before work begins; failure exposes an
  actionable message and no stale artifact.
- Export tests use temporary storage and leave production output untouched.

## Deterministic loading

Clean-cache and warm-cache runs reconcile exactly:

| Dataset type | Count |
|---|---:|
| Filters | 1,558 |
| QE profiles | 3 |
| Illuminants | 1 |
| Reflectors | 4 |
| Total bundled TSVs | 1,566 |

Identity lists and named workflow arrays are identical between the clean and
warm paths. No bundled file is modified by verification.

## Complete verification command

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate3_vertical.sh
```

The command creates a temporary locked Python 3.12 environment, runs the full
pytest suite, runs the inherited Gate 2 Streamlit smoke, exercises the Gate 3
interaction and artifact path, prints and enforces the approved performance
budgets, runs `pip check`, and cleans temporary environments and artifacts.

## Verification result

Verified on 2026-08-03 with Python 3.12.13:

- `41 passed`;
- exact 1,566-file reconciliation passed;
- inherited Streamlit startup/export smoke passed;
- Gate 3 interaction, report metadata, PNG signature, dimensions, non-blank
  content, deterministic naming, replacement, and stale suppression passed;
- `pip check`: no broken requirements;
- `git diff --check`: passed.

Measured timings on the target machine:

| Operation | Measured | Approved budget | Status |
|---|---:|---:|---|
| Uncached bundled-data processing | 0.962 s | 2.500 s | Pass |
| Cached initial Streamlit render | 0.269 s | 1.500 s | Pass |
| Filter-selection rerun median | 0.107 s | 0.750 s | Pass |
| Filter-selection rerun maximum | 0.137 s | 1.500 s | Pass |
| Count-change rerun median | 0.108 s | 0.750 s | Pass |
| Count-change rerun maximum | 0.145 s | 1.500 s | Pass |
| PNG generation and download | 0.428 s | 3.000 s | Pass |

The results above are from the final clean command after the actionable-failure
coverage was added.

## Deferred scope

The approved exclusions remain unchanged: no UI redesign, advanced-search
hardening, importer-form work, complete balance/mixer parity matrix, broader
reflector interaction parity, hosting, accounts, databases, telemetry, RAW
functionality, bundled-data edits, or new scientific formulas.
