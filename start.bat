@echo off
setlocal
cd /d "%~dp0"
if "%FS_FILTERLAB_VENV_DIR%"=="" set "FS_FILTERLAB_VENV_DIR=%CD%\.venv"

if not exist "%FS_FILTERLAB_VENV_DIR%\Scripts\python.exe" (
  echo Python environment not found. Run install.bat first.
  exit /b 1
)
if not exist "data\filters_data" (
  echo Bundled filter data is missing. Restore data\ before launching.
  exit /b 1
)

"%FS_FILTERLAB_VENV_DIR%\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
if errorlevel 1 (
  echo FS FilterLab requires a Python 3.12 environment. Run install.bat again.
  exit /b 1
)
"%FS_FILTERLAB_VENV_DIR%\Scripts\python.exe" -c "import streamlit, numpy, pandas, plotly, matplotlib"
if errorlevel 1 exit /b 1
if "%~1"=="--check" (
  echo FS FilterLab launcher check: passed
  exit /b 0
)

"%FS_FILTERLAB_VENV_DIR%\Scripts\python.exe" -m streamlit run app.py %*
