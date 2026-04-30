from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from .db import fetch_one
from .security import ensure_org_access

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class TenantResourceSpec:
    resource_type: str
    table: str
    id_column: str = "id"
    organization_column: str = "organization_id"


MULTI_TENANT_RESOURCE_SPECS: tuple[TenantResourceSpec, ...] = (
    TenantResourceSpec("bot_id", "bots"),
    TenantResourceSpec("conversation_id", "conversations"),
    TenantResourceSpec("run_id", "ai_workflow_runs"),
    TenantResourceSpec("tool_execution_id", "tool_execution_runs"),
    TenantResourceSpec("knowledge_document_id", "knowledge_documents"),
    TenantResourceSpec("integration_id", "integration_connections"),
    TenantResourceSpec("outcome_id", "outcome_events"),
    TenantResourceSpec("payment_id", "commerce_payments"),
)

RESOURCE_SPECS_BY_TYPE = {spec.resource_type: spec for spec in MULTI_TENANT_RESOURCE_SPECS}


def _safe_identifier(value: str) -> str:
    text = str(value or "").strip()
    if not _IDENTIFIER_RE.match(text):
        raise ValueError(f"unsafe_sql_identifier:{text}")
    return text


def require_same_tenant_resource(
    conn,
    *,
    user: dict[str, Any],
    resource_type: str,
    resource_id: str,
    organization_id: str | None = None,
    return_row: bool = True,
) -> dict[str, Any] | None:
    """Fetch a tenant-owned resource and prove it belongs to the caller's tenant.

    This is intentionally generic so fuzz tests can exercise every critical id
    class with real database rows. It returns 404 when the id does not exist and
    403 when it exists in another tenant; it never returns a cross-tenant row.
    """
    spec = RESOURCE_SPECS_BY_TYPE.get(resource_type)
    if spec is None:
        raise ValueError(f"unknown_tenant_resource_type:{resource_type}")
    table = _safe_identifier(spec.table)
    id_column = _safe_identifier(spec.id_column)
    org_column = _safe_identifier(spec.organization_column)
    row = fetch_one(conn, f"SELECT * FROM {table} WHERE {id_column} = ? LIMIT 1", (resource_id,))
    if not row:
        raise HTTPException(status_code=404, detail=f"{resource_type}_not_found")
    actual_org = str(row.get(org_column) or "")
    if organization_id is not None and str(organization_id) != actual_org:
        raise HTTPException(status_code=403, detail="forbidden_cross_tenant")
    ensure_org_access(user, actual_org)
    return row if return_row else None
