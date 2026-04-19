from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentPolicyEvaluationRequest(BaseModel):
    organization_id: str
    bot_id: str
    specialist_agent_key: str
    conversation_id: str | None = None
    contact_id: str | None = None
    requested_action: str | None = None
    classification: dict[str, Any] = Field(default_factory=dict)
    route: dict[str, Any] = Field(default_factory=dict)
    conversation: dict[str, Any] = Field(default_factory=dict)
    shared_memory: dict[str, Any] = Field(default_factory=dict)
    persist: bool = True
