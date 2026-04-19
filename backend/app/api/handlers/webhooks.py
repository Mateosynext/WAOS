from __future__ import annotations

from .common import *
from ...application.inbound_service import inbound_service
from ...contracts import ok
from ...errors import ForbiddenError, NotFoundError, ProviderError, ValidationAppError
from ...payments_runtime import handle_stripe_webhook
from ...whatsapp_channel_runtime import apply_whatsapp_provider_error, apply_whatsapp_status_event, flatten_whatsapp_webhook_events, register_whatsapp_event_receipt
from ...whatsapp_safety import apply_quality_rating_update


def simulate_inbound(payload: SimulateInboundRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, payload.bot_id)
        if not bot:
            raise NotFoundError("Bot not found")
        ensure_bot_access(user, bot)
        result = inbound_service.handle_inbound(conn, bot_id=payload.bot_id, phone=payload.phone, name=payload.name, body=payload.body, external_id=f"SIM-{new_id('ext')}", apply_defensive_rate_limit=False)
        create_audit_log(conn, organization_id=bot["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="webhook", entity_id=payload.bot_id, action="simulate.inbound", metadata={"phone": payload.phone})
        return ok(result)



def whatsapp_verify(number_id: str, hub_mode: str | None = Query(alias="hub.mode", default=None), hub_verify_token: str | None = Query(alias="hub.verify_token", default=None), hub_challenge: str | None = Query(alias="hub.challenge", default=None)):
    with get_connection() as conn:
        number = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE phone_number_id = ?", (number_id,))
        if not number:
            raise NotFoundError("Number not found")
        valid = hub_mode == "subscribe" and hub_verify_token == number["webhook_verify_token"]
        if not valid:
            raise ForbiddenError("Invalid verify token", code="webhook_verify_failed")
        return HTMLResponse(content=hub_challenge or "", status_code=200)


async def stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise ValidationAppError("Missing Stripe signature")
    with get_connection() as conn:
        try:
            result = handle_stripe_webhook(conn, payload=payload, signature=signature)
        except Exception as exc:
            raise ProviderError("Stripe webhook processing failed", code="stripe_webhook_failed", retryable=True, details={"reason": str(exc)}) from exc
        return ok(result)


async def whatsapp_webhook(number_id: str, request: Request) -> dict:
    payload = await request.body()
    with get_connection() as conn:
        number = get_whatsapp_number_by_phone_id(conn, number_id)
        if not number:
            raise NotFoundError("Number not found")
        app_secret = resolve_whatsapp_app_secret(
            conn,
            organization_id=number.get("organization_id"),
            bot_id=number.get("bot_id"),
        )
        signature = request.headers.get("x-hub-signature-256")
        if app_secret and signature and not verify_hub_signature(app_secret, payload, signature):
            raise ForbiddenError("Invalid signature", code="webhook_signature_invalid")
        data = WhatsAppWebhookPayload.model_validate(await request.json())
        correlation_id = getattr(request.state, "correlation_id", None)
        inbound_processed: list[dict] = []
        status_processed: list[dict] = []
        provider_errors: list[dict] = []
        ignored: list[dict] = []
        deduplicated: list[dict] = []

        for event in flatten_whatsapp_webhook_events(data):
            if not register_whatsapp_event_receipt(conn, organization_id=number["organization_id"], event=event):
                deduplicated.append({
                    "event_class": event.get("event_class"),
                    "message_id": event.get("message_id"),
                    "message_type": event.get("message_type") or event.get("status"),
                })
                continue
            if event.get("event_class") == "message":
                if not event.get("supported"):
                    ignored.append({"reason": "unsupported_message_type", "message_type": event.get("message_type"), "message_id": event.get("message_id")})
                    continue
                phone = event.get("phone") or "unknown"
                body = event.get("body") or ""
                result = inbound_service.handle_inbound(
                    conn,
                    bot_id=number["bot_id"],
                    phone=phone,
                    name=event.get("profile_name"),
                    body=body,
                    external_id=event.get("message_id"),
                    correlation_id=correlation_id,
                    kind=event.get("kind") or event.get("message_type") or "text",
                    source="whatsapp",
                    metadata={
                        "provider": "meta_cloud_api",
                        "provider_phone_number_id": number_id,
                        "webhook_entry_id": event.get("entry_id"),
                        "webhook_field": event.get("field"),
                        "webhook_metadata": event.get("metadata") or {},
                        **(event.get("metadata") or {}),
                    },
                )
                inbound_processed.append({
                    "message_id": event.get("message_id"),
                    "message_type": event.get("message_type"),
                    "kind": event.get("kind"),
                    "conversation_id": ((result.get("conversation") or {}).get("id")),
                    "inbound_id": ((result.get("inbound_message") or {}).get("id")),
                })
            elif event.get("event_class") == "status":
                status_processed.append(
                    apply_whatsapp_status_event(
                        conn,
                        organization_id=number["organization_id"],
                        bot_id=number.get("bot_id"),
                        conversation_id=None,
                        event=event,
                        correlation_id=correlation_id,
                    )
                )
            elif event.get("event_class") == "provider_error":
                provider_errors.append(
                    apply_whatsapp_provider_error(
                        conn,
                        organization_id=number["organization_id"],
                        bot_id=number.get("bot_id"),
                        event=event,
                        correlation_id=correlation_id,
                    )
                )

        return ok({
            "processed": len(inbound_processed),
            "status_events": len(status_processed),
            "provider_errors": len(provider_errors),
            "ignored": ignored,
            "deduplicated": deduplicated,
            "details": {
                "messages": inbound_processed,
                "statuses": status_processed,
                "errors": provider_errors,
                "deduplicated": deduplicated,
            },
        })


async def whatsapp_quality_webhook(number_id: str, request: Request) -> dict:
    payload = await request.json()
    with get_connection() as conn:
        number = get_whatsapp_number_by_phone_id(conn, number_id)
        if not number:
            raise NotFoundError("Number not found")
        quality_rating = str(payload.get("quality_rating") or payload.get("event", {}).get("quality_rating") or payload.get("value", {}).get("quality_rating") or "").upper()
        if not quality_rating:
            raise ValidationAppError("Missing quality_rating")
        result = apply_quality_rating_update(
            conn,
            organization_id=number.get("organization_id"),
            bot_id=number.get("bot_id"),
            phone_number_id=number_id,
            quality_rating=quality_rating,
            payload=payload,
        )
        return ok(result)
