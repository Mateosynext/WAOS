# Refactor: API contracts + application split

## Qué quedó actualizado

### API / transport layer
- Se agregaron `response_model` explícitos para dominios críticos:
  - `organizations`
  - `conversations`
  - `onboarding`
  - `operational_control`
  - `outcomes`
- Se introdujeron DTOs de salida en `backend/app/schemas/response_models.py`.
- Se normalizaron prefixes por router:
  - `conversations` ahora agrupa subrouters con prefixes por contexto (`/api/v1/conversations`, `/api/v1/inbox`, `/api/v1/leads`, `/api/v1/supervisor`, `/api/v1/qa`).
  - `onboarding` ahora usa `/api/v1/onboarding` y separa `/api/v1/inbox` para saved views.
  - `operational_control` ahora encapsula `/api/v1/client/operations` en router dedicado.
  - `outcomes` ahora usa `APIRouter(prefix="/api/v1/outcomes")`.

### Application layer
Se hizo una primera partición transversal para sacar policy/presentation de servicios grandes:

- `conversation_service.py`
  - `conversation_policies.py`
  - `conversation_presenters.py`
- `outcomes_service.py`
  - `outcomes_policy.py`
  - `outcomes_presenters.py`
- `operational_control_service.py`
  - `operational_control_policy.py`
  - `operational_control_presenters.py`
- `tool_execution_service.py`
  - `tool_execution_policy.py`
  - `tool_execution_presenters.py`

## Validación
- Compilación Python del backend: OK
- Smoke OpenAPI de rutas críticas: OK
