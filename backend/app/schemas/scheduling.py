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


class AppointmentRescheduleRequest(BaseModel):
    scheduled_for: str


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
