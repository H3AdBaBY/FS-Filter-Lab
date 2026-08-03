# Third-party notices

FS FilterLab does not bundle a Python runtime or dependency wheels. The
installer obtains the exact distributions constrained by
`constraints-py312.txt`. Their license files remain in each installed
distribution and are identified below by path and SHA-256.

This is a deterministic engineering inventory, not legal advice.

## Runtime dependencies

| Distribution | Version | Direct | License | Installed license files |
|---|---:|:---:|---|---:|
| altair | 6.2.2 | No | BSD-3-Clause | 1 |
| anyio | 4.14.2 | No | MIT | 1 |
| attrs | 26.1.0 | No | MIT | 1 |
| blinker | 1.9.0 | No | MIT | 1 |
| certifi | 2026.7.22 | No | MPL-2.0 | 1 |
| charset-normalizer | 3.4.9 | No | MIT | 1 |
| click | 8.4.2 | No | BSD-3-Clause | 1 |
| contourpy | 1.3.3 | No | BSD-3-Clause | 1 |
| cycler | 0.12.1 | No | BSD-3-Clause | 1 |
| fonttools | 4.63.0 | No | MIT | 2 |
| gitdb | 4.0.12 | No | BSD-3-Clause | 1 |
| GitPython | 3.1.57 | No | BSD-3-Clause | 2 |
| h11 | 0.16.0 | No | MIT | 1 |
| httptools | 0.8.0 | No | MIT | 3 |
| idna | 3.18 | No | BSD-3-Clause | 1 |
| itsdangerous | 2.2.0 | No | BSD-3-Clause | 1 |
| Jinja2 | 3.1.6 | No | BSD-3-Clause | 1 |
| jsonschema | 4.26.0 | No | MIT | 1 |
| jsonschema-specifications | 2025.9.1 | No | MIT | 1 |
| kiwisolver | 1.5.0 | No | BSD-3-Clause | 1 |
| MarkupSafe | 3.0.3 | No | BSD-3-Clause | 1 |
| matplotlib | 3.11.1 | Yes | PSF-2.0 | 3 |
| narwhals | 2.24.0 | No | MIT | 1 |
| numpy | 2.5.1 | Yes | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 20 |
| packaging | 26.2 | No | Apache-2.0 OR BSD-2-Clause | 7 |
| pandas | 3.0.5 | Yes | BSD-3-Clause | 1 |
| pillow | 12.3.0 | No | MIT-CMU | 1 |
| plotly | 6.9.0 | Yes | MIT | 1 |
| protobuf | 7.35.1 | No | BSD-3-Clause | 1 |
| pyarrow | 24.0.0 | No | Apache-2.0 | 2 |
| pydeck | 0.9.3 | No | Apache-2.0 | 1 |
| pyparsing | 3.3.2 | No | MIT | 1 |
| python-dateutil | 2.9.0.post0 | No | Apache-2.0 OR BSD-3-Clause | 1 |
| python-multipart | 0.0.32 | No | Apache-2.0 | 1 |
| referencing | 0.37.0 | No | MIT | 1 |
| requests | 2.34.2 | No | Apache-2.0 | 2 |
| rpds-py | 2026.6.3 | No | MIT | 1 |
| scipy | 1.18.0 | Yes | BSD-3-Clause | 5 |
| six | 1.17.0 | No | MIT | 1 |
| smmap | 5.0.3 | No | BSD-3-Clause | 1 |
| starlette | 1.3.1 | No | BSD-3-Clause | 1 |
| streamlit | 1.60.0 | Yes | Apache-2.0 | 1 |
| tenacity | 9.1.4 | No | Apache-2.0 | 1 |
| toml | 0.10.2 | No | MIT | 1 |
| typing_extensions | 4.16.0 | No | PSF-2.0 | 1 |
| urllib3 | 2.7.0 | No | MIT | 1 |
| uvicorn | 0.52.1 | No | BSD-3-Clause | 1 |
| websockets | 16.1.1 | No | BSD-3-Clause | 1 |

## Test-only dependencies

These are used to audit the released source and are not required to
run the application.

| Distribution | Version | Direct | License | Installed license files |
|---|---:|:---:|---|---:|
| iniconfig | 2.3.0 | No | MIT | 1 |
| pluggy | 1.6.0 | No | MIT | 1 |
| Pygments | 2.20.0 | No | BSD-2-Clause | 2 |
| pytest | 9.1.1 | Yes | MIT | 1 |

The machine-readable `dependency-licenses.json` records canonical
names, exact versions, project URLs, installed license-file paths, and
license-file hashes. Regenerate both files only from the pinned Python
3.12 environment with `python scripts/generate_dependency_notices.py`.
