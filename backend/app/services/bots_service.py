from __future__ import annotations

from ..db import fetch_all, fetch_one


def bot_health_summary(conn, *, organization_id: str, bot_id: str) -> dict:
    bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ? AND organization_id = ?", (bot_id, organization_id)) or {}
    integrations = fetch_all(conn, "SELECT status, health_status FROM integration_connections WHERE organization_id = ? AND (bot_id = ? OR bot_id IS NULL)", (organization_id, bot_id))
    paused = bot.get("status") == "paused"
    healthy = sum(1 for row in integrations if row.get("health_status") == "healthy")
    degraded = sum(1 for row in integrations if row.get("health_status") not in {None, "healthy"})
    return {
        "bot_id": bot_id,
        "status": bot.get("status") or "unknown",
        "is_paused": paused,
        "published_version_id": bot.get("published_version_id"),
        "integrations": {"total": len(integrations), "healthy": healthy, "degraded": degraded},
    }
