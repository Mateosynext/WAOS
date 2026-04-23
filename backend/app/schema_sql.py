from __future__ import annotations

from functools import lru_cache
from pathlib import Path


_DB_DIR = Path(__file__).resolve().parents[1] / "db"


@lru_cache(maxsize=None)
def _read_sql(*relative_parts: str) -> str:
    path = _DB_DIR.joinpath(*relative_parts)
    return path.read_text(encoding="utf-8")


def load_migration_sql(filename: str) -> str:
    return _read_sql("migrations", filename)


def apply_migration_sql(conn, filename: str) -> None:
    conn.executescript(load_migration_sql(filename))


def load_schema_sql(*relative_parts: str) -> str:
    return _read_sql("schema", *relative_parts)


def apply_schema_sql(conn, *relative_parts: str) -> None:
    conn.executescript(load_schema_sql(*relative_parts))


# Backwards-compatible alias for existing imports.
_migration_sql = load_migration_sql
