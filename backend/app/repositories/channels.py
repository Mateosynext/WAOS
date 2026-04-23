from __future__ import annotations

import os
from typing import Any

from .base import ConnectionLike

from ..db import execute, fetch_all, fetch_one
from ..defaults import default_bot_config
from ..utils import from_json, hash_password, new_id, slugify, to_json, utcnow_iso
from ..verticals import build_organization_settings

def get_whatsapp_number_by_phone_id(conn: ConnectionLike, phone_number_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE phone_number_id = ?", (phone_number_id,))


def get_whatsapp_number_for_bot(conn: ConnectionLike, bot_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE bot_id = ?", (bot_id,))
