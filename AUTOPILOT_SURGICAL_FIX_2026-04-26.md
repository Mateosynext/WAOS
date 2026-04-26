# AUTOPILOT SURGICAL FIX 2026-04-26

## Incident

Production failed on `POST /api/v1/ai/bot-autopilot?async_mode=true` because the request body contained `intensity: "godmode"` while `AI_ENABLE_GODMODE=false`. Pydantic raised a validation error with `ctx.error = ValueError(...)`; the global error renderer then passed that raw exception into `JSONResponse`, producing a secondary `TypeError: Object of type ValueError is not JSON serializable` and surfacing a 500.

## Surgical resolution

1. `backend/app/errors.py`
   - Keeps the global `_json_safe()` sanitizer.
   - Sanitizes `RequestValidationError.errors()` before adding them to the public error envelope.
   - Keeps a last-line fallback in `error_response()` so error rendering cannot become the production failure.

2. `backend/app/ai_workflows/bot_autopilot/schemas.py`
   - Removed the hard validation rejection for disabled `godmode`.
   - Normalizes disabled `godmode` to `savage` before field validation.
   - Normalizes stale or manipulated `auto_apply=true` to `false` instead of rejecting startup.
   - Adds explicit telemetry fields:
     - `requested_intensity`
     - `effective_intensity`
     - `safety_warnings`

3. `backend/app/ai_workflows/bot_autopilot/service.py`
   - Persists and returns both requested/effective intensity.
   - Uses `effective_intensity` for cost governor, generation profiles, policy generation, vertical intelligence and tool planning.
   - Emits safety warnings in the `workflow.started` event.

4. Frontend AI Command Center
   - Keeps hiding `godmode` unless `NEXT_PUBLIC_AI_ENABLE_GODMODE=true`.
   - Keeps forcing `auto_apply=false` client-side.
   - Displays backend safety warnings when a run starts.

5. Regression tests
   - Static regression checks assert that disabled `godmode` is normalized, not rejected.
   - Static regression checks assert the error renderer remains JSON-safe for `ValueError` in validation context.

## Expected production behavior after deploy

Given this request:

```json
{
  "intensity": "godmode",
  "auto_apply": false
}
```

with `AI_ENABLE_GODMODE=false`, the backend should start the run as:

```json
{
  "requested_intensity": "godmode",
  "effective_intensity": "savage",
  "safety_warnings": ["godmode_disabled_downgraded_to_savage"]
}
```

It should no longer return `500 Internal server error` for this path.

## Validation performed in this container

- Parsed modified Python files with `ast.parse` successfully.
- Ran direct static assertions for the surgical invariants successfully.
- Full pytest/import execution could not be completed in this sandbox because Python subprocesses intermittently timed out while importing the project environment; this is a sandbox limitation observed during validation, not a syntax failure.
