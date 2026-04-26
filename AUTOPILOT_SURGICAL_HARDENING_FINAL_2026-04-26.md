# Autopilot surgical hardening final - 2026-04-26

## Root cause repaired

The production failure was caused by persisted workflow JSON converting Python `None` into `{}`. The initial HTTP request to `/api/v1/ai/bot-autopilot?async_mode=true` could succeed, but the background worker later rehydrated `BotAutopilotRequest` from `ai_workflow_runs.config_json` and failed because fields such as `bot_id` expected `str | None`, not an object.

## Backend changes

- `backend/app/ai_workflows/persistence.py`
  - Keeps `None` as JSON `null` during persistence.
  - Prevents future optional scalar fields from being contaminated as `{}`.

- `backend/app/ai_workflows/bot_autopilot/schemas.py`
  - Normalizes legacy `{}` values for optional strings and numbers.
  - Normalizes `{}` / empty values for boolean feature gates.
  - Restores safe defaults for `primary_objective`, `language`, and `timezone`.
  - Keeps `auto_apply` human-gated and disabled even if the client sends it enabled.

- `backend/app/ai_workflows/bot_autopilot/service.py`
  - Repairs persisted legacy `config_json` before validating `BotAutopilotRequest`.
  - Drops unknown persisted fields during repair.
  - Recovers `organization_id` from the run row.
  - Recovers `user_description` from the run prompt if config is damaged.
  - Recovers `bot_id` from the run row if config is damaged.
  - Rewrites the repaired config back to the run so future polls/retries use clean data.

## Frontend changes

- `frontend/app/bot-studio/page.tsx`
  - Loads the vertical catalog for Bot Studio.

- `frontend/features/ai-command-center/AiCommandCenter.tsx`
  - Cleans optional strings before sending the Autopilot request.
  - Cleans optional cost value.
  - Forces `auto_apply: false`.
  - Downgrades `godmode` client-side unless explicitly enabled.

- `frontend/features/ai-command-center/AiCommandPrompt.tsx`
  - Adds selectable vertical.
  - Adds dependent subvertical options.
  - Resets subvertical when vertical changes.
  - Falls back to manual inputs if the catalog is unavailable.

- `frontend/features/ai-command-center/types.ts`
  - Adds vertical/subvertical catalog types for the AI command center.

## Validation performed

- Python compile check:
  - `app/ai_workflows/persistence.py`
  - `app/ai_workflows/bot_autopilot/schemas.py`
  - `app/ai_workflows/bot_autopilot/service.py`
  - `tests/test_ai_autopilot_null_payload_regression.py`

- Regression tests:
  - `PYTHONPATH=. pytest -q tests/test_ai_autopilot_null_payload_regression.py`
  - Result: 4 passed.

Frontend typecheck was not run because this zip does not include `frontend/node_modules`.
