from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.voice_channel_service import voice_channel_service
from ...schemas import (
    VoiceChannelHandoffEnvelope,
    VoiceChannelSessionEnvelope,
    VoiceChannelSessionListEnvelope,
    VoiceChannelTurnEnvelope,
    VoiceChannelHandoffRequest,
    VoiceChannelInterruptRequest,
    VoiceChannelSessionStartRequest,
    VoiceChannelTurnRequest,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=['voice_channel'])


@router.post('/api/v1/voice-channel/sessions/start', response_model=VoiceChannelSessionEnvelope)
def start_voice_channel_session(payload: VoiceChannelSessionStartRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return voice_channel_service.start_session(uow, payload=payload, user=user)


@router.get('/api/v1/voice-channel/sessions', response_model=VoiceChannelSessionListEnvelope)
def list_voice_channel_sessions(
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    contact_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return voice_channel_service.list_sessions(uow, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id, limit=limit, user=user)


@router.get('/api/v1/voice-channel/sessions/{session_id}', response_model=VoiceChannelSessionEnvelope)
def get_voice_channel_session(session_id: str, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return voice_channel_service.get_session(uow, session_id=session_id, user=user)


@router.post('/api/v1/voice-channel/sessions/{session_id}/turns', response_model=VoiceChannelTurnEnvelope)
def ingest_voice_channel_turn(session_id: str, payload: VoiceChannelTurnRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return voice_channel_service.ingest_turn(uow, session_id=session_id, payload=payload, user=user)


@router.post('/api/v1/voice-channel/sessions/{session_id}/interrupt', response_model=VoiceChannelTurnEnvelope)
def interrupt_voice_channel_session(session_id: str, payload: VoiceChannelInterruptRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return voice_channel_service.interrupt(uow, session_id=session_id, payload=payload, user=user)


@router.post('/api/v1/voice-channel/sessions/{session_id}/handoff', response_model=VoiceChannelHandoffEnvelope)
def handoff_voice_channel_session(session_id: str, payload: VoiceChannelHandoffRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return voice_channel_service.handoff(uow, session_id=session_id, payload=payload, user=user)
