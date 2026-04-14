from __future__ import annotations

from .common import *
from .common import _handle_inbound
from ...payments_runtime import handle_stripe_webhook


def simulate_inbound(payload: SimulateInboundRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        bot = get_bot(conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        result = _handle_inbound(conn, bot_id=payload.bot_id, phone=payload.phone, name=payload.name, body=payload.body, external_id=f"SIM-{new_id('ext')}")
        create_audit_log(conn, organization_id=bot["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="webhook", entity_id=payload.bot_id, action="simulate.inbound", metadata={"phone": payload.phone})
        return result


def whatsapp_verify(number_id: str, hub_mode: str | None = Query(alias="hub.mode", default=None), hub_verify_token: str | None = Query(alias="hub.verify_token", default=None), hub_challenge: str | None = Query(alias="hub.challenge", default=None)):
    with get_connection() as conn:
        number = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE phone_number_id = ?", (number_id,))
        if not number:
            raise HTTPException(status_code=404, detail="Number not found")
        valid = hub_mode == "subscribe" and hub_verify_token == number["webhook_verify_token"]
        if not valid:
            raise HTTPException(status_code=403, detail="Invalid verify token")
        return HTMLResponse(content=hub_challenge or "", status_code=200)


async def stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    with get_connection() as conn:
        result = handle_stripe_webhook(conn, payload=payload, signature=signature)
        return result


async def whatsapp_webhook(number_id: str, request: Request) -> dict:
    payload = await request.body()
    with get_connection() as conn:
        number = get_whatsapp_number_by_phone_id(conn, number_id)
        if not number:
            raise HTTPException(status_code=404, detail="Number not found")
        app_secret = resolve_whatsapp_app_secret(
            conn,
            organization_id=number.get("organization_id"),
            bot_id=number.get("bot_id"),
        )
        signature = request.headers.get("x-hub-signature-256")
        if app_secret and signature and not verify_hub_signature(app_secret, payload, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")
        data = await request.json()
        processed: list[dict] = []
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = value.get("contacts", []) or []
                messages = value.get("messages", []) or []
                for message in messages:
                    if message.get("type") != "text":
                        continue
                    profile_name = None
                    if contacts:
                        profile_name = (contacts[0].get("profile") or {}).get("name")
                    phone = message.get("from") or "unknown"
                    body = (message.get("text") or {}).get("body") or ""
                    result = _handle_inbound(
                        conn,
                        bot_id=number["bot_id"],
                        phone=phone,
                        name=profile_name,
                        body=body,
                        external_id=message.get("id"),
                    )
                    processed.append(result)
        return {"ok": True, "processed": len(processed)}
