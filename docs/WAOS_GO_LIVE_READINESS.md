# WAOS Go-Live Readiness

Módulo: `backend/app/ai_workflows/go_live/readiness.py`.

Inputs: wizard, dry run, validation snapshot, simulation report, knowledge plan, integration status, WhatsApp/template status, tool plan, policy pack y handoff config.

Output: `ready`, `ready_with_warnings` o `blocked`, score, blockers, warnings, human confirmations, risks, `can_apply`, `can_publish` y `canary_required`.

Apply queda bloqueado si readiness está `blocked`.
