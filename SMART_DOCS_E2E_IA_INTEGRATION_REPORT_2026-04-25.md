# WAOS Smart Docs E2E + IA Integration Report

Fecha: 2026-04-25
Paquete base: `waos_ia_smart_docs_mejorado.zip`
Resultado: integracion end-to-end de Smart Docs con runtime IA, catalogo/documentos, PDF, envio, aceptacion, pagos, ordenes de trabajo y recibos.

## Resumen ejecutivo

Se extendio el modulo WAOS Smart Docs para que deje de ser solo una pantalla de documentos y se conecte con el ciclo comercial completo:

**Conversacion -> IA -> catalogo/reglas -> presupuesto PDF -> link publico -> WhatsApp -> aceptacion -> anticipo/pago -> orden de trabajo -> recibo PDF.**

La integracion conserva la capa inicial de documentos comerciales y agrega funciones E2E reutilizables desde API, runtime IA, pagos y frontend.

## Backend agregado

### Nuevo dominio E2E

Archivo:

- `backend/app/domains/commercial_documents_e2e.py`

Funciones principales:

- `ensure_public_url`: crea link publico firmado para ver documentos.
- `get_public_document`: valida token publico y marca el documento como visto.
- `public_pdf_path`: entrega PDF protegido por token.
- `create_payment_for_document`: crea solicitud de pago/anticipo conectada al documento.
- `send_document`: envia el Smart Doc por WhatsApp con link publico y, si aplica, link de pago.
- `accept_document`: acepta el documento desde panel interno o link publico.
- `mark_document_paid_from_payment`: al confirmar pago, marca documento como pagado, convierte presupuesto en orden de trabajo y genera recibo.
- `maybe_run_runtime`: hook de IA para detectar intencion comercial desde mensajes entrantes y crear Smart Docs automaticamente.
- `build_reply_addendum`: agrega al texto de respuesta de IA el contexto del documento generado.

## API autenticada

Archivos:

- `backend/app/api/handlers/commercial_documents.py`
- `backend/app/api/routers/commercial_documents.py`

Nuevos endpoints:

- `POST /api/v1/commercial-documents/{document_id}/send`
- `POST /api/v1/commercial-documents/{document_id}/accept`
- `POST /api/v1/commercial-documents/{document_id}/payment`

Estos endpoints permiten mandar documentos, aceptarlos internamente y crear cobros/anticipos desde el panel.

## API publica para clientes

Archivos:

- `backend/app/api/handlers/commercial_documents.py`
- `backend/app/api/routers/public.py`

Nuevos endpoints:

- `GET /api/public/commercial-documents/{document_id}?token=...`
- `GET /api/public/commercial-documents/{document_id}/pdf?token=...`
- `GET /api/public/commercial-documents/{document_id}/accept?token=...`

El cliente puede abrir una pagina publica del documento, descargar el PDF, aceptar presupuesto y acceder al link de pago si existe.

## Runtime IA conectado

Archivo:

- `backend/app/ai_runtime/persistence_write.py`

Ahora, cuando WAOS genera respuesta a un mensaje entrante, intenta detectar intencion comercial con:

- clasificacion `pricing` o `payment`, o
- palabras como cotizacion, presupuesto, cuanto cuesta, precio, orden de trabajo, recibo, comprobante, propuesta, garantia, pagar o anticipo.

Si detecta intencion comercial:

1. Crea borrador de Smart Doc desde la conversacion.
2. Genera PDF.
3. Genera link publico.
4. Si no faltan datos ni aprobacion, puede enviarlo automaticamente por WhatsApp.
5. Agrega al texto de respuesta de IA una nota con folio/link/pago.
6. Guarda metadata para trazabilidad.

La automatizacion puede apagarse por configuracion del bot con:

```json
{
  "smart_docs": { "enabled": false }
}
```

o ajustarse con:

```json
{
  "smart_docs": { "auto_send_quotes": false }
}
```

## Pagos conectados

Archivo:

- `backend/app/domains/payments.py`

Cuando se confirma un pago que viene de Smart Docs:

1. Marca el documento comercial como `paid`.
2. Si era presupuesto, crea o reutiliza orden de trabajo.
3. Genera recibo comercial pagado.
4. Genera PDF del recibo.
5. Conserva metadata de referencia del pago y documento original.

## Frontend conectado

Archivos:

- `frontend/app/actions/commercial_documents.ts`
- `frontend/app/business-hub/page.tsx`

La pestaña `Documentos` ahora permite:

- crear Smart Doc desde solicitud de cliente,
- abrir PDF,
- abrir pagina publica para cliente,
- abrir link de pago,
- enviar por WhatsApp,
- aceptar documento,
- crear anticipo/pago,
- convertir presupuesto en orden de trabajo.

## Modelos/schemas nuevos

Archivo:

- `backend/app/schemas/commercial_documents.py`

Nuevos schemas:

- `CommercialDocumentSendRequest`
- `CommercialDocumentAcceptRequest`
- `CommercialDocumentPaymentRequest`

## Validacion realizada

Se compilaron correctamente los archivos backend modificados con:

```bash
/usr/bin/python3 -m py_compile \
backend/app/domains/commercial_documents.py \
backend/app/domains/commercial_documents_e2e.py \
backend/app/api/handlers/commercial_documents.py \
backend/app/api/routers/commercial_documents.py \
backend/app/api/routers/public.py \
backend/app/schemas/commercial_documents.py \
backend/app/domains/payments.py \
backend/app/ai_runtime/persistence_write.py
```

Resultado: OK.

## Nota de validacion frontend

El ZIP no incluye `frontend/node_modules`. Los comandos Node/Next de validacion no pudieron completarse de forma confiable en este entorno. La integracion del frontend se hizo siguiendo la estructura existente de server actions y Business Hub.

## Flujo E2E esperado

1. Cliente pregunta precio o presupuesto por WhatsApp.
2. Runtime IA detecta intencion comercial.
3. WAOS crea Smart Doc desde la conversacion.
4. WAOS consulta catalogo/reglas y arma partidas.
5. WAOS genera PDF.
6. WAOS crea link publico firmado.
7. WAOS envia el documento al cliente si no requiere aprobacion.
8. Cliente abre link publico.
9. Sistema marca documento como visto.
10. Cliente acepta.
11. WAOS crea cobro/anticipo.
12. Cliente paga.
13. WAOS marca documento como pagado.
14. WAOS crea orden de trabajo.
15. WAOS genera recibo PDF.

## Archivos principales modificados

- `backend/app/domains/commercial_documents_e2e.py`
- `backend/app/domains/payments.py`
- `backend/app/ai_runtime/persistence_write.py`
- `backend/app/api/handlers/commercial_documents.py`
- `backend/app/api/routers/commercial_documents.py`
- `backend/app/api/routers/public.py`
- `backend/app/schemas/commercial_documents.py`
- `frontend/app/actions/commercial_documents.ts`
- `frontend/app/business-hub/page.tsx`

## Hardening adicional

La pagina publica del cliente escapa valores dinamicos antes de renderizar HTML para reducir riesgo de inyeccion en datos como folio, titulo, resumen, terminos y partidas.
