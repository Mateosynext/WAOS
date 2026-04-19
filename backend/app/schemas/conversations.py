from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator
from typing_extensions import Annotated


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
BodyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
PhoneText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=7, max_length=32)]
OrgIdText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
BotIdText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ContactIdText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ConversationMessageRequest(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=4000)
    kind: Literal["text", "note"] = "text"
    whatsapp_payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "ConversationMessageRequest":
        if self.kind == "note" and not (self.body or "").strip():
            raise ValueError("note_body_required")
        if self.kind == "text" and not (self.body or "").strip() and not self.whatsapp_payload:
            raise ValueError("text_body_or_whatsapp_payload_required")
        return self


class TakeoverRequest(BaseModel):
    freeze_minutes: int = Field(default=30, ge=1, le=1440)


class LeadMemoryUpdateRequest(BaseModel):
    lead_stage: ShortText | None = None
    lead_score: int | None = Field(default=None, ge=0, le=100)
    interest: ShortText | None = None
    objections: str | None = Field(default=None, max_length=2000)
    summary: str | None = Field(default=None, max_length=4000)
    next_action: ShortText | None = None
    followup_at: str | None = None


class SimulateInboundRequest(BaseModel):
    bot_id: BotIdText
    phone: PhoneText
    name: ShortText | None = None
    body: BodyText


class ConversationReviewRequest(BaseModel):
    organization_id: OrgIdText
    bot_id: BotIdText
    agent_user_id: str | None = None
    review_type: Literal["commercial_quality", "compliance", "coaching"] = "commercial_quality"


class VoiceNoteRequest(BaseModel):
    organization_id: OrgIdText
    bot_id: BotIdText
    conversation_id: str
    contact_id: ContactIdText
    transcript: str = Field(min_length=1, max_length=8000)
    language: str = Field(default="es", min_length=2, max_length=16)


class FeedbackRequest(BaseModel):
    organization_id: OrgIdText
    bot_id: BotIdText
    conversation_id: str | None = None
    contact_id: ContactIdText | None = None
    score_type: Literal["csat", "nps"] = "csat"
    score_value: int = Field(default=5, ge=0, le=10)
    reason: str = Field(default="", max_length=2000)
    agent_user_id: str | None = None


class ConversationCopilotRequest(BaseModel):
    draft: str = Field(default="", max_length=4000)
    objective: Literal["reply", "followup", "save_deal", "book"] = "reply"


class ConversationTagRequest(BaseModel):
    tags: list[ShortText] = Field(default_factory=list, max_length=20)



class ConversationAssignRequest(BaseModel):
    assigned_user_id: str | None = None
    mode: Literal["manual", "auto"] = "manual"
    note: str = Field(default="", max_length=1000)


class InboxAutoAssignRequest(BaseModel):
    organization_id: OrgIdText
    limit: int = Field(default=25, ge=1, le=200)
    queue_role: ShortText | None = None


class StructuredInternalNoteRequest(BaseModel):
    category: Literal["general", "billing", "compliance", "quality", "followup", "takeover", "supervisor", "risk"] = "general"
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    visibility: Literal["internal", "supervisor"] = "internal"
    summary: str = Field(min_length=1, max_length=500)
    detail: str = Field(default="", max_length=4000)
    next_steps: list[ShortText] = Field(default_factory=list, max_length=10)
    sources: list[ShortText] = Field(default_factory=list, max_length=10)
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    risk_flags: list[ShortText] = Field(default_factory=list, max_length=10)

