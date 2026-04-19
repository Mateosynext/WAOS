from __future__ import annotations

from backend.app.agent_runtime import orchestrate_runtime_turn
from backend.app.db import execute, fetch_one, get_connection
from backend.app.defaults import default_bot_config
from backend.app.growth_os_runtime import active_growth_os_focus, run_growth_os_cycle, run_growth_os_master_scheduler
from backend.app.utils import to_json
from backend.tests.test_activation_foundations import _auth_headers


GROWTH_CONTACT_ID = "ct_growth_master"
GROWTH_CONVERSATION_ID = "conv_growth_master"
GROWTH_PAYMENT_ID = "pay_growth_master"
GROWTH_LEAD_ID = "lead_growth_master"

_GROWTH_OS_CONFIG = {
    "enabled": True,
    "scheduler": {
        "enabled": True,
        "mode": "autopilot",
        "interval_minutes": 5,
        "goals": ["payments", "reactivation"],
        "max_targets": 3,
        "auto_execute": True,
        "include_suppressed": False,
        "scorecard_window": "28d",
    },
    "runtime_priority": {
        "enabled": True,
        "contact_focus_hours": 72,
        "prioritize_specialist": True,
        "prioritize_tools": True,
        "prioritize_handoffs": True,
        "prioritize_playbooks": True,
    },
}


def _seed_growth_master_entities() -> dict:
    _auth_headers()
    with get_connection() as conn:
        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", ("bot_activation",))
        config = default_bot_config(
            business_name=bot.get("business_name") or "Org Activation",
            vertical=bot.get("vertical") or "fitness",
            bot_name=bot.get("name") or "Bot Activation",
            primary_objective="agendar",
            tone="cercano",
            language=bot.get("language") or "es",
            timezone=bot.get("timezone") or "America/Mexico_City",
            services=["Consulta inicial"],
            hours="Lunes a viernes de 9:00 a 18:00",
            faqs=[{"q": "¿Tienen WhatsApp?", "a": "Sí, te atendemos por aquí."}],
            whatsapp_number="+5215550001111",
        )
        config["growth_os"] = _GROWTH_OS_CONFIG
        execute(conn, "UPDATE bots SET config_draft_json = ?, updated_at = ? WHERE id = ?", (to_json(config), "2026-04-18T12:00:00Z", "bot_activation"))

        if not fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (GROWTH_CONTACT_ID,)):
            execute(
                conn,
                "INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at) VALUES (?, 'org_activation', ?, ?, ?, '[]', ?, ?)",
                (GROWTH_CONTACT_ID, "+5215556667777", "Cliente Growth Master", "growth-master@example.com", "2026-04-16T09:00:00Z", "2026-04-16T09:00:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (GROWTH_CONVERSATION_ID,)):
            execute(
                conn,
                "INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, 'open', 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)",
                (GROWTH_CONVERSATION_ID, GROWTH_CONTACT_ID, "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM crm_leads WHERE id = ?", (GROWTH_LEAD_ID,)):
            execute(
                conn,
                """INSERT INTO crm_leads (id, organization_id, bot_id, conversation_id, contact_id, stage, estimated_amount, owner_user_id, next_action, followup_at, tags_json, notes, lost_reason, language, source_channel, source_campaign, pipeline_json, score_buying_intent, close_probability, detected_objections_json, best_next_action, temperature_status, last_qualification_at, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, ?, 'propuesta', 1800, 'usr_activation', 'Cobrar hoy', ?, '[]', '', NULL, 'es', 'whatsapp', 'organico', '{}', 88, 80, '[]', 'Enviar link de pago', 'hot', ?, ?, ?)""",
                (GROWTH_LEAD_ID, GROWTH_CONVERSATION_ID, GROWTH_CONTACT_ID, "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z", "2026-04-16T10:00:00Z"),
            )
        if not fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (GROWTH_PAYMENT_ID,)):
            execute(
                conn,
                "INSERT INTO commerce_payments (id, organization_id, bot_id, conversation_id, contact_id, crm_lead_id, title, amount, currency, status, payment_link_url, payment_link_status, reminder_scheduled_at, confirmed_at, receipt_sent_at, cart_recovery_status, send_receipt_on_confirm, metadata_json, created_at, updated_at) VALUES (?, 'org_activation', 'bot_activation', ?, ?, ?, 'Pago Growth Master', 900, 'MXN', 'pending', NULL, 'generated', NULL, NULL, NULL, 'inactive', 1, '{}', ?, ?)",
                (GROWTH_PAYMENT_ID, GROWTH_CONVERSATION_ID, GROWTH_CONTACT_ID, GROWTH_LEAD_ID, "2026-04-16T08:00:00Z", "2026-04-16T08:00:00Z"),
            )
        execute(conn, "DELETE FROM proactive_playbook_runs WHERE contact_id = ?", (GROWTH_CONTACT_ID,))
        execute(conn, "DELETE FROM proactive_contact_candidates WHERE contact_id = ?", (GROWTH_CONTACT_ID,))
        execute(conn, "DELETE FROM proactive_signal_events WHERE contact_id = ?", (GROWTH_CONTACT_ID,))
        execute(conn, "DELETE FROM growth_os_targets WHERE contact_id = ?", (GROWTH_CONTACT_ID,))
        conn.commit()
        return config


def test_growth_os_master_scheduler_runs_due_cycle_and_updates_control_state() -> None:
    _seed_growth_master_entities()

    with get_connection() as conn:
        processed = run_growth_os_master_scheduler(conn, limit=10)
        conn.commit()
        assert processed
        completed = next(item for item in processed if item["bot_id"] == "bot_activation")
        assert completed["status"] == "completed"
        assert completed["selected_count"] >= 1
        control = fetch_one(conn, "SELECT * FROM growth_os_control_states WHERE bot_id = ?", ("bot_activation",))
        assert control is not None
        assert control["latest_run_id"]
        assert control["last_status"] == "completed"


def test_growth_os_focus_becomes_runtime_priority_for_contact() -> None:
    config = _seed_growth_master_entities()

    with get_connection() as conn:
        run_growth_os_cycle(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            goals=["payments"],
            mode="recommend",
            max_targets=3,
            auto_execute=False,
            metadata={"source": "test_growth_os_focus"},
        )
        conn.commit()
        focus = active_growth_os_focus(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            contact_id=GROWTH_CONTACT_ID,
            conversation_id=GROWTH_CONVERSATION_ID,
            bot_config=config,
        )
        assert focus["focus_target"] is not None
        assert focus["preferred_specialist"] == "collections"
        assert focus["recommended_runtime_action"] == "execute_tool"

        conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (GROWTH_CONVERSATION_ID,))
        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", ("bot_activation",))
        result = orchestrate_runtime_turn(
            text="Hola",
            conversation=conversation,
            bot=bot,
            memory={"lead_stage": "proposal", "last_quoted_amount": 900, "currency": "MXN"},
            bot_config=config,
            recent_messages=[],
            conn=conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            contact_id=GROWTH_CONTACT_ID,
            conversation_id=GROWTH_CONVERSATION_ID,
            recent_voice_notes=[],
            language_config={"default_language": "es", "supported_languages": ["es", "en"]},
        )
        assert result["growth_os_focus"]["focus_target"] is not None
        assert result["specialist_route"]["specialist_agent_key"] == "collections"
        assert result["decision"]["action"] == "execute_tool"
        assert (result["self_state"]["turn"]["tool_plan"] or {}).get("action") == "create_payment_link"
