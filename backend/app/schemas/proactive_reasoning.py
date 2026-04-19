from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProactiveEvaluateRequest(BaseModel):
    organization_id: str
    bot_id: str
    contact_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)
    as_of: str | None = None
    persist: bool = True
    include_suppressed: bool = False
    limit: int = Field(default=100, ge=1, le=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProactiveMaterializeRequest(BaseModel):
    organization_id: str
    schedule_for: str | None = None
    record_exposure: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
