# Gate 4 Remaining Parity and UX Decision Proposal

Status: **Approved for implementation**

Prerequisites: Gate 2 scientific policies and Gate 3 vertical workflow accepted

Scope: FS FilterLab only

## Purpose

Gate 4 completes the approved v1 parity surface without redesigning the product:

`advanced search + four importers + balance/mixer parity + reflector previews + application states + accessibility/responsiveness + documentation/launchers`

The recommendations preserve the Python/Streamlit architecture, the Gate 2
scientific policies, the Gate 3 workflow snapshot, and local/offline operation.
They do not authorize new scientific formulas, bundled-data edits, hosting,
accounts, databases, telemetry, RAW functionality, or a visual redesign.

## Audit findings requiring decisions

1. Advanced-search results are calculated, but its pending selection is never
   applied to the primary filter selector.
2. Search ordering needs deterministic tie-breakers, and unknown transmission
   samples need an explicit inclusion rule.
3. Importers currently write into bundled-data directories and can overwrite a
   same-named file without confirmation or rollback.
4. Filter and reflectance forms silently force endpoint extrapolation.
5. Newly imported filter, reflectance, and QE data still lack the explicit unit
   choices required by `G2-D001`.
6. The reflectance form offers absorption even though `G2-D009` makes
   absorption ineligible for reflector preview.
7. Gate 3 froze the default balance/mixer path, but not the full toggle,
   identity, custom-matrix, visibility, preview, and export parity matrix.
8. Preview calculations do not yet apply optional balance before the mixer.
9. Empty, unavailable, and failed states use inconsistent messages and can be
   difficult to distinguish from a valid zero response.
10. Current launchers assume an existing environment or combine installation
    and application startup; clean release-archive behavior is undocumented.

## Recommended decisions

### G4-D001 — Deliver Gate 4 as three bounded slices

Implement and review in this order:

1. **Gate 4A — Search and import:** advanced-search selection, four importers,
   user-data storage, collision handling, and deterministic reload.
2. **Gate 4B — Processing parity:** white balance, channel mixer, RGB
   visibility, vegetation preview, single-surface preview, and PNG parity.
3. **Gate 4C — Product hardening:** loading/empty/warning/error states,
   accessibility, narrow layouts, documentation, and clean-install launchers.

Each slice must keep the complete prior suite green and receive a focused code
review before the next slice. Approval of this sheet authorizes all three
slices, but a failed slice blocks progression.

### G4-D002 — Freeze advanced-search semantics

- Manufacturer filtering uses exact bundled/user metadata values.
- Wavelength is an integer sample on the inclusive 300–1100 nm grid.
- Transmission bounds are inclusive physical fractions displayed as percent.
- A filter with `NaN` at the chosen wavelength is excluded from a numeric range
  result and counted in an “unknown at this wavelength” note.
- Sorts are deterministic:
  - filter number and filter name sort case-insensitively, then by stable display
    identity;
  - transmission sorts high-to-low, then by stable display identity;
  - rainbow sorting uses hue, saturation, and lightness, with invalid colors
    last and explicitly labeled.
- **Done** adds checked results to the current primary selection, de-duplicates
  by display identity, and preserves the current selection order.
- **Cancel** changes no primary selection or count.
- Removed primary selections stay removed; search must not resurrect stale
  session keys.

This repairs the existing disconnected pending-selection behavior without
changing navigation or redesigning the search surface.

### G4-D003 — Keep imported data separate from bundled data

- Bundled `data/` remains read-only application content with the frozen 1,566
  file reconciliation.
- Successful imports are written under a local, git-ignored `user_data/` tree
  with the same four data-type subdivisions.
- Tests redirect the user-data root to a temporary directory through one
  documented environment variable.
- Loaders combine bundled and user collections while preserving source/provenance
  metadata and reporting counts separately.
- Reject a filename or stable display-identity collision. V1 does not overwrite,
  replace, or silently version an existing dataset.
- Validate completely before writing, then atomically publish a same-directory
  temporary file only if the destination is still absent. A failed import leaves
  no partial dataset.
- A successful import invalidates only the affected collection cache and appears
  after one deterministic rerun.

This remains local file storage, not a database or account system.

### G4-D004 — Make importer units, domains, and supported quantities explicit

All import forms accept deterministic comma- or semicolon-separated numeric
CSV, with an optional single header row, and reject ambiguous parsing.

- **Filter:** require `fraction` or `percent`; require wavelength in nm.
- **QE:** require `fraction` or `percent`; serialize to the approved internal
  percent convention; require R, G, and B columns.
- **Reflectance:** require `fraction` or `percent`; require wavelength in nm.
- **Illuminant:** label values as non-negative relative power and explicitly
  peak-normalize serialized values to 100, preserving current importer
  compatibility and reporting that normalization.
- Filter and reflectance forms expose lower and upper constant extrapolation as
  separate choices, both off by default. Every extrapolated sample remains
  masked and visibly distinguished.
- QE and illuminant imports retain `NaN` outside measured support; Gate 4 does
  not invent an extrapolation policy for them.
- Remove absorption as an eligible reflector import. Show an actionable message
  that absorption is not converted to reflectance because no measurement model
  is approved.
- Surface structured normalization, clipping, sorting, and unknown-value
  diagnostics in the success result.

### G4-D005 — Freeze the complete balance/mixer/visibility processing matrix

Retain the approved order from `G2-D008`:

`linear sensor response → optional balance multiplier → optional 3×3 mixer → visibility/display transform`

Required states:

- balance off and on;
- mixer disabled;
- mixer enabled with identity coefficients;
- mixer enabled with an R/B swap;
- mixer enabled with finite negative and above-unity coefficients;
- identity reset;
- R, G, and B independently visible/hidden.

Rules:

- Enabling an identity mixer is numerically invariant but labeled “Mixer
  enabled: identity.”
- Reset restores all nine identity coefficients without changing the panel's
  enabled state.
- Hiding a channel affects plotted interactive and PNG traces only. It does not
  alter balance, mixer inputs, previews, metrics, or stored scientific arrays.
- Non-finite coefficients are rejected. Analytical negative/above-range output
  remains linear; display pixels clamp only at the display boundary.
- The Gate 3 snapshot remains the sole state source for interactive plots,
  previews, and PNG generation.

### G4-D006 — Apply the same processing state to reflector previews

- Vegetation and single-surface calculations use the snapshot's validated
  transmission, illuminant, QE, optional balance multipliers, and mixer.
- RGB chart visibility never changes preview calculations.
- The four named vegetation reflectors keep their approved fixed 2×2 order and
  one shared exposure.
- A selected single surface uses the vegetation group's exposure when that
  group is available. Otherwise it may use independent auto-exposure only with
  the existing explicit label.
- Missing required leaves, missing QE/illuminant, empty common support, invalid
  reflectance, and zero response produce distinct messages and no fabricated
  color patch.
- All preview text continues to say “illustrative sensor response; not
  calibrated color.”

### G4-D007 — Standardize loading, empty, warning, and error states

Use concise, actionable states without a navigation redesign:

- Initial loading identifies the collection being loaded when work is visible
  long enough to need feedback.
- No filters is a critical blocking state with the expected data location.
- No QE or no illuminant leaves filter analysis usable, hides dependent output,
  and states what selection is required.
- No filter selection is a valid empty state, not an error.
- Partial spectral coverage remains a warning attached to the affected result.
- Missing reflector data disables previews without blocking filter analysis.
- Import, cache, and export failures name the failed operation, preserve the
  last valid scientific state, and never expose a stale or partial artifact.
- A true numerical zero is labeled as a valid zero and is never presented as a
  loading or missing-data state.

### G4-D008 — Define blocker-level accessibility acceptance

Gate 4 targets the practical WCAG 2.2 AA baseline available through Streamlit.
A blocker is any issue that prevents a keyboard or screen-reader user from
completing the named filter workflow, search, import, processing controls, or
report download.

Required acceptance:

- Every interactive element has a unique, descriptive accessible label.
- Keyboard navigation reaches controls in a logical order with visible focus;
  no operation requires pointer-only interaction.
- Heading order and control grouping convey the same structure as the visual
  layout.
- Text and essential control contrast meet 4.5:1 for normal text and 3:1 for
  large text/UI components; filter colors never carry meaning without text.
- RGB channels, warnings, success, and errors use text labels in addition to
  color or icons.
- Preview images have adjacent descriptive captions, and charts retain textual
  titles, axis labels, trace names, and metric summaries.
- Automated structural checks are supplemented by a documented keyboard and
  macOS VoiceOver smoke on the reference machine.

This authorizes accessibility corrections, not a new visual design system.

### G4-D009 — Define responsive-layout acceptance

- Preserve Streamlit's wide-page structure and existing sidebar/main-content
  organization.
- Verify desktop widths of 1280 px and above, a 768 px tablet/narrow-window
  width, and a 390 px phone-width fallback.
- At narrow widths, multi-column forms and the 3×3 mixer may stack vertically;
  labels must remain associated with their controls.
- No essential control, metric, warning, table, preview, or download action may
  require horizontal page scrolling.
- Charts resize to their container and retain legible titles/trace access.
- Dense bundled search results may scroll vertically and use bounded rendering,
  but v1 does not add a new client-side framework or virtualized application.

### G4-D010 — Make documentation and launchers match the verified product

- README and usage documentation describe CSV import columns, explicit units,
  extrapolation choices, user-data storage, balance/mixer order, preview limits,
  and the exact Gate 4 verification command.
- Technical documentation distinguishes raw, physical, analytical, and display
  values and identifies the workflow snapshot.
- `install.sh`/`install.bat` create a Python 3.12 `.venv`, initialize the data
  submodule when Git is available, install through the pinned constraints, and
  stop with an actionable message on failure. Installation does not implicitly
  launch a long-running server.
- `run.sh`/`start.bat` verify the environment and data, then launch Streamlit.
- A release archive with populated data must run without Git. Local application
  use is offline after dependencies are installed; offline dependency
  installation is not promised.
- Launcher verification uses a temporary copy/environment and never overwrites
  the developer's `.venv`, cache, output, or user data.

### G4-D011 — Adopt measured Gate 4 responsiveness budgets

Measure on the 2020 M1 MacBook Air with the pinned Python 3.12 environment,
excluding dependency installation and first-time font-cache creation.

| Operation | Proposed budget |
|---|---:|
| Advanced-search apply over 1,558 bundled filters | ≤ 0.25 s median and ≤ 0.75 s maximum over 10 runs |
| Balance toggle rerun | ≤ 0.25 s median and ≤ 0.75 s maximum over 10 runs |
| Mixer coefficient rerun | ≤ 0.25 s median and ≤ 0.75 s maximum over 10 runs |
| Surface-selection rerun | ≤ 0.25 s median and ≤ 0.75 s maximum over 10 runs |
| Normal 801-sample importer backend result | ≤ 1.0 s |
| Warm clean-install application render | ≤ 3.0 s |

Report measurements before enforcing them in ordinary CI. Target-machine
failure blocks Gate 4 unless evidence supports an explicitly approved revision.

### G4-D012 — Keep the Gate 4 boundary closed

Do not include:

- new scientific or colorimetric formulas;
- conversion from absorption to reflectance;
- bundled TSV edits or per-dataset provenance remediation;
- a UI/navigation redesign or framework rewrite;
- hosting, accounts, databases, collaboration, analytics, or telemetry;
- RAW decoding, image development, or integration with another product;
- packaging/notarization, release publishing, dependency-license review, or
  final release known-limitations work assigned to Gate 5.

## Acceptance matrix

| Area | Required evidence |
|---|---|
| Advanced search | Stable filters/sorts, unknown handling, Done merge, Cancel invariance, no stale selection |
| Filter import | Explicit unit/extrapolation, atomic user-data write, reload, collision rejection, diagnostics |
| Illuminant import | Relative-power validation, explicit peak normalization, atomic write/reload |
| QE import | Explicit unit, aligned RGB validation, atomic write/reload, invalid-channel rejection |
| Reflectance import | Explicit unit/extrapolation, absorption rejection, atomic write/reload |
| Data ownership | Frozen bundled count plus separately reconciled temporary user data; no bundled changes |
| Balance/mixer | Full approved state matrix across response arrays, plots, previews, and PNG |
| Visibility | Independent plotted traces; no scientific or preview delta |
| Vegetation preview | Fixed order, shared exposure, applied balance/mixer, named invalid states |
| Surface preview | Shared or explicitly independent exposure, selected curve, named invalid states |
| Application states | Loading, valid empty, missing dependency, partial, zero, import/cache/export failure |
| Accessibility | Automated labels/structure plus keyboard and VoiceOver smoke; no blockers |
| Responsive layout | 1280, 768, and 390 px evidence with no essential horizontal overflow |
| Documentation | Clean setup/use/import/science-limit instructions match tested behavior |
| Launchers | Temporary clean-install and populated-release-archive launch smoke |
| Performance | Reference-machine measurements meet `G4-D011` |
| Regression | Gate 3 command, 1,566 bundled reconciliation, PNG inspection, and `pip check` remain green |

## Complete Gate 4 command

Implementation should provide one command, proposed as:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate4_verification.sh
```

It should create temporary user-data, cache, output, and Python environments;
run all prior tests; run search/import/parity/state interaction suites; reconcile
bundled and temporary user datasets separately; inspect PNG artifacts; print
performance measurements; run launcher smoke checks and `pip check`; and clean
all temporary state.

Manual evidence recorded beside the command result must cover keyboard,
VoiceOver, and the three approved viewport widths until those checks can be
reliably automated in the local stack.

## Exit criteria

Gate 4 exits only when:

1. `G4-D001` through `G4-D012` are approved or amended by the owner.
2. Gate 4A, 4B, and 4C each pass focused review in order.
3. The complete parity matrix passes with no undocumented scientific change.
4. Bundled counts remain exactly reconciled and imports touch only temporary or
   user-data storage.
5. No blocker-level accessibility issue remains.
6. Target-machine responsiveness meets the approved budgets.
7. The complete Gate 4 command passes from a clean environment.
8. Deferred Gate 5 work remains documented and unimplemented.

## Approval record

The owner approved `G4-D001` through `G4-D012` as written on 2026-08-03.
