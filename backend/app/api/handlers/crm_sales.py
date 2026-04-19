from __future__ import annotations

from .common import *
from .common import _org_filter_sql, _require_permission
from ...contracts import ok, payment_row
from ...db import table_exists
from ...domains.whatsapp_flows import (
    create_flow_experiment,
    create_whatsapp_flow_version,
    execute_whatsapp_flow,
    publish_whatsapp_flow,
    record_whatsapp_flow_event,
    rollback_whatsapp_flow,
    runtime_step,
    serialize_flow,
    sync_whatsapp_flow,
    whatsapp_flow_analytics,
)
from ...domains.whatsapp_templates import (
    create_whatsapp_template,
    create_whatsapp_template_version,
    lint_whatsapp_template_definition,
    serialize_template,
    sync_whatsapp_template,
    sync_whatsapp_template_status,
    update_whatsapp_template_approval,
    whatsapp_template_analytics,
)

def list_crm_leads(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if organization_id:
            _require_permission(user, organization_id, "crm.manage")
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT * FROM crm_leads {where_sql} ORDER BY updated_at DESC LIMIT 200", params)
        return [
            {
                **row,
                "tags": from_json(row.get("tags_json"), []),
                "pipeline": from_json(row.get("pipeline_json"), {}),
                "detected_objections": from_json(row.get("detected_objections_json"), []),
            }
            for row in rows
        ]

def upsert_crm_lead_route(payload: CRMLeadUpsertRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "crm.manage")
    with get_connection() as conn:
        lead = _ensure_crm_lead(
            conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            contact_id=payload.contact_id,
            conversation_id=payload.conversation_id,
            defaults=payload.model_dump(exclude={"organization_id", "bot_id", "contact_id", "conversation_id"}),
        )
        previous_stage = lead.get("stage")
        execute(
            conn,
            """
            UPDATE crm_leads
            SET stage = ?, estimated_amount = ?, owner_user_id = ?, next_action = ?, followup_at = ?, tags_json = ?, notes = ?, lost_reason = ?, language = ?, source_channel = ?, source_campaign = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.stage,
                payload.estimated_amount,
                payload.owner_user_id,
                payload.next_action,
                payload.followup_at,
                to_json(payload.tags),
                payload.notes,
                payload.lost_reason,
                payload.language,
                payload.source_channel,
                payload.source_campaign,
                utcnow_iso(),
                lead["id"],
            ),
        )
        if previous_stage != payload.stage and table_exists(conn, "lead_stage_history"):
            execute(conn, "INSERT INTO lead_stage_history (id, organization_id, crm_lead_id, previous_stage, new_stage, reason, changed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (new_id("lstg"), payload.organization_id, lead["id"], previous_stage, payload.stage, payload.notes or payload.next_action or "manual_update", user["id"], utcnow_iso()))
        return fetch_one(conn, "SELECT * FROM crm_leads WHERE id = ?", (lead["id"],))

def list_payments(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if organization_id:
            _require_permission(user, organization_id, "revenue.manage")
        rows = fetch_all(conn, f"SELECT * FROM commerce_payments {where_sql} ORDER BY created_at DESC LIMIT 200", params)
        return [payment_row(row) for row in rows]

def create_payment_link_route(payload: PaymentRequestCreate, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "revenue.manage")
    with get_connection() as conn:
        values = payload.model_dump()
        metadata = dict(values.get("metadata") or {})
        if values.get("appointment_id"):
            metadata["appointment_id"] = values["appointment_id"]
        if values.get("provider"):
            metadata["provider"] = values["provider"]
        values["metadata"] = metadata
        values.pop("appointment_id", None)
        values.pop("provider", None)
        payment = create_payment_request(conn, actor_user=user, **values)
        return payment_row(payment)

def confirm_payment_route(payment_id: str, payload: PaymentConfirmRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        ensure_org_access(user, payment["organization_id"])
        _require_permission(user, payment["organization_id"], "revenue.manage")
        if payment.get("provider") == "stripe":
            from ...payments_runtime import refresh_payment_status
            updated = refresh_payment_status(conn, payment_id)
            if (updated or {}).get("status") != "paid":
                raise HTTPException(status_code=409, detail="Payment is not confirmed by provider webhook or reconciliation yet")
            return payment_row(updated)
        raise HTTPException(status_code=409, detail="Manual confirmation is disabled. Wait for provider webhook or reconciliation")

def get_seller_mode(conversation_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        conversation = get_conversation(conn, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        ensure_org_access(user, conversation["organization_id"])
        _require_permission(user, conversation["organization_id"], "crm.manage")
        return seller_mode_summary(conn, conversation_id)

def list_whatsapp_flows(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        rows = fetch_all(conn, f"SELECT * FROM whatsapp_flows {where_sql} ORDER BY updated_at DESC LIMIT 100", params)
        return [serialize_flow(conn, row, include_versions=True, include_publications=True) for row in rows]


def get_whatsapp_flow_route(flow_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        row = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not row:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, row["organization_id"])
        _require_permission(user, row["organization_id"], "bot.manage")
        return serialize_flow(conn, row, include_versions=True, include_publications=True)


def create_whatsapp_flow_route(payload: WhatsAppFlowCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return create_whatsapp_flow(conn, **payload.model_dump())


def create_whatsapp_flow_version_route(flow_id: str, payload: WhatsAppFlowVersionCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not flow:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, flow["organization_id"])
        _require_permission(user, flow["organization_id"], "bot.manage")
        return create_whatsapp_flow_version(conn, flow_id=flow_id, actor_user_id=user.get("id"), **payload.model_dump())


def publish_whatsapp_flow_route(flow_id: str, payload: WhatsAppFlowPublishRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not flow:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, flow["organization_id"])
        _require_permission(user, flow["organization_id"], "bot.manage")
        try:
            return publish_whatsapp_flow(conn, flow_id=flow_id, version_id=payload.version_id, actor_user_id=user.get("id"), register_encryption_public_key=payload.register_encryption_public_key)
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc))


def sync_whatsapp_flow_route(flow_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not flow:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, flow["organization_id"])
        _require_permission(user, flow["organization_id"], "bot.manage")
        try:
            return sync_whatsapp_flow(conn, flow_id=flow_id)
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc))


def rollback_whatsapp_flow_route(flow_id: str, payload: WhatsAppFlowRollbackRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not flow:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, flow["organization_id"])
        _require_permission(user, flow["organization_id"], "bot.manage")
        try:
            return rollback_whatsapp_flow(conn, flow_id=flow_id, target_version_id=payload.target_version_id, register_encryption_public_key=payload.register_encryption_public_key)
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc))


def execute_whatsapp_flow_route(flow_id: str, payload: WhatsAppFlowExecutionRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not flow:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, flow["organization_id"])
        _require_permission(user, flow["organization_id"], "conversation.manage")
        return execute_whatsapp_flow(conn, flow_id=flow_id, **payload.model_dump())


def whatsapp_flow_runtime_route(flow_id: str, payload: WhatsAppFlowRuntimeRequest) -> dict:
    with get_connection() as conn:
        try:
            return runtime_step(conn, flow_id=flow_id, execution_id=payload.execution_id, action=payload.action, screen_id=payload.screen_id, submitted_data=payload.submitted_data, client_capabilities=payload.client_capabilities)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


def whatsapp_flow_event_route(flow_id: str, payload: WhatsAppFlowTelemetryRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not flow:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, flow["organization_id"])
        _require_permission(user, flow["organization_id"], "insights.read")
        return record_whatsapp_flow_event(conn, flow_id=flow_id, execution_id=payload.execution_id, event_type=payload.event_type, screen_id=payload.screen_id, step_index=payload.step_index, payload=payload.payload)


def whatsapp_flow_experiment_route(flow_id: str, payload: WhatsAppFlowExperimentCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not flow:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, flow["organization_id"])
        _require_permission(user, flow["organization_id"], "bot.manage")
        return create_flow_experiment(conn, flow_id=flow_id, **payload.model_dump())


def whatsapp_flow_analytics_route(
    flow_id: str,
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    with get_connection() as conn:
        flow = fetch_one(conn, "SELECT * FROM whatsapp_flows WHERE id = ?", (flow_id,))
        if not flow:
            raise HTTPException(status_code=404, detail="WhatsApp flow not found")
        ensure_org_access(user, flow["organization_id"])
        _require_permission(user, flow["organization_id"], "insights.read")
        return whatsapp_flow_analytics(conn, flow_id=flow_id, since=since, until=until)


def list_whatsapp_templates(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT * FROM whatsapp_templates {where_sql} ORDER BY updated_at DESC LIMIT 100", tuple(params)) if table_exists(conn, "whatsapp_templates") else []
        return [serialize_template(conn, row, include_versions=True, include_sync_runs=True) for row in rows]


def get_whatsapp_template_route(template_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        row = fetch_one(conn, "SELECT * FROM whatsapp_templates WHERE id = ?", (template_id,)) if table_exists(conn, "whatsapp_templates") else None
        if not row:
            raise HTTPException(status_code=404, detail="WhatsApp template not found")
        ensure_org_access(user, row["organization_id"])
        _require_permission(user, row["organization_id"], "bot.manage")
        return serialize_template(conn, row, include_versions=True, include_sync_runs=True)


def create_whatsapp_template_route(payload: WhatsAppTemplateCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        values = payload.model_dump()
        version = values.pop("version")
        template_metadata = values.get("metadata") or {}
        version_metadata = version.pop("metadata", {}) or {}
        return create_whatsapp_template(
            conn,
            organization_id=values["organization_id"],
            bot_id=values["bot_id"],
            name=values["name"],
            category=version.get("category") or values.get("category"),
            default_language=version.get("language_code") or values.get("default_language"),
            body_text=version["body_text"],
            header_type=version.get("header_type") or "NONE",
            header_text=version.get("header_text"),
            footer_text=version.get("footer_text"),
            buttons=version.get("buttons") or [],
            variables=version.get("variables") or [],
            assets=version.get("assets") or {},
            sample_values=version.get("sample_values") or {},
            metadata={**template_metadata, **version_metadata},
            approval_status=version.get("approval_status") or "draft",
            fallback_template_id=version.get("fallback_template_id") or values.get("fallback_template_id"),
        )


def create_whatsapp_template_version_route(template_id: str, payload: WhatsAppTemplateVersionCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        template = fetch_one(conn, "SELECT * FROM whatsapp_templates WHERE id = ?", (template_id,)) if table_exists(conn, "whatsapp_templates") else None
        if not template:
            raise HTTPException(status_code=404, detail="WhatsApp template not found")
        ensure_org_access(user, template["organization_id"])
        _require_permission(user, template["organization_id"], "bot.manage")
        return create_whatsapp_template_version(conn, template_id=template_id, **payload.model_dump())


def lint_whatsapp_template_route(payload: WhatsAppTemplateLintRequest, user: dict = Depends(get_current_user)) -> dict:
    version = payload.version.model_dump()
    return lint_whatsapp_template_definition(
        template_name=payload.name,
        language_code=version.get("language_code"),
        category=version.get("category"),
        body_text=version.get("body_text"),
        header_type=version.get("header_type"),
        header_text=version.get("header_text"),
        footer_text=version.get("footer_text"),
        buttons=version.get("buttons"),
        variables=version.get("variables"),
        assets=version.get("assets"),
        sample_values=version.get("sample_values"),
    )


def sync_whatsapp_template_route(template_id: str, payload: WhatsAppTemplateSyncRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        template = fetch_one(conn, "SELECT * FROM whatsapp_templates WHERE id = ?", (template_id,)) if table_exists(conn, "whatsapp_templates") else None
        if not template:
            raise HTTPException(status_code=404, detail="WhatsApp template not found")
        ensure_org_access(user, template["organization_id"])
        _require_permission(user, template["organization_id"], "bot.manage")
        try:
            return sync_whatsapp_template(conn, template_id=template_id, version_id=payload.version_id, action=payload.action)
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc))


def sync_whatsapp_template_status_route(template_id: str, version_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        template = fetch_one(conn, "SELECT * FROM whatsapp_templates WHERE id = ?", (template_id,)) if table_exists(conn, "whatsapp_templates") else None
        if not template:
            raise HTTPException(status_code=404, detail="WhatsApp template not found")
        ensure_org_access(user, template["organization_id"])
        _require_permission(user, template["organization_id"], "bot.manage")
        try:
            return sync_whatsapp_template_status(conn, template_id=template_id, version_id=version_id)
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc))


def update_whatsapp_template_approval_route(template_id: str, payload: WhatsAppTemplateApprovalUpdateRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        template = fetch_one(conn, "SELECT * FROM whatsapp_templates WHERE id = ?", (template_id,)) if table_exists(conn, "whatsapp_templates") else None
        if not template:
            raise HTTPException(status_code=404, detail="WhatsApp template not found")
        ensure_org_access(user, template["organization_id"])
        _require_permission(user, template["organization_id"], "bot.manage")
        return update_whatsapp_template_approval(conn, template_id=template_id, **payload.model_dump())


def whatsapp_template_analytics_route(
    template_id: str,
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    with get_connection() as conn:
        template = fetch_one(conn, "SELECT * FROM whatsapp_templates WHERE id = ?", (template_id,)) if table_exists(conn, "whatsapp_templates") else None
        if not template:
            raise HTTPException(status_code=404, detail="WhatsApp template not found")
        ensure_org_access(user, template["organization_id"])
        _require_permission(user, template["organization_id"], "insights.read")
        return whatsapp_template_analytics(conn, template_id=template_id, since=since, until=until)

def list_reactivation(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    regenerate: bool = Query(default=False),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        if organization_id:
            ensure_org_access(user, organization_id)
            _require_permission(user, organization_id, "crm.manage")
            if regenerate:
                generate_reactivation_recommendations(conn, organization_id=organization_id, bot_id=bot_id)
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        return fetch_all(conn, f"SELECT * FROM reactivation_recommendations {where_sql} ORDER BY priority DESC, updated_at DESC LIMIT 200", params)

def create_voice_note(payload: VoiceNoteRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "conversation.manage")
    with get_connection() as conn:
        return ingest_voice_note(conn, **payload.model_dump())

def list_voice_notes(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        return fetch_all(conn, f"SELECT * FROM voice_notes {where_sql} ORDER BY created_at DESC LIMIT 100", params)

def create_feedback(payload: FeedbackRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "insights.read")
    with get_connection() as conn:
        return record_feedback(conn, **payload.model_dump())

def list_feedback(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        return fetch_all(conn, f"SELECT * FROM customer_feedback {where_sql} ORDER BY created_at DESC LIMIT 200", params)

def create_portal_request(payload: ServiceRequestCreate, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "conversation.manage")
    with get_connection() as conn:
        return create_service_request(conn, **payload.model_dump())

def list_portal_requests(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        rows = fetch_all(conn, f"SELECT * FROM service_requests {where_sql} ORDER BY updated_at DESC LIMIT 100", params)
        return [{**row, "payload": from_json(row.get("payload_json"), {}), "response": from_json(row.get("response_json"), {})} for row in rows]

def create_playbook_route(payload: PlaybookCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "playbooks.manage")
    with get_connection() as conn:
        return create_playbook(conn, **payload.model_dump())

def list_playbooks(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        rows = fetch_all(conn, f"SELECT * FROM industry_playbooks {where_sql} ORDER BY updated_at DESC LIMIT 100", params)
        return [{**row, "config": from_json(row.get("config_json"), {})} for row in rows]


def refresh_payment_route(payment_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        ensure_org_access(user, payment["organization_id"])
        _require_permission(user, payment["organization_id"], "revenue.manage")
        from ...payments_runtime import refresh_payment_status
        updated = refresh_payment_status(conn, payment_id)
        return payment_row(updated)


def get_crm_pipeline_summary(
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    with get_connection() as conn:
        ensure_org_access(user, organization_id)
        _require_permission(user, organization_id, "crm.manage")
        params: list[object] = [organization_id]
        where = "WHERE organization_id = ?"
        if bot_id:
            where += " AND bot_id = ?"
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT stage, COUNT(*) AS total, COALESCE(SUM(estimated_amount), 0) AS amount, COALESCE(AVG(close_probability), 0) AS avg_close_probability FROM crm_leads {where} GROUP BY stage ORDER BY total DESC, amount DESC", params)
        lost_rows = fetch_all(conn, f"SELECT COALESCE(lost_reason, 'sin_motivo') AS lost_reason, COUNT(*) AS total FROM crm_leads {where} AND (stage = 'cerrado_perdido' OR lost_reason IS NOT NULL) GROUP BY COALESCE(lost_reason, 'sin_motivo') ORDER BY total DESC LIMIT 10", params)
        history_rows = fetch_all(conn, "SELECT * FROM lead_stage_history WHERE organization_id = ? ORDER BY created_at DESC LIMIT 20", (organization_id,)) if table_exists(conn, "lead_stage_history") else []
        summary = {
            "total_leads": sum(int(row.get("total") or 0) for row in rows),
            "weighted_amount": sum(float(row.get("amount") or 0) * (float(row.get("avg_close_probability") or 0) / 100.0) for row in rows),
            "stages": rows,
            "lost_reasons": lost_rows,
            "recent_stage_changes": history_rows,
        }
        return ok(summary)


def get_crm_funnel_summary(
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    with get_connection() as conn:
        ensure_org_access(user, organization_id)
        _require_permission(user, organization_id, "crm.manage")
        params: list[object] = [organization_id]
        where = "WHERE organization_id = ?"
        if bot_id:
            where += " AND bot_id = ?"
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT stage, COUNT(*) AS total FROM crm_leads {where} GROUP BY stage ORDER BY total DESC", params)
        total = sum(int(row.get("total") or 0) for row in rows) or 1
        funnel = [{**row, "share": round((int(row.get("total") or 0) / total) * 100, 2)} for row in rows]
        return ok({"organization_id": organization_id, "funnel": funnel})
