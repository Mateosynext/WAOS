# WAOS World-Class Second Pass

## Added in this pass

- Omnichannel identity graph and channel event ingestion
- Public SDK manifest and public API key issuance
- Shadow runs persisted with diff verdicts
- Prompt artifacts + analytics overview
- OTEL export queue with optional OTLP HTTP flush

## New endpoints

- `GET /api/public/sdk/manifest`
- `POST /api/public/v1/channels/events`
- `POST /api/v1/public-api/credentials`
- `GET /api/v1/observability/otel`
- `POST /api/v1/observability/otel/flush`
- `POST /api/v1/shadow/runs`
- `GET /api/v1/shadow/overview`
- `POST /api/v1/prompts/artifacts`
- `GET /api/v1/prompts/analytics`

## Environment

- `OTEL_EXPORT_ENABLED`
- `OTEL_EXPORT_ENDPOINT`
- `OTEL_SERVICE_NAME`
- `OTEL_EXPORT_TIMEOUT_SECONDS`
