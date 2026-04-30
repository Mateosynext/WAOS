from __future__ import annotations

from typing import Any

from .utils import from_json, to_json, utcnow_iso

WHATSAPP_STATUS_PENDING_SETUP = "pending_setup"
WHATSAPP_STATUS_NUMBER_ENTERED = "number_entered"
WHATSAPP_STATUS_PROVIDER_CONNECTED = "provider_connected"
WHATSAPP_STATUS_WEBHOOK_VERIFIED = "webhook_verified"
WHATSAPP_STATUS_SEND_READY = "send_ready"

WHATSAPP_SETUP_STATES = {
    WHATSAPP_STATUS_PENDING_SETUP,
    WHATSAPP_STATUS_NUMBER_ENTERED,
    WHATSAPP_STATUS_PROVIDER_CONNECTED,
    WHATSAPP_STATUS_WEBHOOK_VERIFIED,
    WHATSAPP_STATUS_SEND_READY,
}

# Legacy aliases are recognized for rendering/migrations, but new writes must not
# persist these values for whatsapp_numbers.connection_status.
LEGACY_WHATSAPP_READY_ALIASES = {"connected", "active", "ready", "live", "verified", "ok"}
_PLACEHOLDER_PREFIXES = ("PHONE-", "WABA-")


def _text(value: Any) -> str:
    return str(value or "").strip()


def is_placeholder_provider_id(value: Any) -> bool:
    upper = _text(value).upper()
    return any(upper.startswith(prefix) for prefix in _PLACEHOLDER_PREFIXES)


def clean_provider_id(value: Any) -> str | None:
    text = _text(value)
    if not text or is_placeholder_provider_id(text):
        return None
    return text


def require_real_provider_ids(*, phone_number_id: Any = None, waba_id: Any = None) -> None:
    bad: list[str] = []
    if is_placeholder_provider_id(phone_number_id):
        bad.append("phone_number_id")
    if is_placeholder_provider_id(waba_id):
        bad.append("waba_id")
    if bad:
        raise ValueError("whatsapp_provider_ids_must_be_real:" + ",".join(bad))


def _metadata_dict(metadata: Any) -> dict[str, Any]:
    if isinstance(metadata, dict):
        return dict(metadata)
    parsed = from_json(metadata, {}) if metadata else {}
    return parsed if isinstance(parsed, dict) else {}


def build_whatsapp_connection_steps(
    *,
    phone_number: Any = None,
    phone_number_id: Any = None,
    waba_id: Any = None,
    access_token_present: bool = False,
    webhook_verified: bool = False,
) -> dict[str, bool]:
    real_phone_number_id = clean_provider_id(phone_number_id)
    real_waba_id = clean_provider_id(waba_id)
    number_entered = bool(_text(phone_number))
    # Provider-connected is intentionally strict: it requires the real Meta
    # phone_number_id, the real WABA id and a stored access token. A captured
    # phone number or one provider id is only setup progress, never "connected".
    provider_connected = bool(real_phone_number_id and real_waba_id and access_token_present)
    webhook_ready = bool(provider_connected and webhook_verified)
    send_ready = webhook_ready
    return {
        WHATSAPP_STATUS_NUMBER_ENTERED: number_entered,
        WHATSAPP_STATUS_PROVIDER_CONNECTED: provider_connected,
        WHATSAPP_STATUS_WEBHOOK_VERIFIED: webhook_ready,
        WHATSAPP_STATUS_SEND_READY: send_ready,
    }


def resolve_whatsapp_connection_status(
    *,
    phone_number: Any = None,
    phone_number_id: Any = None,
    waba_id: Any = None,
    access_token_present: bool = False,
    webhook_verified: bool = False,
) -> str:
    steps = build_whatsapp_connection_steps(
        phone_number=phone_number,
        phone_number_id=phone_number_id,
        waba_id=waba_id,
        access_token_present=access_token_present,
        webhook_verified=webhook_verified,
    )
    if steps[WHATSAPP_STATUS_SEND_READY]:
        return WHATSAPP_STATUS_SEND_READY
    if steps[WHATSAPP_STATUS_WEBHOOK_VERIFIED]:
        return WHATSAPP_STATUS_WEBHOOK_VERIFIED
    if steps[WHATSAPP_STATUS_PROVIDER_CONNECTED]:
        return WHATSAPP_STATUS_PROVIDER_CONNECTED
    if steps[WHATSAPP_STATUS_NUMBER_ENTERED]:
        return WHATSAPP_STATUS_NUMBER_ENTERED
    return WHATSAPP_STATUS_PENDING_SETUP


def update_whatsapp_metadata(
    metadata: Any,
    *,
    phone_number: Any = None,
    phone_number_id: Any = None,
    waba_id: Any = None,
    access_token_present: bool = False,
    webhook_verified: bool = False,
    webhook_verified_at: str | None = None,
    provider_confirmed_at: str | None = None,
    source: str | None = None,
) -> tuple[str, str]:
    data = _metadata_dict(metadata)
    if webhook_verified and not webhook_verified_at:
        webhook_verified_at = _text(data.get("webhook_verified_at")) or utcnow_iso()
    if access_token_present and clean_provider_id(phone_number_id) and not provider_confirmed_at:
        provider_confirmed_at = _text(data.get("provider_confirmed_at")) or utcnow_iso()
    if webhook_verified_at:
        data["webhook_verified_at"] = webhook_verified_at
    if provider_confirmed_at:
        data["provider_confirmed_at"] = provider_confirmed_at
    if source:
        data["connection_state_source"] = source
    status = resolve_whatsapp_connection_status(
        phone_number=phone_number,
        phone_number_id=phone_number_id,
        waba_id=waba_id,
        access_token_present=access_token_present,
        webhook_verified=bool(webhook_verified or data.get("webhook_verified_at")),
    )
    steps = build_whatsapp_connection_steps(
        phone_number=phone_number,
        phone_number_id=phone_number_id,
        waba_id=waba_id,
        access_token_present=access_token_present,
        webhook_verified=bool(webhook_verified or data.get("webhook_verified_at")),
    )
    data["connection_steps"] = steps
    data["connection_status"] = status
    data["ui_status"] = "WhatsApp listo para enviar" if status == WHATSAPP_STATUS_SEND_READY else "WhatsApp pendiente de conexión"
    data["ui_status_detail"] = _status_detail(status)
    return status, to_json(data)


def decorate_whatsapp_number(row: dict[str, Any] | None, *, access_token_present: bool = False) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    metadata = _metadata_dict(data.get("metadata_json"))
    webhook_verified = bool(metadata.get("webhook_verified_at") or (metadata.get("connection_steps") or {}).get(WHATSAPP_STATUS_WEBHOOK_VERIFIED))
    status, metadata_json = update_whatsapp_metadata(
        metadata,
        phone_number=data.get("phone_number"),
        phone_number_id=data.get("phone_number_id"),
        waba_id=data.get("waba_id"),
        access_token_present=access_token_present,
        webhook_verified=webhook_verified,
    )
    rendered_metadata = _metadata_dict(metadata_json)
    data["connection_status"] = status
    data["metadata_json"] = metadata_json
    data["metadata"] = rendered_metadata
    data["connection_steps"] = rendered_metadata.get("connection_steps") or {}
    data["ui_status"] = rendered_metadata.get("ui_status")
    data["ui_status_detail"] = rendered_metadata.get("ui_status_detail")
    data["send_ready"] = status == WHATSAPP_STATUS_SEND_READY
    data["provider_ids_real"] = bool(clean_provider_id(data.get("phone_number_id")) and clean_provider_id(data.get("waba_id")))
    return data


def is_whatsapp_send_ready(row: dict[str, Any] | None, *, access_token_present: bool = False) -> bool:
    """Return true only from verifiable prerequisites, never from a stored label.

    A stale or malicious DB value such as connection_status="send_ready" or a
    legacy "connected" alias must not unlock outbound messaging. Readiness is
    recomputed from real provider ids, a present token and webhook proof.
    """
    if not row:
        return False
    metadata = _metadata_dict(row.get("metadata_json"))
    webhook_verified = bool(
        metadata.get("webhook_verified_at")
        or (metadata.get("connection_steps") or {}).get(WHATSAPP_STATUS_WEBHOOK_VERIFIED)
    )
    steps = build_whatsapp_connection_steps(
        phone_number=row.get("phone_number"),
        phone_number_id=row.get("phone_number_id"),
        waba_id=row.get("waba_id"),
        access_token_present=access_token_present,
        webhook_verified=webhook_verified,
    )
    return bool(steps.get(WHATSAPP_STATUS_SEND_READY))


def _status_detail(status: str) -> str:
    return {
        WHATSAPP_STATUS_PENDING_SETUP: "Falta capturar el número de WhatsApp.",
        WHATSAPP_STATUS_NUMBER_ENTERED: "Número capturado; falta conectar Meta Cloud API con IDs reales y token.",
        WHATSAPP_STATUS_PROVIDER_CONNECTED: "Provider conectado; falta verificar el webhook antes de enviar.",
        WHATSAPP_STATUS_WEBHOOK_VERIFIED: "Webhook verificado; falta completar credenciales operativas para envío.",
        WHATSAPP_STATUS_SEND_READY: "Provider, webhook y credenciales están listos para enviar.",
    }.get(status, "WhatsApp pendiente de conexión.")
