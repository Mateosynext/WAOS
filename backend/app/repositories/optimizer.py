from __future__ import annotations

from typing import Any

from .base import ConnectionLike
from ..db import execute, fetch_all, fetch_one, table_exists
from ..utils import new_id, to_json, utcnow_iso


def list_control_rows(conn: ConnectionLike, *, organization_id: str, bot_id: str | None) -> list[dict[str, Any]]:
    if not organization_id or not table_exists(conn, "optimizer_control_states"):
        return []
    sql = "SELECT * FROM optimizer_control_states WHERE organization_id = ?"
    params: list[Any] = [organization_id]
    if bot_id:
        sql += " AND COALESCE(bot_id, '') = COALESCE(?, '')"
        params.append(bot_id)
    sql += " ORDER BY updated_at DESC"
    return fetch_all(conn, sql, tuple(params))


def list_active_experiments(conn: ConnectionLike, *, organization_id: str, bot_id: str | None) -> list[dict[str, Any]]:
    if not organization_id or not table_exists(conn, "optimizer_experiments"):
        return []
    sql = (
        "SELECT * FROM optimizer_experiments WHERE organization_id = ? "
        "AND status IN ('running', 'planned', 'winner_selected') ORDER BY updated_at DESC"
    )
    params: list[Any] = [organization_id]
    if bot_id:
        sql = sql.replace(" ORDER BY", " AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY")
        params.append(bot_id)
    return fetch_all(conn, sql, tuple(params))


def proposal_target_name(conn: ConnectionLike, proposal_id: str | None) -> str:
    if not proposal_id:
        return ""
    proposal = fetch_one(conn, "SELECT target_name FROM optimizer_proposals WHERE id = ?", (proposal_id,)) or {}
    return str(proposal.get("target_name") or "").strip()


def insert_runtime_optimizer_audit(
    conn: ConnectionLike,
    *,
    organization_id: str | None,
    bot_id: str | None,
    target_name: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    if conn is None or not organization_id or not table_exists(conn, "optimizer_change_audits"):
        return
    execute(
        conn,
        "INSERT INTO optimizer_change_audits (id, organization_id, bot_id, proposal_id, experiment_id, decision_id, event_type, payload_json, created_by, created_at) VALUES (?, ?, ?, NULL, NULL, NULL, ?, ?, NULL, ?)",
        (new_id("optimizer_audit"), organization_id, bot_id, f"runtime_{target_name}_{event_type}", to_json(payload), utcnow_iso()),
    )
