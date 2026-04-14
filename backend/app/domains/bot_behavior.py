from __future__ import annotations

from typing import Any

from ..config import settings
from ..utils import from_json, new_id, slugify, to_json, utcnow_iso

def fetch_one(conn, sql: str, params=()):
    row = conn.execute(sql, tuple(params)).fetchone()
    return dict(row) if row else None


def fetch_all(conn, sql: str, params=()):
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def execute(conn, sql: str, params=()):
    conn.execute(sql, tuple(params))
    conn.commit()


def create_audit_log(conn, *, organization_id: str | None, actor_user_id: str | None, actor_type: str, entity_type: str, entity_id: str | None, action: str, metadata: dict[str, Any] | None = None) -> None:
    execute(conn, """
        INSERT INTO audit_logs (id, organization_id, actor_user_id, actor_type, entity_type, entity_id, action, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (new_id('audit'), organization_id, actor_user_id, actor_type, entity_type, entity_id, action, to_json(metadata or {}), utcnow_iso()))


def _parse_row(row: dict, mapping: dict[str, Any]) -> dict:
    parsed = dict(row)
    for key, default in mapping.items():
        clean_key = key[:-5] if key.endswith("_json") else key
        parsed[clean_key] = from_json(parsed.get(key), default)
    return parsed


def _parse_template(row: dict) -> dict:
    return _parse_row(row, {"variables_json": []})


def _parse_behavior(row: dict) -> dict:
    return _parse_row(
        row,
        {
            "escalate_when_json": [],
            "active_hours_json": [],
            "active_channels_json": [],
            "forbidden_topics_json": [],
            "required_phrases_json": [],
        },
    )


def upsert_bot_response_template(conn, *, organization_id: str, bot_id: str, template_key: str, channel: str = "whatsapp", title: str | None = None, content: str, variables: list[str] | None = None, is_active: bool = True, actor_user: dict | None = None) -> dict:
    now = utcnow_iso()
    existing = fetch_one(conn, "SELECT * FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key = ? AND channel = ?", (organization_id, bot_id, template_key, channel))
    if existing:
        execute(conn, "UPDATE bot_response_templates SET title = ?, content = ?, variables_json = ?, is_active = ?, updated_at = ? WHERE id = ?", (title, content, to_json(variables or []), 1 if is_active else 0, now, existing["id"]))
        row_id = existing["id"]
        action_name = "bot.template_updated"
    else:
        row_id = new_id("tmpl")
        execute(conn, "INSERT INTO bot_response_templates (id, organization_id, bot_id, template_key, channel, title, content, variables_json, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row_id, organization_id, bot_id, template_key, channel, title, content, to_json(variables or []), 1 if is_active else 0, now, now))
        action_name = "bot.template_created"
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="bot_response_template", entity_id=row_id, action=action_name, metadata={"template_key": template_key, "channel": channel})
    row = fetch_one(conn, "SELECT * FROM bot_response_templates WHERE id = ?", (row_id,)) or {}
    return _parse_template(row) if row else {}


def list_bot_response_templates(conn, organization_id: str, bot_id: str | None = None) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM bot_response_templates WHERE organization_id = ?"
    if bot_id:
        sql += " AND bot_id = ?"
        params.append(bot_id)
    sql += " ORDER BY template_key ASC, updated_at DESC"
    return [_parse_template(row) for row in fetch_all(conn, sql, params)]


def upsert_bot_behavior_settings(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    tone: str = "cercano",
    response_length: str = "media",
    use_emojis: bool = False,
    sales_intensity: str = "media",
    offer_promotions_when: str = "when_relevant",
    escalate_when: list[str] | None = None,
    insistence_policy: str = "respectful",
    can_share_price_directly: bool = True,
    can_negotiate: bool = False,
    can_mention_stock: bool = True,
    auto_send_images: bool = True,
    bot_mode: str = "hybrid",
    active_hours: list[dict[str, Any]] | None = None,
    active_channels: list[str] | None = None,
    forbidden_topics: list[str] | None = None,
    required_phrases: list[str] | None = None,
    fallback_message: str = "Te ayudo con gusto, pero necesito un poco mas de detalle para responderte bien.",
    actor_user: dict | None = None,
) -> dict:
    now = utcnow_iso()
    existing = fetch_one(conn, "SELECT * FROM bot_behavior_settings WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id))
    values = (
        tone, response_length, 1 if use_emojis else 0, sales_intensity, offer_promotions_when,
        to_json(escalate_when or []), insistence_policy, 1 if can_share_price_directly else 0,
        1 if can_negotiate else 0, 1 if can_mention_stock else 0, 1 if auto_send_images else 0,
        bot_mode, to_json(active_hours or []), to_json(active_channels or ["whatsapp"]),
        to_json(forbidden_topics or []), to_json(required_phrases or []), fallback_message,
    )
    if existing:
        execute(
            conn,
            """
            UPDATE bot_behavior_settings
            SET tone = ?, response_length = ?, use_emojis = ?, sales_intensity = ?, offer_promotions_when = ?,
                escalate_when_json = ?, insistence_policy = ?, can_share_price_directly = ?, can_negotiate = ?,
                can_mention_stock = ?, auto_send_images = ?, bot_mode = ?, active_hours_json = ?, active_channels_json = ?,
                forbidden_topics_json = ?, required_phrases_json = ?, fallback_message = ?, updated_at = ?
            WHERE id = ?
            """,
            values + (now, existing["id"]),
        )
        row_id = existing["id"]
        action_name = "bot.behavior_updated"
    else:
        row_id = new_id("bhv")
        execute(
            conn,
            """
            INSERT INTO bot_behavior_settings (
                id, organization_id, bot_id, tone, response_length, use_emojis, sales_intensity, offer_promotions_when,
                escalate_when_json, insistence_policy, can_share_price_directly, can_negotiate, can_mention_stock,
                auto_send_images, bot_mode, active_hours_json, active_channels_json, forbidden_topics_json,
                required_phrases_json, fallback_message, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, organization_id, bot_id) + values + (now, now),
        )
        action_name = "bot.behavior_created"
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="bot_behavior_settings", entity_id=row_id, action=action_name, metadata={"bot_id": bot_id})
    row = fetch_one(conn, "SELECT * FROM bot_behavior_settings WHERE id = ?", (row_id,)) or {}
    return _parse_behavior(row) if row else {}


def get_bot_behavior_settings(conn, organization_id: str, bot_id: str) -> dict:
    row = fetch_one(conn, "SELECT * FROM bot_behavior_settings WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id))
    return _parse_behavior(row) if row else {}
