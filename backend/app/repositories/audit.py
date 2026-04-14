from __future__ import annotations

import os
import sqlite3
from typing import Any

from ..db import execute, fetch_all, fetch_one
from ..defaults import default_bot_config
from ..utils import from_json, hash_password, new_id, slugify, to_json, utcnow_iso
from ..verticals import build_organization_settings

def create_audit_log(
    conn: sqlite3.Connection,
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
