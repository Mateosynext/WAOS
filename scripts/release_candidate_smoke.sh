#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

echo "[1/4] Python compileall"
python -m compileall backend/app backend/worker.py > /tmp/waos_compileall.log

echo "[2/4] Backend env validation with production-shaped sample values"
APP_ENV=production \
APP_SECRET=smoke-secret \
SECRET_ENCRYPTION_KEY=smoke-secret-encryption-key \
DATABASE_URL=postgresql://user:pass@db.example.com:5432/waos \
PUBLIC_APP_URL=https://app.example.com \
API_BASE_URL=https://api.example.com \
CORS_ALLOWED_ORIGINS=https://app.example.com \
ALLOWED_HOSTS=api.example.com \
SECURE_COOKIES=true \
AUTO_RUN_MIGRATIONS=true \
python backend/scripts/validate_render_env.py

echo "[3/4] Frontend env validation with production-shaped sample values"
NODE_ENV=production \
NEXT_PUBLIC_API_BASE_URL=https://api.example.com \
API_INTERNAL_URL=https://api.example.com \
NEXT_PUBLIC_APP_URL=https://app.example.com \
API_BASE_URL=https://api.example.com \
API_TIMEOUT_MS=12000 \
node frontend/scripts/validate-env.mjs

echo "[4/4] Frontend critical route smoke"
node frontend/scripts/smoke-routes.mjs

echo "[ok] release candidate smoke passed"
