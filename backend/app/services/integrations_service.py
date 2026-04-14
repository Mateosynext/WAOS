from __future__ import annotations

from ..db import fetch_all


def integration_health_summary(conn, *, organization_id: str, bot_id: str | None = None) -> dict:
    params = [organization_id]
    where_sql = "organization_id = ?"
    if bot_id:
        where_sql += " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    rows = fetch_all(conn, f"SELECT id, name, provider, status, health_status, credential_status, updated_at FROM integration_connections WHERE {where_sql} ORDER BY updated_at DESC", params)
    healthy = [row for row in rows if row.get("health_status") == "healthy"]
    degraded = [row for row in rows if row.get("health_status") not in {None, "healthy"}]
    expiring = [row for row in rows if row.get("credential_status") in {"expiring", "expired", "invalid"}]
    return {
        "items": rows,
        "totals": {"total": len(rows), "healthy": len(healthy), "degraded": len(degraded), "credential_attention": len(expiring)},
    }
