from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ...application.appointment_service import AppointmentService
from ...schemas import (
    AgendaBlockedSlotDeleteResponse,
    AgendaBlockedSlotRequest,
    AgendaBlockedSlotResponse,
    AgendaCapacityOverviewResponse,
    AgendaCapacityRuleRequest,
    AgendaCapacityRuleResponse,
    AgendaOverviewResponse,
    AgendaReminderPreferencesRequest,
    AgendaReminderPreferencesResponse,
    AgendaResourceRequest,
    AgendaResourceResponse,
    AppointmentRequest,
    AppointmentRescheduleRequest,
    AppointmentResourceAssignRequest,
    AppointmentResourceAssignmentResponse,
    AppointmentStatusRequest,
    OperationalAppointmentResponse,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["appointments"])
service = AppointmentService()


@router.get("/api/v1/appointments", response_model=list[OperationalAppointmentResponse])
def list_appointments(organization_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> list[dict]:
    return service.list(uow, user=user, organization_id=organization_id)


def _client_request_id_from_request(request: Request, explicit: str | None = None) -> str | None:
    return (request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key") or explicit or "").strip() or None


@router.post("/api/v1/appointments", response_model=OperationalAppointmentResponse)
def create_appointment(payload: AppointmentRequest, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create(uow, user=user, payload=payload, client_request_id=_client_request_id_from_request(request, payload.client_request_id))


@router.post("/api/v1/appointments/{appointment_id}/confirm", response_model=OperationalAppointmentResponse)
def confirm_appointment(appointment_id: str, payload: AppointmentStatusRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    del payload
    return service.confirm(uow, user=user, appointment_id=appointment_id)


@router.post("/api/v1/appointments/{appointment_id}/reschedule", response_model=OperationalAppointmentResponse)
def reschedule_appointment(appointment_id: str, payload: AppointmentRescheduleRequest, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.reschedule(uow, user=user, appointment_id=appointment_id, scheduled_for=payload.scheduled_for, client_request_id=_client_request_id_from_request(request, payload.client_request_id))


@router.post("/api/v1/appointments/{appointment_id}/cancel", response_model=OperationalAppointmentResponse)
def cancel_appointment(appointment_id: str, payload: AppointmentStatusRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.cancel(uow, user=user, appointment_id=appointment_id, reason=payload.reason)


@router.post("/api/v1/appointments/{appointment_id}/no-show", response_model=OperationalAppointmentResponse)
def no_show_appointment(appointment_id: str, payload: AppointmentStatusRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    del payload
    return service.no_show(uow, user=user, appointment_id=appointment_id)


@router.post("/api/v1/appointments/{appointment_id}/follow-up", response_model=OperationalAppointmentResponse)
def follow_up_appointment(appointment_id: str, payload: AppointmentStatusRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    del payload
    return service.follow_up(uow, user=user, appointment_id=appointment_id)


@router.get("/api/v1/agenda/overview", response_model=AgendaOverviewResponse)
def agenda_overview(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.agenda_overview(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.get("/api/v1/agenda/reminder-preferences", response_model=AgendaReminderPreferencesResponse)
def agenda_reminder_preferences(organization_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.reminder_preferences(uow, user=user, organization_id=organization_id)


@router.post("/api/v1/agenda/reminder-preferences", response_model=AgendaReminderPreferencesResponse)
def save_agenda_reminder_preferences(payload: AgendaReminderPreferencesRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.save_reminder_preferences(uow, user=user, payload=payload)


@router.get("/api/v1/agenda/blocked-slots", response_model=list[AgendaBlockedSlotResponse])
def list_agenda_blocked_slots(organization_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> list[dict]:
    return service.list_blocked_slots(uow, user=user, organization_id=organization_id)


@router.post("/api/v1/agenda/blocked-slots", response_model=AgendaBlockedSlotResponse)
def create_agenda_blocked_slot(payload: AgendaBlockedSlotRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create_blocked_slot(uow, user=user, payload=payload)


@router.delete("/api/v1/agenda/blocked-slots/{slot_id}", response_model=AgendaBlockedSlotDeleteResponse)
def delete_agenda_blocked_slot(slot_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.delete_blocked_slot(uow, user=user, slot_id=slot_id)


@router.get("/api/v1/agenda/resources", response_model=list[AgendaResourceResponse])
def list_agenda_resources(organization_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> list[dict]:
    return service.list_resources(uow, user=user, organization_id=organization_id)


@router.post("/api/v1/agenda/resources", response_model=AgendaResourceResponse)
def create_agenda_resource(payload: AgendaResourceRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create_resource(uow, user=user, payload=payload)


@router.get("/api/v1/agenda/capacity-rules", response_model=list[AgendaCapacityRuleResponse])
def list_agenda_capacity_rules(organization_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> list[dict]:
    return service.list_capacity_rules(uow, user=user, organization_id=organization_id)


@router.post("/api/v1/agenda/capacity-rules", response_model=AgendaCapacityRuleResponse)
def create_agenda_capacity_rule(payload: AgendaCapacityRuleRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create_capacity_rule(uow, user=user, payload=payload)


@router.get("/api/v1/agenda/capacity/overview", response_model=AgendaCapacityOverviewResponse)
def agenda_capacity_overview(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.capacity_overview(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.post("/api/v1/appointments/{appointment_id}/assign-resource", response_model=AppointmentResourceAssignmentResponse)
def assign_resource_to_appointment(appointment_id: str, payload: AppointmentResourceAssignRequest, user: CurrentUser, uow: CurrentUoW = None) -> dict:
    return service.assign_resource(uow, user=user, appointment_id=appointment_id, payload=payload)
