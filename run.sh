#!/usr/bin/env bash
# Start Family Health Vault on http://127.0.0.1:8765 (localhost only).
#   ./run.sh             start the app
#   ./run.sh --samples   (re)generate the fake reports first
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating .venv and installing requirements…"
  python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
PY=.venv/bin/python

if [ "${1:-}" = "--samples" ]; then
  $PY tools/make_fake_reports.py
fi

PORT="${PORT:-8765}"
echo "Family Health Vault → http://127.0.0.1:$PORT"
exec $PY -m uvicorn src.api:app --host 127.0.0.1 --port "$PORT" --reload
