from __future__ import annotations

from backend.app.db import execute, get_connection, init_db
from backend.app.utils import new_id, utcnow_iso
from backend.app.verticals import get_vertical_profile, list_vertical_profiles
from backend.app.vertical_10x import apply_subvertical_pack, build_strongest_verticals, get_subvertical_profile, strongest_vertical_ids


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
            (bot_id, organization_id, 'Bot Demo', 'Bot Demo', vertical, now, now),
        )
    actor = {"id": user_id, "global_role": "super_admin", "organization_ids": [organization_id]}
    return actor, organization_id, bot_id


def test_phase7_strongest_verticals_are_top_five_hard_domains() -> None:
    init_db()
    strongest = build_strongest_verticals(list_vertical_profiles())
    assert [item["id"] for item in strongest] == strongest_vertical_ids()
    assert all(item.get("is_strongest_vertical") for item in strongest)
    assert strongest[0]["ten_x_score"] >= strongest[-1]["ten_x_score"]


def test_phase7_subvertical_profiles_are_generated_with_pack_fields() -> None:
    init_db()
    profile = get_vertical_profile("dental")
    sub = get_subvertical_profile(profile, "ortodoncia")
    assert sub
    assert sub["name"] == "ortodoncia"
    assert sub["service_bundle"]
    assert sub["qualification_questions"]
    assert sub["templates"]
    assert int(sub["strength_score"]) >= 70


def test_phase7_apply_subvertical_pack_seeds_behavior_templates_and_services() -> None:
    init_db()
    actor, organization_id, bot_id = _seed_actor_org_bot("fitness")
    profile = get_vertical_profile("fitness")
    with get_connection() as conn:
        result = apply_subvertical_pack(
            conn,
            profile=profile,
            organization_id=organization_id,
            bot_id=bot_id,
            subvertical="personal training",
            actor_user=actor,
        )
        assert result["subvertical"] == "personal training"
        assert result["template_keys"]
        assert result["created_services"]
        templates = conn.execute("SELECT COUNT(*) AS value FROM bot_response_templates WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id)).fetchone()[0]
        services = conn.execute("SELECT COUNT(*) AS value FROM catalog_services WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id)).fetchone()[0]
        behavior = conn.execute("SELECT COUNT(*) AS value FROM bot_behavior_settings WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id)).fetchone()[0]
        assert templates >= 3
        assert services >= 3
        assert behavior == 1
