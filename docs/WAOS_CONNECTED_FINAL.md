# WAOS connected final

Esta versión deja el motor v12 conectado con adaptadores concretos dentro del paquete.

## Qué quedó conectado

- Stripe checkout para comandos transaccionales monetarios.
- Webhook de Stripe que actualiza `commerce_payments` y sincroniza de vuelta el `vertical_transaction_account`.
- Google Calendar para comandos de booking/capacidad.
- Sincronización automática de citas al calendario cuando existe integración activa.
- WhatsApp/outbox para notificaciones operativas ya existentes del sistema.

## Comandos conectados

### Cobro
- `create_quote`
- `request_deposit`
- `capture_order`
- `sell_session_package`
- `propose_fee`

Estos comandos crean `commerce_payments` con metadata del `vertical_transaction_account` y generan link de pago con Stripe si la integración está configurada.

### Agenda
- `reserve_capacity`
- `confirm_booking`
- `schedule_service_window`

Estos comandos crean `appointments` y, si existe integración Google Calendar activa, hacen sync al calendario.

## Variables y secretos

### Stripe
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

### Google Calendar
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_ACCESS_TOKEN`
- `GOOGLE_REFRESH_TOKEN`

### Modo fake para smoke/E2E locales
- `WAOS_E2E_FAKE_PROVIDERS=true`

Con ese flag:
- Stripe genera checkout fake pero consistente.
- Google Calendar responde disponibilidad/listado/sync fake sin pegarle a Google.

## Límite honesto de esta entrega

Quedó conectado a nivel de código, persistencia, endpoints y pruebas de humo.
Lo que todavía depende de credenciales e infraestructura del ambiente:

- claves reales de Stripe
- OAuth real de Google
- URLs públicas reales para webhooks
- reverse proxy / SSL / dominio productivo

## Secuencia mínima de producción

1. Configurar integraciones por tenant/bot.
2. Guardar secretos reales.
3. Exponer:
   - `POST /webhooks/stripe`
   - `GET/POST /webhooks/whatsapp/{number_id}`
   - `GET /api/v1/integrations/oauth/google/callback`
4. Activar auto sync si aplica.
5. Ejecutar smoke test post deploy.
