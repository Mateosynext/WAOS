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
