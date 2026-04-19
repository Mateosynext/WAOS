# WAOS Observability World-Class Upgrade

## Included
- Distributed tracing propagated with shared `trace_id` / `correlation_id` from inbound WhatsApp through AI pipeline and outbound delivery.
- OTLP export queue with multi-target APM support (`OTEL_EXPORT_ENDPOINT`, `DATADOG_OTLP_ENDPOINT`, `NEW_RELIC_OTLP_ENDPOINT`).
- Structured production logs enriched with service, environment, version, request, correlation and trace identifiers.
- Pipeline stage latency telemetry (`pipeline_stage_metrics`) with P50/P95/P99 aggregation.
- Error-rate dashboard by vertical / bot / hour.
- Queue depth real-time sampling (`queue_depth_samples`).
- AI cost dashboard by conversation.
- Proactive alert rules seeded by default per organization:
  - queue backlog > 100 messages for 5 minutes
  - execution error rate > 5% in 10 minutes
  - pipeline latency P95 > 10 seconds in 10 minutes

## Main files
- `backend/app/telemetry_runtime.py`
- `backend/app/apm.py`
- `backend/app/observability.py`
- `backend/app/platform/runtime.py`
- `backend/app/application/inbound_service.py`
- `backend/app/ai.py`
- `backend/worker.py`

## Suggested endpoints to consume
- `GET /api/v1/observability/overview`
- `GET /api/v1/ai/dashboard`
- `GET /api/v1/observability/otel`
- `GET /api/v1/alerts/events`

## Runtime notes
- OTLP export remains non-blocking: spans are queued in `otel_span_exports` and flushed asynchronously.
- If no APM vendor is configured, telemetry is still persisted internally for dashboarding and alerting.
- Worker stores queue-depth samples on every loop and evaluates alert rules already present in `alert_rules_v14`.
