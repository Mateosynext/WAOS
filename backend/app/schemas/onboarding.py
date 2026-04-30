from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from ..config import settings


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "si", "sí"}
    return False


def _clean_id_like(value: Any, field_name: str) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, bool):
        return value if field_name == "organization_id" else None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Mapping):
        for key in ("id", "bot_id", "organization_id", "value"):
            candidate = value.get(key)
            nested = _clean_id_like(candidate, field_name)
            if nested:
                return nested
        return value if field_name == "organization_id" else None
    return value


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

    @field_validator("organization_id", "bot_id", "vertical_id", "subvertical", "primary_objective", mode="before")
    @classmethod
    def _normalize_id_fields(cls, value: Any, info: ValidationInfo) -> Any:
        return _clean_id_like(value, info.field_name)


class GuidedOnboardingWizardStepUpdateRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = None


class GuidedOnboardingWizardApplyRequest(BaseModel):
    confirm: bool = False

    @field_validator("confirm", mode="before")
    @classmethod
    def _normalize_confirm(cls, value: Any) -> bool:
        return _truthy(value)


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

    @field_validator("organization_id", "bot_id", "vertical_id", "subvertical", "primary_objective", mode="before")
    @classmethod
    def _normalize_id_fields(cls, value: Any, info: ValidationInfo) -> Any:
        return _clean_id_like(value, info.field_name)


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
    user_description: str = Field(min_length=20, max_length=4000)
    intensity: Literal["balanced", "aggressive", "conservative", "savage"] = "aggressive"
    existing_answers: dict[str, Any] = Field(default_factory=dict)
    max_autofix_rounds: int = Field(default_factory=lambda: settings.autopilot_max_autofix_rounds, ge=1, le=2)
    auto_apply: bool = False

    @model_validator(mode="before")
    @classmethod
    def _normalize_safe_flags(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        normalized = dict(data)
        # Legacy wizard Autopilot must stay human-gated. Normalize stale clients
        # instead of letting string/object booleans accidentally trigger apply.
        normalized["auto_apply"] = False
        return normalized

    @field_validator("organization_id", "bot_id", "vertical_id", "subvertical", "primary_objective", mode="before")
    @classmethod
    def _normalize_id_fields(cls, value: Any, info: ValidationInfo) -> Any:
        return _clean_id_like(value, info.field_name)
