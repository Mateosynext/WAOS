from __future__ import annotations

import os
from typing import Any

from .base import ConnectionLike

from ..db import execute, fetch_all, fetch_one
from ..defaults import default_bot_config
from ..utils import from_json, hash_password, new_id, slugify, to_json, utcnow_iso
from ..verticals import build_organization_settings

def get_org(conn: ConnectionLike, organization_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (organization_id,))


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


def _unique_org_slug(conn: ConnectionLike, base_slug: str) -> str:
    slug = base_slug
    suffix = 2
    while fetch_one(conn, "SELECT id FROM organizations WHERE slug = ?", (slug,)):
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def create_organization(conn: ConnectionLike, *, name: str, vertical: str, timezone: str, created_by: dict) -> dict:
    organization_id = new_id("org")
    now = utcnow_iso()
    slug = _unique_org_slug(conn, slugify(name))
    execute(
        conn,
        """
        INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at)
        VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)
        """,
        (organization_id, name, slug, timezone, vertical, to_json(build_organization_settings(vertical, organization_name=name)), now, now),
    )
    execute(
        conn,
        """
        INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at)
        VALUES (?, ?, ?, ?, 1, ?)
        """,
        (new_id("orgm"), organization_id, created_by["id"], created_by["global_role"], now),
    )
    create_audit_log(
        conn,
        organization_id=organization_id,
        actor_user_id=created_by["id"],
        actor_type="user",
        entity_type="organization",
        entity_id=organization_id,
        action="organization.created",
        metadata={"name": name, "vertical": vertical},
    )
    return get_org(conn, organization_id)
