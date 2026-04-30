#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

python backend/scripts/validate_release_candidate.py
python -m compileall backend/app backend/worker.py
pytest -q backend/tests
find backend -type d -name __pycache__ -prune -exec rm -rf {} +
find backend -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
python backend/scripts/export_openapi.py
python backend/scripts/preflight_check.py

if [[ "${WAOS_SKIP_EXTERNAL_SMOKES:-0}" != "1" ]]; then
  python backend/scripts/post_deploy_smoke.py --required
  python backend/scripts/payment_provider_sandbox_smoke.py --required
  python backend/scripts/critical_e2e_smoke.py --required
fi

if [[ -d frontend ]]; then
  cd frontend
  if [[ -f package-lock.json || -f npm-shrinkwrap.json ]]; then
    npm ci
  else
    npm install --package-lock-only --ignore-scripts --no-audit --no-fund
    npm ci
  fi
  npm run typecheck
  if [[ "${WAOS_SKIP_EXTERNAL_SMOKES:-0}" != "1" ]]; then
    npm run test:e2e:real:critical
  fi
  npm run build
fi
