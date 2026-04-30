from __future__ import annotations

from typing import Any

from .base import ConnectionLike

from ..db import execute, fetch_all, fetch_one
from ..defaults import default_bot_config
from ..utils import from_json, hash_password, new_id, slugify, to_json, utcnow_iso
from ..whatsapp_connection_state import WHATSAPP_STATUS_NUMBER_ENTERED, update_whatsapp_metadata
from ..verticals import build_organization_settings

def get_bot(conn: ConnectionLike, bot_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM bots WHERE id = ? AND deleted_at IS NULL", (bot_id,))


def list_bot_versions(conn: ConnectionLike, bot_id: str) -> list[dict]:
    return fetch_all(
        conn,
        "SELECT * FROM bot_versions WHERE bot_id = ? ORDER BY version_number DESC",
        (bot_id,),
    )


def publish_version(conn: ConnectionLike, *, bot_id: str, actor_user: dict, notes: str = "") -> dict:
    bot = get_bot(conn, bot_id)
    versions = list_bot_versions(conn, bot_id)
    next_number = 1 if not versions else max(v["version_number"] for v in versions) + 1
    version_id = new_id("bver")
    execute(
        conn,
        """
        INSERT INTO bot_versions (id, organization_id, bot_id, version_number, status, config_json, created_by, notes, created_at)
        VALUES (?, ?, ?, ?, 'published', ?, ?, ?, ?)
        """,
        (
            version_id,
            bot["organization_id"],
            bot_id,
            next_number,
            bot["config_draft_json"],
            actor_user["id"],
            notes,
            utcnow_iso(),
        ),
    )
    execute(
        conn,
        """
        UPDATE bots
        SET published_version_id = ?, current_state = 'published', updated_at = ?
        WHERE id = ?
        """,
        (version_id, utcnow_iso(), bot_id),
    )
    create_audit_log(
        conn,
        organization_id=bot["organization_id"],
        actor_user_id=actor_user["id"],
        actor_type="user",
        entity_type="bot",
        entity_id=bot_id,
        action="bot.version_published",
        metadata={"version_number": next_number, "notes": notes},
    )
    return fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ?", (version_id,))


def create_audit_log(
    conn: ConnectionLike,
    *,
    organization_id: str | None,
    actor_user_id: str | None,
    actor_type: str,
    entity_type: str,
    entity_id: str | None,
    action: str,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
    session_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    severity: str = "info",
    trace_id: str | None = None,
) -> None:
    execute(
        conn,
        """
        INSERT INTO audit_logs (
            id, organization_id, actor_user_id, actor_type, entity_type, entity_id, action,
            metadata_json, request_id, session_id, ip_address, user_agent, severity, trace_id, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("audit"),
            organization_id,
            actor_user_id,
            actor_type,
            entity_type,
            entity_id,
            action,
            to_json(metadata or {}),
            request_id,
            session_id,
            ip_address,
            user_agent,
            severity,
            trace_id,
            utcnow_iso(),
        ),
    )


def create_bot(
    conn: ConnectionLike,
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
    client_request_id: str | None = None,
) -> dict:
    if client_request_id:
        existing = fetch_one(
            conn,
            """
            SELECT * FROM bots
            WHERE organization_id = ? AND client_request_id = ? AND deleted_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (organization_id, client_request_id),
        )
        if existing:
            return existing

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
        (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, published_version_id, config_draft_json, created_at, updated_at, client_request_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 0, ?, NULL, ?, ?, ?, ?)
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
            client_request_id,
        ),
    )
    if whatsapp_number:
        connection_status, metadata_json = update_whatsapp_metadata(
            {},
            phone_number=whatsapp_number,
            phone_number_id=None,
            waba_id=None,
            access_token_present=False,
            webhook_verified=False,
            source="bot_creation",
        )
        execute(
            conn,
            """
            INSERT INTO whatsapp_numbers
            (id, organization_id, bot_id, provider, phone_number, phone_number_id, waba_id, connection_status, webhook_verify_token, access_token_masked, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, 'meta_cloud_api', ?, NULL, NULL, ?, NULL, NULL, ?, ?, ?)
            """,
            (
                new_id("wan"),
                organization_id,
                bot_id,
                whatsapp_number,
                connection_status or WHATSAPP_STATUS_NUMBER_ENTERED,
                metadata_json,
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
        metadata={"name": bot_name, "publish_now": publish_now, "client_request_id": client_request_id},
    )
    return get_bot(conn, bot_id)


def rollback_version(conn: ConnectionLike, *, bot_id: str, version_id: str, actor_user: dict) -> dict:
    version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ? AND bot_id = ?", (version_id, bot_id))
    bot = get_bot(conn, bot_id)
    execute(
        conn,
        """
        UPDATE bots
        SET config_draft_json = ?, published_version_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (version["config_json"], version_id, utcnow_iso(), bot_id),
    )
    create_audit_log(
        conn,
        organization_id=bot["organization_id"],
        actor_user_id=actor_user["id"],
        actor_type="user",
        entity_type="bot",
        entity_id=bot_id,
        action="bot.version_rollback",
        metadata={"version_id": version_id},
    )
    return get_bot(conn, bot_id)
