# PowerShell Launcher for WhisperFlow Transcriber
$ErrorActionPreference = "Stop"

Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host " WhisperFlow: Faster-Whisper Local YouTube Transcriber" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host ""

try {
    $pythonVersion = python --version 2>&1
    Write-Host "[1/2] Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python was not found on your system PATH." -ForegroundColor Red
    Exit 1
}

Write-Host "[2/2] Launching WhisperFlow Server..." -ForegroundColor Yellow
python main.py
