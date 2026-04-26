from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from typing import Any
from ..db import DBConnection, fetch_one, fetch_all

JSON_MAX_BYTES = 1_250_000
RUN_UPDATE_FIELDS = {"organization_id","bot_id","wizard_id","user_id","workflow_type","status","intensity","prompt","current_step","progress","config_json","result_json","error_json","cost_estimate_usd","created_at","updated_at","completed_at"}
TERMINAL_STATUSES = {"completed","completed_partial","failed","cancelled","paused_cost_limit"}

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
CREATE TABLE IF NOT EXISTS ai_workflow_runs (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, bot_id TEXT, wizard_id TEXT, user_id TEXT, workflow_type TEXT NOT NULL, status TEXT NOT NULL, intensity TEXT, prompt TEXT, current_step TEXT, progress INTEGER DEFAULT 0, config_json TEXT DEFAULT '{}', result_json TEXT DEFAULT '{}', error_json TEXT DEFAULT '{}', cost_estimate_usd REAL DEFAULT 0, created_at TEXT, updated_at TEXT, completed_at TEXT);
CREATE TABLE IF NOT EXISTS ai_workflow_steps (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, step_key TEXT NOT NULL, step_label TEXT, status TEXT NOT NULL, input_json TEXT DEFAULT '{}', output_json TEXT DEFAULT '{}', error_json TEXT DEFAULT '{}', retry_count INTEGER DEFAULT 0, cost_estimate_usd REAL DEFAULT 0, latency_ms INTEGER DEFAULT 0, started_at TEXT, completed_at TEXT);
CREATE TABLE IF NOT EXISTS ai_workflow_events (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, event_type TEXT NOT NULL, message TEXT, progress INTEGER DEFAULT 0, entity_type TEXT, entity_id TEXT, payload_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS ai_cost_ledger (id TEXT PRIMARY KEY, organization_id TEXT, bot_id TEXT, run_id TEXT, provider TEXT, model TEXT, operation TEXT, prompt_tokens INTEGER DEFAULT 0, completion_tokens INTEGER DEFAULT 0, estimated_cost_usd REAL DEFAULT 0, latency_ms INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS simulation_reports (id TEXT PRIMARY KEY, run_id TEXT, wizard_id TEXT, bot_id TEXT, status TEXT, score REAL, total_scenarios INTEGER, passed_scenarios INTEGER, failed_scenarios INTEGER, blocking_failures_json TEXT DEFAULT '[]', report_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS simulation_scenarios (id TEXT PRIMARY KEY, run_id TEXT, scenario_key TEXT, result_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS go_live_readiness_reports (id TEXT PRIMARY KEY, run_id TEXT, wizard_id TEXT, bot_id TEXT, status TEXT, score REAL, blockers_json TEXT DEFAULT '[]', warnings_json TEXT DEFAULT '[]', human_confirmations_json TEXT DEFAULT '[]', can_apply INTEGER DEFAULT 0, can_publish INTEGER DEFAULT 0, canary_required INTEGER DEFAULT 1, created_at TEXT);
CREATE TABLE IF NOT EXISTS agent_policy_packs (id TEXT PRIMARY KEY, run_id TEXT, bot_id TEXT, pack_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS whatsapp_production_packs (id TEXT PRIMARY KEY, run_id TEXT, bot_id TEXT, pack_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS tool_execution_plans (id TEXT PRIMARY KEY, run_id TEXT, bot_id TEXT, plan_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS knowledge_grounding_plans (id TEXT PRIMARY KEY, run_id TEXT, bot_id TEXT, plan_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS human_confirmation_items (id TEXT PRIMARY KEY, run_id TEXT, wizard_id TEXT, bot_id TEXT, field_key TEXT, label TEXT, reason TEXT, status TEXT, suggested_value TEXT, confirmed_value TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS ai_runtime_turn_inspections (id TEXT PRIMARY KEY, organization_id TEXT, bot_id TEXT, conversation_id TEXT, turn_id TEXT, inspection_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS ai_provider_health_snapshots (id TEXT PRIMARY KEY, provider TEXT, model TEXT, status TEXT, metrics_json TEXT DEFAULT '{}', created_at TEXT);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_runs_org_created ON ai_workflow_runs (organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_runs_status ON ai_workflow_runs (status);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_events_run_created ON ai_workflow_events (run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_workflow_steps_run_key ON ai_workflow_steps (run_id, step_key);
CREATE INDEX IF NOT EXISTS idx_ai_cost_ledger_org_run ON ai_cost_ledger (organization_id, run_id);
CREATE INDEX IF NOT EXISTS idx_human_confirmation_run_field ON human_confirmation_items (run_id, field_key);
''')

def create_run(conn: DBConnection, *, organization_id: str, bot_id: str|None, user_id: str|None, prompt: str, intensity: str, config: dict) -> dict:
    ensure_ai_workflow_schema(conn); rid=str(uuid.uuid4()); now=_now()
    conn.execute("INSERT INTO ai_workflow_runs (id,organization_id,bot_id,user_id,workflow_type,status,intensity,prompt,current_step,progress,config_json,result_json,error_json,cost_estimate_usd,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (rid,organization_id,bot_id,user_id,"bot_autopilot","running",intensity,prompt,"created",1,_json(config),_json({}),_json({}),0,now,now))
    return require_run(conn, rid)

def require_run(conn: DBConnection, run_id: str) -> dict:
    ensure_ai_workflow_schema(conn); row=_decode(fetch_one(conn,"SELECT * FROM ai_workflow_runs WHERE id=?",(run_id,)))
    if not row: raise KeyError(f"workflow run not found: {run_id}")
    return row

def get_run(conn: DBConnection, run_id: str) -> dict|None:
    ensure_ai_workflow_schema(conn); return _decode(fetch_one(conn,"SELECT * FROM ai_workflow_runs WHERE id=?",(run_id,)))

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
    ensure_ai_workflow_schema(conn); sid=f"{run_id}:{step_key}"; now=_now()
    existing=fetch_one(conn,"SELECT id FROM ai_workflow_steps WHERE id=?",(sid,))
    data=(step_label,status,_json(input_json),_json(output_json),_json(error_json),retry_count,cost_estimate_usd,latency_ms,now,sid)
    if existing: conn.execute("UPDATE ai_workflow_steps SET step_label=?,status=?,input_json=?,output_json=?,error_json=?,retry_count=?,cost_estimate_usd=?,latency_ms=?,completed_at=? WHERE id=?", data)
    else: conn.execute("INSERT INTO ai_workflow_steps (id,run_id,step_key,step_label,status,input_json,output_json,error_json,retry_count,cost_estimate_usd,latency_ms,started_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (sid,run_id,step_key,step_label,status,_json(input_json),_json(output_json),_json(error_json),retry_count,cost_estimate_usd,latency_ms,now,now))

def record_event(conn: DBConnection, run_id: str, event_type: str, message: str="", progress: int=0, entity_type: str|None=None, entity_id: str|None=None, payload_json: dict|None=None) -> dict:
    ensure_ai_workflow_schema(conn); eid=str(uuid.uuid4()); now=_now(); payload_json=_clean_json_value(payload_json or {})
    progress=max(0,min(100,int(progress or 0)))
    event_type=str(event_type or "workflow.event")[:160]; message=str(message or "")[:4000]
    conn.execute("INSERT INTO ai_workflow_events (id,run_id,event_type,message,progress,entity_type,entity_id,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)", (eid,run_id,event_type,message,progress,entity_type,entity_id,_json(payload_json),now))
    return {"id":eid,"run_id":run_id,"event_type":event_type,"message":message,"progress":progress,"entity_type":entity_type,"entity_id":entity_id,"payload_json":payload_json,"created_at":now}

def list_events(conn: DBConnection, run_id: str) -> list[dict]:
    ensure_ai_workflow_schema(conn); return [_decode(r) or {} for r in fetch_all(conn,"SELECT * FROM ai_workflow_events WHERE run_id=? ORDER BY created_at ASC, id ASC",(run_id,))]

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
    ensure_ai_workflow_schema(conn); cid=str(uuid.uuid4()); now=_now()
    conn.execute("INSERT INTO ai_cost_ledger (id,organization_id,bot_id,run_id,provider,model,operation,prompt_tokens,completion_tokens,estimated_cost_usd,latency_ms,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (cid,organization_id,bot_id,run_id,provider,model,operation,prompt_tokens,completion_tokens,estimated_cost_usd,latency_ms,now))
    return {"id":cid,"organization_id":organization_id,"bot_id":bot_id,"run_id":run_id,"provider":provider,"model":model,"operation":operation,"prompt_tokens":prompt_tokens,"completion_tokens":completion_tokens,"estimated_cost_usd":estimated_cost_usd,"latency_ms":latency_ms,"created_at":now}

def save_json_artifact(conn: DBConnection, *, table: str, json_column: str, run_id: str, bot_id: str|None, payload: dict) -> dict:
    ensure_ai_workflow_schema(conn); aid=str(uuid.uuid4()); now=_now()
    allowed={"agent_policy_packs":"pack_json","whatsapp_production_packs":"pack_json","tool_execution_plans":"plan_json","knowledge_grounding_plans":"plan_json"}
    if allowed.get(table) != json_column:
        raise ValueError(f"unsupported artifact table: {table}.{json_column}")
    conn.execute(f"INSERT INTO {table} (id,run_id,bot_id,{json_column},created_at) VALUES (?,?,?,?,?)", (aid,run_id,bot_id,_json(payload),now))
    return {"id":aid,"run_id":run_id,"bot_id":bot_id,json_column:payload,"created_at":now}

def save_simulation_report(conn: DBConnection, *, run_id: str, wizard_id: str|None, bot_id: str|None, report: dict) -> dict:
    ensure_ai_workflow_schema(conn); sid=str(uuid.uuid4()); now=_now()
    blocking=report.get("blocking_failures") or []
    conn.execute("INSERT INTO simulation_reports (id,run_id,wizard_id,bot_id,status,score,total_scenarios,passed_scenarios,failed_scenarios,blocking_failures_json,report_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (sid,run_id,wizard_id,bot_id,report.get("status") or report.get("go_live_recommendation") or "completed",float(report.get("average_score") or report.get("score") or 0),int(report.get("total") or report.get("total_scenarios") or 0),int(report.get("passed") or report.get("passed_scenarios") or 0),int(report.get("failed") or report.get("failed_scenarios") or 0),json.dumps(blocking, ensure_ascii=False),_json(report),now))
    for scenario in report.get("scenarios") or []:
        conn.execute("INSERT INTO simulation_scenarios (id,run_id,scenario_key,result_json,created_at) VALUES (?,?,?,?,?)", (str(uuid.uuid4()),run_id,str(scenario.get("scenario_id") or scenario.get("key") or "scenario"),_json(scenario),now))
    return {"id":sid,"run_id":run_id,"report_json":report,"created_at":now}

def save_go_live_readiness(conn: DBConnection, *, run_id: str, wizard_id: str|None, bot_id: str|None, report: dict) -> dict:
    ensure_ai_workflow_schema(conn); rid=str(uuid.uuid4()); now=_now()
    conn.execute("INSERT INTO go_live_readiness_reports (id,run_id,wizard_id,bot_id,status,score,blockers_json,warnings_json,human_confirmations_json,can_apply,can_publish,canary_required,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (rid,run_id,wizard_id,bot_id,report.get("status"),float(report.get("score") or 0),json.dumps(report.get("blockers") or [], ensure_ascii=False),json.dumps(report.get("warnings") or [], ensure_ascii=False),json.dumps(report.get("human_confirmations_required") or [], ensure_ascii=False),1 if report.get("can_apply") else 0,1 if report.get("can_publish") else 0,1 if report.get("canary_required") else 0,now))
    return {"id":rid,"run_id":run_id,"report_json":report,"created_at":now}

def upsert_human_confirmation(conn: DBConnection, *, run_id: str, wizard_id: str|None=None, bot_id: str|None=None, field_key: str, label: str|None=None, reason: str|None=None, status: str="pending", suggested_value: str|None=None, confirmed_value: str|None=None) -> dict:
    ensure_ai_workflow_schema(conn); now=_now(); field_key=str(field_key or "confirmation")[:160]
    existing=fetch_one(conn,"SELECT id FROM human_confirmation_items WHERE run_id=? AND field_key=?",(run_id,field_key))
    if existing:
        conn.execute("UPDATE human_confirmation_items SET label=COALESCE(?,label),reason=COALESCE(?,reason),status=?,suggested_value=COALESCE(?,suggested_value),confirmed_value=COALESCE(?,confirmed_value),updated_at=? WHERE id=?", (label,reason,status,suggested_value,confirmed_value,now,existing["id"]))
        return dict(fetch_one(conn,"SELECT * FROM human_confirmation_items WHERE id=?",(existing["id"],)))
    hid=str(uuid.uuid4())
    conn.execute("INSERT INTO human_confirmation_items (id,run_id,wizard_id,bot_id,field_key,label,reason,status,suggested_value,confirmed_value,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (hid,run_id,wizard_id,bot_id,field_key,label or field_key,reason or "Confirmación humana requerida",status,suggested_value,confirmed_value,now,now))
    return dict(fetch_one(conn,"SELECT * FROM human_confirmation_items WHERE id=?",(hid,)))

def list_human_confirmations(conn: DBConnection, run_id: str) -> list[dict]:
    ensure_ai_workflow_schema(conn); return [dict(r) for r in fetch_all(conn,"SELECT * FROM human_confirmation_items WHERE run_id=? ORDER BY created_at ASC, id ASC",(run_id,))]
