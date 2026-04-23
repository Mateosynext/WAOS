# WAOS Release Package

Paquete de release orientado a producción, auditoría técnica y operación verticalizada sobre WhatsApp.

## Qué incluye
- `backend/`: API, runtime, seguridad, worker, esquema y scripts operativos con orquestación agentic explícita (planificación, grounding, verificación y evaluación post-envío).
- `frontend/`: aplicación Next.js lista para despliegue.
- `docs/`: documentación interna y portafolio vertical.
- `scripts/`: tooling de release, gate, escaneo y reportes de tamaño/higiene.

## Qué excluye deliberadamente del runtime release
- Bases SQLite embebidas.
- `__pycache__` y residuos de compilación local.
- PDFs o reportes generados durante operación.
- suites de prueba y artefactos temporales.
- credenciales visibles, usuarios temporales y dominios locales de staging.

## Base de datos de este release
- Este release es **PostgreSQL-only** para runtime, migraciones y despliegue.
- `DATABASE_URL` debe apuntar a PostgreSQL.

## Artefactos de release esperados
Ejecutando `python scripts/release_build.py --output-dir dist` se generan:
- `dist/waos_runtime_<version>-clean-release.zip`: runtime desplegable limpio.
- `dist/waos_audit_docs_<version>-clean-release.zip`: documentación y evidencia de auditoría.
- `dist/waos_source_<version>-clean-release.zip`: código fuente actualizado con tooling de release.
- `dist/RELEASE_MANIFEST.json`: manifiesto con hashes, conteos e higiene aplicada.
- `dist/ARTIFACT_SIZES.json`: reporte de peso y archivos locales/generados removidos del artefacto final.

## Mejoras agentic incluidas en este ZIP
- planner por objetivos con `tool_orchestration` explícita por intención
- grounded context multi-fuente antes de generar
- verifier previo al envío para claims operativos de precio, horario y ubicación
- memory curator y post-send evaluation integrados al runtime
- blueprint explícito para cerrar aprendizaje por outcomes reales sobre prompts, flows, templates, routing y operación humana (`docs/WAOS_OUTCOMES_CLOSED_LOOP.md`)
- control plane backend aterrizado con modelo de datos, API operativa, atribución last-touch, scorecards por version/vertical/funnel y migración aplicada para closed loop (`docs/WAOS_OUTCOMES_CONTROL_PLANE.md`, `backend/db/migrations/004_outcomes_closed_loop.sql`, `backend/app/application/outcomes_service.py`, `backend/app/api/routers/outcomes.py`)

## Validación recomendada antes de publicar
```bash
python -m compileall backend/app backend/worker.py
PYTHONPATH=. pytest -q backend/tests
python backend/scripts/export_openapi.py
bash scripts/validate_release_in_ci.sh
```

## Frontend QA
- `npm run smoke`: verifica superficies críticas mínimas.
- `npm run test:node`: ejecuta pruebas Node/TS sin navegador.
- `npm run test:e2e:real`: ejecuta Playwright contra frontend real + backend FastAPI vivo con SQLite efímero y seeds reproducibles.
- `npm run test:critical`: corre smoke + node tests + una variante crítica de browser E2E real.

## Notas operativas
- `RUN_BOOTSTRAP_SEED` queda desactivado por default.
- Si se activa bootstrap, exige credenciales explícitas por entorno.
- El directorio `backend/app/artifacts/reports/` se entrega vacío para generación runtime y source release, preservando solo `.gitkeep`.


## Higiene y trazabilidad del empaquetado
- El source tree de trabajo debe permanecer libre de SQLite local, PDFs generados y `*.tsbuildinfo` antes de distribuirse.
- `scripts/release_build.py` ahora sanea también el source artifact para que no arrastre reportes runtime ni residuos locales.
- `scripts/release_gate.py` falla si el runtime incluye bases locales, `*.tsbuildinfo` o PDFs generados.
- `dist/ARTIFACT_SIZES.json` deja evidencia del peso final y de los archivos locales/generados eliminados del paquete.
- `scripts/check_repo_hygiene.py` y `scripts/release_gate.py --profile source` ahora también validan referencias `docs/*.md` y fugas legacy en raíz.

## Revisión de mantenibilidad
- Se extrajeron adapters y políticas de ejecución a `backend/app/application/tool_execution_adapters.py` para reducir complejidad en `tool_execution_service.py`.
- La revisión de siguientes candidatos de refactor quedó documentada en `docs/MAINTAINABILITY_REVIEW_2026-04-18.md`.

## Render + Vercel
- Render usa preferentemente `render.yaml` en raíz; `backend/render.yaml` queda como copia explícita del backend.
- El endpoint `GET /api/v1/system/deploy-checklist` resume coherencia de despliegue.
- Vercel debe usar `Root Directory = frontend`.
- El frontend exige envs correctos en build y trae `frontend/.env.vercel.example` + `frontend/.vercelignore`.
- El backend trae `backend/.env.render.example` para cargar variables mínimas de Render.
- Ruta única de handoff: `RELEASE_HANDOFF.md` y `docs/WAOS_RELEASE_CANDIDATE_HANDOFF.md`.
- Validación local rápida: `bash scripts/release_candidate_smoke.sh`.

## Frontend fallback vertical
- El fallback de verticales ya no vive como un blob único: quedó modularizado en `frontend/app/lib/vertical-fallback/`.
- Cada vertical vive en `profiles/*.json`, con `index.json` como índice versionado y loader validado por contrato al cargar.
- `getFallbackVerticalProfile(...)` puede resolver una vertical concreta sin cargar todo el catálogo primero.

## Browser E2E real
- El modo real arranca `backend/scripts/run_browser_e2e_server.py`.
- Ese script levanta FastAPI con base SQLite efímera, seeds reproducibles y providers falsos solo para pruebas de navegador.
- Los artifacts del modo real se publican desde Playwright (`playwright-report`, `test-results`, traces, screenshots y video en fallos).


## WhatsApp anti-blocking hardening

- `docs/WAOS_WHATSAPP_ANTI_BLOCKING_HARDENING.md`
- `backend/db/migrations/005_whatsapp_anti_blocking_guardrails.sql`


## Native external tool execution runtime

WAOS now exposes a typed operational execution layer under `/api/v1/tool-executions/*` so the system can move from recommending actions to actually executing them.

Included in this upgrade:
- typed actions: `book_appointment`, `reschedule`, `create_payment_link`, `update_contact_stage`, `send_receipt`
- preview + confirmation + execute flow for high-impact actions
- adapter resolution by integration/provider (`google_calendar`, `stripe`, `waos_crm`, `waos_calendar`)
- idempotent execution keys backed by `job_idempotency_keys`
- execution runs and step logs in `tool_execution_runs` and `tool_execution_step_logs`
- unified audit trail for every preview, success, replay and failure


## Tool execution ↔ outcomes flywheel

- Cada `tool_execution_run` exitoso crea una `outcome_exposure` automática con `tool_execution_run_id`, `tool_action`, `tool_adapter_key` y `tool_provider`.
- El runtime emite outcomes operativos inmediatos (`appointment_scheduled`, `payment_started`, `lead_stage_progressed`, `receipt_sent`) y deja la ejecución lista para ser atribuida por outcomes reales posteriores como `appointment_attended`, `payment_completed` o `sale_closed`.
- Los scorecards se recomputan automáticamente por `tool_action`, `tool_adapter`, `tool_provider` y `tool_execution_run`, además de vertical y funnel stage.
- `GET /api/v1/tool-executions/runs/{id}` ahora incluye `closed_loop` con exposición vinculada, eventos automáticos, atribución posterior y scorecards vigentes.

## Multi-agent intent orchestration

WAOS ahora separa el runtime por objetivo operacional con un router de intención y agentes especialistas.

Incluido en esta mejora:
- `intent_router_v1` para enrutar a `booking`, `sales`, `support`, `collections`, `recovery`, `retention` o `general`
- prompts base y políticas por especialista (`prompt_specialist_*`)
- memoria compartida `shared_memory_v1` con contexto de lead, citas, pagos, outcomes y ejecuciones previas
- supervisor `specialist_supervisor_v1` para revisar riesgo y forzar handoff cuando aplica
- persistencia de routing en `agent_routing_runs`
- exposures y scorecards por `specialist_agent` dentro del closed loop existente
- endpoints nuevos bajo `/api/v1/agent-orchestration/*`

Referencia: `docs/WAOS_MULTI_AGENT_INTENT_ORCHESTRATION.md`

## Agent policy engine by specialist

WAOS ahora agrega una capa de policy engine por specialist para que cada agente opere con límites, SLAs y enforcement propios.

Incluido en esta mejora:
- profiles por agente: `booking_ops`, `sales_ops`, `support_ops`, `collections_ops`, `recovery_ops`, `retention_ops`, `general_ops`
- budgets operativos por intención y contacto, por ejemplo `max_payment_links_per_contact_24h`, `max_reschedules_per_contact_7d` y `max_routes_per_conversation_1h`
- SLAs por specialist con estados `healthy`, `at_risk`, `breached` y `unknown`
- persistencia de evaluaciones en `agent_policy_evaluations`
- enforcement integrado en `agent-orchestration` y `tool-executions`
- exposures y scorecards también por `policy_profile`
- endpoints nuevos bajo `/api/v1/agent-policy/*`

Referencia: `docs/WAOS_AGENT_POLICY_ENGINE.md`



## Continuous knowledge ingestion

This release adds a live knowledge ingestion layer with native source connections, watcher/sync runs, validation, versioning and publication into the governed knowledge runtime. Runtime retrieval keeps using `knowledge_documents`, but now those documents can be refreshed continuously from Notion, Drive, URLs, PDFs and internal forms through `knowledge_source_connections`, `knowledge_source_sync_runs`, `knowledge_source_sync_items` and `knowledge_source_publications`.


## Proactive reasoning engine

WAOS ahora puede detectar señales del negocio y decidir proactivamente a quién contactar, cuándo, con qué objetivo y con qué mensaje.

Incluido en esta mejora:
- señales reales persistidas: `appointment_upcoming`, `payment_failed`, `payment_pending`, `no_response_hot_lead`, `repeat_purchase_window`, `churn_risk`
- scoring y prioridad por candidato en `proactive_contact_candidates`
- playbooks proactivos materializados en `proactive_playbook_runs`
- policy de frecuencia y elegibilidad conectada al specialist adecuado
- exposure automática opcional al materializar para alimentar scorecards por `playbook` dentro del closed loop existente
- endpoints nuevos bajo `/api/v1/proactive-engine/*`

Referencia: `docs/WAOS_PROACTIVE_REASONING_ENGINE.md`

## Multi-candidate response ranking

WAOS ahora puede generar varias respuestas candidatas antes de enviar una sola.

Incluido en esta mejora:
- pipeline `generate N -> verify each -> score -> select best -> send`
- variantes controladas de tono, CTA, longitud y framing
- ranking persistido en `response_candidate_rankings`
- resumen de selección en `message_ai_runs.selected_variant`, `candidate_count`, `ranking_version` y `ranking_summary_json`
- exposures con `assigned_variant` para scorecards por `response_variant`

Referencia: `docs/WAOS_MULTI_CANDIDATE_RESPONSE_RANKING.md`


## Guided vertical onboarding

WAOS ahora incluye un wizard de onboarding verticalizado para acelerar activacion por industria y subvertical.

Incluido en esta mejora:
- blueprint por `vertical` y `subvertical` con defaults inteligentes de tono, catalogo, FAQs, politicas, CTAs, flows e integraciones
- persistencia de wizard en `vertical_onboarding_wizards` y `vertical_onboarding_step_runs`
- aplicacion real sobre `bots`, `organizations`, `bot_behavior_settings`, `bot_response_templates`, `catalog_services`, `knowledge_documents` e `integration_connections`
- endpoints nuevos bajo `/api/v1/onboarding/wizard/*`

Referencia: `docs/WAOS_GUIDED_VERTICAL_ONBOARDING.md`


## Latest runtime upgrade

- Voice is now a first-class channel with native session/turn orchestration, urgency detection, barge-in handling, and voice↔text handoff on the same runtime memory and policy stack.


## Vertical Marketplace

WAOS ahora incluye un marketplace de verticales y paquetes instalables con versionado, manifest, compatibilidad, instalación por organización/bot y upgrades controlados. Ver `docs/WAOS_VERTICAL_MARKETPLACE.md`.

- WAOS_GROWTH_OS.md
