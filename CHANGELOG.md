# Changelog

## 1.0.0 — release candidate

FS FilterLab 1.0.0 completes the approved standalone v1 modernization from the
`V0.5.1-Beta` upstream lineage.

### Added

- deterministic pytest coverage for scientific calculations, data policy,
  workflow state, importers, reports, and product states;
- exact validation for all 1,566 bundled TSV files;
- separate atomic `user_data/` imports with explicit quantities, units,
  extrapolation, diagnostics, provenance, collision rejection, and reload;
- deterministic advanced search with Done/Cancel selection parity;
- one workflow snapshot shared by interactive plots, previews, metrics, and PNG
  reports;
- complete balance, channel-mixer, visibility, reflector-preview, responsive,
  launcher, and clean-environment verification;
- pinned Python 3.12 dependencies and local/offline release configuration.

### Changed

- scientific ambiguities now follow the approved Gate 2 policies for units,
  interpolation, duplicates, support, zero, non-finite values, and display
  boundaries;
- imported data no longer modifies bundled data;
- missing QE, illuminant, reflector, zero-response, and failure states are
  distinguished without fabricated scientific output;
- launchers separate installation from application startup.

### Compatibility and limitations

- reflector patches remain illustrative sensor responses, not calibrated color;
- bundled-data provenance may be incomplete and curves are not official
  manufacturer documentation;
- Python 3.12 is required; macOS Apple Silicon is the sole supported release
  platform, while Linux, Windows, and Intel macOS are unsupported;
- manual keyboard usability remains a release check; formal VoiceOver
  verification and accessibility conformance are outside the v1 scope;
- dependency installation may require package-index access, while normal use is
  local and Streamlit usage statistics are disabled;
- see [docs/Known-Limitations.md](docs/Known-Limitations.md).
