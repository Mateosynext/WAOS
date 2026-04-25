#!/usr/bin/env bash
set -euo pipefail
export RUN_BOOTSTRAP_SEED=${RUN_BOOTSTRAP_SEED:-false}
export AUTO_RUN_MIGRATIONS=${AUTO_RUN_MIGRATIONS:-true}
export WEB_CONCURRENCY=${WEB_CONCURRENCY:-3}
export GUNICORN_TIMEOUT_SECONDS=${GUNICORN_TIMEOUT_SECONDS:-120}
python scripts/deploy_guard.py --runtime
python scripts/preflight_check.py
if [ "${AUTO_RUN_MIGRATIONS}" = "true" ]; then
  python scripts/run_migrations.py
fi
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w ${WEB_CONCURRENCY} \
  -b 0.0.0.0:${PORT:-8000} \
  --timeout ${GUNICORN_TIMEOUT_SECONDS} \
  --graceful-timeout 30 \
  --keep-alive 15 \
  --access-logfile - \
  --error-logfile -
