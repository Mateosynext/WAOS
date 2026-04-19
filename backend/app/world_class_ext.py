from __future__ import annotations

import hashlib
from typing import Any
from urllib import request as urllib_request

from .config import settings
from .apm import default_export_target, resolve_apm_targets
from .utils import from_json, hash_value, new_id, parse_iso, to_json, utcnow_iso
from .world_class import execute, fetch_all, fetch_one, sparse_vector_from_text, table_exists, vector_similarity
from .world_class_plus import append_immutable_audit_event


def _hash_token(value: str) -> str:
    return hash_value(f"public-api:{value}")


def _normalize_channel(channel: str) -> str:
    value = str(channel or "").strip().lower().replace(" ", "_")
    aliases = {
        "instagram": "instagram_dm",
        "ig": "instagram_dm",
        "web": "webchat",
        "widget": "webchat",
        "mail": "email",
        "text": "sms",
    }
    return aliases.get(value, value or "whatsapp")


def _identity_key(identity_type: str, identity_value: str) -> str:
    return hash_value(f"{identity_type.lower()}:{identity_value.strip().lower()}")


def _lookup_contact_id(conn, organization_id: str, identity_type: str, identity_value: str) -> str | None:
    if not table_exists(conn, "contacts"):
        return None
    normalized = identity_value.strip().lower()
    if identity_type == "phone":
        row = fetch_one(
            conn,
            "SELECT id FROM contacts WHERE organization_id = ? AND replace(phone,' ','') = replace(?, ' ', '') ORDER BY updated_at DESC LIMIT 1",
            (organization_id, identity_value),
        )
        return row.get("id") if row else None
    if identity_type == "email":
        row = fetch_one(
            conn,
            "SELECT id FROM contacts WHERE organization_id = ? AND lower(email) = ? ORDER BY updated_at DESC LIMIT 1",
            (organization_id, normalized),
        )
        return row.get("id") if row else None
    return None


def upsert_omnichannel_identity(
    conn,
    *,
    organization_id: str,
    identity_type: str,
    identity_value: str,
    contact_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    confidence: float = 1.0,
) -> dict[str, Any]:
    identity_type = str(identity_type or "unknown").strip().lower()
    identity_value = str(identity_value or "").strip()
    if not identity_value:
        return {}
    resolved_contact = contact_id or _lookup_contact_id(conn, organization_id, identity_type, identity_value)
    key = _identity_key(identity_type, identity_value)
    now = utcnow_iso()
    existing = fetch_one(
        conn,
        "SELECT * FROM omnichannel_identities WHERE organization_id = ? AND identity_key = ?",
        (organization_id, key),
    )
    if existing:
        execute(
            conn,
            "UPDATE omnichannel_identities SET contact_id = COALESCE(?, contact_id), confidence = ?, metadata_json = ?, updated_at = ? WHERE id = ?",
            (resolved_contact, float(confidence), to_json(metadata or {}), now, existing["id"]),
        )
        return fetch_one(conn, "SELECT * FROM omnichannel_identities WHERE id = ?", (existing["id"],)) or {}
    row_id = new_id("omniid")
    execute(
        conn,
        "INSERT INTO omnichannel_identities (id, organization_id, contact_id, identity_key, identity_type, identity_value, confidence, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, resolved_contact, key, identity_type, identity_value, float(confidence), to_json(metadata or {}), now, now),
    )
    return fetch_one(conn, "SELECT * FROM omnichannel_identities WHERE id = ?", (row_id,)) or {}


def register_channel_event(
    conn,
    *,
    organization_id: str,
    channel: str,
    direction: str,
    event_type: str,
    body: str | None = None,
    contact_id: str | None = None,
    bot_id: str | None = None,
    conversation_id: str | None = None,
    external_thread_id: str | None = None,
    external_user_id: str | None = None,
    identities: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not table_exists(conn, "channel_events"):
        return {}
    resolved_contact = contact_id
    normalized_identities: list[dict[str, Any]] = []
    for item in identities or []:
        id_type = str(item.get("type") or item.get("identity_type") or "").strip().lower()
        id_value = str(item.get("value") or item.get("identity_value") or "").strip()
        if not id_type or not id_value:
            continue
        identity_row = upsert_omnichannel_identity(
            conn,
            organization_id=organization_id,
            identity_type=id_type,
            identity_value=id_value,
            contact_id=resolved_contact,
            metadata={"channel": channel, **(item.get("metadata") or {})},
            confidence=float(item.get("confidence") or 1.0),
        )
        normalized_identities.append(identity_row)
        resolved_contact = resolved_contact or identity_row.get("contact_id")
    now = utcnow_iso()
    row_id = new_id("chev")
    payload = dict(metadata or {})
    if normalized_identities:
        payload["identities"] = [{k: v for k, v in row.items() if k != "metadata_json"} for row in normalized_identities]
    execute(
        conn,
        "INSERT INTO channel_events (id, organization_id, bot_id, conversation_id, contact_id, channel, external_thread_id, external_user_id, direction, event_type, body, status, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, bot_id, conversation_id, resolved_contact, _normalize_channel(channel), external_thread_id, external_user_id, direction, event_type, body, "received", to_json(payload), now, now),
    )
    return fetch_one(conn, "SELECT * FROM channel_events WHERE id = ?", (row_id,)) or {}


def omnichannel_world_class_overview(conn, *, organization_id: str, bot_id: str | None = None, limit: int = 20) -> dict[str, Any]:
    if not table_exists(conn, "channel_events"):
        return {
            "summary": {
                "channels": [],
                "active_threads": 0,
                "cross_channel_contacts": 0,
                "known_identities": 0,
                "recommended_channels": ["whatsapp", "instagram_dm", "webchat"],
            },
            "threads": [],
        }
    params: list[Any] = [organization_id]
    bot_clause = ""
    if bot_id:
        bot_clause = " AND ce.bot_id = ?"
        params.append(bot_id)
    rows = fetch_all(
        conn,
        f"""
        SELECT ce.*, ct.name AS contact_name, ct.phone AS contact_phone, ct.email AS contact_email
        FROM channel_events ce
        LEFT JOIN contacts ct ON ct.id = ce.contact_id
        WHERE ce.organization_id = ?{bot_clause}
        ORDER BY ce.updated_at DESC
        LIMIT ?
        """,
        (*params, limit),
    )
    channels: dict[str, int] = {}
    contact_channels: dict[str, set[str]] = {}
    for row in rows:
        channel = str(row.get("channel") or "unknown")
        channels[channel] = channels.get(channel, 0) + 1
        if row.get("contact_id"):
            contact_channels.setdefault(str(row["contact_id"]), set()).add(channel)
    identities = fetch_all(conn, "SELECT * FROM omnichannel_identities WHERE organization_id = ? ORDER BY updated_at DESC LIMIT 500", (organization_id,)) if table_exists(conn, "omnichannel_identities") else []
    return {
        "summary": {
            "channels": [{"channel": key, "total": value} for key, value in sorted(channels.items(), key=lambda item: (-item[1], item[0]))],
            "active_threads": len(rows),
            "cross_channel_contacts": sum(1 for values in contact_channels.values() if len(values) > 1),
            "known_identities": len(identities),
            "recommended_channels": ["whatsapp", "instagram_dm", "telegram", "webchat", "email"],
        },
        "threads": [
            {
                **row,
                "channel": _normalize_channel(str(row.get("channel") or "")),
                "contact_name": row.get("contact_name") or row.get("external_user_id") or "Unknown",
                "status": row.get("status") or "received",
                "summary": str(row.get("body") or "")[:180],
                "metadata": from_json(row.get("metadata_json"), {}),
            }
            for row in rows
        ],
    }


def create_shadow_run(
    conn,
    *,
    organization_id: str,
    experiment_key: str,
    production_output: Any,
    candidate_output: Any,
    bot_id: str | None = None,
    conversation_id: str | None = None,
    verdict: str | None = None,
) -> dict[str, Any]:
    prod_text = production_output if isinstance(production_output, str) else to_json(production_output)
    cand_text = candidate_output if isinstance(candidate_output, str) else to_json(candidate_output)
    similarity = round(vector_similarity(sparse_vector_from_text(prod_text), sparse_vector_from_text(cand_text)), 4)
    diff: dict[str, Any] = {
        "similarity": similarity,
        "production_chars": len(prod_text),
        "candidate_chars": len(cand_text),
        "changed": prod_text != cand_text,
    }
    if isinstance(production_output, dict) and isinstance(candidate_output, dict):
        diff["changed_keys"] = sorted({key for key in set(production_output) | set(candidate_output) if production_output.get(key) != candidate_output.get(key)})
    final_verdict = verdict or ("pass" if similarity >= 0.92 else "review")
    row_id = new_id("shadow")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO shadow_runs (id, organization_id, bot_id, conversation_id, experiment_key, production_output_json, candidate_output_json, diff_json, verdict, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, bot_id, conversation_id, experiment_key, to_json(production_output), to_json(candidate_output), to_json(diff), final_verdict, now),
    )
    row = fetch_one(conn, "SELECT * FROM shadow_runs WHERE id = ?", (row_id,)) or {}
    append_immutable_audit_event(conn, organization_id=organization_id, event_type="quality.shadow_run_recorded", entity_type="shadow_run", entity_id=row_id, payload={"experiment_key": experiment_key, "verdict": final_verdict, "bot_id": bot_id})
    return row


def shadow_overview(conn, *, organization_id: str, experiment_key: str | None = None, limit: int = 50) -> dict[str, Any]:
    if not table_exists(conn, "shadow_runs"):
        return {"totals": {"runs": 0, "pass_rate": 0.0}, "recent": []}
    if experiment_key:
        rows = fetch_all(conn, "SELECT * FROM shadow_runs WHERE organization_id = ? AND experiment_key = ? ORDER BY created_at DESC LIMIT ?", (organization_id, experiment_key, limit))
    else:
        rows = fetch_all(conn, "SELECT * FROM shadow_runs WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, limit))
    passed = sum(1 for row in rows if row.get("verdict") == "pass")
    return {
        "totals": {
            "runs": len(rows),
            "pass_rate": round((passed / len(rows)) if rows else 0.0, 4),
        },
        "recent": [{**row, "diff": from_json(row.get("diff_json"), {})} for row in rows],
    }


def upsert_prompt_artifact(
    conn,
    *,
    organization_id: str,
    artifact_type: str,
    artifact_key: str,
    body: str,
    bot_id: str | None = None,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
    status: str = "active",
) -> dict[str, Any]:
    now = utcnow_iso()
    existing = fetch_one(
        conn,
        "SELECT * FROM prompt_artifacts WHERE organization_id = ? AND artifact_type = ? AND artifact_key = ?",
        (organization_id, artifact_type, artifact_key),
    )
    if existing:
        execute(
            conn,
            "UPDATE prompt_artifacts SET bot_id = COALESCE(?, bot_id), title = ?, body = ?, metadata_json = ?, status = ?, updated_at = ? WHERE id = ?",
            (bot_id, title, body, to_json(metadata or {}), status, now, existing["id"]),
        )
        return fetch_one(conn, "SELECT * FROM prompt_artifacts WHERE id = ?", (existing["id"],)) or {}
    row_id = new_id("prmpt")
    execute(
        conn,
        "INSERT INTO prompt_artifacts (id, organization_id, bot_id, artifact_type, artifact_key, title, body, metadata_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, bot_id, artifact_type, artifact_key, title, body, to_json(metadata or {}), status, now, now),
    )
    row = fetch_one(conn, "SELECT * FROM prompt_artifacts WHERE id = ?", (row_id,)) or {}
    append_immutable_audit_event(conn, organization_id=organization_id, event_type="quality.prompt_artifact_upserted", entity_type="prompt_artifact", entity_id=row.get("id"), payload={"artifact_type": artifact_type, "artifact_key": artifact_key, "bot_id": bot_id, "status": status})
    return row


def prompt_analytics_overview(conn, *, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    artifacts = fetch_all(conn, "SELECT * FROM prompt_artifacts WHERE organization_id = ? ORDER BY updated_at DESC LIMIT 200", (organization_id,)) if table_exists(conn, "prompt_artifacts") else []
    usage_rows = fetch_all(conn, "SELECT * FROM ai_usage_events WHERE organization_id = ? ORDER BY created_at DESC LIMIT 500", (organization_id,)) if table_exists(conn, "ai_usage_events") else []
    by_model: dict[str, dict[str, Any]] = {}
    by_intent: dict[str, int] = {}
    for row in usage_rows:
        model = str(row.get("model") or "unknown")
        bucket = by_model.setdefault(model, {"events": 0, "estimated_cost": 0.0, "tokens": 0})
        bucket["events"] += 1
        bucket["estimated_cost"] = round(bucket["estimated_cost"] + float(row.get("estimated_cost") or 0), 6)
        bucket["tokens"] += int(row.get("total_tokens") or 0)
        metadata = from_json(row.get("metadata_json"), {})
        intent = str(metadata.get("intent") or "unknown")
        by_intent[intent] = by_intent.get(intent, 0) + 1
    artifact_rows = [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in artifacts[:50] if (not bot_id or row.get("bot_id") == bot_id or row.get("bot_id") is None)]
    return {
        "summary": {
            "artifacts": len(artifact_rows),
            "ai_events": len(usage_rows),
            "models": by_model,
            "intents": by_intent,
        },
        "artifacts": artifact_rows,
    }


def issue_public_api_credential(conn, *, organization_id: str, name: str, scopes: list[str] | None = None) -> dict[str, Any]:
    raw_secret = f"waos_live_{new_id('key')}_{new_id('sec')}"
    token_hash = _hash_token(raw_secret)
    row_id = new_id("pubkey")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO public_api_credentials (id, organization_id, name, token_hash, scopes_json, status, last_used_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)",
        (row_id, organization_id, name, token_hash, to_json(scopes or ["channels.write", "channels.read"]), "active", now, now),
    )
    row = fetch_one(conn, "SELECT * FROM public_api_credentials WHERE id = ?", (row_id,)) or {}
    append_immutable_audit_event(conn, organization_id=organization_id, event_type="integration.public_api_credential_issued", entity_type="public_api_credential", entity_id=row_id, payload={"name": name, "scopes": scopes or ["channels.write", "channels.read"]})
    return {**row, "scopes": from_json(row.get("scopes_json"), []), "token": raw_secret}


def authenticate_public_api_credential(conn, *, organization_id: str, token: str, required_scope: str | None = None) -> dict[str, Any] | None:
    token_hash = _hash_token(token)
    row = fetch_one(
        conn,
        "SELECT * FROM public_api_credentials WHERE organization_id = ? AND token_hash = ? AND status = ?",
        (organization_id, token_hash, "active"),
    )
    if not row:
        return None
    scopes = from_json(row.get("scopes_json"), [])
    if required_scope and required_scope not in scopes:
        return None
    execute(conn, "UPDATE public_api_credentials SET last_used_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), row["id"]))
    return {**row, "scopes": scopes}


def public_sdk_manifest() -> dict[str, Any]:
    return {
        "name": "waos-public-sdk",
        "version": settings.app_version,
        "authentication": {"header": "X-WAOS-Public-Key", "scope_model": "scoped_api_keys"},
        "capabilities": ["omnichannel_ingest", "defensive_rate_limits", "unified_identity_resolution"],
        "endpoints": [
            {"method": "POST", "path": "/api/public/v1/channels/events", "scope": "channels.write", "description": "Ingesta eventos omnicanal en inbox unificado"},
            {"method": "GET", "path": "/api/public/sdk/manifest", "scope": "public", "description": "Descubre endpoints y contratos públicos"},
            {"method": "GET", "path": "/api/v1/unified-inbox/overview", "scope": "channels.read", "description": "Vista consolidada de threads cross-channel"},
            {"method": "GET", "path": "/api/v1/runtime/autoscaling", "scope": "operations.read", "description": "Recomendaciones de autoscaling por backlog"},
        ],
        "channels": ["whatsapp", "telegram", "instagram_dm", "sms", "email", "webchat"],
    }


def _otel_hex_id(value: str, length: int) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:length]


def _otlp_attributes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, bool):
            items.append({"key": str(key), "value": {"boolValue": value}})
        elif isinstance(value, int):
            items.append({"key": str(key), "value": {"intValue": str(value)}})
        elif isinstance(value, float):
            items.append({"key": str(key), "value": {"doubleValue": value}})
        else:
            items.append({"key": str(key), "value": {"stringValue": str(value)}})
    return items


def _iso_to_unix_nano(value: str | None) -> str:
    dt = parse_iso(value)
    if not dt:
        return "0"
    return str(int(dt.timestamp() * 1_000_000_000))


def _build_otlp_payload(span_row: dict[str, Any]) -> dict[str, Any]:
    attributes = from_json(span_row.get("attributes_json"), {})
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": _otlp_attributes({"service.name": settings.otel_service_name, "service.version": settings.app_version})},
                "scopeSpans": [
                    {
                        "scope": {"name": "waos", "version": settings.app_version},
                        "spans": [
                            {
                                "traceId": _otel_hex_id(str(span_row.get("trace_id") or ""), 32),
                                "spanId": _otel_hex_id(str(span_row.get("span_id") or ""), 16),
                                "parentSpanId": _otel_hex_id(str(span_row.get("parent_span_id") or ""), 16) if span_row.get("parent_span_id") else "",
                                "name": span_row.get("name") or "waos.span",
                                "kind": 2,
                                "startTimeUnixNano": _iso_to_unix_nano(span_row.get("started_at")),
                                "endTimeUnixNano": _iso_to_unix_nano(span_row.get("ended_at") or span_row.get("started_at")),
                                "attributes": _otlp_attributes(
                                    {
                                        "status": span_row.get("status"),
                                        "organization_id": span_row.get("organization_id"),
                                        "bot_id": span_row.get("bot_id"),
                                        "conversation_id": span_row.get("conversation_id"),
                                        **attributes,
                                    }
                                ),
                            }
                        ],
                    }
                ],
            }
        ]
    }


def queue_otel_span_export(conn, span_row: dict[str, Any]) -> dict[str, Any] | None:
    if not span_row or not table_exists(conn, "otel_span_exports"):
        return None
    existing = fetch_one(
        conn,
        "SELECT * FROM otel_span_exports WHERE trace_id = ? AND span_id = ? ORDER BY created_at DESC LIMIT 1",
        (span_row.get("trace_id"), span_row.get("span_id")),
    )
    payload = _build_otlp_payload(span_row)
    target = default_export_target() or {}
    endpoint = target.get("endpoint") or None
    now = utcnow_iso()
    if existing:
        execute(
            conn,
            "UPDATE otel_span_exports SET endpoint = ?, payload_json = ?, status = ?, updated_at = ? WHERE id = ?",
            (endpoint, to_json(payload), "pending", now, existing["id"]),
        )
        row = fetch_one(conn, "SELECT * FROM otel_span_exports WHERE id = ?", (existing["id"],)) or None
    else:
        row_id = new_id("otlp")
        execute(
            conn,
            "INSERT INTO otel_span_exports (id, trace_id, span_id, organization_id, endpoint, payload_json, status, attempts, last_error, exported_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?)",
            (row_id, span_row.get("trace_id"), span_row.get("span_id"), span_row.get("organization_id"), endpoint, to_json(payload), "pending", now, now),
        )
        row = fetch_one(conn, "SELECT * FROM otel_span_exports WHERE id = ?", (row_id,)) or None
    if settings.otel_export_enabled and endpoint:
        flush_otel_exports(conn, limit=1)
    return row


def otel_export_overview(conn) -> dict[str, Any]:
    if not table_exists(conn, "otel_span_exports"):
        return {"totals": {"pending": 0, "exported": 0, "failed": 0}, "recent": []}
    rows = fetch_all(conn, "SELECT * FROM otel_span_exports ORDER BY updated_at DESC LIMIT 100")
    return {
        "totals": {
            "pending": sum(1 for row in rows if row.get("status") == "pending"),
            "exported": sum(1 for row in rows if row.get("status") == "exported"),
            "failed": sum(1 for row in rows if row.get("status") == "failed"),
        },
        "recent": rows[:20],
    }


def flush_otel_exports(conn, *, limit: int = 50, dry_run: bool = False) -> dict[str, Any]:
    if not table_exists(conn, "otel_span_exports"):
        return {"flushed": 0, "failed": 0, "dry_run": dry_run, "items": []}
    rows = fetch_all(conn, "SELECT * FROM otel_span_exports WHERE status IN ('pending', 'failed') ORDER BY updated_at ASC LIMIT ?", (limit,))
    target = default_export_target() or {}
    endpoint = str(target.get("endpoint") or "")
    headers = {"Content-Type": "application/json", **dict(target.get("headers") or {})}
    if dry_run or not endpoint:
        return {"flushed": 0, "failed": 0, "dry_run": (dry_run or not bool(endpoint)), "items": rows, "targets": resolve_apm_targets()}
    flushed = 0
    failed = 0
    item_results = []
    for row in rows:
        payload_raw = row.get("payload_json") or "{}"
        try:
            req = urllib_request.Request(endpoint, data=payload_raw.encode("utf-8"), headers=headers, method="POST")
            with urllib_request.urlopen(req, timeout=settings.otel_export_timeout_seconds) as response:
                code = getattr(response, "status", 200)
            execute(conn, "UPDATE otel_span_exports SET status = ?, attempts = attempts + 1, last_error = NULL, exported_at = ?, updated_at = ? WHERE id = ?", ("exported", utcnow_iso(), utcnow_iso(), row["id"]))
            flushed += 1
            item_results.append({"id": row.get("id"), "status": "exported", "http_status": code})
        except Exception as exc:
            execute(conn, "UPDATE otel_span_exports SET status = ?, attempts = attempts + 1, last_error = ?, updated_at = ? WHERE id = ?", ("failed", str(exc)[:500], utcnow_iso(), row["id"]))
            failed += 1
            item_results.append({"id": row.get("id"), "status": "failed", "error": str(exc)[:200]})
    return {"flushed": flushed, "failed": failed, "dry_run": False, "items": item_results}
