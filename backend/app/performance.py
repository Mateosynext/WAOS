from __future__ import annotations

import time
from threading import Lock
from typing import Any

from .config import settings


def clamp_limit(value: int | None, *, default: int | None = None, max_value: int | None = None) -> int:
    requested = int(value or default or settings.default_page_size)
    upper_bound = int(max_value or settings.max_page_size)
    if requested < 1:
        return 1
    return min(requested, upper_bound)


def clamp_offset(value: int | None) -> int:
    requested = int(value or 0)
    return 0 if requested < 0 else requested


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._values: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            entry = self._values.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._values.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> Any:
        with self._lock:
            self._values[key] = (time.time() + self.ttl_seconds, value)
        return value

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in list(self._values.keys()):
                if key.startswith(prefix):
                    self._values.pop(key, None)
