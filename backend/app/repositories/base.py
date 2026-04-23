from __future__ import annotations

from typing import Any, Iterable, Protocol


class ConnectionLike(Protocol):
    def execute(self, *args: Any, **kwargs: Any) -> Any: ...
    def executescript(self, *args: Any, **kwargs: Any) -> Any: ...
    def commit(self) -> None: ...


def _normalize_row(row: Any) -> dict | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def fetch_one(conn: ConnectionLike, sql: str, params: Iterable = ()) -> dict | None:
    row = conn.execute(sql, tuple(params)).fetchone()
    return _normalize_row(row)


def fetch_all(conn: ConnectionLike, sql: str, params: Iterable = ()) -> list[dict]:
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [_normalize_row(row) or {} for row in rows]


def execute(conn: ConnectionLike, sql: str, params: Iterable = ()) -> None:
    conn.execute(sql, tuple(params))
    conn.commit()
