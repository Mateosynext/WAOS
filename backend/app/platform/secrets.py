from __future__ import annotations

import hashlib
import hmac
from typing import Any

from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..contracts import count_row, runtime_callback_row, integration_sync_run_row
from ..verticals import get_vertical_profile
from ..utils import (
    add_minutes,
    current_mfa_code,
    decrypt_secret,
    encrypt_secret,
    from_json,
    generate_recovery_codes,
    generate_totp_secret,
    hash_value,
    new_id,
    next_day_iso,
    parse_iso,
    provisioning_uri,
    qr_svg_data_url,
    random_token,
    to_json,
    utcnow_iso,
    verify_totp,
)

def _canonical_json(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}***{value[-3:]}"


def _record_secret_access(
    conn,
    *,
    secret_id: str,
    organization_id: str,
    actor_type: str,
    actor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    now = utcnow_iso()
    execute(
        conn,
        "UPDATE secret_entries SET last_accessed_at = ?, last_access_actor_type = ?, last_access_actor_id = ? WHERE id = ?",
        (now, actor_type, actor_id, secret_id),
    )
    execute(
        conn,
        "INSERT INTO audit_logs (id, organization_id, actor_user_id, actor_type, entity_type, entity_id, action, metadata_json, created_at) VALUES (?, ?, ?, ?, 'secret', ?, 'secret.accessed', ?, ?)",
        (new_id('audit'), organization_id, actor_id if actor_type == 'user' else None, actor_type, secret_id, to_json(metadata or {}), now),
    )


def serialize_secret_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload.pop('value_encrypted', None)
    payload['metadata'] = from_json(payload.get('metadata_json'), {})
    return payload


def resolve_secret(
    conn,
    *,
    organization_id: str,
    key_name: str,
    bot_id: str | None = None,
    actor_type: str = 'runtime',
    actor_id: str | None = None,
) -> str | None:
    candidates = []
    if bot_id:
        candidates.append((organization_id, bot_id, key_name))
    candidates.append((organization_id, None, key_name))
    for org_id, scoped_bot_id, scoped_key in candidates:
        row = fetch_one(
            conn,
            "SELECT * FROM secret_entries WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND key_name = ? ORDER BY updated_at DESC LIMIT 1",
            (org_id, scoped_bot_id, scoped_key),
        )
        if not row:
            continue
        encrypted = row.get('value_encrypted')
        if encrypted:
            secret_value = decrypt_secret(encrypted, settings.secret_encryption_key)
            _record_secret_access(conn, secret_id=row['id'], organization_id=organization_id, actor_type=actor_type, actor_id=actor_id, metadata={'key_name': key_name})
            return secret_value
    return None


def store_secret(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    scope: str,
    key_name: str,
    secret_value: str,
    expires_at: str | None = None,
) -> dict[str, Any]:
    normalized = (secret_value or "").strip()
    if len(normalized) < 8:
        raise ValueError("secret_value_too_short")
    existing = fetch_one(
        conn,
        "SELECT * FROM secret_entries WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND key_name = ?",
        (organization_id, bot_id, key_name),
    )
    now = utcnow_iso()
    masked = mask_secret(normalized)
    encrypted = encrypt_secret(normalized, settings.secret_encryption_key)
    metadata = {"length": len(normalized), "scope": scope, "rotation_state": "current"}
    if existing:
        execute(
            conn,
            """
            UPDATE secret_entries
            SET scope = ?, value_masked = ?, value_encrypted = ?, encryption_version = 'v2', metadata_json = ?, expires_at = ?, last_rotated_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (scope, masked, encrypted, to_json(metadata), expires_at, now, now, existing["id"]),
        )
        return serialize_secret_row(fetch_one(conn, "SELECT * FROM secret_entries WHERE id = ?", (existing["id"],)))
    secret_id = new_id("sec")
    execute(
        conn,
        """
        INSERT INTO secret_entries
        (id, organization_id, bot_id, scope, key_name, value_masked, value_encrypted, encryption_version, metadata_json, expires_at, last_rotated_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'v2', ?, ?, ?, ?, ?)
        """,
        (secret_id, organization_id, bot_id, scope, key_name, masked, encrypted, to_json(metadata), expires_at, now, now, now),
    )
    return serialize_secret_row(fetch_one(conn, "SELECT * FROM secret_entries WHERE id = ?", (secret_id,)))
