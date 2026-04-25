# WAOS Local and Deploy Guide

1. Ejecutar migraciones para crear tablas AI workflow.
2. Configurar env vars AI.
3. Levantar backend y frontend.
4. Abrir `/bot-studio`.
5. Probar prompt dental con intensity `savage`.
6. Ver SSE, readiness y human confirmations.
7. No aplicar si readiness está `blocked`.

Feature flags backend: `AI_ENABLE_WORKFLOW_ENGINE`, `AI_ENABLE_BOT_AUTOPILOT_V2`, `AI_ENABLE_SIMULATION_SUITE`, `AI_ENABLE_GO_LIVE_READINESS`, `AI_ENABLE_GODMODE`, `AI_MAX_COST_PER_RUN`, `AI_PROVIDER_TIMEOUT_MS`.
