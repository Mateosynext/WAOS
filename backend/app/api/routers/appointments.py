from __future__ import annotations

from fastapi import APIRouter, Query

from ...application.appointment_service import AppointmentService
from ...schemas import AppointmentRequest, AppointmentRescheduleRequest, AppointmentStatusRequest
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
