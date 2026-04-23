from __future__ import annotations

from typing import Any

from .base import ConnectionLike, execute, fetch_all, fetch_one
from ..utils import to_json


def get_latest_conversation_for_contact(conn: ConnectionLike, *, organization_id: str, bot_id: str, contact_id: str) -> dict | None:
    return fetch_one(
        conn,
        "SELECT * FROM conversations WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY created_at DESC LIMIT 1",
        (organization_id, bot_id, contact_id),
    )


def insert_outbox_message(
    conn: ConnectionLike,
    *,
    outbox_id: str,
    organization_id: str,
    bot_id: str,
    conversation_id: str,
    payload: dict[str, Any],
    priority: int,
    scheduled_for: str,
    created_at: str,
) -> None:
    execute(
        conn,
        """
        INSERT INTO outbox_messages (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, status, attempts, last_error, provider_response_json, priority, next_attempt_at, locked_at, scheduled_for, sent_at, created_at)
        VALUES (?, ?, ?, NULL, ?, 'whatsapp', ?, 'queued', 0, NULL, '{}', ?, NULL, NULL, ?, NULL, ?)
        """,
        (outbox_id, organization_id, bot_id, conversation_id, to_json(payload), priority, scheduled_for, created_at),
    )


def get_outbox_message(conn: ConnectionLike, outbox_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM outbox_messages WHERE id = ?", (outbox_id,))


def insert_appointment(
    conn: ConnectionLike,
    *,
    appointment_id: str,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str | None,
    scheduled_for: str,
    status: str,
    duration_minutes: int,
    timezone: str,
    notes: str,
    reminder_scheduled_at: str,
    created_at: str,
) -> None:
    execute(
        conn,
        """
        INSERT INTO appointments
        (id, organization_id, bot_id, conversation_id, contact_id, scheduled_for, status, duration_minutes, timezone, notes, reminder_scheduled_at, followup_status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            appointment_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            scheduled_for,
            status,
            duration_minutes,
            timezone,
            notes,
            reminder_scheduled_at,
            created_at,
            created_at,
        ),
    )


def get_appointment(conn: ConnectionLike, appointment_id: str) -> dict | None:
    return fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))


def update_appointment_confirmed(conn: ConnectionLike, *, appointment_id: str, confirmed_at: str, updated_at: str) -> None:
    execute(conn, "UPDATE appointments SET status = 'confirmed', confirmed_at = ?, updated_at = ? WHERE id = ?", (confirmed_at, updated_at, appointment_id))


def update_appointment_rescheduled(
    conn: ConnectionLike,
    *,
    appointment_id: str,
    scheduled_for: str,
    reminder_scheduled_at: str,
    updated_at: str,
) -> None:
    execute(
        conn,
        """
        UPDATE appointments
        SET status = 'rescheduled', scheduled_for = ?, reminder_scheduled_at = ?, rescheduled_from_appointment_id = COALESCE(rescheduled_from_appointment_id, id), updated_at = ?
        WHERE id = ?
        """,
        (scheduled_for, reminder_scheduled_at, updated_at, appointment_id),
    )


def update_appointment_cancelled(
    conn: ConnectionLike,
    *,
    appointment_id: str,
    cancelled_at: str,
    notes: str,
    updated_at: str,
) -> None:
    execute(conn, "UPDATE appointments SET status = 'cancelled', cancelled_at = ?, notes = ?, updated_at = ? WHERE id = ?", (cancelled_at, notes, updated_at, appointment_id))


def update_appointment_no_show(conn: ConnectionLike, *, appointment_id: str, no_show_at: str, updated_at: str) -> None:
    execute(conn, "UPDATE appointments SET status = 'no_show', no_show_at = ?, followup_status = 'recommended', updated_at = ? WHERE id = ?", (no_show_at, updated_at, appointment_id))


def update_appointment_followup_sent(conn: ConnectionLike, *, appointment_id: str, followup_sent_at: str, updated_at: str) -> None:
    execute(conn, "UPDATE appointments SET followup_status = 'queued', followup_sent_at = ?, updated_at = ? WHERE id = ?", (followup_sent_at, updated_at, appointment_id))


def appointment_dashboard_metrics(conn: ConnectionLike, *, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    where = "organization_id = ?"
    params: list[Any] = [organization_id]
    if bot_id:
        where += " AND bot_id = ?"
        params.append(bot_id)
    return {
        "total": fetch_one(conn, f"SELECT COUNT(*) AS value FROM appointments WHERE {where}", params) or {},
        "confirmed": fetch_one(conn, f"SELECT COUNT(*) AS value FROM appointments WHERE {where} AND status IN ('confirmed','completed')", params) or {},
        "no_show": fetch_one(conn, f"SELECT COUNT(*) AS value FROM appointments WHERE {where} AND status = 'no_show'", params) or {},
        "upcoming": fetch_all(conn, f"SELECT * FROM appointments WHERE {where} ORDER BY scheduled_for ASC LIMIT 10", params),
        "pending": fetch_one(conn, f"SELECT COUNT(*) AS value FROM appointments WHERE {where} AND status IN ('pending','scheduled','created')", params) or {},
    }
