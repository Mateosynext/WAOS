# Bot creation AI flow full audit — 2026-04-26

## Scope audited

- `/bot-studio` server page data loading
- `AiCommandCenter` payload normalization and start action
- `AiCommandPrompt` click/validation behavior
- Next.js API proxy routes for `/api/ai/bot-autopilot` and workflow actions
- SSE workflow event proxy and backend event stream replay
- Backend `/api/v1/ai/bot-autopilot` start endpoint
- `BotAutopilotRequest` Pydantic normalization
- Workflow persistence, run/event snapshot durability, and JSON serialization
- Background workflow execution and terminal status handling
- Apply/readiness/canary guardrails
- Static regression tests

## Finding fixed in this audit

### Persistence converted optional JSON nulls into empty objects

`backend/app/ai_workflows/persistence.py` had `_clean_json_value(None) -> {}`. This meant optional fields like `bot_id`, `vertical_id`, `subvertical`, and `primary_objective` could be persisted into `config_json`, `result_json`, or event payloads as `{}` instead of `null`.

Impact:

- It could reintroduce object-shaped optional IDs in workflow snapshots.
- It explains why earlier payloads could surface as `bot_id: {}`.
- Backend schema now tolerates `{}`, but snapshots/results should still preserve the correct JSON contract.

Fix:

- `_clean_json_value(None)` now returns `None`, which serializes to JSON `null`.
- Added a regression guard in `test_ai_production_autopilot_v3_blindado_static.py`.

## Existing flow checks that passed

- The generate button is no longer silently disabled by validation; it is only disabled while busy.
- Missing organization/description now produces visible UI feedback before any POST.
- Frontend sanitizes optional ID fields before submit.
- Start route uses `POST /api/ai/bot-autopilot?async_mode=true`.
- Next proxy preserves query params, including `async_mode=true`.
- Backend start endpoint enforces tenant access before creating the run.
- Background workflow is scheduled after the run is committed.
- SSE emits event IDs and retry metadata.
- SSE catch-up handles stale `last_event_id` by replaying snapshot events instead of getting stuck.
- Workflow events are committed between steps for polling/SSE recovery.
- Apply requires a completed/completed_partial workflow, recomputes readiness, and requires explicit `confirm: true`.
- Canary requires a successful safe apply first.

## Validation performed

```text
pytest backend/tests/test_ai_production_autopilot_v3_blindado_static.py backend/tests/test_ai_workflow_e2e_guard_static.py -q
12 passed
```

```text
[OK] persistence null serializer regression
[OK] static end-to-end audit invariants passed
```

## Runtime validation limitation

Full frontend `npm test` / `npm run typecheck` was not executed because the ZIP does not include `node_modules`, and this environment has no dependency install step available. The audit therefore used repository static tests plus targeted static/runtime serializer validation.

## Recommendation after deploy

After deploying both frontend and backend, open `/bot-studio`, enter a description over 20 characters, select an organization, and confirm that backend logs show:

- `POST /api/v1/ai/bot-autopilot?...` once after pressing the button
- `GET /api/v1/ai/workflows/<run_id>/events...` after the run is created
- later workflow events such as `workflow.started`, `vertical.detected`, `wizard.created`, and terminal `workflow.completed` or `workflow.completed_partial`
