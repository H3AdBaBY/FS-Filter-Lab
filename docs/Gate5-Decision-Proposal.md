# Gate 5 release decision proposal

Status: **Approved and amended for macOS Apple Silicon-only support**

Prerequisites: Gate 2 scientific policies, Gate 3 vertical workflow, and Gate 4
parity implementation complete

Scope: FS FilterLab only

## Purpose

Gate 5 turns the verified local application into an inspectable release
candidate. It does not add product features, scientific formulas, hosting,
accounts, telemetry, RAW functionality, a framework rewrite, or a native app.

The release audit found:

1. The current lineage is `V0.5.1-Beta` plus ten modernization commits; there
   is no current version source inside the application.
2. The application and bundled-data repository contain MIT licenses, but the
   upstream data notice explicitly says per-dataset attribution may be
   incomplete or out of date.
3. Some vendor folders carry source notices while others do not; bundled curves
   are reformatted reference data and are not official manufacturer documents.
4. Exact Python 3.12 dependencies are constrained, but Python package license
   metadata is inconsistent and sometimes reports `UNKNOWN` or an entire
   multi-license text. A release notice must use installed distribution license
   files, not metadata fields alone.
5. The application code has no explicit external network client. Streamlit
   usage statistics should nevertheless be disabled in release configuration
   so the offline/privacy promise is unambiguous.
6. The verified delivery form is a local Python/Streamlit source application.
   Creating a native executable, installer, signed bundle, or notarized macOS
   application would be a new packaging project.
7. macOS Apple Silicon is the only reference platform exercised end to end and
   is the sole supported v1 platform. Intel macOS, Linux, Windows, and other
   platforms are unsupported; the release does not deliberately prevent the
   source from running elsewhere.
8. All automated Gate 4 evidence is green. A physical keyboard usability smoke
   remains required. Formal VoiceOver verification and accessibility
   conformance are outside the v1 scope.

## Recommended decisions

### G5-D001 — Deliver Gate 5 as three bounded release slices

Implement and review in order:

1. **Gate 5A — Release evidence:** version source, notices, known limitations,
   dependency/data license inventory, offline configuration, and release
   checklist.
2. **Gate 5B — Candidate construction:** deterministic archive builder,
   manifest/checksums, clean extracted-archive verification, and final
   performance/evidence report.
3. **Gate 5C — Acceptance and publication:** manual keyboard result, owner
   inspection of the candidate, final approval, tag, and optional GitHub
   publication.

Approval of this sheet authorizes Gate 5A and Gate 5B local repository work. It
does **not** authorize a tag, push, GitHub release, or other external
publication; those require the separate `G5-D012` approval point.

### G5-D002 — Name the first hardened release `v1.0.0`

- Use SemVer spelling `v1.0.0` for the Git tag and `1.0.0` inside artifacts.
- Add a plain `VERSION` file as the release-version source of truth.
- Name archives `FS-Filter-Lab-1.0.0.tar.gz` and
  `FS-Filter-Lab-1.0.0.zip`.
- Record the application commit, data-submodule commit, Python version, and
  constraint-file SHA-256 in the release manifest.
- Do not silently derive a version from the older beta tag during runtime.

This marks completion of the approved v1 modernization boundary, not a claim
that every upstream data curve or scientific assumption has been independently
certified.

### G5-D003 — Release populated source archives, not a packaged executable

Both archives contain the same release tree:

- application source, macOS shell launchers, requirements, constraints, and
  `VERSION`;
- populated bundled `data/`, including its license and vendor notices;
- README, usage/technical documentation, changelog, known limitations,
  third-party notices, and application license;
- deterministic tests, synthetic fixtures, and verification scripts so the
  released source can be independently audited.

Exclude:

- `.git`, `.gitmodules`, worktrees, caches, virtual environments, user data,
  imported data, generated reports, test caches, editor state, and local logs;
- developer-only planning proposals and transient release-candidate output;
- dependency wheels or a prebuilt Python runtime.

Installation may require package access. After dependencies are installed, the
application must operate locally without external services.

### G5-D004 — Support macOS Apple Silicon only

- **Supported and verified:** macOS Apple Silicon on the reference 2020 M1
  MacBook Air, Python 3.12.
- **Unsupported:** Intel macOS, Linux, Windows, and all other platforms.
- Remove Windows batch launchers and do not publish Linux or Windows
  compatibility claims.
- Do not deliberately add an operating-system block; the source may happen to
  run elsewhere without creating a support commitment.
- Browser support follows the current Streamlit-supported modern browser set;
  no browser-specific compatibility guarantee is added.

This defines a narrow support contract around the product's intended and
verified environment.

### G5-D005 — Make local/offline and privacy behavior testable

- Add release Streamlit configuration with usage statistics disabled.
- No analytics, telemetry, account, cloud, update-check, or remote-data call is
  added.
- Verify the extracted release with non-loopback socket access denied after the
  dependency environment is installed; localhost browser/server traffic remains
  allowed.
- Document that dependency installation is not guaranteed offline and may use
  the configured package index.
- Imported spectra, cache files, and reports remain local to their documented
  paths.

### G5-D006 — Generate dependency notices from the installed release environment

- Inventory every installed runtime distribution and exact version, including
  transitive dependencies.
- Resolve each distribution's license from its installed license/notice files;
  metadata is only a cross-check.
- Produce a human-readable `THIRD_PARTY_NOTICES.md` and a deterministic
  machine-readable `dependency-licenses.json`.
- Every runtime dependency must have a classified license and retained notice
  before release; unresolved or incompatible terms block Gate 5.
- Test-only dependencies are listed separately and are not represented as
  shipped runtime components.
- This is an engineering license inventory, not legal advice.

### G5-D007 — Accept incomplete per-dataset provenance only as a prominent limitation

- Preserve the application MIT license, bundled-data MIT license, all vendor
  notice files, and the upstream factual-data disclaimer verbatim.
- Add a release data-provenance notice stating that curves were reformatted
  from public manufacturer, research, or standards graphs/tables; may be
  incomplete or outdated; are not official documentation; and imply no
  endorsement.
- Do not invent a source URL or attribution for an individual TSV.
- The exact 1,566-file validation proves structural acceptance, not provenance,
  accuracy, authorization, or fitness for a purpose.
- Owner approval of this decision accepts provenance incompleteness for the v1
  source release. Any legal requirement for complete per-curve provenance
  blocks release and requires a separate data-remediation project.

### G5-D008 — Publish one authoritative known-limitations document

`docs/Known-Limitations.md` must cover at least:

- fixed 300–1100 nm, 1 nm analytical grid and approved interpolation policies;
- limited bundled QE, illuminant, and reflector collections;
- illustrative sensor-response previews are not calibrated color;
- no conversion from absorption to reflectance;
- imported CSV quantity/unit/domain requirements and explicit extrapolation;
- bundled curves are reference data, not official manufacturer specifications;
- incomplete per-dataset provenance and no endorsement;
- Python 3.12 and the macOS Apple Silicon-only support boundary;
- dependency installation may require internet access, while normal use is
  local/offline;
- local Streamlit application delivery, not a native signed/notarized app;
- current accessibility verification status;
- no hosting, accounts, collaboration, telemetry, RAW processing, or warranty
  of scientific correctness.

README and release notes link to this file rather than maintaining divergent
limitation lists.

### G5-D009 — Freeze the final release verification matrix

One command, proposed as:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate5_release.sh
```

must:

1. run the complete Gate 4 command and exact bundled-data reconciliation;
2. verify dependency and data license inventories have no unresolved entries;
3. build both archives from an allowlist with normalized ordering/timestamps;
4. emit a file manifest and SHA-256 checksums;
5. extract each archive into a fresh temporary directory;
6. install from the extracted archive, with no Git metadata available;
7. enforce non-loopback-offline runtime, launch Streamlit, and check localhost
   health;
8. run the named filter workflow and inspect a current-state PNG;
9. repeat Gate 4 performance measurements and report, not silently revise,
   budgets;
10. verify no cache, user data, output, environment, or report leaked into an
    archive;
11. leave final candidates under ignored `dist/` only after every check passes.

A failure removes partial candidates and leaves prior artifacts untouched.

### G5-D010 — Retain keyboard usability; make VoiceOver out of scope

- Gate 4 automated structure, contrast, captions, and 1280/768/390 responsive
  evidence remains required.
- Before `v1.0.0`, a person on the reference Mac must complete the primary
  workflow, advanced search, importer navigation, balance/mixer controls, and
  report download using Tab/Shift-Tab/Space/Enter without a pointer.
- Specifically confirm the narrow-window Open/Close filter-control focus
  behavior.
- Preserve existing accessible labels, captions, contrast, and semantic
  structure as low-cost quality safeguards.
- Formal VoiceOver verification and accessibility-conformance claims are
  outside the v1 release scope and do not block release.
- A keyboard blocker must be fixed and retested. Approval of this decision
  sheet does not itself count as the manual keyboard result.

### G5-D011 — Make candidate integrity auditable without promising universal reproducibility

- Normalize archive path ordering, file modes, and timestamps so repeated builds
  from the same commit on the reference environment are byte-identical.
- Generate `SHA256SUMS` for the archives and a manifest of every included file.
- Verify two consecutive reference-machine builds have identical hashes.
- Record tool and platform versions used to construct the candidate.
- Do not claim bit-for-bit reproduction on every operating system or archive
  implementation until independently demonstrated.
- No code signing or notarization applies to these source archives.

### G5-D012 — Separate candidate approval from external publication

Gate 5C has two explicit owner actions:

1. **Candidate approval:** owner accepts the final artifacts, checksums, known
   limitations, license/provenance report, manual keyboard result, and
   release notes.
2. **Publication approval:** owner separately authorizes the exact commit/tag,
   remote, and release assets to publish.

Only after both approvals may a worker:

- create the signed or annotated `v1.0.0` tag requested by the owner;
- push the approved branch/tag to the named remote;
- create a GitHub release and attach the exact approved archives/checksums.

If publication fails, do not rebuild assets under the same version. Preserve
the approved candidate, report the failure, and resume only with owner
direction. No automatic updater or rollback service is added.

## Acceptance matrix

| Area | Required evidence |
|---|---|
| Version | `VERSION`, archive names, manifest, tag proposal agree on 1.0.0 |
| Artifact contents | Allowlisted populated source tree; forbidden local state absent |
| Archive integrity | Two builds identical; manifest and SHA-256 checks pass |
| Scientific regression | Gate 4 suite and exact 1,566-file reconciliation pass |
| Workflow/export | Named filter path and current-state PNG pass from both extracts |
| Offline/privacy | Usage statistics disabled; non-loopback runtime denied; localhost works |
| Dependencies | Exact runtime versions and complete license/notice inventory |
| Data licensing | MIT/data/vendor notices retained; provenance limitation accepted |
| Known limitations | One authoritative document linked from README/release notes |
| Platforms | macOS Apple Silicon is the sole supported platform |
| Accessibility | Manual keyboard path passes; VoiceOver verification is out of scope |
| Performance | Approved Gate 4 budgets pass on the reference machine |
| Publication | Exact candidate and remote approved before any external mutation |

## Exit criteria

Gate 5 exits only when:

1. `G5-D001` through `G5-D012` are approved or amended by the owner.
2. Gate 5A and Gate 5B pass focused review in order.
3. Both final archives reproduce on the reference machine and pass extracted
   clean-install, offline, workflow, PNG, and performance verification.
4. Dependency licenses have no unresolved or incompatible entry.
5. The owner accepts the incomplete per-dataset provenance limitation.
6. Manual keyboard smoke has no blocker; VoiceOver verification is not a gate.
7. Known limitations and release notes match the verified product.
8. The exact candidate receives owner approval.
9. If publication is requested, the exact tag, remote, and assets receive a
   separate owner approval before mutation.

## Approval record

The owner approved `G5-D001` through `G5-D012` as written. This authorizes
local Gate 5A and Gate 5B implementation only. It does not authorize a tag,
push, GitHub release, or other external publication.

The owner subsequently approved a platform/accessibility amendment: macOS
Apple Silicon is the sole supported platform; Intel macOS, Linux, Windows, and
other platforms are unsupported; Windows launchers are removed; the manual
keyboard smoke remains required; and VoiceOver verification and formal
accessibility conformance are outside the v1 scope. This amendment supersedes
the original `G5-D004`, `G5-D010`, and related Gate 5 wording.

The owner subsequently reported the manual keyboard smoke passed, accepted the
exact candidate archives and checksums, and separately authorized publication.
The completed branch, annotated `v1.0.0` tag, and approved assets were published
to the owner's `H3AdBaBY/FS-Filter-Lab` fork on 2026-08-03.
