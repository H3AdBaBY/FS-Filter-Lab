# Gate 5 implementation record

Status: **Gate 5A evidence implemented; Gate 5B tooling implemented with full
clean-tree verification pending**

Version: `1.0.0`

Publication authority: **Not granted**

## Approved boundary

The owner approved `G5-D001` through `G5-D012` as written. That approval
authorizes local Gate 5A release evidence and Gate 5B deterministic candidate
construction. It does not authorize a tag, push, GitHub release, or other
external publication. Gate 5C still requires the recorded manual keyboard and
macOS VoiceOver smoke, candidate approval, and separate publication approval.

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
- `docs/Release-Checklist.md` keeps manual accessibility and owner publication
  actions explicit and incomplete.

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

Construction results and exact artifact hashes will be recorded only after the
full clean-tree release command passes.
