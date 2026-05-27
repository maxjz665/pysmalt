@echo off
chcp 65001 >nul
echo === SMALT Authorship Worker ===
echo Polls the database every 5 seconds and executes queued experiments.
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: .venv not found.
    echo Run run_smoke_authorship.bat or run_full_authorship.bat first
    echo to create the environment.
    pause & exit /b 1
)

call .venv\Scripts\activate.bat
echo Worker started. Press Ctrl+C to stop.
echo.
python manage.py run_authorship_worker --settings=shower.settings.demo
pause
