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
