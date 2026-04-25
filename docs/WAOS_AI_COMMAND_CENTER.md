# WAOS AI Command Center

`/bot-studio` ahora renderiza directamente `AiCommandCenter`.

Zonas:
1. AI Command: prompt, intensity, objetivo, vertical y toggles.
2. Build Timeline: SSE real desde `/api/v1/ai/workflows/{run_id}/events`.
3. Generated Operating System: artifacts JSON.
4. Production Readiness: dry run, simulation, readiness, blockers.
5. Launch Actions: simulation rerun, prepare apply, safe apply, canary, AI Ops.

El flujo manual queda oculto por default detrás de `NEXT_PUBLIC_ENABLE_MANUAL_BOT_CREATE=true`.
