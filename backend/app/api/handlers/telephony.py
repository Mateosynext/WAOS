from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import Response

from ...db import get_connection
from ...errors import ForbiddenError, NotFoundError
from ...repositories import get_bot
from ...telephony_twilio import (
    TwiMLResponseBuilder,
    build_external_url,
    close_twilio_voice_session,
    find_or_create_twilio_voice_session,
    resolve_twilio_auth_token,
    verify_twilio_signature,
)
from ...voice_channel_runtime import get_voice_channel_session, ingest_voice_channel_turn


async def _validated_form(request: Request, *, bot_id: str | None = None, session_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    form = dict(await request.form())
    with get_connection() as conn:
        session = get_voice_channel_session(conn, session_id=session_id) if session_id else None
        bot = get_bot(conn, bot_id) if bot_id else (get_bot(conn, session["bot_id"]) if session else None)
        if not bot:
            raise NotFoundError("Bot not found")
        auth_token = resolve_twilio_auth_token(conn, organization_id=bot["organization_id"], bot_id=bot["id"])
        signature = request.headers.get("x-twilio-signature")
        if auth_token:
            url = build_external_url(request)
            if not verify_twilio_signature(auth_token=auth_token, signature=signature, url=url, params=form):
                raise ForbiddenError("Invalid Twilio signature", code="twilio_signature_invalid")
        return form, bot


async def twilio_voice_inbound(request: Request, bot_id: str) -> Response:
    form, bot = await _validated_form(request, bot_id=bot_id)
    from_phone = str(form.get("From") or form.get("Caller") or "unknown").strip() or "unknown"
    to_phone = str(form.get("To") or "").strip() or None
    call_sid = str(form.get("CallSid") or "").strip()
    caller_name = str(form.get("CallerName") or form.get("FromCity") or "").strip() or None
    if not call_sid:
        raise HTTPException(status_code=400, detail="Missing CallSid")

    with get_connection() as conn:
        session = find_or_create_twilio_voice_session(
            conn,
            bot_id=bot_id,
            from_phone=from_phone,
            to_phone=to_phone,
            call_sid=call_sid,
            caller_name=caller_name,
        )
        conn.commit()

    business_name = ((bot.get("config") or {}).get("identity") or {}).get("business_name") or bot.get("name") or "el negocio"
    turn_url = build_external_url(request, extra_query={"session_id": session["id"]}).replace("/voice", "/voice/turn", 1)
    fallback_url = build_external_url(request, extra_query={"session_id": session["id"]}).replace("/voice", "/voice/turn", 1)

    xml = TwiMLResponseBuilder()
    xml.gather_open(action=turn_url)
    xml.say(f"Hola, habla el asistente de {business_name}. Te escucho. Cuéntame en qué te ayudo hoy.")
    xml.gather_close()
    xml.redirect(fallback_url)
    return Response(content=xml.build(), media_type="application/xml")


async def twilio_voice_turn(request: Request, session_id: str) -> Response:
    form, _bot = await _validated_form(request, session_id=session_id)
    transcript = str(form.get("SpeechResult") or form.get("Digits") or "").strip()
    call_status = str(form.get("CallStatus") or "").strip().lower()

    with get_connection() as conn:
        session = get_voice_channel_session(conn, session_id=session_id)
        if not session:
            raise NotFoundError("Voice session not found")
        if call_status in {"completed", "busy", "failed", "no-answer", "canceled"}:
            close_twilio_voice_session(conn, session_id=session_id, call_status=call_status, metadata={"twilio": form})
            conn.commit()
            xml = TwiMLResponseBuilder()
            xml.hangup()
            return Response(content=xml.build(), media_type="application/xml")

        if not transcript:
            retry_url = build_external_url(request)
            xml = TwiMLResponseBuilder()
            xml.gather_open(action=retry_url)
            xml.say("No alcancé a escucharte bien. Dímelo otra vez, por favor.")
            xml.gather_close()
            xml.redirect(retry_url)
            return Response(content=xml.build(), media_type="application/xml")

        result = ingest_voice_channel_turn(
            conn,
            session_id=session_id,
            actor="contact",
            transcript_text=transcript,
            requested_reply_mode="voice",
            metadata={"provider": "twilio", "form": form},
        )
        conn.commit()

    assistant_turn = result.get("assistant_turn") or {}
    response_payload = assistant_turn.get("response") or {}
    render = response_payload.get("render") or {}
    response_text = str((response_payload.get("text") or assistant_turn.get("transcript_text") or "Te ayudo con eso.")).strip()
    next_url = build_external_url(request)

    xml = TwiMLResponseBuilder()
    xml.gather_open(action=next_url)
    asset = render.get("asset") or {}
    audio_url = str(asset.get("audio_url") or "").strip()
    if render.get("status") == "ready" and audio_url:
        xml.play(audio_url)
    else:
        xml.say(response_text)
    xml.gather_close()
    xml.redirect(next_url)
    return Response(content=xml.build(), media_type="application/xml")


async def twilio_voice_status(request: Request, session_id: str) -> dict[str, Any]:
    form, _bot = await _validated_form(request, session_id=session_id)
    with get_connection() as conn:
        session = close_twilio_voice_session(
            conn,
            session_id=session_id,
            call_status=str(form.get("CallStatus") or "").strip() or None,
            metadata={"twilio_status": form},
        )
        conn.commit()
    return {"ok": True, "session": session}
