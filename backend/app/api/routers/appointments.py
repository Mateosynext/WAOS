from __future__ import annotations

from fastapi import APIRouter, Query

from ...application.appointment_service import AppointmentService
from ...schemas import AppointmentRequest, AppointmentRescheduleRequest, AppointmentStatusRequest, AgendaReminderPreferencesRequest, AgendaBlockedSlotRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["appointments"])
service = AppointmentService()


@router.get("/api/v1/appointments")
def list_appointments(organization_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> list[dict]:
    return service.list(uow, user=user, organization_id=organization_id)


@router.post("/api/v1/appointments")
def create_appointment(payload: AppointmentRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create(uow, user=user, payload=payload)


@router.post("/api/v1/appointments/{appointment_id}/confirm")
def confirm_appointment(appointment_id: str, payload: AppointmentStatusRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    del payload
    return service.confirm(uow, user=user, appointment_id=appointment_id)


@router.post("/api/v1/appointments/{appointment_id}/reschedule")
def reschedule_appointment(appointment_id: str, payload: AppointmentRescheduleRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.reschedule(uow, user=user, appointment_id=appointment_id, scheduled_for=payload.scheduled_for)


@router.post("/api/v1/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: str, payload: AppointmentStatusRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.cancel(uow, user=user, appointment_id=appointment_id, reason=payload.reason)


@router.post("/api/v1/appointments/{appointment_id}/no-show")
def no_show_appointment(appointment_id: str, payload: AppointmentStatusRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    del payload
    return service.no_show(uow, user=user, appointment_id=appointment_id)


@router.post("/api/v1/appointments/{appointment_id}/follow-up")
def follow_up_appointment(appointment_id: str, payload: AppointmentStatusRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    del payload
    return service.follow_up(uow, user=user, appointment_id=appointment_id)


@router.get("/api/v1/agenda/overview")
def agenda_overview(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.agenda_overview(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.get("/api/v1/agenda/reminder-preferences")
def agenda_reminder_preferences(organization_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.reminder_preferences(uow, user=user, organization_id=organization_id)


@router.post("/api/v1/agenda/reminder-preferences")
def save_agenda_reminder_preferences(payload: AgendaReminderPreferencesRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.save_reminder_preferences(uow, user=user, payload=payload)


@router.get("/api/v1/agenda/blocked-slots")
def list_agenda_blocked_slots(organization_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> list[dict]:
    return service.list_blocked_slots(uow, user=user, organization_id=organization_id)


@router.post("/api/v1/agenda/blocked-slots")
def create_agenda_blocked_slot(payload: AgendaBlockedSlotRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create_blocked_slot(uow, user=user, payload=payload)


@router.delete("/api/v1/agenda/blocked-slots/{slot_id}")
def delete_agenda_blocked_slot(slot_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.delete_blocked_slot(uow, user=user, slot_id=slot_id)
