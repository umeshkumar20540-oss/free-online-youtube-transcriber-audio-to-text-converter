@echo off
title WhisperFlow - Faster-Whisper YouTube Transcriber
cd /d "%~dp0"

echo ===============================================================
echo  WhisperFlow: Faster-Whisper Local YouTube Transcriber
echo ===============================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found on your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/2] Verifying Python dependencies...
python -m pip install -r requirements.txt --quiet --no-warn-script-location

echo.
echo [2/2] Starting WhisperFlow Server and opening browser...
echo.
python main.py

pause
