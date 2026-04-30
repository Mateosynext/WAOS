from __future__ import annotations
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./.waos-production-smoke.db")
    os.environ.setdefault("APP_SECRET", "production-smoke-" + secrets.token_hex(24))
    os.environ.setdefault("SECRET_ENCRYPTION_KEY", "production-encryption-" + secrets.token_hex(24))
    os.environ.setdefault("META_VERIFY_TOKEN", "production-meta-" + secrets.token_hex(16))
    os.environ.setdefault("OPENAI_API_KEY", "smoke-only")
    os.environ.setdefault("OPENAI_MODEL", "gpt-5")
    os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")
    os.environ.setdefault("ENABLE_API_DOCS", "false")
    from app.db import fetch_all, fetch_one, get_connection, init_db
    from app.security import create_access_token
    from app.utils import hash_password, utcnow_iso
    init_db()
    conn = get_connection()
    tables = {row["name"] for row in fetch_all(conn, "SELECT name FROM sqlite_master WHERE type='table'")}
    required = {"users", "organizations", "organization_members", "bots", "conversations", "messages", "outbox_messages", "job_idempotency_keys", "report_generation_jobs"}
    missing = sorted(required - tables)
    if missing:
        raise SystemExit(f"smoke failed: missing tables {missing}")
    now = utcnow_iso()
    user_id = "smoke-user"
    org_id = "smoke-org"
    bot_id = "smoke-bot"
    conn.execute("INSERT OR REPLACE INTO users (id,email,password_hash,full_name,global_role,is_active,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)", (user_id, "smoke@example.invalid", hash_password("SmokePassword123!"), "Production Smoke", "admin", 1, now, now))
    conn.execute("INSERT OR REPLACE INTO organizations (id,name,tenant_mode,settings_json,created_at,updated_at) VALUES (?,?,?,?,?,?)", (org_id, "Smoke Org", "production", "{}", now, now))
    conn.execute("INSERT OR REPLACE INTO organization_members (id,organization_id,user_id,role,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)", ("smoke-membership", org_id, user_id, "admin", "active", now, now))
    conn.execute("INSERT OR REPLACE INTO bots (id,organization_id,name,slug,vertical,status,config_json,readiness_json,created_by_user_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (bot_id, org_id, "Smoke Bot", "smoke-bot", "general", "ready", "{}", "{}", user_id, now, now))
    conn.commit()
    user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise SystemExit("smoke failed: user was not persisted")
    token = create_access_token({**user, "memberships": [{"organization_id": org_id, "role": "admin"}], "organization_ids": [org_id]}, session_id="smoke-session")
    if not token or token.count(".") != 2:
        raise SystemExit("smoke failed: JWT token was not created")
    print("production smoke ok")


if __name__ == "__main__":
    main()
