# Runtime IA, schema y repositories

## Cerrado en esta pasada

### 1. Corte completo a handlers por caso de uso
Se completó el corte de los servicios grandes de application hacia handlers específicos por caso de uso:

- `backend/app/application/conversation_handlers/`
- `backend/app/application/outcomes_handlers/`
- `backend/app/application/operational_control_handlers/`
- `backend/app/application/tool_execution_handlers/`

Los servicios quedaron como fachada delgada y conservan compatibilidad pública.

### 2. Runtime / orquestación IA
Se partió el hub de `ai.py` y `agent_runtime.py` en un paquete explícito:

- `backend/app/ai_runtime/classification.py`
- `backend/app/ai_runtime/planning.py`
- `backend/app/ai_runtime/grounding.py`
- `backend/app/ai_runtime/generation.py`
- `backend/app/ai_runtime/ranking.py`
- `backend/app/ai_runtime/verification.py`
- `backend/app/ai_runtime/memory.py`
- `backend/app/ai_runtime/post_send.py`
- `backend/app/ai_runtime/persistence.py`
- `backend/app/ai_runtime/pipeline.py`
- `backend/app/ai_runtime/orchestration.py`
- `backend/app/ai_runtime/types.py`

`backend/app/ai.py`, `backend/app/agent_runtime.py` y `backend/app/runtime_pipeline.py` quedaron como fronteras/fachadas compatibles.

### 3. Persistencia y esquema
Se introdujo `backend/app/schema_sql.py` para cargar y aplicar migraciones SQL versionadas como fuente principal de verdad.

Se movió el ownership de DDL hacia `backend/db/migrations/*.sql` y se redujo el runtime schema a compatibilidad/transición en:

- `backend/app/live_knowledge_runtime.py`
- `backend/app/proactive_reasoning_runtime.py`
- `backend/app/vertical_onboarding_runtime.py`
- `backend/app/vertical_marketplace_runtime.py`
- `backend/app/migrations.py`

También se completaron definiciones faltantes en migraciones SQL para evitar drift.

### 4. Repositories
Se agregó:

- `backend/app/repositories/base.py`
- `backend/app/repositories/ai_runtime.py`

Y se normalizaron type hints de conexión para evitar depender de `sqlite3.Connection` como contrato público.

## Validación ejecutada

Pasaron estas pruebas objetivo:

- `tests/test_architecture_refactor.py`
- `tests/test_agent_runtime_orchestration.py`
- `tests/test_guided_vertical_onboarding.py`
- `tests/test_vertical_marketplace.py`
- `tests/test_continuous_knowledge_ingestion.py`
- `tests/test_proactive_reasoning_engine.py`
- `tests/test_operational_control_phase6.py`
- `tests/test_outcomes_closed_loop_runtime.py`
- `tests/test_tool_execution_native_runtime.py`
- `tests/test_tool_execution_outcomes_flywheel.py`

Además, se recompilaron módulos críticos con `python -m py_compile`.

## Notas

- Se mantuvo compatibilidad de imports para no romper rutas API ni entrypoints existentes.
- El refactor deja preparada una siguiente pasada para endurecer aún más CQRS y separar algunos helpers transversales que siguen viviendo dentro de servicios puente.
