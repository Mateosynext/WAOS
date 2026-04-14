from __future__ import annotations

from ...contracts import audit_log_row, run_row
from .common import *

def list_runs(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    if organization_id:
        ensure_org_access(user, organization_id)
        _require_permission(user, organization_id, "runs.read")
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
        if status:
            where_sql += " AND status = ? "
            params.append(status)
        if source_type:
            where_sql += " AND source_type = ? "
            params.append(source_type)
        rows = fetch_all(conn, f"SELECT * FROM execution_runs {where_sql} ORDER BY created_at DESC LIMIT 200", params)
        return [run_row(row) for row in rows]

def get_run(run_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        run = fetch_one(conn, "SELECT * FROM execution_runs WHERE id = ?", (run_id,))
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        ensure_org_access(user, run["organization_id"])
        logs = fetch_all(conn, "SELECT * FROM technical_logs WHERE execution_run_id = ? ORDER BY created_at ASC", (run_id,))
        return {
            **run_row(run),
            "logs": [audit_log_row(row) for row in logs],
        }

def list_technical_logs(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    level: str | None = Query(default=None),
    trace_id: str | None = Query(default=None),
    execution_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    if organization_id:
        ensure_org_access(user, organization_id)
        _require_permission(user, organization_id, "logs.read")
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
        if level:
            where_sql += " AND level = ? "
            params.append(level)
        if trace_id:
            where_sql += " AND trace_id = ? "
            params.append(trace_id)
        if execution_id:
            where_sql += " AND execution_id = ? "
            params.append(execution_id)
        rows = fetch_all(conn, f"SELECT * FROM technical_logs {where_sql} ORDER BY created_at DESC LIMIT 300", params)
        return [audit_log_row(row) for row in rows]

def deliveries_list(organization_id: str | None = Query(default=None), channel: str | None = Query(default=None), entity_type: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if channel:
            where_sql += " AND channel = ? "
            params.append(channel)
        if entity_type:
            where_sql += " AND entity_type = ? "
            params.append(entity_type)
        rows = fetch_all(conn, f"SELECT * FROM delivery_attempts {where_sql} ORDER BY created_at DESC LIMIT 200", params)
        return [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in rows]

def notifications_list(
    organization_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=settings.default_page_size),
    offset: int = Query(default=0),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        where_sql += " AND (user_id IS NULL OR user_id = ?) "
        params.append(user["id"])
        if status:
            where_sql += " AND status = ? "
            params.append(status)
        if category:
            where_sql += " AND category = ? "
            params.append(category)
        params.extend([clamp_limit(limit), clamp_offset(offset)])
        rows = fetch_all(conn, f"SELECT * FROM operator_notifications {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?", params)
        return [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in rows]

def notifications_mark_read(notification_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        row = fetch_one(conn, "SELECT * FROM operator_notifications WHERE id = ?", (notification_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")
        ensure_org_access(user, row["organization_id"])
        if row.get("user_id") and row.get("user_id") != user["id"]:
            raise HTTPException(status_code=403, detail="Notification not accessible")
        execute(conn, "UPDATE operator_notifications SET status = 'read', read_at = ? WHERE id = ?", (utcnow_iso(), notification_id))
        updated = fetch_one(conn, "SELECT * FROM operator_notifications WHERE id = ?", (notification_id,))
        return {**updated, "metadata": from_json(updated.get("metadata_json"), {})}

def alert_events_list(organization_id: str | None = Query(default=None), limit: int = Query(default=settings.default_page_size), offset: int = Query(default=0), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        rows = fetch_all(conn, f"SELECT * FROM alert_events {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [clamp_limit(limit), clamp_offset(offset)])
        return [{**row, "details": from_json(row.get("details_json"), {})} for row in rows]
