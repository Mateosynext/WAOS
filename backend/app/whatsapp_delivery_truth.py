from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

from .db import execute, fetch_all, fetch_one, table_exists
from .utils import from_json, hash_value, new_id, parse_iso, to_json, utcnow_iso


TRUTH_STATUSES = {"accepted", "sent", "delivered", "read", "failed", "deleted"}
_STATUS_RANK = {"accepted": 0, "sent": 1, "delivered": 2, "read": 3, "failed": 4, "deleted": 5}


def _stringify(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _to_iso_timestamp(value: Any) -> str | None:
    raw = _stringify(value)
    if not raw:
        return None
    if raw.isdigit():
        try:
            return dt.datetime.fromtimestamp(int(raw), tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except Exception:
            return None
    try:
        parsed = parse_iso(raw)
        if parsed is None:
            return None
        return parsed.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def _min_iso(*values: str | None) -> str | None:
    parsed = [parse_iso(item) for item in values if item]
    parsed = [item for item in parsed if item is not None]
    if not parsed:
        return None
    return min(parsed).astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _max_iso(*values: str | None) -> str | None:
    parsed = [parse_iso(item) for item in values if item]
    parsed = [item for item in parsed if item is not None]
    if not parsed:
        return None
    return max(parsed).astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _choose_status(current_status: str | None, current_seen_at: str | None, new_status: str, new_seen_at: str | None) -> str:
    normalized_current = _stringify(current_status).lower() or "accepted"
    current_rank = _STATUS_RANK.get(normalized_current, 0)
    new_rank = _STATUS_RANK.get(new_status, 0)
    if new_rank > current_rank and normalized_current in {"accepted", "sent"}:
        return new_status
    current_dt = parse_iso(current_seen_at) if current_seen_at else None
    new_dt = parse_iso(new_seen_at) if new_seen_at else None
    if current_dt and new_dt:
        if new_dt > current_dt:
            return new_status
        if new_dt < current_dt and new_rank <= current_rank:
            return normalized_current
    if new_rank >= current_rank:
        return new_status
    return normalized_current


def _template_name_from_payload(payload: dict[str, Any], governance: dict[str, Any], message_metadata: dict[str, Any]) -> str | None:
    candidates = [
        ((payload.get("template") or {}).get("name")),
        (((governance.get("payload") or {}).get("template") or {}).get("name")),
        governance.get("selected_template"),
        ((((message_metadata.get("whatsapp") or {}).get("template") or {}).get("name"))),
    ]
    for item in candidates:
        value = _stringify(item)
        if value:
            return value
    return None


def _message_kind_from_payload(payload: dict[str, Any], message: dict[str, Any] | None) -> str:
    return _stringify(payload.get("message_type") or payload.get("type") or (message or {}).get("kind") or "text").lower() or "text"


def _vertical_for_projection(conn, *, bot_id: str | None, organization_id: str) -> str:
    if bot_id:
        bot = fetch_one(conn, "SELECT vertical FROM bots WHERE id = ?", (bot_id,))
        value = _stringify((bot or {}).get("vertical"))
        if value:
            return value
    org = fetch_one(conn, "SELECT vertical FROM organizations WHERE id = ?", (organization_id,))
    return _stringify((org or {}).get("vertical")) or "unknown"


def _projection_from_outbox_and_message(conn, *, outbox: dict[str, Any], message: dict[str, Any] | None) -> dict[str, Any]:
    payload = from_json(outbox.get("payload_json"), {})
    governance = from_json(outbox.get("governance_json"), {})
    message_metadata = from_json((message or {}).get("metadata_json"), {})
    provider_message_id = _stringify(outbox.get("provider_message_id") or (message or {}).get("external_id"))
    if not provider_message_id:
        return {}

    existing = fetch_one(conn, "SELECT * FROM whatsapp_delivery_projection WHERE provider_message_id = ?", (provider_message_id,)) if table_exists(conn, "whatsapp_delivery_projection") else None
    accepted_at = outbox.get("sent_at") or outbox.get("created_at") or utcnow_iso()
    current_status = _stringify((existing or {}).get("current_status") or "accepted").lower() or "accepted"
    if not existing:
        inferred = _stringify(outbox.get("status")).lower()
        if inferred in {"delivered", "read", "failed"}:
            current_status = inferred
        current_status = current_status if current_status in TRUTH_STATUSES else "accepted"
        projection_id = new_id("wdp")
        execute(
            conn,
            """
            INSERT INTO whatsapp_delivery_projection
            (id, organization_id, bot_id, conversation_id, contact_id, outbox_id, message_id, provider_message_id, phone_number_id, recipient_id, template_name, message_kind, vertical, accepted_at, current_status, first_event_at, last_event_at, pricing_json, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?, ?)
            """,
            (
                projection_id,
                outbox["organization_id"],
                outbox.get("bot_id"),
                outbox.get("conversation_id") or (message or {}).get("conversation_id"),
                payload.get("contact_id") or (message or {}).get("contact_id"),
                outbox.get("id"),
                payload.get("message_id") or (message or {}).get("id"),
                provider_message_id,
                _stringify((from_json(outbox.get("provider_response_json"), {}).get("phone_number_id"))) or None,
                None,
                _template_name_from_payload(payload, governance, message_metadata),
                _message_kind_from_payload(payload, message),
                _vertical_for_projection(conn, bot_id=outbox.get("bot_id"), organization_id=outbox["organization_id"]),
                accepted_at,
                current_status,
                accepted_at,
                accepted_at,
                to_json({
                    "delivery_attempt_id": payload.get("delivery_attempt_id"),
                    "governance": governance,
                    "source": payload.get("source"),
                    "outbox_status": outbox.get("status"),
                }),
                accepted_at,
                utcnow_iso(),
            ),
        )
        existing = fetch_one(conn, "SELECT * FROM whatsapp_delivery_projection WHERE id = ?", (projection_id,))
    else:
        metadata = from_json(existing.get("metadata_json"), {})
        if payload.get("delivery_attempt_id") and not metadata.get("delivery_attempt_id"):
            metadata["delivery_attempt_id"] = payload.get("delivery_attempt_id")
        if outbox.get("id") and not existing.get("outbox_id"):
            execute(conn, "UPDATE whatsapp_delivery_projection SET outbox_id = ?, message_id = COALESCE(message_id, ?), conversation_id = COALESCE(conversation_id, ?), contact_id = COALESCE(contact_id, ?), accepted_at = COALESCE(accepted_at, ?), metadata_json = ?, updated_at = ? WHERE id = ?", (outbox.get("id"), payload.get("message_id") or (message or {}).get("id"), outbox.get("conversation_id") or (message or {}).get("conversation_id"), payload.get("contact_id") or (message or {}).get("contact_id"), accepted_at, to_json(metadata), utcnow_iso(), existing["id"]))
            existing = fetch_one(conn, "SELECT * FROM whatsapp_delivery_projection WHERE id = ?", (existing["id"],))
    return existing or {}


def _fact_fingerprint(provider_message_id: str, status: str, observed_at: str | None, source: str, payload: dict[str, Any], error_code: int | None, error_message: str | None) -> str:
    base = to_json({
        "provider_message_id": provider_message_id,
        "status": status,
        "observed_at": observed_at,
        "source": source,
        "error_code": error_code,
        "error_message": error_message,
        "payload": payload,
    })
    return hash_value(base)


def _update_projection_with_fact(conn, projection: dict[str, Any], *, status: str, observed_at: str | None, pricing: dict[str, Any] | None, recipient_id: str | None, phone_number_id: str | None, error_code: int | None, error_message: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    metadata = from_json(projection.get("metadata_json"), {})
    sent_at = projection.get("sent_at")
    delivered_at = projection.get("delivered_at")
    read_at = projection.get("read_at")
    failed_at = projection.get("failed_at")
    if status == "sent":
        sent_at = _min_iso(sent_at, observed_at)
    elif status == "delivered":
        sent_at = _min_iso(sent_at, observed_at) if not sent_at else sent_at
        delivered_at = _min_iso(delivered_at, observed_at)
    elif status == "read":
        sent_at = _min_iso(sent_at, observed_at) if not sent_at else sent_at
        if not delivered_at:
            metadata["delivered_inferred_from_read"] = True
            delivered_at = observed_at
        read_at = _min_iso(read_at, observed_at)
    elif status == "failed":
        failed_at = _min_iso(failed_at, observed_at)
        if error_code is not None:
            metadata["last_error_code"] = error_code
        if error_message:
            metadata["last_error_message"] = error_message
    elif status == "deleted":
        metadata["deleted_at"] = observed_at

    last_event_at = _max_iso(projection.get("last_event_at"), observed_at, projection.get("accepted_at"))
    first_event_at = _min_iso(projection.get("first_event_at"), observed_at, projection.get("accepted_at"))
    current_status = _choose_status(projection.get("current_status"), projection.get("last_event_at"), status, observed_at)
    if status in {"delivered", "read"} and current_status == "failed":
        current_status = status
    pricing_payload = pricing or from_json(projection.get("pricing_json"), {})
    metadata["last_payload"] = payload
    execute(
        conn,
        """
        UPDATE whatsapp_delivery_projection
        SET phone_number_id = COALESCE(?, phone_number_id),
            recipient_id = COALESCE(?, recipient_id),
            current_status = ?,
            sent_at = ?,
            delivered_at = ?,
            read_at = ?,
            failed_at = ?,
            first_event_at = ?,
            last_event_at = ?,
            last_error_code = ?,
            last_error_message = ?,
            pricing_json = ?,
            metadata_json = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            phone_number_id,
            recipient_id,
            current_status,
            sent_at,
            delivered_at,
            read_at,
            failed_at,
            first_event_at,
            last_event_at,
            error_code,
            error_message,
            to_json(pricing_payload),
            to_json(metadata),
            utcnow_iso(),
            projection["id"],
        ),
    )
    return fetch_one(conn, "SELECT * FROM whatsapp_delivery_projection WHERE id = ?", (projection["id"],)) or projection


def seed_whatsapp_delivery_projection(conn, *, outbox: dict[str, Any], message: dict[str, Any] | None = None) -> dict[str, Any]:
    if not table_exists(conn, "whatsapp_delivery_projection"):
        return {}
    return _projection_from_outbox_and_message(conn, outbox=outbox, message=message)


def record_whatsapp_delivery_status(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    event: dict[str, Any],
    outbox: dict[str, Any] | None = None,
    message: dict[str, Any] | None = None,
    source: str = "webhook",
) -> dict[str, Any]:
    if not table_exists(conn, "whatsapp_delivery_status_facts") or not table_exists(conn, "whatsapp_delivery_projection"):
        return {}
    provider_message_id = _stringify(event.get("message_id") or event.get("provider_message_id"))
    if not provider_message_id:
        return {}
    normalized_status = _stringify(event.get("status") or "sent").lower() or "sent"
    if normalized_status not in TRUTH_STATUSES:
        normalized_status = "sent"
    observed_at = _to_iso_timestamp(event.get("timestamp") or event.get("observed_at") or event.get("occurred_at")) or utcnow_iso()
    pricing = event.get("pricing") or {}
    errors = event.get("errors") or []
    error = errors[0] if isinstance(errors, list) and errors else (event.get("error") or {})
    error_code = _safe_int(error.get("code"))
    error_message = _stringify(error.get("message") or error.get("title")) or None
    phone_number_id = _stringify(((event.get("metadata") or {}).get("phone_number_id")) or event.get("phone_number_id")) or None
    recipient_id = _stringify(event.get("recipient_id")) or None

    if outbox is None and provider_message_id:
        outbox = fetch_one(conn, "SELECT * FROM outbox_messages WHERE provider_message_id = ? ORDER BY created_at DESC LIMIT 1", (provider_message_id,))
    if message is None and provider_message_id:
        message = fetch_one(conn, "SELECT * FROM messages WHERE external_id = ? ORDER BY created_at DESC LIMIT 1", (provider_message_id,))
    if outbox is None:
        outbox = {
            "id": None,
            "organization_id": organization_id,
            "bot_id": bot_id,
            "conversation_id": (message or {}).get("conversation_id"),
            "payload_json": to_json({"message_id": (message or {}).get("id"), "contact_id": (message or {}).get("contact_id")}),
            "governance_json": "{}",
            "provider_message_id": provider_message_id,
            "sent_at": observed_at,
            "created_at": observed_at,
            "status": "sent",
        }
    projection = _projection_from_outbox_and_message(conn, outbox=outbox, message=message)
    if not projection:
        return {}
    payload = {
        "conversation": event.get("conversation") or {},
        "pricing": pricing,
        "errors": errors,
        "recipient_id": recipient_id,
        "metadata": event.get("metadata") or {},
        "source": source,
    }
    fingerprint = _fact_fingerprint(provider_message_id, normalized_status, observed_at, source, payload, error_code, error_message)
    existing_fact = fetch_one(conn, "SELECT * FROM whatsapp_delivery_status_facts WHERE event_fingerprint = ?", (fingerprint,))
    if existing_fact:
        return projection
    execute(
        conn,
        """
        INSERT INTO whatsapp_delivery_status_facts
        (id, organization_id, bot_id, conversation_id, outbox_id, message_id, provider_message_id, phone_number_id, recipient_id, status, observed_at, source, pricing_json, error_code, error_message, payload_json, event_fingerprint, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("wfact"),
            organization_id,
            bot_id,
            projection.get("conversation_id"),
            projection.get("outbox_id"),
            projection.get("message_id"),
            provider_message_id,
            phone_number_id,
            recipient_id,
            normalized_status,
            observed_at,
            source,
            to_json(pricing),
            error_code,
            error_message,
            to_json(payload),
            fingerprint,
            utcnow_iso(),
        ),
    )
    return _update_projection_with_fact(
        conn,
        projection,
        status=normalized_status,
        observed_at=observed_at,
        pricing=pricing,
        recipient_id=recipient_id,
        phone_number_id=phone_number_id,
        error_code=error_code,
        error_message=error_message,
        payload=payload,
    )


def reconcile_whatsapp_delivery_truth(conn, *, organization_id: str, bot_id: str | None = None, lookback_hours: int = 168) -> dict[str, Any]:
    if not table_exists(conn, "outbox_messages") or not table_exists(conn, "whatsapp_delivery_projection"):
        return {"performed": False, "reason": "schema_missing"}
    now = parse_iso(utcnow_iso()) or dt.datetime.now(dt.timezone.utc)
    since = (now - dt.timedelta(hours=max(1, int(lookback_hours or 168)))).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    params: list[Any] = [organization_id, since]
    bot_clause = ""
    if bot_id:
        bot_clause = " AND o.bot_id = ? "
        params.append(bot_id)
    rows = fetch_all(
        conn,
        f"""
        SELECT o.*, m.id AS linked_message_id, m.metadata_json AS linked_message_metadata_json, m.status AS linked_message_status, m.external_id AS linked_message_external_id,
               m.contact_id AS linked_message_contact_id, m.conversation_id AS linked_message_conversation_id, m.kind AS linked_message_kind, m.body AS linked_message_body
        FROM outbox_messages o
        LEFT JOIN messages m ON m.id = json_extract(o.payload_json, '$.message_id')
        WHERE o.organization_id = ? AND o.channel = 'whatsapp' AND o.provider_message_id IS NOT NULL AND COALESCE(o.sent_at, o.created_at) >= ? {bot_clause}
        ORDER BY COALESCE(o.sent_at, o.created_at) DESC
        """,
        params,
    )
    touched = 0
    facts = 0
    for row in rows:
        message = None
        if row.get("linked_message_id"):
            message = {
                "id": row.get("linked_message_id"),
                "metadata_json": row.get("linked_message_metadata_json"),
                "status": row.get("linked_message_status"),
                "external_id": row.get("linked_message_external_id"),
                "contact_id": row.get("linked_message_contact_id"),
                "conversation_id": row.get("linked_message_conversation_id"),
                "kind": row.get("linked_message_kind"),
                "body": row.get("linked_message_body"),
            }
        projection = seed_whatsapp_delivery_projection(conn, outbox=row, message=message)
        if projection:
            touched += 1
        response = from_json(row.get("provider_response_json"), {})
        message_metadata = from_json((message or {}).get("metadata_json"), {})
        synthetic_events: list[dict[str, Any]] = []
        for event in response.get("status_events", []) or []:
            if isinstance(event, dict):
                synthetic_events.append({**event, "metadata": {"phone_number_id": projection.get("phone_number_id")}})
        for event in ((((message_metadata.get("whatsapp") or {}).get("status_events")) or [])):
            if isinstance(event, dict):
                synthetic_events.append({**event, "metadata": {"phone_number_id": projection.get("phone_number_id")}})
        if not synthetic_events:
            status = _stringify(row.get("status")).lower()
            if status in {"delivered", "read", "failed"}:
                synthetic_events.append({
                    "message_id": row.get("provider_message_id"),
                    "status": status,
                    "observed_at": row.get("sent_at") or row.get("created_at"),
                    "errors": response.get("errors") or [],
                    "metadata": {"phone_number_id": projection.get("phone_number_id")},
                })
        for event in synthetic_events:
            before = fetch_one(conn, "SELECT COUNT(*) AS value FROM whatsapp_delivery_status_facts", ()) if table_exists(conn, "whatsapp_delivery_status_facts") else {"value": 0}
            record_whatsapp_delivery_status(conn, organization_id=organization_id, bot_id=row.get("bot_id"), event=event, outbox=row, message=message, source="reconcile")
            after = fetch_one(conn, "SELECT COUNT(*) AS value FROM whatsapp_delivery_status_facts", ()) if table_exists(conn, "whatsapp_delivery_status_facts") else {"value": 0}
            facts += max(0, int((after or {}).get("value") or 0) - int((before or {}).get("value") or 0))
    return {"performed": True, "lookback_hours": lookback_hours, "scanned_outbox": len(rows), "projection_touched": touched, "facts_inserted": facts}


def _seconds_between(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    first = parse_iso(start)
    second = parse_iso(end)
    if not first or not second:
        return None
    delta = (second - first).total_seconds()
    return round(delta, 2) if delta >= 0 else None


def _empty_metric_bucket(label: str) -> dict[str, Any]:
    return {
        "label": label,
        "accepted_count": 0,
        "sent_count": 0,
        "delivered_count": 0,
        "read_count": 0,
        "failed_count": 0,
        "pending_truth_count": 0,
        "delivery_rate": 0.0,
        "read_rate": 0.0,
        "read_rate_over_accepted": 0.0,
        "fail_rate": 0.0,
        "avg_time_to_delivered_seconds": None,
        "avg_time_to_read_seconds": None,
        "_delivery_times": [],
        "_read_times": [],
    }


def _classify_projection(row: dict[str, Any]) -> dict[str, bool]:
    delivered = bool(row.get("delivered_at") or row.get("read_at") or _stringify(row.get("current_status")) in {"delivered", "read"})
    read = bool(row.get("read_at") or _stringify(row.get("current_status")) == "read")
    failed = bool(row.get("failed_at") or _stringify(row.get("current_status")) == "failed")
    sent = bool(row.get("sent_at") or delivered or read or failed or _stringify(row.get("current_status")) in {"sent", "delivered", "read", "failed"})
    pending_truth = not delivered and not read and not failed
    return {"sent": sent, "delivered": delivered, "read": read, "failed": failed, "pending_truth": pending_truth}


def _accumulate_bucket(bucket: dict[str, Any], row: dict[str, Any]) -> None:
    state = _classify_projection(row)
    bucket["accepted_count"] += 1
    bucket["sent_count"] += 1 if state["sent"] else 0
    bucket["delivered_count"] += 1 if state["delivered"] else 0
    bucket["read_count"] += 1 if state["read"] else 0
    bucket["failed_count"] += 1 if state["failed"] else 0
    bucket["pending_truth_count"] += 1 if state["pending_truth"] else 0
    delivery_seconds = _seconds_between(row.get("accepted_at"), row.get("delivered_at"))
    read_seconds = _seconds_between(row.get("accepted_at"), row.get("read_at"))
    if delivery_seconds is not None:
        bucket["_delivery_times"].append(delivery_seconds)
    if read_seconds is not None:
        bucket["_read_times"].append(read_seconds)


def _finalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    accepted = max(int(bucket["accepted_count"] or 0), 1)
    delivered = int(bucket["delivered_count"] or 0)
    bucket["delivery_rate"] = round((delivered / accepted) * 100, 2)
    bucket["read_rate"] = round((int(bucket["read_count"] or 0) / max(delivered, 1)) * 100, 2) if delivered else 0.0
    bucket["read_rate_over_accepted"] = round((int(bucket["read_count"] or 0) / accepted) * 100, 2)
    bucket["fail_rate"] = round((int(bucket["failed_count"] or 0) / accepted) * 100, 2)
    delivery_times = bucket.pop("_delivery_times", [])
    read_times = bucket.pop("_read_times", [])
    bucket["avg_time_to_delivered_seconds"] = round(sum(delivery_times) / len(delivery_times), 2) if delivery_times else None
    bucket["avg_time_to_read_seconds"] = round(sum(read_times) / len(read_times), 2) if read_times else None
    return bucket


def evaluate_whatsapp_delivery_alerts(conn, *, organization_id: str, bot_id: str | None = None, window_hours: int = 24) -> list[dict[str, Any]]:
    if not table_exists(conn, "whatsapp_delivery_projection"):
        return []
    now = parse_iso(utcnow_iso()) or dt.datetime.now(dt.timezone.utc)
    since = (now - dt.timedelta(hours=max(1, int(window_hours or 24)))).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    params: list[Any] = [organization_id, since]
    bot_clause = ""
    if bot_id:
        bot_clause = " AND bot_id = ? "
        params.append(bot_id)
    rows = fetch_all(conn, f"SELECT * FROM whatsapp_delivery_projection WHERE organization_id = ? AND COALESCE(accepted_at, created_at) >= ? {bot_clause}", params)
    by_number: dict[str, dict[str, Any]] = {}
    by_template: dict[str, dict[str, Any]] = {}
    by_vertical: dict[str, dict[str, Any]] = {}
    for row in rows:
        for collection, key in ((by_number, _stringify(row.get("phone_number_id")) or "número desconocido"), (by_template, _stringify(row.get("template_name")) or "sin plantilla"), (by_vertical, _stringify(row.get("vertical")) or "sin vertical")):
            bucket = collection.setdefault(key, _empty_metric_bucket(key))
            _accumulate_bucket(bucket, row)
    alerts: list[dict[str, Any]] = []
    for dimension, collection, rules in (
        ("number", by_number, [{"metric": "fail_rate", "comparator": ">=", "threshold": 20.0, "min_volume": 10, "severity": "warning", "title": "Fail rate alto por número"}, {"metric": "delivery_rate", "comparator": "<", "threshold": 75.0, "min_volume": 10, "severity": "warning", "title": "Delivery rate bajo por número"}]),
        ("template", by_template, [{"metric": "fail_rate", "comparator": ">=", "threshold": 15.0, "min_volume": 5, "severity": "warning", "title": "Plantilla con fail rate alto"}]),
        ("vertical", by_vertical, [{"metric": "fail_rate", "comparator": ">=", "threshold": 12.0, "min_volume": 10, "severity": "warning", "title": "Vertical con degradación de delivery"}]),
    ):
        for key, raw_bucket in collection.items():
            bucket = _finalize_bucket(raw_bucket)
            for rule in rules:
                if int(bucket.get("accepted_count") or 0) < int(rule["min_volume"]):
                    continue
                observed = float(bucket.get(rule["metric"]) or 0)
                triggered = observed >= float(rule["threshold"]) if rule["comparator"] == ">=" else observed < float(rule["threshold"])
                if not triggered:
                    continue
                title = str(rule["title"])
                body = f"{title}: {key} observó {rule['metric']}={observed}% en {int(bucket.get('accepted_count') or 0)} mensajes durante las últimas {window_hours}h."
                existing = fetch_one(conn, "SELECT id FROM operator_notifications WHERE organization_id = ? AND category = 'whatsapp_delivery_truth' AND title = ? AND body = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 1", (organization_id, title, body, since)) if table_exists(conn, "operator_notifications") else None
                payload = {
                    "dimension": dimension,
                    "key": key,
                    "metric": rule["metric"],
                    "observed_value": observed,
                    "threshold": rule["threshold"],
                    "window_hours": window_hours,
                    "accepted_count": int(bucket.get("accepted_count") or 0),
                }
                if not existing and table_exists(conn, "operator_notifications"):
                    execute(
                        conn,
                        "INSERT INTO operator_notifications (id, organization_id, bot_id, user_id, conversation_id, category, channel, title, body, severity, status, metadata_json, created_at) VALUES (?, ?, ?, NULL, NULL, 'whatsapp_delivery_truth', 'in_app', ?, ?, ?, 'unread', ?, ?)",
                        (new_id("notif"), organization_id, bot_id, title, body, rule["severity"], to_json(payload), utcnow_iso()),
                    )
                alerts.append({"title": title, "body": body, "severity": rule["severity"], **payload, "deduplicated": bool(existing)})
    return alerts


def build_whatsapp_delivery_truth_report(
    conn,
    *,
    organization_id: str,
    bot_id: str | None = None,
    window_hours: int = 168,
    reconcile: bool = False,
    reconcile_hours: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    if reconcile:
        reconciliation = reconcile_whatsapp_delivery_truth(conn, organization_id=organization_id, bot_id=bot_id, lookback_hours=reconcile_hours or window_hours)
    else:
        reconciliation = {"performed": False}
    if not table_exists(conn, "whatsapp_delivery_projection"):
        return {
            "organization_id": organization_id,
            "bot_id": bot_id,
            "window_hours": window_hours,
            "generated_at": utcnow_iso(),
            "reconciliation": reconciliation,
            "summary": _finalize_bucket(_empty_metric_bucket("summary")),
            "breakdowns": {"by_template": [], "by_number": [], "by_vertical": []},
            "recent_messages": [],
            "alerts": [],
        }

    now = parse_iso(utcnow_iso()) or dt.datetime.now(dt.timezone.utc)
    since = (now - dt.timedelta(hours=max(1, int(window_hours or 168)))).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    params: list[Any] = [organization_id, since]
    bot_clause = ""
    if bot_id:
        bot_clause = " AND bot_id = ? "
        params.append(bot_id)
    rows = fetch_all(conn, f"SELECT * FROM whatsapp_delivery_projection WHERE organization_id = ? AND COALESCE(accepted_at, created_at) >= ? {bot_clause} ORDER BY COALESCE(last_event_at, accepted_at, created_at) DESC", params)
    summary = _empty_metric_bucket("summary")
    by_template: dict[str, dict[str, Any]] = {}
    by_number: dict[str, dict[str, Any]] = {}
    by_vertical: dict[str, dict[str, Any]] = {}
    recent_messages: list[dict[str, Any]] = []
    for row in rows:
        _accumulate_bucket(summary, row)
        template_key = _stringify(row.get("template_name")) or "sin plantilla"
        number_key = _stringify(row.get("phone_number_id")) or "número desconocido"
        vertical_key = _stringify(row.get("vertical")) or "sin vertical"
        _accumulate_bucket(by_template.setdefault(template_key, _empty_metric_bucket(template_key)), row)
        _accumulate_bucket(by_number.setdefault(number_key, _empty_metric_bucket(number_key)), row)
        _accumulate_bucket(by_vertical.setdefault(vertical_key, _empty_metric_bucket(vertical_key)), row)
        if len(recent_messages) < max(1, int(limit or 25)):
            recent_messages.append({
                "provider_message_id": row.get("provider_message_id"),
                "current_status": row.get("current_status"),
                "template_name": row.get("template_name"),
                "phone_number_id": row.get("phone_number_id"),
                "recipient_id": row.get("recipient_id"),
                "vertical": row.get("vertical"),
                "accepted_at": row.get("accepted_at"),
                "sent_at": row.get("sent_at"),
                "delivered_at": row.get("delivered_at"),
                "read_at": row.get("read_at"),
                "failed_at": row.get("failed_at"),
                "last_error_code": row.get("last_error_code"),
                "last_error_message": row.get("last_error_message"),
                "time_to_delivered_seconds": _seconds_between(row.get("accepted_at"), row.get("delivered_at")),
                "time_to_read_seconds": _seconds_between(row.get("accepted_at"), row.get("read_at")),
            })
    alerts = evaluate_whatsapp_delivery_alerts(conn, organization_id=organization_id, bot_id=bot_id, window_hours=min(window_hours, 24))
    return {
        "organization_id": organization_id,
        "bot_id": bot_id,
        "window_hours": window_hours,
        "generated_at": utcnow_iso(),
        "reconciliation": reconciliation,
        "summary": _finalize_bucket(summary),
        "breakdowns": {
            "by_template": sorted((_finalize_bucket(item) for item in by_template.values()), key=lambda item: (-float(item.get("fail_rate") or 0), -int(item.get("accepted_count") or 0), item.get("label") or ""))[:10],
            "by_number": sorted((_finalize_bucket(item) for item in by_number.values()), key=lambda item: (-float(item.get("fail_rate") or 0), -int(item.get("accepted_count") or 0), item.get("label") or ""))[:10],
            "by_vertical": sorted((_finalize_bucket(item) for item in by_vertical.values()), key=lambda item: (-float(item.get("fail_rate") or 0), -int(item.get("accepted_count") or 0), item.get("label") or ""))[:10],
        },
        "recent_messages": recent_messages,
        "alerts": alerts,
    }
