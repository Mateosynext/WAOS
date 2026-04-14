# WAOS v12 transactional runtime

Esta entrega ejecuta las 11 verticales sobre un núcleo transaccional común y persistente.

## Qué agrega

- cuentas transaccionales por vertical (`vertical_transaction_accounts`)
- comandos idempotentes (`vertical_transaction_commands`)
- event log append-only (`vertical_transaction_events`)
- ledger financiero (`vertical_transaction_ledger`)
- readiness documental (`vertical_transaction_documents`)
- reservas y locking operativo (`vertical_transaction_resources`)
- proyecciones / vistas (`vertical_transaction_views`)

## API nueva

- `POST /api/v1/vertical-transactions/accounts`
- `GET /api/v1/vertical-transactions/accounts/{account_id}`
- `POST /api/v1/vertical-transactions/accounts/{account_id}/commands`
- `POST /api/v1/vertical-transactions/accounts/{account_id}/execute-playbook`

## Modelo operativo

El motor no codifica 11 backends separados. Lee `transactional_motor_v12` del perfil vertical y usa:

- catálogo de comandos
- catálogo de eventos
- aggregate root
- unidad transaccional
- vistas operativas
- guards / compliance

## Resultado

Cada vertical puede abrir una cuenta transaccional, ejecutar su playbook completo, emitir eventos, mover estados, registrar dinero, marcar documentos, reservar recursos y refrescar vistas operativas.
