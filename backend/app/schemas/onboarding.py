from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings


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


class GuidedOnboardingAiPrefillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    organization_id: str = Field(min_length=1, max_length=120)
    bot_id: str | None = Field(default=None, max_length=120)
    vertical_id: str | None = Field(default=None, max_length=120)
    subvertical: str | None = Field(default=None, max_length=120)
    primary_objective: str | None = Field(default=None, max_length=120)
    user_description: str = Field(default="", max_length=4000)
    intensity: Literal["balanced", "aggressive", "conservative", "savage"] = "balanced"
    existing_answers: dict[str, Any] = Field(default_factory=dict)


class GuidedOnboardingAiAutofixRequest(BaseModel):
    user_description: str = Field(default="", max_length=4000)
    max_rounds: int = Field(default=3, ge=1, le=5)


class GuidedOnboardingAiAutopilotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    organization_id: str = Field(min_length=1, max_length=120)
    bot_id: str | None = Field(default=None, max_length=120)
    vertical_id: str | None = Field(default=None, max_length=120)
    subvertical: str | None = Field(default=None, max_length=120)
    primary_objective: str | None = Field(default=None, max_length=120)
    user_description: str = Field(default="", max_length=4000)
    intensity: Literal["balanced", "aggressive", "conservative", "savage"] = "aggressive"
    existing_answers: dict[str, Any] = Field(default_factory=dict)
    max_autofix_rounds: int = Field(default_factory=lambda: settings.autopilot_max_autofix_rounds, ge=1, le=2)
    auto_apply: bool = False
