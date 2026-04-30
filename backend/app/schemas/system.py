from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

class DeadLetterRequeueRequest(BaseModel):
    scheduled_for: str | None = None


class SettingsUpdateRequest(BaseModel):
    global_policy: str | None = None
    default_model: str | None = None
    freeze_minutes_after_takeover: int | None = None
    ai_optimization: dict[str, Any] | None = None
    memory_runtime: dict[str, Any] | None = None


class FrontendTelemetryEvent(BaseModel):
    """Public frontend telemetry payload with closed schema and strict field limits."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: Literal["frontend", "frontend-error", "frontend-analytics"] = "frontend"
    kind: Literal[
        "page_view",
        "ui_click",
        "form_error",
        "frontend_error",
        "unhandled_error",
        "render_error",
        "api_error",
        "route_error",
        "hydration_error",
    ] = "frontend_error"
    message: str | None = Field(default=None, max_length=500)
    error: str | None = Field(default=None, max_length=500)
    stack: str | None = Field(default=None, max_length=2000)
    path: str | None = Field(default=None, max_length=300)
    digest: str | None = Field(default=None, max_length=128)
    label: str | None = Field(default=None, max_length=120)
    component: str | None = Field(default=None, max_length=120)
    ts: str | None = Field(default=None, max_length=64)

    @model_validator(mode="before")
    @classmethod
    def enforce_public_telemetry_field_budget(cls, data: Any) -> Any:
        if isinstance(data, dict) and len(data) > 10:
            raise ValueError("frontend_telemetry_too_many_fields")
        return data
