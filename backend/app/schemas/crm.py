from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class CRMLeadUpsertRequest(BaseModel):
    organization_id: str
    bot_id: str
    contact_id: str
    conversation_id: str | None = None
    stage: str = "nuevo"
    estimated_amount: float = 0
    owner_user_id: str | None = None
    next_action: str = "Calificar lead"
    followup_at: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    lost_reason: str | None = None
    language: str = "es"
    source_channel: Literal["whatsapp", "instagram_dm", "webchat"] = "whatsapp"
    source_campaign: str = "orgánico"
