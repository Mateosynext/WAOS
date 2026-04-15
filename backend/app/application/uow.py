from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from ..db import DBConnection, get_connection

TransactionMode = Literal["read", "write"]


@dataclass
class UnitOfWork:
    """Explicit request-scoped transactional boundary for application services."""

    mode: TransactionMode = "write"
    conn: DBConnection | None = field(default=None, init=False)
    _context: Any = field(default=None, init=False, repr=False)

    def __enter__(self) -> "UnitOfWork":
        self._context = get_connection()
        self.conn = self._context.__enter__()
        if self.mode == "read" and self.conn.backend == "postgresql":
            try:
                self.conn.execute("SET TRANSACTION READ ONLY")
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._context is None:
            return
        if self.mode == "read" and exc_type is None:
            self.rollback()
            self.conn.close() if self.conn is not None else None
            self._context = None
            self.conn = None
            return
        self._context.__exit__(exc_type, exc, tb)
        self._context = None
        self.conn = None

    def commit(self) -> None:
        if self.mode == "read":
            raise RuntimeError("Read-only unit of work cannot commit")
        if self.conn is not None:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn is not None:
            self.conn.rollback()
