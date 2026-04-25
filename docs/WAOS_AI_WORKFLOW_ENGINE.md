# WAOS AI Workflow Engine

Módulo: `backend/app/ai_workflows/`.

Componentes:
- `persistence.py`: runs, steps, events, cost ledger y artifact tables.
- `events.py`: serialización SSE.
- `cost_governor.py`: límites por intensity.
- `engine.py` / `step_runner.py`: contrato central para retry, fallback, timeout, cancel, resume, pause, partial failure e idempotency.
- `bot_autopilot/service.py`: workflow productivo.

Tablas principales: `ai_workflow_runs`, `ai_workflow_steps`, `ai_workflow_events`, `ai_cost_ledger`, `simulation_reports`, `go_live_readiness_reports`, `agent_policy_packs`, `whatsapp_production_packs`, `tool_execution_plans`, `knowledge_grounding_plans`, `human_confirmation_items`, `ai_runtime_turn_inspections`, `ai_provider_health_snapshots`.
