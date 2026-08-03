# Gate 2 Scientific and Compatibility Decision Proposal

Status: **Approved**

Owner approval: **G2-D001 through G2-D010 as written, 2026-08-03**

Baseline: application `95bf346e95927a64e5433f6c3d5c84cf145e92cd`,
data `a1e7a927dcd4c477aca2f7d36748532ad92fb895`

Scope: FS FilterLab only

## Purpose

This sheet turns the ambiguities recorded by Gate 1 into a recommended policy
set for Gate 2. Approval authorizes focused changes to data validation,
calculations, diagnostics, cache behavior, dependency constraints, and tests. It
does not authorize a UI redesign, bundled-data edits, hosting, accounts,
databases, RAW functionality, or claims of calibrated colorimetry.

The recommendations favor four principles:

1. Preserve source measurements and current results as traceable evidence.
2. Keep unknown data unknown instead of silently converting it to zero.
3. Separate physical calculations from display normalization and clipping.
4. Name outputs according to what the inputs and formula actually support.

## Approval summary

| ID | Recommended decision | Expected compatibility |
|---|---|---|
| G2-D001 | Canonical internal units with diagnostic legacy inference | Bundled classification unchanged |
| G2-D002 | Deterministic wavelength validation and linear interpolation | Bundled ordering unchanged; bad imports become actionable errors |
| G2-D003 | Preserve raw values; derive bounded physical values for calculations | Numeric changes only where source values fall outside physical bounds |
| G2-D004 | One stack/overlap policy; preserve zero and `NaN` | Removes inconsistent single/stack clipping |
| G2-D005 | Rename and harden effective-stops calculation; report coverage | Zero becomes infinite stops; partial-domain results become explicit |
| G2-D006 | Make white-balance divisors and multipliers explicit | Normal valid cases retain the same applied correction |
| G2-D007 | Keep RGB response linear; move floor/normalization to display | Zero channels render black; visibility no longer changes calculations |
| G2-D008 | Apply mixer as an unclipped linear transform in a fixed order | Identity and swaps remain invariant |
| G2-D009 | Label reflector previews as illustrative sensor simulations | No calibrated-color claim; shared exposure preserves comparisons |
| G2-D010 | Use Python 3.12 as the v1 reference and lock dependencies | Reproducible install; pandas 3 loader failure corrected |

## Bundled-data evidence affecting the recommendations

Gate 1 classified all 1,566 TSV files as accepted by the current processors. A
read-only diagnostic pass found additional conditions that those permissive
processors do not report:

- All wavelengths are already ascending with no duplicate wavelength samples.
- Of 1,558 filter files, 28 have a maximum at or below 1, 1,518 have a maximum
  above 1.5 and at or below 100, and 12 contain at least one value above 100.
  No bundled filter has a maximum in the current ambiguous interval `(1, 1.5]`.
- Twenty-two filter files contain a negative transmittance sample. The lowest
  observed value is -0.36 percent, consistent with small measurement or
  digitization excursions rather than a physical negative transmission.
- Fifty-nine filter files contain at least one non-finite transmittance sample;
  two QE files contain at least one non-finite channel sample.
- Three Schott files contain `5150` transmittance at wavelength `3650 nm`,
  outside the canonical 300–1100 nm analysis grid. This must be reported as a
  provenance/data-quality issue, not silently used to infer physical bounds or
  edited during Gate 2.
- With the bundled default green QE and illuminant, only 684 filters cover 100%
  of the positive weighting domain; the median weight coverage is about 99.46%,
  while some specialized filters have little or no overlap. A metric without a
  coverage value can therefore be misleading.

These findings do not reclassify or modify the data submodule. They define the
diagnostics and edge cases Gate 2 must test.

## Recommended decisions

### G2-D001 — Units and normalization

**Recommendation**

- Use nanometres for wavelength.
- Store filter transmission and surface reflectance internally as fractions.
  Their physical calculation range is 0 through 1.
- Store QE internally as percent from 0 through 100 for v1, matching the
  bundled files and the current `/ 100` calculation convention.
- Store illuminants as non-negative relative spectral distributions. Preserve
  their declared basis and normalization metadata; absolute scale is not
  required for normalized ratios.
- For legacy TSV files without unit metadata, infer `max <= 1` as fractional
  and `max > 1` as percent, and emit the inference in structured diagnostics.
  This preserves the bundled classification while eliminating the unexplained
  `1.5` boundary.
- Require an explicit unit choice for newly imported filter, reflectance, and QE
  data when the import workflow is hardened. Until that Gate 4 form change, the
  backend may use legacy inference only when it also returns a warning.
- Normalize units exactly once at the data boundary. Calculations must never
  guess units.

**Compatibility impact**

No bundled file falls in `(1, 1.5]`, so the pinned inventory retains its current
fraction/percent classification. Out-of-range physical values are handled by
G2-D003 rather than changing the source data.

**Required acceptance tests**

- Explicit fraction, percent, and QE-percent fixtures normalize once.
- Unitless values with maxima of 1.0, 1.2, 100, and above 100 produce the
  documented classification and diagnostics.
- Every bundled file reports its chosen unit interpretation.

### G2-D002 — Wavelength validation and interpolation

**Recommendation**

- Require finite numeric wavelength samples and at least two unique points.
- Stable-sort unsorted input into strictly ascending wavelength order and emit
  a warning containing the affected file. Do not reorder bundled files on disk.
- Reject duplicate wavelengths, including duplicates with identical values,
  because silently selecting or averaging samples invents an undocumented
  measurement policy.
- Treat non-finite spectral values as unknown samples. Preserve the affected
  region as `NaN`; do not replace it with zero or interpolate across it without
  an explicit future decision.
- Use linear interpolation onto the inclusive 300–1100 nm, 1 nm grid.
- Return `NaN` outside measured support by default. Constant endpoint extension
  is permitted only through an explicit extrapolation request, and every
  extrapolated sample must carry a mask used by charts and reports.
- Keep full floating-point precision in memory. Round only serialized or
  displayed values, with the chosen output precision stated at that boundary.

NumPy requires increasing sample coordinates for meaningful `numpy.interp`
results, while SciPy documents `interp1d` as a legacy interface. A small shared
linear-interpolation service should therefore use one documented implementation
rather than preserving two subtly different paths.

**Compatibility impact**

The pinned files are already ascending and have no duplicate wavelengths.
Imports with malformed coordinates will change from permissive or undefined
behavior to actionable rejection. Existing non-finite value regions remain
unknown rather than being silently filled.

**Required acceptance tests**

- Ascending, descending, duplicate, non-finite, short-range, and explicit
  extrapolation fixtures.
- Loader and importer return identical results for the same valid spectrum.
- Extrapolation masks and measured-domain boundaries survive cache round trips.

### G2-D003 — Raw measurements and physical calculation values

**Recommendation**

- Preserve normalized source values, including small negative and above-one
  excursions, as raw measurement data for traceability.
- Derive a separate physical calculation curve by clipping finite transmission
  and reflectance values to `[0, 1]`.
- Emit file-level diagnostics with the number, original range, and wavelengths
  of clipped samples. Do not rewrite the bundled TSV.
- Preserve `NaN` as unknown. Clipping must not turn `NaN` into zero.
- Charts may offer raw-versus-physical views later; Gate 2 should use physical
  values for stacks, stops, sensor response, and reflector simulation while
  retaining raw values in the loaded model or diagnostic record.

**Compatibility impact**

Most results remain unchanged. Filters containing negative values or values
above 100% will change only at affected wavelengths, with an explicit
compatibility-delta fixture and diagnostic.

**Required acceptance tests**

- Negative, zero, unity, above-unity, and `NaN` fixtures.
- Raw values are recoverable; physical values remain within `[0, 1]`.
- The bundled validation report lists every clipped file and reason.

### G2-D004 — Filter stacking and overlap

**Recommendation**

- Multiply physical fractional transmissions wavelength-by-wavelength.
- Repeated filters use the same operation and therefore calculate `T ** count`.
- A combined sample is valid only when every stack member is finite at that
  wavelength. Any unknown member produces `NaN` rather than zero.
- Preserve true zero. Do not replace it with epsilon in the scientific result.
- Use the same stack function for single, active, repeated, and combined paths.
  Labels and display transforms may differ; numerical policy may not.

**Compatibility impact**

Valid in-range stack results remain unchanged. The current multi-filter-only
epsilon clip is removed, and out-of-range raw measurements use G2-D003's
physical curve consistently.

**Required acceptance tests**

- Identity, single, two-filter, repeated, zero, partial-overlap, and `NaN`
  propagation cases.
- Selection order does not affect a stack.
- Interactive charts and PNG reports consume the same combined array.

### G2-D005 — Effective transmission and stops

**Recommendation**

- Retain the current v1 weighting basis, but name it accurately:
  **Green-QE-weighted effective transmission** and **green-channel effective
  stops**. Do not call it photometric weighting or actual photon flux.
- Calculate on the common finite domain:

  `T_eff = sum(T_physical * illuminant_relative * QE_G) / sum(illuminant_relative * QE_G)`

- Require finite, non-negative illuminant and QE weights with a positive
  denominator. Otherwise return an unavailable result with a reason.
- Return weight coverage alongside every result:

  `coverage = sum(weight where transmission is finite) / sum(all positive weight)`

- A result with coverage below 100% remains available but must be labeled
  partial and show coverage. Zero coverage is unavailable. Gate 2 should not
  invent an arbitrary suppression threshold.
- Calculate `stops = -log2(T_eff)`. `T_eff == 0` yields positive infinity and is
  displayed as `∞`; epsilon is allowed only as a plotting limit, never as the
  scientific result.
- Do not create a combined RGB or exposure-meter metric until a supported sensor
  or metering model is specified.
- Do not multiply illuminant data by wavelength to claim photon conversion until
  each illuminant declares whether it represents spectral power or photon flux.

**Compatibility impact**

Positive, fully covered cases retain the current formula. Exact-zero cases
change from about 19.93 stops to infinity. Partial-domain results gain explicit
coverage and a more accurate name.

**Required acceptance tests**

- Analytic weighted average, zero, all-zero weights, negative weights, no
  overlap, and partial-overlap cases.
- Frozen current-versus-new deltas for representative bundled filters.
- Coverage is identical in interactive and exported metrics.

### G2-D006 — White balance

**Recommendation**

- Compute channel integrals over one common finite R/G/B/transmission/illuminant
  domain so channel ratios do not use different spectral supports.
- Keep green as the v1 reference channel.
- Name the current returned quantities `balance_divisors`, where
  `divisor[channel] = response[channel] / response[G]`.
- Also expose the actually applied multiplicative values as
  `balance_multipliers[channel] = 1 / divisor[channel]`.
- Apply the multipliers once. Do not alternate between multiplying and dividing
  values named “gains.”
- If green response is zero, any required channel is missing, or common support
  is empty, return an unavailable state with a reason rather than silent unity.
- Describe this as sensor-response neutralization, not calibrated scene or
  chromatic-adaptation white balance.

**Compatibility impact**

Valid current cases retain the same applied numerical correction. Names,
structured invalid states, and common-domain handling change.

**Required acceptance tests**

- Identity, unequal channel responses, missing channel, zero green, partial
  overlap, and one-time application cases.
- Divisors and multipliers are reciprocal within tolerance.

### G2-D007 — RGB response versus RGB display

**Recommendation**

- The calculation layer returns linear sensor-response curves and an unfloored
  RGB response matrix. Physical zero remains zero.
- Do not normalize scientific response arrays by their maximum.
- Channel visibility is presentation state only. It must not change white
  balance, mixer inputs, maximum response, metrics, or exported numeric data.
- Move normalization, auto-exposure, `[0, 1]` clipping, and integer conversion to
  a named display transform.
- Remove the `1/255` floor. A zero or hidden display channel renders black.
- Every display transform must state whether exposure is shared across a group
  or calculated independently.

**Compatibility impact**

Raw response curves become easier to compare and test. Preview pixels can change
where the current floor brightens zero channels or visibility changes mixer
inputs.

**Required acceptance tests**

- Zero/black, hidden channel, normalization, shared exposure, and export parity.
- Toggling chart visibility leaves all calculation outputs unchanged.

### G2-D008 — Channel mixer

**Recommendation**

- Apply the 3-by-3 matrix as an unclipped linear transform.
- Fix the processing order as: sensor response → optional white-balance
  multiplier → channel mixer → visibility/display transform.
- Keep finite negative and above-range mixed values in analytical output.
  Clamp them only when producing display pixels.
- Reject non-finite coefficients. Retain the current UI coefficient range for
  v1; changing that range is a separate UX decision.
- Identity, channel swaps, and matrix application must behave identically for
  response curves and reflector-response triplets.

**Compatibility impact**

Identity and ordinary swaps remain unchanged. Hidden-channel behavior and the
handling of negative or above-range previews become deterministic.

**Required acceptance tests**

- Identity, R/B swap, negative coefficient, above-unity coefficient, invalid
  coefficient, operation ordering, and calculation/display separation.

### G2-D009 — Reflector previews and color claims

**Recommendation**

- Name the output an **illustrative sensor-response preview**, not a calibrated
  color, colorimetric value, or sRGB prediction.
- Use the same validated transmission, illuminant, QE, white-balance, and mixer
  policies as the response calculations.
- Preserve relative brightness among the four vegetation reflectors by using one
  shared exposure transform for the 2-by-2 group.
- A single-reflector preview may use independent auto-exposure only when the UI
  labels that behavior; it must not be visually compared as absolute brightness
  with the vegetation group.
- Reflectance input must be fractional. Do not treat “absorption” as reflectance
  or assume `reflectance = 1 - absorption` without a measurement model. Absorption
  data remains ineligible for reflector preview until such a policy is approved.
- A future calibrated-color mode requires a CIE standard observer, declared
  illuminant basis, tristimulus integration, chromatic adaptation when needed,
  output color space, transfer function, and display mapping. That is outside
  Gate 2.

**Compatibility impact**

The four named leaf workflow remains. Labels and invalid-state behavior improve;
shared exposure preserves comparisons. No claim is made that current camera QE
triplets form a standard color space.

**Required acceptance tests**

- Four-leaf ordering, shared exposure, single-reflector exposure disclosure,
  missing reflector, zero response, channel swap, and absorption rejection.

### G2-D010 — Runtime and dependency policy

**Recommendation**

- Use Python 3.12 as the supported v1 reference runtime. Update documentation
  that currently claims Python 3.8 support. Broader Python support can be added
  only when the clean-install suite runs in that version.
- Record direct dependencies separately from a generated, exact constraint or
  lock file. Keep the existing Python/Streamlit/NumPy/Pandas/SciPy/Plotly/
  Matplotlib stack.
- Fix pandas 3 compatibility by requesting a writable NumPy copy at the loader
  boundary before normalization. Do not work around Copy-on-Write by forcing a
  shared array's writable flag.
- After the pandas fix and full clean-install verification, lock the versions
  used for v1 rather than retaining `pandas<3` as a permanent scientific policy.
- Keep pytest in development/test dependencies, not runtime dependencies.
- Make cache keys include source identity, source modification state, schema
  version, normalization policy version, and dependency-sensitive format
  version. Cache failures must emit diagnostics and fall back safely.

Python's `X | Y` union syntax is new in Python 3.10, so the current README's
Python 3.8 statement is already incorrect. Streamlit currently supports Python
3.10–3.14; Python 3.12 is recommended here because Gate 1 passed on 3.12.13 and
a single reference runtime minimizes v1 validation cost.

**Compatibility impact**

Supported setup becomes narrower but reproducible. Pandas 3 no longer causes
percentage-valued filters to disappear through the production loader's silent
failure boundary.

**Required acceptance tests**

- Clean Python 3.12 install from the lock/constraints file.
- All 1,566 bundled TSV classifications reconcile under the locked environment.
- pandas writable-copy regression, cache hit/miss/invalidation/corruption, and
  application startup smoke tests.

## Recommended Gate 2 implementation order after approval

1. **Data boundary:** G2-D001, D002, D003, and the pandas portion of D010.
   Re-run the full per-file audit and produce a compatibility-delta report.
2. **Scientific calculations:** G2-D004, D005, and D006. Update golden tests
   before changing each formula or invalid-state contract.
3. **Calculation/display separation:** G2-D007, D008, and D009 without redesigning
   controls or layout.
4. **Diagnostics and cache:** structured loader/import/cache outcomes and the
   remaining D010 constraints work.
5. **Gate review:** clean install, complete pytest suite, exact dataset
   reconciliation, application startup smoke test, and explicit review of every
   intentional difference from Gate 1.

Each slice should be independently reviewable and should stop if a bundled-data
exception cannot be explained without changing source data or scientific scope.

## Gate 2 exit criteria

- Every approved decision has an executable golden or edge-case test.
- Every discovered TSV is accepted, skipped, duplicate, or invalid with a file
  and reason; totals reconcile exactly.
- Raw measurements remain traceable and bundled TSV files are unchanged.
- Calculation arrays do not contain presentation floors or auto-exposure.
- Interactive and exported calculations share the same services and results.
- All differences from Gate 1 are listed with before/after fixtures and owner
  approval.
- The application installs and starts locally from the supported locked runtime.

## Explicitly not recommended

- Keeping the `max > 1.5` heuristic undocumented.
- Averaging conflicting duplicate wavelengths silently.
- Replacing unknown samples with zero.
- Applying epsilon to physical transmission merely to make logarithms finite.
- Letting channel-visibility toggles change calculations.
- Clipping or normalizing inside the channel mixer.
- Calling camera-QE triplets calibrated colorimetry.
- Editing bundled datasets as part of a loader or formula change.
- Expanding Gate 2 into UI modernization or new product infrastructure.

## Primary references

- [NumPy `interp` documentation](https://numpy.org/doc/stable/reference/generated/numpy.interp.html)
- [SciPy one-dimensional interpolation guidance](https://docs.scipy.org/doc/scipy/tutorial/interpolate/1D.html)
- [pandas Copy-on-Write and read-only NumPy arrays](https://pandas.pydata.org/pandas-docs/stable/user_guide/copy_on_write.html)
- [Python 3.10 union types](https://docs.python.org/3.10/library/stdtypes.html#union-type)
- [Streamlit installation and supported Python versions](https://docs.streamlit.io/get-started/installation/command-line)
- [CIE 015:2018, Colorimetry, 4th Edition](https://www.cie.co.at/publications/colorimetry-4th-edition)

## Approval record

The owner approved `G2-D001` through `G2-D010` as written on 2026-08-03. Gate 2
implementation is authorized within the scope and exclusions of this document.
