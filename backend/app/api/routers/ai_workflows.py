from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from ...schemas import ApiEnvelope, FlexibleSchema
from ...config import settings
from ...db import fetch_one, get_connection
from ...security import accessible_org_ids, ensure_org_access
from ..dependencies import CurrentUoW, CurrentUser
from ...ai_workflows.bot_autopilot.schemas import BotAutopilotRequest
from ...ai_workflows.bot_autopilot.service import run_bot_autopilot, run_bot_autopilot_background, start_bot_autopilot_run
from ...ai_workflows.persistence import (
    event_cursor_exists,
    get_latest_event_id,
    get_run,
    list_events,
    list_events_after,
    list_human_confirmations,
    list_runs,
    list_steps,
    patch_run_result,
    recover_stale_running_runs,
    mark_stale_running_runs,
    promote_stale_runs_to_retryable_failed,
    start_workflow_action,
    complete_workflow_action,
    record_event,
    save_go_live_readiness,
    save_simulation_report,
    update_run,
    upsert_human_confirmation,
)
from ...ai_workflows.hardening import (
    TERMINAL_STATUSES,
    pending_human_confirmations,
    require_authorized_run,
    require_finished_before_launch,
    require_not_terminal,
    validate_confirmation_status,
    validate_run_id,
)
from ...ai_workflows.events import to_sse
from ...ai_workflows.simulation.simulator import run_simulation_suite
from ...ai_workflows.go_live.readiness import evaluate_go_live_readiness
from ...ai_workflows.go_live.release import prepare_release_plan
from ...vertical_onboarding_runtime import apply_guided_onboarding_wizard

router = APIRouter(tags=["ai-workflows"])


class HumanConfirmationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    field_key: str = Field(..., min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")
    status: str = Field(default="confirmed", max_length=64)
    confirmed_value: str | None = Field(default=None, max_length=10000)
    label: str | None = Field(default=None, max_length=240)
    reason: str | None = Field(default=None, max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=180)
    audit_note: str | None = Field(default=None, max_length=2000)


def _b64url_encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> dict[str, Any]:
    padded = value + "=" * (-len(value) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    decoded = json.loads(raw.decode("utf-8"))
    return decoded if isinstance(decoded, dict) else {}


def _sign_apply_confirmation(run: dict[str, Any], readiness_report: dict[str, Any]) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "scope": "ai_workflow_apply",
        "run_id": str(run.get("id") or ""),
        "wizard_id": str(run.get("wizard_id") or ""),
        "status": str(run.get("status") or ""),
        "readiness_status": str(readiness_report.get("status") or ""),
        "readiness_score": readiness_report.get("score"),
        "can_apply": bool(readiness_report.get("can_apply")),
        "iat": now,
        "exp": now + 30 * 60,
    }
    body = _b64url_encode(payload)
    sig = hmac.new(settings.app_secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _verify_apply_confirmation(token: str, run: dict[str, Any], readiness_report: dict[str, Any]) -> None:
    try:
        body, sig = str(token or "").split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "invalid_apply_confirmation_token", "message": "Apply requiere confirmation_token emitido por prepare-apply"}) from exc
    expected = hmac.new(settings.app_secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=409, detail={"code": "invalid_apply_confirmation_token", "message": "confirmation_token signature mismatch"})
    data = _b64url_decode(body)
    now = int(datetime.now(timezone.utc).timestamp())
    if int(data.get("exp") or 0) < now:
        raise HTTPException(status_code=409, detail={"code": "expired_apply_confirmation_token", "message": "confirmation_token expired; run prepare-apply again"})
    checks = {
        "scope": data.get("scope") == "ai_workflow_apply",
        "run_id": data.get("run_id") == str(run.get("id") or ""),
        "wizard_id": data.get("wizard_id") == str(run.get("wizard_id") or ""),
        "status": data.get("status") == str(run.get("status") or ""),
        "readiness_status": data.get("readiness_status") == str(readiness_report.get("status") or ""),
        "can_apply": bool(data.get("can_apply")) is bool(readiness_report.get("can_apply")),
    }
    if not all(checks.values()):
        raise HTTPException(status_code=409, detail={"code": "stale_apply_confirmation_token", "message": "confirmation_token does not match current run/readiness state", "failed_checks": [k for k, ok in checks.items() if not ok]})


def _request_idempotency_key(payload: dict | None, *, fallback: str) -> str:
    key = str((payload or {}).get("idempotency_key") or "").strip()
    if key:
        return key[:180]
    return hashlib.sha256(fallback.encode("utf-8")).hexdigest()


def _serialize_workflow(conn, run_id: str, user: dict) -> dict[str, Any]:
    run = require_authorized_run(conn, run_id, user)
    return {
        "run": run,
        "steps": list_steps(conn, run_id),
        "events": list_events(conn, run_id),
        "human_confirmations": list_human_confirmations(conn, run_id),
        "result": run.get("result_json") or {},
    }


def _materialize_human_confirmations(conn, run: dict[str, Any]) -> dict[str, Any]:
    run_id = str(run["id"])
    confirmations = list_human_confirmations(conn, run_id)
    applied: dict[str, Any] = {}
    for item in confirmations:
        status = str(item.get("status") or "pending")
        if status in {"confirmed", "range_confirmed", "deferred_safe", "not_applicable", "escalate_to_human", "blocked_response"}:
            key = str(item.get("field_key") or "").strip()
            if not key:
                continue
            applied[key] = {
                "status": status,
                "label": item.get("label"),
                "value": item.get("confirmed_value") or item.get("suggested_value"),
                "updated_at": item.get("updated_at"),
            }
    patch_run_result(conn, run_id, "human_confirmations_applied", applied)
    latest = get_run(conn, run_id) or run
    return latest


def _compute_readiness(conn, run: dict[str, Any]) -> dict[str, Any]:
    run_id = str(run["id"])
    result = run.get("result_json") or {}
    confirmations = list_human_confirmations(conn, run_id)
    handoff = next((item for item in confirmations if item.get("field_key") == "human_handoff_destination" and item.get("status") in {"confirmed", "escalate_to_human"}), None)
    report = evaluate_go_live_readiness(
        wizard=result.get("wizard") or {},
        dry_run_result=(result.get("dry_run.completed") or {}).get("dry_run_result") or result.get("dry_run_result") or {},
        validation_snapshot=result.get("validation_snapshot") or {},
        simulation_report=result.get("simulation_report") or {},
        knowledge_plan=result.get("knowledge_plan") or {},
        tool_execution_plan=result.get("tool_execution_plan") or {},
        policy_pack=result.get("agent_policy_pack") or {},
        human_handoff_config={"destination": handoff.get("confirmed_value") or handoff.get("suggested_value")} if handoff else None,
    )
    pending = pending_human_confirmations(confirmations)
    wizard_id = str(run.get("wizard_id") or result.get("wizard_id") or "").strip()
    blockers = list(report.get("blockers") or [])
    if not wizard_id:
        if "wizard_required" not in blockers:
            blockers.append("wizard_required")
    if run.get("status") == "completed_partial":
        if "partial_completion_requires_override" not in blockers:
            blockers.append("partial_completion_requires_override")
    if pending:
        if "pending_human_confirmations" not in blockers:
            blockers.append("pending_human_confirmations")
    if blockers:
        report.update(
            status="blocked",
            blockers=blockers,
            can_apply=False,
            can_publish=False,
            recommended_next_action="generate_wizard" if "wizard_required" in blockers else "request_partial_apply_waiver" if "partial_completion_requires_override" in blockers else "resolve_human_confirmations",
        )
    save_go_live_readiness(conn, run_id=run_id, wizard_id=run.get("wizard_id"), bot_id=run.get("bot_id"), report=report)
    patch_run_result(conn, run_id, "go_live_readiness", report)
    return report




@router.get("/api/v1/ai/bot-autopilot/health", response_model=ApiEnvelope[FlexibleSchema])
def bot_autopilot_health(user: CurrentUser, uow: CurrentUoW) -> dict:
    # Authenticated health check for frontend preflight/debugging. It also
    # initializes the workflow tables so a first production run cannot fail
    # simply because the AI workflow schema has not been touched yet.
    from ...ai_workflows.persistence import ensure_ai_workflow_schema

    ensure_ai_workflow_schema(uow.conn)
    return {
        "data": {
            "status": "ready",
            "router": "ai-workflows",
            "start_endpoint": "/api/v1/ai/bot-autopilot",
            "events_endpoint": "/api/v1/ai/workflows/{run_id}/events",
            "apply_endpoint": "/api/v1/ai/workflows/{run_id}/apply",
            "recovery_scan_endpoint": "/api/v1/ai/workflow-recovery/stale-runs",
        }
    }

@router.post("/api/v1/ai/bot-autopilot", response_model=ApiEnvelope[FlexibleSchema])
def bot_autopilot(payload: BotAutopilotRequest, background_tasks: BackgroundTasks, user: CurrentUser, uow: CurrentUoW, async_mode: bool = Query(True)) -> dict:
    ensure_org_access(user, payload.organization_id)
    if not async_mode:
        result = run_bot_autopilot(uow.conn, payload, user=user)
        return {"data": result}
    starter = start_bot_autopilot_run(uow.conn, payload, user=user)
    uow.commit()
    if starter.get("enqueue_worker", True):
        background_tasks.add_task(run_bot_autopilot_background, starter["run_id"], {"id": user.get("id"), "global_role": user.get("global_role"), "organization_ids": user.get("organization_ids", [])})
    return {"data": starter}


@router.post("/api/v1/ai/workflow-recovery/stale-runs", response_model=ApiEnvelope[FlexibleSchema])
def recover_stale_workflows(user: CurrentUser, uow: CurrentUoW, stale_after_minutes: int = Query(30), limit: int = Query(50)) -> dict:
    org_ids = accessible_org_ids(user)
    stale = mark_stale_running_runs(uow.conn, organization_ids=org_ids, stale_after_minutes=stale_after_minutes, limit=limit)
    retryable_failed = promote_stale_runs_to_retryable_failed(uow.conn, organization_ids=org_ids, limit=limit)
    return {"data": {"count": len(retryable_failed), "stale_count": len(stale), "retryable_failed_count": len(retryable_failed), "recovered": retryable_failed, "stale": stale, "stale_after_minutes": max(1, min(int(stale_after_minutes or 30), 24 * 60))}}


@router.get("/api/v1/ai/workflows/{run_id}", response_model=ApiEnvelope[FlexibleSchema])
def get_workflow(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return {"data": _serialize_workflow(uow.conn, run_id, user)}


@router.get("/api/v1/ai/workflows/{run_id}/events")
def workflow_events(run_id: str, request: Request, user: CurrentUser):
    run_id = validate_run_id(run_id)
    with get_connection() as conn:
        require_authorized_run(conn, run_id, user)
    last_event_id = request.headers.get("last-event-id") or request.query_params.get("last_event_id")

    def gen():
        seen: set[str] = set()
        resume_after_id = str(last_event_id or "").strip()
        cursor_checked = False
        idle_ticks = 0
        while True:
            with get_connection() as conn:
                run = get_run(conn, run_id)
                if not run:
                    yield "event: workflow.failed\ndata: {\"event_type\":\"workflow.failed\",\"message\":\"workflow not found\"}\n\n"
                    return
                if resume_after_id and not cursor_checked:
                    cursor_checked = True
                    if not event_cursor_exists(conn, run_id, resume_after_id):
                        latest_event_id = get_latest_event_id(conn, run_id)
                        yield to_sse({
                            "event_type": "workflow.cursor_not_found",
                            "message": "Last-Event-ID desconocido; no se reenvia todo el stream. El cliente debe recuperar snapshot.",
                            "payload_json": {"requested_last_event_id": resume_after_id, "resume_from_tail": bool(latest_event_id)},
                        })
                        resume_after_id = latest_event_id or ""
                events = list_events_after(conn, run_id, resume_after_id, limit=100)
                for ev in events:
                    ev_id = str(ev.get("id") or "")
                    if ev_id and ev_id in seen:
                        continue
                    if ev_id:
                        seen.add(ev_id)
                        resume_after_id = ev_id
                    yield to_sse(ev)
                if run.get("status") in TERMINAL_STATUSES:
                    return
            idle_ticks += 1
            if idle_ticks > 40:
                # Keep intermediaries from treating an idle but healthy workflow stream as dead.
                yield 'data: {"event_type":"workflow.keepalive","message":"keepalive"}\n\n'
                idle_ticks = 0
            time.sleep(0.25)
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/v1/ai/workflows/{run_id}/cancel", response_model=ApiEnvelope[FlexibleSchema])
def cancel(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    if run.get("status") in {"completed", "completed_partial"}:
        raise HTTPException(status_code=409, detail={"code": "workflow_already_finished", "message": "Completed workflows cannot be cancelled"})
    run = update_run(uow.conn, run_id, status="cancelled")
    record_event(uow.conn, run_id, "workflow.cancelled", "Workflow cancelado")
    return {"data": run}


@router.post("/api/v1/ai/workflows/{run_id}/resume", response_model=ApiEnvelope[FlexibleSchema])
def resume(run_id: str, background_tasks: BackgroundTasks, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    if run.get("status") in {"completed", "completed_partial"}:
        raise HTTPException(status_code=409, detail={"code": "workflow_already_finished", "message": "Completed workflows cannot be resumed"})
    if run.get("status") == "running":
        raise HTTPException(status_code=409, detail={"code": "workflow_already_running", "message": "Workflow is already running; resume would create a duplicate worker"})
    if run.get("status") not in {"failed", "retryable_failed", "cancelled", "paused_cost_limit"}:
        raise HTTPException(status_code=409, detail={"code": "workflow_resume_not_allowed", "message": f"Cannot resume workflow in status {run.get('status')}"})
    retry_count = int(run.get("retry_count") or 0) + 1
    run = update_run(uow.conn, run_id, status="running", retry_count=retry_count, worker_id=None, heartbeat_at=None, completed_at=None)
    record_event(uow.conn, run_id, "workflow.resumed", "Workflow resumido")
    uow.commit()
    background_tasks.add_task(run_bot_autopilot_background, run_id, {"id": user.get("id"), "global_role": user.get("global_role"), "organization_ids": user.get("organization_ids", [])})
    return {"data": run}


@router.post("/api/v1/ai/workflows/{run_id}/rerun-failed-step", response_model=ApiEnvelope[FlexibleSchema])
def rerun_failed_step(run_id: str, background_tasks: BackgroundTasks, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    if run.get("status") == "running":
        raise HTTPException(status_code=409, detail={"code": "workflow_already_running", "message": "Workflow is already running; rerun would create a duplicate worker"})
    if run.get("status") not in {"failed", "retryable_failed"}:
        raise HTTPException(status_code=409, detail={"code": "workflow_rerun_not_allowed", "message": f"rerun-failed-step requires failed/retryable_failed status, got {run.get('status')}"})
    progress = max(1, int(run.get("progress") or 1))
    retry_count = int(run.get("retry_count") or 0) + 1
    update_run(uow.conn, run_id, status="running", current_step="workflow.rerun_failed_step", progress=progress, completed_at=None, error_json={}, retry_count=retry_count, worker_id=None, heartbeat_at=None)
    record_event(uow.conn, run_id, "workflow.rerun_failed_step.requested", "Rerun solicitado y worker encolado", progress, payload_json={"previous_status": "failed"})
    uow.commit()
    background_tasks.add_task(run_bot_autopilot_background, run_id, {"id": user.get("id"), "global_role": user.get("global_role"), "organization_ids": user.get("organization_ids", [])})
    return {"data": {"run_id": run_id, "status": "running", "worker_enqueued": True}}


@router.post("/api/v1/ai/workflows/{run_id}/simulate", response_model=ApiEnvelope[FlexibleSchema])
def simulate(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    result_json = run.get("result_json") or {}
    pack = result_json.get("vertical_pack.generated") or result_json.get("vertical_profile") or {}
    wizard = result_json.get("wizard") or (result_json.get("wizard.created") or {}).get("wizard") or {}
    result = run_simulation_suite(pack, wizard, 8)
    save_simulation_report(uow.conn, run_id=run_id, wizard_id=run.get("wizard_id"), bot_id=run.get("bot_id"), report=result)
    patch_run_result(uow.conn, run_id, "simulation_report", result)
    record_event(uow.conn, run_id, "simulation.completed", "Simulation rerun completada", 84, payload_json=result)
    return {"data": result}


@router.get("/api/v1/ai/workflows/{run_id}/simulation-report", response_model=ApiEnvelope[FlexibleSchema])
def simulation_report(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    return {"data": (run.get("result_json") or {}).get("simulation_report", {})}


@router.get("/api/v1/ai/workflows/{run_id}/go-live-readiness", response_model=ApiEnvelope[FlexibleSchema])
def readiness(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    return {"data": (run.get("result_json") or {}).get("go_live_readiness", {})}


@router.post("/api/v1/ai/workflows/{run_id}/go-live-readiness", response_model=ApiEnvelope[FlexibleSchema])
def rerun_readiness(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    run = _materialize_human_confirmations(uow.conn, run)
    report = _compute_readiness(uow.conn, run)
    record_event(uow.conn, run_id, "go_live_readiness.completed", "Go-live readiness recalculado", 90, payload_json=report)
    return {"data": report}


@router.post("/api/v1/ai/workflows/{run_id}/human-confirmations", response_model=ApiEnvelope[FlexibleSchema])
def confirm_human_item(run_id: str, user: CurrentUser, uow: CurrentUoW, payload: HumanConfirmationPayload = Body(...)) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    payload_data = payload.model_dump(exclude_none=True)
    field_key = payload.field_key.strip()
    status = validate_confirmation_status(payload.status or "confirmed")
    confirmed_value = str(payload.confirmed_value or "").strip()
    if status == "confirmed" and not confirmed_value:
        raise HTTPException(status_code=422, detail={"code": "confirmed_value_required", "message": "Confirmed human fields require a value"})
    item = upsert_human_confirmation(
        uow.conn,
        run_id=run_id,
        wizard_id=run.get("wizard_id"),
        bot_id=run.get("bot_id"),
        field_key=field_key,
        label=payload.label,
        reason=payload.reason,
        status=status,
        confirmed_value=confirmed_value,
    )
    _materialize_human_confirmations(uow.conn, run)
    record_event(uow.conn, run_id, "human_confirmation.updated", item.get("label", field_key), 92, payload_json={**item, "actor_user_id": user.get("id"), "audit_note": payload.audit_note, "idempotency_key": payload.idempotency_key, "request": payload_data})
    return {"data": item}


@router.post("/api/v1/ai/workflows/{run_id}/prepare-apply", response_model=ApiEnvelope[FlexibleSchema])
def prepare_apply(run_id: str, user: CurrentUser, uow: CurrentUoW, payload: dict | None = Body(default=None)) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    allow_partial = bool((payload or {}).get("explicit_partial_apply_override"))
    require_finished_before_launch(run, allow_partial_override=allow_partial)
    run = _materialize_human_confirmations(uow.conn, run)
    readiness_report = _compute_readiness(uow.conn, run)
    if allow_partial and run.get("status") == "completed_partial":
        readiness_report = dict(readiness_report)
        readiness_report["partial_apply_override"] = True
        readiness_report["blockers"] = [item for item in readiness_report.get("blockers", []) if item != "partial_completion_requires_override"]
        if not readiness_report["blockers"]:
            readiness_report.update(status="ready", can_apply=True)
    if readiness_report.get("status") == "blocked" or not readiness_report.get("can_apply"):
        raise HTTPException(status_code=409, detail={"code": "readiness_blocked", "message": "No se puede preparar apply con readiness bloqueado", "readiness": readiness_report})
    plan = prepare_release_plan(readiness_report)
    plan["confirmation_token"] = _sign_apply_confirmation(run, readiness_report)
    plan["confirmation_token_expires_in_seconds"] = 30 * 60
    plan["requires_confirmation_token"] = True
    patch_run_result(uow.conn, run_id, "apply_plan", plan)
    record_event(uow.conn, run_id, "apply.prepared", "Apply preparado con confirmation_token firmado", payload_json={k: v for k, v in plan.items() if k != "confirmation_token"})
    return {"data": plan}

@router.post("/api/v1/ai/workflows/{run_id}/apply", response_model=ApiEnvelope[FlexibleSchema])
def apply(run_id: str, user: CurrentUser, uow: CurrentUoW, payload: dict | None = Body(default=None)) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    payload = payload or {}
    allow_partial = bool(payload.get("explicit_partial_apply_override"))
    require_finished_before_launch(run, allow_partial_override=allow_partial)
    existing_apply = (run.get("result_json") or {}).get("apply_result") or {}
    if existing_apply.get("status") == "applied":
        return {"data": existing_apply}
    run = _materialize_human_confirmations(uow.conn, run)
    readiness_report = _compute_readiness(uow.conn, run)
    if allow_partial and run.get("status") == "completed_partial":
        readiness_report = dict(readiness_report)
        readiness_report["partial_apply_override"] = True
        readiness_report["blockers"] = [item for item in readiness_report.get("blockers", []) if item != "partial_completion_requires_override"]
        if not readiness_report["blockers"]:
            readiness_report.update(status="ready", can_apply=True)
    if readiness_report.get("status") == "blocked" or not readiness_report.get("can_apply"):
        raise HTTPException(status_code=409, detail={"code": "readiness_blocked", "message": "No se puede aplicar con readiness bloqueado", "readiness": readiness_report})
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=409, detail={"code": "explicit_confirmation_required", "message": "Apply requiere confirm=true"})
    _verify_apply_confirmation(str(payload.get("confirmation_token") or ""), run, readiness_report)
    apply_idempotency_key = _request_idempotency_key(payload, fallback=f"{run_id}:{payload.get('confirmation_token')}")
    wizard_id = str(run.get("wizard_id") or "").strip()
    if not wizard_id:
        raise HTTPException(status_code=409, detail={"code": "wizard_required", "message": "No hay wizard generado para aplicar"})
    action = start_workflow_action(uow.conn, run_id, "apply")
    if action.get("status") == "completed":
        return {"data": action.get("result_json") or existing_apply}
    if action.get("_already_in_progress"):
        raise HTTPException(status_code=409, detail={"code": "apply_already_in_progress", "message": "Apply is already in progress for this run"})
    # Persist the apply lock before executing the non-idempotent side effect.
    # A second tab/request will now observe in_progress/completed instead of
    # racing into apply_guided_onboarding_wizard.
    uow.commit()
    try:
        applied = apply_guided_onboarding_wizard(uow.conn, wizard_id=wizard_id, actor_user=user)
    except Exception as exc:
        complete_workflow_action(uow.conn, run_id, "apply", {"status": "failed", "error": str(exc)}, status="failed")
        uow.commit()
        raise HTTPException(status_code=409, detail={"code": "wizard_apply_failed", "message": str(exc)}) from exc
    applied_wizard = applied.get("wizard") if isinstance(applied, dict) else {}
    bot_id = None
    if isinstance(applied_wizard, dict):
        bot_id = applied_wizard.get("bot_id")
    bot_id = bot_id or (applied.get("bot_id") if isinstance(applied, dict) else None) or run.get("bot_id")
    if bot_id:
        update_run(uow.conn, run_id, bot_id=bot_id)
        patch_run_result(uow.conn, run_id, "bot_id", bot_id)
    result = {"run_id": run_id, "wizard_id": wizard_id, "bot_id": bot_id, "status": "applied", "release_state": "release_candidate", "idempotency_key": apply_idempotency_key, "partial_apply_override": allow_partial, "wizard_apply_result": applied}
    record_event(uow.conn, run_id, "apply.completed", "Apply seguro completado", payload_json=result)
    patch_run_result(uow.conn, run_id, "apply_result", result)
    complete_workflow_action(uow.conn, run_id, "apply", result, status="completed")
    return {"data": result}


@router.post("/api/v1/ai/workflows/{run_id}/prepare-canary", response_model=ApiEnvelope[FlexibleSchema])
def canary(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    require_finished_before_launch(run)
    result = run.get("result_json") or {}
    if (result.get("apply_result") or {}).get("status") != "applied":
        raise HTTPException(status_code=409, detail={"code": "apply_required", "message": "Canary requires safe apply first"})
    existing_plan = result.get("canary_plan") or {}
    if existing_plan.get("status") == "ready_for_canary":
        return {"data": {**existing_plan, "idempotent": True}}
    action = start_workflow_action(uow.conn, run_id, "prepare_canary")
    if action.get("status") == "completed":
        return {"data": action.get("result_json") or existing_plan}
    if action.get("_already_in_progress"):
        raise HTTPException(status_code=409, detail={"code": "canary_already_in_progress", "message": "Prepare canary is already in progress for this run"})
    plan = {"status": "ready_for_canary", "traffic_percent": 10, "monitor_turns": 25, "rollback_on": ["policy_violation", "hallucination_risk_high", "handoff_failure"], "depends_on_apply_result": (result.get("apply_result") or {}).get("idempotency_key")}
    patch_run_result(uow.conn, run_id, "canary_plan", plan)
    record_event(uow.conn, run_id, "canary.prepared", "Canary preparado", payload_json=plan)
    complete_workflow_action(uow.conn, run_id, "prepare_canary", plan, status="completed")
    return {"data": plan}


@router.get("/api/v1/internal/ai-ops/runs", response_model=ApiEnvelope[FlexibleSchema])
def ops_runs(user: CurrentUser, uow: CurrentUoW) -> dict:
    org_ids = None if user.get("global_role") == "super_admin" else accessible_org_ids(user)
    return {"data": {"runs": list_runs(uow.conn, 100, organization_ids=org_ids)}}


@router.get("/api/v1/internal/ai-ops/runs/{run_id}", response_model=ApiEnvelope[FlexibleSchema])
def ops_run(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return {"data": _serialize_workflow(uow.conn, run_id, user)}


@router.get("/api/v1/internal/ai-ops/runtime-turns/{turn_id}", response_model=ApiEnvelope[FlexibleSchema])
def runtime_turn(turn_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    row = fetch_one(uow.conn, "SELECT * FROM ai_runtime_turn_inspections WHERE turn_id=? OR id=?", (turn_id, turn_id))
    if row and user.get("global_role") != "super_admin" and row.get("organization_id") not in user.get("organization_ids", []):
        raise HTTPException(status_code=403, detail={"code": "tenant_access_denied", "message": "No access to this runtime turn"})
    return {"data": row or {"turn_id": turn_id, "status": "not_found"}}
