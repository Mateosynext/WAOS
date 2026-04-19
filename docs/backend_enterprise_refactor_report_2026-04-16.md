# Backend enterprise refactor report — 2026-04-16

## 1. Hallazgos reales del backend actual

El backend ya tenía una base técnica mejor que un CRUD simple: routers por dominio, application services, repositorios, providers, observabilidad, seguridad, idempotencia, runtimes y tests. El problema principal no era la ausencia de piezas, sino la falta de endurecimiento transversal entre ellas.

Los hallazgos con más impacto fueron estos:

1. **Contexto tenant/bot inconsistente entre frontend y backend.** El frontend enviaba `x-waos-org-id` y `x-waos-bot-id`, mientras el backend privilegiaba `x-organization-id` y `x-bot-id`. Eso permitía pérdida silenciosa de contexto o ambigüedad operacional.
2. **Errores demasiado heterogéneos.** Había fallas que terminaban como `HTTPException`, otras como errores genéricos, y otras sin contrato consistente para frontend, soporte y observabilidad.
3. **Contexto de request poco gobernado.** `request_id`, `correlation_id`, tenant, bot y user no quedaban normalizados ni propagados como un contrato único de request.
4. **Contratos de respuesta poco maduros.** Existía una base, pero faltaba consistencia de envelope, metadatos y trazabilidad sin romper compatibilidad.
5. **Autenticación y sesiones correctas en lo funcional, pero con madurez operativa insuficiente.** El idle timeout no quedaba gobernado como estado persistido por sesión de manera suficientemente explícita.
6. **Configuración relativamente permisiva.** Faltaba validación más agresiva de secretos inseguros, hosts confiables, cookies, CORS y relaciones entre TTLs.
7. **Observabilidad útil para desarrollo, pero todavía corta para operación.** Faltaba estructuración uniforme con contexto enriquecido automáticamente.
8. **Schemas con margen de endurecimiento.** Había validaciones razonables, pero algunos payloads clave seguían siendo demasiado laxos para un backend más enterprise.
9. **Webhooks y providers con margen de normalización.** Los errores de integración no siempre quedaban mapeados de forma consistente a errores internos serios.
10. **Conexión backend ↔ frontend no suficientemente blindada.** Había compatibilidad funcional, pero no una alineación lo bastante explícita en headers, envelopes y errores.

## 2. Arquitectura objetivo aplicada

Se reforzó una arquitectura con estos principios:

- **HTTP layer**: recibe request, resuelve contexto, aplica middleware, serializa respuesta y mapea excepciones.
- **Application layer**: ejecuta casos de uso, aplica reglas, controla invariantes y orquesta repositorios/providers.
- **Infrastructure layer**: DB, providers, sesiones, SSO, observabilidad y runtimes técnicos.
- **Request context como contrato transversal**: request, correlation, tenant, bot y user quedan disponibles como contexto operativo común.
- **Error contract estable**: todo error relevante puede serializarse a un envelope consistente y trazable.
- **Compatibilidad hacia atrás**: donde el frontend o tests ya consumían formas anteriores, se mantuvo el shape esperado agregando compatibilidad en vez de romper.

## 3. Cambios implementados

### 3.1. Gobernanza de contexto de request

Se agregó `backend/app/request_context.py` para centralizar:

- `request_id`
- `correlation_id`
- `organization_id`
- `bot_id`
- `user_id`
- path / method

Además, se aceptan aliases de headers para compatibilidad:

- org: `x-waos-org-id`, `x-organization-id`, `x-org-id`
- bot: `x-waos-bot-id`, `x-bot-id`
- user: `x-user-id`, `x-waos-user-id`

Si llegan valores conflictivos para el mismo scope, ahora el backend responde con error explícito y trazable, en vez de aceptar ambigüedad silenciosa.

### 3.2. Taxonomía de errores seria y consistente

Se agregó `backend/app/errors.py` con una taxonomía explícita:

- `ValidationAppError`
- `UnauthorizedError`
- `ForbiddenError`
- `NotFoundError`
- `ConflictError`
- `RateLimitedError`
- `TenantIsolationError`
- `ProviderError`
- `StepUpRequiredError`
- `InternalServerAppError`

Los errores ahora se serializan en un envelope consistente con:

- `ok`
- `error.code`
- `error.message`
- `error.category`
- `error.retryable`
- `error.details` cuando aplica
- `request_id`
- `correlation_id`

También se mantuvieron claves heredadas (`detail`, `message`) para no romper consumidores existentes.

### 3.3. Middleware y main endurecidos

En `backend/app/main.py` se reforzó:

- `TrustedHostMiddleware`
- validación de runtime en startup
- exception handlers centralizados para `AppError`, `HTTPException`, `RequestValidationError` y fallback general
- propagación sistemática de `request_id` y `correlation_id`
- logging consistente por request
- headers de seguridad y cache-control más predecibles

### 3.4. Observabilidad estructurada

`backend/app/observability.py` quedó reforzado con logging JSON estructurado y enriquecimiento automático del contexto actual. Ahora los logs pueden incluir de forma consistente:

- tenant
- bot
- user
- request_id
- correlation_id
- endpoint
- resultado
- duración

Se agregaron helpers para distinguir mejor eventos de seguridad y de negocio.

### 3.5. Contratos de salida más sólidos

`backend/app/contracts.py` ahora añade metadatos de contexto (`meta`, `request_id`, `correlation_id`) sin romper el consumo existente. También se agregó un patrón más claro para respuestas paginadas.

### 3.6. Configuración y hardening operativo

`backend/app/config.py` se endureció para validar más agresivamente:

- secretos débiles o default
- URLs inválidas
- CORS wildcard en contextos inseguros
- relaciones inválidas entre TTL de access y refresh
- trust proxy y cookies seguras
- allowed hosts para ambientes no productivos y productivos

El objetivo fue mover la configuración de “permisiva mientras arranca” a “explícita o falla temprano”.

### 3.7. Sesiones y auth con mayor madurez operativa

En `backend/app/platform/security.py`, `backend/app/security.py`, `backend/app/application/auth_service.py` y `backend/app/db.py` se reforzó:

- persistencia explícita de `idle_timeout_minutes` por sesión
- refresh respetando esa política por sesión
- separación más limpia entre errores de auth y errores internos
- compatibilidad del contrato de auth para frontend y tests existentes

### 3.8. Schemas más estrictos

Se endurecieron schemas relevantes en:

- `backend/app/schemas/auth.py`
- `backend/app/schemas/conversations.py`
- `backend/app/schemas/security.py`

Se añadieron límites de longitud, rangos y validaciones de campos críticos para reducir payloads ambiguos o demasiado laxos.

### 3.9. Webhooks y errores de integración

`backend/app/api/handlers/webhooks.py` quedó alineado con la nueva taxonomía para que fallas de firma, provider o recurso inexistente se traduzcan en errores operables y consistentes.

### 3.10. Limpieza arquitectónica real

Se eliminó `backend/app/v8.py`, dejando la versión legacy únicamente bajo `backend/app/legacy/v8.py`. Esto reduce duplicidad arquitectónica visible y alinea mejor el árbol con una arquitectura deliberada en vez de acumulativa.

### 3.11. Conexión backend ↔ frontend corregida

En `frontend/app/lib/api.ts` y `frontend/app/lib/contracts.ts` se reforzó:

- envío de `x-request-id` y `x-correlation-id`
- compatibilidad simultánea de headers modernos y legacy para org/bot
- parsing del nuevo envelope de errores
- exposición de `requestId`, `correlationId` y `details` al runtime frontend

Esto corrige un problema real de drift entre capas y mejora trazabilidad end-to-end.

## 4. Archivos modificados

### Nuevos
- `backend/app/request_context.py`
- `backend/app/errors.py`
- `backend/tests/test_request_context_and_error_contracts.py`
- `docs/backend_enterprise_refactor_report_2026-04-16.md`

### Modificados
- `backend/app/main.py`
- `backend/app/http_runtime.py`
- `backend/app/observability.py`
- `backend/app/config.py`
- `backend/app/contracts.py`
- `backend/app/api/dependencies.py`
- `backend/app/application/uow.py`
- `backend/app/application/auth_service.py`
- `backend/app/application/security_service.py`
- `backend/app/security.py`
- `backend/app/platform/security.py`
- `backend/app/db.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/conversations.py`
- `backend/app/schemas/security.py`
- `backend/app/api/handlers/webhooks.py`
- `backend/tests/conftest.py`
- `frontend/app/lib/api.ts`
- `frontend/app/lib/contracts.ts`

### Eliminados
- `backend/app/v8.py`

## 5. Verificaciones ejecutadas

### Verde
1. **Backend test suite**
   - comando: `cd backend && pytest -q`
   - resultado: `38 passed, 2 warnings`
2. **Frontend smoke**
   - comando: `cd frontend && npm run smoke`
   - resultado: `Smoke OK: 7 critical files present`
3. **Frontend node tests**
   - comando: `cd frontend && npm run test:node`
   - resultado: `11 passed, 0 failed`

Los artefactos de verificación deben publicarse en el store de artefactos del pipeline de CI/CD; este árbol limpio ya no incluye una carpeta local store de artefactos de CI/CD.

### No verde / pendiente honesto
4. **Frontend typecheck completo**
   - comando: `cd frontend && npm run typecheck`
   - resultado: **falla**
   - causa observada: deuda preexistente amplia del frontend (tipos de Next no resueltos, problemas JSX y typing extendidos en muchas páginas), no introducida por los cambios focales de `lib/api.ts` y `lib/contracts.ts`.

Se dejó evidencia textual del fallo en:

- `CI artifact: frontend-typecheck-enterprise-refactor.txt`

## 6. Riesgos mitigados

Los riesgos que sí quedaron mitigados con evidencia son:

- pérdida silenciosa de contexto tenant/bot entre frontend y backend
- errores heterogéneos y poco trazables
- falta de `request_id` / `correlation_id` utilizable de punta a punta
- validación de configuración demasiado permisiva
- sesión con idle timeout sin gobierno operativo suficientemente explícito
- envelopes de error débiles para frontend y soporte
- logging poco consistente para operación e incidentes

## 7. Qué quedó pendiente de una fase 2

Para llevarlo todavía más cerca de una plataforma enterprise completa, lo siguiente conviene como siguiente iteración deliberada:

1. endurecer `policy_engine.py` y autorización por acción sensible con una matriz explícita por dominio
2. introducir circuit breaking / retry policy homogénea en todos los providers
3. ampliar tests de webhooks firmados, replay protection y step-up auth
4. profundizar `performance.py` con métricas por endpoint y percentiles
5. limpiar deuda de typecheck del frontend para poder declarar verde el contrato extremo a extremo también a nivel estático
6. revisar más a fondo consistencia de repositorios y UoW multi-paso en todos los dominios verticales

## 8. Conclusión

La refactorización no fue cosmética. El backend quedó notablemente más serio en cuatro ejes clave:

- **gobernanza operacional** de request, tenant, bot, user y correlación
- **taxonomía de errores** consistente y auditable
- **hardening** de startup, configuración y sesión
- **compatibilidad real** con frontend manteniendo contratos existentes mientras se agrega madurez

El resultado ya no se siente solo como “backend funcional”; se siente más cercano a una base de producto operable, trazable y defendible en producción.
