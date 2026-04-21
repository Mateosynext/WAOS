from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TenantModeUpdateRequest(BaseModel):
    organization_id: str
    tenant_mode: Literal["sandbox", "go_live"]


class InboxSavedViewCreateRequest(BaseModel):
    organization_id: str
    name: str = Field(min_length=1, max_length=80)
    filters: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class GuidedOnboardingWizardStartRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    vertical_id: str | None = None
    subvertical: str | None = None
    business_name: str | None = None
    bot_name: str | None = None
    tone: str | None = None
    language: str | None = None
    timezone: str | None = None
    primary_objective: str | None = None
    hours: str | None = None
    whatsapp_number: str | None = None
    answers: dict[str, Any] = Field(default_factory=dict)


class GuidedOnboardingWizardStepUpdateRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = None
