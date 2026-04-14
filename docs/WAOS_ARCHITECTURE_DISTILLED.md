# WAOS distilled architecture

## Active source of truth
- transactional runtime: `backend.app.vertical_transactions`
- persistent vertical domains: `backend.app.vertical_domain_runtime`
- integrations runtime: `backend.app.integrations_runtime`
- api entrypoint: `backend.app.main`

## Legacy isolation
Deprecated compatibility modules live under `backend/app/legacy/`.
Active modules and tests must not import `backend.app.legacy.*`.

## Verification
- `PYTHONPATH=. pytest -q backend/tests`
- `cd frontend && npm run -s typecheck`
