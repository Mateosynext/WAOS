# Multi-tenant security fuzz register — 2026-04-26

Este registro convierte los riesgos multi-tenant/security en una lista explícita de superficies que deben tener fuzz/integration tests antes de declarar release completo. Los cambios de esta ronda cierran guardrails comunes y no sustituyen pruebas E2E reales con DB/provider.

## Controles comunes aplicados

- El proxy AI frontend reenvía `X-WAOS-Org-Id`, `X-WAOS-Bot-Id`, `X-Request-Id` y `X-Correlation-Id` hacia backend.
- `ensure_org_access` y `ensure_bot_access` validan membresía real y además rechazan contradicciones entre request context declarado y recurso autoritativo.
- `require_authorized_run` valida acceso a la organización del run y rechaza mismatch de `organization_id`/`bot_id` cuando el request declaró contexto tenant.
- Human confirmations usan schema tipado con `extra="forbid"`, `field_key` restringido, límites de longitud y audit payload con actor/idempotency key.
- Workflow persistence bloquea escrituras hijas huérfanas a runs inexistentes en operaciones de steps/events/actions/artifacts/reports/confirmations.

## Fuzz targets obligatorios

| Target | Riesgo | Guardrail actual | Estado runtime |
| --- | --- | --- | --- |
| `/api/v1/bots` | crear/listar bots cross-org o duplicados | `BotService.create/list` usa `ensure_org_access`, permisos e idempotencia `client_request_id` | NO VERIFICADO con fuzz concurrente real |
| `/api/v1/bots/{bot_id}` | leer/mutar bot ajeno | `BotService.get/update/publish/...` delega en `ensure_bot_access` | NO VERIFICADO con fuzz multi-org real |
| `/api/v1/ai/workflows/{run_id}` | leer run de otra org | `require_authorized_run` + `ensure_request_scope_matches` | NO VERIFICADO con fuzz real |
| `/api/v1/ai/workflows/{run_id}/apply` | aplicar run ajeno o con contexto falso | `require_authorized_run`, token firmado, claim atómico | NO VERIFICADO con apply concurrente real |
| `/api/v1/ai/workflows/{run_id}/prepare-canary` | canary sobre run/bot ajeno | `require_authorized_run` + apply requerido | NO VERIFICADO con fuzz real |
| `/api/v1/ai/workflows/{run_id}/human-confirmations` | payload crudo, auditoría incompleta o confirmación de run ajeno | `HumanConfirmationPayload`, `require_authorized_run`, audit event | NO VERIFICADO con fuzz real |
| `/api/v1/conversations/{conversation_id}/messages` | enviar mensaje en conversación cross-org | `_get_accessible_conversation`, `ensure_org_access`, permiso `conversation.manage` | NO VERIFICADO con provider WhatsApp real |
| `/api/v1/tool-executions/execute` | ejecutar tool sobre bot/org ajena o replay duplicado | `ensure_org_access`, `_validate_bot_access`, idempotency key/job claim | NO VERIFICADO con adapters/provider real |
| `/api/v1/sales/payments/{payment_id}/confirm` | confirmar pago ajeno o duplicar cobro | lookup por `payment_id`, `ensure_org_access`, confirmación solo por provider refresh | NO VERIFICADO con provider real |
| `/api/v1/knowledge/sources/{source_connection_id}/sync` | ingesta/publicación cross-tenant | `knowledge_ingestion_service.sync_source` debe validar org del source | NO VERIFICADO con provider/conector real |

## Tests faltantes de integración/fuzz

1. Usuario A de `org_a` intenta cada target con ids de `org_b`: debe responder `403` o `404` sin filtrar existencia.
2. Usuario multi-org declara header `X-WAOS-Org-Id: org_a` pero objeto pertenece a `org_b`: debe responder `403 tenant_context_mismatch`.
3. Header `X-WAOS-Bot-Id` distinto al bot autoritativo del recurso: debe responder `403 bot_context_mismatch`.
4. Replay/concurrencia en `apply`, `tool-executions/execute`, `bots` y payments: un solo side effect, respuesta determinista.
5. Knowledge ingestion/publication con source de otra org: sin lectura de documentos ni publicación cruzada.
6. Provider faults: timeouts, 409/402/5xx externos, webhooks duplicados y retries.

## No-claims explícitos

- NO VERIFICADO: provider WhatsApp real, payments provider real, tool adapters externos, embeddings/vector store, browser E2E real y DB PostgreSQL concurrente.
- NO VERIFICADO: que todos los endpoints legacy fuera de la lista anterior llamen a `ensure_*`; este registro cubre la lista P0/P1 indicada y debe expandirse antes de release general.
