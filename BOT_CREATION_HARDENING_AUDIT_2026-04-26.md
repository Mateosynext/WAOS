# Bot creation and Autopilot hardening audit - 2026-04-26

## Incident root cause

The production error shown as "No se pudo iniciar el Autopilot / Internal server error" was caused by error rendering, not by `/livez`. A Pydantic validation failure included a raw `ValueError` in `ctx.error`; the API tried to return that structure directly through `JSONResponse`, which caused `TypeError: Object of type ValueError is not JSON serializable`.

## Hardening applied

1. Error contract is now JSON-safe by default.
   - `backend/app/errors.py` now sanitizes exceptions, dates, decimals, enums, bytes, paths, sets, tuples, NaN/Infinity, deep objects and arbitrary objects before `JSONResponse`.
   - `error_response()` has a final fallback so error rendering cannot become the next 500.

2. Autopilot gate validation no longer emits raw `ValueError` for expected product gates.
   - `backend/app/ai_workflows/bot_autopilot/schemas.py` now uses structured `PydanticCustomError` for `godmode_disabled` and `auto_apply_disabled`.
   - Backend uses `settings.ai_enable_godmode`, not ad-hoc environment reads.

3. Frontend launch payload is forced safe.
   - `frontend/features/ai-command-center/AiCommandCenter.tsx` always sends `auto_apply: false`.
   - If `NEXT_PUBLIC_AI_ENABLE_GODMODE` is not enabled, stale or manipulated UI state downgrades `godmode` to `savage` before submit.

4. Bot creation contract now fails closed.
   - `backend/app/schemas/bots.py` forbids extra fields, trims strings, bounds lengths, normalizes list fields and caps list sizes.
   - `backend/app/application/bot_service.py` verifies the created bot exists, belongs to the requested organization, has a valid config draft, and has an initial published version when `publish_now=true`.

5. Guided onboarding apply now requires fresh dry-run for both flows.
   - `backend/app/vertical_onboarding_runtime.py` now enforces the same validation-hash, revision and `apply_ready` checks before applying a wizard whether it reconfigures an existing bot or creates a brand-new bot.

## Tests / checks added

- `backend/tests/test_request_context_and_error_contracts.py`
  - Keeps the original `ValueError` serialization regression test.
  - Adds nested non-JSON object sanitation coverage.
- `backend/tests/test_ai_production_autopilot_v3_blindado_static.py`
  - Adds a static guard ensuring guided apply validates freshness before reaching bot creation.

## Local verification performed

- `python -S -m py_compile` passed on the modified backend modules and tests.
- Full pytest / TypeScript test execution was not completed in this container because normal Python/Node startup hangs in the environment; syntax-level backend validation was completed with `python -S`.

## Deployment notes

- Redeploy backend and frontend together.
- Keep `AI_ENABLE_GODMODE=false` unless intentionally testing admin-only behavior.
- Do not expose `NEXT_PUBLIC_AI_ENABLE_GODMODE=true` unless backend `AI_ENABLE_GODMODE=true` is also enabled.
- The expected result for blocked Autopilot input is now a structured 422/409 envelope, never a generic 500 from error serialization.
