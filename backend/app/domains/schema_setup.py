from __future__ import annotations

from ..schema_sql import apply_migration_sql
from ..schema_sql import _migration_sql

V9_SCHEMA_SQL = _migration_sql("015_catalog_v9.sql")


def ensure_v9_schema(conn) -> None:
    apply_migration_sql(conn, "015_catalog_v9.sql")
    conn.commit()
