from __future__ import annotations

from .common import *
from .common import _require_permission
from ...whatsapp_delivery_truth import build_whatsapp_delivery_truth_report

def analytics_dashboard(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    if organization_id:
        ensure_org_access(user, organization_id)
    _require_permission(user, organization_id, "runs.read")
    with get_connection() as conn:
        return _compute_dashboard(conn, organization_id)

def audit_logs(
    organization_id: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if entity_type:
            where_sql += " AND entity_type = ? "
            params.append(entity_type)
        if entity_id:
            where_sql += " AND entity_id = ? "
            params.append(entity_id)
        if action:
            where_sql += " AND action = ? "
            params.append(action)
        rows = fetch_all(conn, f"SELECT * FROM audit_logs {where_sql} ORDER BY created_at DESC LIMIT 200", params)
        return [{**row, "metadata": from_json(row["metadata_json"], {})} for row in rows]

def analytics_daily(organization_id: str = Query(...), bot_id: str | None = Query(default=None), day: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, organization_id)
    _require_permission(user, organization_id, "operations.read")
    with get_connection() as conn:
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
        return materialize_daily_metrics(conn, organization_id=organization_id, bot_id=bot_id, day=day)

def read_i18n_config(
    organization_id: str,
    bot_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return get_language_config(conn, organization_id, bot_id)

def write_i18n_config(payload: I18nConfigRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    with get_connection() as conn:
        return upsert_language_config(conn, **payload.model_dump())

def read_i18n_analytics(
    organization_id: str,
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return language_analytics(conn, organization_id, bot_id)

def read_omnichannel_overview(
    organization_id: str,
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return omnichannel_overview(conn, organization_id, bot_id)

def analytics_director_mode(
    organization_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    _require_permission(user, organization_id, "insights.read")
    with get_connection() as conn:
        return director_dashboard(conn, organization_id)

def analytics_funnel(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT lead_stage, COUNT(*) AS total FROM contact_memory {where_sql} GROUP BY lead_stage", params)
        mapping = {"new": "new", "contacted": "contacted", "qualified": "qualified", "booked": "booked", "won": "won", "nuevo": "new", "contactado": "contacted", "calificado": "qualified", "agendado": "booked", "ganado": "won"}
        stages = {key: 0 for key in ["new", "contacted", "qualified", "booked", "won"]}
        for row in rows:
            normalized = mapping.get((row.get("lead_stage") or "").lower())
            if normalized:
                stages[normalized] += int(row.get("total") or 0)
        order = ["new", "contacted", "qualified", "booked", "won"]
        funnel = []
        prev = None
        for stage in order:
            total = stages.get(stage, 0)
            conversion = round((total / prev) * 100, 2) if prev else 100.0
            funnel.append({"stage": stage, "total": total, "conversion_from_previous": conversion})
            prev = max(total, 1)
        return {"organization_id": organization_id, "bot_id": bot_id, "funnel": funnel}

def analytics_operator_performance(organization_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "c.organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        rows = fetch_all(
            conn,
            f"""
            SELECT u.id AS user_id, u.full_name, u.email,
                   COUNT(DISTINCT c.id) AS takeovers,
                   COUNT(DISTINCT CASE WHEN cm.lead_stage IN ('won', 'ganado', 'booked', 'agendado') THEN c.id END) AS closes,
                   AVG(CASE WHEN c.last_human_at IS NOT NULL AND c.created_at IS NOT NULL THEN 1 ELSE NULL END) AS avg_resolution_proxy
            FROM conversations c
            JOIN users u ON u.id = c.assigned_user_id
            LEFT JOIN contact_memory cm ON cm.contact_id = c.contact_id AND cm.bot_id = c.bot_id
            {where_sql} AND c.assigned_user_id IS NOT NULL
            GROUP BY u.id, u.full_name, u.email
            ORDER BY takeovers DESC, closes DESC
            """,
            params,
        )
        return [{**row, "avg_resolution_proxy": round(float(row.get("avg_resolution_proxy") or 0), 2)} for row in rows]

def analytics_objections(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT objections FROM contact_memory {where_sql}", params)
        counts: dict[str, int] = {}
        for row in rows:
            value = (row.get("objections") or "").strip()
            if not value:
                continue
            for item in [part.strip().lower() for part in value.replace(';', ',').split(',') if part.strip()]:
                counts[item] = counts.get(item, 0) + 1
        return [{"objection": key, "count": value} for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]

def analytics_heatmap(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT created_at FROM messages {where_sql} AND direction = 'inbound'", params)
        buckets: dict[tuple[int, int], int] = {}
        for row in rows:
            created = parse_iso(row.get("created_at"))
            if not created:
                continue
            key = (created.weekday(), created.hour)
            buckets[key] = buckets.get(key, 0) + 1
        return [
            {"weekday": weekday, "hour": hour, "messages": count}
            for (weekday, hour), count in sorted(buckets.items(), key=lambda item: (item[0][0], item[0][1]))
        ]

def analytics_contact_windows(organization_id: str | None = Query(default=None), contact_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict:
    if organization_id:
        ensure_org_access(user, organization_id)
    with get_connection() as conn:
        if not organization_id:
            orgs = accessible_org_ids(user)
            organization_id = orgs[0] if orgs else None
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        return {"organization_id": organization_id, "contact_id": contact_id, "bot_id": bot_id, "windows": _best_contact_windows(conn, organization_id, contact_id=contact_id, bot_id=bot_id)}

def analytics_closure_attribution(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        where_sql, params = _org_filter_sql(user, organization_id, "organization_id")
        if not where_sql:
            where_sql = " WHERE 1 = 1 "
        if bot_id:
            where_sql += " AND bot_id = ? "
            params.append(bot_id)
        rows = fetch_all(conn, f"SELECT human_takeover, status FROM conversations {where_sql}", params)
        ai_only = sum(1 for row in rows if int(row.get("human_takeover") or 0) == 0)
        assisted = sum(1 for row in rows if int(row.get("human_takeover") or 0) == 1)
        total = max(len(rows), 1)
        return {
            "ai_only": ai_only,
            "assisted": assisted,
            "ai_only_share": round((ai_only / total) * 100, 2),
            "assisted_share": round((assisted / total) * 100, 2),
        }


def analytics_whatsapp_delivery_truth(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    window_hours: int = Query(default=168),
    reconcile: bool = Query(default=False),
    reconcile_hours: int | None = Query(default=None),
    limit: int = Query(default=25),
    user: dict = Depends(get_current_user),
) -> dict:
    if not organization_id:
        orgs = accessible_org_ids(user)
        organization_id = orgs[0] if orgs else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    _require_permission(user, organization_id, "insights.read")
    with get_connection() as conn:
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
        report = build_whatsapp_delivery_truth_report(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            window_hours=max(1, min(int(window_hours or 168), 24 * 90)),
            reconcile=bool(reconcile),
            reconcile_hours=max(1, min(int(reconcile_hours or window_hours or 168), 24 * 90)),
            limit=max(1, min(int(limit or 25), 100)),
        )
        return ok(report)
