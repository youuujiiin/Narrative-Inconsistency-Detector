@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo AI environment setup
echo ========================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    pause
    exit /b 1
)

if not exist .venv (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto :error
) else (
    echo [1/3] .venv already exists. Skipping creation.
)

echo [2/3] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 goto :error

echo [3/3] Installing dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist .env (
    copy /Y .env.example .env >nul
    echo.
    echo Created .env from .env.example.
    echo Add your ANTHROPIC_API_KEY to .env before using Claude API.
)

echo.
echo Setup complete.
echo To activate later in PowerShell:
echo   .\.venv\Scripts\Activate.ps1
pause
exit /b 0

:error
echo.
echo [ERROR] Setup failed.
pause
exit /b 1
