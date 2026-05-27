@echo off
chcp 65001 >nul
echo === SMALT Authorship: Smoke launch (3x4 corpus) ===
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

echo Running Django system check...
python manage.py check --settings=shower.settings.demo
if errorlevel 1 ( echo ERROR: Django check failed. & pause & exit /b 1 )

echo Running migrations...
python manage.py migrate --settings=shower.settings.demo

echo Loading smoke corpus (3 authors x 4 texts)...
python manage.py load_authorship_demo --settings=shower.settings.demo

echo.
echo Starting worker in a separate window...
echo (Worker executes queued Profile/ML experiments)
start "SMALT Authorship Worker" cmd /k "cd /d %CD% && call .venv\Scripts\activate.bat && python manage.py run_authorship_worker --settings=shower.settings.demo"

echo.
echo ====================================================
echo  Server starting at:
echo  http://127.0.0.1:8000/research/authorship/
echo ====================================================
echo  Open the URL above, click Profile or ML to run
echo  an experiment. Worker will execute it in the
echo  background window.
echo  Press Ctrl+C here to stop the server.
echo ====================================================
echo.
python manage.py runserver --settings=shower.settings.demo
