# Gate 4 Remaining Parity and UX Implementation

Status: **In progress — Gate 4A verified**

Owner approval: `G4-D001` through `G4-D012` as written, 2026-08-03

## Gate 4A — Search and import

Implemented:

- deterministic advanced-search text, transmission, and rainbow ordering;
- explicit exclusion and count of filters with unknown transmission at the
  selected wavelength;
- Done merges checked identities into the primary selector without duplicates;
- Cancel leaves the primary selection unchanged and stale result keys are
  cleared only when the search closes;
- immutable bundled `data/` plus configurable, git-ignored `user_data/` loading;
- exact bundled/user identity collision rejection;
- explicit units for filter, QE, and reflectance imports;
- explicit lower/upper extrapolation controls, both off by default;
- explicit peak-to-100 normalization for relative illuminant imports;
- absorption rejection with no inferred reflectance conversion;
- fully validated same-directory temporary writes atomically published without
  overwrite;
- affected-collection cache invalidation and deterministic reload;
- original upload filename retained as import provenance.

Verification checkpoint:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate3_vertical.sh
```

Result: **45 passed** on Python 3.12.13; exact 1,566 bundled reconciliation,
Gate 3 Streamlit interaction/export, PNG inspection, all provisional Gate 3
performance budgets, and `pip check` passed. Imported fixture data was written
only to temporary user-data roots.

Gate 4B and Gate 4C remain unimplemented at this checkpoint.
