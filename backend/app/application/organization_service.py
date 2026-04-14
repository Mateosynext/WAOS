from __future__ import annotations

from fastapi import HTTPException

from ..db import fetch_all
from ..verticals import build_organization_settings
from ..performance import clamp_limit, clamp_offset
from ..repositories import create_audit_log, create_organization, get_org
from ..security import ensure_org_access
from ..utils import to_json, utcnow_iso
from .support import org_filter_sql, require_permission
from .uow import UnitOfWork


class OrganizationService:
    def list(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, limit: int, offset: int) -> list[dict]:
        conn = uow.conn
        where_sql, params = org_filter_sql(user, organization_id, "id")
        params.extend([clamp_limit(limit), clamp_offset(offset)])
        return fetch_all(conn, f"SELECT * FROM organizations {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?", params)

    def create(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        if user["global_role"] != "super_admin":
            raise HTTPException(status_code=403, detail="Only super admin can create organizations")
        return create_organization(uow.conn, name=payload.name, vertical=payload.vertical, timezone=payload.timezone, created_by=user)

    def update(self, uow: UnitOfWork, *, user: dict, organization_id: str, payload) -> dict:
        conn = uow.conn
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        org = get_org(conn, organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        updated = {
            "name": payload.name or org["name"],
            "vertical": payload.vertical if payload.vertical is not None else org.get("vertical"),
            "timezone": payload.timezone or org["timezone"],
            "status": payload.status or org["status"],
        }
        conn.execute(
            """
            UPDATE organizations
            SET name = ?, vertical = ?, timezone = ?, status = ?, settings_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (updated["name"], updated["vertical"], updated["timezone"], updated["status"], to_json(build_organization_settings(updated["vertical"], organization_name=updated["name"])), utcnow_iso(), organization_id),
        )
        create_audit_log(
            conn,
            organization_id=organization_id,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="organization",
            entity_id=organization_id,
            action="organization.updated",
            metadata=updated,
        )
        return get_org(conn, organization_id)
