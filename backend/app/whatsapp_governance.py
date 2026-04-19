from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from .db import execute, fetch_all, fetch_one, table_exists
from .utils import add_seconds, from_json, new_id, parse_iso, to_json, utcnow, utcnow_iso
from .world_class_ext import register_channel_event
from .domains.whatsapp_templates import resolve_whatsapp_template_for_payload
from .whatsapp_safety import evaluate_outbound_rate_limit, is_contact_suppressed, validate_message_content, whatsapp_business_profile

CUSTOMER_CARE_WINDOW_HOURS = 24
DEFAULT_TEMPLATE_LANGUAGE = "es_MX"
DEFAULT_THROUGHPUT_BY_TIER = {
    "standard": 80,
    "high": 250,
    "premium": 500,
    "ultra": 1000,
}
NON_TEMPLATE_EXEMPT_TYPES = {"mark_as_read"}

META_ERROR_POLICIES: dict[int, dict[str, Any]] = {
    1: {"retryable": True, "retry_after_seconds": 30, "error_class": "transient_infra", "health": "degraded"},
    2: {"retryable": True, "retry_after_seconds": 30, "error_class": "transient_infra", "health": "degraded"},
    4: {"retryable": True, "retry_after_seconds": 120, "error_class": "rate_limit", "health": "degraded"},
    17: {"retryable": True, "retry_after_seconds": 300, "error_class": "rate_limit", "health": "degraded"},
    32: {"retryable": True, "retry_after_seconds": 300, "error_class": "rate_limit", "health": "degraded"},
    613: {"retryable": True, "retry_after_seconds": 300, "error_class": "rate_limit", "health": "degraded"},
    130429: {"retryable": True, "retry_after_seconds": 900, "error_class": "throughput_limit", "health": "degraded"},
    131016: {"retryable": True, "retry_after_seconds": 180, "error_class": "service_unavailable", "health": "degraded"},
    131048: {"retryable": True, "retry_after_seconds": 600, "error_class": "spam_rate_limit", "health": "degraded"},
    10: {"retryable": False, "retry_after_seconds": None, "error_class": "permission_denied", "health": "blocked"},
    190: {"retryable": False, "retry_after_seconds": None, "error_class": "auth_invalid", "health": "blocked"},
    200: {"retryable": False, "retry_after_seconds": None, "error_class": "permission_denied", "health": "blocked"},
    131005: {"retryable": False, "retry_after_seconds": None, "error_class": "access_denied", "health": "blocked"},
    131008: {"retryable": False, "retry_after_seconds": None, "error_class": "template_invalid", "health": "at_risk"},
    131009: {"retryable": False, "retry_after_seconds": None, "error_class": "parameter_invalid", "health": "at_risk"},
    131021: {"retryable": False, "retry_after_seconds": None, "error_class": "recipient_unavailable", "health": "at_risk"},
    131031: {"retryable": False, "retry_after_seconds": None, "error_class": "integrity_restricted", "health": "blocked"},
}


def _stringify(value: Any) -> str:
    return str(value or "").strip()


def _int_value(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except Exception:
        return None


def _message_type(payload: dict[str, Any]) -> str:
    if payload.get("provider_payload"):
        provider_payload = payload.get("provider_payload") or {}
        if provider_payload.get("status") == "read":
            return "mark_as_read"
        return _stringify(provider_payload.get("type") or "text").lower() or "text"
    value = _stringify(payload.get("message_type") or payload.get("type") or ("text" if payload.get("body") else ""))
    aliases = {
        "button": "interactive_button",
        "buttons": "interactive_button",
        "list": "interactive_list",
        "flow": "flow_entrypoint",
        "read": "mark_as_read",
        "mark_read": "mark_as_read",
    }
    return aliases.get(value.lower(), value.lower())


def _throughput_limit(number: dict[str, Any], metadata: dict[str, Any], payload: dict[str, Any]) -> int:
    policy = metadata.get("policy") if isinstance(metadata.get("policy"), dict) else {}
    runtime_policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
    explicit = _int_value(runtime_policy.get("throughput_per_minute") or policy.get("throughput_per_minute") or metadata.get("throughput_per_minute"))
    if explicit:
        return max(1, explicit)
    tier = _stringify(payload.get("throughput_tier") or number.get("throughput_tier") or metadata.get("throughput_tier") or "standard").lower()
    return DEFAULT_THROUGHPUT_BY_TIER.get(tier, DEFAULT_THROUGHPUT_BY_TIER["standard"])


def _template_language(payload: dict[str, Any], metadata: dict[str, Any]) -> str:
    policy = metadata.get("policy") if isinstance(metadata.get("policy"), dict) else {}
    return (
        _stringify(((payload.get("template") or {}).get("language") or {}).get("code"))
        or _stringify(((payload.get("template_fallback") or {}).get("language") or {}).get("code"))
        or _stringify((payload.get("policy") or {}).get("default_template_language"))
        or _stringify(policy.get("default_template_language"))
        or DEFAULT_TEMPLATE_LANGUAGE
    )


def _template_category(payload: dict[str, Any], template: dict[str, Any] | None = None) -> str:
    template = template or {}
    return (
        _stringify(template.get("category"))
        or _stringify(payload.get("message_category"))
        or _stringify((payload.get("policy") or {}).get("message_category"))
        or "utility"
    ).lower()


def _recent_throughput(conn, *, bot_id: str, channel: str = "whatsapp", window_seconds: int = 60) -> int:
    since = add_seconds(utcnow_iso(), -window_seconds)
    row = fetch_one(
        conn,
        """
        SELECT COUNT(*) AS value
        FROM outbox_messages
        WHERE bot_id = ? AND channel = ?
          AND status IN ('running','sent','delivered','read')
          AND COALESCE(sent_at, created_at) >= ?
        """,
        (bot_id, channel, since),
    )
    return int((row or {}).get("value") or 0)


def customer_care_window_state(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str | None,
) -> dict[str, Any]:
    params: list[Any] = [organization_id, bot_id]
    clauses = ["organization_id = ?", "bot_id = ?", "direction = 'inbound'", "source = 'whatsapp'"]
    if conversation_id:
        clauses.append("conversation_id = ?")
        params.append(conversation_id)
    elif contact_id:
        clauses.append("contact_id = ?")
        params.append(contact_id)
    else:
        return {
            "last_inbound_at": None,
            "customer_care_window_closes_at": None,
            "window_hours": CUSTOMER_CARE_WINDOW_HOURS,
            "is_open": False,
            "reason": "missing_conversation_or_contact",
        }

    latest = fetch_one(
        conn,
        f"SELECT created_at, body, external_id FROM messages WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT 1",
        tuple(params),
    )
    last_inbound_at = latest.get("created_at") if latest else None
    closes_at = add_seconds(last_inbound_at, CUSTOMER_CARE_WINDOW_HOURS * 3600) if last_inbound_at else None
    now = utcnow()
    closes_dt = parse_iso(closes_at)
    is_open = bool(closes_dt and closes_dt > now)
    return {
        "last_inbound_at": last_inbound_at,
        "customer_care_window_closes_at": closes_at,
        "window_hours": CUSTOMER_CARE_WINDOW_HOURS,
        "is_open": is_open,
        "reason": "customer_reply_within_window" if is_open else ("window_expired" if last_inbound_at else "no_inbound_customer_message"),
        "last_inbound_preview": (latest or {}).get("body"),
        "last_inbound_message_id": (latest or {}).get("external_id"),
    }


def classify_meta_error_policy(status_code: int | None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    error = payload.get("error") or {}
    code = _int_value(error.get("code"))
    base = META_ERROR_POLICIES.get(code, {})
    retryable = bool(base.get("retryable"))
    retry_after_seconds = base.get("retry_after_seconds")
    error_class = base.get("error_class") or "provider_error"
    health = base.get("health") or ("degraded" if retryable else "at_risk")
    if not base:
        if status_code in {408, 409, 423, 429, 500, 502, 503, 504}:
            retryable = True
            health = "degraded"
            error_class = "http_transient"
            retry_after_seconds = 300 if status_code == 429 else 60
        else:
            retryable = False
            health = "at_risk"
            error_class = "provider_error"
            retry_after_seconds = None
    return {
        "provider_code": code,
        "retryable": retryable,
        "retry_after_seconds": retry_after_seconds,
        "error_class": error_class,
        "health": health,
        "status_code": status_code,
        "message": _stringify(error.get("message") or payload.get("message") or "whatsapp_provider_error"),
    }


def update_whatsapp_number_health(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    status_code: int | None = None,
    payload: dict[str, Any] | None = None,
    success: bool = False,
    event_type: str = "provider_api",
) -> dict[str, Any]:
    if not bot_id:
        return {}
    number = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,))
    if not number:
        return {}
    metadata = from_json(number.get("metadata_json"), {})
    channel_health = metadata.setdefault("channel_health", {})
    provider_errors = metadata.setdefault("provider_errors", [])
    now = utcnow_iso()
    if success:
        channel_health.update(
            {
                "status": "healthy",
                "last_success_at": now,
                "provider_degraded_until": None,
                "consecutive_provider_errors": 0,
                "last_event_type": event_type,
            }
        )
        if not _stringify(number.get("quality_status")) or number.get("quality_status") in {"unknown", "degraded"}:
            execute(
                conn,
                "UPDATE whatsapp_numbers SET quality_status = ?, provider_degraded_until = NULL, last_health_check_at = ?, updated_at = ?, metadata_json = ? WHERE id = ?",
                ("healthy", now, now, to_json(metadata), number["id"]),
            )
        else:
            execute(
                conn,
                "UPDATE whatsapp_numbers SET provider_degraded_until = NULL, last_health_check_at = ?, updated_at = ?, metadata_json = ? WHERE id = ?",
                (now, now, to_json(metadata), number["id"]),
            )
        return {"status": "healthy", "number_id": number["id"], "metadata": metadata}

    decision = classify_meta_error_policy(status_code, payload)
    retry_after_seconds = _int_value(decision.get("retry_after_seconds")) or 0
    degraded_until = add_seconds(now, retry_after_seconds) if retry_after_seconds else None
    provider_errors.append(
        {
            "at": now,
            "event_type": event_type,
            "provider_code": decision.get("provider_code"),
            "status_code": status_code,
            "error_class": decision.get("error_class"),
            "message": decision.get("message"),
        }
    )
    provider_errors[:] = provider_errors[-25:]
    channel_health.update(
        {
            "status": decision.get("health"),
            "last_provider_error_at": now,
            "last_provider_error": decision,
            "provider_degraded_until": degraded_until,
            "consecutive_provider_errors": int(channel_health.get("consecutive_provider_errors") or 0) + 1,
            "last_event_type": event_type,
        }
    )
    quality_status = "healthy"
    if decision.get("health") == "blocked":
        quality_status = "blocked"
    elif decision.get("health") == "degraded":
        quality_status = "degraded"
    elif decision.get("health") == "at_risk":
        quality_status = "at_risk"
    execute(
        conn,
        """
        UPDATE whatsapp_numbers
        SET quality_status = ?,
            provider_degraded_until = ?,
            last_health_check_at = ?,
            last_provider_error_code = ?,
            last_provider_error_at = ?,
            updated_at = ?,
            metadata_json = ?
        WHERE id = ?
        """,
        (
            quality_status,
            degraded_until,
            now,
            str(decision.get("provider_code")) if decision.get("provider_code") is not None else None,
            now,
            now,
            to_json(metadata),
            number["id"],
        ),
    )
    return {"status": quality_status, "number_id": number["id"], "metadata": metadata, "decision": decision}


def evaluate_whatsapp_outbound_policy(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str | None,
    outbox_id: str | None,
    message_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    number = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,))
    if not number:
        return {
            "status": "dead_letter",
            "reason_code": "whatsapp_number_not_configured",
            "decision": "deny",
            "retryable": False,
            "payload": deepcopy(payload),
            "message_type": _message_type(payload),
            "care_window": customer_care_window_state(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, contact_id=contact_id),
            "channel_health": {"status": "blocked", "reason": "number_missing"},
            "retry_after_seconds": None,
            "message_category": None,
            "selected_template": None,
            "throughput": {"limit": 0, "current": 0, "remaining": 0, "status": "blocked"},
        }
    metadata = from_json(number.get("metadata_json"), {})
    channel_health = deepcopy(metadata.get("channel_health") or {})
    degraded_until = parse_iso(_stringify(number.get("provider_degraded_until") or channel_health.get("provider_degraded_until")) or None)
    now = utcnow()
    throughput_limit = _throughput_limit(number, metadata, payload)
    throughput_current = _recent_throughput(conn, bot_id=bot_id)
    throughput_status = "ok"
    retry_after_seconds: int | None = None
    business_profile = whatsapp_business_profile(number)
    rate_limit_state = evaluate_outbound_rate_limit(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_id=contact_id,
        number=number,
        outbox_id=outbox_id,
    )
    suppression_state = is_contact_suppressed(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id)
    organization = fetch_one(conn, "SELECT vertical FROM organizations WHERE id = ?", (organization_id,)) or {}
    content_guard = validate_message_content(text=_stringify(payload.get("body") or payload.get("summary") or ((payload.get("text") or {}).get("body"))), vertical=organization.get("vertical"))
    if throughput_current >= throughput_limit:
        throughput_status = "limited"
        retry_after_seconds = 60
    health_status = _stringify(channel_health.get("status") or number.get("quality_status") or "healthy").lower() or "healthy"
    if degraded_until and degraded_until > now and health_status in {"degraded", "blocked"}:
        retry_after_seconds = max(retry_after_seconds or 0, max(15, int(math.ceil((degraded_until - now).total_seconds()))))
    care_window = customer_care_window_state(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, contact_id=contact_id)
    message_type = _message_type(payload)
    template_payload = deepcopy(payload.get("template") or {}) if isinstance(payload.get("template"), dict) else None
    template_fallback = deepcopy(payload.get("template_fallback") or payload.get("template_candidate") or {}) if isinstance(payload.get("template_fallback") or payload.get("template_candidate") or {}, dict) else None

    decision_status = "allow"
    decision = "allow"
    reason_code = "care_window_open"
    chosen_payload = deepcopy(payload)
    selected_template = None
    message_category = _template_category(payload, template_payload)

    template_lifecycle: dict[str, Any] | None = None
    template_validation: dict[str, Any] | None = None
    selected_template_version_id: str | None = None
    selected_template_language: str | None = None
    used_template_fallback = False

    if _stringify(number.get("connection_status")).lower() not in {"connected", "healthy", "active"}:
        decision_status = "dead_letter"
        decision = "deny"
        reason_code = "channel_not_connected"
    elif health_status == "blocked":
        decision_status = "dead_letter"
        decision = "deny"
        reason_code = "channel_health_blocked"
    elif _stringify(number.get("quality_rating")).upper() == "RED":
        decision_status = "dead_letter"
        decision = "deny"
        reason_code = "quality_rating_red_pause"
    elif suppression_state.get("suppressed"):
        decision_status = "dead_letter"
        decision = "deny"
        reason_code = "contact_opted_out"
    elif not content_guard.get("ok"):
        decision_status = "dead_letter"
        decision = "deny"
        reason_code = "content_policy_blocked"
    elif content_guard.get("severity") == "review":
        decision_status = "retry"
        decision = "review"
        reason_code = "content_review_required"
        retry_after_seconds = max(retry_after_seconds or 0, 900)
    elif not rate_limit_state.get("allowed"):
        decision_status = "retry"
        decision = "throttle"
        reason_code = rate_limit_state.get("reason_code") or "rate_limit_exceeded"
        retry_after_seconds = max(retry_after_seconds or 0, int(rate_limit_state.get("retry_after_seconds") or 60))
    elif throughput_status == "limited":
        decision_status = "retry"
        decision = "throttle"
        reason_code = "throughput_limit_reached"
    elif degraded_until and degraded_until > now and health_status == "degraded":
        decision_status = "retry"
        decision = "delay"
        reason_code = "provider_degraded"
    elif message_type in NON_TEMPLATE_EXEMPT_TYPES:
        reason_code = "message_type_exempt"
    elif message_type == "template":
        if template_payload and not ((template_payload.get("language") or {}).get("code")):
            template_payload["language"] = {"code": _template_language(payload, metadata)}
        if template_payload:
            template_payload["category"] = _template_category(payload, template_payload)
            chosen_payload["template"] = template_payload
            selected_template = template_payload.get("name")
            message_category = _template_category(payload, template_payload)
        template_lifecycle = resolve_whatsapp_template_for_payload(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            payload=chosen_payload,
            metadata={"default_template_language": _template_language(payload, metadata), "default_template_category": message_category},
            allow_alternative=True,
        )
        template_validation = template_lifecycle.get("coverage") if isinstance(template_lifecycle, dict) else None
        if template_lifecycle.get("ok"):
            chosen_payload = deepcopy(template_lifecycle.get("payload") or chosen_payload)
            selected_template = template_lifecycle.get("selected_template") or selected_template
            selected_template_version_id = template_lifecycle.get("selected_template_version_id")
            selected_template_language = template_lifecycle.get("selected_template_language")
            message_category = template_lifecycle.get("message_category") or message_category
            used_template_fallback = bool(template_lifecycle.get("used_fallback"))
            reason_code = "template_fallback_selected" if used_template_fallback else "template_requested"
            decision = "template_fallback" if used_template_fallback else decision
        else:
            decision_status = "dead_letter"
            decision = "deny"
            reason_code = "template_not_approved_or_invalid"
    elif care_window.get("is_open"):
        reason_code = "care_window_open"
    elif template_fallback:
        template_fallback.setdefault("language", {"code": _template_language(payload, metadata)})
        template_fallback["category"] = _template_category(payload, template_fallback)
        chosen_payload = {k: deepcopy(v) for k, v in payload.items() if k not in {"body", "message_type", "type", "provider_payload"}}
        chosen_payload["message_type"] = "template"
        chosen_payload["template"] = template_fallback
        if payload.get("body") and not chosen_payload.get("summary"):
            chosen_payload["summary"] = _stringify(payload.get("body"))
        template_lifecycle = resolve_whatsapp_template_for_payload(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            payload=chosen_payload,
            metadata={"default_template_language": _template_language(payload, metadata), "default_template_category": _template_category(payload, template_fallback)},
            allow_alternative=True,
            fallback_only=True,
        )
        if template_lifecycle.get("ok"):
            chosen_payload = deepcopy(template_lifecycle.get("payload") or chosen_payload)
            selected_template = template_lifecycle.get("selected_template")
            selected_template_version_id = template_lifecycle.get("selected_template_version_id")
            selected_template_language = template_lifecycle.get("selected_template_language")
            message_category = template_lifecycle.get("message_category") or message_category
            template_validation = template_lifecycle.get("coverage")
            used_template_fallback = bool(template_lifecycle.get("used_fallback") or True)
            decision = "rewrite_to_template"
            reason_code = "outside_customer_care_window_template_required"
        else:
            decision_status = "dead_letter"
            decision = "deny"
            reason_code = "template_fallback_invalid_or_unapproved"
    else:
        decision_status = "dead_letter"
        decision = "deny"
        reason_code = "outside_customer_care_window_template_required"

    return {
        "status": decision_status,
        "decision": decision,
        "reason_code": reason_code,
        "retryable": decision_status == "retry",
        "retry_after_seconds": retry_after_seconds,
        "payload": chosen_payload,
        "message_type": _message_type(chosen_payload),
        "care_window": care_window,
        "channel_health": {
            "status": health_status,
            "connection_status": number.get("connection_status"),
            "quality_status": number.get("quality_status"),
            "quality_rating": number.get("quality_rating"),
            "provider_degraded_until": number.get("provider_degraded_until") or channel_health.get("provider_degraded_until"),
        },
        "throughput": {
            "limit": throughput_limit,
            "current": throughput_current,
            "remaining": max(0, throughput_limit - throughput_current),
            "status": throughput_status,
        },
        "business_profile": business_profile,
        "rate_limit": rate_limit_state,
        "suppression": suppression_state,
        "content_guard": content_guard,
        "message_category": message_category,
        "selected_template": selected_template,
        "selected_template_version_id": selected_template_version_id,
        "selected_template_language": selected_template_language,
        "template_validation": template_validation,
        "template_lifecycle": template_lifecycle,
        "used_template_fallback": used_template_fallback,
        "number_id": number.get("id"),
        "outbox_id": outbox_id,
        "message_id": message_id,
    }


def persist_whatsapp_policy_decision(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str | None,
    outbox_id: str | None,
    message_id: str | None,
    decision: dict[str, Any],
) -> dict[str, Any]:
    now = utcnow_iso()
    row_id = new_id("wapol")
    execute(
        conn,
        """
        INSERT INTO whatsapp_policy_decisions
        (id, organization_id, bot_id, conversation_id, contact_id, outbox_id, message_id, decision_status, delivery_mode, reason_code, policy_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            outbox_id,
            message_id,
            decision.get("status"),
            decision.get("message_type"),
            decision.get("reason_code"),
            to_json(decision),
            now,
        ),
    )
    if outbox_id and table_exists(conn, "outbox_messages"):
        execute(conn, "UPDATE outbox_messages SET governance_json = ? WHERE id = ?", (to_json(decision), outbox_id))
    register_channel_event(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        channel="whatsapp",
        direction="system",
        event_type=f"whatsapp_policy_{decision.get('status')}",
        body=_stringify(decision.get("reason_code") or decision.get("decision") or "whatsapp_policy"),
        metadata=decision,
    )
    return fetch_one(conn, "SELECT * FROM whatsapp_policy_decisions WHERE id = ?", (row_id,)) or {}


def whatsapp_governance_snapshot(conn, *, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = [organization_id]
    clause = "WHERE organization_id = ?"
    if bot_id:
        clause += " AND bot_id = ?"
        params.append(bot_id)
    numbers = fetch_all(conn, f"SELECT * FROM whatsapp_numbers {clause} ORDER BY updated_at DESC", tuple(params))
    decision_params = list(params)
    decisions = fetch_all(
        conn,
        f"SELECT * FROM whatsapp_policy_decisions {clause} ORDER BY created_at DESC LIMIT 100",
        tuple(decision_params),
    ) if table_exists(conn, "whatsapp_policy_decisions") else []
    queue_rows = fetch_all(
        conn,
        "SELECT bot_id, status, COUNT(*) AS value FROM outbox_messages WHERE organization_id = ? AND channel = 'whatsapp' GROUP BY bot_id, status",
        (organization_id,),
    ) if table_exists(conn, "outbox_messages") else []
    queue_by_bot: dict[str, dict[str, int]] = {}
    for row in queue_rows:
        bot_key = _stringify(row.get("bot_id")) or "unknown"
        bucket = queue_by_bot.setdefault(bot_key, {})
        bucket[str(row.get("status") or "unknown")] = int(row.get("value") or 0)

    number_cards: list[dict[str, Any]] = []
    degraded = 0
    blocked = 0
    for row in numbers:
        metadata = from_json(row.get("metadata_json"), {})
        health = metadata.get("channel_health") if isinstance(metadata.get("channel_health"), dict) else {}
        status = _stringify(health.get("status") or row.get("quality_status") or row.get("connection_status") or "unknown").lower() or "unknown"
        if status == "degraded":
            degraded += 1
        if status == "blocked":
            blocked += 1
        throughput_limit = _throughput_limit(row, metadata, {})
        current = _recent_throughput(conn, bot_id=row["bot_id"])
        recent_decisions = [item for item in decisions if item.get("bot_id") == row.get("bot_id")][:20]
        recent_provider_errors = metadata.get("provider_errors") if isinstance(metadata.get("provider_errors"), list) else []
        number_cards.append(
            {
                "bot_id": row.get("bot_id"),
                "phone_number": row.get("phone_number"),
                "phone_number_id": row.get("phone_number_id"),
                "connection_status": row.get("connection_status"),
                "quality_rating": row.get("quality_rating"),
                "quality_status": row.get("quality_status"),
                "throughput_tier": row.get("throughput_tier"),
                "business_profile": whatsapp_business_profile(row),
                "provider_degraded_until": row.get("provider_degraded_until"),
                "last_provider_error_code": row.get("last_provider_error_code"),
                "last_provider_error_at": row.get("last_provider_error_at"),
                "channel_health": {
                    **health,
                    "status": status,
                    "throughput": {
                        "limit_per_minute": throughput_limit,
                        "current_last_minute": current,
                        "remaining": max(0, throughput_limit - current),
                    },
                    "queue": queue_by_bot.get(_stringify(row.get("bot_id")), {}),
                },
                "recent_policy_decisions": {
                    "total": len(recent_decisions),
                    "allowed": sum(1 for item in recent_decisions if item.get("decision_status") == "allow"),
                    "retry": sum(1 for item in recent_decisions if item.get("decision_status") == "retry"),
                    "dead_letter": sum(1 for item in recent_decisions if item.get("decision_status") == "dead_letter"),
                },
                "recent_provider_errors": recent_provider_errors[-5:],
            }
        )

    summary = {
        "numbers": len(number_cards),
        "degraded_numbers": degraded,
        "blocked_numbers": blocked,
        "recent_decisions": len(decisions),
        "decision_breakdown": {
            "allow": sum(1 for item in decisions if item.get("decision_status") == "allow"),
            "retry": sum(1 for item in decisions if item.get("decision_status") == "retry"),
            "dead_letter": sum(1 for item in decisions if item.get("decision_status") == "dead_letter"),
        },
    }
    status = "ok"
    if blocked:
        status = "error"
    elif degraded:
        status = "degraded"
    return {
        "status": status,
        "summary": summary,
        "policy": {
            "customer_care_window_hours": CUSTOMER_CARE_WINDOW_HOURS,
            "throughput_tiers": DEFAULT_THROUGHPUT_BY_TIER,
            "template_required_outside_window": True,
            "non_template_exempt_types": sorted(NON_TEMPLATE_EXEMPT_TYPES),
            "opt_out_keywords": ["stop", "baja", "cancelar", "no más"],
            "content_guard_enabled": True,
            "business_verification_impacts_daily_limit": True,
        },
        "numbers": number_cards,
        "recent_decisions": [
            {
                **row,
                "policy": from_json(row.get("policy_json"), {}),
            }
            for row in decisions[:25]
        ],
    }
