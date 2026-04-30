from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Iterable

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def to_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return "{}"

def from_json(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return {} if default is None else default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return {} if default is None else default

def execute(conn, sql: str, params: Iterable[Any] = ()) -> None:
    conn.execute(sql, tuple(params or ()))

def fetch_one(conn, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    row = conn.execute(sql, tuple(params or ())).fetchone()
    if row is None:
        return None
    return dict(row) if not isinstance(row, dict) else row

def fetch_all(conn, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    rows = conn.execute(sql, tuple(params or ())).fetchall()
    return [dict(row) if not isinstance(row, dict) else row for row in rows]

def table_exists(conn, table: str) -> bool:
    backend = getattr(conn, "backend", "sqlite")
    if backend == "sqlite":
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        return bool(row)
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = ? LIMIT 1",
        (table,),
    ).fetchone()
    return bool(row)

def has_column(conn, table: str, column: str) -> bool:
    backend = getattr(conn, "backend", "sqlite")
    if backend == "sqlite":
        return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})").fetchall())
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = ? AND column_name = ? LIMIT 1",
        (table, column),
    ).fetchone()
    return bool(row)

def _ensure_table(conn, sql: str) -> None:
    conn.executescript(sql)

def ensure_world_class_schema(conn) -> None:
    _ensure_table(conn, """
    CREATE TABLE IF NOT EXISTS trace_spans (
        trace_id TEXT NOT NULL,
        span_id TEXT NOT NULL,
        parent_span_id TEXT,
        name TEXT NOT NULL,
        organization_id TEXT,
        bot_id TEXT,
        request_id TEXT,
        correlation_id TEXT,
        status TEXT NOT NULL DEFAULT 'running',
        attributes_json TEXT NOT NULL DEFAULT '{}',
        started_at TEXT NOT NULL,
        finished_at TEXT,
        PRIMARY KEY (trace_id, span_id)
    );
    CREATE TABLE IF NOT EXISTS ai_cache (
        cache_key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS ai_usage_events (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        bot_id TEXT,
        model TEXT,
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0,
        cost_estimate REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS memory_episodes (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        bot_id TEXT,
        contact_id TEXT,
        summary TEXT NOT NULL DEFAULT '',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS memory_vectors (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        bot_id TEXT,
        contact_id TEXT,
        text TEXT NOT NULL DEFAULT '',
        vector_json TEXT NOT NULL DEFAULT '[]',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS knowledge_embeddings (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        bot_id TEXT,
        source_id TEXT,
        text TEXT NOT NULL DEFAULT '',
        vector_json TEXT NOT NULL DEFAULT '[]',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS conversation_checkpoints (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        bot_id TEXT,
        conversation_id TEXT,
        summary TEXT NOT NULL DEFAULT '',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS dead_letter_events (
        id TEXT PRIMARY KEY,
        topic TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{}',
        error TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS revenue_events (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        bot_id TEXT,
        amount REAL NOT NULL DEFAULT 0,
        currency TEXT NOT NULL DEFAULT 'MXN',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS circuit_breakers (
        name TEXT PRIMARY KEY,
        state TEXT NOT NULL DEFAULT 'closed',
        failure_count INTEGER NOT NULL DEFAULT 0,
        opened_at TEXT,
        updated_at TEXT NOT NULL
    );
    """)

def start_trace_span(conn, *, trace_id: str, span_id: str, parent_span_id: str | None = None, name: str = "", organization_id: str | None = None, bot_id: str | None = None, request_id: str | None = None, correlation_id: str | None = None, attributes: dict[str, Any] | None = None, **_: Any) -> dict[str, Any]:
    ensure_world_class_schema(conn)
    conn.execute(
        """INSERT OR REPLACE INTO trace_spans
        (trace_id, span_id, parent_span_id, name, organization_id, bot_id, request_id, correlation_id, status, attributes_json, started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)""",
        (trace_id, span_id, parent_span_id, name or span_id, organization_id, bot_id, request_id, correlation_id, to_json(attributes or {}), _now()),
    )
    return {"trace_id": trace_id, "span_id": span_id, "status": "running"}

def finish_trace_span(conn, *, trace_id: str, span_id: str, status: str = "ok", attributes: dict[str, Any] | None = None, **_: Any) -> None:
    ensure_world_class_schema(conn)
    conn.execute(
        "UPDATE trace_spans SET status = ?, attributes_json = ?, finished_at = ? WHERE trace_id = ? AND span_id = ?",
        (status, to_json(attributes or {}), _now(), trace_id, span_id),
    )

def trace_timeline(conn, *, trace_id: str | None = None, limit: int = 100, **_: Any) -> list[dict[str, Any]]:
    ensure_world_class_schema(conn)
    if trace_id:
        return fetch_all(conn, "SELECT * FROM trace_spans WHERE trace_id = ? ORDER BY started_at DESC LIMIT ?", (trace_id, limit))
    return fetch_all(conn, "SELECT * FROM trace_spans ORDER BY started_at DESC LIMIT ?", (limit,))

def sparse_vector_from_text(text: str, *, dimensions: int = 64) -> list[float]:
    buckets = [0.0] * max(8, int(dimensions))
    for token in str(text or "").lower().split():
        digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        buckets[digest % len(buckets)] += 1.0
    norm = math.sqrt(sum(v * v for v in buckets)) or 1.0
    return [v / norm for v in buckets]

def vector_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    av = list(a or [])
    bv = list(b or [])
    if not av or not bv:
        return 0.0
    size = min(len(av), len(bv))
    dot = sum(av[i] * bv[i] for i in range(size))
    an = math.sqrt(sum(x * x for x in av)) or 1.0
    bn = math.sqrt(sum(x * x for x in bv)) or 1.0
    return float(dot / (an * bn))

def compress_prompt_payload(payload: Any, *, max_chars: int = 4000, **_: Any) -> str:
    text = payload if isinstance(payload, str) else to_json(payload)
    return text[:max(200, int(max_chars))]

def choose_model(*_: Any, **kwargs: Any) -> str:
    return str(kwargs.get("model") or kwargs.get("default_model") or "gpt-5")

def lookup_ai_cache(conn, cache_key: str, **_: Any) -> Any:
    ensure_world_class_schema(conn)
    row = fetch_one(conn, "SELECT value_json FROM ai_cache WHERE cache_key = ?", (cache_key,))
    return from_json(row["value_json"]) if row else None

def store_ai_cache(conn, cache_key: str, value: Any, **_: Any) -> None:
    ensure_world_class_schema(conn)
    conn.execute("INSERT OR REPLACE INTO ai_cache (cache_key, value_json, created_at) VALUES (?, ?, ?)", (cache_key, to_json(value), _now()))

def cache_efficiency_overview(*_: Any, **__: Any) -> dict[str, Any]:
    return {"enabled": True, "mode": "rc_compatibility", "hit_rate": None}

def circuit_allow(*_: Any, **__: Any) -> bool:
    return True

def circuit_record_failure(*_: Any, **__: Any) -> None:
    return None

def circuit_record_success(*_: Any, **__: Any) -> None:
    return None

def circuit_breaker_summary(*_: Any, **__: Any) -> dict[str, Any]:
    return {"enabled": True, "open_circuits": 0, "mode": "rc_compatibility"}

def record_ai_usage(conn=None, **kwargs: Any) -> dict[str, Any]:
    if conn is not None:
        ensure_world_class_schema(conn)
        event_id = kwargs.get("id") or hashlib.sha256(to_json(kwargs).encode("utf-8")).hexdigest()[:24]
        conn.execute(
            "INSERT OR REPLACE INTO ai_usage_events (id, organization_id, bot_id, model, input_tokens, output_tokens, cost_estimate, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, kwargs.get("organization_id"), kwargs.get("bot_id"), kwargs.get("model"), int(kwargs.get("input_tokens") or 0), int(kwargs.get("output_tokens") or 0), float(kwargs.get("cost_estimate") or 0), _now()),
        )
        return {"id": event_id}
    return {"id": None}

def summarize_ai_usage(*_: Any, **__: Any) -> dict[str, Any]:
    return {"total_cost_estimate": 0, "events": 0, "mode": "rc_compatibility"}

def append_memory_episode(conn=None, **kwargs: Any) -> dict[str, Any]:
    episode_id = kwargs.get("id") or hashlib.sha256(to_json(kwargs).encode("utf-8")).hexdigest()[:24]
    if conn is not None:
        ensure_world_class_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO memory_episodes (id, organization_id, bot_id, contact_id, summary, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (episode_id, kwargs.get("organization_id"), kwargs.get("bot_id"), kwargs.get("contact_id"), kwargs.get("summary") or kwargs.get("text") or "", to_json(kwargs.get("metadata") or {}), _now()),
        )
    return {"id": episode_id, "status": "stored"}

def upsert_memory_vector(conn=None, **kwargs: Any) -> dict[str, Any]:
    vector_id = kwargs.get("id") or hashlib.sha256(to_json(kwargs).encode("utf-8")).hexdigest()[:24]
    if conn is not None:
        ensure_world_class_schema(conn)
        text = kwargs.get("text") or ""
        conn.execute(
            "INSERT OR REPLACE INTO memory_vectors (id, organization_id, bot_id, contact_id, text, vector_json, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (vector_id, kwargs.get("organization_id"), kwargs.get("bot_id"), kwargs.get("contact_id"), text, to_json(kwargs.get("vector") or sparse_vector_from_text(text)), to_json(kwargs.get("metadata") or {}), _now()),
        )
    return {"id": vector_id}

def index_bot_knowledge(conn=None, **kwargs: Any) -> dict[str, Any]:
    item_id = kwargs.get("id") or hashlib.sha256(to_json(kwargs).encode("utf-8")).hexdigest()[:24]
    if conn is not None:
        ensure_world_class_schema(conn)
        text = kwargs.get("text") or kwargs.get("content") or ""
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_embeddings (id, organization_id, bot_id, source_id, text, vector_json, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (item_id, kwargs.get("organization_id"), kwargs.get("bot_id"), kwargs.get("source_id"), text, to_json(kwargs.get("vector") or sparse_vector_from_text(text)), to_json(kwargs.get("metadata") or {}), _now()),
        )
    return {"id": item_id}

def search_memory_vectors(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return []

def search_memory_episodes(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return []

def search_knowledge_embeddings(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return []

def search_knowledge_embeddings_cached(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return search_knowledge_embeddings(*args, **kwargs)

def recent_checkpoints(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return []

def maybe_create_conversation_checkpoint(*_: Any, **__: Any) -> dict[str, Any] | None:
    return None

def memory_runtime_overview(*_: Any, **__: Any) -> dict[str, Any]:
    return {"enabled": True, "mode": "rc_compatibility"}

def record_revenue_event(conn=None, **kwargs: Any) -> dict[str, Any]:
    event_id = kwargs.get("id") or hashlib.sha256(to_json(kwargs).encode("utf-8")).hexdigest()[:24]
    if conn is not None:
        ensure_world_class_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO revenue_events (id, organization_id, bot_id, amount, currency, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, kwargs.get("organization_id"), kwargs.get("bot_id"), float(kwargs.get("amount") or 0), kwargs.get("currency") or "MXN", to_json(kwargs.get("metadata") or {}), _now()),
        )
    return {"id": event_id}

def revenue_overview(*_: Any, **__: Any) -> dict[str, Any]:
    return {"amount": 0, "currency": "MXN", "mode": "rc_compatibility"}

def search_technical_logs(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return []

def record_dead_letter_event(conn=None, **kwargs: Any) -> dict[str, Any]:
    event_id = kwargs.get("id") or hashlib.sha256(to_json(kwargs).encode("utf-8")).hexdigest()[:24]
    if conn is not None:
        ensure_world_class_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO dead_letter_events (id, topic, payload_json, error, created_at) VALUES (?, ?, ?, ?, ?)",
            (event_id, kwargs.get("topic") or "unknown", to_json(kwargs.get("payload") or {}), kwargs.get("error"), _now()),
        )
    return {"id": event_id}

def consume_retry_budget(*_: Any, **__: Any) -> bool:
    return True
