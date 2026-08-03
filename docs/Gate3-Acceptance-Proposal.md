# Gate 3 Vertical Workflow Acceptance Proposal

Status: **Proposed — owner approval required before implementation**

Prerequisite: reviewed Gate 2 implementation merged or explicitly accepted
Scope: FS FilterLab only

## Purpose

Gate 3 hardens one complete production path:

`load bundled data → select filter/count → choose QE and illuminant → calculate → render → export PNG`

This gate connects already-approved scientific services to one tested Streamlit
workflow. It does not redesign the interface or expand the product.

## Recommended Gate 3 decisions

### G3-D001 — Freeze one named reference workflow

Use this stable identity-based path, never positional array indices:

- bundled filter `IR Chrome (0.0, Kolari)`;
- stack count `2`;
- QE profile `Generic CMOS sensor`;
- illuminant `AM1.5_Global_REL`;
- no target profile;
- sensor-response balance toggle off for the primary path;
- identity/disabled channel mixer;
- all RGB chart channels visible.

The expected scientific outputs are the values recorded in `Gate2-Review.md`.
Tests use full-precision tolerances; the UI and PNG use their declared display
precision.

### G3-D002 — Test the workflow at three layers

1. **Service orchestration:** identity resolution, repeated-filter expansion,
   calculation results, diagnostics, and report inputs.
2. **Streamlit interaction:** select the named filter, set count two, confirm QE
   and illuminant, verify metric text and charts, generate the report, and expose
   one download action without an application exception.
3. **Artifact inspection:** confirm PNG signature, dimensions, non-blank image
   content, deterministic filename components, and expected report state.

Do not use a full-image byte hash as the cross-platform requirement. Fonts and
rendering backends can change bytes without changing the report. The pinned
Python 3.12 environment may additionally keep a local visual reference with a
tolerant perceptual comparison.

### G3-D003 — One state snapshot drives calculation, charts, and export

- Resolve selected filter identities and counts once per rerun.
- Use the same combined physical transmission for interactive metrics, charts,
  and PNG export.
- Use the same QE, illuminant, balance state, mixer state, and diagnostics for
  every consumer in that rerun.
- Do not introduce a second scientific formula in a view or exporter.

This allows small orchestration cleanup only where necessary to remove observed
duplication. It does not authorize a broad state or production-architecture
rewrite.

### G3-D004 — Export must reflect current interactive state

- With the primary workflow defaults, neither the interactive sensor response
  nor PNG response is balance-adjusted or channel-mixed.
- The calculated balance multipliers may still be displayed as information and
  must be labeled “not applied.”
- The filter count, effective transmission, stops, coverage, QE identity, and
  illuminant identity must agree between the interactive workflow and report.
- Export creates one PNG and one download artifact. Tests redirect disk output
  to a temporary directory.

Gate 3 does not expand coverage to all optional balance/mixer configurations;
that parity matrix remains Gate 4.

### G3-D005 — Deterministic loading and identity resolution

- The test starts from a clean cache and verifies the exact bundled inventory:
  1,558 filters, 3 QE profiles, 1 illuminant, and 4 reflectors.
- Reference selections resolve by stable display identity, not filesystem order
  or DataFrame row number.
- Cache-hit and cache-miss runs must produce identical workflow outputs.
- No bundled TSV is modified.

### G3-D006 — Provisional responsiveness budgets

Measure on the stated 2020 M1 MacBook Air, Python 3.12 locked environment, with
dependency installation and first-time font-cache creation excluded.

| Operation | Provisional budget |
|---|---:|
| Uncached bundled-data processing | ≤ 2.5 seconds |
| Cached initial Streamlit workflow render | ≤ 1.5 seconds |
| Filter-selection rerun | ≤ 0.75 seconds median and ≤ 1.5 seconds maximum over 10 runs |
| Count-change rerun | ≤ 0.75 seconds median and ≤ 1.5 seconds maximum over 10 runs |
| PNG generation and download availability | ≤ 3.0 seconds |

Review measurements before enforcing them in ordinary CI. Target-machine
failure blocks Gate 3 unless evidence supports an explicitly approved revision.
Reference review measurements were approximately 0.887 seconds for uncached
bundled loading, 0.343 seconds for initial AppTest execution, 0.106 seconds for
a selection/count rerun, and 0.482 seconds for PNG generation.

### G3-D007 — Required states within the vertical slice

Gate 3 covers only states needed to make the path trustworthy:

- initial no-filter state does not show a fabricated filter metric;
- the named selection and count are retained across reruns;
- partial coverage is visibly labeled `99.98%`;
- report generation failure produces an actionable error and no stale download;
- successful regeneration replaces the previous download deterministically;
- cache-hit and cache-miss paths show no scientific delta.

The broad loading, empty, warning, accessibility, and responsive-layout matrix
remains Gate 4.

### G3-D008 — Scope exclusions

Do not include:

- UI redesign or navigation changes;
- advanced search hardening;
- importer-form hardening or explicit unit controls;
- the complete white-balance/channel-mixer parity matrix;
- vegetation or arbitrary single-surface interaction parity;
- hosting, accounts, databases, telemetry, or RAW functionality;
- bundled-data edits or new scientific formulas.

## Acceptance matrix

| Area | Required evidence |
|---|---|
| Data load | Exact inventory and identical clean-cache/warm-cache identities |
| Selection | Named filter resolves without positional assumptions; count two expands to repeated indices |
| Calculation | Frozen transmission, stops, coverage, divisors, and multipliers within explicit tolerance |
| Interaction | AppTest performs selection and count changes with zero exceptions |
| Charts | Combined transmission and three sensor-response traces are present and use current state |
| Metrics | Interactive label, values, units, partial-coverage text, and applied-state label are correct |
| Export | One valid PNG and download artifact; state agrees with interactive calculation |
| Failure | Forced export error is actionable and cannot expose a stale artifact |
| Performance | Target-machine measurements meet the provisional budgets |
| Regression | Gate 2 suite, 1,566-file reconciliation, startup smoke, and `pip check` remain green |

## Complete Gate 3 command

Implementation should provide one command, proposed as:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate3_vertical.sh
```

It should create a temporary locked environment, run Gate 2 regression tests,
run the Gate 3 service and Streamlit interaction suite, redirect export output
to temporary storage, validate the PNG, print performance measurements, run
`pip check`, and clean up.

## Exit criteria

Gate 3 exits only when:

1. `G3-D001` through `G3-D008` are approved or amended by the owner.
2. The named workflow passes service, Streamlit, and artifact coverage.
3. Interactive and exported results use the same approved scientific services.
4. Cache-hit and cache-miss outputs are identical.
5. Target-machine responsiveness meets the approved provisional budgets.
6. Gate 2 verification and exact dataset reconciliation remain green.
7. Intentional behavior changes, if any, are documented before implementation.

## Approval record

No Gate 3 implementation is authorized by this proposal. Record owner approval
or amendments here before changing the vertical workflow.
