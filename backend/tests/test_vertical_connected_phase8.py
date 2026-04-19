from __future__ import annotations

from backend.app.db import execute, get_connection, init_db
from backend.app.utils import from_json, new_id, utcnow_iso
from backend.app.verticals import get_vertical_profile
from backend.app.vertical_10x import apply_subvertical_pack, enrich_vertical_profile_for_runtime


def _seed_actor_org_bot(vertical: str = "fitness") -> tuple[dict, str, str]:
    organization_id = new_id("org")
    user_id = new_id("user")
    bot_id = new_id("bot")
    now = utcnow_iso()
    with get_connection() as conn:
        execute(
            conn,
            "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 'super_admin', 1, ?, ?)",
            (user_id, f"{user_id}@example.com", "Test User", "not-used", now, now),
        )
        execute(
            conn,
            "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', ?, '{}', ?, ?)",
            (organization_id, "Org Test", f"org-{organization_id[-8:]}", vertical, now, now),
        )
        execute(
            conn,
            "INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, 'es', 'America/Mexico_City', 'active', 0, 'published', NULL, '{}', ?, ?, NULL)",
            (bot_id, organization_id, 'Bot Productivo', 'Bot Productivo', vertical, now, now),
        )
    actor = {"id": user_id, "global_role": "super_admin", "organization_ids": [organization_id]}
    return actor, organization_id, bot_id


def test_phase8_apply_pack_persists_subvertical_in_org_and_bot() -> None:
    init_db()
    actor, organization_id, bot_id = _seed_actor_org_bot("fitness")
    profile = get_vertical_profile("fitness")
    with get_connection() as conn:
        result = apply_subvertical_pack(conn, profile=profile, organization_id=organization_id, bot_id=bot_id, subvertical="pilates", actor_user=actor)
        org = dict(conn.execute("SELECT * FROM organizations WHERE id = ?", (organization_id,)).fetchone())
        bot = dict(conn.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone())
        org_settings = from_json(org.get("settings_json"), {})
        bot_config = from_json(bot.get("config_draft_json"), {})
        assert result["subvertical"] == "pilates"
        assert org_settings.get("subvertical") == "pilates"
        assert org_settings.get("active_subvertical") == "pilates"
        assert bot_config.get("selected_subvertical") == "pilates"


def test_phase8_runtime_profile_uses_persisted_subvertical_and_pack_status() -> None:
    init_db()
    actor, organization_id, bot_id = _seed_actor_org_bot("dental")
    profile = get_vertical_profile("dental")
    with get_connection() as conn:
        apply_subvertical_pack(conn, profile=profile, organization_id=organization_id, bot_id=bot_id, subvertical="ortodoncia", actor_user=actor)
        org = dict(conn.execute("SELECT * FROM organizations WHERE id = ?", (organization_id,)).fetchone())
        bot = dict(conn.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone())
        enriched = enrich_vertical_profile_for_runtime(conn, profile=profile, organization_id=organization_id, bot=bot, org=org)
        runtime = enriched.get("runtime_connection") or {}
        pack_status = runtime.get("pack_status") or {}
        assert enriched.get("selected_subvertical", {}).get("name") == "ortodoncia"
        assert runtime.get("active_subvertical") == "ortodoncia"
        assert pack_status.get("pack_applied") is True
        assert int(pack_status.get("coverage_score") or 0) > 0
