# WAOS Product Integration - Phase 1

Este corte aterriza la primera ola real dentro del producto existente, sin romper contratos multi-tenant ni mover módulos legacy fuera de `backend/app/legacy`.

## Implementado en este zip
- Control tower de activación con endpoint `/api/v1/onboarding/summary`
- Persistencia de progreso de activación (`activation_progress`)
- Tabla de `feature_flag_overrides` para rollout por tenant/bot
- Tabla de `product_events` para TTFV y eventos de producto
- Modo `sandbox` vs `go_live` persistido en `organizations.tenant_mode`
- Endpoint `/api/v1/onboarding/tenant-mode`
- Saved views para inbox (`/api/v1/inbox/saved-views`)
- Prioridad heurística en conversaciones (`priority_score`, `next_best_action`, `attention_class`, `stalled`)
- Onboarding UI conectada a estado real del tenant
- Inbox UI con saved views y orden por prioridad WAOS

## Lo que quedó preparado pero no cerrado end-to-end
- Materialización fuerte de TTFV por cohorte
- Rollout UI completo de feature flags
- A/B testing, simulador de conversaciones y score calibrado
- Portal monetizable y agenda avanzada por recurso
- Contratos versionados de integraciones y replay UI completo

## Siguiente tramo recomendado
1. cerrar typecheck completo del frontend
2. agregar tests API para onboarding e inbox saved views
3. introducir feature flags UI y overrides por bot
4. conectar product_events a métricas y executive reports
