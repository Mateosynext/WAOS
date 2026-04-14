from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class ExecutiveReportRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    period_start: str
    period_end: str
    delivery_channels: list[Literal["email", "whatsapp", "pdf"]] = Field(default_factory=lambda: ["email", "whatsapp", "pdf"])


class AlertRuleRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    name: str
    metric_key: Literal["handoff_rate", "unanswered_risk", "bookings_drop", "close_probability_drop"] = "handoff_rate"
    comparator: Literal[">", ">=", "<", "<="] = ">="
    threshold_value: float
    window_minutes: int = 60
    notify_channels: list[str] = Field(default_factory=lambda: ["email"])
    status: Literal["active", "paused"] = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class ReportScheduleRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    name: str
    frequency: Literal["daily", "weekly", "monthly"] = "weekly"
    next_run_at: str
    delivery_channels: list[str] = Field(default_factory=lambda: ["email", "pdf"])
    status: Literal["active", "paused"] = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class FollowupExperimentRequest(BaseModel):
    organization_id: str
    bot_id: str
    name: str
    vertical: str = "general"
    channel: str = "whatsapp"
    variant_a_text: str
    variant_b_text: str
    goal_metric: Literal["reply_rate", "booking_rate", "close_rate"] = "reply_rate"
    status: Literal["draft", "active", "paused", "completed"] = "draft"


class FollowupExperimentSendRequest(BaseModel):
    conversation_id: str
    preferred_variant: Literal["A", "B"] | None = None
    operator_user_id: str | None = None
    note: str = ""
