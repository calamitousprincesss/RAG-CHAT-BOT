@echo off
REM RAGChatbot - one-click Windows setup (uv-powered)
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ===========================================
echo   RAGChatbot - one-click setup
echo ===========================================
echo.

REM 1) Install uv if missing (user-scope, no admin)
where uv >nul 2>nul
if errorlevel 1 (
  echo [1/4] Installing uv...
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
) else (
  echo [1/4] uv already installed.
)

REM 2) Install Python 3.12 (uv-managed)
echo [2/4] Ensuring Python 3.12...
uv python install 3.12

REM 3) Sync from pyproject.toml (creates .venv automatically)
echo [3/4] Syncing dependencies from pyproject.toml...
uv sync

REM 4) Copy env, seed KB, launch
if not exist ".env" copy .env.example .env >nul

echo [4/4] Seeding the knowledge base...
uv run python seed.py

echo.
echo ===========================================
echo   Setup complete. Launching app...
echo   Open http://127.0.0.1:5000
echo   Press Ctrl+C to stop.
echo ===========================================
echo.
uv run python public\index.py
