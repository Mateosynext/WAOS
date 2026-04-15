from __future__ import annotations

from fastapi import HTTPException

from ..db import fetch_all, fetch_one
from ..security import accessible_org_ids, ensure_org_access
from ..domains.appointments import (
    appointment_dashboard,
    cancel_appointment,
    confirm_appointment,
    create_appointment_bundle,
    mark_appointment_no_show,
    reschedule_appointment,
    send_appointment_followup,
)
from .support import org_filter_sql, require_permission
from .uow import UnitOfWork
from ..utils import new_id, utcnow_iso


class AppointmentService:
    def list(self, uow: UnitOfWork, *, user: dict, organization_id: str | None) -> list[dict]:
        conn = uow.conn
        if organization_id:
            ensure_org_access(user, organization_id)
            require_permission(user, organization_id, "appointment.manage")
        where_sql, params = org_filter_sql(user, organization_id, "organization_id")
        return fetch_all(conn, f"SELECT * FROM appointments {where_sql} ORDER BY scheduled_for ASC", params)

    def create(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "appointment.manage")
        return create_appointment_bundle(uow.conn, actor_user=user, **payload.model_dump())

    def confirm(self, uow: UnitOfWork, *, user: dict, appointment_id: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return confirm_appointment(uow.conn, appointment["id"], actor_user=user)

    def reschedule(self, uow: UnitOfWork, *, user: dict, appointment_id: str, scheduled_for: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return reschedule_appointment(uow.conn, appointment["id"], scheduled_for=scheduled_for, actor_user=user)

    def cancel(self, uow: UnitOfWork, *, user: dict, appointment_id: str, reason: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return cancel_appointment(uow.conn, appointment["id"], reason=reason, actor_user=user)

    def no_show(self, uow: UnitOfWork, *, user: dict, appointment_id: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return mark_appointment_no_show(uow.conn, appointment["id"], actor_user=user)

    def follow_up(self, uow: UnitOfWork, *, user: dict, appointment_id: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return send_appointment_followup(uow.conn, appointment["id"], actor_user=user)

    def reminder_preferences(self, uow: UnitOfWork, *, user: dict, organization_id: str | None) -> dict:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, "appointment.manage")
        row = fetch_one(uow.conn, "SELECT * FROM agenda_reminder_preferences WHERE organization_id = ?", (selected_org,))
        if not row:
            return {
                "organization_id": selected_org,
                "tone": "amable",
                "hours_before": 24,
                "last_hours": 2,
                "count": 2,
                "updated_at": None,
            }
        return row

    def save_reminder_preferences(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "appointment.manage")
        now = utcnow_iso()
        existing = fetch_one(uow.conn, "SELECT id FROM agenda_reminder_preferences WHERE organization_id = ?", (payload.organization_id,))
        if existing:
            uow.conn.execute(
                """
                UPDATE agenda_reminder_preferences
                SET tone = ?, hours_before = ?, last_hours = ?, count = ?, updated_by_user_id = ?, updated_at = ?
                WHERE organization_id = ?
                """,
                (payload.tone, payload.hours_before, payload.last_hours, payload.count, user["id"], now, payload.organization_id),
            )
        else:
            uow.conn.execute(
                """
                INSERT INTO agenda_reminder_preferences
                (id, organization_id, tone, hours_before, last_hours, count, updated_by_user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id("arp"), payload.organization_id, payload.tone, payload.hours_before, payload.last_hours, payload.count, user["id"], now, now),
            )
        return self.reminder_preferences(uow, user=user, organization_id=payload.organization_id)

    def list_blocked_slots(self, uow: UnitOfWork, *, user: dict, organization_id: str | None) -> list[dict]:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, "appointment.manage")
        return fetch_all(
            uow.conn,
            "SELECT * FROM agenda_blocked_slots WHERE organization_id = ? ORDER BY start_at ASC, created_at DESC LIMIT 200",
            (selected_org,),
        )

    def create_blocked_slot(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "appointment.manage")
        if str(payload.end_at) <= str(payload.start_at):
            raise HTTPException(status_code=400, detail="blocked_slot_invalid_range")
        overlapping = fetch_one(
            uow.conn,
            """
            SELECT id FROM agenda_blocked_slots
            WHERE organization_id = ?
              AND COALESCE(bot_id, '') = COALESCE(?, '')
              AND start_at < ?
              AND end_at > ?
            LIMIT 1
            """,
            (payload.organization_id, payload.bot_id, payload.end_at, payload.start_at),
        )
        if overlapping:
            raise HTTPException(status_code=409, detail="blocked_slot_overlaps_existing")
        now = utcnow_iso()
        slot_id = new_id("abk")
        uow.conn.execute(
            """
            INSERT INTO agenda_blocked_slots
            (id, organization_id, bot_id, start_at, end_at, reason, created_by_user_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (slot_id, payload.organization_id, payload.bot_id, payload.start_at, payload.end_at, payload.reason, user["id"], now, now),
        )
        return fetch_one(uow.conn, "SELECT * FROM agenda_blocked_slots WHERE id = ?", (slot_id,)) or {}

    def delete_blocked_slot(self, uow: UnitOfWork, *, user: dict, slot_id: str) -> dict:
        slot = fetch_one(uow.conn, "SELECT * FROM agenda_blocked_slots WHERE id = ?", (slot_id,))
        if not slot:
            raise HTTPException(status_code=404, detail="blocked_slot_not_found")
        ensure_org_access(user, slot["organization_id"])
        require_permission(user, slot["organization_id"], "appointment.manage")
        uow.conn.execute("DELETE FROM agenda_blocked_slots WHERE id = ?", (slot_id,))
        return {"ok": True, "id": slot_id}

    def agenda_overview(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> dict:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, "appointment.manage")
        return appointment_dashboard(uow.conn, selected_org, bot_id)

    def _get_accessible_appointment(self, uow: UnitOfWork, *, user: dict, appointment_id: str) -> dict:
        appointment = fetch_one(uow.conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        if not appointment:
            raise HTTPException(status_code=404, detail="appointment_not_found")
        ensure_org_access(user, appointment["organization_id"])
        require_permission(user, appointment["organization_id"], "appointment.manage")
        return appointment
