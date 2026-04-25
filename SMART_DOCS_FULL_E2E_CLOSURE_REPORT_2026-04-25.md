# WAOS Smart Docs - cierre end-to-end real

Fecha: 2026-04-25

Este paquete refuerza la integración de Smart Docs para que el flujo quede conectado desde la IA hasta el cobro confirmado por proveedor.

## Flujo E2E cubierto

1. Mensaje entrante de WhatsApp.
2. Runtime de IA detecta intención comercial: cotización, presupuesto, precio, anticipo, recibo, comprobante, garantía o pago.
3. WAOS crea borrador desde conversación y catálogo.
4. El catálogo alimenta partidas, precio, reglas de cotización, anticipo, preguntas faltantes y aprobación humana.
5. Se genera PDF con branding del negocio.
6. Se crea link público firmado para que el cliente vea y acepte el documento.
7. Business Hub puede enviar el documento por WhatsApp.
8. Si aplica, se crea anticipo/pago conectado al documento.
9. Cuando Stripe/webhook/refresh/reconciliación marca el pago como pagado, Smart Docs cierra el flujo automáticamente.
10. El presupuesto cambia a pagado.
11. El presupuesto se convierte en orden de trabajo.
12. Se genera recibo comercial con PDF.
13. Se genera link público del recibo.
14. Se manda mensaje de recibo por WhatsApp cuando hay conversación y bot disponibles.
15. Todo queda trazado en eventos de documento y metadata de pago.

## Cierre adicional implementado en esta versión

- `backend/app/payments_runtime/implementation.py`
  - `_mark_payment_paid` ahora dispara `mark_document_paid_from_payment` cuando el pago trae `commercial_document_id` en metadata.
  - Esto conecta pagos confirmados por Stripe, refresh manual y reconciliación programada con Smart Docs.

- `backend/app/domains/commercial_documents_e2e.py`
  - Al confirmar pago, el sistema crea o reutiliza recibo.
  - Genera PDF de recibo.
  - Genera link público firmado de recibo.
  - Envía el recibo por WhatsApp si hay contexto de conversación.
  - Marca metadata del pago con `smart_docs_receipt_sent_at` y `smart_docs_receipt_id` para evitar duplicados.

## Validación realizada

- Compilación Python con `py_compile` de los archivos modificados:
  - `backend/app/domains/commercial_documents_e2e.py`
  - `backend/app/payments_runtime/implementation.py`

## Nota

No se ejecutó typecheck completo de frontend porque el ZIP no incluye `node_modules`. La integración frontend existente se conserva y el cierre añadido es principalmente backend/runtime, donde faltaba la conexión de pagos de proveedor hacia Smart Docs.
