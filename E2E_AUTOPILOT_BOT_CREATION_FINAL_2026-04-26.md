# WAOS Bot Creation / Autopilot E2E hardening final - 2026-04-26

Scope applied on top of `waos_bot_creation_hardened_blindado_testeado_sse_autorecovery.zip`.

## E2E flow covered

1. `/bot-studio` server page loads session, bots and the real vertical catalog.
2. `AiCommandCenter` receives organizations, bots, verticals and any initial `run_id`.
3. `AiCommandPrompt` shows real selectors for:
   - Organization
   - Existing bot/new bot
   - Industry
   - Dependent subvertical / operation type
   - Objective
   - Intensity
   - Safe generation toggles
4. Start payload is normalized client-side before POST:
   - `auto_apply` is forced false.
   - `godmode` is hidden and downgraded when the public flag is off.
5. Backend still normalizes defensively:
   - disabled `godmode` -> `savage`
   - invalid intensity -> `balanced`
   - `auto_apply=true` -> `false`
6. Validation errors remain JSON-safe even if Pydantic includes a raw `ValueError` in `ctx.error`.
7. SSE stream keeps `Last-Event-ID` semantics and now avoids stale catch-up deadlocks.
8. If SSE disconnects, frontend recovers by polling the workflow snapshot and updates the timeline automatically.
9. Timeline dedupes events from snapshot + stream and derives terminal status from events when snapshot status is unavailable.

## Files changed in this E2E pass

- `frontend/app/bot-studio/page.tsx`
- `frontend/features/ai-command-center/types.ts`
- `frontend/features/ai-command-center/AiCommandCenter.tsx`
- `frontend/features/ai-command-center/AiCommandPrompt.tsx`
- `frontend/features/ai-command-center/useAiWorkflowStream.ts`
- `frontend/features/ai-command-center/AiRunTimeline.tsx`
- `backend/app/api/routers/ai_workflows.py`
- `frontend/tests/ai-command-center-e2e-guard.test.ts`
- `backend/tests/test_ai_workflow_e2e_guard_static.py`

## Validation performed in sandbox

Backend syntax:

```bash
python3 -S -m py_compile backend/app/api/routers/ai_workflows.py backend/app/ai_workflows/events.py backend/app/errors.py backend/app/ai_workflows/bot_autopilot/schemas.py backend/tests/test_ai_workflow_e2e_guard_static.py
```

Static E2E guards: 14/14 PASS.

TypeScript parser/typecheck attempt on changed files:

```bash
timeout 30s tsc --noEmit --pretty false --skipLibCheck --jsx preserve --module ESNext --moduleResolution bundler --target ES2022 ...changed files...
```

Result: no syntax errors surfaced. The only reported issues were expected missing dependency/path modules because this sandbox has no `node_modules` and no installed Next/React type packages.

## Required validation after extracting on your machine / CI

```bash
cd frontend
npm ci
npm run typecheck
npm run test:node
npm run test:e2e:real:critical

cd ../backend
python -m pytest backend/tests/test_ai_workflow_e2e_guard_static.py backend/tests/test_request_context_and_error_contracts.py backend/tests/test_ai_workflow_sse_resilience_static.py
```
