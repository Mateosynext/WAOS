# WAOS Smart Docs Integration Report · 2026-04-25

## Resumen

Se integró una primera versión funcional de **WAOS Smart Docs** al ZIP original. La función convierte solicitudes comerciales en documentos operables: presupuestos, órdenes de trabajo, recibos, propuestas y garantías con PDF, folio, estado, partidas, reglas de aprobación, branding y conversión de presupuesto a orden de trabajo.

## Backend integrado

- Nuevo dominio `backend/app/domains/commercial_documents.py`.
- Nueva migración `backend/db/migrations/016_commercial_documents_v1.sql`.
- Nuevos esquemas `backend/app/schemas/commercial_documents.py`.
- Nuevo router `backend/app/api/routers/commercial_documents.py` incluido en `backend/app/api/router.py`.
- Nuevos handlers `backend/app/api/handlers/commercial_documents.py`.

## Tablas nuevas

- `organization_branding`: logo, colores, datos comerciales y footer del negocio.
- `commercial_document_templates`: plantillas por tipo de documento.
- `commercial_documents`: documento principal con folio, estado, totales, PDF y metadata.
- `commercial_document_items`: conceptos/productos/servicios/cargos/descuentos.
- `commercial_document_events`: historial de eventos y cambios de estado.
- `catalog_quote_rules`: reglas de cotización por producto/servicio: precio fijo, por hora, por visita, domicilio, m2, anticipo, preguntas obligatorias y aprobación.

## API nueva

- `GET /api/v1/commercial-documents/overview`
- `GET /api/v1/commercial-documents`
- `POST /api/v1/commercial-documents`
- `POST /api/v1/commercial-documents/draft-from-catalog`
- `POST /api/v1/commercial-documents/draft-from-conversation`
- `GET /api/v1/commercial-documents/{document_id}/pdf`
- `POST /api/v1/commercial-documents/{document_id}/generate-pdf`
- `POST /api/v1/commercial-documents/{document_id}/status`
- `POST /api/v1/commercial-documents/{document_id}/convert-to-work-order`
- `GET /api/v1/organization-branding`
- `POST /api/v1/organization-branding`
- `GET /api/v1/catalog/quote-rules`
- `POST /api/v1/catalog/quote-rules`

## PDF

El PDF se genera con ReportLab e incluye:

- Encabezado con marca del negocio.
- Logo local si existe o iniciales del negocio como fallback.
- Folio y estado.
- Cliente.
- Resumen financiero.
- Tabla de conceptos.
- Total, anticipo y saldo.
- Condiciones y siguientes pasos.
- Footer de marca WAOS.

## Frontend integrado

- Business Hub ahora tiene pestaña **Documentos**.
- Nueva acción server-side `frontend/app/actions/commercial_documents.ts`.
- Nuevos contracts y normalizadores en `frontend/app/lib/contracts/commerce.ts`.
- Nuevas funciones de datos en `frontend/app/lib/data/commerce.ts`.
- Navegación lateral incluye acceso directo a **Documentos**.

## Flujo funcional entregado

1. El usuario pega la solicitud del cliente en Business Hub > Documentos.
2. WAOS intenta empatarla contra productos/servicios activos del catálogo.
3. Aplica reglas de cotización si existen.
4. Detecta preguntas faltantes y motivos de aprobación.
5. Crea documento con folio.
6. Genera PDF.
7. Permite abrir PDF.
8. Permite marcar como enviado.
9. Permite convertir presupuesto en orden de trabajo.

## Validación ejecutada

- `python3 -S -m py_compile` sobre archivos backend nuevos/modificados.
- `node ./scripts/check-local-imports.mjs` en frontend: OK.

No se ejecutó `npm run typecheck` porque el ZIP entregado no incluye `frontend/node_modules`.
