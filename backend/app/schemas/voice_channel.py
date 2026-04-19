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
