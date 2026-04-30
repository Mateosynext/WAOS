from __future__ import annotations

from typing import Any

import httpx

from .config import settings
from .db import execute, fetch_one
from .platform import resolve_secret
from .utils import RetryableProviderError, from_json, new_id, to_json, utcnow_iso
from .circuit_breaker import circuit_guard, record_provider_failure, record_provider_success
from .whatsapp_channel_runtime import normalize_whatsapp_outbound_request
from .whatsapp_governance import classify_meta_error_policy, update_whatsapp_number_health
from .whatsapp_connection_state import WHATSAPP_STATUS_SEND_READY, clean_provider_id, is_whatsapp_send_ready


WHATSAPP_TOKEN_KEYS = [
    "META_ACCESS_TOKEN",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_CLOUD_API_ACCESS_TOKEN",
]
WHATSAPP_APP_SECRET_KEYS = [
    "META_APP_SECRET",
    "WHATSAPP_APP_SECRET",
]


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def resolve_whatsapp_access_token(conn, *, organization_id: str, bot_id: str | None) -> str | None:
    for key_name in WHATSAPP_TOKEN_KEYS:
        token = resolve_secret(conn, organization_id=organization_id, bot_id=bot_id, key_name=key_name)
        if token:
            return token
    return None


def resolve_whatsapp_app_secret(conn, *, organization_id: str, bot_id: str | None) -> str | None:
    for key_name in WHATSAPP_APP_SECRET_KEYS:
        secret = resolve_secret(conn, organization_id=organization_id, bot_id=bot_id, key_name=key_name)
        if secret:
            return secret
    return None


def classify_whatsapp_error(status_code: int | None, payload: dict[str, Any] | None = None) -> RetryableProviderError:
    payload = payload or {}
    decision = classify_meta_error_policy(status_code, payload)
    return RetryableProviderError(
        decision.get("message") or "whatsapp_provider_error",
        retryable=bool(decision.get("retryable")),
        status_code=status_code,
        details={
            "provider_error": payload,
            "provider_code": decision.get("provider_code"),
            "retry_after_seconds": decision.get("retry_after_seconds"),
            "error_class": decision.get("error_class"),
            "channel_health": decision.get("health"),
        },
    )


def send_whatsapp_message(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    phone: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    number = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,))
    if not number:
        raise RetryableProviderError("whatsapp_number_not_configured", retryable=False)
    if not clean_provider_id(number.get("phone_number_id")):
        raise RetryableProviderError("whatsapp_phone_number_id_not_verified", retryable=False)
    if not clean_provider_id(number.get("waba_id")):
        raise RetryableProviderError("whatsapp_waba_id_not_verified", retryable=False)
    access_token = resolve_whatsapp_access_token(conn, organization_id=organization_id, bot_id=bot_id)
    if not access_token:
        raise RetryableProviderError("missing_whatsapp_access_token", retryable=False)
    if not is_whatsapp_send_ready(number, access_token_present=bool(access_token)):
        raise RetryableProviderError(
            "whatsapp_not_send_ready",
            retryable=False,
            details={
                "connection_status": number.get("connection_status"),
                "required_status": WHATSAPP_STATUS_SEND_READY,
                "requires": {
                    "real_phone_number_id": True,
                    "real_waba_id": True,
                    "access_token": True,
                    "webhook_verified": True,
                },
            },
        )
    provider_payload = {"messaging_product": "whatsapp", **payload}
    if provider_payload.get("status") != "read":
        provider_payload.update({"recipient_type": "individual", "to": _normalize_phone(phone)})
    allowed, _breaker, _policy = circuit_guard(
        conn,
        provider='meta_whatsapp',
        circuit_key=bot_id or 'global',
        organization_id=organization_id,
        metadata={'module': 'whatsapp.send', 'bot_id': bot_id},
    )
    if not allowed:
        raise RetryableProviderError('whatsapp_circuit_open', retryable=True)
    response = httpx.post(
        f"{settings.meta_graph_api_base}/{number['phone_number_id']}/messages",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=provider_payload,
        timeout=20.0,
    )
    data: dict[str, Any]
    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}
    if response.status_code >= 400:
        record_provider_failure(
            conn,
            provider='meta_whatsapp',
            circuit_key=bot_id or 'global',
            error_text=str(data),
            organization_id=organization_id,
            metadata={'module': 'whatsapp.send', 'bot_id': bot_id, 'status_code': response.status_code},
        )
        update_whatsapp_number_health(conn, organization_id=organization_id, bot_id=bot_id, status_code=response.status_code, payload=data, success=False, event_type="provider_api")
        raise classify_whatsapp_error(response.status_code, data)
    record_provider_success(
        conn,
        provider='meta_whatsapp',
        circuit_key=bot_id or 'global',
        organization_id=organization_id,
        metadata={'module': 'whatsapp.send', 'bot_id': bot_id, 'status_code': response.status_code},
    )
    update_whatsapp_number_health(conn, organization_id=organization_id, bot_id=bot_id, payload=data, success=True, event_type="provider_api")
    external_id = None
    messages = data.get("messages") or []
    if messages:
        external_id = messages[0].get("id")
    return {
        "provider": "meta_cloud_api",
        "status": "sent",
        "phone_number_id": number["phone_number_id"],
        "external_id": external_id,
        "status_code": response.status_code,
        "response": data,
    }



def send_whatsapp_text(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    phone: str,
    body: str,
) -> dict[str, Any]:
    return send_whatsapp_message(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        phone=phone,
        payload={"type": "text", "text": {"body": body}},
    )


def enqueue_manual_whatsapp_message(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str,
    contact_id: str | None,
    body: str | None,
    author_user_id: str | None,
    whatsapp_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_whatsapp_outbound_request(body=body, whatsapp_payload=whatsapp_payload)
    message_id = new_id("msg_manual")
    execute(
        conn,
        """
        INSERT INTO messages
        (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, 'outbound', ?, 'human', ?, NULL, 'queued', ?, ?)
        """,
        (
            message_id,
            organization_id,
            conversation_id,
            contact_id,
            bot_id,
            normalized["kind"],
            normalized["summary"],
            to_json({
                "author_user_id": author_user_id,
                "provider": "queued_for_worker",
                "whatsapp": {
                    "message_type": normalized["message_type"],
                    **normalized["payload"],
                },
            }),
            utcnow_iso(),
        ),
    )
    outbox_id = new_id("out_manual")
    execute(
        conn,
        """
        INSERT INTO outbox_messages
        (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, status, attempts, last_error, scheduled_for, sent_at, created_at, provider_response_json, priority)
        VALUES (?, ?, ?, NULL, ?, 'whatsapp', ?, 'queued', 0, NULL, ?, NULL, ?, '{}', 100)
        """,
        (
            outbox_id,
            organization_id,
            bot_id,
            conversation_id,
            to_json({
                **normalized["payload"],
                "message_type": normalized["message_type"],
                "body": normalized["summary"],
                "message_id": message_id,
                "contact_id": contact_id,
                "source": "manual_human",
            }),
            utcnow_iso(),
            utcnow_iso(),
        ),
    )
    row = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (message_id,))
    row["metadata"] = from_json(row.get("metadata_json"), {})
    return {"message": row, "outbox_id": outbox_id}
