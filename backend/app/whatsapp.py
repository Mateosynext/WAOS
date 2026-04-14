from __future__ import annotations

from typing import Any

import httpx

from .config import settings
from .db import execute, fetch_one
from .platform import resolve_secret
from .utils import RetryableProviderError, from_json, to_json, utcnow_iso


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
    error = payload.get("error") or {}
    code = error.get("code")
    message = error.get("message") or payload.get("message") or "whatsapp_provider_error"
    retryable = False
    if status_code in {408, 409, 423, 429, 500, 502, 503, 504}:
        retryable = True
    if code in {1, 2, 4, 17, 32, 613, 130429, 131016, 131048}:  # rate limit / transient infra buckets
        retryable = True
    if code in {10, 190, 200, 131005, 131008, 131009, 131021, 131031}:  # auth / permission / integrity
        retryable = False
    return RetryableProviderError(message, retryable=retryable, status_code=status_code, details={"provider_error": payload, "provider_code": code})


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
    access_token = resolve_whatsapp_access_token(conn, organization_id=organization_id, bot_id=bot_id)
    if not access_token:
        raise RetryableProviderError("missing_whatsapp_access_token", retryable=False)
    provider_payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": _normalize_phone(phone),
        **payload,
    }
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
        raise classify_whatsapp_error(response.status_code, data)
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
    body: str,
    author_user_id: str | None,
) -> dict[str, Any]:
    message_id = f"msg_manual_{utcnow_iso().replace(':','').replace('-','')}"
    execute(
        conn,
        """
        INSERT INTO messages
        (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, 'outbound', 'text', 'human', ?, NULL, 'queued', ?, ?)
        """,
        (
            message_id,
            organization_id,
            conversation_id,
            contact_id,
            bot_id,
            body,
            to_json({"author_user_id": author_user_id, "provider": "queued_for_worker"}),
            utcnow_iso(),
        ),
    )
    outbox_id = f"out_manual_{utcnow_iso().replace(':','').replace('-','')}"
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
            to_json({"body": body, "message_id": message_id, "contact_id": contact_id, "source": "manual_human"}),
            utcnow_iso(),
            utcnow_iso(),
        ),
    )
    row = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (message_id,))
    row["metadata"] = from_json(row.get("metadata_json"), {})
    return {"message": row, "outbox_id": outbox_id}
