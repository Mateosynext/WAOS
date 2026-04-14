from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..db import DBConnection, get_connection


@dataclass
class UnitOfWork:
    """Explicit request-scoped transactional boundary for application services."""

    conn: DBConnection | None = field(default=None, init=False)
    _context: Any = field(default=None, init=False, repr=False)

    def __enter__(self) -> "UnitOfWork":
        self._context = get_connection()
        self.conn = self._context.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._context is None:
            return
        self._context.__exit__(exc_type, exc, tb)
        self._context = None
        self.conn = None

    def commit(self) -> None:
        if self.conn is not None:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn is not None:
            self.conn.rollback()
