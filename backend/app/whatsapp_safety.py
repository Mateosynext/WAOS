from __future__ import annotations

import re
from typing import Any

from .db import execute, fetch_one, table_exists
from .utils import add_minutes, add_seconds, from_json, new_id, parse_iso, to_json, utcnow, utcnow_iso

DEFAULT_VERIFIED_LIMITS = {
    "per_second": 80,
    "per_day": 250000,
    "per_contact_5m": 6,
}
DEFAULT_UNVERIFIED_LIMITS = {
    "per_second": 1,
    "per_day": 1000,
    "per_contact_5m": 3,
}
OPTOUT_KEYWORDS = {
    "stop", "unsubscribe", "cancel", "cancelar", "baja", "no mas", "no más", "salir", "remove",
}
PROHIBITED_PATTERNS = [
    (r"bit\.ly|tinyurl|goo\.gl|t\.co/", "shortened_link"),
    (r"\b(click aqui|click aquí|haz click aqui|haz click aquí|haz clic aqui|haz clic aquí|click here)\b", "clickbait_cta"),
    (r"🚨|⚠️|❗{2,}", "spam_urgency_emojis"),
    (r"\b(mlm|multinivel|piramide|pirámide)\b", "prohibited_scheme"),
]
SPAM_PHRASES = [
    (r"\bgratis\b", "promotional_free_claim"),
    (r"\burgente\b", "spam_urgency_word"),
    (r"\bhaz click aqui\b|\bhaz click aquí\b|\bclick aqui\b|\bclick aquí\b", "spam_clickbait"),
]
VERTICAL_BLOCKLISTS = {
    "dental": [
        (r"\b(receta|prescripcion|prescripción|antibiotico|antibiótico)\b", "medical_prescription_claim"),
    ],
}


def _stringify(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(value: str) -> str:
    lowered = _stringify(value).lower()
    lowered = lowered.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def is_opt_out_request(text: str) -> bool:
    normalized = _normalize_text(text)
    if normalized in OPTOUT_KEYWORDS:
        return True
    compact = re.sub(r"[^a-z0-9 ]+", "", normalized)
    return compact in OPTOUT_KEYWORDS


def _safe_text_from_payload(payload: dict[str, Any]) -> str:
    provider_payload = payload.get("provider_payload") if isinstance(payload.get("provider_payload"), dict) else {}
    if isinstance((provider_payload.get("text") or {}), dict):
        body = _stringify((provider_payload.get("text") or {}).get("body"))
        if body:
            return body
    if isinstance((payload.get("text") or {}), dict):
        body = _stringify((payload.get("text") or {}).get("body"))
        if body:
            return body
    return _stringify(payload.get("body") or payload.get("summary"))


def validate_message_content(*, text: str, vertical: str | None = None) -> dict[str, Any]:
    normalized = _normalize_text(text)
    violations: list[dict[str, str]] = []
    severity = "ok"
    if not normalized:
        return {"ok": True, "severity": severity, "violations": violations, "normalized_text": normalized}

    for pattern, code in PROHIBITED_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            violations.append({"code": code, "pattern": pattern, "action": "block"})
            severity = "block"

    for pattern, code in SPAM_PHRASES:
        if re.search(pattern, normalized, re.IGNORECASE):
            violations.append({"code": code, "pattern": pattern, "action": "review"})
            if severity != "block":
                severity = "review"

    for pattern, code in VERTICAL_BLOCKLISTS.get(_normalize_text(vertical or ""), []):
        if re.search(pattern, normalized, re.IGNORECASE):
            violations.append({"code": code, "pattern": pattern, "action": "block"})
            severity = "block"

    return {
        "ok": severity != "block",
        "severity": severity,
        "violations": violations,
        "normalized_text": normalized,
    }


def whatsapp_business_profile(number: dict[str, Any]) -> dict[str, Any]:
    metadata = from_json(number.get("metadata_json"), {})
    business = metadata.get("business_profile") if isinstance(metadata.get("business_profile"), dict) else {}
    verified = bool(business.get("verified") or business.get("verified_name") or metadata.get("verified_name"))
    quality_rating = _stringify(number.get("quality_rating") or business.get("quality_rating") or "unknown").upper() or "UNKNOWN"
    limits = DEFAULT_VERIFIED_LIMITS if verified else DEFAULT_UNVERIFIED_LIMITS
    return {
        "verified": verified,
        "verification_status": "verified" if verified else "unverified",
        "verified_name": business.get("verified_name") or metadata.get("verified_name"),
        "quality_rating": quality_rating,
        "limits": limits,
    }


def evaluate_outbound_rate_limit(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    contact_id: str | None,
    number: dict[str, Any],
    outbox_id: str | None = None,
) -> dict[str, Any]:
    profile = whatsapp_business_profile(number)
    limits = profile["limits"]
    now_iso = utcnow_iso()
    since_second = add_seconds(now_iso, -1)
    since_day = add_seconds(now_iso, -86400)
    second_row = fetch_one(
        conn,
        "SELECT COUNT(*) AS value FROM outbox_messages WHERE bot_id = ? AND channel = 'whatsapp' AND status IN ('running','sent','delivered','read') AND (? IS NULL OR id != ?) AND COALESCE(sent_at, created_at) >= ?",
        (bot_id, outbox_id, outbox_id, since_second),
    )
    day_row = fetch_one(
        conn,
        "SELECT COUNT(*) AS value FROM outbox_messages WHERE bot_id = ? AND channel = 'whatsapp' AND status IN ('running','sent','delivered','read') AND (? IS NULL OR id != ?) AND COALESCE(sent_at, created_at) >= ?",
        (bot_id, outbox_id, outbox_id, since_day),
    )
    per_contact_current = 0
    if contact_id:
        since_contact = add_minutes(now_iso, -5)
        message_id_expr = "json_extract(om.payload_json, '$.message_id')"
        if getattr(conn, "backend", "sqlite") == "postgresql":
            message_id_expr = "CAST(om.payload_json AS jsonb) ->> 'message_id'"
        joined = fetch_one(
            conn,
            f"""
            SELECT COUNT(*) AS value
            FROM outbox_messages om
            JOIN messages m ON m.id = {message_id_expr}
            WHERE om.bot_id = ? AND om.channel = 'whatsapp'
              AND om.status IN ('running','sent','delivered','read')
              AND (? IS NULL OR om.id != ?)
              AND m.contact_id = ?
              AND COALESCE(om.sent_at, om.created_at) >= ?
            """,
            (bot_id, outbox_id, outbox_id, contact_id, since_contact),
        )
        per_contact_current = int((joined or {}).get("value") or 0)
    allowed = True
    reason_code = "ok"
    retry_after_seconds = None
    if int((second_row or {}).get("value") or 0) >= int(limits["per_second"]):
        allowed = False
        reason_code = "rate_limit_per_second_exceeded"
        retry_after_seconds = 1
    elif int((day_row or {}).get("value") or 0) >= int(limits["per_day"]):
        allowed = False
        reason_code = "rate_limit_per_day_exceeded"
        retry_after_seconds = 3600
    elif contact_id and per_contact_current >= int(limits["per_contact_5m"]):
        allowed = False
        reason_code = "rate_limit_per_contact_burst_exceeded"
        retry_after_seconds = 300
    return {
        "allowed": allowed,
        "reason_code": reason_code,
        "retry_after_seconds": retry_after_seconds,
        "limits": limits,
        "current": {
            "per_second": int((second_row or {}).get("value") or 0),
            "per_day": int((day_row or {}).get("value") or 0),
            "per_contact_5m": per_contact_current,
        },
        "verification_status": profile["verification_status"],
    }


def is_contact_suppressed(conn, *, organization_id: str, bot_id: str, contact_id: str | None, phone: str | None = None) -> dict[str, Any]:
    if not table_exists(conn, "whatsapp_opt_outs"):
        return {"suppressed": False}
    row = None
    if contact_id:
        row = fetch_one(conn, "SELECT * FROM whatsapp_opt_outs WHERE organization_id = ? AND bot_id = ? AND contact_id = ? AND active = 1 ORDER BY updated_at DESC LIMIT 1", (organization_id, bot_id, contact_id))
    if not row and phone:
        row = fetch_one(conn, "SELECT * FROM whatsapp_opt_outs WHERE organization_id = ? AND bot_id = ? AND phone = ? AND active = 1 ORDER BY updated_at DESC LIMIT 1", (organization_id, bot_id, phone))
    return {"suppressed": bool(row), "record": row}


def register_opt_out(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    contact_id: str | None,
    conversation_id: str | None,
    phone: str | None,
    source_message_id: str | None,
    keyword: str,
) -> dict[str, Any]:
    now = utcnow_iso()
    existing = None
    if table_exists(conn, "whatsapp_opt_outs"):
        if contact_id:
            existing = fetch_one(conn, "SELECT * FROM whatsapp_opt_outs WHERE organization_id = ? AND bot_id = ? AND contact_id = ? LIMIT 1", (organization_id, bot_id, contact_id))
        if not existing and phone:
            existing = fetch_one(conn, "SELECT * FROM whatsapp_opt_outs WHERE organization_id = ? AND bot_id = ? AND phone = ? LIMIT 1", (organization_id, bot_id, phone))
    if existing:
        execute(
            conn,
            "UPDATE whatsapp_opt_outs SET active = 1, keyword = ?, source_message_id = ?, conversation_id = COALESCE(?, conversation_id), updated_at = ? WHERE id = ?",
            (keyword, source_message_id, conversation_id, now, existing["id"]),
        )
        row_id = existing["id"]
    else:
        row_id = new_id("waopt")
        execute(
            conn,
            "INSERT INTO whatsapp_opt_outs (id, organization_id, bot_id, contact_id, conversation_id, phone, keyword, source_message_id, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (row_id, organization_id, bot_id, contact_id, conversation_id, phone, keyword, source_message_id, now, now),
        )
    if conversation_id:
        execute(
            conn,
            "UPDATE conversations SET ai_active = 0, human_takeover = 1, automation_freeze_until = ?, updated_at = ? WHERE id = ?",
            (add_minutes(now, 1440), now, conversation_id),
        )
    return fetch_one(conn, "SELECT * FROM whatsapp_opt_outs WHERE id = ?", (row_id,)) or {"id": row_id, "active": 1}


def apply_quality_rating_update(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    phone_number_id: str,
    quality_rating: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    number = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,))
    if not number:
        return {}
    metadata = from_json(number.get("metadata_json"), {})
    business = metadata.setdefault("business_profile", {})
    quality = _stringify(quality_rating).upper() or "UNKNOWN"
    business["quality_rating"] = quality
    if payload:
        business["last_quality_webhook"] = payload
    quality_status = "healthy"
    if quality == "RED":
        quality_status = "blocked"
    elif quality == "YELLOW":
        quality_status = "at_risk"
    now = utcnow_iso()
    execute(
        conn,
        "UPDATE whatsapp_numbers SET quality_rating = ?, quality_status = ?, metadata_json = ?, last_health_check_at = ?, updated_at = ? WHERE phone_number_id = ?",
        (quality, quality_status, to_json(metadata), now, now, phone_number_id),
    )
    if quality == "RED":
        execute(conn, "UPDATE bots SET ai_paused = 1, updated_at = ? WHERE id = ?", (now, bot_id))
        execute(conn, "UPDATE conversations SET ai_active = 0, human_takeover = 1, automation_freeze_until = ?, updated_at = ? WHERE bot_id = ? AND status != 'closed'", (add_minutes(now, 1440), now, bot_id))
    return {
        "phone_number_id": phone_number_id,
        "quality_rating": quality,
        "quality_status": quality_status,
        "bot_paused": quality == "RED",
    }
