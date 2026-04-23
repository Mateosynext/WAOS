from __future__ import annotations

from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ..repositories import create_audit_log, create_message, get_bot, get_contact, get_conversation
from ..repositories.appointments_domain import (
    appointment_dashboard_metrics,
    get_appointment,
    get_latest_conversation_for_contact,
    get_outbox_message,
    insert_appointment,
    insert_outbox_message,
    update_appointment_cancelled,
    update_appointment_confirmed,
    update_appointment_followup_sent,
    update_appointment_no_show,
    update_appointment_rescheduled,
)
from ..utils import add_minutes, from_json, new_id, parse_iso, to_json, utcnow_iso

def _safe_filename(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "waos-report"


def _queue_whatsapp_message(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str | None,
    body: str,
    scheduled_for: str | None = None,
    priority: int = 80,
    metadata: dict[str, Any] | None = None,
) -> dict:
    now = utcnow_iso()
    scheduled = scheduled_for or now
    conversation = get_conversation(conn, conversation_id) if conversation_id else None
    resolved_conv_id = conversation_id or (conversation or {}).get("id")
    if not resolved_conv_id and contact_id and bot_id:
        existing = get_latest_conversation_for_contact(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id)
        resolved_conv_id = existing["id"] if existing else None
    if not resolved_conv_id:
        return {}
    message = create_message(
        conn,
        organization_id=organization_id,
        conversation_id=resolved_conv_id,
        contact_id=contact_id,
        bot_id=bot_id,
        direction="outbound",
        kind="text",
        source="system",
        body=body,
        status="queued",
        metadata=metadata or {},
    )
    outbox_id = new_id("out")
    insert_outbox_message(
        conn,
        outbox_id=outbox_id,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=resolved_conv_id,
        payload={"message_id": message["id"], "contact_id": contact_id, "body": body, **(metadata or {})},
        priority=priority,
        scheduled_for=scheduled,
        created_at=now,
    )
    return get_outbox_message(conn, outbox_id) or {}


def _default_reminder_at(scheduled_for: str) -> str:
    target = parse_iso(scheduled_for)
    if not target:
        return add_minutes(utcnow_iso(), 30)
    now = parse_iso(utcnow_iso())
    assert now is not None
    delta = target - now
    if delta.total_seconds() > 26 * 3600:
        reminder = target - timedelta(hours=24)
    elif delta.total_seconds() > 3 * 3600:
        reminder = target - timedelta(hours=2)
    else:
        reminder = now + timedelta(minutes=15)
    return reminder.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def create_appointment_bundle(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    scheduled_for: str,
    duration_minutes: int,
    timezone: str,
    notes: str = "",
    conversation_id: str | None = None,
    contact_id: str | None = None,
    status: str = "scheduled",
    actor_user: dict | None = None,
) -> dict:
    appointment_id = new_id("appt")
    now = utcnow_iso()
    reminder_scheduled_at = _default_reminder_at(scheduled_for)
    insert_appointment(
        conn,
        appointment_id=appointment_id,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        scheduled_for=scheduled_for,
        status=status,
        duration_minutes=duration_minutes,
        timezone=timezone,
        notes=notes,
        reminder_scheduled_at=reminder_scheduled_at,
        created_at=now,
    )
    appointment = get_appointment(conn, appointment_id)
    if appointment and contact_id:
        human_date = scheduled_for
        _queue_whatsapp_message(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            body=f"Tu cita quedó reservada para {human_date}. Te recordaré automáticamente antes de la hora.",
            metadata={"type": "appointment_created", "appointment_id": appointment_id},
            priority=90,
        )
        _queue_whatsapp_message(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            body=f"Recordatorio: tienes una cita programada para {human_date}. Responde con CONFIRMAR si asistirás.",
            scheduled_for=reminder_scheduled_at,
            metadata={"type": "appointment_reminder", "appointment_id": appointment_id},
            priority=85,
        )
    if actor_user:
        create_audit_log(
            conn,
            organization_id=organization_id,
            actor_user_id=actor_user.get("id"),
            actor_type="user",
            entity_type="appointment",
            entity_id=appointment_id,
            action="appointment.bundle_created",
            metadata={"scheduled_for": scheduled_for, "reminder_scheduled_at": reminder_scheduled_at},
        )
    return get_appointment(conn, appointment_id) or {}


def _appointment_row(conn, appointment_id: str) -> dict:
    appointment = get_appointment(conn, appointment_id)
    if not appointment:
        raise ValueError("appointment_not_found")
    return appointment


def confirm_appointment(conn, appointment_id: str, *, actor_user: dict | None = None) -> dict:
    appointment = _appointment_row(conn, appointment_id)
    now = utcnow_iso()
    update_appointment_confirmed(conn, appointment_id=appointment_id, confirmed_at=now, updated_at=now)
    _queue_whatsapp_message(
        conn,
        organization_id=appointment["organization_id"],
        bot_id=appointment["bot_id"],
        conversation_id=appointment.get("conversation_id"),
        contact_id=appointment.get("contact_id"),
        body="Perfecto, tu asistencia quedó confirmada. Si necesitas reprogramar, te ayudo por aquí.",
        metadata={"type": "appointment_confirmed", "appointment_id": appointment_id},
        priority=95,
    )
    if actor_user:
        create_audit_log(conn, organization_id=appointment["organization_id"], actor_user_id=actor_user.get("id"), actor_type="user", entity_type="appointment", entity_id=appointment_id, action="appointment.confirmed", metadata={})
    return get_appointment(conn, appointment_id) or {}


def reschedule_appointment(conn, appointment_id: str, *, scheduled_for: str, actor_user: dict | None = None) -> dict:
    appointment = _appointment_row(conn, appointment_id)
    now = utcnow_iso()
    reminder_scheduled_at = _default_reminder_at(scheduled_for)
    update_appointment_rescheduled(conn, appointment_id=appointment_id, scheduled_for=scheduled_for, reminder_scheduled_at=reminder_scheduled_at, updated_at=now)
    _queue_whatsapp_message(
        conn,
        organization_id=appointment["organization_id"],
        bot_id=appointment["bot_id"],
        conversation_id=appointment.get("conversation_id"),
        contact_id=appointment.get("contact_id"),
        body=f"Tu cita fue reprogramada para {scheduled_for}. Te enviaré un recordatorio automático antes de la nueva hora.",
        metadata={"type": "appointment_rescheduled", "appointment_id": appointment_id},
        priority=95,
    )
    _queue_whatsapp_message(
        conn,
        organization_id=appointment["organization_id"],
        bot_id=appointment["bot_id"],
        conversation_id=appointment.get("conversation_id"),
        contact_id=appointment.get("contact_id"),
        body=f"Recordatorio: tu cita reprogramada es {scheduled_for}. Responde con CONFIRMAR si asistirás.",
        scheduled_for=reminder_scheduled_at,
        metadata={"type": "appointment_reminder_rescheduled", "appointment_id": appointment_id},
        priority=85,
    )
    if actor_user:
        create_audit_log(conn, organization_id=appointment["organization_id"], actor_user_id=actor_user.get("id"), actor_type="user", entity_type="appointment", entity_id=appointment_id, action="appointment.rescheduled", metadata={"scheduled_for": scheduled_for})
    return get_appointment(conn, appointment_id) or {}


def cancel_appointment(conn, appointment_id: str, *, reason: str = "", actor_user: dict | None = None) -> dict:
    appointment = _appointment_row(conn, appointment_id)
    now = utcnow_iso()
    notes = (appointment.get("notes") or "").strip()
    if reason:
        notes = f"{notes}\nCancelación: {reason}".strip()
    update_appointment_cancelled(conn, appointment_id=appointment_id, cancelled_at=now, notes=notes, updated_at=now)
    _queue_whatsapp_message(
        conn,
        organization_id=appointment["organization_id"],
        bot_id=appointment["bot_id"],
        conversation_id=appointment.get("conversation_id"),
        contact_id=appointment.get("contact_id"),
        body="Tu cita quedó cancelada. Cuando quieras, te ayudo a reagendar aquí mismo.",
        metadata={"type": "appointment_cancelled", "appointment_id": appointment_id},
        priority=90,
    )
    if actor_user:
        create_audit_log(conn, organization_id=appointment["organization_id"], actor_user_id=actor_user.get("id"), actor_type="user", entity_type="appointment", entity_id=appointment_id, action="appointment.cancelled", metadata={"reason": reason})
    return get_appointment(conn, appointment_id) or {}


def mark_appointment_no_show(conn, appointment_id: str, *, actor_user: dict | None = None) -> dict:
    appointment = _appointment_row(conn, appointment_id)
    now = utcnow_iso()
    update_appointment_no_show(conn, appointment_id=appointment_id, no_show_at=now, updated_at=now)
    _queue_whatsapp_message(
        conn,
        organization_id=appointment["organization_id"],
        bot_id=appointment["bot_id"],
        conversation_id=appointment.get("conversation_id"),
        contact_id=appointment.get("contact_id"),
        body="No pudimos verte en tu cita. Si quieres, te propongo dos horarios nuevos y la reprogramamos aquí.",
        scheduled_for=add_minutes(now, 20),
        metadata={"type": "appointment_no_show_recovery", "appointment_id": appointment_id},
        priority=92,
    )
    if actor_user:
        create_audit_log(conn, organization_id=appointment["organization_id"], actor_user_id=actor_user.get("id"), actor_type="user", entity_type="appointment", entity_id=appointment_id, action="appointment.no_show", metadata={})
    return get_appointment(conn, appointment_id) or {}


def send_appointment_followup(conn, appointment_id: str, *, actor_user: dict | None = None) -> dict:
    appointment = _appointment_row(conn, appointment_id)
    now = utcnow_iso()
    update_appointment_followup_sent(conn, appointment_id=appointment_id, followup_sent_at=now, updated_at=now)
    _queue_whatsapp_message(
        conn,
        organization_id=appointment["organization_id"],
        bot_id=appointment["bot_id"],
        conversation_id=appointment.get("conversation_id"),
        contact_id=appointment.get("contact_id"),
        body="Gracias por tu visita. ¿Cómo te fue? También puedo ayudarte con tu siguiente cita o seguimiento.",
        metadata={"type": "appointment_followup", "appointment_id": appointment_id},
        priority=88,
    )
    if actor_user:
        create_audit_log(conn, organization_id=appointment["organization_id"], actor_user_id=actor_user.get("id"), actor_type="user", entity_type="appointment", entity_id=appointment_id, action="appointment.followup_sent", metadata={})
    return get_appointment(conn, appointment_id) or {}


def appointment_dashboard(conn, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    where = "organization_id = ?"
    params: list[Any] = [organization_id]
    if bot_id:
        where += " AND bot_id = ?"
        params.append(bot_id)
    metrics = appointment_dashboard_metrics(conn, organization_id=organization_id, bot_id=bot_id)
    total = metrics["total"]
    confirmed = metrics["confirmed"]
    no_show = metrics["no_show"]
    upcoming = metrics["upcoming"]
    pending = metrics["pending"]
    total_value = max(int(total.get("value") or 0), 1)
    show_rate = round((int(confirmed.get("value") or 0) / total_value) * 100, 1)
    no_show_rate = round((int(no_show.get("value") or 0) / total_value) * 100, 1)
    return {
        "summary": {
            "total_appointments": int(total.get("value") or 0),
            "pending": int(pending.get("value") or 0),
            "confirmed": int(confirmed.get("value") or 0),
            "no_show": int(no_show.get("value") or 0),
            "show_rate": show_rate,
            "no_show_rate": no_show_rate,
        },
        "upcoming": upcoming,
    }
