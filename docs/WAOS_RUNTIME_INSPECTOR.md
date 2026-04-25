# WAOS Runtime Inspector / AI Ops

Endpoints internos:
- `GET /api/v1/internal/ai-ops/runs`
- `GET /api/v1/internal/ai-ops/runs/{run_id}`
- `GET /api/v1/internal/ai-ops/runtime-turns/{turn_id}`

La UI base vive en `frontend/features/ai-ops/AiOpsInspector.tsx` y está pensada para operador/admin, no cliente final.
