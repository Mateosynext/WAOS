#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python backend/scripts/deploy_guard.py
python scripts/release_gate.py --profile source
python -m py_compile \
  backend/app/config.py \
  backend/app/vertical_onboarding_ai_prefill.py \
  backend/app/schemas/onboarding.py \
  backend/app/application/onboarding_handlers/commands.py \
  backend/scripts/deploy_guard.py \
  backend/scripts/preflight_check.py \
  backend/scripts/validate_render_env.py \
  backend/scripts/run_migrations.py \
  backend/scripts/export_vertical_profiles.py \
  scripts/release_gate.py
python -m unittest backend.tests.test_deploy_hardening_guardrails -v

(
  cd frontend
  node ./scripts/validate-env.mjs
  node ./scripts/clean-stale-botstudio.mjs
  npm ci
  npm run typecheck
  npm run build
)
