from __future__ import annotations

from ..application.support import bot_payload


def serialize_bot_details(conn, bot: dict) -> dict:
    return bot_payload(conn, bot)
