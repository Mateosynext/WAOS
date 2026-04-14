from __future__ import annotations

from .common import *

def list_automation_rules(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    if organization_id:
        ensure_org_access(user, organization_id)
        _require_permission(user, organization_id, "integration.manage")
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT * FROM automation_rules {where_sql} ORDER BY created_at DESC", params)
        return [{**r, "config": from_json(r["config_json"], {})} for r in rows]

def create_automation_rule(payload: AutomationRuleRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    with get_connection() as conn:
        bot = get_bot(conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        rule_id = new_id("rule")
        config = {
            "delay_minutes": payload.delay_minutes,
            "max_attempts": payload.max_attempts,
            "message_template": payload.message_template,
        }
        execute(
            conn,
            """
            INSERT INTO automation_rules (id, organization_id, bot_id, rule_type, name, status, config_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rule_id, payload.organization_id, payload.bot_id, payload.rule_type, payload.name, payload.status, to_json(config), utcnow_iso(), utcnow_iso()),
        )
        create_audit_log(conn, organization_id=payload.organization_id, actor_user_id=user["id"], actor_type="user", entity_type="automation_rule", entity_id=rule_id, action="automation_rule.created", metadata=config)
        return fetch_one(conn, "SELECT * FROM automation_rules WHERE id = ?", (rule_id,))

def list_automation_jobs(
    organization_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    if organization_id:
        ensure_org_access(user, organization_id)
        _require_permission(user, organization_id, "runs.read")
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if status:
            where_sql += " AND status = ? "
            params.append(status)
        return fetch_all(conn, f"SELECT * FROM automation_jobs {where_sql} ORDER BY scheduled_for ASC", params)

def process_due_jobs(user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        if user["global_role"] != "super_admin":
            raise HTTPException(status_code=403, detail="Only super admin can process due jobs")
        jobs = fetch_all(
            conn,
            """
            SELECT * FROM automation_jobs
            WHERE status = 'queued' AND scheduled_for <= ?
            ORDER BY scheduled_for ASC
            LIMIT 50
            """,
            (utcnow_iso(),),
        )
        processed = []
        for job in jobs:
            conversation = get_conversation(conn, job["conversation_id"]) if job.get("conversation_id") else None
            if not conversation or int(conversation.get("human_takeover", 0)) == 1:
                execute(conn, "UPDATE automation_jobs SET status = 'skipped', executed_at = ?, last_error = ? WHERE id = ?", (utcnow_iso(), "human_takeover_or_missing_conversation", job["id"]))
                processed.append({"id": job["id"], "status": "skipped"})
                continue
            payload = from_json(job.get("payload_json"), {})
            body = payload.get("message_template") or "Solo dando seguimiento a tu consulta."
            create_message(
                conn,
                organization_id=job["organization_id"],
                conversation_id=job["conversation_id"],
                contact_id=job.get("contact_id"),
                bot_id=job["bot_id"],
                direction="outbound",
                kind="text",
                source="ai",
                body=body,
                status="simulated",
                metadata={"automation_job_id": job["id"]},
            )
            execute(conn, "UPDATE automation_jobs SET status = 'executed', executed_at = ? WHERE id = ?", (utcnow_iso(), job["id"]))
            processed.append({"id": job["id"], "status": "executed"})
        return {"processed": processed, "count": len(processed)}
