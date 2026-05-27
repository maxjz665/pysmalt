# SMALT Authorship Worker — PowerShell launcher
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force -ErrorAction SilentlyContinue

Write-Host "=== SMALT Authorship Worker (PowerShell) ===" -ForegroundColor Cyan
Write-Host "Polls the database every 5 seconds and executes queued experiments."
Write-Host ""

$activateScript = ".\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error ".venv not found. Run run_smoke_authorship.bat or run_full_authorship.bat first."
    Read-Host "Press Enter to exit"
    exit 1
}

& $activateScript

Write-Host "Worker started. Press Ctrl+C to stop." -ForegroundColor Green
Write-Host ""
python manage.py run_authorship_worker --settings=shower.settings.demo
