from __future__ import annotations

from .common import *
from .common import _org_filter_sql, _require_permission
from ...contracts import payment_row

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
        return [{**row, "definition": from_json(row.get("definition_json"), {}), "metadata": from_json(row.get("metadata_json"), {})} for row in rows]

def create_whatsapp_flow_route(payload: WhatsAppFlowCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        row = create_whatsapp_flow(conn, **payload.model_dump())
        return {**row, "definition": from_json(row.get("definition_json"), {}), "metadata": from_json(row.get("metadata_json"), {})}

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
