# Gate 5 implementation record

Status: **Gate 5 complete; v1.0.0 published**

Version: `1.0.0`

Publication authority: **Granted by the owner and exercised on 2026-08-03**

## Approved boundary

The owner approved `G5-D001` through `G5-D012` as written. That approval
authorizes local Gate 5A release evidence and Gate 5B deterministic candidate
construction. It does not authorize a tag, push, GitHub release, or other
external publication. The owner subsequently approved the exact candidate and
reported the manual keyboard smoke passed on 2026-08-03. Separate publication
approval was then granted for the exact tag, repository, and assets. The
approved amendment makes formal VoiceOver verification and accessibility
conformance outside the v1 scope.

## Gate 5A evidence

- `VERSION` is the release-version source of truth.
- `.streamlit/config.toml` disables Streamlit usage statistics.
- `dependency-licenses.json` and `THIRD_PARTY_NOTICES.md` are deterministically
  generated from the exact installed Python 3.12 dependency set.
- Every runtime distribution has a classified license and retained license-file
  evidence. The Streamlit 1.60.0 Apache-2.0 license is retained locally because
  its installed wheel does not contain the license file named by the metadata.
- `docs/Data-Provenance.md` records the pinned bundled-data commit and exact
  corpus reconciliation without inventing missing per-curve attribution.
- `docs/Known-Limitations.md` is the authoritative product and scientific
  limitation record linked from release-facing documentation.
- `docs/Release-Checklist.md` records the completed manual keyboard and exact
  candidate acceptance while keeping external publication approval explicit
  and incomplete.
- macOS Apple Silicon is the sole supported platform. Windows launchers and
  Linux/Windows compatibility claims are excluded; other platforms are
  unsupported without being deliberately blocked in code.

## Gate 5B tooling

- `scripts/release_candidate.py` builds populated ZIP and tar.gz candidates
  from an explicit allowlist, normalizes ordering, timestamps, and modes, and
  embeds a manifest covering every other regular file.
- Safe verification rejects traversal, unsupported archive members, manifest
  drift, forbidden local state, incorrect modes, and any bundled TSV count
  other than 1,566.
- `scripts/offline_guard/sitecustomize.py` is opt-in test instrumentation that
  denies non-loopback name resolution and connections while permitting
  localhost and local Unix sockets. It does not alter normal application runs.
- `scripts/run_gate5_release.sh` is the one complete command. It builds each
  archive twice, verifies identical hashes, then installs and exercises both
  extracted forms before atomically replacing ignored `dist/` candidates.

## Automated verification result

The complete command passed on 2026-08-03 using Python 3.12.13 on the reference
arm64 Mac running macOS 26.5.2. Evidence included:

- 64 deterministic tests and the complete Gate 4 launcher/workflow matrix;
- 1,566 discovered and accepted bundled TSV files, with zero skipped,
  duplicate, or invalid entries;
- 48 exact runtime distributions and four test-only distributions with zero
  unresolved runtime licenses;
- two consecutive byte-identical builds of each archive form;
- manifest, checksum, mode, forbidden-path, and populated-data verification for
  both extracted forms;
- independent runtime installation, `pip check`, dataset audit, non-loopback
  denial, localhost health, named filter/PNG workflow, and Gate 4 interactions
  from both the tar.gz and ZIP candidates;
- every recorded Gate 3 and Gate 4 performance measurement below its approved
  budget.

The command writes the exact candidate hashes and machine-readable environment
record to ignored `dist/SHA256SUMS` and `dist/release-evidence.json`. The owner
accepted those exact hashes and reported the manual keyboard smoke passed on
2026-08-03. Gate 5C local acceptance is therefore complete. VoiceOver
verification is not a release gate.

After separate owner authorization, the completed branch and annotated
`v1.0.0` tag were pushed to `H3AdBaBY/FS-Filter-Lab`. The tag resolves to the
recorded application commit
`12a5a7f9c3c8cc6e27863d631f6efc95c34404e9`. GitHub release `v1.0.0` contains
the exact approved tar.gz, ZIP, and `SHA256SUMS`; downloading those published
assets and checking the published hashes passed.
