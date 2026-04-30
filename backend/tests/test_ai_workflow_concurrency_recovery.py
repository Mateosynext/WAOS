from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
import threading
import queue
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
PERSISTENCE_PATH = ROOT / "backend/app/ai_workflows/persistence.py"
ROUTER_PATH = ROOT / "backend/app/api/routers/ai_workflows.py"
SERVICE_PATH = ROOT / "backend/app/ai_workflows/bot_autopilot/service.py"


class DBConnection:
    def __init__(self, path: str):
        self.backend = "sqlite"
        self._connection = sqlite3.connect(path, check_same_thread=False, timeout=2, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA busy_timeout = 10000")

    def execute(self, sql: str, params: Iterable = ()):  # mirrors backend.app.db.DBConnection enough for persistence.py
        return self._connection.execute(sql, tuple(params))

    def executescript(self, script: str) -> None:
        self._connection.executescript(script)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def fetch_one(conn: DBConnection, sql: str, params: Iterable = ()) -> dict | None:
    row = conn.execute(sql, tuple(params)).fetchone()
    return dict(row) if row is not None else None


def fetch_all(conn: DBConnection, sql: str, params: Iterable = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]


def _load_persistence():
    # persistence.py has a relative import from ..db. The ZIP test environment does
    # not include the full DB migrations tree, so this injects a minimal real sqlite
    # DB adapter and executes the actual persistence module against it.
    sys.modules.pop("app.ai_workflows.persistence", None)
    app = types.ModuleType("app")
    app.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("app", app)
    ai_workflows = types.ModuleType("app.ai_workflows")
    ai_workflows.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("app.ai_workflows", ai_workflows)
    db = types.ModuleType("app.db")
    db.DBConnection = DBConnection
    db.fetch_one = fetch_one
    db.fetch_all = fetch_all
    sys.modules["app.db"] = db
    spec = importlib.util.spec_from_file_location("app.ai_workflows.persistence", PERSISTENCE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["app.ai_workflows.persistence"] = module
    spec.loader.exec_module(module)
    return module


def _tmp_db() -> str:
    handle = tempfile.NamedTemporaryFile(prefix="waos-ai-workflow-", suffix=".sqlite", delete=False)
    handle.close()
    return handle.name


def _new_conn(db_path: str) -> DBConnection:
    conn = DBConnection(db_path)
    _load_persistence().ensure_ai_workflow_schema(conn)
    conn.commit()
    return conn


def _create_running_run(persistence, conn: DBConnection, *, key: str = "request-1") -> dict:
    run = persistence.create_run(
        conn,
        organization_id="org-1",
        bot_id=None,
        user_id="user-1",
        prompt="crear bot para clinica dental con agenda y FAQs",
        intensity="balanced",
        config={"organization_id": "org-1", "user_description": "crear bot para clinica dental con agenda y FAQs"},
        idempotency_key=key,
    )
    conn.commit()
    return run


def test_two_concurrent_starts_return_same_run_id_or_conflict() -> None:
    persistence = _load_persistence()
    db_path = _tmp_db()
    conn = _new_conn(db_path)
    key = persistence._workflow_idempotency_key(
        organization_id="org-1",
        user_id="user-1",
        payload={"organization_id": "org-1", "user_description": "crear bot para clinica dental con agenda y FAQs", "client_request_id": "same-click-123"},
        explicit_key="same-click-123",
    )
    original = persistence.create_run(
        conn,
        organization_id="org-1",
        bot_id=None,
        user_id="user-1",
        prompt="crear bot para clinica dental con agenda y FAQs",
        intensity="balanced",
        config={"client_request_id": "same-click-123"},
        idempotency_key=key,
    )
    conn.commit()
    conn.close()

    start_line = threading.Barrier(2)
    results: queue.Queue[tuple[str, str]] = queue.Queue()

    def replay_start() -> None:
        local = DBConnection(db_path)
        try:
            start_line.wait(timeout=5)
            run = persistence.create_run(
                local,
                organization_id="org-1",
                bot_id=None,
                user_id="user-1",
                prompt="crear bot para clinica dental con agenda y FAQs",
                intensity="balanced",
                config={"client_request_id": "same-click-123"},
                idempotency_key=key,
            )
            local.commit()
            results.put(("ok", run["id"]))
        except Exception as exc:
            results.put(("err", str(exc)))
        finally:
            local.close()

    threads = [threading.Thread(target=replay_start, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=6)
    assert not any(thread.is_alive() for thread in threads), "concurrent start replay threads did not finish"

    messages = [results.get_nowait() for _ in range(results.qsize())]
    oks = [payload for status, payload in messages if status == "ok"]
    errs = [payload for status, payload in messages if status == "err"]
    assert len(messages) == 2
    assert oks, errs
    assert set(oks) == {original["id"]}


def test_two_concurrent_applies_execute_one_side_effect() -> None:
    persistence = _load_persistence()
    db_path = _tmp_db()
    conn = _new_conn(db_path)
    run = _create_running_run(persistence, conn, key="apply-race")
    persistence.update_run(conn, run["id"], status="completed", wizard_id="wizard-1", progress=100)
    conn.execute("CREATE TABLE apply_side_effects (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, worker TEXT NOT NULL)")
    conn.commit()
    conn.close()

    lock_committed = threading.Event()
    results: queue.Queue[str] = queue.Queue()

    def first_apply() -> None:
        local = DBConnection(db_path)
        try:
            action = persistence.start_workflow_action(local, run["id"], "apply")
            local.commit()
            assert not action.get("_already_in_progress")
            lock_committed.set()
            time.sleep(0.15)
            local.execute("INSERT INTO apply_side_effects (run_id, worker) VALUES (?, ?)", (run["id"], "first"))
            persistence.complete_workflow_action(local, run["id"], "apply", {"status": "applied", "worker": "first"}, status="completed")
            local.commit()
            results.put("applied")
        except Exception as exc:
            results.put(f"err:{exc}")
        finally:
            local.close()

    def second_apply() -> None:
        local = DBConnection(db_path)
        try:
            assert lock_committed.wait(timeout=5)
            action = persistence.start_workflow_action(local, run["id"], "apply")
            local.commit()
            if action.get("status") == "completed":
                results.put("completed_replay")
            elif action.get("_already_in_progress"):
                results.put("conflict")
            else:
                local.execute("INSERT INTO apply_side_effects (run_id, worker) VALUES (?, ?)", (run["id"], "second"))
                persistence.complete_workflow_action(local, run["id"], "apply", {"status": "applied", "worker": "second"}, status="completed")
                local.commit()
                results.put("applied_second")
        except Exception as exc:
            results.put(f"err:{exc}")
        finally:
            local.close()

    threads = [threading.Thread(target=first_apply, daemon=True), threading.Thread(target=second_apply, daemon=True)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=6)
    assert not any(thread.is_alive() for thread in threads), "concurrent apply threads did not finish"

    outcomes = [results.get_nowait() for _ in range(results.qsize())]
    verify = DBConnection(db_path)
    count = verify.execute("SELECT COUNT(*) AS count FROM apply_side_effects").fetchone()["count"]
    action = persistence.get_workflow_action(verify, run["id"], "apply")
    verify.close()
    assert count == 1
    assert action and action["status"] == "completed"
    assert outcomes.count("applied") == 1
    assert "conflict" in outcomes or "completed_replay" in outcomes
    assert all(not item.startswith("err:") for item in outcomes)


def test_refresh_during_run_recovers_snapshot_from_committed_state() -> None:
    persistence = _load_persistence()
    db_path = _tmp_db()
    conn = _new_conn(db_path)
    run = _create_running_run(persistence, conn, key="refresh-mid-run")
    persistence.upsert_step(conn, run["id"], "vertical.detected", "Vertical detectada", "completed", output_json={"vertical_id": "salud"})
    persistence.patch_run_result(conn, run["id"], "vertical.detected", {"vertical_id": "salud"})
    persistence.record_event(conn, run["id"], "vertical.detected", "Vertical detectada", 10, payload_json={"vertical_id": "salud"})
    persistence.update_run(conn, run["id"], current_step="vertical.detected", progress=10)
    conn.commit()
    conn.close()

    refreshed = DBConnection(db_path)
    snapshot = persistence.get_run(refreshed, run["id"])
    steps = persistence.list_steps(refreshed, run["id"])
    events = persistence.list_events(refreshed, run["id"])
    refreshed.close()

    assert snapshot is not None
    assert snapshot["status"] == "running"
    assert snapshot["current_step"] == "vertical.detected"
    assert snapshot["progress"] == 10
    assert (snapshot["result_json"] or {}).get("vertical.detected", {}).get("vertical_id") == "salud"
    assert any(step["step_key"] == "vertical.detected" for step in steps)
    assert any(event["event_type"] == "vertical.detected" for event in events)


def test_chaos_worker_crash_reaper_marks_retryable_failed_and_rerun_claims() -> None:
    persistence = _load_persistence()
    db_path = _tmp_db()
    conn = _new_conn(db_path)
    run = _create_running_run(persistence, conn, key="chaos-crash")
    claimed = persistence.claim_workflow_run_execution(conn, run["id"], worker_id="worker-before-crash", lease_seconds=60)
    assert claimed["_worker_claimed"] is True
    persistence.record_event(conn, run["id"], "intent.normalized", "first side of crash", 5)
    old = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    conn.execute("UPDATE ai_workflow_runs SET heartbeat_at=?, updated_at=? WHERE id=?", (old, old, run["id"]))
    conn.commit()
    conn.close()  # simulated backend/worker death: no terminal status was written

    reaper = DBConnection(db_path)
    recovered = persistence.recover_stale_running_runs(reaper, stale_after_minutes=5, limit=10)
    reaper.commit()
    assert len(recovered) == 1
    recovered_run = persistence.get_run(reaper, run["id"])
    assert recovered_run["status"] == "retryable_failed"
    event_types = [event["event_type"] for event in persistence.list_events(reaper, run["id"])]
    assert "workflow.stale_detected" in event_types
    assert "workflow.retryable_failed" in event_types

    persistence.update_run(reaper, run["id"], status="running", worker_id=None, heartbeat_at=None, completed_at=None, retry_count=int(recovered_run.get("retry_count") or 0) + 1)
    rerun_claim = persistence.claim_workflow_run_execution(reaper, run["id"], worker_id="worker-after-restart", lease_seconds=60)
    reaper.commit()
    reaper.close()
    assert rerun_claim["_worker_claimed"] is True
    assert rerun_claim["status"] == "running"
    assert rerun_claim["worker_id"] == "worker-after-restart"


def test_router_and_worker_have_recovery_and_apply_lock_guards() -> None:
    router = ROUTER_PATH.read_text(encoding="utf-8")
    service = SERVICE_PATH.read_text(encoding="utf-8")
    assert "mark_stale_running_runs" in router
    assert "promote_stale_runs_to_retryable_failed" in router
    assert "retryable_failed" in router
    apply_body = router.split("def apply(run_id", 1)[1].split("@router.post", 1)[0]
    assert "uow.commit()" in apply_body.split("applied = apply_guided_onboarding_wizard", 1)[0]
    assert "claim_workflow_run_execution" in service
    assert "touch_run_heartbeat" in service
    assert "workflow.worker_claim_rejected" in service



def test_apply_and_canary_routes_have_idempotent_action_locks() -> None:
    router = ROUTER_PATH.read_text(encoding="utf-8")
    apply_body = router.split("def apply(", 1)[1].split("@router.post(\"/api/v1/ai/workflows/{run_id}/prepare-canary\"", 1)[0]
    canary_body = router.split("def canary(", 1)[1].split("@router.get(\"/api/v1/internal/ai-ops/runs\"", 1)[0]

    assert "_verify_apply_confirmation" in apply_body
    assert "start_workflow_action(uow.conn, run_id, \"apply\")" in apply_body
    assert "apply_already_in_progress" in apply_body
    assert "complete_workflow_action(uow.conn, run_id, \"apply\", result, status=\"completed\")" in apply_body
    assert apply_body.index("uow.commit()") < apply_body.index("applied = apply_guided_onboarding_wizard")

    assert "start_workflow_action(uow.conn, run_id, \"prepare_canary\")" in canary_body
    assert "canary_already_in_progress" in canary_body
    assert "complete_workflow_action(uow.conn, run_id, \"prepare_canary\", plan, status=\"completed\")" in canary_body
    assert "idempotent" in canary_body
