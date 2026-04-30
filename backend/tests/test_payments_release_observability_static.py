from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_legacy_payment_route_delegates_to_tool_execution_contract():
    source = read("app/api/handlers/crm_sales.py")
    assert "payment_requires_preview_execution_id" in source
    assert "payment_requires_confirmation_token" in source
    assert "payment_requires_idempotency_key" in source
    assert "tool_execution_service.execute" in source
    assert "create_payment_request(conn, actor_user=user" not in source


def test_payment_domain_persists_provider_and_confirmation_audit_fields():
    source = read("app/domains/payments.py")
    for token in [
        "tool_execution_idempotency_key",
        "client_request_id",
        "preview_execution_id",
        "confirmation_token_hash",
        "external_payment_id",
        "record_operational_event",
    ]:
        assert token in source


def test_operational_states_and_correlation_exist():
    migration = read("app/migrations.py") + read("app/operational_events.py")
    for token in [
        "operational_provider_events",
        "correlation_id",
        "job_id",
        "message_id",
        "outbox_message_id",
        "provider_message_id",
        "provider_confirmed",
        "provider_failed",
        "dead_letter",
    ]:
        assert token in migration


def test_release_gate_is_executable_and_complete():
    gate = Path(__file__).resolve().parents[2] / "scripts/validate_release_in_ci.sh"
    ci = Path(__file__).resolve().parents[1] / "scripts/run_ci_checks.sh"
    assert gate.exists() and gate.stat().st_mode & 0o111
    assert ci.exists() and ci.stat().st_mode & 0o111
    text = gate.read_text()
    for command in [
        "python -m compileall backend/app backend/worker.py",
        "pytest -q backend/tests",
        "python backend/scripts/export_openapi.py",
        "python backend/scripts/preflight_check.py",
        "python backend/scripts/post_deploy_smoke.py --required",
        "python backend/scripts/payment_provider_sandbox_smoke.py --required",
        "python backend/scripts/critical_e2e_smoke.py --required",
        "npm run test:e2e:real:critical",
        "npm run build",
    ]:
        assert command in text


def test_production_db_required_is_forced():
    assert 'startup_db_required: bool = _env_bool("STARTUP_DB_REQUIRED", True)' in read("app/config.py")
    assert "STARTUP_DB_REQUIRED=false is forbidden in production" in read("scripts/validate_render_env.py")
    assert "STARTUP_DB_REQUIRED\n        value: false" not in (Path(__file__).resolve().parents[2] / "render.yaml").read_text()


def test_tool_execution_preview_execute_contract_prevents_double_spend_and_links_provider_events():
    preview = read("app/application/tool_execution_handlers/preview.py")
    execute_handler = read("app/application/tool_execution_handlers/execute.py")

    assert "confirmation_token = service._build_confirmation_token" in preview
    assert "confirmation_token_hash=confirmation_hash" in preview
    assert "preview_run_id=(preview_run or {}).get(\"id\")" in execute_handler
    assert "tool-preview-consume" in execute_handler
    assert "tool_execution_preview_already_consumed" in execute_handler
    assert "idempotency_key_payload_mismatch" in execute_handler
    assert "record_operational_event" in execute_handler
    assert "provider_pending" in execute_handler
    assert "provider_confirmed" in execute_handler
    assert "provider_failed" in execute_handler
