# WAOS Governed Knowledge Runtime Upgrade

## Problema resuelto

El runtime ya tenía `knowledge_embeddings`, pero la recuperación visible seguía muy apoyada en configuración ligera (`hours`, `location`, `faqs`, `services`) y memoria reciente. Eso servía para bootstrap, pero no alcanzaba para un sistema top-tier que opere con conocimiento vivo, versionado y trazable.

## Qué cambia

Esta mejora agrega una capa explícita de **knowledge governance** sobre el runtime agentic:

- ingestión formal de documentos y snapshots de conocimiento
- versionado por documento
- separación por dominio: `commercial`, `operational`, `legal`, `support`
- evaluación de freshness y candidatos de refresh
- invalidación cuando desaparecen fuentes configuradas
- trazabilidad por respuesta y por fuente
- integración directa con planner, grounding y verifier

## Nuevas tablas

### `knowledge_documents`
Catálogo de documentos activos del bot.

Campos clave:
- `domain`
- `source_kind`
- `source_uri`
- `source_key`
- `status`
- `refresh_strategy`
- `refresh_after`
- `freshness_window_days`
- `current_version_id`
- `invalidated_reason`

### `knowledge_document_versions`
Historial versionado del contenido.

Campos clave:
- `version_number`
- `content_text`
- `content_hash`
- `vector_json`
- `supports_json`
- `freshness_status`
- `is_current`

### `knowledge_refresh_events`
Bitácora de ingestión, versionado, invalidación y refresh.

## Nuevo módulo

### `backend/app/knowledge_runtime.py`

Expone las primitivas del subsistema:

- `ensure_knowledge_governance_schema(...)`
- `ingest_knowledge_document(...)`
- `invalidate_knowledge_document(...)`
- `list_refresh_candidates(...)`
- `sync_config_knowledge(...)`
- `search_governed_knowledge(...)`
- `governed_knowledge_summary(...)`

## Flujo operativo

### 1. Ingestión
`sync_config_knowledge(...)` convierte `bot_config.business_knowledge` en documentos gobernados.

Esto deja de tratar la config solamente como memoria de render y la usa como **seed corpus** versionado.

### 2. Versionado
Si cambia el contenido de un `source_key`, se crea una nueva versión y se conserva el historial.

### 3. Invalidación
Si un precio, FAQ o policy desaparece del catálogo/config actual, el documento previo pasa a `invalidated` con razón explícita.

### 4. Retrieval gobernado
`search_governed_knowledge(...)` rankea resultados usando:
- similitud vectorial
- match por dominio/intención
- freshness score
- soporte temático (`pricing`, `schedule`, `payment`, etc.)

### 5. Grounding y planner
`build_grounded_context(...)` ahora agrega:
- `coverage.governed_knowledge`
- `support_status` por tema
- `traceability`
- `knowledge_summary`
- `freshness_status`

`plan_runtime_execution(...)` agrega herramientas explícitas:
- `governed_knowledge`
- `freshness_evaluator`

### 6. Verificación
`verify_runtime_reply(...)` ya no acepta claims operativos delicados solo porque “hay algo parecido” en memoria/config.

Ahora revisa:
- soporte temático por claim
- freshness del conocimiento
- rechazo de pricing/schedule si la base está `stale`

## Dominios

### Commercial
- catálogo
- precios
- bundles
- promociones

### Operational
- horarios
- ubicación
- SOPs
- disponibilidad

### Legal
- políticas
- pagos
- devoluciones
- compliance

### Support
- FAQs
- troubleshooting
- guías de atención

## Tipos de fuente soportados

El runtime ya acepta documentos gobernados con `source_kind` como:
- `config_seed`
- `catalog`
- `policy`
- `sop`
- `faq`
- `pdf`
- `web_page`
- `doc`
- `import`

Esto deja lista la arquitectura para ingestión desde PDFs, páginas web, SOPs o políticas, aunque el fetch/parser específico podrá crecer después por conector o job.

## Efecto arquitectónico

Antes:
- config + embeddings + memory recall

Ahora:
- corpus gobernado versionado
- retrieval trazable
- freshness-aware verification
- invalidación explícita
- seed config como bootstrap, no como única fuente de verdad

## Validación

Tests agregados:
- versionado y búsqueda trazable
- invalidación cuando cambia catálogo/config
- grounding con trazabilidad gobernada
- bloqueo de claims de pricing cuando la fuente está stale

También se validó compatibilidad con la suite previa de runtime/arquitectura.
