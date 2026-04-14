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
