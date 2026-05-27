@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo === SMALT Authorship: Full corpus launch (5x8 / 5x7 / 7x6) ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ and add it to PATH.
    pause & exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 ( echo ERROR: venv creation failed. & pause & exit /b 1 )
)

call .venv\Scripts\activate.bat

echo Installing / updating dependencies...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 ( echo ERROR: pip install failed. & pause & exit /b 1 )

:: --- Find SQL dump (single loop with delayed expansion) ---
set SQL_DUMP=
for %%f in (
    "smalt.sql.20260115.070144.gz"
    "..\smalt.sql.20260115.070144.gz"
    "smalt.sql.20220421.112227.gz"
    "..\smalt.sql.20220421.112227.gz"
) do (
    if "!SQL_DUMP!"=="" if exist %%f set SQL_DUMP=%%~f
)

if "!SQL_DUMP!"=="" (
    echo.
    echo ERROR: SQL dump not found.
    echo Put smalt.sql.20260115.070144.gz next to manage.py or one folder above.
    echo For smoke launch only (no dump needed): run_smoke_authorship.bat
    echo.
    pause & exit /b 1
)
echo Found dump: !SQL_DUMP!
echo.

echo Running Django system check...
python manage.py check --settings=shower.settings.demo
if errorlevel 1 ( echo ERROR: Django check failed. & pause & exit /b 1 )

echo Running migrations...
python manage.py migrate --settings=shower.settings.demo

echo Loading all corpora from dump (this may take a minute)...
echo Note: features are NOT extracted here -- they will be extracted
echo       on first experiment run via Natasha/Razdel (takes a few minutes).
python manage.py load_authorship_demo --corpus=all --source-sql="!SQL_DUMP!" --no-extract --settings=shower.settings.demo
if errorlevel 1 ( echo ERROR: corpus loading failed. & pause & exit /b 1 )

echo.
echo === Corpora 5x8, 5x7, 7x6 loaded. ===
echo.
echo Run experiments from the web UI or via CLI:
echo   python manage.py run_authorship --list-name="Authorship corpus 5x8" --method=profile --extract-features --queue --settings=shower.settings.demo
echo   python manage.py run_authorship --list-name="Authorship corpus 5x8" --method=ml --queue --settings=shower.settings.demo
echo.

echo Starting worker in a separate window...
start "SMALT Authorship Worker" cmd /k "cd /d %CD% && call .venv\Scripts\activate.bat && python manage.py run_authorship_worker --settings=shower.settings.demo"

echo.
echo ====================================================
echo  Server starting at:
echo  http://127.0.0.1:8000/research/authorship/
echo ====================================================
echo  First experiment will extract Natasha/Razdel features
echo  (may take several minutes per corpus).
echo  Press Ctrl+C here to stop the server.
echo ====================================================
echo.
python manage.py runserver --settings=shower.settings.demo
endlocal
