#!/bin/bash

set -e

APP_DIR=/var/www/pysmalt
cd $APP_DIR

source venv/bin/activate
python manage.py run_authorship_worker
