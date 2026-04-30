#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export PORT="${PORT:-10000}"

echo "[waos] running release-candidate validation"
python scripts/validate_release_candidate.py

if [[ "${WAOS_SKIP_PREFLIGHT:-false}" != "true" ]]; then
  echo "[waos] running production preflight"
  python scripts/preflight_check.py
fi

if [[ "${AUTO_RUN_MIGRATIONS:-false}" == "true" ]]; then
  echo "[waos] applying database schema and migrations"
  python - <<'PY'
from app.db import init_db
init_db()
print("database init ok")
PY
fi

echo "[waos] starting API on port ${PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
