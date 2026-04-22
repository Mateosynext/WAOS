# Validation report

Validated on 2026-04-21.

## Backend
- `pytest -q backend/tests/test_guided_vertical_onboarding.py` -> 8 passed
- `python3 -m py_compile backend/app/vertical_onboarding_runtime.py backend/app/migrations.py backend/app/application/onboarding_service.py backend/app/application/runtime_service.py backend/app/schemas/onboarding.py scripts/check_repo_hygiene.py` -> ok

## Frontend
- `npm install --no-fund --no-audit` -> ok
- `npm run typecheck` -> ok
- `npm run test:node` -> 44 passed, 0 failed

## Hygiene
- `python3 scripts/check_repo_hygiene.py` -> ok

## Build
- `npm run build` reached env validation, typecheck and Next production build start.
- `.next/BUILD_ID` was not emitted in this sandbox, so build is not marked final-green here.
