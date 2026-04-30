from __future__ import annotations

from typing import Any

def ensure_vertical_domain_schema(conn) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS vertical_domains (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        vertical_key TEXT NOT NULL DEFAULT 'default',
        domain_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT,
        updated_at TEXT
    );
    """)

def get_vertical_domain_snapshot(*_: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "organization_id": kwargs.get("organization_id"),
        "vertical": kwargs.get("vertical") or "default",
        "status": "not_configured",
        "domains": [],
        "mode": "rc_compatibility",
    }
