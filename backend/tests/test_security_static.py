from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMERCIAL_DOCUMENTS = (ROOT / "backend/app/api/handlers/commercial_documents.py").read_text(encoding="utf-8")
PUBLIC_ROUTER = (ROOT / "backend/app/api/routers/public.py").read_text(encoding="utf-8")
BOT_AUTOPILOT_SCHEMA = (ROOT / "backend/app/ai_workflows/bot_autopilot/schemas.py").read_text(encoding="utf-8")
BOT_AUTOPILOT_SERVICE = (ROOT / "backend/app/ai_workflows/bot_autopilot/service.py").read_text(encoding="utf-8")


def test_public_smart_docs_pages_have_strict_csp_headers() -> None:
    assert "'/api/public/commercial-documents/{document_id}'" in PUBLIC_ROUTER
    assert "_smart_docs_security_headers" in COMMERCIAL_DOCUMENTS
    assert "Content-Security-Policy" in COMMERCIAL_DOCUMENTS
    assert "default-src 'none'" in COMMERCIAL_DOCUMENTS
    assert "script-src 'none'" in COMMERCIAL_DOCUMENTS
    assert "frame-ancestors 'none'" in COMMERCIAL_DOCUMENTS
    assert "base-uri 'none'" in COMMERCIAL_DOCUMENTS
    assert "object-src 'none'" in COMMERCIAL_DOCUMENTS
    assert "form-action 'none'" in COMMERCIAL_DOCUMENTS
    assert "X-Content-Type-Options" in COMMERCIAL_DOCUMENTS
    assert "Referrer-Policy" in COMMERCIAL_DOCUMENTS
    assert "Permissions-Policy" in COMMERCIAL_DOCUMENTS
    assert "'unsafe-inline'" not in COMMERCIAL_DOCUMENTS
    assert "nonce-" in COMMERCIAL_DOCUMENTS
    assert "HTMLResponse(html, headers=_smart_docs_security_headers(style_nonce=style_nonce))" in COMMERCIAL_DOCUMENTS


def test_godmode_requires_server_side_super_admin_role() -> None:
    assert "def _actor_global_role" in BOT_AUTOPILOT_SCHEMA
    assert "def _actor_is_super_admin" in BOT_AUTOPILOT_SCHEMA
    assert "def enforce_actor_godmode" in BOT_AUTOPILOT_SCHEMA
    assert "godmode_requires_super_admin_downgraded_to_savage" in BOT_AUTOPILOT_SCHEMA
    assert "settings.ai_enable_godmode" in BOT_AUTOPILOT_SCHEMA
    assert "payload = payload.enforce_actor_godmode(user)" in BOT_AUTOPILOT_SERVICE
    assert "BotAutopilotRequest.model_validate(run.get(\"config_json\") or {}).enforce_actor_godmode(user)" in BOT_AUTOPILOT_SERVICE
