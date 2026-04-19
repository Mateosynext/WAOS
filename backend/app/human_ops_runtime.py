from __future__ import annotations

from typing import Any

from .contact_intelligence import enrich_conversation_row
from .db import fetch_all, fetch_one, table_exists
from .knowledge_runtime import search_governed_knowledge
from .repositories import create_audit_log, create_message
from .utils import add_minutes, from_json, new_id, parse_iso, to_json, utcnow_iso


_TEAM_CAPACITY_BASELINES = {
    "ventas": 12,
    "agenda": 16,
    "cobranza": 10,
    "soporte": 14,
}


def _conversation_row(conn, conversation_id: str) -> dict[str, Any] | None:
    return fetch_one(
        conn,
        """
        SELECT c.*, ct.name AS contact_name, ct.phone AS contact_phone, b.name AS bot_name,
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


def _conversation_messages(conn, conversation_id: str, *, limit: int = 30) -> list[dict[str, Any]]:
    return fetch_all(
        conn,
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
        (conversation_id, limit),
    )


def _latest_structured_notes(conn, conversation_id: str, *, limit: int = 3) -> list[dict[str, Any]]:
    if not table_exists(conn, "conversation_internal_notes"):
        return []
    rows = fetch_all(
        conn,
        "SELECT * FROM conversation_internal_notes WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
        (conversation_id, limit),
    )
    return [
        {
            **row,
            "next_steps": from_json(row.get("next_steps_json"), []),
            "sources": from_json(row.get("sources_json"), []),
            "risk_flags": from_json(row.get("risk_flags_json"), []),
            "metadata": from_json(row.get("metadata_json"), {}),
        }
        for row in rows
    ]


def _queue_role_for_item(item: dict[str, Any]) -> tuple[str, str]:
    intent = str(item.get("current_intent") or "").lower()
    if int(item.get("pending_payment_count") or 0) > 0 or intent in {"payment", "invoice", "cobranza", "charge"}:
        return "cobranza", "Tiene pago pendiente o intento de cobro activo"
    if int(item.get("appointment_count") or 0) > 0 or intent in {"schedule", "appointment", "reschedule", "booking"}:
        return "agenda", "Tiene cita o intención clara de agenda"
    if int(item.get("lead_score") or 0) >= 60 or int(item.get("close_probability") or 0) >= 60 or str(item.get("lead_stage") or "").lower() in {"hot", "qualified", "propuesta", "cotizacion", "nuevo"}:
        return "ventas", "Lead activo con oportunidad comercial"
    return "soporte", "Necesita seguimiento operativo o soporte humano"


def _sla_for_item(item: dict[str, Any]) -> dict[str, Any]:
    role_key, _ = _queue_role_for_item(item)
    now = parse_iso(utcnow_iso())
    anchor = parse_iso(item.get("last_inbound_at") or item.get("updated_at") or item.get("created_at"))
    overdue_minutes = 0
    target_minutes = {"ventas": 10, "soporte": 20, "agenda": 8, "cobranza": 15}.get(role_key, 15)
    if anchor and now:
        overdue_minutes = max(0, int((now - anchor).total_seconds() // 60) - target_minutes)
    status = "healthy"
    if overdue_minutes > 0:
        status = "breached"
    elif anchor and now and int((now - anchor).total_seconds() // 60) >= max(1, target_minutes - 3):
        status = "at_risk"
    return {
        "role_key": role_key,
        "target_minutes": target_minutes,
        "due_at": add_minutes(item.get("last_inbound_at") or item.get("updated_at") or utcnow_iso(), target_minutes),
        "status": status,
        "overdue_minutes": overdue_minutes,
    }


def _decorate_item(item: dict[str, Any]) -> dict[str, Any]:
    item = enrich_conversation_row(item)
    priority_score = min(100, int(item.get("urgency_score") or 0) + int(item.get("lead_score") or 0) + min(20, int(item.get("close_probability") or 0) // 5))
    item["priority_score"] = priority_score
    item["priority_band"] = "critical" if priority_score >= 90 else "high" if priority_score >= 70 else "medium" if priority_score >= 40 else "normal"
    item["next_best_action"] = item.get("lead_best_next_action") or item.get("next_action") or (
        "Responder con humano"
        if str(item.get("status") or "").lower() == "human_takeover"
        else "Enviar siguiente paso"
        if int(item.get("lead_score") or 0) >= 70
        else "Dar seguimiento"
    )
    item["requires_human"] = bool(str(item.get("status") or "").lower() == "human_takeover" or str(item.get("attention_tier") or "").lower() == "owner_now")
    queue_role, queue_reason = _queue_role_for_item(item)
    item["work_queue_role"] = queue_role
    item["work_queue_reason"] = queue_reason
    sla = _sla_for_item(item)
    item["sla_status"] = sla["status"]
    item["sla_due_at"] = sla["due_at"]
    item["sla_target_minutes"] = sla["target_minutes"]
    item["sla_overdue_minutes"] = sla["overdue_minutes"]
    return item


def _match_macros(item: dict[str, Any], messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_inbound = next((m for m in reversed(messages) if m.get("direction") == "inbound"), None)
    last_text = str((latest_inbound or {}).get("body") or "").lower()
    queue_role = str(item.get("work_queue_role") or "soporte")
    macros: list[dict[str, Any]] = []
    if queue_role == "agenda" or any(token in last_text for token in ["agenda", "cita", "horario", "disponibilidad"]):
        macros.append({"key": "agenda_confirm", "label": "Confirmar disponibilidad", "why": "El lead está listo para coordinar agenda."})
    if queue_role == "cobranza" or any(token in last_text for token in ["precio", "pago", "costo", "factura"]):
        macros.append({"key": "payment_recovery", "label": "Resolver pago y objeción", "why": "La conversación toca cobro o precio."})
    if any(token in last_text for token in ["humano", "asesor", "agente", "supervisor"]):
        macros.append({"key": "human_ack", "label": "Acuse de takeover", "why": "El cliente pidió atención humana explícita."})
    if not macros:
        macros.append({"key": "standard_followup", "label": "Seguimiento contextual", "why": "Mantener continuidad y cerrar con siguiente paso."})
    return macros[:3]


def save_structured_internal_note(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str,
    contact_id: str,
    author_user_id: str,
    category: str,
    priority: str,
    summary: str,
    detail: str = "",
    next_steps: list[str] | None = None,
    sources: list[str] | None = None,
    risk_level: str = "low",
    risk_flags: list[str] | None = None,
    visibility: str = "internal",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    next_steps = [str(item).strip() for item in (next_steps or []) if str(item).strip()]
    sources = [str(item).strip() for item in (sources or []) if str(item).strip()]
    risk_flags = [str(item).strip() for item in (risk_flags or []) if str(item).strip()]
    note_id = new_id("inote")
    now = utcnow_iso()
    rendered_lines = [
        f"[{category}/{priority}] {summary}",
        detail.strip(),
        f"Risk: {risk_level}" if risk_level else "",
        f"Next: {' | '.join(next_steps)}" if next_steps else "",
        f"Sources: {' | '.join(sources)}" if sources else "",
    ]
    rendered_body = "\n".join(line for line in rendered_lines if line).strip()
    message = create_message(
        conn,
        organization_id=organization_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        bot_id=bot_id,
        direction="internal",
        kind="note",
        source="human",
        body=rendered_body,
        status="internal",
        metadata={
            "author_user_id": author_user_id,
            "structured": True,
            "category": category,
            "priority": priority,
            "risk_level": risk_level,
        },
    )
    conn.execute(
        """
        INSERT INTO conversation_internal_notes
        (id, organization_id, bot_id, conversation_id, contact_id, message_id, author_user_id, category, priority, visibility, summary, detail, next_steps_json, sources_json, risk_level, risk_flags_json, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            note_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            message["id"],
            author_user_id,
            category,
            priority,
            visibility,
            summary,
            detail,
            to_json(next_steps),
            to_json(sources),
            risk_level,
            to_json(risk_flags),
            to_json(metadata or {}),
            now,
        ),
    )
    create_audit_log(
        conn,
        organization_id=organization_id,
        actor_user_id=author_user_id,
        actor_type="user",
        entity_type="conversation",
        entity_id=conversation_id,
        action="conversation.structured_internal_note_added",
        metadata={"category": category, "priority": priority, "risk_level": risk_level, "note_id": note_id},
    )
    return {
        "id": note_id,
        "message_id": message["id"],
        "category": category,
        "priority": priority,
        "summary": summary,
        "detail": detail,
        "next_steps": next_steps,
        "sources": sources,
        "risk_level": risk_level,
        "risk_flags": risk_flags,
        "visibility": visibility,
        "created_at": now,
    }


def build_takeover_brief(conn, conversation_id: str, *, brief_type: str = "takeover", generated_by_user_id: str | None = None, persist: bool = True) -> dict[str, Any]:
    row = _conversation_row(conn, conversation_id)
    if not row:
        raise ValueError("conversation_not_found")
    item = _decorate_item(row)
    messages = _conversation_messages(conn, conversation_id, limit=40)
    notes = _latest_structured_notes(conn, conversation_id, limit=3)
    latest_inbound = next((m for m in reversed(messages) if m.get("direction") == "inbound"), None)
    latest_outbound = next((m for m in reversed(messages) if m.get("direction") == "outbound"), None)
    summary = str(item.get("summary") or "").strip()
    objections = [note.get("summary") for note in notes if note.get("category") in {"quality", "risk", "billing", "compliance"}]
    pending_items: list[str] = []
    if int(item.get("pending_payment_count") or 0) > 0:
        pending_items.append("Pago pendiente por resolver")
    if int(item.get("appointment_count") or 0) > 0:
        pending_items.append("Hay cita existente o agenda abierta")
    if item.get("followup_at"):
        pending_items.append(f"Follow-up comprometido para {item.get('followup_at')}")
    if not pending_items:
        pending_items.append("Confirmar siguiente paso antes de devolver a IA")
    payload = {
        "conversation_id": conversation_id,
        "brief_type": brief_type,
        "contact": {"name": item.get("contact_name"), "phone": item.get("contact_phone")},
        "lead": {
            "stage": item.get("lead_stage") or "new",
            "score": int(item.get("lead_score") or 0),
            "intent": item.get("current_intent"),
            "urgency_score": int(item.get("urgency_score") or 0),
        },
        "queue": {"role_key": item.get("work_queue_role"), "reason": item.get("work_queue_reason")},
        "sla": {
            "status": item.get("sla_status"),
            "due_at": item.get("sla_due_at"),
            "target_minutes": item.get("sla_target_minutes"),
            "overdue_minutes": item.get("sla_overdue_minutes"),
        },
        "latest_inbound": {"body": (latest_inbound or {}).get("body"), "created_at": (latest_inbound or {}).get("created_at")},
        "latest_outbound": {"body": (latest_outbound or {}).get("body"), "created_at": (latest_outbound or {}).get("created_at")},
        "executive_summary": summary or f"Conversación priorizada en {item.get('work_queue_role')} con score {item.get('priority_score')}",
        "pending_items": pending_items,
        "next_best_action": item.get("next_best_action"),
        "notes": notes,
        "objections_or_risks": objections,
        "macros": _match_macros(item, messages),
        "generated_at": utcnow_iso(),
    }
    if persist and table_exists(conn, "conversation_takeover_briefs"):
        conn.execute(
            """
            INSERT INTO conversation_takeover_briefs
            (id, organization_id, bot_id, conversation_id, contact_id, brief_type, content_json, generated_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("tobr"),
                row["organization_id"],
                row["bot_id"],
                conversation_id,
                row["contact_id"],
                brief_type,
                to_json(payload),
                generated_by_user_id,
                utcnow_iso(),
            ),
        )
    return payload


def detect_failed_takeover(conn, conversation_id: str) -> dict[str, Any]:
    row = _conversation_row(conn, conversation_id)
    if not row:
        raise ValueError("conversation_not_found")
    messages = _conversation_messages(conn, conversation_id, limit=50)
    takeover_anchor = parse_iso(row.get("last_human_at") or row.get("updated_at") or row.get("created_at"))
    latest_inbound = next((m for m in reversed(messages) if m.get("direction") == "inbound"), None)
    latest_human = next((m for m in reversed(messages) if m.get("direction") in {"outbound", "internal"} and m.get("source") in {"human", "operator"}), None)
    inbound_after_takeover = 0
    if takeover_anchor:
        for message in messages:
            created = parse_iso(message.get("created_at"))
            if created and created >= takeover_anchor and message.get("direction") == "inbound":
                inbound_after_takeover += 1
    reasons: list[str] = []
    score = 0
    if str(row.get("status") or "").lower() == "human_takeover":
        score += 25
    if inbound_after_takeover >= 2:
        reasons.append("Múltiples mensajes del cliente tras takeover sin cierre claro")
        score += 30
    latest_inbound_at = parse_iso((latest_inbound or {}).get("created_at"))
    latest_human_at = parse_iso((latest_human or {}).get("created_at"))
    if latest_inbound_at and (not latest_human_at or latest_human_at < latest_inbound_at):
        reasons.append("La última señal sigue siendo inbound del cliente")
        score += 25
    freeze_until = parse_iso(row.get("automation_freeze_until"))
    now = parse_iso(utcnow_iso())
    if freeze_until and now and freeze_until < now and str(row.get("status") or "").lower() == "human_takeover":
        reasons.append("El freeze del takeover expiró sin resolución explícita")
        score += 20
    severity = "critical" if score >= 70 else "high" if score >= 45 else "medium" if score >= 25 else "low"
    return {
        "conversation_id": conversation_id,
        "failed_takeover": score >= 45,
        "risk_score": min(100, score),
        "severity": severity,
        "reasons": reasons,
        "inbound_after_takeover": inbound_after_takeover,
        "last_human_at": (latest_human or {}).get("created_at") or row.get("last_human_at"),
        "last_inbound_at": (latest_inbound or {}).get("created_at") or row.get("last_inbound_at"),
    }


def _governed_sources(conn, row: dict[str, Any], last_text: str, intent: str | None) -> list[dict[str, Any]]:
    if not row.get("organization_id") or not row.get("bot_id") or not last_text.strip():
        return []
    hits = search_governed_knowledge(
        conn,
        organization_id=row["organization_id"],
        bot_id=row["bot_id"],
        query=last_text,
        intent=intent,
        limit=3,
    )
    return [
        {
            "type": "governed_knowledge",
            "label": hit.get("title") or hit.get("source_key"),
            "excerpt": str(hit.get("content_text") or "")[:180],
            "domain": hit.get("domain"),
            "freshness_status": hit.get("freshness_status"),
            "traceability": hit.get("traceability") or {},
        }
        for hit in hits
    ]


def build_human_reply_suggestion(
    conn,
    conversation_id: str,
    *,
    objective: str = "reply",
    draft: str = "",
    operator_user_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    row = _conversation_row(conn, conversation_id)
    if not row:
        raise ValueError("conversation_not_found")
    item = _decorate_item(row)
    messages = _conversation_messages(conn, conversation_id, limit=40)
    notes = _latest_structured_notes(conn, conversation_id, limit=2)
    latest_inbound = next((m for m in reversed(messages) if m.get("direction") == "inbound"), None)
    last_text = str((latest_inbound or {}).get("body") or "")
    lower = last_text.lower()
    contact_name = item.get("contact_name") or ""
    risk = detect_failed_takeover(conn, conversation_id)
    sources: list[dict[str, Any]] = []
    if latest_inbound:
        sources.append({"type": "message", "label": "latest_inbound", "excerpt": last_text[:180], "created_at": latest_inbound.get("created_at")})
    if item.get("summary"):
        sources.append({"type": "memory", "label": "contact_memory", "excerpt": str(item.get("summary"))[:180]})
    for note in notes:
        sources.append({"type": "internal_note", "label": note.get("category"), "excerpt": str(note.get("summary") or note.get("detail") or "")[:180], "risk_level": note.get("risk_level")})
    sources.extend(_governed_sources(conn, row, last_text, str(item.get("current_intent") or "") or None))

    greeting = f"Hola {contact_name},".strip().rstrip(",") + "," if contact_name else "Hola,"
    if draft.strip():
        suggestion = draft.strip()
    elif objective == "book" or any(token in lower for token in ["cita", "agendar", "agenda", "horario"]):
        suggestion = f"{greeting} con gusto te ayudo a agendar. Te propongo resolverlo en este paso: compárteme el horario que más te acomoda y te confirmo la mejor opción disponible hoy."
    elif any(token in lower for token in ["precio", "cotización", "cotizacion", "costo", "pago"]):
        suggestion = f"{greeting} te ayudo con eso. Para darte una respuesta clara y sin vueltas, reviso tu caso y te comparto la mejor opción con el siguiente paso exacto para avanzar hoy."
    elif any(token in lower for token in ["humano", "asesor", "agente", "supervisor"]):
        suggestion = f"{greeting} ya tomé tu caso y te voy a dar seguimiento personalmente. Estoy revisando el contexto para responderte con precisión y dejarte una solución concreta."
    elif objective == "followup":
        suggestion = f"{greeting} retomo tu solicitud para que no se enfríe. Vi tu contexto y puedo ayudarte a avanzar en este momento con el siguiente paso más conveniente para ti."
    else:
        suggestion = f"{greeting} ya revisé tu mensaje y tu contexto. Te ayudo a resolverlo de forma clara y rápida; si te parece, avanzamos por el siguiente paso que mejor encaja con tu caso."

    risk_flags: list[dict[str, Any]] = []
    if int(item.get("pending_payment_count") or 0) > 0:
        risk_flags.append({"key": "payment_sensitive", "severity": "medium", "message": "Hay pago pendiente o una conversación sensible de cobro."})
    if risk.get("failed_takeover"):
        risk_flags.append({"key": "failed_takeover", "severity": risk.get("severity"), "message": "; ".join(risk.get("reasons") or [])})
    stale_sources = [source for source in sources if source.get("freshness_status") == "stale"]
    if stale_sources:
        risk_flags.append({"key": "stale_knowledge", "severity": "medium", "message": "Parte del grounding está stale; valida catálogo/políticas antes de enviar."})

    explanation = {
        "objective": objective,
        "why": [
            f"Queue operativa: {item.get('work_queue_role')}",
            f"Prioridad actual: {item.get('priority_band')} ({item.get('priority_score')})",
            f"Siguiente mejor acción: {item.get('next_best_action')}",
        ],
        "operator_guidance": [
            "Responder con una acción concreta, no solo con información.",
            "Cerrar con CTA único para reducir fricción.",
            "No devolver a IA si el takeover falló o sigue el riesgo de cobro.",
        ],
    }
    response = {
        "conversation_id": conversation_id,
        "objective": objective,
        "suggestion": suggestion,
        "sources": sources[:6],
        "risk": {
            "level": "high" if any(flag.get("severity") in {"high", "critical"} for flag in risk_flags) else "medium" if risk_flags else "low",
            "flags": risk_flags,
            "failed_takeover": risk,
        },
        "explanation": explanation,
        "next_best_action": item.get("next_best_action"),
        "macros": _match_macros(item, messages),
        "takeover_reactivation_guardrails": recommend_ai_reactivation(conn, conversation_id),
        "source": "human_ops_supervision_v1",
    }
    if persist and table_exists(conn, "human_reply_suggestions"):
        conn.execute(
            """
            INSERT INTO human_reply_suggestions
            (id, organization_id, bot_id, conversation_id, contact_id, operator_user_id, objective, draft_text, suggestion_text, explanation_json, sources_json, risk_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'suggested', ?)
            """,
            (
                new_id("hrsug"),
                row["organization_id"],
                row["bot_id"],
                conversation_id,
                row["contact_id"],
                operator_user_id,
                objective,
                draft,
                suggestion,
                to_json(explanation),
                to_json(response["sources"]),
                to_json(response["risk"]),
                utcnow_iso(),
            ),
        )
    return response


def recommend_ai_reactivation(conn, conversation_id: str) -> dict[str, Any]:
    row = _conversation_row(conn, conversation_id)
    if not row:
        raise ValueError("conversation_not_found")
    risk = detect_failed_takeover(conn, conversation_id)
    reasons: list[str] = []
    blockers: list[str] = []
    if risk.get("failed_takeover"):
        blockers.append("Existe takeover fallido o no resuelto")
    if int(row.get("pending_payment_count") or 0) > 0:
        blockers.append("Hay pago pendiente o conversación de cobranza")
    if str(row.get("current_intent") or "").lower() in {"complaint", "legal", "refund"}:
        blockers.append("Intent sensible; requiere cierre humano explícito")
    if blockers:
        decision = "blocked"
    else:
        decision = "allowed"
        reasons.extend([
            "No hay riesgos críticos abiertos.",
            "La conversación puede volver a IA con guardrails de seguimiento.",
        ])
    return {
        "conversation_id": conversation_id,
        "decision": decision,
        "allowed": decision == "allowed",
        "blockers": blockers,
        "reasons": reasons,
        "reactivation_plan": [
            "Dejar última nota interna con contexto y next action.",
            "Reactivar IA con freeze limpio y sin owner asignado.",
            "Monitorear el primer turno post-reactivación.",
        ] if decision == "allowed" else [],
    }


def qa_scorecard(conn, organization_id: str, *, bot_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = [organization_id]
    where = "WHERE cr.organization_id = ?"
    if bot_id:
        where += " AND cr.bot_id = ?"
        params.append(bot_id)
    reviews = fetch_all(
        conn,
        f"""
        SELECT cr.*, c.contact_id, c.bot_id AS conversation_bot_id, c.id AS conv_id
        FROM conversation_reviews cr
        JOIN conversations c ON c.id = cr.conversation_id
        {where}
        ORDER BY cr.created_at DESC
        LIMIT 200
        """,
        params,
    )
    by_agent: dict[str, dict[str, Any]] = {}
    by_bot: dict[str, dict[str, Any]] = {}
    coaching: list[dict[str, Any]] = []
    for row in reviews:
        agent_key = str(row.get("agent_user_id") or "bot")
        agent_bucket = by_agent.setdefault(agent_key, {"agent_user_id": row.get("agent_user_id"), "reviews": 0, "avg_quality": 0.0, "response_delay_seconds": 0.0, "review_type_mix": {}})
        agent_bucket["reviews"] += 1
        agent_bucket["avg_quality"] += float(row.get("quality_score") or 0)
        agent_bucket["response_delay_seconds"] += float(row.get("response_delay_seconds") or 0)
        review_type = str(row.get("review_type") or "general")
        agent_bucket["review_type_mix"][review_type] = int(agent_bucket["review_type_mix"].get(review_type) or 0) + 1

        bot_key = str(row.get("bot_id") or "unknown")
        bot_bucket = by_bot.setdefault(bot_key, {"bot_id": row.get("bot_id"), "reviews": 0, "avg_quality": 0.0})
        bot_bucket["reviews"] += 1
        bot_bucket["avg_quality"] += float(row.get("quality_score") or 0)

    for bucket in by_agent.values():
        reviews_count = max(1, int(bucket.get("reviews") or 0))
        bucket["avg_quality"] = round(float(bucket.get("avg_quality") or 0) / reviews_count, 2)
        bucket["response_delay_seconds"] = round(float(bucket.get("response_delay_seconds") or 0) / reviews_count, 2)
        if bucket["avg_quality"] < 85:
            coaching.append({
                "entity_type": "agent",
                "entity_id": bucket.get("agent_user_id") or "bot",
                "focus": "quality_and_closing",
                "recommendation": "Reforzar cierre con CTA, velocidad de respuesta y manejo de objeciones.",
            })
    for bucket in by_bot.values():
        reviews_count = max(1, int(bucket.get("reviews") or 0))
        bucket["avg_quality"] = round(float(bucket.get("avg_quality") or 0) / reviews_count, 2)
    return {
        "organization_id": organization_id,
        "bot_id": bot_id,
        "by_agent": sorted(by_agent.values(), key=lambda item: (-float(item.get("avg_quality") or 0), str(item.get("agent_user_id") or ""))),
        "by_bot": sorted(by_bot.values(), key=lambda item: (-float(item.get("avg_quality") or 0), str(item.get("bot_id") or ""))),
        "coaching_loops": coaching,
    }


def build_supervisor_console(conn, organization_id: str) -> dict[str, Any]:
    rows = fetch_all(
        conn,
        """
        SELECT c.*, ct.name AS contact_name, ct.phone AS contact_phone, b.name AS bot_name,
               cm.lead_stage, cm.lead_score, cm.summary, cm.memory_json, cm.next_action, cm.followup_at,
               cm.current_intent, cm.urgency_score AS memory_urgency_score, cm.urgency_level AS memory_urgency_level,
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
        WHERE c.organization_id = ?
        ORDER BY COALESCE(c.last_message_at, c.updated_at) DESC
        LIMIT 500
        """,
        (organization_id,),
    )
    items = [_decorate_item(row) for row in rows]
    teams: dict[str, dict[str, Any]] = {}
    failed_takeovers: list[dict[str, Any]] = []
    for item in items:
        team_key = str(item.get("work_queue_role") or "soporte")
        team = teams.setdefault(team_key, {
            "team_key": team_key,
            "open_conversations": 0,
            "active_takeovers": 0,
            "sla_breached": 0,
            "unassigned": 0,
            "priority_peak": 0,
            "response_latency_minutes": 0.0,
            "capacity_baseline": _TEAM_CAPACITY_BASELINES.get(team_key, 12),
        })
        team["open_conversations"] += 1
        team["active_takeovers"] += 1 if item.get("human_takeover") else 0
        team["sla_breached"] += 1 if item.get("sla_status") == "breached" else 0
        team["unassigned"] += 1 if not item.get("assigned_user_id") else 0
        team["priority_peak"] = max(int(team.get("priority_peak") or 0), int(item.get("priority_score") or 0))
        team["response_latency_minutes"] += max(0, int(item.get("sla_overdue_minutes") or 0) + int(item.get("sla_target_minutes") or 0))
        takeover_risk = detect_failed_takeover(conn, item["id"])
        if takeover_risk.get("failed_takeover"):
            failed_takeovers.append({
                "conversation_id": item["id"],
                "team_key": team_key,
                "contact_name": item.get("contact_name"),
                "risk_score": takeover_risk.get("risk_score"),
                "reasons": takeover_risk.get("reasons"),
            })
    teams_payload = []
    for team in teams.values():
        open_count = max(1, int(team.get("open_conversations") or 0))
        team["response_latency_minutes"] = round(float(team.get("response_latency_minutes") or 0) / open_count, 2)
        team["occupancy_pct"] = round(min(200.0, (open_count / max(1, int(team.get("capacity_baseline") or 1))) * 100), 2)
        team["workload_score"] = min(100, int(team["occupancy_pct"] / 2) + int(team.get("sla_breached") or 0) * 8 + int(team.get("active_takeovers") or 0) * 5)
        teams_payload.append(team)
    reviews = qa_scorecard(conn, organization_id)
    total_open = len(items)
    summary = {
        "organization_id": organization_id,
        "total_open": total_open,
        "unassigned_open": sum(1 for item in items if not item.get("assigned_user_id")),
        "active_takeovers": sum(1 for item in items if item.get("human_takeover")),
        "failed_takeovers": len(failed_takeovers),
        "avg_priority_score": round(sum(int(item.get("priority_score") or 0) for item in items) / max(1, total_open), 2),
        "avg_response_latency_minutes": round(sum(int(item.get("sla_target_minutes") or 0) + int(item.get("sla_overdue_minutes") or 0) for item in items) / max(1, total_open), 2),
    }
    return {
        "summary": summary,
        "teams": sorted(teams_payload, key=lambda item: (-float(item.get("workload_score") or 0), item.get("team_key") or "")),
        "failed_takeovers": sorted(failed_takeovers, key=lambda item: (-int(item.get("risk_score") or 0), item.get("conversation_id") or ""))[:20],
        "qa": reviews,
        "supervisor_actions": [
            "Revisar takeovers fallidos primero.",
            "Balancear ownership en equipos con occupancy alta.",
            "Aplicar coaching a agentes con QA < 85.",
        ],
    }
