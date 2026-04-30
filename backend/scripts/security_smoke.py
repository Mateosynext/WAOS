from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("APP_SECRET", "security-smoke-" + secrets.token_hex(24))
    os.environ.setdefault("SECRET_ENCRYPTION_KEY", "security-encryption-" + secrets.token_hex(24))
    os.environ.setdefault("META_VERIFY_TOKEN", "security-meta-" + secrets.token_hex(16))
    os.environ.setdefault("OPENAI_API_KEY", "security-smoke-only")
    os.environ.setdefault("OPENAI_MODEL", "gpt-5")
    os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")
    os.environ.setdefault("SECURITY_HARDENING_ENABLED", "true")
    os.environ.setdefault("SECURITY_RATE_LIMIT_ENABLED", "true")
    os.environ.setdefault("ENFORCE_HTTPS", "true")
    os.environ.setdefault("REJECT_UNTRUSTED_PROXY_HEADERS", "true")
    os.environ.setdefault("MAX_REQUEST_BODY_BYTES", "1024")
    os.environ.setdefault("MAX_WEBHOOK_BODY_BYTES", "1024")
    # This smoke intentionally does not import app.main to keep it fast and DB-free.
    from app.hardening import _body_limit_for, _rate_policy_for
    from app.config import settings
    assert settings.security_hardening_enabled is True
    assert _body_limit_for("/webhooks/whatsapp/123") == settings.max_webhook_body_bytes
    assert settings.max_webhook_body_bytes >= 1024
    assert _body_limit_for("/api/v1/auth/login") == settings.max_request_body_bytes
    assert _rate_policy_for("/api/v1/auth/login")[0] == "auth"
    assert "frame-ancestors" in settings.content_security_policy
    print("security smoke ok")


if __name__ == "__main__":
    main()
