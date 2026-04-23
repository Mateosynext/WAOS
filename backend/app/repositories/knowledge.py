from __future__ import annotations

import os
from typing import Any

from .base import ConnectionLike

from ..db import execute, fetch_all, fetch_one
from ..defaults import default_bot_config
from ..utils import from_json, hash_password, new_id, slugify, to_json, utcnow_iso
from ..verticals import build_organization_settings

def create_or_update_knowledge_items(conn: ConnectionLike, *, organization_id: str, bot_id: str, config: dict) -> None:
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
