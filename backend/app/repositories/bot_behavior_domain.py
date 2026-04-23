from __future__ import annotations

from typing import Any

from .base import ConnectionLike, execute, fetch_all, fetch_one
from ..utils import to_json


def get_bot_response_template_by_scope(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str,
    template_key: str,
    channel: str,
) -> dict | None:
    return fetch_one(
        conn,
        "SELECT * FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key = ? AND channel = ?",
        (organization_id, bot_id, template_key, channel),
    )


def update_bot_response_template(
    conn: ConnectionLike,
    *,
    template_id: str,
    title: str | None,
    content: str,
    variables: list[str],
    is_active: bool,
    updated_at: str,
) -> None:
    execute(
        conn,
        "UPDATE bot_response_templates SET title = ?, content = ?, variables_json = ?, is_active = ?, updated_at = ? WHERE id = ?",
        (title, content, to_json(variables), 1 if is_active else 0, updated_at, template_id),
    )


def insert_bot_response_template(
    conn: ConnectionLike,
    *,
    row_id: str,
    organization_id: str,
    bot_id: str,
    template_key: str,
    channel: str,
    title: str | None,
    content: str,
    variables: list[str],
    is_active: bool,
    created_at: str,
) -> None:
    execute(
        conn,
        "INSERT INTO bot_response_templates (id, organization_id, bot_id, template_key, channel, title, content, variables_json, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, bot_id, template_key, channel, title, content, to_json(variables), 1 if is_active else 0, created_at, created_at),
    )


def get_bot_response_template(conn: ConnectionLike, template_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM bot_response_templates WHERE id = ?", (template_id,))


def list_bot_response_templates(conn: ConnectionLike, *, organization_id: str, bot_id: str | None = None) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM bot_response_templates WHERE organization_id = ?"
    if bot_id:
        sql += " AND bot_id = ?"
        params.append(bot_id)
    sql += " ORDER BY template_key ASC, updated_at DESC"
    return fetch_all(conn, sql, params)


def get_bot_behavior_settings_by_scope(conn: ConnectionLike, *, organization_id: str, bot_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM bot_behavior_settings WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id))


def update_bot_behavior_settings(conn: ConnectionLike, *, row_id: str, values: tuple[Any, ...], updated_at: str) -> None:
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
        values + (updated_at, row_id),
    )


def insert_bot_behavior_settings(
    conn: ConnectionLike,
    *,
    row_id: str,
    organization_id: str,
    bot_id: str,
    values: tuple[Any, ...],
    created_at: str,
) -> None:
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
        (row_id, organization_id, bot_id) + values + (created_at, created_at),
    )


def get_bot_behavior_settings(conn: ConnectionLike, row_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM bot_behavior_settings WHERE id = ?", (row_id,))
