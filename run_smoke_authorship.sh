#!/usr/bin/env bash
# SMALT Authorship: Smoke launch (3x4 corpus)
set -e

echo "=== SMALT Authorship: Smoke launch ==="

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.11+." >&2
    exit 1
fi

[ -d .venv ] || python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate

pip install -r requirements.txt --quiet

python manage.py check --settings=shower.settings.demo
python manage.py migrate --settings=shower.settings.demo
python manage.py load_authorship_demo --settings=shower.settings.demo

echo "Starting worker in background..."
python manage.py run_authorship_worker --settings=shower.settings.demo &
WORKER_PID=$!
echo "Worker PID: $WORKER_PID (stop with: kill $WORKER_PID)"

echo ""
echo "======================================================"
echo " Server starting at:"
echo " http://127.0.0.1:8000/research/authorship/"
echo "======================================================"
echo " Open the URL above, click Profile or ML to run"
echo " an experiment. Worker executes it in background."
echo " Press Ctrl+C to stop the server."
echo "======================================================"
echo ""
python manage.py runserver 0.0.0.0:8000 --settings=shower.settings.demo
