from __future__ import annotations

from pydantic import BaseModel, Field


class OptimizerRunRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    targets: list[str] = Field(default_factory=list)
    scorecard_window: str = Field(default="28d")
    mode: str = Field(default="auto")
    auto_shadow: bool = Field(default=True)
    auto_ab: bool = Field(default=True)
    auto_promote: bool = Field(default=False)
    auto_degrade: bool = Field(default=True)
    min_confidence: float = Field(default=70, ge=0, le=100)
    min_delta: float = Field(default=1.5, ge=0)


class OptimizerEvaluateRequest(BaseModel):
    organization_id: str
    scorecard_window: str = Field(default="28d")
    min_confidence: float = Field(default=70, ge=0, le=100)
    min_shadow_runs: int = Field(default=10, ge=1, le=10000)
    auto_apply: bool = Field(default=False)
