from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bot_creation_never_fakes_whatsapp_connected_state():
    bots = read("backend/app/repositories/bots.py")
    seed = read("backend/app/repositories/seed.py")
    for source in (bots, seed):
        assert "PHONE-{bot_id" not in source
        assert "WABA-{bot_id" not in source
        assert "'connected', ?, '***redacted'" not in source
        assert "connection_status or WHATSAPP_STATUS_NUMBER_ENTERED" in source
        assert "phone_number_id=None" in source
        assert "waba_id=None" in source


def test_whatsapp_config_requires_real_provider_ids_and_no_fallbacks():
    commands = read("backend/app/application/integration_handlers/commands.py")
    assert "require_real_provider_ids" in commands
    assert "clean_provider_id" in commands
    assert "f\"PHONE-" not in commands
    assert "f\"WABA-" not in commands
    assert "manual_whatsapp_config" in commands
    assert 'final_status = "active" if connection_status == "send_ready" else payload.status' in commands
    assert 'or "provider_connected") if token' not in commands
    assert 'or "configured") if token' in commands


def test_connection_state_requires_complete_meta_proof():
    state = read("backend/app/whatsapp_connection_state.py")
    assert "real_phone_number_id and real_waba_id and access_token_present" in state
    assert "never \"connected\"" in state
    assert "provider_ids_real" in state
    assert "clean_provider_id(data.get(\"phone_number_id\")) and clean_provider_id(data.get(\"waba_id\"))" in state
    assert "def is_whatsapp_send_ready(row: dict[str, Any] | None, *, access_token_present: bool = False)" in state
    assert "never from a stored label" in state
    assert "connection_status=\"send_ready\"" in state


def test_meta_signup_and_webhook_move_through_explicit_states():
    meta = read("backend/app/meta_runtime.py")
    webhooks = read("backend/app/api/handlers/webhooks.py")
    assert "whatsapp_phone_number_id_required" in meta
    assert "connection_status = ?," in meta
    assert "connection_status == \"send_ready\"" in meta
    assert "source=\"webhook_verify\"" in webhooks
    assert "source=\"webhook_delivery\"" in webhooks
    assert "UPDATE whatsapp_numbers SET connection_status = ?, metadata_json = ?" in webhooks


def test_runtime_send_recomputes_send_ready_and_requires_waba_token_webhook():
    whatsapp = read("backend/app/whatsapp.py")
    assert "clean_provider_id(number.get(\"phone_number_id\"))" in whatsapp
    assert "whatsapp_phone_number_id_not_verified" in whatsapp
    assert "clean_provider_id(number.get(\"waba_id\"))" in whatsapp
    assert "whatsapp_waba_id_not_verified" in whatsapp
    assert "missing_whatsapp_access_token" in whatsapp
    assert "is_whatsapp_send_ready(number, access_token_present=bool(access_token))" in whatsapp
    assert "real_waba_id" in whatsapp
    assert "webhook_verified" in whatsapp
    assert "whatsapp_not_send_ready" in whatsapp


def test_ui_and_release_surfaces_pending_not_connected():
    support = read("backend/app/application/support.py")
    bot_service = read("backend/app/application/bot_service.py")
    release = read("backend/app/platform/release.py")
    app_js = read("backend/app/static/app.js")
    assert "decorate_whatsapp_number" in support
    assert "whatsapp_ui_status" in bot_service
    assert "whatsapp_send_ready" in bot_service
    assert "WHATSAPP_STATUS_SEND_READY" in release
    assert "WhatsApp pendiente de conexión" in release
    assert "WhatsApp listo para enviar" in release
    assert "function whatsappStatusBadge" in app_js
    assert "WhatsApp pendiente de conexión" in app_js
    assert "Bot creado. WhatsApp queda pendiente de conexión" in app_js
