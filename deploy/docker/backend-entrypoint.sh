#!/usr/bin/env bash
set -euo pipefail

cd /app

mkdir -p backend/database backend/uploads backend/uploads/avatars uploads

python - <<'PY'
from backend.main import create_tables

create_tables()
PY

exec gunicorn \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-720}" \
  --bind 0.0.0.0:5001 \
  backend.main:app
