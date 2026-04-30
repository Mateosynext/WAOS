from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "backend/app/application/bot_creation_workflow_service.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "backend/app/api/routers/bots.py").read_text(encoding="utf-8")
SCHEMA = (ROOT / "backend/app/schemas/bots.py").read_text(encoding="utf-8")
FRONTEND = (ROOT / "frontend/app/actions/bots.ts").read_text(encoding="utf-8")


def test_bot_creation_workflow_has_required_persistent_phases() -> None:
    for phase in [
        "bot_created",
        "vertical_synced",
        "subvertical_pack_applied",
        "whatsapp_pending",
        "ready",
        "failed_recoverable",
    ]:
        assert phase in SERVICE
    assert "CREATE TABLE IF NOT EXISTS bot_creation_workflows" in SERVICE
    assert "failed_phase" in SERVICE
    assert "last_error" in SERVICE
    assert "client_request_id" in SERVICE


def test_bot_creation_workflow_exposes_safe_retry_endpoint() -> None:
    assert '"/api/v1/bots/creation-workflows"' in ROUTER
    assert '"/api/v1/bots/creation-workflows/{workflow_id}/retry"' in ROUTER
    assert "workflow_service.retry" in ROUTER
    assert "BotCreateWorkflowRequest" in ROUTER


def test_frontend_create_uses_workflow_endpoint_not_partial_side_effect_chain() -> None:
    create_body = FRONTEND.split("export async function createBotAction", 1)[1].split("export async function applyBotVerticalAction", 1)[0]
    assert "/api/v1/bots/creation-workflows" in create_body
    assert "/api/v1/bots`," not in create_body
    assert "syncOrganizationVertical(organizationId, vertical, subvertical)" not in create_body
    assert "applySubverticalPack(organizationId, createdBotId" not in create_body
    assert "workflowStatus !== \"ready\"" in create_body


def test_publish_now_backend_source_of_truth_when_frontend_omits_checkbox() -> None:
    assert "publish_now: bool = True" in SCHEMA
    assert "readOptionalBoolean" in FRONTEND
    create_body = FRONTEND.split("export async function createBotAction", 1)[1].split("export async function applyBotVerticalAction", 1)[0]
    assert "if (publishNow !== undefined) createPayload.publish_now = publishNow;" in create_body


def test_bot_creation_workflow_has_lease_retry_budget_and_transition_guards() -> None:
    assert "BOT_CREATION_LEASE_SECONDS" in SERVICE
    assert "BOT_CREATION_MAX_ATTEMPTS" in SERVICE
    assert "_acquire_workflow_lease" in SERVICE
    assert "bot_creation_workflow_locked" in SERVICE
    assert "bot_creation_retry_exhausted" in SERVICE
    assert "_assert_valid_transition" in SERVICE
    assert "phase_attempts_json" in SERVICE
    assert "locked_until" in SERVICE


def test_bot_creation_idempotency_is_backed_by_database_keys() -> None:
    MIGRATIONS = (ROOT / "backend/app/migrations.py").read_text(encoding="utf-8")
    REPOSITORY = (ROOT / "backend/app/repositories/bots.py").read_text(encoding="utf-8")
    assert "ux_bot_creation_workflows_org_request" in SERVICE
    assert "ux_bots_org_client_request" in SERVICE
    assert "client_request_id" in REPOSITORY
    assert "WHERE organization_id = ? AND client_request_id = ?" in REPOSITORY
    assert '_ensure_column(conn, "bots", "client_request_id", "TEXT")' in MIGRATIONS


def test_frontend_sends_stable_client_request_id_to_workflow_endpoint() -> None:
    create_body = FRONTEND.split("export async function createBotAction", 1)[1].split("export async function applyBotVerticalAction", 1)[0]
    assert "stableClientRequestId" in FRONTEND
    assert "client_request_id" in create_body
    assert "/api/v1/bots/creation-workflows" in create_body


def test_bot_creation_workflow_validates_created_bot_contract_and_subvertical_fallbacks() -> None:
    assert "def _assert_created_bot_contract" in SERVICE
    assert "bot_scope_mismatch" in SERVICE
    assert "bot_config_invalid" in SERVICE
    assert "bot_initial_publish_missing" in SERVICE
    assert "def _persist_subvertical_fallback" in SERVICE
    assert "bot.subvertical_pack_fallback_applied" in SERVICE
    assert "selected_subvertical" in SERVICE
    assert "identity[\"subvertical\"]" in SERVICE
