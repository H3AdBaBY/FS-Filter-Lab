# Gate 2 Review

Status: **Passed after corrective changes**

Reviewed implementation: `24866a3`
Approved policy: `G2-D001` through `G2-D010`
Review date: 2026-08-03

## Outcome

The scientific-policy implementation is ready for the Gate 2 merge checkpoint
after the corrections in this review are committed. The review found five
actionable defects; all five are fixed and covered by focused verification.

## Findings and resolution

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| G2-R001 | Blocker | Importers independently dropped missing wavelength and value cells, which could shift row alignment and discard unknown samples before validation. | Import columns are now extracted together; wavelengths must be finite, and non-finite spectral values remain aligned and reach the shared policy as unknown samples. |
| G2-R002 | High | Explicit importer extrapolation was saved only in a filename suffix, so the per-sample mask was lost after loading. | Imported filter and reflector TSVs carry an `Extrapolated` column; loaders restore the mask, models retain it, and charts render extrapolated reflector regions distinctly. |
| G2-R003 | Medium | Partial coverage of 99.976% was displayed as both “partial” and “100.0%.” | Interactive and PNG metrics now use two decimal places for partial coverage, displaying `99.98%`. |
| G2-R004 | Blocker | The named PNG workflow failed because the renderer requested missing `legend` and `main_title` font roles. | Both roles are defined and tested; the export produces one valid full-size PNG and one download artifact. |
| G2-R005 | High | PNG sensor response always applied balance and omitted the active mixer, regardless of interactive state. | Report configuration now carries the existing balance toggle and mixer, and the renderer uses the shared response pipeline and labels the applied processing. |

## Additional edge coverage

The review added executable checks for:

- filter-stack order invariance;
- negative effective-metric weights and zero overlap;
- common partial-domain sensor-response balance;
- negative and above-unity mixer output;
- absorption rejection as reflectance;
- cache round-trip preservation of measured and extrapolated masks;
- importer raw excursions, unknown values, coordinate rejection, diagnostics,
  and extrapolation-mask round trips;
- report configuration completeness, display black preservation, shared group
  exposure, partial-coverage precision, Streamlit selection/count interaction,
  PNG generation, download availability, and PNG structure.

## Named review workflow

- Filter: `IR Chrome (0.0, Kolari)`
- Count: `2`
- QE: `Generic CMOS sensor`
- Illuminant: `AM1.5_Global_REL`
- Green-QE-weighted transmission: `0.2006086128216617`
- Green-channel effective stops: `2.3175445477191383`
- Weight coverage: `0.9997590771609786` (`99.98%` displayed)
- Balance divisors: R `0.19374828429823737`, G `1.0`, B
  `1.9813636440172737`
- Balance multipliers: R `5.1613360274235855`, G `1.0`, B
  `0.5047029115627004`

These values are compatibility expectations for the pinned data revision, not
claims of external scientific calibration.

## Verification

The complete clean-environment command remains:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate2_verification.sh
```

Gate 2 is merge-ready only when this command, `git diff --check`, and the exact
1,566-file dataset reconciliation pass after the review commit.

Final review result: **36 tests passed** on Python 3.12.13; all 1,566 bundled
TSVs reconciled; the Streamlit selection/count/export smoke passed; the PNG and
download artifact checks passed; `pip check` reported no broken requirements;
and `git diff --check` passed.

## Deferred by plan

- Broader white-balance and mixer UI parity belongs to Gate 4.
- All four importer forms and explicit unit selectors belong to Gate 4.
- Broader empty/error/accessibility UX belongs to Gate 4.
- Gate 3 covers only the approved named vertical workflow.
