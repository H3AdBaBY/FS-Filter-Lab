@echo off
setlocal
cd /d "%~dp0"
if "%FS_FILTERLAB_VENV_DIR%"=="" set "FS_FILTERLAB_VENV_DIR=%CD%\.venv"

py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
if errorlevel 1 (
  echo FS FilterLab requires Python 3.12.
  exit /b 1
)

if not exist "data\filters_data" (
  where git >nul 2>nul
  if not errorlevel 1 git submodule update --init --recursive
)
if not exist "data\filters_data" (
  echo Bundled data is missing. Restore data\ or initialize the data submodule.
  exit /b 1
)

py -3.12 -m venv "%FS_FILTERLAB_VENV_DIR%"
if errorlevel 1 exit /b 1
"%FS_FILTERLAB_VENV_DIR%\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 exit /b 1
"%FS_FILTERLAB_VENV_DIR%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 exit /b 1

echo Installation complete. Launch with start.bat
