from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class VoiceChannelSessionStartRequest(BaseModel):
    organization_id: str
    bot_id: str
    contact_id: str | None = None
    conversation_id: str | None = None
    channel: str = 'voice'
    requested_modality: Literal['voice', 'text', 'hybrid'] = 'voice'
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceChannelTurnRequest(BaseModel):
    actor: Literal['contact', 'assistant', 'system'] = 'contact'
    transcript_text: str | None = None
    provider_transcript: str | None = None
    audio_url: str | None = None
    requested_reply_mode: Literal['voice', 'text', 'hybrid'] = 'voice'
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceChannelInterruptRequest(BaseModel):
    reason: str = 'customer_barge_in'


class VoiceChannelHandoffRequest(BaseModel):
    to_channel: Literal['text', 'voice', 'human_text', 'human_voice'] = 'text'
    reason: str
    summary_text: str | None = None
    target_queue: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


from .response_models import ApiEnvelope, FlexibleSchema


class VoiceChannelSessionResponse(FlexibleSchema):
    id: str | None = None
    organization_id: str | None = None
    bot_id: str | None = None
    contact_id: str | None = None
    conversation_id: str | None = None
    channel: str | None = None
    requested_modality: str | None = None
    status: str | None = None
    last_turn_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    metadata_json: str | None = None


class VoiceChannelSessionListData(FlexibleSchema):
    items: list[VoiceChannelSessionResponse] = Field(default_factory=list)
    count: int = 0


class VoiceChannelTurnResult(FlexibleSchema):
    session_id: str | None = None
    turn_id: str | None = None
    actor: str | None = None
    status: str | None = None
    reply_mode: str | None = None
    message_id: str | None = None
    created_at: str | None = None


class VoiceChannelHandoffResult(FlexibleSchema):
    handoff: FlexibleSchema | dict[str, Any] | None = None
    session: VoiceChannelSessionResponse | FlexibleSchema | dict[str, Any] | None = None


VoiceChannelSessionEnvelope = ApiEnvelope[VoiceChannelSessionResponse]
VoiceChannelSessionListEnvelope = ApiEnvelope[VoiceChannelSessionListData]
VoiceChannelTurnEnvelope = ApiEnvelope[VoiceChannelTurnResult]
VoiceChannelHandoffEnvelope = ApiEnvelope[VoiceChannelHandoffResult]
