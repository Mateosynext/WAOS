# WAOS P1.8 release-ready patch notes — 2026-04-30

## Purpose

This patch closes the remaining release-gate fragility found in the P1.7 package.

## Changes

1. Replaced `frontend/scripts/check-local-imports.mjs` with a deterministic line-oriented local import scanner.
   - Avoids the prior long-running process behavior under CI/container runners.
   - Ignores build/test output directories.
   - Validates `@/` and relative imports against direct file and `index.*` candidates.
   - Exits explicitly with `process.exit(0)` on success and `process.exit(1)` on unresolved imports.

2. Hardened `backend/scripts/release_gate.py`.
   - Keeps frontend guardrail execution mandatory.
   - Runs Node guardrails through a non-interactive shell with captured output for more stable process reaping in constrained CI containers.
   - Runs deterministic AI evals in-process to avoid child-process stdio instability while preserving `python -m backend.app.ai_evals.run_all` as a standalone command.

## Validation performed in patch workspace

Validated successfully:

```bash
cd frontend
node ./scripts/check-local-imports.mjs
node ./scripts/check-bot-creation-guardrails.mjs
node ./scripts/check-p1-operational-guardrails.mjs
node ./scripts/check-critical-flow-guardrails.mjs
node ./scripts/check-multitenant-security-guardrails.mjs
node ./scripts/check-workflow-runtime-guardrails.mjs
node ./scripts/validate-env.mjs
```

Validated successfully:

```bash
/usr/bin/python3 backend/scripts/validate_release_candidate.py
/usr/bin/python3 backend/scripts/check_repo_hygiene.py
/usr/bin/python3 -m backend.app.ai_evals.run_all
```

## Production certification requirement

A production promotion still requires a clean CI run with the configured package registry and secrets:

```bash
bash scripts/validate_release_in_ci.sh
WAOS_REQUIRE_LIVE_AI_EVALS=1 WAOS_AI_EVAL_LIVE=1 OPENAI_API_KEY=... bash scripts/validate_release_in_ci.sh
bash scripts/validate_zip_reproducible.sh <final-zip>
```

The package must not be promoted if `npm ci`, `npm audit --audit-level=moderate`, `npm run typecheck`, `npm run build`, `npm run test:node`, `pytest`, deterministic AI evals, or required live AI evals fail in CI.
