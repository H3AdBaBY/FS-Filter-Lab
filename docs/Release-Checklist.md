# FS FilterLab 1.0.0 release checklist

Status: **Gate 5A/Gate 5B implementation in progress**

Publication authority: **Not granted**

## Automated candidate evidence

- [ ] Complete Gate 4 command passes in Python 3.12.
- [ ] Bundled audit reconciles 1,566 discovered and accepted TSV files with zero
  skipped, duplicate, or invalid entries.
- [ ] Runtime dependency versions match constraints.
- [ ] Runtime license inventory has no unresolved entry.
- [ ] Application/data/vendor notices are present in both archives.
- [ ] Two consecutive builds of each archive have identical SHA-256 hashes.
- [ ] Archive manifest matches both extracted release trees.
- [ ] Forbidden local state is absent from both archives.
- [ ] Each extracted archive installs without Git metadata.
- [ ] Non-loopback socket access is denied while localhost health succeeds.
- [ ] Named filter workflow and current-state PNG pass from each archive form.
- [ ] Gate 4 performance budgets pass on the reference machine.

## Manual keyboard smoke — required

Record:

- Date:
- Tester:
- macOS version:
- Browser/version:
- Archive SHA-256:

Without using a pointer:

- [ ] Open/close filter controls at 1280, 768, and 390 px.
- [ ] Select and remove a named filter.
- [ ] Change its stack count.
- [ ] Complete advanced search Done and Cancel paths.
- [ ] Navigate all four importer tabs and their labeled controls.
- [ ] Toggle sensor-response balance and RGB visibility.
- [ ] Enable, edit, and reset the channel mixer.
- [ ] Select a surface and reach both preview captions.
- [ ] Generate and activate the current report download.
- [ ] Focus order is logical, focus is visible, and no keyboard trap occurs.

Result/blockers:

## macOS VoiceOver smoke — required

Using the same environment and archive:

- [ ] Open/Close filter controls are announced clearly at narrow width.
- [ ] Headings and control groups convey the visual workflow structure.
- [ ] Filter selection and advanced search are understandable and operable.
- [ ] Import controls expose type, quantity, unit, and extrapolation labels.
- [ ] Balance, mixer, visibility, and surface controls expose their state.
- [ ] Charts expose titles/axes/traces and nearby metric summaries.
- [ ] Warnings, errors, zero states, and preview limitations are announced.
- [ ] Report generation and download are understandable and operable.
- [ ] No blocker prevents completing the named workflow.

Result/blockers:

## Owner gates

- [ ] Owner accepts the dependency and data-provenance evidence.
- [ ] Owner accepts `docs/Known-Limitations.md` and release notes.
- [ ] Owner approves the exact candidate archives and checksums.
- [ ] Owner separately approves the exact tag, remote, and assets before any
  tag, push, or GitHub release.
