from __future__ import annotations

from typing import Any

from .base import ConnectionLike, execute
from ..utils import new_id, to_json, utcnow_iso

def create_audit_log(
    conn: ConnectionLike,
    *,
    organization_id: str | None,
    actor_user_id: str | None,
    actor_type: str,
    entity_type: str,
    entity_id: str | None,
    action: str,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
    session_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    severity: str = "info",
    trace_id: str | None = None,
) -> None:
    execute(
        conn,
        """
        INSERT INTO audit_logs (
            id, organization_id, actor_user_id, actor_type, entity_type, entity_id, action,
            metadata_json, request_id, session_id, ip_address, user_agent, severity, trace_id, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("audit"),
            organization_id,
            actor_user_id,
            actor_type,
            entity_type,
            entity_id,
            action,
            to_json(metadata or {}),
            request_id,
            session_id,
            ip_address,
            user_agent,
            severity,
            trace_id,
            utcnow_iso(),
        ),
    )
