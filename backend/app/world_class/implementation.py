from __future__ import annotations

import math
from collections import Counter
from typing import Any

from ..utils import add_minutes, add_seconds, from_json, hash_value, new_id, parse_iso, to_json, utcnow_iso
from ..runtime_schema_guards import assert_schema_ready



def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        keys = getattr(row, 'keys', lambda: [])()
        return {key: row[key] for key in keys}


def execute(conn, sql: str, params: Any = ()) -> None:
    conn.execute(sql, params)


def fetch_one(conn, sql: str, params: Any = ()) -> dict[str, Any] | None:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def fetch_all(conn, sql: str, params: Any = ()) -> list[dict[str, Any]]:
    return [_row_to_dict(row) for row in conn.execute(sql, params).fetchall()]


def table_exists(conn, table: str) -> bool:
    backend = getattr(conn, 'backend', 'sqlite')
    if backend == 'sqlite':
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


def has_column(conn, table: str, column: str) -> bool:
    backend = getattr(conn, 'backend', 'sqlite')
    if backend == 'sqlite':
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
_STOP_WORDS = {
    'a','al','algo','and','are','as','at','be','con','de','del','do','el','en','es','esta','este','for','from','hay',
    'hola','i','in','is','it','la','las','lo','los','me','mi','my','no','of','or','para','por','que','se','si',
    'so','su','te','the','to','tu','un','una','we','y','yo','your'
}


def ensure_world_class_schema(conn) -> None:
    assert_schema_ready(
        conn,
        owner="migrations.py / platform_schema_migration.py",
        tables=(
            "provider_circuit_breakers",
            "retry_budget_windows",
            "dead_letter_events",
            "ai_cache_entries",
            "ai_usage_events",
            "memory_vectors",
            "memory_episodes",
            "knowledge_query_cache",
            "knowledge_embeddings",
            "trace_spans",
            "conversation_checkpoints",
            "revenue_optimization_events",
            "omnichannel_identities",
            "channel_events",
            "shadow_runs",
            "prompt_artifacts",
            "public_api_credentials",
            "otel_span_exports",
        ),
    )


def _normalize_text(text: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(text or "")).split())



def sparse_vector_from_text(text: str, *, max_terms: int = 24) -> dict[str, float]:
    normalized = _normalize_text(text)
    if not normalized:
        return {}
    tokens = [token for token in normalized.split() if len(token) > 2 and token not in _STOP_WORDS]
    if not tokens:
        return {}
    counts = Counter(tokens)
    most_common = counts.most_common(max_terms)
    total = sum(value for _, value in most_common) or 1
    return {token: round(value / total, 6) for token, value in most_common}



def vector_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(left.get(key, 0.0) * right.get(key, 0.0) for key in set(left) | set(right))
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)



def prompt_signature(payload: Any) -> tuple[str, str, dict[str, float]]:
    if isinstance(payload, str):
        canonical = _normalize_text(payload)
    else:
        canonical = _normalize_text(to_json(payload))
    return canonical, hash_value(canonical), sparse_vector_from_text(canonical)



def compress_prompt_payload(payload: dict[str, Any], *, char_budget: int = 2400) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = to_json(payload)
    if len(raw) <= char_budget:
        return payload, {"compressed": False, "original_chars": len(raw), "final_chars": len(raw)}
    compressed = dict(payload)
    recent = list(compressed.get('recent_conversation_context') or [])[-4:]
    compact_recent = []
    for item in recent:
        compact_recent.append({
            'direction': item.get('direction'),
            'body': str(item.get('body') or '')[:160],
        })
    compressed['recent_conversation_context'] = compact_recent
    if 'business_knowledge' in compressed:
        bk = dict(compressed.get('business_knowledge') or {})
        for key in ['faqs', 'services', 'prices']:
            items = bk.get(key)
            if isinstance(items, list):
                bk[key] = items[:8]
        compressed['business_knowledge'] = bk
    if 'memory' in compressed and isinstance(compressed['memory'], dict):
        memory = dict(compressed['memory'])
        if memory.get('summary'):
            memory['summary'] = str(memory['summary'])[:280]
        compressed['memory'] = memory
    final = to_json(compressed)
    return compressed, {
        'compressed': True,
        'original_chars': len(raw),
        'final_chars': len(final),
        'compression_ratio': round(len(final) / max(1, len(raw)), 4),
    }



def choose_model(default_model: str, *, operation: str, input_text: str, classification: dict[str, Any] | None = None) -> str:
    import os

    fast_model = os.getenv('OPENAI_FAST_MODEL', default_model)
    complex_model = os.getenv('OPENAI_COMPLEX_MODEL', default_model)
    text = str(input_text or '')
    classification = classification or {}
    if operation == 'classification' and len(text) < 120:
        return fast_model
    if operation == 'generation' and classification.get('intent') in {'greeting', 'faq'} and len(text) < 180:
        return fast_model
    if operation == 'generation' and (classification.get('urgency_level') in {'high', 'critical'} or len(text) > 350):
        return complex_model
    return default_model



def _cost_rates(model: str) -> tuple[float, float]:
    model_l = str(model or '').lower()
    if 'mini' in model_l or 'nano' in model_l:
        return (0.00000025, 0.000001)
    if 'gpt-4' in model_l or 'o3' in model_l:
        return (0.000005, 0.000015)
    return (0.00000125, 0.000005)



def estimate_cost(model: str, *, prompt_tokens: int, completion_tokens: int) -> float:
    in_rate, out_rate = _cost_rates(model)
    return round((prompt_tokens * in_rate) + (completion_tokens * out_rate), 6)



def lookup_ai_cache(conn, *, organization_id: str | None, bot_id: str | None, cache_type: str, payload: Any, min_similarity: float = 0.92) -> dict[str, Any] | None:
    if not table_exists(conn, 'ai_cache_entries'):
        return None
    canonical, prompt_hash, vector = prompt_signature(payload)
    now = utcnow_iso()
    exact = fetch_one(
        conn,
        """
        SELECT * FROM ai_cache_entries
        WHERE prompt_hash = ? AND cache_type = ? AND COALESCE(bot_id,'') = COALESCE(?, '')
          AND (expires_at IS NULL OR expires_at = '' OR expires_at >= ?)
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (prompt_hash, cache_type, bot_id, now),
    )
    if exact:
        execute(conn, "UPDATE ai_cache_entries SET hit_count = hit_count + 1, updated_at = ? WHERE id = ?", (now, exact['id']))
        metadata = from_json(exact.get('metadata_json'), {})
        return {'match': 'exact', 'row': exact, 'metadata': metadata, 'similarity': 1.0}
    rows = fetch_all(
        conn,
        """
        SELECT * FROM ai_cache_entries
        WHERE cache_type = ? AND COALESCE(bot_id,'') = COALESCE(?, '')
          AND (expires_at IS NULL OR expires_at = '' OR expires_at >= ?)
        ORDER BY updated_at DESC
        LIMIT 50
        """,
        (cache_type, bot_id, now),
    )
    best: dict[str, Any] | None = None
    for row in rows:
        metadata = from_json(row.get('metadata_json'), {})
        candidate_vector = metadata.get('vector') or sparse_vector_from_text(row.get('canonical_prompt') or '')
        similarity = vector_similarity(vector, candidate_vector)
        if similarity >= min_similarity and (best is None or similarity > best['similarity']):
            best = {'match': 'semantic', 'row': row, 'metadata': metadata, 'similarity': similarity}
    if best:
        execute(conn, "UPDATE ai_cache_entries SET hit_count = hit_count + 1, updated_at = ? WHERE id = ?", (now, best['row']['id']))
    return best



def store_ai_cache(conn, *, organization_id: str | None, bot_id: str | None, cache_scope: str, cache_type: str, payload: Any, response_text: str | None = None, response_json: dict[str, Any] | None = None, ttl_seconds: int = 3600) -> dict[str, Any]:
    canonical, prompt_hash, vector = prompt_signature(payload)
    now = utcnow_iso()
    cache_key = hash_value(f"{cache_type}:{bot_id or ''}:{prompt_hash}")
    expires_at = add_seconds(now, ttl_seconds) if ttl_seconds > 0 else None
    metadata = {'response_json': response_json or {}, 'vector': vector}
    existing = fetch_one(conn, 'SELECT * FROM ai_cache_entries WHERE cache_key = ?', (cache_key,))
    if existing:
        execute(conn, 'UPDATE ai_cache_entries SET canonical_prompt = ?, response_text = ?, metadata_json = ?, updated_at = ?, expires_at = ? WHERE id = ?', (canonical, response_text, to_json(metadata), now, expires_at, existing['id']))
        return fetch_one(conn, 'SELECT * FROM ai_cache_entries WHERE id = ?', (existing['id'],)) or {}
    row_id = new_id('aicache')
    execute(
        conn,
        'INSERT INTO ai_cache_entries (id, organization_id, bot_id, cache_scope, cache_type, cache_key, prompt_hash, canonical_prompt, response_text, metadata_json, hit_count, created_at, updated_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)',
        (row_id, organization_id, bot_id, cache_scope, cache_type, cache_key, prompt_hash, canonical, response_text, to_json(metadata), now, now, expires_at),
    )
    return fetch_one(conn, 'SELECT * FROM ai_cache_entries WHERE id = ?', (row_id,)) or {}



def record_ai_usage(conn, *, organization_id: str | None, bot_id: str | None, conversation_id: str | None, model: str, operation: str, prompt_tokens: int, completion_tokens: int, latency_ms: int | None, cache_hit: bool, fallback_source: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not table_exists(conn, 'ai_usage_events'):
        return {}
    row_id = new_id('aiuse')
    total_tokens = max(0, int(prompt_tokens or 0) + int(completion_tokens or 0))
    estimated_cost = estimate_cost(model, prompt_tokens=int(prompt_tokens or 0), completion_tokens=int(completion_tokens or 0))
    execute(
        conn,
        'INSERT INTO ai_usage_events (id, organization_id, bot_id, conversation_id, model, operation, prompt_tokens, completion_tokens, total_tokens, estimated_cost, latency_ms, cache_hit, fallback_source, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (row_id, organization_id, bot_id, conversation_id, model, operation, int(prompt_tokens or 0), int(completion_tokens or 0), total_tokens, estimated_cost, latency_ms, 1 if cache_hit else 0, fallback_source, to_json(metadata or {}), utcnow_iso()),
    )
    return fetch_one(conn, 'SELECT * FROM ai_usage_events WHERE id = ?', (row_id,)) or {}



def summarize_ai_usage(conn, *, organization_id: str | None = None, bot_id: str | None = None, limit: int = 500) -> dict[str, Any]:
    if not table_exists(conn, 'ai_usage_events'):
        return {'totals': {'events': 0, 'estimated_cost': 0.0, 'cache_hit_rate': 0.0}}
    clauses: list[str] = []
    params: list[Any] = []
    if organization_id:
        clauses.append('organization_id = ?')
        params.append(organization_id)
    if bot_id:
        clauses.append('bot_id = ?')
        params.append(bot_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = fetch_all(conn, f'SELECT * FROM ai_usage_events {where} ORDER BY created_at DESC LIMIT ?', (*params, limit))
    total_cost = round(sum(float(row.get('estimated_cost') or 0) for row in rows), 6)
    cache_hits = sum(1 for row in rows if int(row.get('cache_hit') or 0) == 1)
    latency_values = sorted(int(row.get('latency_ms') or 0) for row in rows if row.get('latency_ms') is not None)
    by_operation: dict[str, dict[str, Any]] = {}
    for row in rows:
        bucket = by_operation.setdefault(str(row.get('operation') or 'unknown'), {'events': 0, 'estimated_cost': 0.0, 'tokens': 0})
        bucket['events'] += 1
        bucket['estimated_cost'] = round(bucket['estimated_cost'] + float(row.get('estimated_cost') or 0), 6)
        bucket['tokens'] += int(row.get('total_tokens') or 0)
    return {
        'totals': {
            'events': len(rows),
            'estimated_cost': total_cost,
            'cache_hit_rate': round((cache_hits / len(rows)) * 100, 2) if rows else 0.0,
            'p95_latency_ms': latency_values[min(len(latency_values) - 1, int(len(latency_values) * 0.95))] if latency_values else None,
        },
        'operations': by_operation,
        'recent': rows[:20],
    }



def _load_circuit(conn, *, provider: str, circuit_key: str, failure_threshold: int) -> dict[str, Any] | None:
    row = fetch_one(conn, 'SELECT * FROM provider_circuit_breakers WHERE provider = ? AND circuit_key = ?', (provider, circuit_key))
    if row:
        return row
    row_id = new_id('cb')
    now = utcnow_iso()
    execute(
        conn,
        'INSERT INTO provider_circuit_breakers (id, provider, circuit_key, state, consecutive_failures, failure_threshold, opened_at, half_open_after, last_error, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, NULL, NULL, NULL, ?, ?, ?)',
        (row_id, provider, circuit_key, 'closed', failure_threshold, '{}', now, now),
    )
    return fetch_one(conn, 'SELECT * FROM provider_circuit_breakers WHERE id = ?', (row_id,))



def circuit_allow(conn, *, provider: str, circuit_key: str = 'default', failure_threshold: int = 3, open_minutes: int = 2) -> tuple[bool, dict[str, Any]]:
    if not table_exists(conn, 'provider_circuit_breakers'):
        return True, {'provider': provider, 'circuit_key': circuit_key, 'state': 'closed'}
    row = _load_circuit(conn, provider=provider, circuit_key=circuit_key, failure_threshold=failure_threshold) or {}
    state = str(row.get('state') or 'closed')
    now = utcnow_iso()
    if state == 'open':
        reopen_at = parse_iso(row.get('half_open_after'))
        if reopen_at and reopen_at > parse_iso(now):
            return False, row
        execute(conn, 'UPDATE provider_circuit_breakers SET state = ?, updated_at = ? WHERE id = ?', ('half_open', now, row['id']))
        row = fetch_one(conn, 'SELECT * FROM provider_circuit_breakers WHERE id = ?', (row['id'],)) or row
    return True, row



def circuit_record_success(conn, *, provider: str, circuit_key: str = 'default', metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    row = _load_circuit(conn, provider=provider, circuit_key=circuit_key, failure_threshold=3) or {}
    execute(conn, 'UPDATE provider_circuit_breakers SET state = ?, consecutive_failures = 0, opened_at = NULL, half_open_after = NULL, last_error = NULL, metadata_json = ?, updated_at = ? WHERE id = ?', ('closed', to_json(metadata or {}), utcnow_iso(), row['id']))
    return fetch_one(conn, 'SELECT * FROM provider_circuit_breakers WHERE id = ?', (row['id'],)) or {}



def circuit_record_failure(conn, *, provider: str, error_text: str, circuit_key: str = 'default', failure_threshold: int = 3, open_minutes: int = 2, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    row = _load_circuit(conn, provider=provider, circuit_key=circuit_key, failure_threshold=failure_threshold) or {}
    failures = int(row.get('consecutive_failures') or 0) + 1
    state = 'open' if failures >= int(row.get('failure_threshold') or failure_threshold) else 'closed'
    opened_at = utcnow_iso() if state == 'open' else None
    half_open_after = add_minutes(opened_at, open_minutes) if state == 'open' else None
    execute(conn, 'UPDATE provider_circuit_breakers SET state = ?, consecutive_failures = ?, opened_at = ?, half_open_after = ?, last_error = ?, metadata_json = ?, updated_at = ? WHERE id = ?', (state, failures, opened_at, half_open_after, error_text[:500], to_json(metadata or {}), utcnow_iso(), row['id']))
    return fetch_one(conn, 'SELECT * FROM provider_circuit_breakers WHERE id = ?', (row['id'],)) or {}



def circuit_breaker_summary(conn, *, provider: str | None = None) -> dict[str, Any]:
    if not table_exists(conn, 'provider_circuit_breakers'):
        return {'total': 0, 'open': 0, 'half_open': 0, 'closed': 0, 'items': []}
    if provider:
        rows = fetch_all(conn, 'SELECT * FROM provider_circuit_breakers WHERE provider = ? ORDER BY updated_at DESC', (provider,))
    else:
        rows = fetch_all(conn, 'SELECT * FROM provider_circuit_breakers ORDER BY updated_at DESC')
    return {
        'total': len(rows),
        'open': sum(1 for row in rows if row.get('state') == 'open'),
        'half_open': sum(1 for row in rows if row.get('state') == 'half_open'),
        'closed': sum(1 for row in rows if row.get('state') == 'closed'),
        'items': rows[:20],
    }



def consume_retry_budget(conn, *, provider: str, scope_key: str, max_retries: int = 5, window_seconds: int = 900, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not table_exists(conn, 'retry_budget_windows'):
        return {'allowed': True, 'remaining': max_retries}
    now = parse_iso(utcnow_iso())
    row = fetch_one(conn, 'SELECT * FROM retry_budget_windows WHERE provider = ? AND scope_key = ?', (provider, scope_key))
    if row:
        started = parse_iso(row.get('window_started_at'))
        expired = not started or not now or (now - started).total_seconds() > int(row.get('window_seconds') or window_seconds)
        if expired:
            execute(conn, 'UPDATE retry_budget_windows SET window_started_at = ?, retries_used = 0, window_seconds = ?, max_retries = ?, metadata_json = ?, updated_at = ? WHERE id = ?', (utcnow_iso(), window_seconds, max_retries, to_json(metadata or {}), utcnow_iso(), row['id']))
            row = fetch_one(conn, 'SELECT * FROM retry_budget_windows WHERE id = ?', (row['id'],))
    if not row:
        row_id = new_id('rb')
        execute(conn, 'INSERT INTO retry_budget_windows (id, provider, scope_key, window_started_at, window_seconds, max_retries, retries_used, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)', (row_id, provider, scope_key, utcnow_iso(), window_seconds, max_retries, to_json(metadata or {}), utcnow_iso(), utcnow_iso()))
        row = fetch_one(conn, 'SELECT * FROM retry_budget_windows WHERE id = ?', (row_id,))
    used = int(row.get('retries_used') or 0)
    if used >= int(row.get('max_retries') or max_retries):
        return {'allowed': False, 'remaining': 0, 'window': row}
    execute(conn, 'UPDATE retry_budget_windows SET retries_used = retries_used + 1, metadata_json = ?, updated_at = ? WHERE id = ?', (to_json(metadata or {}), utcnow_iso(), row['id']))
    current = fetch_one(conn, 'SELECT * FROM retry_budget_windows WHERE id = ?', (row['id'],)) or row
    remaining = max(0, int(current.get('max_retries') or max_retries) - int(current.get('retries_used') or 0))
    return {'allowed': True, 'remaining': remaining, 'window': current}



def record_dead_letter_event(conn, *, organization_id: str | None, channel: str, source_table: str, source_id: str, reason_code: str, payload_snapshot: dict[str, Any] | None = None, error_payload: dict[str, Any] | None = None, quarantine_minutes: int = 1440) -> dict[str, Any]:
    if not table_exists(conn, 'dead_letter_events'):
        return {}
    now = utcnow_iso()
    existing = fetch_one(conn, 'SELECT * FROM dead_letter_events WHERE source_table = ? AND source_id = ?', (source_table, source_id))
    if existing:
        execute(conn, 'UPDATE dead_letter_events SET organization_id = ?, channel = ?, reason_code = ?, payload_snapshot_json = ?, error_json = ?, replay_count = replay_count + 1, quarantined_until = ?, updated_at = ? WHERE id = ?', (organization_id, channel, reason_code, to_json(payload_snapshot or {}), to_json(error_payload or {}), add_minutes(now, quarantine_minutes), now, existing['id']))
        return fetch_one(conn, 'SELECT * FROM dead_letter_events WHERE id = ?', (existing['id'],)) or {}
    row_id = new_id('dlq')
    execute(conn, 'INSERT INTO dead_letter_events (id, organization_id, channel, source_table, source_id, reason_code, payload_snapshot_json, error_json, quarantined_until, replay_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)', (row_id, organization_id, channel, source_table, source_id, reason_code, to_json(payload_snapshot or {}), to_json(error_payload or {}), add_minutes(now, quarantine_minutes), now, now))
    return fetch_one(conn, 'SELECT * FROM dead_letter_events WHERE id = ?', (row_id,)) or {}



def upsert_memory_vector(conn, *, organization_id: str, contact_id: str | None, bot_id: str | None, scope: str, content_text: str, metadata: dict[str, Any] | None = None, score: float = 0.0) -> dict[str, Any]:
    if not table_exists(conn, 'memory_vectors'):
        return {}
    vector = sparse_vector_from_text(content_text)
    now = utcnow_iso()
    existing = fetch_one(conn, 'SELECT * FROM memory_vectors WHERE organization_id = ? AND COALESCE(contact_id,\'\') = COALESCE(?,\'\') AND COALESCE(bot_id,\'\') = COALESCE(?,\'\') AND scope = ? ORDER BY updated_at DESC LIMIT 1', (organization_id, contact_id, bot_id, scope))
    if existing:
        execute(conn, 'UPDATE memory_vectors SET content_text = ?, vector_json = ?, metadata_json = ?, score = ?, updated_at = ? WHERE id = ?', (content_text, to_json(vector), to_json(metadata or {}), score, now, existing['id']))
        return fetch_one(conn, 'SELECT * FROM memory_vectors WHERE id = ?', (existing['id'],)) or {}
    row_id = new_id('memv')
    execute(conn, 'INSERT INTO memory_vectors (id, organization_id, contact_id, bot_id, scope, content_text, vector_json, metadata_json, score, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (row_id, organization_id, contact_id, bot_id, scope, content_text, to_json(vector), to_json(metadata or {}), score, now, now))
    return fetch_one(conn, 'SELECT * FROM memory_vectors WHERE id = ?', (row_id,)) or {}



def search_memory_vectors(conn, *, organization_id: str, contact_id: str | None, bot_id: str | None, query: str, include_cross_bot: bool = True, limit: int = 5) -> list[dict[str, Any]]:
    if not table_exists(conn, 'memory_vectors'):
        return []
    query_vector = sparse_vector_from_text(query)
    if bot_id and not include_cross_bot:
        rows = fetch_all(conn, 'SELECT * FROM memory_vectors WHERE organization_id = ? AND COALESCE(contact_id,\'\') = COALESCE(?,\'\') AND COALESCE(bot_id,\'\') = COALESCE(?,\'\') ORDER BY updated_at DESC LIMIT 50', (organization_id, contact_id, bot_id))
    else:
        rows = fetch_all(conn, 'SELECT * FROM memory_vectors WHERE organization_id = ? AND COALESCE(contact_id,\'\') = COALESCE(?,\'\') ORDER BY updated_at DESC LIMIT 80', (organization_id, contact_id))
    scored: list[dict[str, Any]] = []
    for row in rows:
        vector = from_json(row.get('vector_json'), {})
        similarity = vector_similarity(query_vector, vector)
        if similarity <= 0:
            continue
        scored.append({**row, 'similarity': round(similarity, 4), 'metadata': from_json(row.get('metadata_json'), {})})
    scored.sort(key=lambda item: (-float(item.get('similarity') or 0), item.get('updated_at') or ''), reverse=False)
    scored = sorted(scored, key=lambda item: float(item.get('similarity') or 0), reverse=True)
    return scored[:limit]




def append_memory_episode(conn, *, organization_id: str, contact_id: str | None, bot_id: str | None, conversation_id: str | None, source_message_id: str | None, episode_type: str, summary_text: str, metadata: dict[str, Any] | None = None, score: float = 0.0) -> dict[str, Any]:
    if not table_exists(conn, 'memory_episodes') or not str(summary_text or '').strip():
        return {}
    now = utcnow_iso()
    payload = dict(metadata or {})
    session_key = str(payload.get('session_key') or f"{contact_id or 'anon'}:{now[:10]}")
    row_id = new_id('mep')
    execute(
        conn,
        'INSERT INTO memory_episodes (id, organization_id, contact_id, bot_id, conversation_id, source_message_id, episode_type, session_key, summary_text, vector_json, metadata_json, score, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (row_id, organization_id, contact_id, bot_id, conversation_id, source_message_id, episode_type, session_key, summary_text, to_json(sparse_vector_from_text(summary_text)), to_json(payload), score, now, now),
    )
    return fetch_one(conn, 'SELECT * FROM memory_episodes WHERE id = ?', (row_id,)) or {}



def search_memory_episodes(conn, *, organization_id: str, contact_id: str | None, bot_id: str | None, query: str, include_cross_bot: bool = True, limit: int = 5, hours_window: int | None = None) -> list[dict[str, Any]]:
    if not table_exists(conn, 'memory_episodes'):
        return []
    if bot_id and not include_cross_bot:
        rows = fetch_all(conn, "SELECT * FROM memory_episodes WHERE organization_id = ? AND COALESCE(contact_id,'') = COALESCE(?,'') AND COALESCE(bot_id,'') = COALESCE(?,'') ORDER BY updated_at DESC LIMIT 120", (organization_id, contact_id, bot_id))
    else:
        rows = fetch_all(conn, "SELECT * FROM memory_episodes WHERE organization_id = ? AND COALESCE(contact_id,'') = COALESCE(?,'') ORDER BY updated_at DESC LIMIT 180", (organization_id, contact_id))
    query_vector = sparse_vector_from_text(query)
    now = parse_iso(utcnow_iso())
    scored: list[dict[str, Any]] = []
    for row in rows:
        if hours_window:
            updated_at = parse_iso(row.get('updated_at'))
            if now and updated_at and (now - updated_at).total_seconds() > (int(hours_window) * 3600):
                continue
        similarity = vector_similarity(query_vector, from_json(row.get('vector_json'), {}))
        if similarity <= 0:
            continue
        scored.append({**row, 'similarity': round(similarity, 4), 'metadata': from_json(row.get('metadata_json'), {})})
    scored.sort(key=lambda item: (float(item.get('similarity') or 0), item.get('updated_at') or ''), reverse=True)
    return scored[:limit]



def memory_runtime_overview(conn, *, organization_id: str | None = None, bot_id: str | None = None) -> dict[str, Any]:
    episode_clauses: list[str] = []
    episode_params: list[Any] = []
    checkpoint_clauses: list[str] = []
    checkpoint_params: list[Any] = []
    if organization_id:
        episode_clauses.append('organization_id = ?')
        checkpoint_clauses.append('organization_id = ?')
        episode_params.append(organization_id)
        checkpoint_params.append(organization_id)
    if bot_id:
        episode_clauses.append("(bot_id = ? OR bot_id IS NULL OR bot_id = '')")
        checkpoint_clauses.append('bot_id = ?')
        episode_params.append(bot_id)
        checkpoint_params.append(bot_id)
    episode_where = f"WHERE {' AND '.join(episode_clauses)}" if episode_clauses else ''
    checkpoint_where = f"WHERE {' AND '.join(checkpoint_clauses)}" if checkpoint_clauses else ''
    episodes = fetch_all(conn, f'SELECT * FROM memory_episodes {episode_where} ORDER BY updated_at DESC LIMIT 200', tuple(episode_params)) if table_exists(conn, 'memory_episodes') else []
    checkpoints = fetch_all(conn, f'SELECT * FROM conversation_checkpoints {checkpoint_where} ORDER BY created_at DESC LIMIT 200', tuple(checkpoint_params)) if table_exists(conn, 'conversation_checkpoints') else []
    cross_bot = 0
    for row in episodes:
        metadata = from_json(row.get('metadata_json'), {})
        if metadata.get('bot_scope') == 'cross_bot' or metadata.get('cross_bot'):
            cross_bot += 1
    return {
        'totals': {
            'episodes': len(episodes),
            'checkpoints': len(checkpoints),
            'cross_bot_episodes': cross_bot,
        },
        'recent_episodes': [{**row, 'metadata': from_json(row.get('metadata_json'), {})} for row in episodes[:10]],
        'recent_checkpoints': checkpoints[:10],
    }



def index_bot_knowledge(conn, *, organization_id: str, bot_id: str, bot_config: dict[str, Any]) -> list[dict[str, Any]]:
    if not table_exists(conn, 'knowledge_embeddings'):
        return []
    business = dict(bot_config.get('business_knowledge') or {})
    items: list[tuple[str, str, str, dict[str, Any]]] = []
    if business.get('hours'):
        items.append(('hours', 'hours', str(business.get('hours')), {}))
    if business.get('location'):
        items.append(('location', 'location', str(business.get('location')), {}))
    for idx, faq in enumerate(business.get('faqs') or []):
        if isinstance(faq, dict):
            items.append(('faq', f'faq_{idx}', f"{faq.get('q')}: {faq.get('a')}", {'question': faq.get('q')}))
        else:
            items.append(('faq', f'faq_{idx}', str(faq), {}))
    for idx, service in enumerate(business.get('services') or []):
        items.append(('service', f'service_{idx}', str(service), {}))
    rows: list[dict[str, Any]] = []
    for knowledge_type, source_key, content_text, metadata in items[:32]:
        vector = sparse_vector_from_text(content_text)
        now = utcnow_iso()
        existing = fetch_one(conn, 'SELECT * FROM knowledge_embeddings WHERE bot_id = ? AND knowledge_type = ? AND source_key = ?', (bot_id, knowledge_type, source_key))
        if existing:
            execute(conn, 'UPDATE knowledge_embeddings SET content_text = ?, vector_json = ?, metadata_json = ?, updated_at = ? WHERE id = ?', (content_text, to_json(vector), to_json(metadata), now, existing['id']))
            row = fetch_one(conn, 'SELECT * FROM knowledge_embeddings WHERE id = ?', (existing['id'],))
        else:
            row_id = new_id('kvec')
            execute(conn, 'INSERT INTO knowledge_embeddings (id, organization_id, bot_id, knowledge_type, source_key, content_text, vector_json, metadata_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (row_id, organization_id, bot_id, knowledge_type, source_key, content_text, to_json(vector), to_json(metadata), now, now))
            row = fetch_one(conn, 'SELECT * FROM knowledge_embeddings WHERE id = ?', (row_id,))
        if row:
            rows.append(row)
    return rows



def search_knowledge_embeddings(conn, *, organization_id: str, bot_id: str, query: str, limit: int = 6) -> list[dict[str, Any]]:
    if not table_exists(conn, 'knowledge_embeddings'):
        return []
    query_vector = sparse_vector_from_text(query)
    rows = fetch_all(conn, 'SELECT * FROM knowledge_embeddings WHERE organization_id = ? AND bot_id = ? ORDER BY updated_at DESC LIMIT 80', (organization_id, bot_id))
    scored: list[dict[str, Any]] = []
    for row in rows:
        similarity = vector_similarity(query_vector, from_json(row.get('vector_json'), {}))
        if similarity <= 0:
            continue
        scored.append({**row, 'similarity': round(similarity, 4), 'metadata': from_json(row.get('metadata_json'), {})})
    scored.sort(key=lambda item: float(item.get('similarity') or 0), reverse=True)
    return scored[:limit]



def lookup_knowledge_query_cache(conn, *, organization_id: str, bot_id: str, query: str) -> list[dict[str, Any]] | None:
    if not table_exists(conn, 'knowledge_query_cache'):
        return None
    now = utcnow_iso()
    query_hash = hash_value(_normalize_text(query))
    row = fetch_one(
        conn,
        "SELECT * FROM knowledge_query_cache WHERE organization_id = ? AND bot_id = ? AND query_hash = ? AND (expires_at IS NULL OR expires_at = '' OR expires_at >= ?) LIMIT 1",
        (organization_id, bot_id, query_hash, now),
    )
    if not row:
        return None
    execute(conn, 'UPDATE knowledge_query_cache SET hit_count = hit_count + 1, updated_at = ? WHERE id = ?', (now, row['id']))
    return list(from_json(row.get('result_json'), []))



def store_knowledge_query_cache(conn, *, organization_id: str, bot_id: str, query: str, results: list[dict[str, Any]], ttl_seconds: int = 21600) -> list[dict[str, Any]]:
    if not table_exists(conn, 'knowledge_query_cache'):
        return results
    now = utcnow_iso()
    query_hash = hash_value(_normalize_text(query))
    expires_at = add_seconds(now, ttl_seconds) if ttl_seconds and ttl_seconds > 0 else None
    existing = fetch_one(conn, 'SELECT * FROM knowledge_query_cache WHERE organization_id = ? AND bot_id = ? AND query_hash = ?', (organization_id, bot_id, query_hash))
    payload = to_json(results)
    if existing:
        execute(conn, 'UPDATE knowledge_query_cache SET query_text = ?, result_json = ?, updated_at = ?, expires_at = ? WHERE id = ?', (query, payload, now, expires_at, existing['id']))
        return results
    execute(conn, 'INSERT INTO knowledge_query_cache (id, organization_id, bot_id, query_hash, query_text, result_json, hit_count, created_at, updated_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)', (new_id('kqc'), organization_id, bot_id, query_hash, query, payload, now, now, expires_at))
    return results



def search_knowledge_embeddings_cached(conn, *, organization_id: str, bot_id: str, query: str, limit: int = 6, ttl_seconds: int = 21600) -> list[dict[str, Any]]:
    cached = lookup_knowledge_query_cache(conn, organization_id=organization_id, bot_id=bot_id, query=query)
    if cached is not None:
        return [{**item, 'cache_hit': True} for item in cached[:limit]]
    results = search_knowledge_embeddings(conn, organization_id=organization_id, bot_id=bot_id, query=query, limit=limit)
    store_knowledge_query_cache(conn, organization_id=organization_id, bot_id=bot_id, query=query, results=results, ttl_seconds=ttl_seconds)
    return [{**item, 'cache_hit': False} for item in results]



def cache_efficiency_overview(conn, *, organization_id: str | None = None, bot_id: str | None = None) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if organization_id:
        clauses.append('organization_id = ?')
        params.append(organization_id)
    if bot_id:
        clauses.append('bot_id = ?')
        params.append(bot_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    ai_rows = fetch_all(conn, f'SELECT cache_type, hit_count, created_at, updated_at FROM ai_cache_entries {where} ORDER BY updated_at DESC LIMIT 500', tuple(params)) if table_exists(conn, 'ai_cache_entries') else []
    knowledge_rows = fetch_all(conn, f'SELECT hit_count, created_at, updated_at FROM knowledge_query_cache {where} ORDER BY updated_at DESC LIMIT 500', tuple(params)) if table_exists(conn, 'knowledge_query_cache') else []
    by_type: dict[str, dict[str, Any]] = {}
    for row in ai_rows:
        key = str(row.get('cache_type') or 'unknown')
        bucket = by_type.setdefault(key, {'entries': 0, 'hits': 0})
        bucket['entries'] += 1
        bucket['hits'] += int(row.get('hit_count') or 0)
    if knowledge_rows:
        by_type['knowledge_search'] = {
            'entries': len(knowledge_rows),
            'hits': sum(int(row.get('hit_count') or 0) for row in knowledge_rows),
        }
    total_entries = sum(item['entries'] for item in by_type.values())
    total_hits = sum(item['hits'] for item in by_type.values())
    return {
        'totals': {
            'entries': total_entries,
            'hits': total_hits,
            'hit_density': round((total_hits / max(1, total_entries)), 2),
        },
        'by_type': by_type,
        'recent_entries': ai_rows[:10],
        'knowledge_query_cache': knowledge_rows[:10],
    }



def maybe_create_conversation_checkpoint(conn, *, organization_id: str, conversation_id: str, bot_id: str, recent_messages: list[dict[str, Any]], classification: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any] | None:
    if not table_exists(conn, 'conversation_checkpoints'):
        return None
    from .runtime_settings import memory_runtime_settings

    profile = memory_runtime_settings()
    checkpoint_every_n_messages = max(3, int(profile.get('checkpoint_every_n_messages') or profile.get('summarize_every_n_messages') or 6))
    checkpoint_min_chars = max(300, int(profile.get('checkpoint_min_chars') or 900))
    total_chars = sum(len(str(item.get('body') or '')) for item in recent_messages)
    if len(recent_messages) < checkpoint_every_n_messages and total_chars < checkpoint_min_chars:
        return None
    latest = recent_messages[-6:]
    transcript = ' | '.join(f"{item.get('direction')}:{str(item.get('body') or '')[:120]}" for item in latest)
    summary_text = f"Intent={classification.get('intent')}; stage={memory.get('lead_stage') or classification.get('lead_stage')}; last_messages={transcript}"[:900]
    existing = fetch_one(conn, 'SELECT * FROM conversation_checkpoints WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1', (conversation_id,))
    existing_facts = from_json((existing or {}).get('facts_json'), {}) if existing else {}
    previous_count = int(existing_facts.get('message_count_at_checkpoint') or 0)
    if existing and (existing.get('summary_text') or '') == summary_text:
        return existing
    if existing and (len(recent_messages) - previous_count) < checkpoint_every_n_messages and total_chars < int(checkpoint_min_chars * 1.25):
        return None
    facts = {
        'intent': classification.get('intent'),
        'lead_stage': memory.get('lead_stage') or classification.get('lead_stage'),
        'lead_score': memory.get('lead_score'),
        'next_action': memory.get('next_action'),
        'message_count_at_checkpoint': len(recent_messages),
        'checkpoint_every_n_messages': checkpoint_every_n_messages,
    }
    row_id = new_id('chk')
    execute(conn, 'INSERT INTO conversation_checkpoints (id, organization_id, conversation_id, bot_id, checkpoint_type, summary_text, facts_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (row_id, organization_id, conversation_id, bot_id, 'auto_summary', summary_text, to_json(facts), utcnow_iso()))
    return fetch_one(conn, 'SELECT * FROM conversation_checkpoints WHERE id = ?', (row_id,)) or {}



def recent_checkpoints(conn, *, conversation_id: str, limit: int = 3) -> list[dict[str, Any]]:
    if not table_exists(conn, 'conversation_checkpoints'):
        return []
    rows = fetch_all(conn, 'SELECT * FROM conversation_checkpoints WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?', (conversation_id, limit))
    return [{**row, 'facts': from_json(row.get('facts_json'), {})} for row in rows]



def record_revenue_event(conn, *, organization_id: str, bot_id: str | None, conversation_id: str | None, contact_id: str | None, event_type: str, recommendation: dict[str, Any], expected_value: float = 0.0) -> dict[str, Any]:
    if not table_exists(conn, 'revenue_optimization_events'):
        return {}
    row_id = new_id('rev')
    now = utcnow_iso()
    execute(conn, 'INSERT INTO revenue_optimization_events (id, organization_id, bot_id, conversation_id, contact_id, event_type, recommendation_json, status, expected_value, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (row_id, organization_id, bot_id, conversation_id, contact_id, event_type, to_json(recommendation), 'pending', expected_value, now, now))
    return fetch_one(conn, 'SELECT * FROM revenue_optimization_events WHERE id = ?', (row_id,)) or {}



def revenue_overview(conn, *, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    if not table_exists(conn, 'revenue_optimization_events'):
        return {'totals': {'events': 0, 'expected_value': 0.0}, 'recent': []}
    if bot_id:
        rows = fetch_all(conn, 'SELECT * FROM revenue_optimization_events WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 100', (organization_id, bot_id))
    else:
        rows = fetch_all(conn, 'SELECT * FROM revenue_optimization_events WHERE organization_id = ? ORDER BY created_at DESC LIMIT 100', (organization_id,))
    return {
        'totals': {
            'events': len(rows),
            'expected_value': round(sum(float(row.get('expected_value') or 0) for row in rows), 2),
        },
        'recent': [{**row, 'recommendation': from_json(row.get('recommendation_json'), {})} for row in rows[:20]],
    }



def search_technical_logs(conn, *, query: str, organization_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if not table_exists(conn, 'technical_logs'):
        return []
    like = f"%{query}%"
    if organization_id:
        rows = fetch_all(conn, 'SELECT * FROM technical_logs WHERE organization_id = ? AND (message LIKE ? OR category LIKE ? OR trace_id LIKE ? OR execution_id LIKE ?) ORDER BY created_at DESC LIMIT ?', (organization_id, like, like, like, like, limit))
    else:
        rows = fetch_all(conn, 'SELECT * FROM technical_logs WHERE message LIKE ? OR category LIKE ? OR trace_id LIKE ? OR execution_id LIKE ? ORDER BY created_at DESC LIMIT ?', (like, like, like, like, limit))
    return [{**row, 'details': from_json(row.get('details_json'), {})} for row in rows]



def trace_timeline(conn, *, trace_id: str) -> dict[str, Any]:
    runs = fetch_all(conn, 'SELECT * FROM execution_runs WHERE trace_id = ? ORDER BY created_at ASC', (trace_id,)) if table_exists(conn, 'execution_runs') else []
    logs = fetch_all(conn, 'SELECT * FROM technical_logs WHERE trace_id = ? ORDER BY created_at ASC', (trace_id,)) if table_exists(conn, 'technical_logs') else []
    spans = fetch_all(conn, 'SELECT * FROM trace_spans WHERE trace_id = ? ORDER BY started_at ASC', (trace_id,)) if table_exists(conn, 'trace_spans') else []
    return {
        'trace_id': trace_id,
        'runs': runs,
        'logs': [{**row, 'details': from_json(row.get('details_json'), {})} for row in logs],
        'spans': [{**row, 'attributes': from_json(row.get('attributes_json'), {})} for row in spans],
    }


def start_trace_span(conn, *, trace_id: str, span_id: str, parent_span_id: str | None, name: str, organization_id: str | None = None, bot_id: str | None = None, conversation_id: str | None = None, execution_run_id: str | None = None, request_id: str | None = None, correlation_id: str | None = None, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    if not table_exists(conn, 'trace_spans'):
        return {}
    row_id = new_id('span')
    execute(conn, 'INSERT INTO trace_spans (id, trace_id, span_id, parent_span_id, name, status, organization_id, bot_id, conversation_id, execution_run_id, request_id, correlation_id, attributes_json, started_at, ended_at, duration_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)', (row_id, trace_id, span_id, parent_span_id, name, 'running', organization_id, bot_id, conversation_id, execution_run_id, request_id, correlation_id, to_json(attributes or {}), utcnow_iso()))
    return fetch_one(conn, 'SELECT * FROM trace_spans WHERE id = ?', (row_id,)) or {}



def finish_trace_span(conn, *, trace_id: str, span_id: str, status: str = 'ok', attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    if not table_exists(conn, 'trace_spans'):
        return {}
    row = fetch_one(conn, 'SELECT * FROM trace_spans WHERE trace_id = ? AND span_id = ? ORDER BY started_at DESC LIMIT 1', (trace_id, span_id))
    if not row:
        return {}
    start_dt = parse_iso(row.get('started_at'))
    end_iso = utcnow_iso()
    end_dt = parse_iso(end_iso)
    duration_ms = int((end_dt - start_dt).total_seconds() * 1000) if start_dt and end_dt else None
    current = from_json(row.get('attributes_json'), {})
    current.update(attributes or {})
    execute(conn, 'UPDATE trace_spans SET status = ?, attributes_json = ?, ended_at = ?, duration_ms = ? WHERE id = ?', (status, to_json(current), end_iso, duration_ms, row['id']))
    refreshed = fetch_one(conn, 'SELECT * FROM trace_spans WHERE id = ?', (row['id'],)) or {}
    try:
        from .world_class_ext import queue_otel_span_export
        queue_otel_span_export(conn, refreshed)
    except Exception:
        pass
    return refreshed
