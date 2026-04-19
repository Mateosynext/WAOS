from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode
from xml.sax.saxutils import escape

from .db import execute, fetch_one
from .platform import resolve_secret
from .repositories import get_bot, upsert_contact, upsert_conversation
from .utils import from_json, to_json, utcnow_iso
from .voice_channel_runtime import get_voice_channel_session, start_voice_channel_session

TWILIO_AUTH_TOKEN_KEYS = [
    "TWILIO_AUTH_TOKEN",
    "TWILIO_VOICE_AUTH_TOKEN",
]


def resolve_twilio_auth_token(conn, *, organization_id: str, bot_id: str | None) -> str | None:
    for key_name in TWILIO_AUTH_TOKEN_KEYS:
        token = resolve_secret(conn, organization_id=organization_id, bot_id=bot_id, key_name=key_name)
        if token:
            return token
    return None


def build_external_url(request, *, extra_query: dict[str, Any] | None = None) -> str:
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    base = f"{scheme}://{host}{request.url.path}"
    query_items: list[tuple[str, str]] = []
    for key, value in request.query_params.multi_items():
        if key not in {"bodySHA256"}:
            query_items.append((key, value))
    if extra_query:
        for key, value in extra_query.items():
            if value is None:
                continue
            query_items.append((key, str(value)))
    if query_items:
        return f"{base}?{urlencode(query_items, doseq=True)}"
    return base


def verify_twilio_signature(*, auth_token: str, signature: str | None, url: str, params: Mapping[str, Any]) -> bool:
    if not auth_token or not signature:
        return False
    pieces = [url]
    for key in sorted(params.keys()):
        value = params.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                pieces.append(f"{key}{item}")
        else:
            pieces.append(f"{key}{value}")
    payload = "".join(pieces).encode("utf-8")
    digest = hmac.new(auth_token.encode("utf-8"), payload, hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def find_or_create_twilio_voice_session(
    conn,
    *,
    bot_id: str,
    from_phone: str,
    to_phone: str | None,
    call_sid: str,
    caller_name: str | None = None,
) -> dict[str, Any]:
    bot = get_bot(conn, bot_id)
    if not bot:
        raise ValueError("Bot not found")
    existing_rows = execute_fetch_all(
        conn,
        "SELECT id, metadata_json FROM voice_channel_sessions WHERE bot_id = ? AND channel = 'twilio_voice' ORDER BY updated_at DESC LIMIT 25",
        (bot_id,),
    )
    for row in existing_rows:
        metadata = from_json(row.get("metadata_json"), {})
        if str(metadata.get("provider_call_sid") or "").strip() == call_sid:
            session = get_voice_channel_session(conn, session_id=row["id"])
            if session:
                return session
    contact = upsert_contact(conn, organization_id=bot["organization_id"], phone=from_phone, name=caller_name)
    conversation = upsert_conversation(conn, organization_id=bot["organization_id"], bot_id=bot_id, contact_id=contact["id"])
    return start_voice_channel_session(
        conn,
        organization_id=bot["organization_id"],
        bot_id=bot_id,
        contact_id=contact["id"],
        conversation_id=conversation["id"],
        channel="twilio_voice",
        requested_modality="voice",
        metadata={
            "provider": "twilio",
            "provider_call_sid": call_sid,
            "from_phone": from_phone,
            "to_phone": to_phone,
            "caller_name": caller_name,
        },
    )


def execute_fetch_all(conn, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(dict(row) if not isinstance(row, dict) else row)
    return items


def close_twilio_voice_session(conn, *, session_id: str, call_status: str | None, metadata: dict[str, Any] | None = None) -> dict[str, Any] | None:
    session = get_voice_channel_session(conn, session_id=session_id)
    if not session:
        return None
    merged = dict(session.get("metadata") or {})
    merged.update(metadata or {})
    if call_status:
        merged["last_call_status"] = call_status
    now = utcnow_iso()
    execute(
        conn,
        "UPDATE voice_channel_sessions SET state = ?, metadata_json = ?, updated_at = ?, ended_at = COALESCE(ended_at, ?) WHERE id = ?",
        ("ended", to_json(merged), now, now, session_id),
    )
    return get_voice_channel_session(conn, session_id=session_id)


class TwiMLResponseBuilder:
    def __init__(self) -> None:
        self.parts: list[str] = ['<?xml version="1.0" encoding="UTF-8"?><Response>']

    def say(self, text: str, *, language: str = "es-MX", voice: str = "Polly.Mia-Neural") -> None:
        if text.strip():
            self.parts.append(f'<Say language="{escape(language)}" voice="{escape(voice)}">{escape(text)}</Say>')

    def play(self, audio_url: str) -> None:
        if audio_url.strip():
            self.parts.append(f'<Play>{escape(audio_url)}</Play>')

    def gather_open(
        self,
        *,
        action: str,
        input_mode: str = "speech dtmf",
        method: str = "POST",
        language: str = "es-MX",
        speech_timeout: str = "auto",
        num_digits: int | None = None,
    ) -> None:
        attrs = [
            f'action="{escape(action)}"',
            f'input="{escape(input_mode)}"',
            f'method="{escape(method)}"',
            f'language="{escape(language)}"',
            f'speechTimeout="{escape(speech_timeout)}"',
        ]
        if num_digits:
            attrs.append(f'numDigits="{int(num_digits)}"')
        self.parts.append(f"<Gather {' '.join(attrs)}>")

    def gather_close(self) -> None:
        self.parts.append("</Gather>")

    def redirect(self, url: str, *, method: str = "POST") -> None:
        self.parts.append(f'<Redirect method="{escape(method)}">{escape(url)}</Redirect>')

    def hangup(self) -> None:
        self.parts.append("<Hangup/>")

    def build(self) -> str:
        return "".join([*self.parts, "</Response>"])
