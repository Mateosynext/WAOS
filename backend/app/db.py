from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Iterable

try:  # pragma: no cover - postgres dependency may not exist in local test env
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

try:  # pragma: no cover - optional in local dev
    from psycopg_pool import ConnectionPool
except Exception:  # pragma: no cover
    ConnectionPool = None

from .config import settings
from .backend_runtime import ensure_backend_runtime_schema
from .domains.schema_setup import ensure_v9_schema
from .vertical_transactions import ensure_vertical_transaction_schema
from .vertical_domain_runtime import ensure_vertical_domain_schema
from .talent_runtime import ensure_talent_schema
from .world_class import ensure_world_class_schema
from .world_class_plus import ensure_world_class_plus_schema
from .telemetry_runtime import ensure_telemetry_schema, seed_default_alert_rules

THIS_FILE = Path(__file__).resolve()
ROOT = next(
    (parent for parent in THIS_FILE.parents if (parent / "db" / "schema.sql").exists()),
    THIS_FILE.parents[1],
)
SCHEMA_PATH = ROOT / "db" / "schema.sql"

_POOL_LOCK = Lock()
_PG_POOL: ConnectionPool | None = None


def _build_pg_pool() -> ConnectionPool | None:
    if settings.database_backend != "postgresql" or ConnectionPool is None:
        return None
    return ConnectionPool(
        conninfo=settings.normalized_database_url,
        min_size=max(1, settings.db_pool_min_size),
        max_size=max(settings.db_pool_min_size, settings.db_pool_max_size),
        timeout=max(1, settings.db_pool_timeout_seconds),
        kwargs={"row_factory": dict_row},
        open=True,
    )


def init_connection_pool() -> ConnectionPool | None:
    global _PG_POOL
    if settings.database_backend != "postgresql":
        return None
    with _POOL_LOCK:
        if _PG_POOL is None:
            _PG_POOL = _build_pg_pool()
    return _PG_POOL


def close_connection_pool() -> None:
    global _PG_POOL
    with _POOL_LOCK:
        if _PG_POOL is not None:
            _PG_POOL.close()
            _PG_POOL = None


def get_pool_stats() -> dict[str, int | str]:
    if settings.database_backend != "postgresql":
        return {"backend": settings.database_backend, "pooling": "disabled"}
    pool = init_connection_pool()
    if pool is None:
        return {"backend": settings.database_backend, "pooling": "unavailable"}
    return {
        "backend": settings.database_backend,
        "pooling": "enabled",
        "min_size": settings.db_pool_min_size,
        "max_size": settings.db_pool_max_size,
        "current_size": pool.get_stats().get("pool_size", 0),
        "available": pool.get_stats().get("pool_available", 0),
        "checked_out": pool.get_stats().get("requests_num", 0),
    }


class DBConnection:
    def __init__(self, backend: str, connection: Any, releaser: Callable[[Any], None] | None = None):
        self.backend = backend
        self._connection = connection
        self._releaser = releaser

    def execute(self, sql: str, params: Iterable = ()):
        if isinstance(sql, str) and "CREATE" in sql.upper() and "INDEX" in sql.upper():
            _ensure_index_columns(self, sql)
        prepared_sql = _prepare_sql(sql, self.backend)
        return self._connection.execute(prepared_sql, tuple(params))

    def executemany(self, sql: str, params_seq: list[Iterable]):
        prepared_sql = _prepare_sql(sql, self.backend)
        params = [tuple(item) for item in params_seq]
        if self.backend == "postgresql":
            with self._connection.cursor() as cur:
                cur.executemany(prepared_sql, params)
            return
        return self._connection.executemany(prepared_sql, params)

    def executescript(self, script: str) -> None:
        _ensure_index_columns(self, script)
        if self.backend == "sqlite":
            self._connection.executescript(script)
            return
        for statement in _split_sql_statements(script):
            cleaned = statement.strip()
            if not cleaned or cleaned.upper().startswith("PRAGMA "):
                continue
            sql = _prepare_sql(cleaned, self.backend)
            with self._connection.cursor() as cur:
                cur.execute(sql)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        if self._releaser is not None:
            self._releaser(self._connection)
            return
        self._connection.close()

    def __enter__(self) -> "DBConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()



def _ensure_index_columns(conn: DBConnection, script: str) -> None:
    """Best-effort guard for versioned DDL that adds indexes before columns."""
    for match in re.finditer(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+IF\s+NOT\s+EXISTS\s+[A-Za-z_][A-Za-z0-9_]*\s+ON\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)",
        script,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        table = match.group(1)
        if not table_exists(conn, table):
            continue
        for raw_term in match.group(2).split(","):
            term = raw_term.strip()
            if not term or "(" in term:
                continue
            column = term.split()[0].strip('"')
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", column):
                continue
            if column.lower() in {"asc", "desc", "nulls", "where"}:
                continue
            if not has_column(conn, table, column):
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")


def get_db_path() -> str:
    path = settings.sqlite_path
    if path.startswith("./"):
        return str((Path(__file__).resolve().parents[1] / path[2:]).resolve())
    return path


def _split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    escape_next = False
    for char in script:
        if escape_next:
            current.append(char)
            escape_next = False
            continue
        if char == "\\":
            current.append(char)
            escape_next = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            continue
        current.append(char)
    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def _convert_qmark_to_percent_s(sql: str) -> str:
    chunks = sql.split("?")
    if len(chunks) == 1:
        return sql
    return "%s".join(chunks)


def _prepare_sql(sql: str, backend: str) -> str:
    cleaned = sql.strip()
    if backend == "postgresql":
        if cleaned.upper().startswith("PRAGMA "):
            return "SELECT 1"
        return _convert_qmark_to_percent_s(sql)
    return sql


def get_connection() -> DBConnection:
    if settings.database_backend == "sqlite":
        conn = sqlite3.connect(get_db_path(), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        return DBConnection("sqlite", conn)

    if psycopg is None:  # pragma: no cover - triggered only when postgres env is used without dependency installed
        raise RuntimeError(
            "PostgreSQL support requires psycopg. Install dependencies from backend/requirements.txt before running in production."
        )

    pool = init_connection_pool()
    if pool is not None:
        conn = pool.getconn()
        return DBConnection("postgresql", conn, releaser=pool.putconn)

    conn = psycopg.connect(settings.normalized_database_url, row_factory=dict_row)
    return DBConnection("postgresql", conn)


def _column_exists(conn: DBConnection, table: str, column: str) -> bool:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column for row in rows)
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



def has_column(conn: DBConnection, table: str, column: str) -> bool:
    return _column_exists(conn, table, column)


def table_exists(conn: DBConnection, table: str) -> bool:
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


def migration_status(conn: DBConnection) -> dict[str, object]:
    from .migrations import migration_status as _migration_status

    return _migration_status(conn)


def init_db() -> None:
    if settings.database_backend == "sqlite":
        Path(get_db_path()).parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        ensure_v9_schema(conn)

        from .migrations import apply_migrations

        apply_migrations(conn)

        ensure_world_class_schema(conn)
        ensure_world_class_plus_schema(conn)
        ensure_telemetry_schema(conn)
        ensure_backend_runtime_schema(conn)
        ensure_vertical_transaction_schema(conn)
        ensure_vertical_domain_schema(conn)
        ensure_talent_schema(conn)

        seed_default_alert_rules(conn)
        conn.commit()


def _normalize_row(row: Any) -> dict | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def fetch_one(conn: DBConnection, sql: str, params: Iterable = ()) -> dict | None:
    row = conn.execute(sql, tuple(params)).fetchone()
    return _normalize_row(row)


def fetch_all(conn: DBConnection, sql: str, params: Iterable = ()) -> list[dict]:
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [_normalize_row(row) or {} for row in rows]


def execute(conn: DBConnection, sql: str, params: Iterable = ()) -> None:
    conn.execute(sql, tuple(params))
    conn.commit()


def execute_many(conn: DBConnection, sql: str, params_seq: list[Iterable]) -> None:
    conn.executemany(sql, [tuple(item) for item in params_seq])
    conn.commit()
