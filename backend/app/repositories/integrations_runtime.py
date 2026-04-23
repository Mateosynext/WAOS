from __future__ import annotations

from typing import Any

from .base import ConnectionLike
from ..db import execute, fetch_all, fetch_one
from ..utils import new_id, to_json, utcnow_iso


def update_integration_config(
    conn: ConnectionLike,
    integration_id: str,
    config: dict[str, Any],
    *,
    health_status: str | None = None,
    credential_status: str | None = None,
    last_error: str | None = None,
) -> dict[str, Any]:
    updates = ["config_json = ?", "updated_at = ?"]
    params: list[Any] = [to_json(config), utcnow_iso()]
    if health_status is not None:
        updates.append("health_status = ?")
        params.append(health_status)
    if credential_status is not None:
        updates.append("credential_status = ?")
        params.append(credential_status)
    if last_error is not None:
        updates.append("last_error = ?")
        params.append(last_error)
    params.append(integration_id)
    execute(conn, f"UPDATE integration_connections SET {', '.join(updates)} WHERE id = ?", params)
    return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,)) or {}


def create_oauth_state(
    conn: ConnectionLike,
    *,
    organization_id: str,
    integration_id: str,
    provider: str,
    state_token_hash: str,
    redirect_uri: str,
    scope: list[str],
    expires_at: str,
) -> dict[str, Any]:
    row_id = new_id("oauth")
    created_at = utcnow_iso()
    execute(
        conn,
        "INSERT INTO oauth_states (id, organization_id, integration_id, provider, state_token_hash, redirect_uri, scope, code_verifier, expires_at, consumed_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?)",
        (row_id, organization_id, integration_id, provider, state_token_hash, redirect_uri, " ".join(scope), expires_at, created_at),
    )
    return fetch_one(conn, "SELECT * FROM oauth_states WHERE id = ?", (row_id,)) or {}


def get_oauth_state_by_hash(conn: ConnectionLike, state_token_hash: str) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM oauth_states WHERE state_token_hash = ?", (state_token_hash,))


def get_integration_by_id(conn: ConnectionLike, integration_id: str) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,))


def mark_oauth_state_consumed(conn: ConnectionLike, oauth_state_id: str, *, consumed_at: str | None = None) -> None:
    execute(conn, "UPDATE oauth_states SET consumed_at = ? WHERE id = ?", (consumed_at or utcnow_iso(), oauth_state_id))


def schedule_integration_sync_now(conn: ConnectionLike, integration_id: str, *, timestamp: str | None = None) -> dict[str, Any] | None:
    now = timestamp or utcnow_iso()
    execute(conn, "UPDATE integration_connections SET next_sync_at = ?, updated_at = ? WHERE id = ?", (now, now, integration_id))
    return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,))


def mark_integration_health(
    conn: ConnectionLike,
    integration_id: str,
    *,
    health_status: str,
    credential_status: str | None = None,
    last_error: str | None = None,
    last_provider_event_at: str | None = None,
    last_provider_status_code: int | None = None,
) -> dict[str, Any] | None:
    updates = ["health_status = ?", "updated_at = ?"]
    params: list[Any] = [health_status, utcnow_iso()]
    if credential_status is not None:
        updates.append("credential_status = ?")
        params.append(credential_status)
    if last_error is not None:
        updates.append("last_error = ?")
        params.append(last_error)
    else:
        updates.append("last_error = NULL")
    if last_provider_event_at is not None:
        updates.append("last_provider_event_at = ?")
        params.append(last_provider_event_at)
    if last_provider_status_code is not None:
        updates.append("last_provider_status_code = ?")
        params.append(last_provider_status_code)
    params.append(integration_id)
    execute(conn, f"UPDATE integration_connections SET {', '.join(updates)} WHERE id = ?", params)
    return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,))


def list_syncable_appointments(conn: ConnectionLike, *, organization_id: str, bot_id: str | None) -> list[dict[str, Any]]:
    return fetch_all(
        conn,
        "SELECT * FROM appointments WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND status IN ('scheduled','confirmed') ORDER BY scheduled_for ASC LIMIT 100",
        (organization_id, bot_id),
    )


def mark_appointment_provider_sync(
    conn: ConnectionLike,
    *,
    appointment_id: str,
    external_id: str,
    provider_payload: dict[str, Any],
    integration_id: str,
    provider: str = "google_calendar",
    synced_at: str | None = None,
) -> dict[str, Any] | None:
    now = synced_at or utcnow_iso()
    execute(
        conn,
        "UPDATE appointments SET external_id = ?, provider = ?, provider_payload_json = ?, integration_id = ?, synced_at = ?, updated_at = ? WHERE id = ?",
        (external_id, provider, to_json(provider_payload), integration_id, now, now, appointment_id),
    )
    return fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))


def mark_fake_google_calendar_sync(conn: ConnectionLike, *, appointment_id: str, integration_id: str, synced_at: str | None = None) -> dict[str, Any] | None:
    external_id = f"gcal_fake_{appointment_id}"
    return mark_appointment_provider_sync(
        conn,
        appointment_id=appointment_id,
        external_id=external_id,
        provider_payload={"id": external_id, "status": "confirmed"},
        integration_id=integration_id,
        synced_at=synced_at,
    )


def find_appointment_by_external_id(conn: ConnectionLike, *, organization_id: str, external_id: str | None) -> dict[str, Any] | None:
    if not external_id:
        return None
    return fetch_one(conn, "SELECT * FROM appointments WHERE organization_id = ? AND external_id = ?", (organization_id, external_id))


def find_appointment_by_id(conn: ConnectionLike, *, organization_id: str, appointment_id: str | None) -> dict[str, Any] | None:
    if not appointment_id:
        return None
    return fetch_one(conn, "SELECT * FROM appointments WHERE organization_id = ? AND id = ?", (organization_id, appointment_id))


def mark_appointment_cancelled_from_provider(conn: ConnectionLike, *, appointment_id: str, provider_payload: dict[str, Any], synced_at: str | None = None) -> dict[str, Any] | None:
    now = synced_at or utcnow_iso()
    execute(
        conn,
        "UPDATE appointments SET status = 'cancelled', provider_payload_json = ?, synced_at = ?, updated_at = ? WHERE id = ?",
        (to_json(provider_payload), now, now, appointment_id),
    )
    return fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))


def update_appointment_from_provider(
    conn: ConnectionLike,
    *,
    appointment_id: str,
    scheduled_for: str,
    status: str,
    notes: str,
    duration_minutes: int,
    timezone: str,
    provider_payload: dict[str, Any],
    integration_id: str,
    provider: str = "google_calendar",
    synced_at: str | None = None,
) -> dict[str, Any] | None:
    now = synced_at or utcnow_iso()
    execute(
        conn,
        "UPDATE appointments SET scheduled_for = ?, status = ?, notes = ?, duration_minutes = ?, timezone = ?, provider = ?, provider_payload_json = ?, integration_id = ?, synced_at = ?, updated_at = ? WHERE id = ?",
        (scheduled_for, status, notes, duration_minutes, timezone, provider, to_json(provider_payload), integration_id, now, now, appointment_id),
    )
    return fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))


def create_appointment_from_provider(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str | None,
    scheduled_for: str,
    status: str,
    duration_minutes: int,
    timezone: str,
    notes: str,
    external_id: str,
    provider_payload: dict[str, Any],
    integration_id: str,
    provider: str = "google_calendar",
    synced_at: str | None = None,
) -> dict[str, Any] | None:
    row_id = new_id("appt")
    now = synced_at or utcnow_iso()
    execute(
        conn,
        "INSERT INTO appointments (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, created_at, updated_at, external_id, provider, provider_payload_json, integration_id, synced_at) VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row_id,
            organization_id,
            bot_id,
            scheduled_for,
            status,
            duration_minutes,
            timezone,
            notes,
            now,
            now,
            external_id,
            provider,
            to_json(provider_payload),
            integration_id,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (row_id,))


def mark_integration_sync_completed(conn: ConnectionLike, integration_id: str, *, timestamp: str | None = None) -> dict[str, Any] | None:
    now = timestamp or utcnow_iso()
    execute(conn, "UPDATE integration_connections SET last_sync_at = ?, last_provider_event_at = ?, updated_at = ? WHERE id = ?", (now, now, now, integration_id))
    return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (integration_id,))
