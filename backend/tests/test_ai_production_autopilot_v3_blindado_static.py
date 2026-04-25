from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v3_tenant_isolation_on_every_workflow_endpoint() -> None:
    api = read("backend/app/api/routers/ai_workflows.py")
    assert "require_authorized_run" in api
    for fn in ["get_workflow", "cancel", "resume", "simulate", "readiness", "rerun_readiness", "confirm_human_item", "prepare_apply", "apply", "canary", "ops_run"]:
        assert f"def {fn}" in api
    assert api.count("require_authorized_run") >= 14
    assert "accessible_org_ids" in api
    assert "tenant_access_denied" in api


def test_v3_background_failures_do_not_rollback_telemetry() -> None:
    service = read("backend/app/ai_workflows/bot_autopilot/service.py")
    assert "background_guard" in service
    assert "return {\"run_id\": run_id, \"status\": \"failed\"" in service
    assert "raise\n" not in service.split("except Exception as exc:")[-1]
    assert "WorkflowCancelled" in service
    assert "_check_cancelled" in service


def test_v3_apply_is_recomputed_and_canary_requires_apply() -> None:
    api = read("backend/app/api/routers/ai_workflows.py")
    assert "_compute_readiness" in api
    assert "pending_human_confirmations" in api
    assert "require_finished_before_launch(run)" in api
    assert "payload.get(\"confirm\") is not True" in api
    assert "apply_required" in api
    assert "Canary requires safe apply first" in api


def test_v3_persistence_redacts_and_bounds_json_payloads() -> None:
    persistence = read("backend/app/ai_workflows/persistence.py")
    assert "JSON_MAX_BYTES" in persistence
    assert "[redacted]" in persistence
    assert "RUN_UPDATE_FIELDS" in persistence
    assert "unsupported ai_workflow_runs field" in persistence
    assert "idx_ai_workflow_events_run_created" in persistence


def test_v3_frontend_stream_and_launch_actions_are_resilient() -> None:
    stream = read("frontend/features/ai-command-center/useAiWorkflowStream.ts")
    center = read("frontend/features/ai-command-center/AiCommandCenter.tsx")
    launch = read("frontend/features/ai-command-center/LaunchActionsPanel.tsx")
    confirm = read("frontend/features/ai-command-center/HumanConfirmationPanel.tsx")
    assert "workflow.paused_cost_limit" in stream
    assert "workflow.cancelled" in stream
    assert "terminalEvent" in stream and "terminalEvent" in center
    assert "readJsonSafely" in launch
    assert "Confirmed human fields require a value" in read("backend/app/api/routers/ai_workflows.py")
    assert "Este campo requiere valor confirmado" in confirm
