from __future__ import annotations

import os
import sqlite3
from typing import Any

from ..db import execute, fetch_all, fetch_one
from ..defaults import default_bot_config
from ..utils import from_json, hash_password, new_id, slugify, to_json, utcnow_iso
from ..verticals import build_organization_settings
from .audit import create_audit_log
from .bots import get_bot, publish_version
from .contacts import get_contact, get_contact_memory
from .conversations import get_conversation

def create_bot(
    conn: sqlite3.Connection,
    *,
    organization_id: str,
    business_name: str,
    vertical: str,
    bot_name: str,
    primary_objective: str,
    tone: str,
    language: str,
    timezone: str,
    services: list[str],
    hours: str,
    faqs: list[dict],
    whatsapp_number: str,
    publish_now: bool,
    created_by: dict,
) -> dict:
    bot_id = new_id("bot")
    now = utcnow_iso()
    config = default_bot_config(
        business_name=business_name,
        vertical=vertical,
        bot_name=bot_name,
        primary_objective=primary_objective,
        tone=tone,
        language=language,
        timezone=timezone,
        services=services,
        hours=hours,
        faqs=faqs,
        whatsapp_number=whatsapp_number,
    )
    execute(
        conn,
        """
        INSERT INTO bots
        (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 0, ?, NULL, ?, ?, ?)
        """,
        (
            bot_id,
            organization_id,
            bot_name,
            business_name,
            vertical,
            language,
            timezone,
            "published" if publish_now else "draft",
            to_json(config),
            now,
            now,
        ),
    )
    if whatsapp_number:
        execute(
            conn,
            """
            INSERT INTO whatsapp_numbers
            (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status, webhook_verify_token, access_token_masked, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, 'meta_cloud_api', ?, ?, ?, 'connected', ?, '***redacted', '{}', ?, ?)
            """,
            (
                new_id("wan"),
                organization_id,
                bot_id,
                whatsapp_number,
                f"PHONE-{bot_id[-8:]}",
                f"WABA-{bot_id[-8:]}",
                os.getenv("META_VERIFY_TOKEN", ""),
                now,
                now,
            ),
        )
    if publish_now:
        publish_version(conn, bot_id=bot_id, actor_user=created_by, notes="Initial publish")
    create_audit_log(
        conn,
        organization_id=organization_id,
        actor_user_id=created_by["id"],
        actor_type="user",
        entity_type="bot",
        entity_id=bot_id,
        action="bot.created",
        metadata={"name": bot_name, "publish_now": publish_now},
    )
    return get_bot(conn, bot_id)


def create_or_update_knowledge_items(conn: sqlite3.Connection, *, organization_id: str, bot_id: str, config: dict) -> None:
    execute(conn, "DELETE FROM knowledge_items WHERE bot_id = ?", (bot_id,))
    knowledge = config.get("business_knowledge", {})
    items: list[tuple] = []
    now = utcnow_iso()
    order = 0
    for item_type in ("services", "products", "prices", "faqs", "policies", "promotions"):
        value = knowledge.get(item_type) or []
        if isinstance(value, list):
            for item in value:
                order += 1
                title = item_type
                content = item if isinstance(item, str) else to_json(item)
                items.append((new_id("k"), organization_id, bot_id, item_type, title, content, order, 1, now, now))
    for item_type in ("hours", "location"):
        value = knowledge.get(item_type)
        if value:
            order += 1
            items.append((new_id("k"), organization_id, bot_id, item_type, item_type, str(value), order, 1, now, now))
    if items:
        conn.executemany(
            """
            INSERT INTO knowledge_items (id, organization_id, bot_id, item_type, title, content, order_index, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            items,
        )
        conn.commit()


def upsert_contact(conn: sqlite3.Connection, *, organization_id: str, phone: str, name: str | None = None) -> dict:
    existing = fetch_one(conn, "SELECT * FROM contacts WHERE organization_id = ? AND phone = ?", (organization_id, phone))
    now = utcnow_iso()
    if existing:
        if name and name != existing.get("name"):
            execute(conn, "UPDATE contacts SET name = ?, updated_at = ? WHERE id = ?", (name, now, existing["id"]))
        return get_contact(conn, existing["id"])
    contact_id = new_id("contact")
    execute(
        conn,
        """
        INSERT INTO contacts (id, organization_id, phone, name, email, tags_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, NULL, '[]', ?, ?)
        """,
        (contact_id, organization_id, phone, name, now, now),
    )
    return get_contact(conn, contact_id)


def upsert_conversation(conn: sqlite3.Connection, *, organization_id: str, bot_id: str, contact_id: str) -> dict:
    existing = fetch_one(
        conn,
        "SELECT * FROM conversations WHERE organization_id = ? AND bot_id = ? AND contact_id = ?",
        (organization_id, bot_id, contact_id),
    )
    now = utcnow_iso()
    if existing:
        execute(conn, "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, existing["id"]))
        return get_conversation(conn, existing["id"])
    conversation_id = new_id("conv")
    execute(
        conn,
        """
        INSERT INTO conversations
        (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'ai_active', 0, 1, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?)
        """,
        (conversation_id, organization_id, bot_id, contact_id, now, now),
    )
    return get_conversation(conn, conversation_id)


def upsert_memory(conn: sqlite3.Connection, *, organization_id: str, contact_id: str, bot_id: str) -> dict:
    existing = get_contact_memory(conn, contact_id, bot_id)
    now = utcnow_iso()
    if existing:
        return existing
    memory_id = new_id("mem")
    execute(
        conn,
        """
        INSERT INTO contact_memory
        (id, organization_id, contact_id, bot_id, lead_stage, lead_score, interest, objections, summary, next_action, followup_at, memory_json, last_updated_at)
        VALUES (?, ?, ?, ?, 'new', 0, NULL, '', '', '', NULL, '{}', ?)
        """,
        (memory_id, organization_id, contact_id, bot_id, now),
    )
    return get_contact_memory(conn, contact_id, bot_id)


def create_message(
    conn: sqlite3.Connection,
    *,
    organization_id: str,
    conversation_id: str,
    contact_id: str | None,
    bot_id: str,
    direction: str,
    kind: str,
    source: str,
    body: str,
    external_id: str | None = None,
    status: str = "sent",
    metadata: dict[str, Any] | None = None,
) -> dict:
    message_id = new_id("msg")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO messages
        (id, organization_id, conversation_id, contact_id, bot_id, direction, kind, source, body, external_id, status, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message_id,
            organization_id,
            conversation_id,
            contact_id,
            bot_id,
            direction,
            kind,
            source,
            body,
            external_id,
            status,
            to_json(metadata or {}),
            now,
        ),
    )
    execute(
        conn,
        """
        UPDATE conversations
        SET last_message_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (now, now, conversation_id),
    )
    return fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (message_id,))


def ensure_seed_data(conn: sqlite3.Connection) -> None:
    admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    admin_name = os.getenv("BOOTSTRAP_ADMIN_NAME", "WAOS Bootstrap Admin").strip() or "WAOS Bootstrap Admin"
    org_name = os.getenv("BOOTSTRAP_ORG_NAME", "WAOS Bootstrap Organization").strip() or "WAOS Bootstrap Organization"
    org_slug = slugify(os.getenv("BOOTSTRAP_ORG_SLUG", org_name))

    if not admin_email or not admin_password:
        raise RuntimeError(
            "RUN_BOOTSTRAP_SEED=true requires BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD to avoid shipping visible static credentials."
        )

    existing = fetch_one(conn, "SELECT id FROM users WHERE email = ?", (admin_email,))
    if existing:
        return

    now = utcnow_iso()
    admin_user_id = new_id("bootstrap_user")
    org_id = new_id("bootstrap_org")

    conn.execute(
        """
        INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'super_admin', 1, ?, ?)
        """,
        (admin_user_id, admin_email, admin_name, hash_password(admin_password), now, now),
    )
    conn.execute(
        """
        INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at)
        VALUES (?, ?, ?, 'active', 'America/Mexico_City', 'general', '{}', ?, ?)
        """,
        (org_id, org_name, org_slug, now, now),
    )
    conn.execute(
        """
        INSERT INTO organization_members (id, organization_id, user_id, role, is_active, created_at)
        VALUES (?, ?, ?, 'super_admin', 1, ?)
        """,
        (new_id("bootstrap_orgm"), org_id, admin_user_id, now),
    )

    admin = {"id": admin_user_id, "global_role": "super_admin", "email": admin_email}
    bot = create_bot(
        conn,
        organization_id=org_id,
        business_name=org_name,
        vertical="general",
        bot_name=os.getenv("BOOTSTRAP_BOT_NAME", "WAOS Assistant"),
        primary_objective="agendar",
        tone="profesional",
        language="es",
        timezone="America/Mexico_City",
        services=["Atención comercial", "Calificación", "Agendamiento"],
        hours="Lunes a viernes de 9 a 18 h",
        faqs=[
            {"q": "¿Qué hace WAOS?", "a": "Centraliza conversaciones, operaciones y seguimiento comercial."},
            {"q": "¿Cómo continúo?", "a": "Configura catálogo, políticas y canales antes de publicar."},
        ],
        whatsapp_number=os.getenv("BOOTSTRAP_WHATSAPP_NUMBER", "+525500000000"),
        publish_now=True,
        created_by=admin,
    )
    config = from_json(bot["config_draft_json"], {})
    create_or_update_knowledge_items(conn, organization_id=org_id, bot_id=bot["id"], config=config)

    contact = upsert_contact(
        conn,
        organization_id=org_id,
        phone=os.getenv("BOOTSTRAP_SAMPLE_CONTACT_PHONE", "+525500000001"),
        name=os.getenv("BOOTSTRAP_SAMPLE_CONTACT_NAME", "Contacto inicial"),
    )
    conv = upsert_conversation(conn, organization_id=org_id, bot_id=bot["id"], contact_id=contact["id"])
    upsert_memory(conn, organization_id=org_id, contact_id=contact["id"], bot_id=bot["id"])
    create_message(
        conn,
        organization_id=org_id,
        conversation_id=conv["id"],
        contact_id=contact["id"],
        bot_id=bot["id"],
        direction="inbound",
        kind="text",
        source="user",
        body="Hola, quiero activar WAOS para mi operación.",
        external_id=new_id("bootstrap_msg"),
        status="received",
    )
    create_message(
        conn,
        organization_id=org_id,
        conversation_id=conv["id"],
        contact_id=contact["id"],
        bot_id=bot["id"],
        direction="outbound",
        kind="text",
        source="ai",
        body="Perfecto. El siguiente paso es configurar canales, catálogo y reglas de operación.",
        external_id=new_id("bootstrap_msg"),
        status="simulated",
    )
    conn.commit()
