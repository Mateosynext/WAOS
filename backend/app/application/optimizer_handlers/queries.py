from __future__ import annotations

from typing import Any

from ...contracts import ok
from ...db import fetch_all, fetch_one, table_exists
from ..uow import UnitOfWork

def overview(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
    self._authorize(user, organization_id)
    latest_cycle = fetch_one(
        uow.conn,
        "SELECT * FROM optimizer_cycles WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY created_at DESC LIMIT 1",
        (organization_id, bot_id),
    ) if table_exists(uow.conn, "optimizer_cycles") else None
    proposals = fetch_all(
        uow.conn,
        "SELECT * FROM optimizer_proposals WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY created_at DESC LIMIT 50",
        (organization_id, bot_id),
    ) if table_exists(uow.conn, "optimizer_proposals") else []
    experiments = fetch_all(
        uow.conn,
        "SELECT * FROM optimizer_experiments WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY updated_at DESC LIMIT 50",
        (organization_id, bot_id),
    ) if table_exists(uow.conn, "optimizer_experiments") else []
    states = fetch_all(
        uow.conn,
        "SELECT * FROM optimizer_control_states WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY updated_at DESC LIMIT 50",
        (organization_id, bot_id),
    ) if table_exists(uow.conn, "optimizer_control_states") else []
    return ok({
        "optimizer": "waos_optimizer_v1",
        "organization_id": organization_id,
        "bot_id": bot_id,
        "latest_cycle": self._serialize_cycle(latest_cycle),
        "proposals": [self._serialize_proposal(item) for item in proposals],
        "experiments": [self._serialize_experiment(item) for item in experiments],
        "control_states": [self._serialize_state(item) for item in states],
    })


def list_proposals(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, status: str | None, user: dict) -> dict[str, Any]:
    self._authorize(user, organization_id)
    where = ["organization_id = ?"]
    params: list[Any] = [organization_id]
    if bot_id:
        where.append("bot_id = ?")
        params.append(bot_id)
    if status:
        where.append("status = ?")
        params.append(status)
    rows = fetch_all(
        uow.conn,
        f"SELECT * FROM optimizer_proposals WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 200",
        tuple(params),
    ) if table_exists(uow.conn, "optimizer_proposals") else []
    return ok({"items": [self._serialize_proposal(item) for item in rows], "count": len(rows)})

