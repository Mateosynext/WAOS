from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRouteRequest(BaseModel):
    organization_id: str
    bot_id: str
    text: str
    conversation_id: str | None = None
    contact_id: str | None = None
    message_id: str | None = None
    memory: dict[str, Any] = Field(default_factory=dict)
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    bot_config: dict[str, Any] = Field(default_factory=dict)
    classification: dict[str, Any] | None = None
    persist: bool = True
    record_exposure: bool = False

