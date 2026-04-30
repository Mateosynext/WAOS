#!/usr/bin/env bash
set -Eeuo pipefail
if [[ "${WAOS_CI_TRACE:-1}" == "1" ]]; then
  set -x
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
DEFAULT_TIMEOUT="${WAOS_STEP_TIMEOUT_SECONDS:-900}"
NPM_CI_TIMEOUT="${WAOS_NPM_CI_TIMEOUT_SECONDS:-$DEFAULT_TIMEOUT}"
NPM_BUILD_TIMEOUT="${WAOS_NPM_BUILD_TIMEOUT_SECONDS:-$DEFAULT_TIMEOUT}"
NPM_AUDIT_TIMEOUT="${WAOS_NPM_AUDIT_TIMEOUT_SECONDS:-300}"
PYTEST_TIMEOUT="${WAOS_PYTEST_TIMEOUT_SECONDS:-$DEFAULT_TIMEOUT}"
PIP_AUDIT_TIMEOUT="${WAOS_PIP_AUDIT_TIMEOUT_SECONDS:-300}"
EXTERNAL_SMOKE_TIMEOUT="${WAOS_EXTERNAL_SMOKE_TIMEOUT_SECONDS:-300}"
PLAYWRIGHT_INSTALL_TIMEOUT="${WAOS_PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS:-600}"
NPM_AUDIT_LEVEL="${NPM_AUDIT_LEVEL:-moderate}"

for flag in WAOS_SKIP_NPM_CI WAOS_SKIP_BACKEND_TESTS WAOS_SKIP_EXTERNAL_SMOKES; do
  if [[ "${!flag:-0}" == "1" ]]; then
    echo "[ci:fail] $flag=1 is not allowed for production certification" >&2
    exit 1
  fi
done

run_with_timeout() {
  local label="$1"
  local seconds="$2"
  shift 2
  echo "[ci:run] $label"
  set +e
  if command -v timeout >/dev/null 2>&1; then
    timeout "$seconds" "$@"
  else
    "$@"
  fi
  local code=$?
  set -e
  if [[ "$code" -eq 124 ]]; then
    echo "[ci:fail] $label timed out after ${seconds}s" >&2
  elif [[ "$code" -ne 0 ]]; then
    echo "[ci:fail] $label exited with code ${code}" >&2
  else
    echo "[ci:ok] $label"
  fi
  return "$code"
}
cleanup_python_artifacts() {
  find "$ROOT" -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
  find "$ROOT" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
}

require_ci_tooling() {
  if ! "$PYTHON_BIN" -m pip_audit --version >/dev/null 2>&1; then
    echo "[ci:fail] pip-audit is required for production SCA. Install tools/requirements-ci.txt before running this gate." >&2
    exit 1
  fi
}

run_with_timeout "backend release candidate validation" "$DEFAULT_TIMEOUT" "$PYTHON_BIN" backend/scripts/validate_release_candidate.py
run_with_timeout "repository hygiene check" "$DEFAULT_TIMEOUT" "$PYTHON_BIN" backend/scripts/check_repo_hygiene.py
run_with_timeout "release source hardening" "$DEFAULT_TIMEOUT" "$PYTHON_BIN" backend/scripts/check_release_source_hardening.py
run_with_timeout "deterministic release gate" "$DEFAULT_TIMEOUT" "$PYTHON_BIN" backend/scripts/release_gate.py
run_with_timeout "backend compileall" "$DEFAULT_TIMEOUT" python -m compileall backend/app backend/worker.py
run_with_timeout "AI behavior eval suite" "${WAOS_AI_EVAL_TIMEOUT_SECONDS:-300}" "$PYTHON_BIN" -m backend.app.ai_evals.run_all
if [[ "${WAOS_REQUIRE_LIVE_AI_EVALS:-0}" == "1" ]]; then
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "[ci:fail] WAOS_REQUIRE_LIVE_AI_EVALS=1 requires OPENAI_API_KEY for live provider sandbox evals" >&2
    exit 1
  fi
  run_with_timeout "AI live provider sandbox evals" "${WAOS_AI_LIVE_EVAL_TIMEOUT_SECONDS:-420}" env WAOS_AI_EVAL_LIVE=1 WAOS_REQUIRE_LIVE_AI_EVALS=1 "$PYTHON_BIN" -m backend.app.ai_evals.eval_live_provider_sandbox
fi

require_ci_tooling
run_with_timeout "backend SCA pip-audit" "$PIP_AUDIT_TIMEOUT" "$PYTHON_BIN" -m pip_audit -r backend/requirements.lock --strict

if [[ -d frontend ]]; then
  cd frontend
  run_node_check() {
    local script="$1"
    run_with_timeout "frontend guardrail ${script}" "$DEFAULT_TIMEOUT" env WAOS_SCRIPT="$script" node --input-type=module -e 'await import(`./scripts/${process.env.WAOS_SCRIPT}`); process.exit(process.exitCode || 0)'
  }

  # The npm install/build/audit path is intentionally not skippable for production certification.
  if [[ -f package-lock.json || -f npm-shrinkwrap.json ]]; then
    run_with_timeout "frontend npm ci" "$NPM_CI_TIMEOUT" npm ci --no-audit --no-fund
  else
    run_with_timeout "frontend package-lock generation" "$NPM_CI_TIMEOUT" npm install --package-lock-only --ignore-scripts --no-audit --no-fund
    run_with_timeout "frontend npm ci" "$NPM_CI_TIMEOUT" npm ci --no-audit --no-fund
  fi

  run_with_timeout "frontend SCA npm audit" "$NPM_AUDIT_TIMEOUT" npm audit --audit-level="$NPM_AUDIT_LEVEL"

  if [[ "${WAOS_INSTALL_PLAYWRIGHT_BROWSERS:-0}" == "1" ]]; then
    run_with_timeout "Playwright browser install" "$PLAYWRIGHT_INSTALL_TIMEOUT" npx playwright install --with-deps chromium
  fi

  run_node_check check-local-imports.mjs
  run_node_check check-bot-creation-guardrails.mjs
  run_node_check check-p1-operational-guardrails.mjs
  run_node_check check-critical-flow-guardrails.mjs
  run_node_check check-multitenant-security-guardrails.mjs
  run_node_check check-workflow-runtime-guardrails.mjs
  run_node_check validate-env.mjs
  if [[ "${WAOS_RUN_STATIC_DELIVERY:-0}" == "1" || -n "${WAOS_FRONTEND_BASE_URL:-}" ]]; then
    run_node_check validate-static-delivery.mjs
  fi

  run_with_timeout "frontend typecheck" "$DEFAULT_TIMEOUT" npm run typecheck
  run_with_timeout "frontend production build" "$NPM_BUILD_TIMEOUT" npm run build
  test -s .next/BUILD_ID || { echo "[ci:fail] missing frontend/.next/BUILD_ID after production build" >&2; exit 1; }
  run_with_timeout "frontend node tests" "$DEFAULT_TIMEOUT" npm run test:node
  run_with_timeout "frontend critical external browser smoke" "$DEFAULT_TIMEOUT" npm run test:e2e:real:critical
  cd "$ROOT"
fi

run_with_timeout "backend pytest" "$PYTEST_TIMEOUT" pytest -q backend/tests

run_with_timeout "OpenAPI export" "$DEFAULT_TIMEOUT" python backend/scripts/export_openapi.py
run_with_timeout "production preflight check" "$EXTERNAL_SMOKE_TIMEOUT" python backend/scripts/preflight_check.py
run_with_timeout "post-deploy liveness/readiness smoke" "$EXTERNAL_SMOKE_TIMEOUT" python backend/scripts/post_deploy_smoke.py --required
run_with_timeout "payment provider sandbox smoke" "$EXTERNAL_SMOKE_TIMEOUT" python backend/scripts/payment_provider_sandbox_smoke.py --required
run_with_timeout "critical E2E production smoke" "$EXTERNAL_SMOKE_TIMEOUT" python backend/scripts/critical_e2e_smoke.py --required

cleanup_python_artifacts
echo "[ci:ok] WAOS release validation passed"
