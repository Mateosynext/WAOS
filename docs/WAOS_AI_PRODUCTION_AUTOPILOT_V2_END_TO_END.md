# WAOS AI Production Autopilot v2 End-to-End

## What changed in v2

v2 closes the main gap from the first implementation: the AI workflow is no longer only a synchronous request that returns after all work is done. `/api/v1/ai/bot-autopilot` now starts a persistent workflow run, returns `run_id` immediately by default, and executes the production autopilot in a FastAPI background task. Bot Studio connects to `GET /api/v1/ai/workflows/{run_id}/events` and receives persisted SSE events until the run reaches a terminal state.

## End-to-end path

1. Operator opens `/bot-studio`.
2. UI renders `WAOS AI Command Center`; manual create remains hidden unless `NEXT_PUBLIC_ENABLE_MANUAL_BOT_CREATE=true`.
3. Operator enters the business prompt and selects intensity.
4. Frontend calls `POST /api/ai/bot-autopilot`.
5. Frontend proxy calls backend `POST /api/v1/ai/bot-autopilot`.
6. Backend creates `ai_workflow_runs`, emits `workflow.started`, commits, then starts the workflow in background.
7. Frontend opens EventSource to `/api/ai/workflows/{run_id}/events`.
8. Backend streams persisted events and polls until terminal status.
9. Workflow runs intent normalization, vertical detection, business profile, wizard generation, vertical pack, policy pack, specialist agents, knowledge plan, WhatsApp pack, tool plan, dry run, autofix, simulation, readiness, human confirmations and apply/canary planning.
10. Artifacts are persisted to first-class tables and also attached to `ai_workflow_runs.result_json`.
11. Human confirmations can be posted with `POST /api/v1/ai/workflows/{run_id}/human-confirmations`.
12. Readiness can be recalculated with `POST /api/v1/ai/workflows/{run_id}/go-live-readiness`.
13. Apply requires readiness not blocked and an explicit `confirm=true` body.
14. AI Operations Inspector can open the run and inspect events, steps, costs, confirmations and generated artifacts.

## Backend endpoints hardened in v2

- `POST /api/v1/ai/bot-autopilot?async_mode=true` starts background execution and returns `run_id` immediately.
- `POST /api/v1/ai/bot-autopilot?async_mode=false` keeps the synchronous compatibility mode.
- `GET /api/v1/ai/workflows/{run_id}` returns run, steps, events, confirmations and result.
- `GET /api/v1/ai/workflows/{run_id}/events` streams historical plus live events until terminal status.
- `POST /api/v1/ai/workflows/{run_id}/human-confirmations` persists critical human-confirmed facts.
- `POST /api/v1/ai/workflows/{run_id}/go-live-readiness` recalculates readiness after confirmations.
- `POST /api/v1/ai/workflows/{run_id}/apply` requires `{ "confirm": true }` and blocks if readiness is blocked.
- `POST /api/v1/ai/workflows/{run_id}/prepare-canary` generates a canary plan with rollback triggers.

## Persisted v2 artifacts

The workflow writes to:

- `ai_workflow_runs`
- `ai_workflow_steps`
- `ai_workflow_events`
- `ai_cost_ledger`
- `agent_policy_packs`
- `knowledge_grounding_plans`
- `whatsapp_production_packs`
- `tool_execution_plans`
- `simulation_reports`
- `simulation_scenarios`
- `go_live_readiness_reports`
- `human_confirmation_items`

## Frontend v2 behavior

`AiCommandCenter` now derives the final visible run from streamed terminal payloads (`workflow.completed` / `workflow.completed_partial`). It no longer waits for a synchronous full response to show progress.

`HumanConfirmationPanel` can persist confirmations and trigger readiness recalculation.

`LaunchActionsPanel` can rerun simulation, recheck readiness, prepare apply, apply safely with explicit confirmation, prepare canary and open AI Ops.

`AI Operations Inspector` is now routable at `/ai-ops` and can inspect a specific run via `?run_id=`.

## Validation commands used

```bash
python -S -m py_compile backend/app/ai_workflows/persistence.py
python -S -m py_compile backend/app/api/routers/ai_workflows.py
python -S - <<'PY'
import ast
ast.parse(open('backend/app/ai_workflows/bot_autopilot/service.py', encoding='utf-8').read())
print('ast_ok')
PY
node scripts/validate-waos-autopilot-v2.mjs
grep -R "Crear desde cero\|Rutas canónicas\|Create y reconfigure\|flujo de creación modular" -n frontend/app frontend/features || true
grep -R "setTimeout" -n frontend/features/bot-studio/create/AiSetupAssistant.tsx frontend/features/ai-command-center || true
```

`npm run typecheck` and full frontend tests require `frontend/node_modules`, which is intentionally not present in the uploaded ZIP. Run `npm ci` inside `frontend/` before executing them.
