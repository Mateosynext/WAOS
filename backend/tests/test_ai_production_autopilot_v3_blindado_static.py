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




def test_v3_persistence_preserves_json_nulls_for_optional_ids() -> None:
    persistence = read("backend/app/ai_workflows/persistence.py")
    assert "if v is None: return None" in persistence
    assert "optional ids such as bot_id/vertical_id" in persistence
    assert "if v is None: return {}" not in persistence

def test_v3_frontend_stream_and_launch_actions_are_resilient() -> None:
    stream = read("frontend/features/ai-command-center/useAiWorkflowStream.ts")
    center = read("frontend/features/ai-command-center/AiCommandCenter.tsx")
    assert "workflow.paused_cost_limit" in stream
    assert "workflow.cancelled" in stream
    assert "terminalEvent" in stream and "terminalEvent" in center
    assert "GODMODE_ENABLED" in center
    assert "auto_apply: false" in center
    assert "safety_warnings" in center
    assert "Confirmed human fields require a value" in read("backend/app/api/routers/ai_workflows.py")

def test_v3_guided_apply_requires_fresh_dry_run_before_bot_creation() -> None:
    runtime = read("backend/app/vertical_onboarding_runtime.py")
    assert "def _require_fresh_guided_onboarding_apply_validation" in runtime
    assert "validation_hash" in runtime and "dry_run_blocked" in runtime
    apply_body = runtime.split("def apply_guided_onboarding_wizard", 1)[1]
    assert "_require_fresh_guided_onboarding_apply_validation(wizard)" in apply_body
    assert apply_body.index("_require_fresh_guided_onboarding_apply_validation(wizard)") < apply_body.index("if not bot_row:")


def test_v3_autopilot_godmode_is_normalized_not_rejected() -> None:
    schema = read("backend/app/ai_workflows/bot_autopilot/schemas.py")
    service = read("backend/app/ai_workflows/bot_autopilot/service.py")
    assert "def _normalize_feature_gates" in schema
    assert "godmode_disabled_downgraded_to_savage" in schema
    assert "invalid_intensity_downgraded_to_balanced" in schema
    assert "raise PydanticCustomError" not in schema
    assert "godmode requires AI_ENABLE_GODMODE=true" not in schema
    assert "effective_intensity" in service
    assert "requested_intensity" in service
    assert "safety_warnings" in service
    assert "unselected optional id as `{}`" in schema
    assert '("id", "bot_id", "organization_id", "value")' in schema


def test_v3_autopilot_payload_ids_are_sanitized_before_submit() -> None:
    schema = read("backend/app/ai_workflows/bot_autopilot/schemas.py")
    center = read("frontend/features/ai-command-center/AiCommandCenter.tsx")
    assert "cleanOptionalString" in center
    assert "bot_id: cleanOptionalString(payload.bot_id)" in center
    assert "vertical_id: cleanOptionalString(payload.vertical_id)" in center
    assert "return None if not value else value" in schema


def test_global_error_renderer_has_last_line_of_defense_for_validation_ctx() -> None:
    errors = read("backend/app/errors.py")
    assert "def _json_safe" in errors
    assert "BaseException" in errors
    assert "exc.errors()" in errors and "_json_safe(exc.errors())" in errors
    assert "Last line of defense" in errors


def test_v3_optional_id_normalizer_rejects_boolean_ids_and_tolerates_option_objects() -> None:
    schema = read("backend/app/ai_workflows/bot_autopilot/schemas.py")
    assert "ValidationInfo" in schema
    assert 'info.field_name == "organization_id"' in schema
    assert "rich option objects" in schema
    assert "return value if info.field_name == \"organization_id\" else None" in schema
    assert "elif isinstance(candidate, bool)" in schema
