from __future__ import annotations

from fastapi import HTTPException

from ...config import settings
from ...human_ops_runtime import build_human_reply_suggestion, build_supervisor_console, build_takeover_brief, detect_failed_takeover, qa_scorecard, recommend_ai_reactivation, save_structured_internal_note
from ...contracts import ok
from ...db import fetch_all, fetch_one, table_exists
from ...performance import clamp_limit, clamp_offset
from ...repositories import create_audit_log, create_message, get_bot, get_contact_memory, get_conversation
from ...security import ensure_bot_access, ensure_org_access
from ...serializers import serialize_conversation_details
from ...utils import add_minutes, from_json, new_id, to_json, utcnow_iso
from ...whatsapp import enqueue_manual_whatsapp_message
from ..conversation_presenters import decorate_conversation_item
from ..support import org_filter_sql, require_permission
from ..uow import UnitOfWork


from typing import Any

def handle(service, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
    conn = uow.conn
    conversation = service._get_accessible_conversation(conn, user, conversation_id)
    require_permission(user, conversation["organization_id"], "conversation.manage")
    row = fetch_one(
        conn,
        """
        SELECT c.*, ct.name as contact_name, ct.phone as contact_phone, b.name as bot_name,
               cm.lead_stage, cm.lead_score, cm.summary, cm.memory_json, cm.next_action, cm.followup_at,
               cm.current_intent, cm.urgency_score AS memory_urgency_score, cm.urgency_level AS memory_urgency_level,
               (SELECT body FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) AS latest_message_preview,
               (SELECT MAX(created_at) FROM messages WHERE conversation_id = c.id AND direction = 'inbound') AS last_inbound_at,
               (SELECT MAX(created_at) FROM messages WHERE conversation_id = c.id AND direction = 'outbound') AS last_outbound_at,
               (SELECT COUNT(*) FROM appointments a WHERE a.conversation_id = c.id AND a.status NOT IN ('cancelled','no_show')) AS appointment_count,
               (SELECT COUNT(*) FROM commerce_payments p WHERE p.conversation_id = c.id AND p.status IN ('pending','pending_provider','requires_action')) AS pending_payment_count,
               (SELECT COALESCE(MAX(close_probability), 0) FROM crm_leads l WHERE l.conversation_id = c.id) AS close_probability,
               (SELECT best_next_action FROM crm_leads l WHERE l.conversation_id = c.id ORDER BY updated_at DESC LIMIT 1) AS lead_best_next_action
        FROM conversations c
        JOIN contacts ct ON ct.id = c.contact_id
        JOIN bots b ON b.id = c.bot_id
        LEFT JOIN contact_memory cm ON cm.contact_id = c.contact_id AND cm.bot_id = c.bot_id
        WHERE c.id = ?
        LIMIT 1
        """,
        (conversation_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    item = service._decorate_item(row)
    latest_ai_run = fetch_one(conn, "SELECT * FROM message_ai_runs WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1", (conversation_id,)) if table_exists(conn, "message_ai_runs") else None
    latest_reasoning = fetch_one(conn, "SELECT * FROM message_operational_reasoning WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1", (conversation_id,)) if table_exists(conn, "message_operational_reasoning") else None
    classifier_output = from_json((latest_ai_run or {}).get("classifier_output"), {})
    decision_output = from_json((latest_ai_run or {}).get("decision_output"), {})
    fallback_chain = from_json((latest_ai_run or {}).get("fallback_chain_json"), [])
    reasoning_summary = from_json((latest_reasoning or {}).get("summary_json"), {})

    confidence = 35
    if latest_ai_run and not latest_ai_run.get("error"):
        confidence += 20
    if classifier_output.get("intent") or latest_reasoning and latest_reasoning.get("intent_detected"):
        confidence += 15
    if decision_output.get("action") or (latest_ai_run or {}).get("action_taken"):
        confidence += 10
    if (latest_reasoning or {}).get("policy_applied") or (latest_ai_run or {}).get("decision_policy"):
        confidence += 10
    if not fallback_chain:
        confidence += 10
    if item.get("requires_human"):
        confidence -= 10
    if item.get("sla_status") == "breached":
        confidence -= 5
    confidence = max(5, min(95, int(confidence)))
    band = "high" if confidence >= 75 else "medium" if confidence >= 50 else "low"
    risk_flags = []
    if confidence < 50:
        risk_flags.append({"key": "low_confidence", "severity": "medium", "message": "La señal de confianza es baja para automatizar sin revisión."})
    if str(item.get("work_queue_role") or "") == "cobranza":
        risk_flags.append({"key": "payment_sensitive", "severity": "medium", "message": "La conversación toca cobro o pago pendiente."})
    if (latest_ai_run or {}).get("error"):
        risk_flags.append({"key": "ai_run_error", "severity": "high", "message": str((latest_ai_run or {}).get("error"))})

    explanation = {
        "intent_detected": (latest_reasoning or {}).get("intent_detected") or classifier_output.get("intent") or item.get("current_intent"),
        "policy_applied": (latest_reasoning or {}).get("policy_applied") or (latest_ai_run or {}).get("decision_policy") or decision_output.get("policy"),
        "action_taken": (latest_ai_run or {}).get("action_taken") or decision_output.get("action"),
        "classifier_source": (latest_ai_run or {}).get("classifier_source"),
        "generator_source": (latest_ai_run or {}).get("generator_source"),
        "fallback_chain": fallback_chain,
        "summary": reasoning_summary,
        "why": [
            f"Queue sugerida: {item.get('work_queue_role')}",
            f"SLA actual: {item.get('sla_status')}",
            f"Prioridad calculada: {item.get('priority_score')}",
            f"Siguiente acción: {item.get('next_best_action')}",
        ],
    }
    if table_exists(conn, "bot_decision_explanations"):
        conn.execute(
            "INSERT INTO bot_decision_explanations (id, organization_id, conversation_id, message_ai_run_id, confidence_score, confidence_band, explanation_json, risk_flags_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id("bexp"), conversation["organization_id"], conversation_id, (latest_ai_run or {}).get("id"), confidence, band, to_json(explanation), to_json(risk_flags), utcnow_iso()),
        )
    takeover_brief = build_takeover_brief(conn, conversation_id, brief_type="decision_support", generated_by_user_id=user.get("id"), persist=False)
    failed_takeover = detect_failed_takeover(conn, conversation_id)
    reactivation = recommend_ai_reactivation(conn, conversation_id)
    reply_suggestion = build_human_reply_suggestion(conn, conversation_id, objective="reply", operator_user_id=user.get("id"), persist=False)
    return ok({
        "conversation_id": conversation_id,
        "next_best_action": item.get("next_best_action"),
        "priority_score": item.get("priority_score"),
        "priority_band": item.get("priority_band"),
        "confidence_score": confidence,
        "confidence_band": band,
        "queue": {"role_key": item.get("work_queue_role"), "reason": item.get("work_queue_reason")},
        "sla": {"status": item.get("sla_status"), "due_at": item.get("sla_due_at"), "target_minutes": item.get("sla_target_minutes"), "overdue_minutes": item.get("sla_overdue_minutes")},
        "explanation": explanation,
        "risk_flags": risk_flags,
        "takeover_brief": takeover_brief,
        "failed_takeover": failed_takeover,
        "reactivation_guardrails": reactivation,
        "reply_suggestion": reply_suggestion,
    })
