#!/usr/bin/env bash
# SMALT Authorship: Full corpus launch (5x8 / 5x7 / 7x6)
set -e

echo "=== SMALT Authorship: Full corpus launch ==="

# --- Find SQL dump ---
SQL_DUMP=""
for f in smalt.sql.20260115.070144.gz ../smalt.sql.20260115.070144.gz \
          smalt.sql.20220421.112227.gz ../smalt.sql.20220421.112227.gz; do
    if [ -f "$f" ]; then
        SQL_DUMP="$f"
        break
    fi
done

if [ -z "$SQL_DUMP" ]; then
    echo ""
    echo "ERROR: SQL dump not found."
    echo "Put smalt.sql.20260115.070144.gz next to manage.py or one folder above."
    echo "For smoke launch only: bash run_smoke_authorship.sh"
    echo ""
    exit 1
fi
echo "Found dump: $SQL_DUMP"

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

echo "Loading all corpora from dump (this may take a minute)..."
echo "Note: features will be extracted on first experiment run via Natasha/Razdel."
python manage.py load_authorship_demo --corpus=all --source-sql="$SQL_DUMP" --no-extract --settings=shower.settings.demo

echo ""
echo "=== Corpora 5x8, 5x7, 7x6 loaded. ==="
echo "Run experiments from the web UI or via CLI:"
echo "  python manage.py run_authorship --list-name=\"Authorship corpus 5x8\" --method=profile --extract-features --queue --settings=shower.settings.demo"
echo "  python manage.py run_authorship --list-name=\"Authorship corpus 5x8\" --method=ml --queue --settings=shower.settings.demo"
echo ""

echo "Starting worker in background..."
python manage.py run_authorship_worker --settings=shower.settings.demo &
WORKER_PID=$!
echo "Worker PID: $WORKER_PID (stop with: kill $WORKER_PID)"

echo ""
echo "======================================================"
echo " Server starting at:"
echo " http://127.0.0.1:8000/research/authorship/"
echo "======================================================"
echo " First experiment will extract Natasha/Razdel features"
echo " (may take several minutes per corpus)."
echo " Press Ctrl+C to stop the server."
echo "======================================================"
echo ""
python manage.py runserver 0.0.0.0:8000 --settings=shower.settings.demo
