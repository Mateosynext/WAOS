# Bot Creation AI Flow - Deep Audit 2026-04-26

## Scope
Audited the full AI bot generation path:

1. `/bot-studio` page data loading
2. `AiCommandPrompt` submit UX
3. `AiCommandCenter` payload build, validation and POST
4. Next.js proxy route `/api/ai/bot-autopilot?async_mode=true`
5. Backend route `/api/v1/ai/bot-autopilot`
6. Background workflow execution
7. Durable workflow persistence/events
8. SSE proxy and backend event replay
9. Snapshot polling fallback
10. Apply / prepare-apply / canary hard gates

## Original production signal
The provided production log contains repeated `GET /api/v1/ai/workflows/{run_id}/events` and `/livez`, but no `POST` request for starting bot autopilot. That means the observed failure mode was consistent with a click that did not start a new run or with a client-side guard swallowing the action.

## Additional issues found in this deeper pass

### 1. Double submit race
The button was disabled while `busy`, but React state updates are asynchronous. A very fast double click could still enqueue duplicate start/apply requests before the disabled state rendered.

Fix:
- Added `startInFlightRef` for start requests.
- Added `actionInFlightRef` for prepare/apply/canary requests.
- Guarded both actions with `Boolean(busy)` plus the ref.

### 2. Boolean IDs could become strings
The frontend/backend optional ID sanitizers previously stringified boolean values. A malformed selector/cookie state could turn `false` into `"false"`, which is a dangerous fake ID.

Fix:
- Frontend `cleanOptionalString(false)` now returns `null`.
- Backend Pydantic pre-validator treats booleans as invalid for required org and as unset for optional IDs.

### 3. Rich option objects without usable ID could still 422 optional fields
The previous backend fallback tolerated `{}` and `{ id/value }`, but a rich UI object such as `{ label: "Crear nuevo" }` could still reach Pydantic as a dict for optional fields.

Fix:
- Optional ID fields now treat rich objects without a useful `id`, `bot_id`, `organization_id`, or `value` as `None`.
- Required `organization_id` remains strict to prevent tenant bypass.

### 4. SSE cursor could leak between run IDs
`lastEventIdRef` persisted across run changes. The backend stale-cursor guard would usually recover, but the client should not connect a new run with a previous run's cursor.

Fix:
- Added `activeRunIdRef`.
- Reset `lastEventIdRef` when `runId` changes.
- Snapshot recovery now also advances `lastEventIdRef` to the latest snapshot event.

### 5. Terminal event display used the first terminal event
The UI used `.find(...)`, which picks the first terminal event. If a failed/paused run was later resumed and completed, the status banner could show the old terminal event.

Fix:
- Terminal event display now scans reversed events and shows the latest terminal event.

## Validation performed
Static deep-audit script checked 20 invariants:

- POST path exists and uses `async_mode=true`.
- Frontend proxy preserves query strings.
- Start click cannot go silent on missing input.
- Start/apply double-submit guards exist.
- Optional IDs are sanitized.
- Frontend route maps to backend route.
- SSE proxy forwards `Last-Event-ID` / `last_event_id`.
- Hook uses EventSource plus snapshot polling fallback.
- SSE cursor resets per run.
- Backend route starts async workflow after `uow.commit()`.
- Workflow endpoints are tenant gated.
- Backend Pydantic schema guards godmode, auto_apply and object-shaped IDs.
- Persistence preserves JSON nulls and redacts sensitive payload keys.
- Backend SSE emits `retry`, `id`, and default `data` messages.
- Stale Last-Event-ID catch-up cannot get stuck.
- Workflow commits progress events step by step.
- Apply recomputes readiness and requires explicit confirmation.
- Guided onboarding apply requires fresh dry-run validation.
- Canary requires successful apply first.
- Disabled buttons have visible styling.
- No fake `setTimeout` progress remains in the stream hook.

Result: `20 checks passed`.

## Limitations
The local container does not include Python dependencies (`pytest`, `pydantic`) or frontend `node_modules`, so full runtime pytest/typecheck was not possible here. The audit therefore used targeted static invariants and code-path inspection.
