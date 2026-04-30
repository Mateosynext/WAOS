from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_vertical_marketplace_schema(conn) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS vertical_marketplace_packages (
        id TEXT PRIMARY KEY,
        vertical_key TEXT NOT NULL DEFAULT 'default',
        name TEXT NOT NULL,
        version TEXT NOT NULL DEFAULT '0.1.0',
        package_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TEXT NOT NULL,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS vertical_marketplace_installs (
        id TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL,
        package_id TEXT NOT NULL,
        version TEXT NOT NULL DEFAULT '0.1.0',
        status TEXT NOT NULL DEFAULT 'installed',
        installed_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    );
    """)

def list_marketplace_packages(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return []

def get_marketplace_package(*_: Any, **kwargs: Any) -> dict[str, Any] | None:
    return None

def publish_marketplace_package(conn=None, **kwargs: Any) -> dict[str, Any]:
    package_id = kwargs.get("id") or kwargs.get("package_id") or "pkg_rc"
    if conn is not None:
        ensure_vertical_marketplace_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO vertical_marketplace_packages (id, vertical_key, name, version, package_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (package_id, kwargs.get("vertical_key") or "default", kwargs.get("name") or "RC package", kwargs.get("version") or "0.1.0", json.dumps(kwargs.get("package") or {}), "published", _now(), _now()),
        )
    return {"id": package_id, "status": "published"}

def install_marketplace_package(*_: Any, **kwargs: Any) -> dict[str, Any]:
    return {"id": kwargs.get("install_id") or "install_rc", "status": "installed"}

def list_marketplace_installs(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return []

def upgrade_marketplace_install(*_: Any, **kwargs: Any) -> dict[str, Any]:
    return {"id": kwargs.get("install_id") or "install_rc", "status": "upgraded"}
