# FS FilterLab

A web-based tool for analyzing and visualizing optical filter stacks, quantum efficiency curves, and illuminant spectra. Built with focus on Full-Spectrum photography. 

Credit: 21.09.2025 Refactor based on 01luna's fork. Contains Vegetation Color Preview feature she created

## Features

- Combine multiple filters and see the resulting transmission
- View and compare RGB channel responses
- Analyze how filters affect different cameras and light sources
- Import your own filter, QE, or illuminant data (TSV format)
- Export analysis as PNG images
- Search and filter by manufacturer, color, or wavelength
- Simple caching for faster data loading

## Quick Start

### Requirements
- Python 3.12
- pip

### Install

1. Clone this repository,
   Or download the latest Release   
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Or use `install.bat` (Windows) or `install.sh` (Linux/macOS).

   The direct dependencies are resolved through `constraints-py312.txt`, the
   exact environment verified for the v1 scientific baseline.
3. Run the app:
   ```bash
   streamlit run app.py
   ```
   Or use `start.bat` (Windows) or `run.sh` (Linux/macOS).
4. Open your browser to [http://localhost:8501](http://localhost:8501)

## How to Use

1. Select filters from the sidebar
2. Adjust stack counts if needed
3. Pick a camera QE profile and an illuminant
4. See the results in the main area (charts, numbers, etc.)
5. Download a PNG report if you want

### Advanced
- Use "Advanced Search" to filter by manufacturer, color, or transmission at a specific wavelength
- Import your own data in the sidebar (TSV files)
- Rebuild the cache if you add new data files


## Project Structure

```
FS-FilterLab/
├── app.py
├── requirements.txt
├── install.bat / install.sh
├── start.bat / run.sh
├── models/         # Data models
├── services/       # Data processing and logic
├── views/          # UI components
├── data/           # Your spectral data files
└── cache/          # Auto-generated cache
```

## Basic Troubleshooting

- Delete .venv, then run install.bat/.sh to re-install dependencies
- Use "Rebuild Cache" in the sidebar if you add or change data files. Alternatively, manually delete the /cache folder

## Scientific baseline

Run the complete deterministic suite, including all 1,566 bundled TSV files:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate1_baseline.sh
```

The calculations capture approved FS FilterLab policies; reflector previews are
illustrative sensor responses, not calibrated color predictions.

For the complete Gate 2 clean-install, scientific-suite, dataset-audit, cache,
and application-startup verification:

```bash
PYTHON_BIN=python3.12 bash scripts/run_gate2_verification.sh
```

## License

MIT License. See LICENSE file.

---
