from __future__ import annotations

from typing import Any

from ..config import settings
from ..repositories import create_audit_log
from ..repositories.bot_behavior_domain import (
    get_bot_behavior_settings as repo_get_bot_behavior_settings,
    get_bot_behavior_settings_by_scope,
    get_bot_response_template,
    get_bot_response_template_by_scope,
    insert_bot_behavior_settings,
    insert_bot_response_template,
    list_bot_response_templates as repo_list_bot_response_templates,
    update_bot_behavior_settings,
    update_bot_response_template,
)
from ..utils import from_json, new_id, slugify, to_json, utcnow_iso

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
    existing = get_bot_response_template_by_scope(conn, organization_id=organization_id, bot_id=bot_id, template_key=template_key, channel=channel)
    if existing:
        update_bot_response_template(conn, template_id=existing["id"], title=title, content=content, variables=variables or [], is_active=is_active, updated_at=now)
        row_id = existing["id"]
        action_name = "bot.template_updated"
    else:
        row_id = new_id("tmpl")
        insert_bot_response_template(conn, row_id=row_id, organization_id=organization_id, bot_id=bot_id, template_key=template_key, channel=channel, title=title, content=content, variables=variables or [], is_active=is_active, created_at=now)
        action_name = "bot.template_created"
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="bot_response_template", entity_id=row_id, action=action_name, metadata={"template_key": template_key, "channel": channel})
    row = get_bot_response_template(conn, row_id) or {}
    return _parse_template(row) if row else {}


def list_bot_response_templates(conn, organization_id: str, bot_id: str | None = None) -> list[dict]:
    return [_parse_template(row) for row in repo_list_bot_response_templates(conn, organization_id=organization_id, bot_id=bot_id)]


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
    existing = get_bot_behavior_settings_by_scope(conn, organization_id=organization_id, bot_id=bot_id)
    values = (
        tone, response_length, 1 if use_emojis else 0, sales_intensity, offer_promotions_when,
        to_json(escalate_when or []), insistence_policy, 1 if can_share_price_directly else 0,
        1 if can_negotiate else 0, 1 if can_mention_stock else 0, 1 if auto_send_images else 0,
        bot_mode, to_json(active_hours or []), to_json(active_channels or ["whatsapp"]),
        to_json(forbidden_topics or []), to_json(required_phrases or []), fallback_message,
    )
    if existing:
        update_bot_behavior_settings(conn, row_id=existing["id"], values=values, updated_at=now)
        row_id = existing["id"]
        action_name = "bot.behavior_updated"
    else:
        row_id = new_id("bhv")
        insert_bot_behavior_settings(conn, row_id=row_id, organization_id=organization_id, bot_id=bot_id, values=values, created_at=now)
        action_name = "bot.behavior_created"
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="bot_behavior_settings", entity_id=row_id, action=action_name, metadata={"bot_id": bot_id})
    row = repo_get_bot_behavior_settings(conn, row_id) or {}
    return _parse_behavior(row) if row else {}


def get_bot_behavior_settings(conn, organization_id: str, bot_id: str) -> dict:
    row = get_bot_behavior_settings_by_scope(conn, organization_id=organization_id, bot_id=bot_id)
    return _parse_behavior(row) if row else {}
