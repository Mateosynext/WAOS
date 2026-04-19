from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..repositories import get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..voice_channel_runtime import (
    create_voice_channel_handoff,
    get_voice_channel_session,
    ingest_voice_channel_turn,
    interrupt_voice_channel_session,
    list_voice_channel_sessions,
    start_voice_channel_session,
)
from .support import require_permission
from .uow import UnitOfWork


class VoiceChannelService:
    def start_session(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, 'conversation.manage')
        bot = get_bot(uow.conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail='Bot not found')
        if bot['organization_id'] != payload.organization_id:
            raise HTTPException(status_code=403, detail='Bot does not belong to organization')
        ensure_bot_access(user, bot)
        result = start_voice_channel_session(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            contact_id=payload.contact_id,
            conversation_id=payload.conversation_id,
            channel=payload.channel,
            requested_modality=payload.requested_modality,
            metadata=payload.metadata,
        )
        uow.commit()
        return ok(result)

    def ingest_turn(self, uow: UnitOfWork, *, session_id: str, payload, user: dict) -> dict[str, Any]:
        session = get_voice_channel_session(uow.conn, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail='Voice session not found')
        ensure_org_access(user, session['organization_id'])
        require_permission(user, session['organization_id'], 'conversation.manage')
        bot = get_bot(uow.conn, session['bot_id'])
        if bot:
            ensure_bot_access(user, bot)
        result = ingest_voice_channel_turn(
            uow.conn,
            session_id=session_id,
            actor=payload.actor,
            transcript_text=payload.transcript_text,
            provider_transcript=payload.provider_transcript,
            audio_url=payload.audio_url,
            requested_reply_mode=payload.requested_reply_mode,
            metadata=payload.metadata,
        )
        uow.commit()
        return ok(result)

    def interrupt(self, uow: UnitOfWork, *, session_id: str, payload, user: dict) -> dict[str, Any]:
        session = get_voice_channel_session(uow.conn, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail='Voice session not found')
        ensure_org_access(user, session['organization_id'])
        require_permission(user, session['organization_id'], 'conversation.manage')
        result = interrupt_voice_channel_session(uow.conn, session_id=session_id, reason=payload.reason)
        uow.commit()
        return ok(result)

    def handoff(self, uow: UnitOfWork, *, session_id: str, payload, user: dict) -> dict[str, Any]:
        session = get_voice_channel_session(uow.conn, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail='Voice session not found')
        ensure_org_access(user, session['organization_id'])
        require_permission(user, session['organization_id'], 'conversation.manage')
        result = create_voice_channel_handoff(
            uow.conn,
            session_id=session_id,
            to_channel=payload.to_channel,
            reason=payload.reason,
            summary_text=payload.summary_text,
            target_queue=payload.target_queue,
            metadata=payload.metadata,
        )
        uow.commit()
        return ok({'handoff': result, 'session': get_voice_channel_session(uow.conn, session_id=session_id)})

    def get_session(self, uow: UnitOfWork, *, session_id: str, user: dict) -> dict[str, Any]:
        session = get_voice_channel_session(uow.conn, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail='Voice session not found')
        ensure_org_access(user, session['organization_id'])
        require_permission(user, session['organization_id'], 'operations.read')
        return ok(session)

    def list_sessions(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, contact_id: str | None, limit: int, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, 'operations.read')
        items = list_voice_channel_sessions(uow.conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id, limit=limit)
        return ok({'items': items, 'count': len(items)})


voice_channel_service = VoiceChannelService()
