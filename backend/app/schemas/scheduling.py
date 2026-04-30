from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class AppointmentRequest(BaseModel):
    organization_id: str
    bot_id: str
    conversation_id: str | None = None
    contact_id: str | None = None
    scheduled_for: str
    status: str = "scheduled"
    duration_minutes: int = 30
    timezone: str = "America/Mexico_City"
    notes: str = ""
    client_request_id: str | None = Field(default=None, min_length=8, max_length=180)


class AppointmentRescheduleRequest(BaseModel):
    scheduled_for: str
    client_request_id: str | None = Field(default=None, min_length=8, max_length=180)


class AppointmentStatusRequest(BaseModel):
    reason: str = ""


class AgendaReminderPreferencesRequest(BaseModel):
    organization_id: str
    tone: Literal["amable", "formal", "cercano"] = "amable"
    hours_before: int = 24
    last_hours: int = 2
    count: int = 2


class AgendaBlockedSlotRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    start_at: str
    end_at: str
    reason: str = ""


class I18nConfigRequest(BaseModel):
    organization_id: str
    bot_id: str
    default_language: str = "es"
    supported_languages: list[str] = Field(default_factory=lambda: ["es", "en"])
    detect_contact_language: bool = True
    templates: dict[str, Any] = Field(default_factory=dict)
    fallback_language: str = "en"
    handoff_respect_language: bool = True


class RoutingRuleRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    name: str
    priority: int = 50
    conditions: dict[str, Any] = Field(default_factory=dict)
    assigned_user_id: str | None = None
    assigned_team: str | None = None
    status: Literal["active", "paused"] = "active"



class AgendaResourceRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    name: str = Field(min_length=1, max_length=180)
    resource_type: Literal["professional", "room", "seat", "machine", "branch"] = "professional"
    branch: str | None = None


class AgendaCapacityRuleRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    resource_id: str
    day_of_week: int = Field(ge=0, le=6)
    start_time: str
    end_time: str
    slot_capacity: int = Field(default=1, ge=1, le=50)


class AppointmentResourceAssignRequest(BaseModel):
    resource_id: str
    note: str = Field(default="", max_length=500)


from .response_models import FlexibleSchema


class AgendaOverviewSummary(FlexibleSchema):
    scheduled: int | None = None
    confirmed: int | None = None
    completed: int | None = None
    cancelled: int | None = None
    no_show: int | None = None
    upcoming: int | None = None


class AgendaOverviewResponse(FlexibleSchema):
    organization_id: str | None = None
    bot_id: str | None = None
    summary: AgendaOverviewSummary | None = None
    upcoming: list[FlexibleSchema] = Field(default_factory=list)
    reminders: list[FlexibleSchema] = Field(default_factory=list)


class AgendaReminderPreferencesResponse(FlexibleSchema):
    organization_id: str | None = None
    tone: str | None = None
    hours_before: int | None = None
    last_hours: int | None = None
    count: int | None = None
    updated_at: str | None = None


class AgendaBlockedSlotResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    reason: str | None = None
    created_by_user_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AgendaBlockedSlotDeleteResponse(FlexibleSchema):
    ok: bool = True
    id: str | None = None


class AgendaResourceResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    name: str | None = None
    resource_type: str | None = None
    branch: str | None = None
    status: str | None = None
    metadata_json: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AgendaCapacityRuleResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    resource_type: str | None = None
    day_of_week: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    slot_capacity: int | None = None
    status: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AgendaCapacityResourceOverview(FlexibleSchema):
    resource_id: str | None = None
    name: str | None = None
    resource_type: str | None = None
    branch: str | None = None
    weekly_slots: int | None = None
    rules_count: int | None = None
    assigned_appointments: int | None = None


class AgendaCapacitySummary(FlexibleSchema):
    resources: int | None = None
    capacity_rules: int | None = None
    declared_weekly_slots: int | None = None
    upcoming_appointments: int | None = None
    assigned_upcoming_appointments: int | None = None
    unassigned_upcoming_appointments: int | None = None


class AgendaCapacityOverviewResponse(FlexibleSchema):
    organization_id: str | None = None
    bot_id: str | None = None
    summary: AgendaCapacitySummary | None = None
    resources: list[AgendaCapacityResourceOverview] = Field(default_factory=list)
    rules: list[AgendaCapacityRuleResponse] = Field(default_factory=list)
    upcoming: list[FlexibleSchema] = Field(default_factory=list)


class AppointmentResourceAssignmentResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    appointment_id: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    resource_type: str | None = None
    assigned_by: str | None = None
    note: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
