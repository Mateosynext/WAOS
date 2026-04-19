from __future__ import annotations

from fastapi import HTTPException

from ..config import settings
from ..contact_intelligence import enrich_conversation_row
from ..human_ops_runtime import build_human_reply_suggestion, build_supervisor_console, build_takeover_brief, detect_failed_takeover, qa_scorecard, recommend_ai_reactivation, save_structured_internal_note
from ..contracts import ok
from ..db import fetch_all, fetch_one, table_exists
from ..performance import clamp_limit, clamp_offset
from ..repositories import create_audit_log, create_message, get_bot, get_contact_memory, get_conversation
from ..security import ensure_bot_access, ensure_org_access
from ..serializers import serialize_conversation_details
from ..utils import add_minutes, from_json, new_id, parse_iso, to_json, utcnow_iso
from ..whatsapp import enqueue_manual_whatsapp_message
from .support import org_filter_sql, require_permission
from .uow import UnitOfWork


class ConversationService:
    def _base_list_rows(self, conn, *, user: dict, organization_id: str | None, bot_id: str | None, status: str | None, sort: str | None, limit: int, offset: int) -> list[dict]:
        where_sql, params = org_filter_sql(user, organization_id, "c.organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if organization_id:
            require_permission(user, organization_id, "conversation.manage")
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
            where_sql += " AND c.bot_id = ? "
            params.append(bot_id)
        if status:
            where_sql += " AND c.status = ? "
            params.append(status)
        order_by = "COALESCE(c.last_message_at, c.updated_at) DESC"
        if str(sort or "").lower() == "priority":
            order_by = "COALESCE(cm.urgency_score, 0) DESC, COALESCE(cm.lead_score, 0) DESC, COALESCE(c.last_message_at, c.updated_at) DESC"
        elif str(sort or "").lower() == "lead":
            order_by = "COALESCE(cm.lead_score, 0) DESC, COALESCE(c.last_message_at, c.updated_at) DESC"
        elif str(sort or "").lower() == "urgency":
            order_by = "COALESCE(cm.urgency_score, 0) DESC, COALESCE(c.last_message_at, c.updated_at) DESC"
        return fetch_all(
            conn,
            f"""
            SELECT c.*, ct.name as contact_name, ct.phone as contact_phone, b.name as bot_name,
                   cm.lead_stage, cm.lead_score, cm.summary, cm.memory_json, cm.next_action, cm.followup_at,
                   cm.current_intent, cm.urgency_score AS memory_urgency_score, cm.urgency_level AS memory_urgency_level,
                   (SELECT body FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) AS latest_message_preview,
                   (SELECT MAX(created_at) FROM messages WHERE conversation_id = c.id AND direction = 'inbound') AS last_inbound_at,
                   (SELECT MAX(created_at) FROM messages WHERE conversation_id = c.id AND direction = 'outbound') AS last_outbound_at,
                   (SELECT COUNT(*) FROM appointments a WHERE a.conversation_id = c.id AND a.status NOT IN ('cancelled','no_show')) AS appointment_count,
                   (SELECT COUNT(*) FROM commerce_payments p WHERE p.conversation_id = c.id AND p.status IN ('pending','pending_provider','requires_action')) AS pending_payment_count,
                   (SELECT COALESCE(MAX(close_probability), 0) FROM crm_leads l WHERE l.conversation_id = c.id) AS close_probability,
                   (SELECT COALESCE(MAX(score_buying_intent), 0) FROM crm_leads l WHERE l.conversation_id = c.id) AS score_buying_intent,
                   (SELECT best_next_action FROM crm_leads l WHERE l.conversation_id = c.id ORDER BY updated_at DESC LIMIT 1) AS lead_best_next_action
            FROM conversations c
            JOIN contacts ct ON ct.id = c.contact_id
            JOIN bots b ON b.id = c.bot_id
            LEFT JOIN contact_memory cm ON cm.contact_id = c.contact_id AND cm.bot_id = c.bot_id
            {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """,
            params + [clamp_limit(limit), clamp_offset(offset)],
        )

    def _queue_role_for_item(self, item: dict) -> tuple[str, str]:
        intent = str(item.get("current_intent") or "").lower()
        if int(item.get("pending_payment_count") or 0) > 0 or intent in {"payment", "invoice", "cobranza", "charge"}:
            return "cobranza", "Tiene pago pendiente o intento de cobro activo"
        if int(item.get("appointment_count") or 0) > 0 or intent in {"schedule", "appointment", "reschedule", "booking"}:
            return "agenda", "Tiene cita o intención clara de agenda"
        if int(item.get("lead_score") or 0) >= 60 or int(item.get("close_probability") or 0) >= 60 or str(item.get("lead_stage") or "").lower() in {"hot", "qualified", "propuesta", "cotizacion", "nuevo"}:
            return "ventas", "Lead activo con oportunidad comercial"
        return "soporte", "Necesita seguimiento operativo o soporte humano"

    def _sla_for_item(self, item: dict) -> dict:
        role_key, _ = self._queue_role_for_item(item)
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
        due_at = add_minutes(item.get("last_inbound_at") or item.get("updated_at") or utcnow_iso(), target_minutes)
        return {
            "role_key": role_key,
            "target_minutes": target_minutes,
            "due_at": due_at,
            "status": status,
            "overdue_minutes": overdue_minutes,
        }

    def _decorate_item(self, item: dict) -> dict:
        item = enrich_conversation_row(item)
        priority_score = min(100, int(item.get("urgency_score") or 0) + int(item.get("lead_score") or 0) + min(20, int(item.get("close_probability") or 0) // 5))
        item["priority_score"] = priority_score
        item["priority_band"] = "critical" if priority_score >= 90 else "high" if priority_score >= 70 else "medium" if priority_score >= 40 else "normal"
        item["next_best_action"] = item.get("lead_best_next_action") or item.get("next_action") or ("Responder con humano" if str(item.get("status") or "").lower() == "human_takeover" else "Enviar siguiente paso" if int(item.get("lead_score") or 0) >= 70 else "Dar seguimiento")
        item["requires_human"] = bool(str(item.get("status") or "").lower() == "human_takeover" or str(item.get("attention_tier") or "").lower() == "owner_now")
        item["attention_class"] = "requires_human" if item["requires_human"] else "follow_up_only" if item.get("followup_at") else "ai_or_operator"
        item["stalled"] = bool(item.get("followup_at") and (item.get("last_outbound_at") or item.get("updated_at")) and str(item.get("status") or "").lower() not in {"closed", "resolved"})
        queue_role, queue_reason = self._queue_role_for_item(item)
        item["work_queue_role"] = queue_role
        item["work_queue_reason"] = queue_reason
        sla = self._sla_for_item(item)
        item["sla_status"] = sla["status"]
        item["sla_due_at"] = sla["due_at"]
        item["sla_target_minutes"] = sla["target_minutes"]
        item["sla_overdue_minutes"] = sla["overdue_minutes"]
        return item

    def list(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None, status: str | None, sort: str | None, limit: int, offset: int) -> list[dict]:
        rows = self._base_list_rows(uow.conn, user=user, organization_id=organization_id, bot_id=bot_id, status=status, sort=sort, limit=limit, offset=offset)
        return [self._decorate_item(row) for row in rows]

    def get(self, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        return serialize_conversation_details(conn, conversation)

    def decision_support(self, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
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
        item = self._decorate_item(row)
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

    def list_work_queues(self, uow: UnitOfWork, *, user: dict, organization_id: str) -> dict:
        conn = uow.conn
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "conversation.manage")
        rows = self._base_list_rows(conn, user=user, organization_id=organization_id, bot_id=None, status=None, sort="priority", limit=500, offset=0)
        buckets: dict[str, dict] = {}
        for row in rows:
            item = self._decorate_item(row)
            bucket = buckets.setdefault(item["work_queue_role"], {"role_key": item["work_queue_role"], "count": 0, "requires_human": 0, "stalled": 0, "sla_breached": 0, "top_priority": 0})
            bucket["count"] += 1
            bucket["requires_human"] += 1 if item.get("requires_human") else 0
            bucket["stalled"] += 1 if item.get("stalled") else 0
            bucket["sla_breached"] += 1 if item.get("sla_status") == "breached" else 0
            bucket["top_priority"] = max(bucket["top_priority"], int(item.get("priority_score") or 0))
        return ok({
            "organization_id": organization_id,
            "queues": sorted(buckets.values(), key=lambda item: (-int(item.get("sla_breached") or 0), -int(item.get("count") or 0), item.get("role_key") or "")),
        })

    def _org_assignment_candidates(self, conn, organization_id: str, queue_role: str) -> list[dict]:
        rows = fetch_all(
            conn,
            """
            SELECT om.user_id, om.role, u.full_name, u.email,
                   (
                     SELECT COUNT(*) FROM conversations c
                     WHERE c.organization_id = om.organization_id
                       AND c.assigned_user_id = om.user_id
                       AND c.status NOT IN ('closed','resolved')
                   ) AS open_conversations
            FROM organization_members om
            JOIN users u ON u.id = om.user_id
            WHERE om.organization_id = ? AND om.is_active = 1 AND u.is_active = 1
            ORDER BY open_conversations ASC, om.created_at ASC
            """,
            (organization_id,),
        )
        preferred_roles = {
            'ventas': {'org_admin', 'operator'},
            'agenda': {'org_admin', 'operator'},
            'cobranza': {'org_admin'},
            'soporte': {'org_admin', 'operator'},
        }.get(queue_role, {'org_admin', 'operator'})
        filtered = [row for row in rows if str(row.get('role') or '').lower() in preferred_roles]
        return filtered or rows

    def _record_assignment(self, conn, *, conversation: dict, previous_user_id: str | None, new_user_id: str | None, queue_role: str | None, mode: str, note: str, actor_user_id: str) -> None:
        if not table_exists(conn, 'conversation_assignment_history'):
            return
        conn.execute(
            """
            INSERT INTO conversation_assignment_history (id, organization_id, conversation_id, previous_assigned_user_id, new_assigned_user_id, queue_role, assignment_mode, reasoning_json, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id('casg'),
                conversation['organization_id'],
                conversation['id'],
                previous_user_id,
                new_user_id,
                queue_role,
                mode,
                to_json({'note': note}),
                actor_user_id,
                utcnow_iso(),
            ),
        )

    def assign(self, uow: UnitOfWork, *, user: dict, conversation_id: str, payload) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation['organization_id'], 'conversation.manage')
        previous_user_id = conversation.get('assigned_user_id')
        target_user_id = payload.assigned_user_id
        queue_role = self._decorate_item(fetch_one(
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
                   (SELECT COALESCE(MAX(score_buying_intent), 0) FROM crm_leads l WHERE l.conversation_id = c.id) AS score_buying_intent,
                   (SELECT best_next_action FROM crm_leads l WHERE l.conversation_id = c.id ORDER BY updated_at DESC LIMIT 1) AS lead_best_next_action
            FROM conversations c
            JOIN contacts ct ON ct.id = c.contact_id
            JOIN bots b ON b.id = c.bot_id
            LEFT JOIN contact_memory cm ON cm.contact_id = c.contact_id AND cm.bot_id = c.bot_id
            WHERE c.id = ?
            LIMIT 1
            """,
            (conversation_id,),
        ) or {})['work_queue_role']
        if payload.mode == 'auto' and not target_user_id:
            candidates = self._org_assignment_candidates(conn, conversation['organization_id'], queue_role)
            target_user_id = (candidates[0] or {}).get('user_id') if candidates else None
        if target_user_id:
            membership = fetch_one(conn, 'SELECT * FROM organization_members WHERE organization_id = ? AND user_id = ? AND is_active = 1', (conversation['organization_id'], target_user_id))
            if not membership:
                raise HTTPException(status_code=404, detail='Assignee not found in organization')
        now = utcnow_iso()
        conn.execute(
            "UPDATE conversations SET assigned_user_id = ?, status = CASE WHEN ? IS NOT NULL THEN 'human_takeover' ELSE status END, human_takeover = CASE WHEN ? IS NOT NULL THEN 1 ELSE human_takeover END, updated_at = ? WHERE id = ?",
            (target_user_id, target_user_id, target_user_id, now, conversation_id),
        )
        self._record_assignment(conn, conversation=conversation, previous_user_id=previous_user_id, new_user_id=target_user_id, queue_role=queue_role, mode=payload.mode, note=payload.note, actor_user_id=user['id'])
        create_audit_log(conn, organization_id=conversation['organization_id'], actor_user_id=user['id'], actor_type='user', entity_type='conversation', entity_id=conversation_id, action='conversation.assigned', metadata={'assigned_user_id': target_user_id, 'previous_assigned_user_id': previous_user_id, 'queue_role': queue_role, 'mode': payload.mode, 'note': payload.note})
        return get_conversation(conn, conversation_id)

    def auto_assign(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        conn = uow.conn
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, 'conversation.manage')
        rows = self._base_list_rows(conn, user=user, organization_id=payload.organization_id, bot_id=None, status=None, sort='priority', limit=payload.limit, offset=0)
        assigned = []
        for row in rows:
            item = self._decorate_item(row)
            if item.get('assigned_user_id'):
                continue
            if payload.queue_role and str(item.get('work_queue_role') or '') != str(payload.queue_role):
                continue
            candidates = self._org_assignment_candidates(conn, payload.organization_id, item['work_queue_role'])
            if not candidates:
                continue
            target_user_id = candidates[0].get('user_id')
            conn.execute(
                "UPDATE conversations SET assigned_user_id = ?, status = 'human_takeover', human_takeover = 1, updated_at = ? WHERE id = ?",
                (target_user_id, utcnow_iso(), item['id']),
            )
            self._record_assignment(conn, conversation=item, previous_user_id=item.get('assigned_user_id'), new_user_id=target_user_id, queue_role=item.get('work_queue_role'), mode='auto', note='bulk auto assignment', actor_user_id=user['id'])
            assigned.append({'conversation_id': item['id'], 'assigned_user_id': target_user_id, 'queue_role': item.get('work_queue_role'), 'priority_score': item.get('priority_score')})
        create_audit_log(conn, organization_id=payload.organization_id, actor_user_id=user['id'], actor_type='user', entity_type='inbox', entity_id=payload.organization_id, action='inbox.auto_assign', metadata={'assigned_count': len(assigned), 'queue_role': payload.queue_role, 'limit': payload.limit})
        return ok({'organization_id': payload.organization_id, 'assigned_count': len(assigned), 'assignments': assigned})

    def ownership_summary(self, uow: UnitOfWork, *, user: dict, organization_id: str) -> dict:
        conn = uow.conn
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, 'conversation.manage')
        members = fetch_all(
            conn,
            """
            SELECT om.user_id, om.role, u.full_name,
                   (
                     SELECT COUNT(*) FROM conversations c
                     WHERE c.organization_id = om.organization_id
                       AND c.assigned_user_id = om.user_id
                       AND c.status NOT IN ('closed','resolved')
                   ) AS open_count,
                   (
                     SELECT COUNT(*) FROM conversations c
                     WHERE c.organization_id = om.organization_id
                       AND c.assigned_user_id = om.user_id
                       AND c.status = 'human_takeover'
                   ) AS human_takeover_count
            FROM organization_members om
            JOIN users u ON u.id = om.user_id
            WHERE om.organization_id = ? AND om.is_active = 1
            ORDER BY open_count DESC, u.full_name ASC
            """,
            (organization_id,),
        )
        unassigned = fetch_one(conn, "SELECT COUNT(*) AS value FROM conversations WHERE organization_id = ? AND assigned_user_id IS NULL AND status NOT IN ('closed','resolved')", (organization_id,))
        return ok({'organization_id': organization_id, 'unassigned_open': int((unassigned or {}).get('value') or 0), 'owners': members})

    def add_message_or_note(self, uow: UnitOfWork, *, user: dict, conversation_id: str, payload) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        if payload.kind == "note":
            message = create_message(
                conn,
                organization_id=conversation["organization_id"],
                conversation_id=conversation_id,
                contact_id=conversation["contact_id"],
                bot_id=conversation["bot_id"],
                direction="internal",
                kind="note",
                source="human",
                body=payload.body,
                status="internal",
                metadata={"author_user_id": user["id"]},
            )
            create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.note_added", metadata={})
            return {"message": message}
        try:
            queued = enqueue_manual_whatsapp_message(
                conn,
                organization_id=conversation["organization_id"],
                bot_id=conversation["bot_id"],
                conversation_id=conversation_id,
                contact_id=conversation["contact_id"],
                body=payload.body,
                author_user_id=user["id"],
                whatsapp_payload=payload.whatsapp_payload,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        now = utcnow_iso()
        conn.execute(
            """
            UPDATE conversations
            SET status = 'human_takeover', human_takeover = 1, ai_active = 0, assigned_user_id = ?, last_human_at = ?, automation_freeze_until = ?, updated_at = ?
            WHERE id = ?
            """,
            (user["id"], now, add_minutes(now, 30), now, conversation_id),
        )
        latest_inbound = fetch_one(conn, "SELECT body, created_at FROM messages WHERE conversation_id = ? AND direction = 'inbound' ORDER BY created_at DESC LIMIT 1", (conversation_id,))
        conn.execute(
            """
            INSERT INTO operator_training_examples (id, organization_id, bot_id, conversation_id, contact_id, operator_user_id, input_text, output_text, example_type, status, context_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'manual_takeover', 'captured', ?, ?)
            """,
            (
                new_id("otrain"),
                conversation["organization_id"],
                conversation["bot_id"],
                conversation_id,
                conversation["contact_id"],
                user["id"],
                latest_inbound.get("body") if latest_inbound else None,
                (queued.get("message") or {}).get("body") or payload.body or "",
                to_json({"latest_inbound_at": latest_inbound.get("created_at") if latest_inbound else None}),
                utcnow_iso(),
            ),
        )
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.manual_message_queued", metadata={"outbox_id": queued["outbox_id"], "training_example_captured": True})
        return {"message": queued["message"], "outbox_id": queued["outbox_id"], "conversation": get_conversation(conn, conversation_id)}

    def takeover(self, uow: UnitOfWork, *, user: dict, conversation_id: str, freeze_minutes: int) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        conn.execute(
            """
            UPDATE conversations
            SET status = 'human_takeover', human_takeover = 1, ai_active = 0, assigned_user_id = ?, automation_freeze_until = ?, updated_at = ?
            WHERE id = ?
            """,
            (user["id"], add_minutes(utcnow_iso(), freeze_minutes), utcnow_iso(), conversation_id),
        )
        build_takeover_brief(conn, conversation_id, brief_type="takeover", generated_by_user_id=user.get("id"), persist=True)
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.takeover", metadata={"freeze_minutes": freeze_minutes})
        return get_conversation(conn, conversation_id)

    def reactivate_ai(self, uow: UnitOfWork, *, user: dict, conversation_id: str) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        guardrails = recommend_ai_reactivation(conn, conversation_id)
        if not guardrails.get("allowed"):
            return ok({"conversation": get_conversation(conn, conversation_id), "reactivation": guardrails})
        conn.execute(
            """
            UPDATE conversations
            SET status = 'ai_active', human_takeover = 0, ai_active = 1, assigned_user_id = NULL, automation_freeze_until = NULL, updated_at = ?
            WHERE id = ?
            """,
            (utcnow_iso(), conversation_id),
        )
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.ai_reactivated", metadata={"guardrails": guardrails})
        return ok({"conversation": get_conversation(conn, conversation_id), "reactivation": guardrails})

    def add_structured_internal_note(self, uow: UnitOfWork, *, user: dict, conversation_id: str, payload) -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        note = save_structured_internal_note(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=conversation["bot_id"],
            conversation_id=conversation_id,
            contact_id=conversation["contact_id"],
            author_user_id=user["id"],
            category=payload.category,
            priority=payload.priority,
            summary=payload.summary,
            detail=payload.detail,
            next_steps=payload.next_steps,
            sources=payload.sources,
            risk_level=payload.risk_level,
            risk_flags=payload.risk_flags,
            visibility=payload.visibility,
        )
        return ok(note)

    def takeover_brief(self, uow: UnitOfWork, *, user: dict, conversation_id: str, brief_type: str = "takeover") -> dict:
        conn = uow.conn
        conversation = self._get_accessible_conversation(conn, user, conversation_id)
        require_permission(user, conversation["organization_id"], "conversation.manage")
        return ok(build_takeover_brief(conn, conversation_id, brief_type=brief_type, generated_by_user_id=user.get("id"), persist=True))

    def supervisor_console(self, uow: UnitOfWork, *, user: dict, organization_id: str) -> dict:
        conn = uow.conn
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "conversation.manage")
        payload = build_supervisor_console(conn, organization_id)
        if table_exists(conn, "supervisor_console_snapshots"):
            conn.execute(
                "INSERT INTO supervisor_console_snapshots (id, organization_id, summary_json, teams_json, qa_json, failed_takeovers_json, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id("supc"), organization_id, to_json(payload["summary"]), to_json(payload["teams"]), to_json(payload["qa"]), to_json(payload["failed_takeovers"]), user.get("id"), utcnow_iso()),
            )
        create_audit_log(conn, organization_id=organization_id, actor_user_id=user["id"], actor_type="user", entity_type="supervisor_console", entity_id=organization_id, action="supervisor.console_viewed", metadata={"teams": len(payload.get("teams") or [])})
        return ok(payload)

    def qa_overview(self, uow: UnitOfWork, *, user: dict, organization_id: str, bot_id: str | None = None) -> dict:
        conn = uow.conn
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "conversation.manage")
        return ok(qa_scorecard(conn, organization_id, bot_id=bot_id))

    def list_leads(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> list[dict]:
        conn = uow.conn
        if organization_id:
            require_permission(user, organization_id, "crm.manage")
        where_sql, params = org_filter_sql(user, organization_id, "cm.organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if organization_id:
            require_permission(user, organization_id, "conversation.manage")
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
            where_sql += " AND cm.bot_id = ? "
            params.append(bot_id)
        return fetch_all(
            conn,
            f"""
            SELECT cm.*, ct.name as contact_name, ct.phone as contact_phone, b.name as bot_name
            FROM contact_memory cm
            JOIN contacts ct ON ct.id = cm.contact_id
            JOIN bots b ON b.id = cm.bot_id
            {where_sql}
            ORDER BY cm.lead_score DESC, cm.last_updated_at DESC
            """,
            params,
        )

    def update_lead_memory(self, uow: UnitOfWork, *, user: dict, contact_id: str, bot_id: str, payload) -> dict:
        conn = uow.conn
        memory = get_contact_memory(conn, contact_id, bot_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        ensure_org_access(user, memory["organization_id"])
        require_permission(user, memory["organization_id"], "crm.manage")
        updated = {
            "lead_stage": payload.lead_stage if payload.lead_stage is not None else memory["lead_stage"],
            "lead_score": payload.lead_score if payload.lead_score is not None else memory["lead_score"],
            "interest": payload.interest if payload.interest is not None else memory["interest"],
            "objections": payload.objections if payload.objections is not None else memory["objections"],
            "summary": payload.summary if payload.summary is not None else memory["summary"],
            "next_action": payload.next_action if payload.next_action is not None else memory["next_action"],
            "followup_at": payload.followup_at if payload.followup_at is not None else memory["followup_at"],
        }
        conn.execute(
            """
            UPDATE contact_memory
            SET lead_stage = ?, lead_score = ?, interest = ?, objections = ?, summary = ?, next_action = ?, followup_at = ?, last_updated_at = ?
            WHERE contact_id = ? AND bot_id = ?
            """,
            (
                updated["lead_stage"],
                updated["lead_score"],
                updated["interest"],
                updated["objections"],
                updated["summary"],
                updated["next_action"],
                updated["followup_at"],
                utcnow_iso(),
                contact_id,
                bot_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO contact_memory_history (id, organization_id, contact_memory_id, contact_id, bot_id, changed_by, before_json, after_json, changed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("memh"),
                memory["organization_id"],
                memory["id"],
                contact_id,
                bot_id,
                user["id"],
                to_json({
                    "lead_stage": memory.get("lead_stage"),
                    "lead_score": memory.get("lead_score"),
                    "interest": memory.get("interest"),
                    "objections": memory.get("objections"),
                    "summary": memory.get("summary"),
                    "next_action": memory.get("next_action"),
                    "followup_at": memory.get("followup_at"),
                }),
                to_json(updated),
                utcnow_iso(),
            ),
        )
        create_audit_log(conn, organization_id=memory["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="contact_memory", entity_id=memory["id"], action="lead.memory_updated", metadata=updated)
        return get_contact_memory(conn, contact_id, bot_id)

    def _get_accessible_conversation(self, conn, user: dict, conversation_id: str) -> dict:
        conversation = get_conversation(conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        return conversation
