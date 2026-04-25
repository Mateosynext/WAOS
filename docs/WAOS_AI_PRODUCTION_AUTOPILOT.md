# WAOS AI Production Autopilot

Endpoint principal: `POST /api/v1/ai/bot-autopilot`.

Flujo implementado:

`prompt del negocio → normalización → detección vertical → business profile → wizard legacy reutilizado → vertical intelligence pack → agent policy pack → specialist config → knowledge plan → WhatsApp production pack → tool plan → dry run → autofix → simulation suite → go-live readiness → human confirmations → apply/canary plan → outcomes learning seed`.

El endpoint legacy `/api/v1/onboarding/wizard/ai-autopilot` se mantiene. El nuevo flujo llama a la base existente con `auto_apply=false` y bloquea producción mediante readiness/human gates.

Estados persistidos: `pending`, `running`, `waiting_for_provider`, `waiting_for_human_confirmation`, `waiting_for_integration`, `waiting_for_whatsapp_approval`, `paused_cost_limit`, `completed`, `completed_partial`, `failed`, `cancelled`.

Nunca se inventan precios, horarios, promociones, integraciones conectadas, claims médicos/legales, certificaciones ni resultados. Esos campos se convierten en `human_confirmation_items`.
