# Gate 5 implementation record

Status: **Gate 5A evidence implemented; Gate 5B candidate work pending**

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

Gate 5B construction results and exact artifact hashes will be appended only
after the full release command passes.
