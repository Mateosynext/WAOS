from __future__ import annotations

from typing import Iterable, Mapping


def _table_exists(conn, table: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
        return bool(row)
    row = conn.execute(
        """
        SELECT 1 AS present
        FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = ?
        LIMIT 1
        """,
        (table,),
    ).fetchone()
    return bool(row)


def _column_exists(conn, table: str, column: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any((row[1] if not isinstance(row, dict) else row.get("name")) == column for row in rows)
    row = conn.execute(
        """
        SELECT 1 AS present
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = ? AND column_name = ?
        LIMIT 1
        """,
        (table, column),
    ).fetchone()
    return bool(row)


def assert_schema_ready(
    conn,
    *,
    owner: str,
    tables: Iterable[str],
    columns: Mapping[str, Iterable[str]] | Iterable[tuple[str, str]] | None = None,
) -> None:
    missing_tables = [table for table in tables if not _table_exists(conn, table)]
    missing_columns: list[str] = []
    if columns is None:
        column_items: list[tuple[str, str]] = []
    elif isinstance(columns, Mapping):
        column_items = [(table, column) for table, expected_columns in columns.items() for column in expected_columns]
    else:
        column_items = list(columns)
    for table, column in column_items:
        if not _column_exists(conn, table, column):
            missing_columns.append(f"{table}.{column}")
    if not missing_tables and not missing_columns:
        return
    parts: list[str] = []
    if missing_tables:
        parts.append("tables=" + ", ".join(missing_tables))
    if missing_columns:
        parts.append("columns=" + ", ".join(missing_columns))
    details = "; ".join(parts)
    raise RuntimeError(
        f"Schema for {owner} is missing required objects ({details}). Run database migrations before invoking this runtime module."
    )
