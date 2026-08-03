# Gate 4 remaining parity and UX implementation

Status: **Complete; automated verification and the Gate 5C manual keyboard
smoke passed**

Owner approval: `G4-D001` through `G4-D012` as written, 2026-08-03

Scope: FS FilterLab only

## Gate 4A — Search and import

Implemented and reviewed:

- deterministic advanced-search text, transmission, and rainbow ordering;
- explicit exclusion/count of unknown transmission at the selected wavelength;
- Done merges checked identities without duplicates; Cancel is invariant;
- immutable bundled `data/` plus configurable, git-ignored `user_data/`;
- exact filename and stable-identity collision rejection;
- explicit filter, QE, and reflectance units;
- independent lower/upper extrapolation controls, both off by default;
- explicit relative-illuminant peak normalization to 100;
- absorption rejection with no inferred reflectance conversion;
- fully validated atomic publication and affected-cache invalidation;
- original upload filename retained as provenance.

Checkpoint result: **45 passed**, exact corpus reconciliation, Gate 3
Streamlit/PNG workflow, performance budgets, and `pip check` passed.

## Gate 4B — Processing parity

Implemented and reviewed:

- analytical R, G, and B arrays remain present regardless of trace visibility;
- visibility affects interactive and PNG traces only;
- optional balance applies exactly once before the mixer in reflector previews;
- disabled, identity, swap, negative, and above-unity mixer states are tested;
- enabled identity is explicitly labeled and is numerically invariant;
- reset restores identity without disabling the panel;
- the Gate 3 workflow snapshot supplies plots, previews, metrics, report
  metadata, and PNG rendering;
- all-hidden reports remain valid without fabricated channel traces;
- decorative report pixels clamp only at the display boundary while analytical
  mixer output remains unclipped.

Checkpoint result: **49 passed**, prior workflows, corpus audit, PNG inspection,
performance budgets, and `pip check` passed.

## Gate 4C — Product hardening

Implemented and reviewed:

- visible loading feedback for the four application collections;
- a critical no-filter-data state naming bundled and user locations;
- missing QE and missing illuminant as distinct non-blocking dependency states;
- missing illuminant no longer substitutes a uniform source;
- distinct invalid-reflector and valid-zero/invalid preview messages;
- an absent cache directory is a valid already-clean rebuild state;
- configurable `FS_FILTERLAB_CACHE_DIR` for isolated verification and operation;
- WCAG relative-luminance contrast selection for filter-result text;
- responsive chart/image bounds and stacked columns at 768 px and below;
- visible Open/Close filter-control labels replace icon-only narrow-window cues;
- removal of the Streamlit default/session-value conflict after search merge;
- Python 3.12 install/run launchers with populated-archive operation without Git;
- README, usage, and technical documentation aligned with verified behavior;
- one clean Gate 4 command using only temporary environment, cache, output, and
  user-data roots.

## Complete automated verification

Command:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate4_verification.sh
```

Verified on the reference 2020 M1 MacBook Air with Python 3.12.13 and the pinned
dependency set:

- **54 pytest tests passed**;
- bundled audit reconciled **1,566 discovered = 1,566 accepted + 0 skipped +
  0 duplicate + 0 invalid**;
- Gate 2 Streamlit/PNG smoke passed;
- Gate 3 vertical workflow and provisional budgets passed;
- Gate 4 search Done/Cancel, four-importer controls, missing-QE state,
  balance/mixer/visibility, vegetation/surface preview, shared exposure, report
  metadata, PNG inspection, and normal 801-sample import passed;
- clean populated-release installation, launcher preflight, live Streamlit
  health endpoint, and `pip check` passed;
- verification cleaned its temporary state and did not create or replace the
  developer `.venv`, cache, output, user data, or bundled TSV files.

Gate 4 measured results from the complete command:

| Operation | Measured | Budget | Result |
|---|---:|---:|---|
| Advanced-search backend, median of 10 | 0.003 s | <= 0.25 s | Pass |
| Advanced-search backend, maximum | 0.005 s | <= 0.75 s | Pass |
| Balance rerun, median of 10 | 0.112 s | <= 0.25 s | Pass |
| Balance rerun, maximum | 0.150 s | <= 0.75 s | Pass |
| Mixer rerun, median of 10 | 0.115 s | <= 0.25 s | Pass |
| Mixer rerun, maximum | 0.150 s | <= 0.75 s | Pass |
| Surface rerun, median of 10 | 0.121 s | <= 0.25 s | Pass |
| Surface rerun, maximum | 0.156 s | <= 0.75 s | Pass |
| 801-sample importer backend | 0.060 s | <= 1.00 s | Pass |
| Warm application render | 0.352 s | <= 3.00 s | Pass |

The advanced-search measurement covers deterministic filter/range/sort work over
all 1,558 bundled filters; interactive Done/Cancel behavior is verified
separately by Streamlit AppTest.

## Browser and accessibility evidence

The local application was inspected in the Codex in-app browser against the
running Streamlit server.

| Viewport | Page horizontal overflow | Chart bounds | Result |
|---|---:|---|---|
| 1280 x 900 | 0 px | 1,109 px main; 1,075 px secondary | Pass |
| 768 x 900 | 0 px | 725 px main; 691 px secondary | Pass |
| 390 x 844 | 0 px | 347 px main; 313 px secondary | Pass |

At 390 px, the 300 px sidebar opens as the intended overlay without widening
the page. Controls, chart title, traces, axis labels, balance text, preview
caption, and filter-control label remained legible. At 768 and 390 px, charts
resized inside their containers and no page-level horizontal scrolling was
present.

The browser DOM audit found application workflow controls in logical source
order, with `tabIndex=0`, unique descriptive labels, and no duplicate label in
the inspected sidebar control sequence. Charts retained textual title, axis,
and trace labels. Result colors have textual identities; previews have adjacent
limitations and exposure captions. Synthetic tests verify the WCAG
relative-luminance choice for black/white text over filter colors.

The in-app automation runtime could inspect focus structure but could not
reliably synthesize native Tab/Space traversal for Streamlit controls. The
owner completed the physical-keyboard usability check in Gate 5C and reported
no blocker. A later approved Gate 5 amendment made formal VoiceOver verification
and accessibility conformance outside the v1 scope.

## Acceptance status

| Criterion | Status |
|---|---|
| Search/import/data ownership | Pass |
| Balance/mixer/visibility and previews | Pass |
| Application states | Pass |
| Responsive 1280/768/390 layouts | Pass |
| Automated accessibility structure/contrast | Pass |
| Documentation and launchers | Pass |
| Performance and regression | Pass |
| Manual keyboard smoke | **Pass in Gate 5C** |
| VoiceOver verification | **Out of v1 scope by approved Gate 5 amendment** |

Gate 4 code is implemented, reviewed, and automated verification is green. The
approved Gate 5 amendment supersedes the earlier VoiceOver release gate. The
manual keyboard check passed for filter selection, advanced search, import,
processing controls, and report download.

## Scientific decisions

No new scientific decision was introduced in Gate 4. The implementation applies
the approved Gate 2 policies and the `G4-D001`–`G4-D012` processing/UX decisions.
It does not claim calibrated color or undocumented scientific correctness.

## Deferred boundary

Gate 5 subsequently completed final release limitations, dependency-license
review, packaging decisions, acceptance, and publication. Gate 4 added no
hosting, accounts, databases, telemetry, RAW functionality, framework rewrite,
bundled TSV edit, or scientific-formula redesign.
