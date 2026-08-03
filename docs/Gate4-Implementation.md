# Gate 4 Remaining Parity and UX Implementation

Status: **In progress — Gate 4A and Gate 4B verified**

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

## Gate 4B — Processing parity

Implemented:

- analytical R, G, and B response arrays remain available regardless of chart
  visibility;
- visibility controls only interactive and PNG plotted traces;
- optional balance is applied exactly once before the mixer for vegetation and
  selected-surface previews;
- mixer-disabled, enabled-identity, custom/swap, negative, and above-range
  analytical states remain deterministic and unclipped;
- enabled identity is labeled explicitly and remains numerically invariant;
- identity reset preserves the enabled panel state;
- Gate 3 workflow snapshots provide processing state to plots, previews, report
  metadata, and PNG rendering;
- all-hidden report state remains valid without fabricated channel traces.

Verification checkpoint: **49 passed** on Python 3.12.13; the complete prior
suite, bundled reconciliation, Streamlit/PNG smoke, performance budgets, and
`pip check` passed.

Gate 4C remains unimplemented at this checkpoint.
