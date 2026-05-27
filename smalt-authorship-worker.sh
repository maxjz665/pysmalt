#!/usr/bin/env bash
# Standalone SMALT Authorship Worker launcher (Linux/macOS)
set -e

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "ERROR: .venv not found. Run run_smoke_authorship.sh or run_full_authorship.sh first." >&2
    exit 1
fi

# shellcheck source=/dev/null
source .venv/bin/activate

echo "=== SMALT Authorship Worker ==="
echo "Polls the database every 5 seconds and executes queued experiments."
echo "Press Ctrl+C to stop."
echo ""
python manage.py run_authorship_worker --settings=shower.settings.demo
