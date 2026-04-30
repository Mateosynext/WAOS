from __future__ import annotations
import json, uuid, hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from ..db import DBConnection, fetch_one, fetch_all

JSON_MAX_BYTES = 1_250_000
RUN_UPDATE_FIELDS = {"organization_id","bot_id","wizard_id","user_id","workflow_type","status","intensity","prompt","current_step","progress","config_json","result_json","error_json","cost_estimate_usd","idempotency_key","worker_id","heartbeat_at","retry_count","last_recovery_at","created_at","updated_at","completed_at"}
TERMINAL_STATUSES = {"completed","completed_partial","failed","retryable_failed","cancelled","paused_cost_limit"}

def _now() -> str: return datetime.now(timezone.utc).isoformat()

def _clean_json_value(v: Any, depth: int = 0) -> Any:
    if depth > 8: return "[truncated_depth]"
    # Preserve JSON null for nested optional fields. Turning None into {} caused
    # optional ids such as bot_id/vertical_id to come back from config_json and
    # result_json as empty objects, which can silently break frontend/backend
    # contracts after a run snapshot is reloaded. Top-level empty payloads are
    # already normalized by callers before _json is invoked.
    if v is None: return None
    if isinstance(v, dict):
        out = {}
        for key, value in v.items():
            k = str(key); lk = k.lower()
            if any(token in lk for token in ("secret","token","api_key","apikey","password","system_message","raw_provider_response")):
                out[k] = "[redacted]"
            else:
                out[k] = _clean_json_value(value, depth + 1)
        return out
    if isinstance(v, list): return [_clean_json_value(item, depth + 1) for item in v[:500]]
    if isinstance(v, (str, int, float, bool)): return v
    return str(v)

def _json(v: Any) -> str:
    try:
        encoded = json.dumps(_clean_json_value(v), ensure_ascii=False, default=str)
    except Exception:
        encoded = json.dumps({"serialization_error": True, "preview": repr(v)[:2000]}, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > JSON_MAX_BYTES:
        encoded = json.dumps({"truncated": True, "preview": encoded[:JSON_MAX_BYTES]}, ensure_ascii=False)
    return encoded

def _ensure_workflow_column(conn: DBConnection, table: str, column: str, definition: str) -> None:
    if getattr(conn, "backend", "sqlite") == "sqlite":
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if any(row[1] == column for row in rows):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return
    row = conn.execute(
        """
        SELECT 1 AS present
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = ? AND column_name = ?
        LIMIT 1
        """,
        (table, column),
    ).fetchone()
    if not row:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _event_dedupe_key(run_id: str, event_type: str, payload_json: dict | None) -> str | None:
    payload_json = payload_json or {}
    explicit = str(payload_json.get("dedupe_key") or payload_json.get("idempotency_key") or payload_json.get("request_id") or "").strip()
    if not explicit:
        return None
    seed = json.dumps({"run_id": run_id, "event_type": event_type, "key": explicit}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _assert_run_exists(conn: DBConnection, run_id: str) -> None:
    if not str(run_id or "").strip():
        raise ValueError("workflow run_id is required")
    if not fetch_one(conn, "SELECT 1 AS present FROM ai_workflow_runs WHERE id=?", (run_id,)):
        raise KeyError(f"workflow run not found for child record: {run_id}")


def _claim_event_sequence(conn: DBConnection, run_id: str) -> int:
    """Atomically claim the next per-run event sequence."""
    now = _now()
    if getattr(conn, "backend", "sqlite") == "sqlite":
        conn.execute(
            "INSERT OR IGNORE INTO ai_workflow_event_cursors (run_id,next_sequence,updated_at) "
            "SELECT ?, COALESCE(MAX(sequence), 0) + 1, ? FROM ai_workflow_events WHERE run_id=?",
            (run_id, now, run_id),
        )
    else:
        conn.execute(
            "INSERT INTO ai_workflow_event_cursors (run_id,next_sequence,updated_at) "
            "SELECT ?, COALESCE(MAX(sequence), 0) + 1, ? FROM ai_workflow_events WHERE run_id=? "
            "ON CONFLICT (run_id) DO NOTHING",
            (run_id, now, run_id),
        )
    conn.execute("UPDATE ai_workflow_event_cursors SET next_sequence=next_sequence+1, updated_at=? WHERE run_id=?", (now, run_id))
    row = fetch_one(conn, "SELECT next_sequence - 1 AS sequence FROM ai_workflow_event_cursors WHERE run_id=?", (run_id,))
    try:
        return max(1, int((row or {}).get("sequence") or 1))
    except Exception:
        return 1


def event_cursor_exists(conn: DBConnection, run_id: str, event_id: str | None) -> bool:
    ensure_ai_workflow_schema(conn)
    event_id = str(event_id or "").strip()
    if not event_id:
        return False
    return bool(fetch_one(conn, "SELECT 1 AS present FROM ai_workflow_events WHERE run_id=? AND id=?", (run_id, event_id)))


def get_latest_event_id(conn: DBConnection, run_id: str) -> str | None:
    ensure_ai_workflow_schema(conn)
    row = fetch_one(conn, "SELECT id FROM ai_workflow_events WHERE run_id=? ORDER BY sequence DESC, created_at DESC, id DESC LIMIT 1", (run_id,))
    return str(row["id"]) if row and row.get("id") else None


def _workflow_idempotency_key(*, organization_id: str, user_id: str | None, payload: dict, explicit_key: str | None = None) -> str:
    explicit = str(explicit_key or "").strip()
    if explicit:
        seed = {"scope": "client", "organization_id": organization_id, "user_id": user_id or "", "client_request_id": explicit}
    else:
        normalized = dict(payload or {})
        normalized.pop("safety_warnings", None)
        normalized.pop("requested_intensity", None)
        normalized.pop("client_request_id", None)
        seed = {"scope": "payload", "organization_id": organization_id, "user_id": user_id or "", "payload": normalized}
    encoded = json.dumps(seed, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def get_run_by_idempotency_key(conn: DBConnection, *, organization_id: str, workflow_type: str, idempotency_key: str) -> dict | None:
    ensure_ai_workflow_schema(conn)
    key = str(idempotency_key or "").strip()
    if not key:
        return None
    return _decode(fetch_one(conn, "SELECT * FROM ai_workflow_runs WHERE organization_id=? AND workflow_type=? AND idempotency_key=? ORDER BY created_at DESC LIMIT 1", (organization_id, workflow_type, key)))


def _decode(row: dict | None) -> dict | None:
    if not row: return None
    out=dict(row)
    for k in list(out):
        if k.endswith("_json"):
            if out[k] is None or out[k] == "": out[k] = {}
            elif isinstance(out[k], str):
                try: out[k]=json.loads(out[k] or "{}")
                except Exception: out[k]={"decode_error": True, "raw_preview": out[k][:1000]}
    return out

def ensure_ai_workflow_schema(conn: DBConnection) -> None:
    conn.executescript('''
CREATE TABLE IF NOT EXISTS ai_workflow_runs (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, bot_id TEXT, wizard_id TEXT, user_id TEXT, workflow_type TEXT NOT NULL, status TEXT NOT NULL, intensity TEXT, prompt TEXT, current_step TEXT, progress INTEGER DEFAULT 0, config_json TEXT DEFAULT '{}', result_json TEXT DEFAULT '{}', error_json TEXT DEFAULT '{}', cost_estimate_usd REAL DEFAULT 0, idempotency_key TEXT, created_at TEXT, updated_at TEXT, completed_at TEXT);
CREATE TABLE IF NOT EXISTS ai_workflow_steps (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, step_key TEXT NOT NULL, step_label TEXT, status TEXT NOT NULL, input_json TEXT DEFAULT '{}', output_json TEXT DEFAULT '{}', error_json TEXT DEFAULT '{}', retry_count INTEGER DEFAULT 0, cost_estimate_usd REAL DEFAULT 0, latency_ms INTEGER DEFAULT 0, started_at TEXT, completed_at TEXT, FOREIGN KEY(run_id) REFERENCES ai_workflow_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS ai_workflow_events (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, event_type TEXT NOT NULL, message TEXT, progress INTEGER DEFAULT 0, entity_type TEXT, entity_id TEXT, payload_json TEXT DEFAULT '{}', created_at TEXT, sequence INTEGER DEFAULT 0, dedupe_key TEXT, FOREIGN KEY(run_id) REFERENCES ai_workflow_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS ai_cost_ledger (id TEXT PRIMARY KEY, organization_id TEXT, bot_id TEXT, run_id TEXT, provider TEXT, model TEXT, operation TEXT, prompt_tokens INTEGER DEFAULT 0, completion_tokens INTEGER DEFAULT 0, estimated_cost_usd REAL DEFAULT 0, latency_ms INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS simulation_reports (id TEXT PRIMARY KEY, run_id TEXT, wizard_id TEXT, bot_id TEXT, status TEXT, score REAL, total_scenarios INTEGER, passed_scenarios INTEGER, failed_scenarios INTEGER, blocking_failures_json TEXT DEFAULT '[]', report_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS simulation_scenarios (id TEXT PRIMARY KEY, run_id TEXT, scenario_key TEXT, result_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS go_live_readiness_reports (id TEXT PRIMARY KEY, run_id TEXT, wizard_id TEXT, bot_id TEXT, status TEXT, score REAL, blockers_json TEXT DEFAULT '[]', warnings_json TEXT DEFAULT '[]', human_confirmations_json TEXT DEFAULT '[]', can_apply INTEGER DEFAULT 0, can_publish INTEGER DEFAULT 0, canary_required INTEGER DEFAULT 1, created_at TEXT);
CREATE TABLE IF NOT EXISTS agent_policy_packs (id TEXT PRIMARY KEY, run_id TEXT, bot_id TEXT, pack_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS whatsapp_production_packs (id TEXT PRIMARY KEY, run_id TEXT, bot_id TEXT, pack_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS tool_execution_plans (id TEXT PRIMARY KEY, run_id TEXT, bot_id TEXT, plan_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS knowledge_grounding_plans (id TEXT PRIMARY KEY, run_id TEXT, bot_id TEXT, plan_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS human_confirmation_items (id TEXT PRIMARY KEY, run_id TEXT, wizard_id TEXT, bot_id TEXT, field_key TEXT, label TEXT, reason TEXT, status TEXT, suggested_value TEXT, confirmed_value TEXT, created_at TEXT, updated_at TEXT, FOREIGN KEY(run_id) REFERENCES ai_workflow_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS ai_workflow_actions (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, action_type TEXT NOT NULL, status TEXT NOT NULL, result_json TEXT DEFAULT '{}', created_at TEXT, updated_at TEXT, UNIQUE(run_id, action_type), FOREIGN KEY(run_id) REFERENCES ai_workflow_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS ai_workflow_event_cursors (run_id TEXT PRIMARY KEY, next_sequence INTEGER NOT NULL DEFAULT 1, updated_at TEXT, FOREIGN KEY(run_id) REFERENCES ai_workflow_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS ai_runtime_turn_inspections (id TEXT PRIMARY KEY, organization_id TEXT, bot_id TEXT, conversation_id TEXT, turn_id TEXT, inspection_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS ai_provider_health_snapshots (id TEXT PRIMARY KEY, provider TEXT, model TEXT, status TEXT, metrics_json TEXT DEFAULT '{}', created_at TEXT);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_runs_org_created ON ai_workflow_runs (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_runs_status ON ai_workflow_runs (status);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_events_run_created ON ai_workflow_events (run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_steps_run_key ON ai_workflow_steps (run_id, step_key);
CREATE INDEX IF NOT EXISTS idx_ai_cost_ledger_org_run ON ai_cost_ledger (organization_id, run_id);
CREATE INDEX IF NOT EXISTS idx_human_confirmation_run_field ON human_confirmation_items (run_id, field_key);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_actions_run_action ON ai_workflow_actions (run_id, action_type);
''')
    _ensure_workflow_column(conn, "ai_workflow_runs", "idempotency_key", "TEXT")
    _ensure_workflow_column(conn, "ai_workflow_runs", "worker_id", "TEXT")
    _ensure_workflow_column(conn, "ai_workflow_runs", "heartbeat_at", "TEXT")
    _ensure_workflow_column(conn, "ai_workflow_runs", "retry_count", "INTEGER DEFAULT 0")
    _ensure_workflow_column(conn, "ai_workflow_runs", "last_recovery_at", "TEXT")
    _ensure_workflow_column(conn, "ai_workflow_events", "sequence", "INTEGER DEFAULT 0")
    _ensure_workflow_column(conn, "ai_workflow_events", "dedupe_key", "TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_workflow_runs_idempotency ON ai_workflow_runs (organization_id, workflow_type, idempotency_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_workflow_events_run_sequence ON ai_workflow_events (run_id, sequence, id)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_workflow_events_run_dedupe ON ai_workflow_events (run_id, dedupe_key) WHERE dedupe_key IS NOT NULL AND dedupe_key <> ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_workflow_runs_recovery ON ai_workflow_runs (status, heartbeat_at, updated_at)")

def create_run(conn: DBConnection, *, organization_id: str, bot_id: str|None, user_id: str|None, prompt: str, intensity: str, config: dict, idempotency_key: str|None=None) -> dict:
    ensure_ai_workflow_schema(conn); rid=str(uuid.uuid4()); now=_now(); key=str(idempotency_key or "").strip() or None
    params=(rid,organization_id,bot_id,user_id,"bot_autopilot","running",intensity,prompt,"created",1,_json(config),_json({}),_json({}),0,key,now,now)
    if key:
        if getattr(conn, "backend", "sqlite") == "sqlite":
            cur = conn.execute("INSERT OR IGNORE INTO ai_workflow_runs (id,organization_id,bot_id,user_id,workflow_type,status,intensity,prompt,current_step,progress,config_json,result_json,error_json,cost_estimate_usd,idempotency_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", params)
        else:
            cur = conn.execute("INSERT INTO ai_workflow_runs (id,organization_id,bot_id,user_id,workflow_type,status,intensity,prompt,current_step,progress,config_json,result_json,error_json,cost_estimate_usd,idempotency_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT (organization_id, workflow_type, idempotency_key) DO NOTHING", params)
        if getattr(cur, "rowcount", 0) == 0:
            existing = get_run_by_idempotency_key(conn, organization_id=organization_id, workflow_type="bot_autopilot", idempotency_key=key)
            if existing:
                existing["_idempotent_replay"] = True
                return existing
    else:
        conn.execute("INSERT INTO ai_workflow_runs (id,organization_id,bot_id,user_id,workflow_type,status,intensity,prompt,current_step,progress,config_json,result_json,error_json,cost_estimate_usd,idempotency_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", params)
    run = require_run(conn, rid)
    run["_idempotent_replay"] = False
    return run

def require_run(conn: DBConnection, run_id: str) -> dict:
    ensure_ai_workflow_schema(conn); row=_decode(fetch_one(conn,"SELECT * FROM ai_workflow_runs WHERE id=?",(run_id,)))
    if not row: raise KeyError(f"workflow run not found: {run_id}")
    return row

def get_run(conn: DBConnection, run_id: str) -> dict|None:
    ensure_ai_workflow_schema(conn); return _decode(fetch_one(conn,"SELECT * FROM ai_workflow_runs WHERE id=?",(run_id,)))


def touch_run_heartbeat(conn: DBConnection, run_id: str, *, worker_id: str | None = None) -> dict:
    """Persist a worker heartbeat so polling/recovery can distinguish alive vs zombie runs."""
    ensure_ai_workflow_schema(conn)
    now = _now()
    if worker_id:
        conn.execute("UPDATE ai_workflow_runs SET worker_id=?, heartbeat_at=?, updated_at=? WHERE id=?", (worker_id, now, now, run_id))
    else:
        conn.execute("UPDATE ai_workflow_runs SET heartbeat_at=?, updated_at=? WHERE id=?", (now, now, run_id))
    return require_run(conn, run_id)


def claim_workflow_run_execution(conn: DBConnection, run_id: str, *, worker_id: str, lease_seconds: int = 120) -> dict:
    """Atomically claim an autopilot run for exactly one active worker.

    A duplicate worker may only take over when the previous heartbeat is stale,
    or when a reaper moved the run into stale/retryable_failed. This protects
    double-clicks, duplicate background tasks, two browser tabs and restart races.
    """
    ensure_ai_workflow_schema(conn)
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    lease_seconds = max(15, min(int(lease_seconds or 120), 60 * 60))
    cutoff = (now_dt - timedelta(seconds=lease_seconds)).isoformat()
    conn.execute(
        """
        UPDATE ai_workflow_runs
        SET status='running', worker_id=?, heartbeat_at=?, updated_at=?, completed_at=NULL
        WHERE id=?
          AND (
            status IN ('stale','retryable_failed')
            OR (
              status='running'
              AND (worker_id IS NULL OR worker_id='' OR heartbeat_at IS NULL OR heartbeat_at<? OR worker_id=?)
            )
          )
        """,
        (worker_id, now, now, run_id, cutoff, worker_id),
    )
    run = require_run(conn, run_id)
    claimed = str(run.get("worker_id") or "") == worker_id and str(run.get("status") or "") == "running"
    run["_worker_claimed"] = claimed
    if not claimed:
        run["_claim_rejected_reason"] = "workflow_run_already_claimed_or_terminal"
    return run

def update_run(conn: DBConnection, run_id: str, **fields: Any) -> dict:
    ensure_ai_workflow_schema(conn); fields["updated_at"]=_now()
    for key in list(fields):
        if key not in RUN_UPDATE_FIELDS:
            raise ValueError(f"unsupported ai_workflow_runs field: {key}")
    if "progress" in fields and fields["progress"] is not None:
        fields["progress"] = max(0, min(100, int(fields["progress"])))
    if fields.get("status") in TERMINAL_STATUSES: fields.setdefault("completed_at", _now())
    encoded={k: _json(v) if k.endswith("_json") else v for k,v in fields.items()}
    sets=", ".join(f"{k}=?" for k in encoded)
    conn.execute(f"UPDATE ai_workflow_runs SET {sets} WHERE id=?", (*encoded.values(), run_id))
    return require_run(conn, run_id)

def upsert_step(conn: DBConnection, run_id: str, step_key: str, step_label: str, status: str, input_json: dict|None=None, output_json: dict|None=None, error_json: dict|None=None, retry_count: int=0, cost_estimate_usd: float=0, latency_ms: int=0) -> None:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); sid=f"{run_id}:{step_key}"; now=_now()
    existing=fetch_one(conn,"SELECT id FROM ai_workflow_steps WHERE id=?",(sid,))
    data=(step_label,status,_json(input_json),_json(output_json),_json(error_json),retry_count,cost_estimate_usd,latency_ms,now,sid)
    if existing: conn.execute("UPDATE ai_workflow_steps SET step_label=?,status=?,input_json=?,output_json=?,error_json=?,retry_count=?,cost_estimate_usd=?,latency_ms=?,completed_at=? WHERE id=?", data)
    else: conn.execute("INSERT INTO ai_workflow_steps (id,run_id,step_key,step_label,status,input_json,output_json,error_json,retry_count,cost_estimate_usd,latency_ms,started_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (sid,run_id,step_key,step_label,status,_json(input_json),_json(output_json),_json(error_json),retry_count,cost_estimate_usd,latency_ms,now,now))

def record_event(conn: DBConnection, run_id: str, event_type: str, message: str="", progress: int=0, entity_type: str|None=None, entity_id: str|None=None, payload_json: dict|None=None) -> dict:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); eid=str(uuid.uuid4()); now=_now(); payload_json=_clean_json_value(payload_json or {})
    progress=max(0,min(100,int(progress or 0)))
    event_type=str(event_type or "workflow.event")[:160]; message=str(message or "")[:4000]
    sequence=_claim_event_sequence(conn, run_id); dedupe_key=_event_dedupe_key(run_id, event_type, payload_json)
    try:
        conn.execute("INSERT INTO ai_workflow_events (id,run_id,event_type,message,progress,entity_type,entity_id,payload_json,created_at,sequence,dedupe_key) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (eid,run_id,event_type,message,progress,entity_type,entity_id,_json(payload_json),now,sequence,dedupe_key))
    except Exception:
        if dedupe_key:
            existing=_decode(fetch_one(conn,"SELECT * FROM ai_workflow_events WHERE run_id=? AND dedupe_key=?",(run_id,dedupe_key)))
            if existing: return existing
        raise
    return {"id":eid,"run_id":run_id,"event_type":event_type,"message":message,"progress":progress,"entity_type":entity_type,"entity_id":entity_id,"payload_json":payload_json,"created_at":now,"sequence":sequence,"dedupe_key":dedupe_key}

def list_events(conn: DBConnection, run_id: str) -> list[dict]:
    ensure_ai_workflow_schema(conn); return [_decode(r) or {} for r in fetch_all(conn,"SELECT * FROM ai_workflow_events WHERE run_id=? ORDER BY sequence ASC, created_at ASC, id ASC",(run_id,))]

def list_events_after(conn: DBConnection, run_id: str, after_event_id: str | None = None, limit: int = 100) -> list[dict]:
    ensure_ai_workflow_schema(conn); limit=max(1,min(int(limit or 100),500)); after_event_id=str(after_event_id or "").strip()
    if not after_event_id:
        return [_decode(r) or {} for r in fetch_all(conn,"SELECT * FROM ai_workflow_events WHERE run_id=? ORDER BY sequence ASC, created_at ASC, id ASC LIMIT ?",(run_id,limit))]
    cursor=fetch_one(conn,"SELECT sequence,created_at,id FROM ai_workflow_events WHERE run_id=? AND id=?",(run_id,after_event_id))
    if not cursor:
        # Unknown/stale Last-Event-ID must not replay the whole stream. The
        # frontend recovers state through snapshot polling while SSE resumes
        # only from new events after the current tail.
        return []
    return [_decode(r) or {} for r in fetch_all(conn,"SELECT * FROM ai_workflow_events WHERE run_id=? AND (sequence>? OR (sequence=? AND created_at>?) OR (sequence=? AND created_at=? AND id>?)) ORDER BY sequence ASC, created_at ASC, id ASC LIMIT ?",(run_id,cursor["sequence"],cursor["sequence"],cursor["created_at"],cursor["sequence"],cursor["created_at"],cursor["id"],limit))]

def list_steps(conn: DBConnection, run_id: str) -> list[dict]:
    ensure_ai_workflow_schema(conn); return [_decode(r) or {} for r in fetch_all(conn,"SELECT * FROM ai_workflow_steps WHERE run_id=? ORDER BY started_at ASC, id ASC",(run_id,))]

def list_runs(conn: DBConnection, limit: int=50, organization_ids: list[str]|None=None) -> list[dict]:
    ensure_ai_workflow_schema(conn); limit=max(1,min(int(limit or 50),200))
    if organization_ids is not None:
        cleaned_org_ids=[str(item).strip() for item in organization_ids if str(item or "").strip()]
        if not cleaned_org_ids:
            return []
        placeholders=",".join("?" for _ in cleaned_org_ids)
        rows=fetch_all(conn,f"SELECT * FROM ai_workflow_runs WHERE organization_id IN ({placeholders}) ORDER BY created_at DESC LIMIT ?",(*cleaned_org_ids,limit))
    else:
        rows=fetch_all(conn,"SELECT * FROM ai_workflow_runs ORDER BY created_at DESC LIMIT ?",(limit,))
    return [_decode(r) or {} for r in rows]

def patch_run_result(conn: DBConnection, run_id: str, key: str, value: Any) -> dict:
    run = require_run(conn, run_id)
    result = dict(run.get("result_json") or {})
    result[key] = value
    return update_run(conn, run_id, result_json=result)

def record_cost(conn: DBConnection, *, organization_id: str|None, bot_id: str|None, run_id: str, provider: str, model: str, operation: str, prompt_tokens: int=0, completion_tokens: int=0, estimated_cost_usd: float=0.0, latency_ms: int=0) -> dict:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); cid=str(uuid.uuid4()); now=_now()
    conn.execute("INSERT INTO ai_cost_ledger (id,organization_id,bot_id,run_id,provider,model,operation,prompt_tokens,completion_tokens,estimated_cost_usd,latency_ms,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (cid,organization_id,bot_id,run_id,provider,model,operation,prompt_tokens,completion_tokens,estimated_cost_usd,latency_ms,now))
    return {"id":cid,"organization_id":organization_id,"bot_id":bot_id,"run_id":run_id,"provider":provider,"model":model,"operation":operation,"prompt_tokens":prompt_tokens,"completion_tokens":completion_tokens,"estimated_cost_usd":estimated_cost_usd,"latency_ms":latency_ms,"created_at":now}

def save_json_artifact(conn: DBConnection, *, table: str, json_column: str, run_id: str, bot_id: str|None, payload: dict) -> dict:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); aid=str(uuid.uuid4()); now=_now()
    allowed={"agent_policy_packs":"pack_json","whatsapp_production_packs":"pack_json","tool_execution_plans":"plan_json","knowledge_grounding_plans":"plan_json"}
    if allowed.get(table) != json_column:
        raise ValueError(f"unsupported artifact table: {table}.{json_column}")
    conn.execute(f"INSERT INTO {table} (id,run_id,bot_id,{json_column},created_at) VALUES (?,?,?,?,?)", (aid,run_id,bot_id,_json(payload),now))
    return {"id":aid,"run_id":run_id,"bot_id":bot_id,json_column:payload,"created_at":now}

def save_simulation_report(conn: DBConnection, *, run_id: str, wizard_id: str|None, bot_id: str|None, report: dict) -> dict:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); sid=str(uuid.uuid4()); now=_now()
    blocking=report.get("blocking_failures") or []
    conn.execute("INSERT INTO simulation_reports (id,run_id,wizard_id,bot_id,status,score,total_scenarios,passed_scenarios,failed_scenarios,blocking_failures_json,report_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (sid,run_id,wizard_id,bot_id,report.get("status") or report.get("go_live_recommendation") or "completed",float(report.get("average_score") or report.get("score") or 0),int(report.get("total") or report.get("total_scenarios") or 0),int(report.get("passed") or report.get("passed_scenarios") or 0),int(report.get("failed") or report.get("failed_scenarios") or 0),json.dumps(blocking, ensure_ascii=False),_json(report),now))
    for scenario in report.get("scenarios") or []:
        conn.execute("INSERT INTO simulation_scenarios (id,run_id,scenario_key,result_json,created_at) VALUES (?,?,?,?,?)", (str(uuid.uuid4()),run_id,str(scenario.get("scenario_id") or scenario.get("key") or "scenario"),_json(scenario),now))
    return {"id":sid,"run_id":run_id,"report_json":report,"created_at":now}

def save_go_live_readiness(conn: DBConnection, *, run_id: str, wizard_id: str|None, bot_id: str|None, report: dict) -> dict:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); rid=str(uuid.uuid4()); now=_now()
    conn.execute("INSERT INTO go_live_readiness_reports (id,run_id,wizard_id,bot_id,status,score,blockers_json,warnings_json,human_confirmations_json,can_apply,can_publish,canary_required,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (rid,run_id,wizard_id,bot_id,report.get("status"),float(report.get("score") or 0),json.dumps(report.get("blockers") or [], ensure_ascii=False),json.dumps(report.get("warnings") or [], ensure_ascii=False),json.dumps(report.get("human_confirmations_required") or [], ensure_ascii=False),1 if report.get("can_apply") else 0,1 if report.get("can_publish") else 0,1 if report.get("canary_required") else 0,now))
    return {"id":rid,"run_id":run_id,"report_json":report,"created_at":now}

def upsert_human_confirmation(conn: DBConnection, *, run_id: str, wizard_id: str|None=None, bot_id: str|None=None, field_key: str, label: str|None=None, reason: str|None=None, status: str="pending", suggested_value: str|None=None, confirmed_value: str|None=None) -> dict:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); now=_now(); field_key=str(field_key or "confirmation")[:160]
    existing=fetch_one(conn,"SELECT id FROM human_confirmation_items WHERE run_id=? AND field_key=?",(run_id,field_key))
    if existing:
        conn.execute("UPDATE human_confirmation_items SET label=COALESCE(?,label),reason=COALESCE(?,reason),status=?,suggested_value=COALESCE(?,suggested_value),confirmed_value=COALESCE(?,confirmed_value),updated_at=? WHERE id=?", (label,reason,status,suggested_value,confirmed_value,now,existing["id"]))
        return dict(fetch_one(conn,"SELECT * FROM human_confirmation_items WHERE id=?",(existing["id"],)))
    hid=str(uuid.uuid4())
    conn.execute("INSERT INTO human_confirmation_items (id,run_id,wizard_id,bot_id,field_key,label,reason,status,suggested_value,confirmed_value,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (hid,run_id,wizard_id,bot_id,field_key,label or field_key,reason or "Confirmación humana requerida",status,suggested_value,confirmed_value,now,now))
    return dict(fetch_one(conn,"SELECT * FROM human_confirmation_items WHERE id=?",(hid,)))

def list_human_confirmations(conn: DBConnection, run_id: str) -> list[dict]:
    ensure_ai_workflow_schema(conn); return [dict(r) for r in fetch_all(conn,"SELECT * FROM human_confirmation_items WHERE run_id=? ORDER BY created_at ASC, id ASC",(run_id,))]


def mark_stale_running_runs(conn: DBConnection, *, organization_ids: list[str] | None = None, stale_after_minutes: int = 30, limit: int = 50) -> list[dict]:
    """Move overlong running runs into an audited stale state.

    This is the first half of recovery: no run jumps directly from running to
    failed, so operators and tests can prove the restart/crash path occurred.
    """
    ensure_ai_workflow_schema(conn)
    stale_after_minutes = max(1, min(int(stale_after_minutes or 30), 24 * 60))
    limit = max(1, min(int(limit or 50), 250))
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)).isoformat()
    params: list[Any] = [cutoff]
    where = "status='running' AND COALESCE(heartbeat_at, updated_at, created_at)<?"
    if organization_ids is not None:
        cleaned = [str(item).strip() for item in organization_ids if str(item or "").strip()]
        if not cleaned:
            return []
        where += " AND organization_id IN (" + ",".join("?" for _ in cleaned) + ")"
        params.extend(cleaned)
    params.append(limit)
    rows = fetch_all(conn, f"SELECT * FROM ai_workflow_runs WHERE {where} ORDER BY COALESCE(heartbeat_at, updated_at, created_at) ASC LIMIT ?", tuple(params))
    stale: list[dict] = []
    for row in rows:
        run = _decode(row) or {}
        run_id = str(run.get("id") or "")
        if not run_id:
            continue
        error = {
            "code": "workflow_run_stale",
            "message": "Running workflow heartbeat exceeded stale threshold; marking stale before retryable failure.",
            "previous_status": "running",
            "previous_worker_id": run.get("worker_id"),
            "previous_heartbeat_at": run.get("heartbeat_at") or run.get("updated_at"),
            "stale_after_minutes": stale_after_minutes,
            "detected_at": _now(),
        }
        updated = update_run(conn, run_id, status="stale", current_step="workflow.stale_detected", error_json=error, last_recovery_at=error["detected_at"])
        record_event(conn, run_id, "workflow.stale_detected", "Workflow running marcado stale por heartbeat vencido", int(updated.get("progress") or 0), payload_json={**error, "dedupe_key": f"stale:{run_id}:{run.get('heartbeat_at') or run.get('updated_at')}"})
        stale.append(updated)
    return stale


def promote_stale_runs_to_retryable_failed(conn: DBConnection, *, organization_ids: list[str] | None = None, limit: int = 50) -> list[dict]:
    """Move stale runs into retryable_failed so rerun is explicit and safe."""
    ensure_ai_workflow_schema(conn)
    limit = max(1, min(int(limit or 50), 250))
    params: list[Any] = []
    where = "status='stale'"
    if organization_ids is not None:
        cleaned = [str(item).strip() for item in organization_ids if str(item or "").strip()]
        if not cleaned:
            return []
        where += " AND organization_id IN (" + ",".join("?" for _ in cleaned) + ")"
        params.extend(cleaned)
    params.append(limit)
    rows = fetch_all(conn, f"SELECT * FROM ai_workflow_runs WHERE {where} ORDER BY updated_at ASC LIMIT ?", tuple(params))
    promoted: list[dict] = []
    for row in rows:
        run = _decode(row) or {}
        run_id = str(run.get("id") or "")
        if not run_id:
            continue
        error = dict(run.get("error_json") or {})
        error.update({
            "code": "workflow_retryable_failed_after_stale",
            "message": "Stale workflow is now retryable_failed; rerun is allowed without assuming the old worker is alive.",
            "previous_status": "stale",
            "retryable": True,
            "promoted_at": _now(),
        })
        retry_count = int(run.get("retry_count") or 0)
        updated = update_run(conn, run_id, status="retryable_failed", current_step="workflow.retryable_failed", error_json=error, retry_count=retry_count, last_recovery_at=error["promoted_at"])
        record_event(conn, run_id, "workflow.retryable_failed", "Workflow stale promovido a retryable_failed", int(updated.get("progress") or 0), payload_json={**error, "dedupe_key": f"retryable_failed:{run_id}:{updated.get('updated_at')}"})
        promoted.append(updated)
    return promoted


def recover_stale_running_runs(conn: DBConnection, *, organization_ids: list[str] | None = None, stale_after_minutes: int = 30, limit: int = 50) -> list[dict]:
    """Reaper entrypoint: running too long -> stale -> retryable_failed."""
    stale = mark_stale_running_runs(conn, organization_ids=organization_ids, stale_after_minutes=stale_after_minutes, limit=limit)
    promoted = promote_stale_runs_to_retryable_failed(conn, organization_ids=organization_ids, limit=limit)
    return promoted or stale

def get_workflow_action(conn: DBConnection, run_id: str, action_type: str) -> dict | None:
    ensure_ai_workflow_schema(conn); return _decode(fetch_one(conn,"SELECT * FROM ai_workflow_actions WHERE run_id=? AND action_type=?",(run_id,action_type)))

def start_workflow_action(conn: DBConnection, run_id: str, action_type: str) -> dict:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); now=_now(); aid=str(uuid.uuid4())
    params=(aid,run_id,action_type,"in_progress",_json({}),now,now)
    if getattr(conn, "backend", "sqlite") == "sqlite":
        cur = conn.execute("INSERT OR IGNORE INTO ai_workflow_actions (id,run_id,action_type,status,result_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?)", params)
    else:
        cur = conn.execute("INSERT INTO ai_workflow_actions (id,run_id,action_type,status,result_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT (run_id, action_type) DO NOTHING", params)
    if getattr(cur, "rowcount", 0) == 1:
        claimed = get_workflow_action(conn,run_id,action_type) or {}
        claimed["_already_in_progress"] = False
        return claimed
    existing=get_workflow_action(conn,run_id,action_type)
    if existing and existing.get("status") == "completed":
        return existing
    if existing and existing.get("status") == "in_progress":
        existing = dict(existing)
        existing["_already_in_progress"] = True
        return existing
    if existing:
        conn.execute("UPDATE ai_workflow_actions SET status=?,result_json=?,updated_at=? WHERE run_id=? AND action_type=? AND status<>'in_progress'",("in_progress",_json({}),now,run_id,action_type))
        claimed = get_workflow_action(conn,run_id,action_type) or {}
        claimed["_already_in_progress"] = False
        return claimed
    return {"_already_in_progress": True, "status": "in_progress"}

def complete_workflow_action(conn: DBConnection, run_id: str, action_type: str, result: dict, status: str="completed") -> dict:
    ensure_ai_workflow_schema(conn); _assert_run_exists(conn, run_id); now=_now(); existing=get_workflow_action(conn,run_id,action_type)
    if existing:
        conn.execute("UPDATE ai_workflow_actions SET status=?,result_json=?,updated_at=? WHERE run_id=? AND action_type=?",(status,_json(result),now,run_id,action_type))
    else:
        conn.execute("INSERT INTO ai_workflow_actions (id,run_id,action_type,status,result_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",(str(uuid.uuid4()),run_id,action_type,status,_json(result),now,now))
    return get_workflow_action(conn,run_id,action_type) or {}
