from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ...config import settings
from ...ai import run_ai_pipeline
from ...contracts import ok
from ...db import execute, fetch_all, fetch_one, get_connection
from ...platform import (
    approve_release_request,
    activate_mfa_factor,
    check_rate_limit,
    compute_observability_overview,
    create_auth_session,
    create_integration_sync_run,
    create_mfa_challenge,
    create_release_request,
    create_runtime_callback,
    diff_configs,
    enroll_mfa_factor,
    finish_integration_sync_run,
    get_security_policy,
    list_integration_sync_runs,
    list_rate_limit_policies,
    list_release_requests,
    list_runtime_callbacks,
    list_sso_providers,
    materialize_daily_metrics,
    publish_release_request,
    queue_overview,
    resolve_secret,
    serialize_mfa_factor,
    serialize_secret_row,
    record_bot_build,
    release_readiness,
    refresh_auth_session,
    revoke_auth_session,
    scheduler_overview,
    store_secret,
    upsert_integration,
    upsert_rate_limit_policy,
    upsert_security_policy,
    upsert_sso_provider,
    validate_bot_config,
    verify_mfa_challenge,
)
from ...repositories import (
    create_audit_log,
    create_bot,
    create_message,
    create_or_update_knowledge_items,
    create_organization,
    ensure_seed_data,
    get_bot,
    get_contact,
    get_contact_memory,
    get_conversation,
    get_org,
    get_whatsapp_number_by_phone_id,
    get_whatsapp_number_for_bot,
    list_bot_versions,
    publish_version,
    rollback_version,
    upsert_contact,
    upsert_conversation,
    upsert_memory,
)
from ...schemas import *
from ...security import accessible_org_ids, create_access_token, ensure_bot_access, ensure_org_access, get_current_user
from ...services import (
    bot_health_summary,
    integration_health_summary,
    list_report_generation_jobs,
    queue_executive_report_generation,
    runtime_overview,
)
from ...utils import add_minutes, from_json, hash_password, hash_value, new_id, parse_iso, password_needs_rehash, to_json, utcnow_iso, verify_hub_signature, verify_password, verify_signed_payload
from ...performance import clamp_limit, clamp_offset
from ...whatsapp import enqueue_manual_whatsapp_message, resolve_whatsapp_app_secret
from ...domains.payments import _ensure_crm_lead, confirm_payment, create_payment_request, create_whatsapp_flow
from ...domains.customer_experience import (
    seller_mode_summary,
    review_conversation,
    generate_reactivation_recommendations,
    ingest_voice_note,
    record_feedback,
    create_service_request,
    customer_experience_preview,
)
from ...domains.playbooks import create_playbook
from ...domains.appointments import (
    appointment_dashboard,
    cancel_appointment,
    confirm_appointment,
    create_appointment_bundle,
    mark_appointment_no_show,
    reschedule_appointment,
    send_appointment_followup,
)
from ...domains.reporting import (
    director_dashboard,
    generate_executive_report,
    omnichannel_overview,
    ensure_executive_report_pdf,
)
from ...domains.language import get_language_config, language_analytics, upsert_language_config
from ...domains.catalog import (
    business_hub_overview,
    commerce_insights,
    create_catalog_category,
    create_catalog_product,
    create_catalog_promotion,
    create_catalog_service,
    create_media_asset,
    create_promotion_rule,
    list_catalog_categories,
    list_catalog_products,
    list_catalog_promotions,
    list_catalog_services,
    list_media_assets,
    list_promotion_rules,
)
from ...domains.bot_behavior import (
    get_bot_behavior_settings,
    list_bot_response_templates,
    upsert_bot_behavior_settings,
    upsert_bot_response_template,
)

def _org_filter_sql(user: dict, organization_id: str | None, column: str = "organization_id") -> tuple[str, list]:
    params: list[Any] = []
    if organization_id:
        ensure_org_access(user, organization_id)
        return f" WHERE {column} = ? ", [organization_id]
    if user["global_role"] == "super_admin":
        return "", []
    org_ids = accessible_org_ids(user)
    if not org_ids:
        return f" WHERE 1 = 0 ", []
    placeholders = ",".join("?" for _ in org_ids)
    return f" WHERE {column} IN ({placeholders}) ", org_ids


def _bot_payload(conn, bot: dict) -> dict:
    number = get_whatsapp_number_for_bot(conn, bot["id"])
    versions = list_bot_versions(conn, bot["id"])
    payload = dict(bot)
    payload["config_draft"] = from_json(bot["config_draft_json"], {})
    payload["whatsapp_number"] = number
    payload["versions"] = versions
    return payload


def _conversation_payload(conn, conversation: dict) -> dict:
    contact = get_contact(conn, conversation["contact_id"])
    memory = get_contact_memory(conn, conversation["contact_id"], conversation["bot_id"])
    bot = get_bot(conn, conversation["bot_id"])
    messages = fetch_all(
        conn,
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation["id"],),
    )
    tags = [row["tag"] for row in fetch_all(conn, "SELECT tag FROM conversation_tags WHERE conversation_id = ? ORDER BY tag ASC", (conversation["id"],))]
    latest_summary_row = fetch_one(conn, "SELECT * FROM conversation_summaries WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1", (conversation["id"],))
    cross_bot_memory = fetch_all(
        conn,
        """
        SELECT cm.*, b.name AS bot_name
        FROM contact_memory cm
        JOIN bots b ON b.id = cm.bot_id
        WHERE cm.contact_id = ? AND cm.organization_id = ?
        ORDER BY cm.last_updated_at DESC
        """,
        (conversation["contact_id"], conversation["organization_id"]),
    )
    return {
        "conversation": conversation,
        "contact": contact,
        "memory": memory,
        "bot": bot,
        "tags": tags,
        "latest_summary": from_json(latest_summary_row.get("content_json"), {}) if latest_summary_row else None,
        "cross_bot_memory": [{**row, "memory": from_json(row.get("memory_json"), {})} for row in cross_bot_memory],
        "messages": [
            {
                **m,
                "metadata": from_json(m.get("metadata_json"), {}),
            }
            for m in messages
        ],
    }


def _normalize_memory(memory: dict | None) -> dict:
    if not memory:
        return {}
    return {**memory, "memory": from_json(memory.get("memory_json"), {})}


def _permissions_matrix() -> dict[str, list[str]]:
    return {
        "super_admin": [
            "org.manage", "bot.manage", "conversation.manage", "appointment.manage",
            "release.request", "release.approve", "release.publish",
            "integration.manage", "secret.manage", "rate_limit.manage",
            "audit.read", "security.manage", "runs.read", "logs.read",
            "scheduler.read", "operations.read", "operations.requeue", "client_view.read",
            "revenue.manage", "crm.manage", "insights.read", "playbooks.manage",
        ],
        "org_admin": [
            "bot.manage", "conversation.manage", "appointment.manage",
            "release.request", "release.approve", "release.publish",
            "integration.manage", "secret.manage", "rate_limit.manage",
            "audit.read", "security.manage", "runs.read", "logs.read",
            "scheduler.read", "operations.read", "operations.requeue", "client_view.read",
            "revenue.manage", "crm.manage", "insights.read", "playbooks.manage",
        ],
        "operator": [
            "conversation.manage", "appointment.manage", "release.request",
            "runs.read", "logs.read", "scheduler.read", "operations.read", "operations.requeue", "crm.manage", "insights.read",
        ],
        "client": ["client_view.read", "runs.read", "insights.read"],
    }


def _org_role(user: dict, organization_id: str) -> str:
    if user["global_role"] == "super_admin":
        return "super_admin"
    for membership in user.get("memberships", []):
        if membership.get("organization_id") == organization_id:
            return membership.get("role") or user.get("global_role")
    return user.get("global_role")


def _has_permission(user: dict, organization_id: str | None, permission: str) -> bool:
    if user["global_role"] == "super_admin":
        return True
    role = _org_role(user, organization_id) if organization_id else user.get("global_role")
    return permission in _permissions_matrix().get(role or "", [])


def _require_permission(user: dict, organization_id: str | None, permission: str) -> None:
    if not _has_permission(user, organization_id, permission):
        raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")


def _record_delivery_attempt(
    conn,
    *,
    organization_id: str,
    bot_id: str | None = None,
    conversation_id: str | None = None,
    entity_type: str,
    entity_id: str,
    channel: str,
    target: str | None = None,
    subject: str = "",
    body: str = "",
    status: str = "queued",
    provider: str | None = None,
    attempt_number: int = 1,
    metadata: dict[str, Any] | None = None,
    scheduled_at: str | None = None,
    delivered_at: str | None = None,
) -> dict[str, Any]:
    delivery_id = new_id("dlv")
    execute(
        conn,
        """
        INSERT INTO delivery_attempts
        (id, organization_id, bot_id, conversation_id, entity_type, entity_id, channel, target, subject, body, status, provider, attempt_number, metadata_json, scheduled_at, delivered_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (delivery_id, organization_id, bot_id, conversation_id, entity_type, entity_id, channel, target, subject, body, status, provider, attempt_number, to_json(metadata or {}), scheduled_at, delivered_at, utcnow_iso()),
    )
    row = fetch_one(conn, "SELECT * FROM delivery_attempts WHERE id = ?", (delivery_id,))
    return {**row, "metadata": from_json(row.get("metadata_json"), {})} if row else {"id": delivery_id}


def _select_followup_variant(conn, *, experiment: dict, conversation_id: str, preferred_variant: str | None = None) -> str:
    if preferred_variant in {"A", "B"}:
        return preferred_variant
    row = fetch_one(
        conn,
        "SELECT COUNT(*) AS total FROM followup_experiment_assignments WHERE experiment_id = ?",
        (experiment["id"],),
    )
    total = int((row or {}).get("total") or 0)
    return "A" if total % 2 == 0 else "B"


def _variant_body(experiment: dict, variant: str) -> str:
    return experiment.get("variant_a_text") if variant == "A" else experiment.get("variant_b_text")


def _mark_followup_reply(conn, *, conversation_id: str, inbound_message_id: str) -> dict[str, Any] | None:
    assignment = fetch_one(
        conn,
        """
        SELECT * FROM followup_experiment_assignments
        WHERE conversation_id = ? AND status = 'sent'
        ORDER BY assigned_at DESC
        LIMIT 1
        """,
        (conversation_id,),
    )
    if not assignment:
        return None
    execute(
        conn,
        "UPDATE followup_experiment_assignments SET status = 'replied', replied_at = ?, last_event_at = ?, metadata_json = ? WHERE id = ?",
        (utcnow_iso(), utcnow_iso(), to_json({**from_json(assignment.get("metadata_json"), {}), "reply_message_id": inbound_message_id}), assignment["id"]),
    )
    updated = fetch_one(conn, "SELECT * FROM followup_experiment_assignments WHERE id = ?", (assignment["id"],))
    return {**updated, "metadata": from_json(updated.get("metadata_json"), {})} if updated else None


def _insert_notification(conn, *, organization_id: str, bot_id: str | None, user_id: str | None, conversation_id: str | None, category: str, title: str, body: str, severity: str = "info", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    notification_id = new_id("notif")
    execute(
        conn,
        """
        INSERT INTO operator_notifications
        (id, organization_id, bot_id, user_id, conversation_id, category, channel, title, body, severity, status, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'in_app', ?, ?, ?, 'unread', ?, ?)
        """,
        (
            notification_id,
            organization_id,
            bot_id,
            user_id,
            conversation_id,
            category,
            title,
            body,
            severity,
            to_json(metadata or {}),
            utcnow_iso(),
        ),
    )
    created = fetch_one(conn, "SELECT * FROM operator_notifications WHERE id = ?", (notification_id,))
    return {**created, "metadata": from_json(created.get("metadata_json"), {})} if created else {}


def _detect_cancel_intent(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    keywords = {
        "cancelar": ["cancelar", "cancelacion", "cancelación"],
        "desinteres": ["ya no", "no me interesa", "mejor no", "olvidalo", "olvídalo"],
        "salida": ["bye", "adios", "adiós", "dejarlo"],
    }
    flags: list[str] = []
    for label, variants in keywords.items():
        if any(token in lowered for token in variants):
            flags.append(label)
    return flags


def _apply_routing_rules(conn, *, conversation: dict, bot: dict, contact: dict, memory: dict | None, body: str) -> dict[str, Any] | None:
    rows = fetch_all(
        conn,
        """
        SELECT * FROM routing_rules
        WHERE organization_id = ? AND status = 'active' AND (bot_id = ? OR bot_id IS NULL)
        ORDER BY priority DESC, updated_at DESC
        """,
        (conversation["organization_id"], conversation["bot_id"]),
    )
    for row in rows:
        matched = _matches_routing_rule(row, conversation=conversation, contact=contact, memory=memory, body=body)
        if not matched:
            continue
        params: list[Any] = [utcnow_iso()]
        updates = ["updated_at = ?"]
        if row.get("assigned_user_id"):
            updates.append("assigned_user_id = ?")
            params.append(row["assigned_user_id"])
        if matched.get("apply_takeover"):
            updates.extend(["status = 'human_takeover'", "human_takeover = 1", "ai_active = 0", "automation_freeze_until = ?"])
            params.append(add_minutes(utcnow_iso(), 30))
        params.append(conversation["id"])
        execute(conn, f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?", params)
        execute(
            conn,
            """
            INSERT INTO routing_assignments
            (id, rule_id, organization_id, bot_id, conversation_id, contact_id, assigned_user_id, assigned_team, matched_conditions_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id("rass"), row["id"], conversation["organization_id"], conversation["bot_id"], conversation["id"], conversation["contact_id"], row.get("assigned_user_id"), row.get("assigned_team"), to_json(matched["conditions"]), utcnow_iso()),
        )
        _insert_notification(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=conversation["bot_id"],
            user_id=row.get("assigned_user_id"),
            conversation_id=conversation["id"],
            category="routing",
            title="Conversacion asignada automaticamente",
            body=f"{contact.get('name') or contact.get('phone') or 'Lead'} fue asignado por la regla {row.get('name')}.",
            severity="info",
            metadata={"rule_id": row["id"], "assigned_team": row.get("assigned_team"), "matched_conditions": matched["conditions"]},
        )
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=row.get("created_by"), actor_type="system", entity_type="conversation", entity_id=conversation["id"], action="conversation.routed", metadata={"rule_id": row["id"], "matched_conditions": matched["conditions"], "apply_takeover": matched.get("apply_takeover")})
        return {"rule_id": row["id"], "rule_name": row.get("name"), "assigned_user_id": row.get("assigned_user_id"), "assigned_team": row.get("assigned_team"), "matched_conditions": matched["conditions"], "takeover_applied": matched.get("apply_takeover", False)}
    return None


def _handle_inbound(conn, *, bot_id: str, phone: str, name: str | None, body: str, external_id: str | None = None) -> dict:
    bot = get_bot(conn, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    rate_limit = check_rate_limit(conn, organization_id=bot["organization_id"], bot_id=bot_id, phone=phone)
    if not rate_limit.get("allowed"):
        raise HTTPException(status_code=429, detail={"message": "Rate limit exceeded", "rate_limit": rate_limit})
    if external_id:
        existing = fetch_one(conn, "SELECT * FROM messages WHERE external_id = ?", (external_id,))
        if existing:
            conversation = get_conversation(conn, existing["conversation_id"])
            contact = get_contact(conn, existing["contact_id"]) if existing.get("contact_id") else None
            return {
                "contact": contact,
                "conversation": conversation,
                "inbound_message": existing,
                "ai": {"deduplicated": True, "reason": "external_id_already_processed"},
            }
    contact = upsert_contact(conn, organization_id=bot["organization_id"], phone=phone, name=name)
    conversation = upsert_conversation(conn, organization_id=bot["organization_id"], bot_id=bot_id, contact_id=contact["id"])
    if conversation["status"] == "closed":
        execute(conn, "UPDATE conversations SET status = 'ai_active', ai_active = 1, updated_at = ? WHERE id = ?", (utcnow_iso(), conversation["id"]))
        conversation = get_conversation(conn, conversation["id"])
    memory = upsert_memory(conn, organization_id=bot["organization_id"], contact_id=contact["id"], bot_id=bot_id)
    inbound = create_message(
        conn,
        organization_id=bot["organization_id"],
        conversation_id=conversation["id"],
        contact_id=contact["id"],
        bot_id=bot_id,
        direction="inbound",
        kind="text",
        source="user",
        body=body,
        external_id=external_id,
        status="received",
        metadata={"channel": "whatsapp"},
    )
    execute(conn, "UPDATE conversations SET last_message_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), conversation["id"]))
    experiment_reply = _mark_followup_reply(conn, conversation_id=conversation["id"], inbound_message_id=inbound["id"])
    conversation = get_conversation(conn, conversation["id"])
    routing = _apply_routing_rules(conn, conversation=conversation, bot=bot, contact=contact, memory=memory, body=body)
    cancel_flags = _detect_cancel_intent(body)
    if cancel_flags:
        execute(
            conn,
            """
            UPDATE conversations
            SET status = 'human_takeover', human_takeover = 1, ai_active = 0, automation_freeze_until = ?, updated_at = ?
            WHERE id = ?
            """,
            (add_minutes(utcnow_iso(), 60), utcnow_iso(), conversation["id"]),
        )
        _insert_notification(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=conversation["bot_id"],
            user_id=(routing or {}).get("assigned_user_id") or conversation.get("assigned_user_id"),
            conversation_id=conversation["id"],
            category="risk",
            title="Lead con intencion de cancelar",
            body=f"{contact.get('name') or contact.get('phone') or 'Lead'} mostro senales de salida: {', '.join(cancel_flags)}.",
            severity="critical",
            metadata={"cancel_flags": cancel_flags},
        )
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=None, actor_type="system", entity_type="conversation", entity_id=conversation["id"], action="conversation.cancel_intent_detected", metadata={"flags": cancel_flags})
        return {
            "contact": contact,
            "conversation": get_conversation(conn, conversation["id"]),
            "inbound_message": inbound,
            "ai": {"skipped": True, "reason": "cancel_intent_detected", "routing": routing, "cancel_flags": cancel_flags, "experiment_reply": experiment_reply},
        }
    if routing and routing.get("takeover_applied"):
        return {
            "contact": contact,
            "conversation": get_conversation(conn, conversation["id"]),
            "inbound_message": inbound,
            "ai": {"skipped": True, "reason": "routing_takeover", "routing": routing, "experiment_reply": experiment_reply},
        }
    result = run_ai_pipeline(conn, incoming_message=inbound, conversation=conversation, bot=bot, contact=contact, memory=memory)
    if isinstance(result, dict):
        result["routing"] = routing
        result["experiment_reply"] = experiment_reply
    return {
        "contact": contact,
        "conversation": get_conversation(conn, conversation["id"]),
        "inbound_message": inbound,
        "ai": result,
    }


def _compute_dashboard(conn, organization_id: str | None = None) -> dict:
    params: list[Any] = []
    if organization_id:
        params = [organization_id]

    def count(sql_all: str, sql_org: str, extra_params: list[Any] | tuple[Any, ...] = ()) -> int:
        query_params = [*params, *list(extra_params)] if organization_id else list(extra_params)
        row = fetch_one(conn, sql_org if organization_id else sql_all, query_params)
        return int(row["value"]) if row else 0

    active_conversations = count(
        "SELECT COUNT(*) AS value FROM conversations WHERE status IN ('ai_active','human_takeover','waiting_followup')",
        "SELECT COUNT(*) AS value FROM conversations WHERE organization_id = ? AND status IN ('ai_active','human_takeover','waiting_followup')",
    )
    new_leads_cutoff = add_minutes(utcnow_iso(), -24 * 60)
    new_leads = count(
        "SELECT COUNT(*) AS value FROM contacts WHERE created_at >= ?",
        "SELECT COUNT(*) AS value FROM contacts WHERE organization_id = ? AND created_at >= ?",
        [new_leads_cutoff],
    )
    hot_leads = count(
        "SELECT COUNT(*) AS value FROM contact_memory WHERE lead_score >= 80",
        "SELECT COUNT(*) AS value FROM contact_memory WHERE organization_id = ? AND lead_score >= 80",
    )
    appointments = count(
        "SELECT COUNT(*) AS value FROM appointments WHERE status = 'scheduled'",
        "SELECT COUNT(*) AS value FROM appointments WHERE organization_id = ? AND status = 'scheduled'",
    )
    handoffs = count(
        "SELECT COUNT(*) AS value FROM conversations WHERE human_takeover = 1",
        "SELECT COUNT(*) AS value FROM conversations WHERE organization_id = ? AND human_takeover = 1",
    )
    messages_sent = count(
        "SELECT COUNT(*) AS value FROM messages WHERE direction = 'outbound'",
        "SELECT COUNT(*) AS value FROM messages WHERE organization_id = ? AND direction = 'outbound'",
    )
    bots_with_error = count(
        "SELECT COUNT(DISTINCT bot_id) AS value FROM message_ai_runs WHERE error IS NOT NULL AND error != ''",
        "SELECT COUNT(DISTINCT bot_id) AS value FROM message_ai_runs WHERE organization_id = ? AND error IS NOT NULL AND error != ''",
    )
    bots_paused = count(
        "SELECT COUNT(*) AS value FROM bots WHERE ai_paused = 1 AND deleted_at IS NULL",
        "SELECT COUNT(*) AS value FROM bots WHERE organization_id = ? AND ai_paused = 1 AND deleted_at IS NULL",
    )

    msg_sql = (
        "SELECT conversation_id, direction, created_at FROM messages WHERE organization_id = ? ORDER BY conversation_id, created_at ASC"
        if organization_id
        else "SELECT conversation_id, direction, created_at FROM messages ORDER BY conversation_id, created_at ASC"
    )
    rows = fetch_all(conn, msg_sql, params)
    conversation_pairs: dict[str, list[dict]] = {}
    for row in rows:
        conversation_pairs.setdefault(row["conversation_id"], []).append(row)
    deltas = []
    from datetime import datetime
    for items in conversation_pairs.values():
        for idx, item in enumerate(items):
            if item["direction"] != "inbound":
                continue
            for nxt in items[idx + 1 :]:
                if nxt["direction"] == "outbound":
                    try:
                        a = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                        b = datetime.fromisoformat(nxt["created_at"].replace("Z", "+00:00"))
                        deltas.append((b - a).total_seconds())
                    except Exception:
                        pass
                    break
    avg_response_time_seconds = round(sum(deltas) / len(deltas), 2) if deltas else None

    if organization_id:
        bot_sql = """
            SELECT b.id, b.name, b.organization_id, b.status, b.ai_paused,
                   COUNT(DISTINCT c.id) as conversations_active
            FROM bots b
            LEFT JOIN conversations c ON c.bot_id = b.id AND c.status IN ('ai_active','human_takeover','waiting_followup')
            WHERE b.organization_id = ? AND b.deleted_at IS NULL
            GROUP BY b.id, b.name, b.organization_id, b.status, b.ai_paused
            ORDER BY b.created_at DESC
        """
        bot_params = [organization_id]
    else:
        bot_sql = """
            SELECT b.id, b.name, b.organization_id, b.status, b.ai_paused,
                   COUNT(DISTINCT c.id) as conversations_active
            FROM bots b
            LEFT JOIN conversations c ON c.bot_id = b.id AND c.status IN ('ai_active','human_takeover','waiting_followup')
            WHERE b.deleted_at IS NULL
            GROUP BY b.id, b.name, b.organization_id, b.status, b.ai_paused
            ORDER BY b.created_at DESC
        """
        bot_params = []
    bots_breakdown = fetch_all(conn, bot_sql, bot_params)

    return {
        "summary": {
            "active_conversations": active_conversations,
            "new_leads": new_leads,
            "hot_leads": hot_leads,
            "appointments_scheduled": appointments,
            "human_handoffs": handoffs,
            "messages_sent": messages_sent,
            "bots_with_error": bots_with_error,
            "bots_paused": bots_paused,
            "avg_response_time_seconds": avg_response_time_seconds,
        },
        "bots": bots_breakdown,
    }


def _safe_hours_between(start: str | None, end: str | None) -> float | None:
    start_dt = parse_iso(start)
    end_dt = parse_iso(end)
    if not start_dt or not end_dt:
        return None
    return max(0.0, round((end_dt - start_dt).total_seconds() / 3600, 2))


def _matched_keywords(text: str, keyword_map: dict[str, list[str]]) -> list[str]:
    lower = (text or "").lower()
    matched: list[str] = []
    for label, words in keyword_map.items():
        if any(word in lower for word in words):
            matched.append(label)
    return matched


def _suggest_tone_from_messages(messages: list[dict]) -> str:
    transcript = _message_texts(messages[-6:]).lower()
    if any(token in transcript for token in ["usted", "quisiera", "agradezco", "cordial"]):
        return "formal"
    if any(token in transcript for token in ["jaja", "bro", "oye", "va", "super"]):
        return "casual"
    return "cercano"


def _conversation_risk_snapshot(conn, conversation: dict, threshold_hours: int = 4) -> dict[str, Any]:
    messages = fetch_all(conn, "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation["id"],))
    inbound_messages = [m for m in messages if m.get("direction") == "inbound"]
    outbound_messages = [m for m in messages if m.get("direction") in {"outbound", "internal"}]
    last_inbound = inbound_messages[-1] if inbound_messages else None
    last_outbound = outbound_messages[-1] if outbound_messages else None
    stale_hours = _safe_hours_between(last_inbound.get("created_at") if last_inbound else None, last_outbound.get("created_at") if last_outbound else utcnow_iso())
    if last_inbound and last_outbound and parse_iso(last_outbound.get("created_at")) and parse_iso(last_inbound.get("created_at")) and parse_iso(last_outbound.get("created_at")) >= parse_iso(last_inbound.get("created_at")):
        stale_hours = 0.0
    last_text = (last_inbound.get("body") if last_inbound else "") or ""
    cancel_flags = _matched_keywords(last_text, {
        "cancel_intent": ["cancel", "cancelar", "ya no", "no me interesa", "deja de escribir", "baja", "stop", "unsubscribe"],
        "price_objection": ["caro", "precio", "costoso", "muy caro"],
        "timing_objection": ["despues", "luego", "mas tarde", "ahorita no"],
        "trust_objection": ["confianza", "seguro", "garantia", "fraude"],
    })
    risk_score = 0
    if stale_hours and stale_hours >= threshold_hours:
        risk_score += min(60, int(stale_hours * 5))
    if "cancel_intent" in cancel_flags:
        risk_score += 40
    if conversation.get("human_takeover"):
        risk_score += 10
    return {
        "conversation_id": conversation["id"],
        "stale_hours": stale_hours or 0,
        "cancel_flags": cancel_flags,
        "risk_score": min(100, risk_score),
        "last_inbound": last_text,
        "at_risk": (stale_hours or 0) >= threshold_hours or "cancel_intent" in cancel_flags,
    }


def _best_contact_windows(conn, organization_id: str, contact_id: str | None = None, bot_id: str | None = None) -> list[dict[str, Any]]:
    params: list[Any] = [organization_id]
    where = " WHERE m.organization_id = ? AND m.direction = 'inbound' "
    if contact_id:
        where += " AND m.contact_id = ? "
        params.append(contact_id)
    if bot_id:
        where += " AND m.bot_id = ? "
        params.append(bot_id)
    rows = fetch_all(conn, f"SELECT created_at FROM messages m {where}", params)
    buckets: dict[int, int] = {}
    for row in rows:
        created = parse_iso(row.get("created_at"))
        if not created:
            continue
        hour = created.hour
        buckets[hour] = buckets.get(hour, 0) + 1
    ordered = sorted(buckets.items(), key=lambda item: (-item[1], item[0]))[:3]
    return [{"hour": hour, "label": f"{hour:02d}:00-{(hour + 1) % 24:02d}:00", "messages": count} for hour, count in ordered]


def _build_conversation_summary(conn, conversation: dict) -> dict[str, Any]:
    payload = _conversation_payload(conn, conversation)
    messages = payload["messages"]
    memory = payload.get("memory") or {}
    bot = payload.get("bot") or {}
    contact = payload.get("contact") or {}
    inbound_text = " ".join((m.get("body") or "") for m in messages if m.get("direction") == "inbound")
    objections = _matched_keywords(inbound_text, {
        "precio": ["precio", "caro", "costoso", "descuento"],
        "tiempo": ["despues", "luego", "mas tarde", "ahorita no"],
        "confianza": ["confianza", "seguro", "garantia", "fraude"],
        "ubicacion": ["ubicacion", "direccion", "donde"],
    })
    risk = _conversation_risk_snapshot(conn, conversation)
    windows = _best_contact_windows(conn, conversation["organization_id"], contact_id=conversation["contact_id"], bot_id=conversation["bot_id"])
    last_inbound = next((m for m in reversed(messages) if m.get("direction") == "inbound"), None)
    executive = f"{contact.get('name') or contact.get('phone') or 'Lead'} conversa con {bot.get('name') or 'bot'} en etapa {memory.get('lead_stage') or 'new'} con score {memory.get('lead_score') or 0}."
    if last_inbound and last_inbound.get("body"):
        executive += f" Ultimo mensaje: {str(last_inbound.get('body'))[:180]}"
    next_action = memory.get("next_action") or ("Escalar a humano" if "cancel_intent" in risk["cancel_flags"] else "Enviar follow-up contextual")
    return {
        "summary": executive,
        "lead_stage": memory.get("lead_stage") or "new",
        "lead_score": memory.get("lead_score") or 0,
        "objections": objections,
        "risk": risk,
        "recommended_next_action": next_action,
        "best_contact_windows": windows,
        "cross_bot_memory_count": len(payload.get("cross_bot_memory") or []),
        "generated_at": utcnow_iso(),
    }


def _copilot_suggestion(conn, conversation: dict, draft: str = "", objective: str = "reply") -> dict[str, Any]:
    payload = _conversation_payload(conn, conversation)
    messages = payload["messages"]
    memory = payload.get("memory") or {}
    contact = payload.get("contact") or {}
    tone = _suggest_tone_from_messages(messages)
    last_inbound = next((m for m in reversed(messages) if m.get("direction") == "inbound"), None)
    last_text = (last_inbound.get("body") if last_inbound else "") or ""
    risk = _conversation_risk_snapshot(conn, conversation)
    greeting = "Hola" if tone != "formal" else "Hola,"
    if "cancel_intent" in risk["cancel_flags"]:
        suggestion = f"{greeting} {contact.get('name') or ''}, gracias por decirmelo. Antes de cerrar, quiero asegurarme de resolver lo que te freno. Si fue por precio, tiempo o alguna duda puntual, te ayudo a resolverlo ahora mismo.".strip()
    elif objective == "book" or any(token in last_text.lower() for token in ["cita", "agendar", "agenda"]):
        suggestion = f"{greeting} {contact.get('name') or ''}, con gusto te ayudo a agendar. Comparteme el dia u horario que te funciona mejor y te propongo la mejor opcion disponible.".strip()
    elif any(token in last_text.lower() for token in ["precio", "caro", "costo", "cotizacion"]):
        suggestion = f"{greeting} {contact.get('name') or ''}, te ayudo con eso. Para recomendarte la mejor opcion, te comparto el rango y lo ajustamos segun lo que necesitas. Si quieres, tambien te dejo listo el siguiente paso para avanzar hoy.".strip()
    elif objective == "followup":
        suggestion = f"{greeting} {contact.get('name') or ''}, solo retomo tu consulta para que no se te enfrie. Vi que tu etapa actual es {memory.get('lead_stage') or 'new'} y puedo ayudarte a avanzar hoy en un solo mensaje.".strip()
    else:
        suggestion = draft.strip() or f"{greeting} {contact.get('name') or ''}, aqui estoy para ayudarte a avanzar. Vi tu ultimo mensaje y puedo resolverlo de forma rapida. ¿Prefieres que te ayude con informacion, cotizacion o agenda?".strip()
    return {
        "tone": tone,
        "objective": objective,
        "suggestion": suggestion,
        "risk_flags": risk["cancel_flags"],
        "source": "heuristic_v14",
    }


def _followup_experiment_performance(conn, experiment_id: str) -> dict[str, Any]:
    experiment = fetch_one(conn, "SELECT * FROM followup_experiments WHERE id = ?", (experiment_id,))
    if not experiment:
        raise HTTPException(status_code=404, detail="followup_experiment_not_found")
    rows = fetch_all(
        conn,
        "SELECT variant, status, COUNT(*) AS total FROM followup_experiment_assignments WHERE experiment_id = ? GROUP BY variant, status",
        (experiment_id,),
    )
    summary: dict[str, dict[str, Any]] = {
        "A": {"variant": "A", "sent": 0, "replied": 0, "reply_rate": 0.0, "booked": 0, "won": 0},
        "B": {"variant": "B", "sent": 0, "replied": 0, "reply_rate": 0.0, "booked": 0, "won": 0},
    }
    for row in rows:
        variant = str(row.get("variant") or "A")
        status = str(row.get("status") or "sent")
        total = int(row.get("total") or 0)
        bucket = summary.setdefault(variant, {"variant": variant, "sent": 0, "replied": 0, "reply_rate": 0.0, "booked": 0, "won": 0})
        bucket["sent"] += total
        if status in {"replied", "booked", "won"}:
            bucket["replied"] += total
        if status in {"booked", "won"}:
            bucket["booked"] += total
        if status == "won":
            bucket["won"] += total
    for bucket in summary.values():
        sent = int(bucket.get("sent") or 0)
        replied = int(bucket.get("replied") or 0)
        bucket["reply_rate"] = round((replied / sent) * 100, 2) if sent else 0.0
    assignments = fetch_all(
        conn,
        "SELECT * FROM followup_experiment_assignments WHERE experiment_id = ? ORDER BY assigned_at DESC LIMIT 25",
        (experiment_id,),
    )
    return {
        "experiment": {**experiment, "results": from_json(experiment.get("results_json"), {})},
        "variants": [summary["A"], summary["B"]],
        "assignments": [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in assignments],
    }
