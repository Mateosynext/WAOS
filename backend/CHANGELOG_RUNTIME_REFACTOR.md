# Runtime/backend refactor summary

This package includes a focused backend hardening pass around runtime governance, idempotency, observability and architectural boundaries.

## Implemented

- Canonical architecture manifest in `app/architecture.py`
- Legacy runtime isolated under `app/legacy/` and removed root `app/v8.py`
- Read/write unit of work policy and per-request transaction mode in `app/application/uow.py` and `app/api/dependencies.py`
- Formal migration layer in `app/migrations.py` integrated into `app/db.py`
- Inbox/runtime indexes, reasoning trail table, inbound lock table and domain events table
- Inbound idempotency + lock strategy in `app/application/inbound_service.py`
- Strict typed webhook intake in `app/schemas/webhooks.py` and `app/api/handlers/webhooks.py`
- Runtime pipeline split into understand / decide / generate in `app/runtime_pipeline.py`
- Agentic orchestration layer in `app/agent_runtime.py` with explicit stages for grounding, planning, action selection, verification, memory curation and post-send evaluation
- `app/runtime_pipeline.py` kept as compatibility boundary while delegating richer plan/render flows
- `app/ai.py` runtime now persists planner, grounding and verifier metadata inside execution outputs and operational reasoning
- Added tests in `tests/test_agent_runtime_orchestration.py` for planner/verifier/stage separation
- Declarative policy engine in `app/policy_engine.py`
- Fallback-chain/source tracing in `app/ai.py`
- Operational reasoning persistence per message in `message_operational_reasoning`
- Domain-level observability events in `app/domain_events.py`
- Correlation ID propagation through request middleware and runtime writes
- Runtime health panel endpoint at `/api/v1/runtime/health-panel`
- Contact memory version/etag/operational fields persistence
- Notification helper restored for routing/cancel flows
- Added tests in `tests/test_runtime_governance.py`

## Validation

- `pytest -q backend/tests` -> passing in this packaged state
