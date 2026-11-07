@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo Muvi needs uv. Install it from https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)
uv run --locked muvi serve --open
if errorlevel 1 pause
endlocal
