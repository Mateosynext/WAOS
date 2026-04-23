from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GrowthOsRunRequest(BaseModel):
    organization_id: str
    bot_id: str
    goals: list[str] = Field(default_factory=list)
    mode: Literal["recommend", "autopilot", "execute"] = "recommend"
    limit: int = Field(default=100, ge=1, le=500)
    max_targets: int = Field(default=10, ge=1, le=100)
    auto_execute: bool = False
    include_suppressed: bool = False
    scorecard_window: str = Field(default="28d")
    metadata: dict[str, Any] = Field(default_factory=dict)


from .response_models import ApiEnvelope, FlexibleSchema


class GrowthOsTargetResponse(FlexibleSchema):
    target_id: str | None = None
    kind: str | None = None
    name: str | None = None
    status: str | None = None
    score: float | int | None = None


class GrowthOsOverviewData(FlexibleSchema):
    organization_id: str | None = None
    bot_id: str | None = None
    scorecard_window: str | None = None
    summary: FlexibleSchema | dict[str, Any] | None = None
    recommendations: list[FlexibleSchema] = Field(default_factory=list)
    targets: list[GrowthOsTargetResponse] = Field(default_factory=list)


class GrowthOsRunResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    mode: str | None = None
    status: str | None = None
    goals_json: str | None = None
    summary_json: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class GrowthOsRunListData(FlexibleSchema):
    items: list[GrowthOsRunResponse] = Field(default_factory=list)
    count: int = 0


GrowthOsOverviewEnvelope = ApiEnvelope[GrowthOsOverviewData]
GrowthOsRunEnvelope = ApiEnvelope[FlexibleSchema]
GrowthOsRunListEnvelope = ApiEnvelope[GrowthOsRunListData]
