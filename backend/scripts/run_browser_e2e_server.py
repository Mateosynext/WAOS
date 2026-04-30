#!/usr/bin/env python3
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / '.waos-browser-e2e.db'}")
os.environ.setdefault("APP_SECRET", "waos-browser-e2e-" + secrets.token_hex(24))
os.environ.setdefault("SECRET_ENCRYPTION_KEY", "waos-browser-e2e-enc-" + secrets.token_hex(24))
os.environ.setdefault("META_VERIFY_TOKEN", "waos-browser-e2e-meta-" + secrets.token_hex(16))
os.environ.setdefault("ENABLE_API_DOCS", "false")
os.environ.setdefault("STARTUP_INIT_DB", "true")
os.environ.setdefault("STARTUP_DB_REQUIRED", "true")
os.environ.setdefault("STRICT_SECURITY_STARTUP", "false")
os.environ.setdefault("RUN_BOOTSTRAP_SEED", "false")
os.environ.setdefault("WAOS_E2E_FAKE_PROVIDERS", "true")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_123456789")
os.environ.setdefault("PUBLIC_APP_URL", f"http://localhost:{os.getenv('PLAYWRIGHT_FRONTEND_PORT', '3000')}")
os.environ.setdefault("API_BASE_URL", f"http://127.0.0.1:{os.getenv('PLAYWRIGHT_API_PORT', '4100')}")
os.environ.setdefault("API_INTERNAL_URL", os.environ["API_BASE_URL"])


def _write_seed_file() -> None:
    seed_path = REPO / "frontend" / "tests" / "e2e" / ".real-secrets.json"
    if seed_path.exists():
        return
    seed_path.write_text(
        '{\n'
        '  "owner_email": "owner@waos.test",\n'
        '  "owner_password": "Passw0rd!",\n'
        '  "client_email": "client@waos.test",\n'
        '  "client_password": "Passw0rd!",\n'
        '  "mfa_user_email": "mfa@waos.test",\n'
        '  "mfa_user_password": "Passw0rd!",\n'
        '  "mfa_user_secret": "JBSWY3DPEHPK3PXP"\n'
        '}\n',
        encoding="utf-8",
    )


def _seed_browser_data() -> None:
    from app.db import execute, fetch_one, get_connection, init_db
    from app.utils import hash_password, utcnow_iso

    init_db()
    now = utcnow_iso()
    with get_connection() as conn:
        users = [
            ("user_owner", "owner@waos.test", "Owner QA", "admin", 1, None),
            ("user_mfa", "mfa@waos.test", "MFA QA", "admin", 1, "JBSWY3DPEHPK3PXP"),
            ("user_client", "client@waos.test", "Client QA", "member", 1, None),
            ("user_sso", "sso@enterprise.test", "SSO QA", "member", 1, None),
        ]
        for user_id, email, name, role, active, mfa_secret in users:
            execute(
                conn,
                """
                INSERT OR REPLACE INTO users
                (id,email,full_name,password_hash,global_role,is_active,mfa_enabled,mfa_secret,created_at,updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, email, name, hash_password("Passw0rd!"), role, active, 1 if mfa_secret else 0, mfa_secret, now, now),
            )
        orgs = [
            ("org_1", "Clínica Uno", "clinica-uno", "dental"),
            ("org_2", "Clínica Dos", "clinica-dos", "aesthetic"),
            ("org_3", "Org restringida", "org-restringida", "commerce"),
        ]
        for org_id, name, slug, vertical in orgs:
            execute(
                conn,
                """
                INSERT OR REPLACE INTO organizations
                (id,name,slug,status,timezone,vertical,settings_json,created_at,updated_at)
                VALUES (?, ?, ?, 'active', 'America/Mexico_City', ?, '{}', ?, ?)
                """,
                (org_id, name, slug, vertical, now, now),
            )
        memberships = [
            ("mem_owner_1", "org_1", "user_owner", "admin"),
            ("mem_owner_2", "org_2", "user_owner", "admin"),
            ("mem_mfa_1", "org_1", "user_mfa", "admin"),
            ("mem_mfa_2", "org_2", "user_mfa", "admin"),
            ("mem_client_1", "org_1", "user_client", "member"),
        ]
        for mem_id, org_id, user_id, role in memberships:
            execute(
                conn,
                """
                INSERT OR REPLACE INTO organization_members
                (id,organization_id,user_id,role,is_active,created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (mem_id, org_id, user_id, role, now),
            )
        bots = [
            ("bot_1", "org_1", "Asistente Uno", "asistente-uno", "dental"),
            ("bot_2", "org_2", "Asistente Dos", "asistente-dos", "aesthetic"),
        ]
        for bot_id, org_id, name, slug, vertical in bots:
            execute(
                conn,
                """
                INSERT OR REPLACE INTO bots
                (id,organization_id,name,slug,vertical,status,config_json,readiness_json,created_by_user_id,created_at,updated_at)
                VALUES (?, ?, ?, ?, ?, 'ready', '{}', '{}', 'user_mfa', ?, ?)
                """,
                (bot_id, org_id, name, slug, vertical, now, now),
            )
        execute(conn, "INSERT OR REPLACE INTO contacts (id,organization_id,phone,name,email,tags_json,created_at,updated_at) VALUES ('ct_1','org_1','+525500000001','Cliente Uno','cliente@example.test','[]',?,?)", (now, now))
        execute(conn, "INSERT OR REPLACE INTO conversations (id,organization_id,bot_id,contact_id,status,human_takeover,ai_active,created_at,updated_at) VALUES ('conv_1','org_1','bot_1','ct_1','ai_active',0,1,?,?)", (now, now))
        if fetch_one(conn, "SELECT id FROM appointments WHERE id = ?", ("apt_org1",)) is None:
            execute(conn, "INSERT INTO appointments (id,organization_id,bot_id,contact_id,conversation_id,title,scheduled_for,status,created_at,updated_at) VALUES ('apt_org1','org_1','bot_1','ct_1','conv_1','Demo comercial','2026-04-17T15:00:00Z','scheduled',?,?)", (now, now))
        if fetch_one(conn, "SELECT id FROM appointments WHERE id = ?", ("apt_org2",)) is None:
            execute(conn, "INSERT INTO appointments (id,organization_id,bot_id,title,scheduled_for,status,created_at,updated_at) VALUES ('apt_org2','org_2','bot_2','Seguimiento premium','2026-04-18T15:00:00Z','scheduled',?,?)", (now, now))


def main() -> None:
    _write_seed_file()
    _seed_browser_data()
    import uvicorn

    port = int(os.getenv("PLAYWRIGHT_API_PORT", "4100"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
