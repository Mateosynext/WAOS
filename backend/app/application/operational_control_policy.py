from __future__ import annotations

from collections.abc import Callable

from ..db import fetch_one, table_exists


def risk_level(intent: str | None, impact: dict, *, high_impact_intents: set[str]) -> str:
    if not intent:
        return "low"
    if intent in high_impact_intents or int(impact.get("appointments_affected") or 0) > 3:
        return "high"
    if intent.startswith("bot.") or int(impact.get("appointments_affected") or 0) > 0:
        return "medium"
    return "low"


def requires_confirmation(intent: str | None, impact: dict, *, high_impact_intents: set[str]) -> bool:
    if not intent:
        return False
    if intent in high_impact_intents:
        return True
    return int(impact.get("appointments_affected") or 0) > 3 or bool(impact.get("whole_business"))


def needs_second_approval(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    intent: str | None,
    impact: dict,
    dual_approval_intents: set[str],
    is_feature_enabled: Callable[[object, str, str, str], bool],
) -> bool:
    if intent not in dual_approval_intents:
        return False
    if not is_feature_enabled(conn, organization_id, bot_id, "ops_control_dual_approval_enterprise_v1"):
        return False
    policy = fetch_one(conn, "SELECT * FROM organization_security_policies WHERE organization_id = ?", (organization_id,)) if table_exists(conn, "organization_security_policies") else None
    return bool(policy and int(policy.get("require_dual_approval_releases") or 0) == 1)
