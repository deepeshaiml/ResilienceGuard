#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r backend/requirements.txt
fi
mkdir -p artifacts
exec .venv/bin/uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
