# FS FilterLab 1.0.0 release checklist

Status: **Gate 5 complete; v1.0.0 published**

Publication authority: **Granted by the owner and exercised on 2026-08-03**

## Automated candidate evidence

- [x] Complete Gate 4 command passes in Python 3.12.
- [x] Bundled audit reconciles 1,566 discovered and accepted TSV files with zero
  skipped, duplicate, or invalid entries.
- [x] Runtime dependency versions match constraints.
- [x] Runtime license inventory has no unresolved entry.
- [x] Application/data/vendor notices are present in both archives.
- [x] Two consecutive builds of each archive have identical SHA-256 hashes.
- [x] Archive manifest matches both extracted release trees.
- [x] Forbidden local state is absent from both archives.
- [x] Each extracted archive installs without Git metadata.
- [x] Non-loopback socket access is denied while localhost health succeeds.
- [x] Named filter workflow and current-state PNG pass from each archive form.
- [x] Gate 4 performance budgets pass on the reference machine.

Automated result recorded 2026-08-03 on macOS 26.5.2 arm64 with Python
3.12.13. Exact candidate hashes and build evidence are generated under ignored
`dist/` by the complete Gate 5 command.

## Manual keyboard smoke — completed

Record:

- Date: 2026-08-03
- Tester: Owner
- macOS version: 26.5.2, Apple Silicon
- Browser/version: Codex in-app browser (embedded browser version not exposed)
- Archive SHA-256:
  - `FS-Filter-Lab-1.0.0.tar.gz`:
    `cf37b42262df947822f1144fe3aa17c57e6f1dd5ad7dc1bab76a222a04ee3df0`
  - `FS-Filter-Lab-1.0.0.zip`:
    `1bd3334cebd2741d560e863cd8a9b8e31c0a98034169490e1795e2568c8db2d4`

Without using a pointer:

- [x] Open/close filter controls at 1280, 768, and 390 px.
- [x] Select and remove a named filter.
- [x] Change its stack count.
- [x] Complete advanced search Done and Cancel paths.
- [x] Navigate all four importer tabs and their labeled controls.
- [x] Toggle sensor-response balance and RGB visibility.
- [x] Enable, edit, and reset the channel mixer.
- [x] Select a surface and reach both preview captions.
- [x] Generate and activate the current report download.
- [x] Focus order is logical, focus is visible, and no keyboard trap occurs.

Result/blockers: **Passed.** The owner reported no keyboard blocker.

## Accessibility scope

Existing accessible labels, captions, contrast, focus structure, and keyboard
behavior remain product quality safeguards. Formal VoiceOver verification and
accessibility-conformance claims are outside the v1 scope and are not release
blockers.

## Owner gates

- [x] Owner accepts the dependency and data-provenance evidence.
- [x] Owner accepts `docs/Known-Limitations.md` and release notes.
- [x] Owner approves the exact candidate archives and checksums.
- [x] Owner separately approves the exact tag, remote, and assets before any
  tag, push, or GitHub release.

## Publication record

- Repository: `https://github.com/H3AdBaBY/FS-Filter-Lab`
- Release: `https://github.com/H3AdBaBY/FS-Filter-Lab/releases/tag/v1.0.0`
- Annotated tag: `v1.0.0`
- Tagged application commit:
  `12a5a7f9c3c8cc6e27863d631f6efc95c34404e9`
- Published assets: both approved archives and `SHA256SUMS`
- Remote audit: downloaded release assets passed the published SHA-256 checks
  after publication.
