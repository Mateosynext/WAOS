from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ...schemas import ApiEnvelope, FlexibleSchema
from ...db import fetch_one, get_connection
from ...security import accessible_org_ids, ensure_org_access
from ..dependencies import CurrentUoW, CurrentUser
from ...ai_workflows.bot_autopilot.schemas import BotAutopilotRequest
from ...ai_workflows.bot_autopilot.service import run_bot_autopilot, run_bot_autopilot_background, start_bot_autopilot_run
from ...ai_workflows.persistence import (
    get_run,
    list_events,
    list_human_confirmations,
    list_runs,
    list_steps,
    patch_run_result,
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
    validate_run_id,
)
from ...ai_workflows.events import to_sse
from ...ai_workflows.simulation.simulator import run_simulation_suite
from ...ai_workflows.go_live.readiness import evaluate_go_live_readiness
from ...ai_workflows.go_live.release import prepare_release_plan
from ...vertical_onboarding_runtime import apply_guided_onboarding_wizard

router = APIRouter(tags=["ai-workflows"])


def _serialize_workflow(conn, run_id: str, user: dict) -> dict[str, Any]:
    run = require_authorized_run(conn, run_id, user)
    return {
        "run": run,
        "steps": list_steps(conn, run_id),
        "events": list_events(conn, run_id),
        "human_confirmations": list_human_confirmations(conn, run_id),
        "result": run.get("result_json") or {},
    }


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
    if pending:
        blockers = list(report.get("blockers") or [])
        if "pending_human_confirmations" not in blockers:
            blockers.append("pending_human_confirmations")
        report.update(
            status="blocked",
            blockers=blockers,
            can_apply=False,
            can_publish=False,
            recommended_next_action="resolve_human_confirmations",
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
    background_tasks.add_task(run_bot_autopilot_background, starter["run_id"], {"id": user.get("id"), "global_role": user.get("global_role"), "organization_ids": user.get("organization_ids", [])})
    return {"data": starter}


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
        catchup_mode = bool(last_event_id)
        idle_ticks = 0
        while True:
            with get_connection() as conn:
                run = get_run(conn, run_id)
                if not run:
                    yield "event: workflow.failed\ndata: {\"event_type\":\"workflow.failed\",\"message\":\"workflow not found\"}\n\n"
                    return
                events = list_events(conn, run_id)
                for ev in events:
                    ev_id = str(ev.get("id") or "")
                    if catchup_mode:
                        if ev_id == last_event_id:
                            catchup_mode = False
                        continue
                    if ev_id and ev_id in seen:
                        continue
                    if ev_id:
                        seen.add(ev_id)
                    yield to_sse(ev)
                if run.get("status") in TERMINAL_STATUSES:
                    return
            idle_ticks += 1
            if idle_ticks > 120:
                yield "event: workflow.keepalive\ndata: {\"event_type\":\"workflow.keepalive\"}\n\n"
                idle_ticks = 0
            time.sleep(0.25)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


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
    run = update_run(uow.conn, run_id, status="running")
    record_event(uow.conn, run_id, "workflow.resumed", "Workflow resumido")
    uow.commit()
    background_tasks.add_task(run_bot_autopilot_background, run_id, {"id": user.get("id"), "global_role": user.get("global_role"), "organization_ids": user.get("organization_ids", [])})
    return {"data": run}


@router.post("/api/v1/ai/workflows/{run_id}/rerun-failed-step", response_model=ApiEnvelope[FlexibleSchema])
def rerun_failed_step(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    require_authorized_run(uow.conn, run_id, user)
    record_event(uow.conn, run_id, "workflow.rerun_failed_step.requested", "Rerun solicitado")
    return {"data": {"run_id": run_id, "status": "queued"}}


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
    report = _compute_readiness(uow.conn, run)
    record_event(uow.conn, run_id, "go_live_readiness.completed", "Go-live readiness recalculado", 90, payload_json=report)
    return {"data": report}


@router.post("/api/v1/ai/workflows/{run_id}/human-confirmations", response_model=ApiEnvelope[FlexibleSchema])
def confirm_human_item(run_id: str, user: CurrentUser, uow: CurrentUoW, payload: dict = Body(...)) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    field_key = str(payload.get("field_key") or "").strip()
    if not field_key:
        raise HTTPException(status_code=422, detail={"code": "field_key_required", "message": "field_key is required"})
    status = str(payload.get("status") or "confirmed")
    confirmed_value = str(payload.get("confirmed_value") or "").strip()
    if status == "confirmed" and not confirmed_value:
        raise HTTPException(status_code=422, detail={"code": "confirmed_value_required", "message": "Confirmed human fields require a value"})
    item = upsert_human_confirmation(
        uow.conn,
        run_id=run_id,
        wizard_id=run.get("wizard_id"),
        bot_id=run.get("bot_id"),
        field_key=field_key,
        label=payload.get("label"),
        reason=payload.get("reason"),
        status=status,
        confirmed_value=confirmed_value,
    )
    record_event(uow.conn, run_id, "human_confirmation.updated", item.get("label", field_key), 92, payload_json=item)
    return {"data": item}


@router.post("/api/v1/ai/workflows/{run_id}/prepare-apply", response_model=ApiEnvelope[FlexibleSchema])
def prepare_apply(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    require_finished_before_launch(run)
    readiness_report = _compute_readiness(uow.conn, run)
    plan = prepare_release_plan(readiness_report)
    patch_run_result(uow.conn, run_id, "apply_plan", plan)
    record_event(uow.conn, run_id, "apply.prepared", "Apply preparado", payload_json=plan)
    return {"data": plan}


@router.post("/api/v1/ai/workflows/{run_id}/apply", response_model=ApiEnvelope[FlexibleSchema])
def apply(run_id: str, user: CurrentUser, uow: CurrentUoW, payload: dict | None = Body(default=None)) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    require_finished_before_launch(run)
    readiness_report = _compute_readiness(uow.conn, run)
    if readiness_report.get("status") == "blocked" or not readiness_report.get("can_apply"):
        raise HTTPException(status_code=409, detail={"code": "readiness_blocked", "message": "No se puede aplicar con readiness bloqueado", "readiness": readiness_report})
    if not payload or payload.get("confirm") is not True:
        raise HTTPException(status_code=409, detail={"code": "explicit_confirmation_required", "message": "Apply requiere confirm=true"})
    wizard_id = str(run.get("wizard_id") or "").strip()
    if not wizard_id:
        raise HTTPException(status_code=409, detail={"code": "wizard_required", "message": "No hay wizard generado para aplicar"})
    try:
        applied = apply_guided_onboarding_wizard(uow.conn, wizard_id=wizard_id, actor_user=user)
    except Exception as exc:
        raise HTTPException(status_code=409, detail={"code": "wizard_apply_failed", "message": str(exc)}) from exc
    applied_wizard = applied.get("wizard") if isinstance(applied, dict) else {}
    bot_id = None
    if isinstance(applied_wizard, dict):
        bot_id = applied_wizard.get("bot_id")
    bot_id = bot_id or (applied.get("bot_id") if isinstance(applied, dict) else None) or run.get("bot_id")
    if bot_id:
        update_run(uow.conn, run_id, bot_id=bot_id)
        patch_run_result(uow.conn, run_id, "bot_id", bot_id)
    result = {"run_id": run_id, "wizard_id": wizard_id, "bot_id": bot_id, "status": "applied", "release_state": "release_candidate", "wizard_apply_result": applied}
    record_event(uow.conn, run_id, "apply.completed", "Apply seguro completado", payload_json=result)
    patch_run_result(uow.conn, run_id, "apply_result", result)
    return {"data": result}


@router.post("/api/v1/ai/workflows/{run_id}/prepare-canary", response_model=ApiEnvelope[FlexibleSchema])
def canary(run_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    run = require_authorized_run(uow.conn, run_id, user)
    require_finished_before_launch(run)
    result = run.get("result_json") or {}
    if (result.get("apply_result") or {}).get("status") != "applied":
        raise HTTPException(status_code=409, detail={"code": "apply_required", "message": "Canary requires safe apply first"})
    plan = {"status": "ready_for_canary", "traffic_percent": 10, "monitor_turns": 25, "rollback_on": ["policy_violation", "hallucination_risk_high", "handoff_failure"]}
    patch_run_result(uow.conn, run_id, "canary_plan", plan)
    record_event(uow.conn, run_id, "canary.prepared", "Canary preparado", payload_json=plan)
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
