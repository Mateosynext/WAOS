from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class ConversationMessageRequest(BaseModel):
    body: str
    kind: Literal["text", "note"] = "text"


class TakeoverRequest(BaseModel):
    freeze_minutes: int = 30


class LeadMemoryUpdateRequest(BaseModel):
    lead_stage: str | None = None
    lead_score: int | None = None
    interest: str | None = None
    objections: str | None = None
    summary: str | None = None
    next_action: str | None = None
    followup_at: str | None = None


class SimulateInboundRequest(BaseModel):
    bot_id: str
    phone: str
    name: str | None = None
    body: str


class ConversationReviewRequest(BaseModel):
    organization_id: str
    bot_id: str
    agent_user_id: str | None = None
    review_type: Literal["commercial_quality", "compliance", "coaching"] = "commercial_quality"


class VoiceNoteRequest(BaseModel):
    organization_id: str
    bot_id: str
    conversation_id: str
    contact_id: str
    transcript: str
    language: str = "es"


class FeedbackRequest(BaseModel):
    organization_id: str
    bot_id: str
    conversation_id: str | None = None
    contact_id: str | None = None
    score_type: Literal["csat", "nps"] = "csat"
    score_value: int = 5
    reason: str = ""
    agent_user_id: str | None = None


class ConversationCopilotRequest(BaseModel):
    draft: str = ""
    objective: Literal["reply", "followup", "save_deal", "book"] = "reply"


class ConversationTagRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)
