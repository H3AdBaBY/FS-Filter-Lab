# Known limitations

These limitations define the FS FilterLab 1.0.0 release boundary.

## Scientific model

- Analysis uses the fixed 300–1100 nm grid at 1 nm intervals and the approved
  interpolation, support, unit, clipping, and extrapolation policies documented
  by the Gate 2 decision record.
- The bundled library contains 1,558 filters, 3 camera QE profiles, 1
  illuminant, and 4 reflector spectra. It is not a comprehensive catalog.
- Effective stops use the approved illuminant and green-QE weighting. This is a
  documented model, not a universal camera-exposure standard.
- Sensor-response balance and the 3×3 mixer operate on linear analytical
  responses. They are not camera profiling or color management.
- Vegetation and selected-surface patches are illustrative sensor responses,
  not calibrated color or predictions of a photograph.
- Absorption is not converted to reflectance because no measurement model is
  approved.
- CSV imports require explicit quantities and units. Constant filter or
  reflectance extrapolation occurs only when separately enabled for the lower
  or upper domain.
- Tests capture approved behavior and regression expectations; they do not
  certify undocumented scientific correctness or fitness for a purpose.

## Bundled data

- Bundled curves are reformatted reference data, not official manufacturer or
  standards-body documentation.
- Per-curve sources and attributions may be incomplete, inaccurate, or out of
  date. Inclusion implies no endorsement.
- The 1,566-file audit proves structural reconciliation, not measurement
  accuracy, provenance, authorization, or suitability.
- See [Data-Provenance.md](Data-Provenance.md) and the preserved data/vendor
  notices for the complete release statement.

## Installation and platforms

- Python 3.12 is required. Dependency installation may require access to the
  configured Python package index; offline dependency installation is not
  promised.
- Normal use is local and offline after dependencies are installed. Streamlit
  usage statistics are disabled in the release configuration.
- The verified platform is macOS on the 2020 M1 MacBook Air reference machine.
  Linux is expected/best effort. Windows 10/11 launchers are experimental until
  the exact release archive completes a native Windows smoke.
- Delivery is a Python/Streamlit source application that starts a localhost
  server. It is not a native, signed, or notarized desktop application.

## Accessibility and product boundary

- Automated labels, focus structure, contrast, captions, and responsive layouts
  have been checked. The stable release still requires the recorded manual
  keyboard and macOS VoiceOver workflow in the release checklist.
- The application has no hosting, accounts, database, collaboration, analytics,
  telemetry, RAW decoding, image-development pipeline, or automatic updater.
- Imported spectra, generated caches, and reports are local files. Users are
  responsible for backups and for the rights and accuracy of imported data.

The software and data are supplied under their included licenses without
warranty. This document is product documentation, not legal advice.
