from __future__ import annotations

from .common import *
from .common import _require_permission
from ...human_ops_runtime import build_human_reply_suggestion

def review_conversation_route(conversation_id: str, payload: ConversationReviewRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "insights.read")
    with get_connection() as conn:
        return review_conversation(conn, conversation_id=conversation_id, **payload.model_dump())

def list_conversation_reviews(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        rows = fetch_all(conn, f"SELECT * FROM conversation_reviews {where_sql} ORDER BY created_at DESC LIMIT 200", params)
        return [{**row, "missed_opportunities": from_json(row.get("missed_opportunities_json"), []), "checklist": from_json(row.get("checklist_json"), []), "recommendations": from_json(row.get("recommendations_json"), [])} for row in rows]

def conversation_summary_on_demand(conversation_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        conversation = get_conversation(conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        summary = _build_conversation_summary(conn, conversation)
        execute(
            conn,
            """
            INSERT INTO conversation_summaries (id, organization_id, bot_id, conversation_id, contact_id, summary_type, content_json, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, 'on_demand', ?, ?, ?)
            """,
            (new_id("csum"), conversation["organization_id"], conversation["bot_id"], conversation_id, conversation["contact_id"], to_json(summary), user["id"], utcnow_iso()),
        )
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.summary_generated", metadata={"mode": "on_demand"})
        return summary

def conversation_copilot(conversation_id: str, payload: ConversationCopilotRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        conversation = get_conversation(conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        _require_permission(user, conversation["organization_id"], "conversation.manage")
        suggestion = build_human_reply_suggestion(conn, conversation_id, draft=payload.draft, objective=payload.objective, operator_user_id=user.get("id"), persist=True)
        execute(
            conn,
            """
            INSERT INTO operator_copilot_suggestions (id, organization_id, bot_id, conversation_id, contact_id, operator_user_id, draft_text, suggestion_text, tone, status, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'suggested', ?, ?)
            """,
            (
                new_id("cops"),
                conversation["organization_id"],
                conversation["bot_id"],
                conversation_id,
                conversation["contact_id"],
                user["id"],
                payload.draft,
                suggestion["suggestion"],
                None,
                to_json({"objective": payload.objective, "risk": suggestion.get("risk"), "sources": suggestion.get("sources"), "explanation": suggestion.get("explanation")}),
                utcnow_iso(),
            ),
        )
        return suggestion

def inbox_search(
    query: str,
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    limit: int = Query(default=settings.default_page_size),
    offset: int = Query(default=0),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "c.organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
            where_sql += " AND c.bot_id = ? "
            params.append(bot_id)
        pattern = f"%{query.lower()}%"
        params.extend([pattern, pattern, pattern, pattern, clamp_limit(limit), clamp_offset(offset)])
        rows = fetch_all(
            conn,
            f"""
            SELECT c.*, ct.name AS contact_name, ct.phone AS contact_phone, b.name AS bot_name, cm.lead_stage, cm.lead_score, cm.summary,
                   MAX(CASE WHEN LOWER(COALESCE(m.body, '')) LIKE ? THEN m.body ELSE NULL END) AS matched_message
            FROM conversations c
            JOIN contacts ct ON ct.id = c.contact_id
            JOIN bots b ON b.id = c.bot_id
            LEFT JOIN contact_memory cm ON cm.contact_id = c.contact_id AND cm.bot_id = c.bot_id
            LEFT JOIN messages m ON m.conversation_id = c.id
            {where_sql}
              AND (
                LOWER(COALESCE(ct.name, '')) LIKE ?
                OR LOWER(COALESCE(ct.phone, '')) LIKE ?
                OR LOWER(COALESCE(cm.summary, '')) LIKE ?
                OR LOWER(COALESCE(m.body, '')) LIKE ?
              )
            GROUP BY c.id, ct.name, ct.phone, b.name, cm.lead_stage, cm.lead_score, cm.summary
            ORDER BY COALESCE(c.last_message_at, c.updated_at) DESC
            LIMIT ? OFFSET ?
            """,
            params,
        )
        return rows

def inbox_risk(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    threshold_hours: int = Query(default=4),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        conversations = fetch_all(conn, f"SELECT * FROM conversations {where_sql} ORDER BY COALESCE(last_message_at, updated_at) DESC LIMIT 300", params)
        enriched = []
        for conversation in conversations:
            snapshot = _conversation_risk_snapshot(conn, conversation, threshold_hours=threshold_hours)
            if snapshot["at_risk"]:
                payload = _conversation_payload(conn, conversation)
                enriched.append({
                    **snapshot,
                    "contact": payload.get("contact"),
                    "bot": payload.get("bot"),
                    "conversation": conversation,
                    "tags": payload.get("tags", []),
                })
        return sorted(enriched, key=lambda item: item["risk_score"], reverse=True)

def list_conversation_tags(conversation_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        conversation = get_conversation(conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        rows = fetch_all(conn, "SELECT tag, created_at, created_by FROM conversation_tags WHERE conversation_id = ? ORDER BY tag ASC", (conversation_id,))
        return {"conversation_id": conversation_id, "tags": rows}

def upsert_conversation_tags(conversation_id: str, payload: ConversationTagRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        conversation = get_conversation(conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        _require_permission(user, conversation["organization_id"], "conversation.manage")
        execute(conn, "DELETE FROM conversation_tags WHERE conversation_id = ?", (conversation_id,))
        now = utcnow_iso()
        for tag in sorted({tag.strip().lower() for tag in payload.tags if tag.strip()}):
            execute(conn, "INSERT INTO conversation_tags (id, organization_id, conversation_id, tag, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)", (new_id("ctag"), conversation["organization_id"], conversation_id, tag, user["id"], now))
        create_audit_log(conn, organization_id=conversation["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="conversation", entity_id=conversation_id, action="conversation.tags_updated", metadata={"tags": payload.tags})
        return {"conversation_id": conversation_id, "tags": sorted({tag.strip().lower() for tag in payload.tags if tag.strip()})}

def memory_history(contact_id: str, bot_id: str = Query(...), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        memory = get_contact_memory(conn, contact_id, bot_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        ensure_org_access(user, memory["organization_id"])
        rows = fetch_all(conn, "SELECT * FROM contact_memory_history WHERE contact_memory_id = ? ORDER BY changed_at DESC", (memory["id"],))
        return [{**row, "before": from_json(row.get("before_json"), {}), "after": from_json(row.get("after_json"), {})} for row in rows]

def alerts_rules_list(organization_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        rows = fetch_all(conn, f"SELECT * FROM alert_rules_v14 {where_sql} ORDER BY updated_at DESC", params)
        return [{**row, "notify_channels": from_json(row.get("notify_channels_json"), []), "config": from_json(row.get("config_json"), {})} for row in rows]

def alerts_rules_create(payload: AlertRuleRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "insights.read")
    with get_connection() as conn:
        row_id = new_id("alrt")
        now = utcnow_iso()
        execute(conn, "INSERT INTO alert_rules_v14 (id, organization_id, bot_id, name, metric_key, comparator, threshold_value, window_minutes, notify_channels_json, status, config_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row_id, payload.organization_id, payload.bot_id, payload.name, payload.metric_key, payload.comparator, payload.threshold_value, payload.window_minutes, to_json(payload.notify_channels), payload.status, to_json(payload.config), user["id"], now, now))
        return fetch_one(conn, "SELECT * FROM alert_rules_v14 WHERE id = ?", (row_id,))

def routing_rules_list(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND (bot_id = ? OR bot_id IS NULL) "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT * FROM routing_rules {where_sql} ORDER BY priority DESC, updated_at DESC", params)
        return [{**row, "conditions": from_json(row.get("conditions_json"), {})} for row in rows]

def routing_rules_create(payload: RoutingRuleRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    with get_connection() as conn:
        row_id = new_id("rrt")
        now = utcnow_iso()
        execute(conn, "INSERT INTO routing_rules (id, organization_id, bot_id, name, priority, conditions_json, assigned_user_id, assigned_team, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row_id, payload.organization_id, payload.bot_id, payload.name, payload.priority, to_json(payload.conditions), payload.assigned_user_id, payload.assigned_team, payload.status, user["id"], now, now))
        return fetch_one(conn, "SELECT * FROM routing_rules WHERE id = ?", (row_id,))

def followup_experiments_list(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT * FROM followup_experiments {where_sql} ORDER BY updated_at DESC", params)
        return [{**row, "results": from_json(row.get("results_json"), {})} for row in rows]

def followup_experiments_create(payload: FollowupExperimentRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    with get_connection() as conn:
        row_id = new_id("abx")
        now = utcnow_iso()
        execute(conn, "INSERT INTO followup_experiments (id, organization_id, bot_id, name, vertical, channel, variant_a_text, variant_b_text, goal_metric, status, results_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?, ?)", (row_id, payload.organization_id, payload.bot_id, payload.name, payload.vertical, payload.channel, payload.variant_a_text, payload.variant_b_text, payload.goal_metric, payload.status, user["id"], now, now))
        return fetch_one(conn, "SELECT * FROM followup_experiments WHERE id = ?", (row_id,))

def followup_experiments_send(experiment_id: str, payload: FollowupExperimentSendRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        experiment = fetch_one(conn, "SELECT * FROM followup_experiments WHERE id = ?", (experiment_id,))
        if not experiment:
            raise HTTPException(status_code=404, detail="followup_experiment_not_found")
        ensure_org_access(user, experiment["organization_id"])
        conversation = get_conversation(conn, payload.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="conversation_not_found")
        if conversation["organization_id"] != experiment["organization_id"]:
            raise HTTPException(status_code=403, detail="conversation_not_in_experiment_org")
        if experiment.get("status") not in {"active", "draft"}:
            raise HTTPException(status_code=400, detail="followup_experiment_not_sendable")
        variant = _select_followup_variant(conn, experiment=experiment, conversation_id=conversation["id"], preferred_variant=payload.preferred_variant)
        body = _variant_body(experiment, variant) or "Hola, solo retomando tu solicitud."
        message = create_message(
            conn,
            organization_id=conversation["organization_id"],
            conversation_id=conversation["id"],
            contact_id=conversation.get("contact_id"),
            bot_id=conversation["bot_id"],
            direction="outbound",
            kind="text",
            source="operator",
            body=body,
            status="queued",
            metadata={"followup_experiment_id": experiment_id, "variant": variant, "note": payload.note},
        )
        assignment_id = new_id("abas")
        metadata = {"note": payload.note, "operator_user_id": payload.operator_user_id or user.get("id")}
        execute(
            conn,
            """
            INSERT INTO followup_experiment_assignments
            (id, experiment_id, organization_id, bot_id, conversation_id, contact_id, message_id, variant, channel, status, assigned_at, replied_at, booked_at, won_at, last_event_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'sent', ?, NULL, NULL, NULL, ?, ?)
            """,
            (assignment_id, experiment_id, experiment["organization_id"], experiment["bot_id"], conversation["id"], conversation.get("contact_id"), message["id"], variant, experiment.get("channel") or "whatsapp", utcnow_iso(), utcnow_iso(), to_json(metadata)),
        )
        delivery_attempt = _record_delivery_attempt(
            conn,
            organization_id=conversation["organization_id"],
            bot_id=conversation["bot_id"],
            conversation_id=conversation["id"],
            entity_type="followup_experiment_assignment",
            entity_id=assignment_id,
            channel=experiment.get("channel") or "whatsapp",
            target="conversation",
            subject=experiment.get("name") or "Follow-up experiment",
            body=body,
            status="queued",
            provider="waos",
            metadata={"experiment_id": experiment_id, "variant": variant, "message_id": message["id"]},
            scheduled_at=utcnow_iso(),
        )
        if (experiment.get("channel") or "whatsapp") == "whatsapp":
            execute(
                conn,
                """
                INSERT INTO outbox_messages
                (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, status, scheduled_for, next_attempt_at, attempts, priority, locked_at, created_at)
                VALUES (?, ?, ?, NULL, ?, 'whatsapp', ?, 'queued', ?, ?, 0, 70, NULL, ?)
                """,
                (new_id("out"), conversation["organization_id"], conversation["bot_id"], conversation["id"], to_json({"body": body, "message_id": message["id"], "contact_id": conversation.get("contact_id"), "delivery_attempt_id": delivery_attempt["id"]}), utcnow_iso(), utcnow_iso(), utcnow_iso()),
            )
        updated = fetch_one(conn, "SELECT * FROM followup_experiment_assignments WHERE id = ?", (assignment_id,))
        return {"assignment": {**updated, "metadata": from_json(updated.get("metadata_json"), {})}, "message": message, "delivery_attempt": delivery_attempt}

def followup_experiment_performance(experiment_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        experiment = fetch_one(conn, "SELECT * FROM followup_experiments WHERE id = ?", (experiment_id,))
        if not experiment:
            raise HTTPException(status_code=404, detail="followup_experiment_not_found")
        ensure_org_access(user, experiment["organization_id"])
        return _followup_experiment_performance(conn, experiment_id)

def followup_experiment_assignments_list(organization_id: str | None = Query(default=None), experiment_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if experiment_id:
            where_sql += " AND experiment_id = ? "
            params.append(experiment_id)
        rows = fetch_all(conn, f"SELECT * FROM followup_experiment_assignments {where_sql} ORDER BY assigned_at DESC LIMIT 100", params)
        return [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in rows]

def routing_assignments_list(
    organization_id: str | None = Query(default=None),
    conversation_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if conversation_id:
            where_sql += " AND conversation_id = ? "
            params.append(conversation_id)
        rows = fetch_all(conn, f"SELECT * FROM routing_assignments {where_sql} ORDER BY created_at DESC LIMIT 100", params)
        return [{**row, "matched_conditions": from_json(row.get("matched_conditions_json"), {})} for row in rows]
