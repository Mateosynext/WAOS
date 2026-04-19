from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .db import execute, fetch_one, table_exists
from .domains.customer_experience import ingest_voice_note
from .utils import add_minutes, from_json, new_id, to_json, utcnow_iso
from .whatsapp import resolve_whatsapp_access_token

PLACEHOLDER_TRANSCRIPTS = {
    "nota de voz recibida por whatsapp.",
    "nota de voz recibida.",
    "voice note received via whatsapp.",
}


class VoicePipelineService:
    def _log_event(
        self,
        conn,
        *,
        organization_id: str,
        bot_id: str,
        conversation_id: str,
        contact_id: str | None,
        message_id: str | None,
        voice_note_id: str | None,
        stage: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        if not table_exists(conn, "voice_processing_events"):
            return
        execute(
            conn,
            "INSERT INTO voice_processing_events (id, organization_id, bot_id, conversation_id, contact_id, message_id, voice_note_id, stage, status, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id("vproc"),
                organization_id,
                bot_id,
                conversation_id,
                contact_id,
                message_id,
                voice_note_id,
                stage,
                status,
                to_json(details or {}),
                utcnow_iso(),
            ),
        )

    def _voice_settings(self) -> dict[str, Any]:
        return {
            "storage_dir": Path(settings.voice_media_storage_dir),
            "ttl_minutes": settings.voice_media_ttl_minutes,
            "stt_webhook": settings.voice_transcription_webhook_url.strip(),
            "stt_timeout": settings.voice_transcription_timeout_seconds,
            "tts_webhook": settings.voice_tts_webhook_url.strip(),
            "tts_timeout": settings.voice_tts_timeout_seconds,
            "min_audio_confidence": settings.voice_min_audio_reply_confidence,
        }


    def build_voice_runtime_context(
        self,
        conn,
        *,
        organization_id: str,
        bot_id: str,
        language: str = "es",
        base_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = dict(base_context or {})
        bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (bot_id,)) or {}
        bot_config = from_json(bot.get("config_draft_json"), {})
        templates = {}
        language_row = fetch_one(conn, "SELECT templates_json FROM bot_language_configs WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id))
        if language_row:
            templates = from_json(language_row.get("templates_json"), {})
        language_template = dict((templates.get(language) or {})) if isinstance(templates, dict) else {}
        voice_profile = dict(language_template.get("voice_profile") or {})
        voice_block = dict(bot_config.get("voice") or bot_config.get("voice_runtime") or {})
        identity_block = dict(bot_config.get("voice_identity") or voice_block.get("identity") or {})
        tts_block = dict(bot_config.get("tts") or voice_block.get("tts") or {})
        owner_name = (
            identity_block.get("owner_name")
            or ((bot_config.get("identity") or {}).get("owner_name"))
            or bot.get("business_name")
            or bot.get("name")
        )
        existing_identity = dict(context.get("voice_identity") or {})
        existing_prefs = dict(context.get("tts_preferences") or {})
        context["voice_profile"] = {**voice_profile, **dict(context.get("voice_profile") or {})}
        context["voice_identity"] = {
            **identity_block,
            **existing_identity,
            "owner_name": existing_identity.get("owner_name") or owner_name,
            "voice_clone_id": existing_identity.get("voice_clone_id") or identity_block.get("voice_clone_id") or tts_block.get("voice_clone_id") or tts_block.get("voice_id"),
            "provider": existing_identity.get("provider") or identity_block.get("provider") or tts_block.get("provider"),
            "consent_status": existing_identity.get("consent_status") or identity_block.get("consent_status") or "required_before_clone",
        }
        context["tts_preferences"] = {**tts_block, **existing_prefs}
        return context

    def _store_binary(self, *, organization_id: str, bot_id: str, conversation_id: str, message_id: str, media_id: str | None, mime_type: str | None, content: bytes) -> dict[str, Any]:
        settings_map = self._voice_settings()
        base_dir = settings_map["storage_dir"] / organization_id / bot_id / conversation_id
        base_dir.mkdir(parents=True, exist_ok=True)
        extension = {
            "audio/ogg": ".ogg",
            "audio/opus": ".opus",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/wav": ".wav",
        }.get((mime_type or "").lower(), ".bin")
        filename = f"{message_id}-{media_id or 'voice'}{extension}"
        path = base_dir / filename
        path.write_bytes(content)
        return {
            "storage_path": str(path),
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    def _persist_media_asset(
        self,
        conn,
        *,
        organization_id: str,
        bot_id: str,
        conversation_id: str,
        contact_id: str | None,
        message_id: str | None,
        voice_note_id: str | None,
        direction: str,
        media_role: str,
        provider_media_id: str | None,
        storage_path: str | None,
        public_url: str | None,
        mime_type: str | None,
        sha256: str | None,
        size_bytes: int | None,
        expires_at: str | None,
        consent_status: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not table_exists(conn, "voice_media_assets"):
            return
        execute(
            conn,
            "INSERT INTO voice_media_assets (id, organization_id, bot_id, conversation_id, contact_id, message_id, voice_note_id, direction, provider, media_role, provider_media_id, storage_path, public_url, mime_type, sha256, size_bytes, expires_at, consent_status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id("vmedia"),
                organization_id,
                bot_id,
                conversation_id,
                contact_id,
                message_id,
                voice_note_id,
                direction,
                "meta_cloud_api" if direction == "inbound" else "waos_voice_runtime",
                media_role,
                provider_media_id,
                storage_path,
                public_url,
                mime_type,
                sha256,
                int(size_bytes or 0),
                expires_at,
                consent_status or "implicit_inbound_whatsapp",
                to_json(metadata or {}),
                utcnow_iso(),
            ),
        )

    def _retrieve_whatsapp_media(
        self,
        conn,
        *,
        organization_id: str,
        bot_id: str,
        conversation_id: str,
        message_id: str,
        audio_payload: dict[str, Any],
    ) -> dict[str, Any]:
        media_id = str(audio_payload.get("id") or "").strip()
        mime_type = str(audio_payload.get("mime_type") or "audio/ogg").strip() or "audio/ogg"
        if not media_id:
            return {
                "media_id": None,
                "mime_type": mime_type,
                "retrieval_status": "missing_media_id",
            }
        token = resolve_whatsapp_access_token(conn, organization_id=organization_id, bot_id=bot_id)
        if not token:
            return {
                "media_id": media_id,
                "mime_type": mime_type,
                "retrieval_status": "missing_access_token",
            }
        headers = {"Authorization": f"Bearer {token}"}
        metadata_response = httpx.get(f"{settings.meta_graph_api_base}/{media_id}", headers=headers, timeout=12.0)
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        media_url = str(metadata.get("url") or "").strip() or None
        resolved_mime = str(metadata.get("mime_type") or mime_type).strip() or mime_type
        if not media_url:
            return {
                "media_id": media_id,
                "mime_type": resolved_mime,
                "retrieval_status": "missing_media_url",
                "provider_metadata": metadata,
            }
        binary_response = httpx.get(media_url, headers=headers, timeout=25.0)
        binary_response.raise_for_status()
        stored = self._store_binary(
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            message_id=message_id,
            media_id=media_id,
            mime_type=resolved_mime,
            content=binary_response.content,
        )
        return {
            "media_id": media_id,
            "media_url": media_url,
            "mime_type": resolved_mime,
            "retrieval_status": "downloaded",
            "storage_path": stored["storage_path"],
            "size_bytes": stored["size_bytes"],
            "sha256": stored["sha256"],
            "provider_metadata": metadata,
        }

    def _transcribe(
        self,
        *,
        storage_path: str | None,
        media_url: str | None,
        mime_type: str | None,
        provider_transcript: str | None,
        organization_id: str,
        bot_id: str,
        conversation_id: str,
        contact_id: str | None,
        message_id: str,
    ) -> dict[str, Any]:
        clean_provider = str(provider_transcript or "").strip()
        if clean_provider and clean_provider.lower() not in PLACEHOLDER_TRANSCRIPTS:
            return {
                "transcript": clean_provider,
                "language": "es",
                "confidence": 0.98,
                "source": "provider_transcript",
                "segments": [{"speaker": "customer", "text": clean_provider, "confidence": 0.98}],
                "diarization": [{"speaker": "customer", "start": 0.0, "end": None}],
                "processing_status": "completed",
            }
        webhook = self._voice_settings()["stt_webhook"]
        if webhook and storage_path and os.path.exists(storage_path):
            with open(storage_path, "rb") as fh:
                response = httpx.post(
                    webhook,
                    data={
                        "organization_id": organization_id,
                        "bot_id": bot_id,
                        "conversation_id": conversation_id,
                        "contact_id": contact_id or "",
                        "message_id": message_id,
                        "media_url": media_url or "",
                        "mime_type": mime_type or "audio/ogg",
                    },
                    files={"file": (Path(storage_path).name, fh, mime_type or "application/octet-stream")},
                    timeout=self._voice_settings()["stt_timeout"],
                )
            response.raise_for_status()
            payload = response.json()
            transcript = str(payload.get("transcript") or "").strip()
            return {
                "transcript": transcript,
                "language": str(payload.get("language") or "es").strip() or "es",
                "confidence": float(payload.get("confidence") or 0),
                "source": str(payload.get("source") or "transcription_webhook"),
                "segments": payload.get("segments") or ([{"speaker": "customer", "text": transcript}] if transcript else []),
                "diarization": payload.get("diarization") or [],
                "processing_status": "completed" if transcript else "transcription_empty",
            }
        return {
            "transcript": "",
            "language": "es",
            "confidence": 0.0,
            "source": "unavailable",
            "segments": [],
            "diarization": [],
            "processing_status": "transcription_pending",
        }

    def _noise_from_confidence(self, confidence: float) -> str:
        if confidence >= 0.9:
            return "low"
        if confidence >= 0.65:
            return "medium"
        return "high"

    def _audio_quality(self, confidence: float, retrieval_status: str) -> str:
        if retrieval_status != "downloaded" and confidence < 0.7:
            return "limited"
        if confidence >= 0.9:
            return "high"
        if confidence >= 0.65:
            return "medium"
        return "poor"

    def process_inbound_voice_message(
        self,
        conn,
        *,
        organization_id: str,
        bot_id: str,
        conversation_id: str,
        contact_id: str | None,
        inbound_message: dict[str, Any],
        metadata: dict[str, Any] | None,
        preferred_transcript: str | None,
    ) -> dict[str, Any]:
        metadata = dict(metadata or {})
        whatsapp_payload = dict(metadata.get("whatsapp") or {})
        audio_payload = dict(whatsapp_payload.get("audio") or {})
        is_voice_note = bool(metadata.get("is_voice_note") or audio_payload.get("voice") or inbound_message.get("kind") == "audio")
        if not is_voice_note and inbound_message.get("kind") != "audio":
            return {"processed": False, "reason": "not_voice"}

        self._log_event(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            message_id=inbound_message.get("id"),
            voice_note_id=None,
            stage="media_intake",
            status="started",
            details={"message_kind": inbound_message.get("kind"), "has_media_id": bool(audio_payload.get("id"))},
        )

        try:
            media = self._retrieve_whatsapp_media(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                message_id=inbound_message["id"],
                audio_payload=audio_payload,
            )
        except Exception as exc:
            media = {
                "media_id": str(audio_payload.get("id") or "").strip() or None,
                "mime_type": str(audio_payload.get("mime_type") or "audio/ogg").strip() or "audio/ogg",
                "retrieval_status": "failed",
                "error": str(exc),
            }

        self._log_event(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            message_id=inbound_message.get("id"),
            voice_note_id=None,
            stage="media_intake",
            status=media.get("retrieval_status") or "unknown",
            details={k: v for k, v in media.items() if k not in {"provider_metadata"}},
        )

        try:
            transcription = self._transcribe(
                storage_path=media.get("storage_path"),
                media_url=media.get("media_url"),
                mime_type=media.get("mime_type"),
                provider_transcript=preferred_transcript,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                contact_id=contact_id,
                message_id=inbound_message["id"],
            )
        except Exception as exc:
            transcription = {
                "transcript": str(preferred_transcript or "").strip() if str(preferred_transcript or "").strip().lower() not in PLACEHOLDER_TRANSCRIPTS else "",
                "language": "es",
                "confidence": 0.0,
                "source": "failed",
                "segments": [],
                "diarization": [],
                "processing_status": "failed",
                "error": str(exc),
            }

        transcript = str(transcription.get("transcript") or "").strip()
        if not transcript:
            transcript = str(preferred_transcript or "").strip()
        if transcript.lower() in PLACEHOLDER_TRANSCRIPTS:
            transcript = ""
        language = str(transcription.get("language") or "es").strip() or "es"
        confidence = float(transcription.get("confidence") or 0)
        audio_quality = self._audio_quality(confidence, str(media.get("retrieval_status") or ""))
        background_noise_level = self._noise_from_confidence(confidence)
        processing_status = str(transcription.get("processing_status") or "completed")
        if transcript:
            processing_status = "completed"
        summary = transcript[:160] + ("..." if len(transcript) > 160 else "") if transcript else "Nota de voz recibida; transcripción pendiente."

        expires_at = add_minutes(utcnow_iso(), self._voice_settings()["ttl_minutes"])
        note = ingest_voice_note(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id or "",
            message_id=inbound_message.get("id"),
            transcript=transcript or "Nota de voz recibida; transcripción pendiente.",
            language=language,
            media_id=media.get("media_id"),
            media_url=media.get("media_url"),
            media_mime_type=media.get("mime_type"),
            media_sha256=media.get("sha256"),
            media_size_bytes=media.get("size_bytes"),
            consent_status="implicit_inbound_whatsapp",
            media_expires_at=expires_at,
            transcription_source=transcription.get("source"),
            transcription_confidence=confidence,
            diarization_json=transcription.get("diarization") or [],
            segments_json=transcription.get("segments") or [],
            audio_quality=audio_quality,
            background_noise_level=background_noise_level,
            processing_status=processing_status,
            reply_mode="audio" if is_voice_note else "text",
            metadata={
                "media": {k: v for k, v in media.items() if k != "provider_metadata"},
                "transcription": {k: v for k, v in transcription.items() if k not in {"segments", "diarization"}},
            },
            summary=summary,
        )

        self._persist_media_asset(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            message_id=inbound_message.get("id"),
            voice_note_id=note.get("id"),
            direction="inbound",
            media_role="raw_input",
            provider_media_id=media.get("media_id"),
            storage_path=media.get("storage_path"),
            public_url=media.get("media_url"),
            mime_type=media.get("mime_type"),
            sha256=media.get("sha256"),
            size_bytes=media.get("size_bytes"),
            expires_at=expires_at,
            consent_status="implicit_inbound_whatsapp",
            metadata={"retrieval_status": media.get("retrieval_status")},
        )

        self._log_event(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            conversation_id=conversation_id,
            contact_id=contact_id,
            message_id=inbound_message.get("id"),
            voice_note_id=note.get("id"),
            stage="transcription",
            status=processing_status,
            details={"confidence": confidence, "source": transcription.get("source"), "audio_quality": audio_quality},
        )

        message_metadata = from_json(inbound_message.get("metadata_json"), {})
        voice_metadata = {
            "voice_note_id": note.get("id"),
            "processing_status": processing_status,
            "transcription_source": transcription.get("source"),
            "transcription_confidence": confidence,
            "audio_quality": audio_quality,
            "background_noise_level": background_noise_level,
            "media_id": media.get("media_id"),
            "media_url": media.get("media_url"),
            "media_storage_path": media.get("storage_path"),
            "media_expires_at": expires_at,
            "is_voice_note": is_voice_note,
        }
        message_metadata["voice_pipeline"] = voice_metadata
        if transcript:
            execute(conn, "UPDATE messages SET body = ?, metadata_json = ? WHERE id = ?", (transcript, to_json(message_metadata), inbound_message["id"]))
        else:
            execute(conn, "UPDATE messages SET metadata_json = ? WHERE id = ?", (to_json(message_metadata), inbound_message["id"]))
        refreshed_message = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (inbound_message["id"],)) or inbound_message
        return {
            "processed": True,
            "voice_note": note,
            "message": refreshed_message,
            "transcript": transcript,
            "processing_status": processing_status,
            "audio_quality": audio_quality,
            "background_noise_level": background_noise_level,
        }

    def _synthesize_audio(self, *, organization_id: str, bot_id: str, conversation_id: str, contact_id: str | None, message_id: str, text: str, language: str, voice_context: dict[str, Any] | None) -> dict[str, Any] | None:
        webhook = self._voice_settings()["tts_webhook"]
        if not webhook or not text.strip():
            return None
        response = httpx.post(
            webhook,
            json={
                "organization_id": organization_id,
                "bot_id": bot_id,
                "conversation_id": conversation_id,
                "contact_id": contact_id,
                "message_id": message_id,
                "text": text,
                "language": language,
                "voice_context": voice_context or {},
            },
            timeout=self._voice_settings()["tts_timeout"],
        )
        response.raise_for_status()
        payload = response.json()
        audio_url = str(payload.get("audio_url") or payload.get("url") or "").strip() or None
        media_id = str(payload.get("media_id") or "").strip() or None
        if not audio_url and not media_id:
            return None
        return {
            "audio_url": audio_url,
            "media_id": media_id,
            "mime_type": str(payload.get("mime_type") or "audio/mpeg").strip() or "audio/mpeg",
            "duration_seconds": payload.get("duration_seconds"),
            "provider": str(payload.get("provider") or "tts_webhook"),
            "metadata": payload,
        }

    def _enqueue_reply(
        self,
        conn,
        *,
        organization_id: str,
        bot_id: str,
        conversation_id: str,
        contact_id: str | None,
        response_message: dict[str, Any],
        execution_run_id: str | None,
        payload: dict[str, Any],
        status: str,
    ) -> dict[str, Any]:
        outbox_id = new_id("out_voice")
        execute(
            conn,
            "INSERT INTO outbox_messages (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, status, attempts, last_error, scheduled_for, sent_at, created_at, provider_response_json, priority) VALUES (?, ?, ?, ?, ?, 'whatsapp', ?, ?, 0, NULL, ?, NULL, ?, '{}', 95)",
            (
                outbox_id,
                organization_id,
                bot_id,
                execution_run_id,
                conversation_id,
                to_json(payload),
                status,
                utcnow_iso(),
                utcnow_iso(),
            ),
        )
        metadata = from_json(response_message.get("metadata_json"), {})
        metadata.update({"provider": "queued_for_worker", "whatsapp": payload, "voice_reply": {"outbox_id": outbox_id}})
        execute(conn, "UPDATE messages SET kind = ?, status = ?, metadata_json = ? WHERE id = ?", (payload.get("message_type") or response_message.get("kind") or "text", status, to_json(metadata), response_message["id"]))
        return fetch_one(conn, "SELECT * FROM outbox_messages WHERE id = ?", (outbox_id,)) or {"id": outbox_id}

    def orchestrate_ai_reply(
        self,
        conn,
        *,
        organization_id: str,
        bot_id: str,
        conversation_id: str,
        contact_id: str | None,
        inbound_message: dict[str, Any],
        ai_result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not ai_result:
            return None
        response_message = ai_result.get("response_message") if isinstance(ai_result, dict) else None
        if not response_message or not response_message.get("id"):
            return None
        inbound_metadata = from_json(inbound_message.get("metadata_json"), {})
        voice_context = dict(inbound_metadata.get("voice_pipeline") or {})
        if not voice_context:
            return None
        response_text = str(response_message.get("body") or "").strip()
        if not response_text:
            return None
        language = "es"
        voice_note_id = voice_context.get("voice_note_id")
        if voice_note_id:
            row = fetch_one(conn, "SELECT * FROM voice_notes WHERE id = ?", (voice_note_id,))
            if row and row.get("detected_language"):
                language = row.get("detected_language")
        voice_context = self.build_voice_runtime_context(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            language=language,
            base_context=voice_context,
        )
        confidence = float(voice_context.get("transcription_confidence") or 0)
        reply_mode = "text"
        tts_asset = None
        if confidence >= self._voice_settings()["min_audio_confidence"]:
            try:
                tts_asset = self._synthesize_audio(
                    organization_id=organization_id,
                    bot_id=bot_id,
                    conversation_id=conversation_id,
                    contact_id=contact_id,
                    message_id=response_message["id"],
                    text=response_text,
                    language=language,
                    voice_context=voice_context,
                )
            except Exception as exc:
                self._log_event(
                    conn,
                    organization_id=organization_id,
                    bot_id=bot_id,
                    conversation_id=conversation_id,
                    contact_id=contact_id,
                    message_id=response_message.get("id"),
                    voice_note_id=voice_note_id,
                    stage="tts",
                    status="failed",
                    details={"error": str(exc)},
                )
                tts_asset = None
        if tts_asset:
            reply_mode = "audio"
            media_payload = {"mime_type": tts_asset.get("mime_type")}
            if tts_asset.get("media_id"):
                media_payload["id"] = tts_asset.get("media_id")
            if tts_asset.get("audio_url"):
                media_payload["link"] = tts_asset.get("audio_url")
            payload = {
                "message_type": "audio",
                "media": media_payload,
                "body": response_text,
                "message_id": response_message["id"],
                "contact_id": contact_id,
                "source": "ai_voice_reply",
            }
            outbox = self._enqueue_reply(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                contact_id=contact_id,
                response_message=response_message,
                execution_run_id=((ai_result.get("execution_run") or {}).get("id")),
                payload=payload,
                status="queued",
            )
            self._persist_media_asset(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                contact_id=contact_id,
                message_id=response_message.get("id"),
                voice_note_id=voice_note_id,
                direction="outbound",
                media_role="reply_tts",
                provider_media_id=tts_asset.get("media_id"),
                storage_path=None,
                public_url=tts_asset.get("audio_url"),
                mime_type=tts_asset.get("mime_type"),
                sha256=None,
                size_bytes=0,
                expires_at=None,
                consent_status="service_response",
                metadata=tts_asset.get("metadata") or {},
            )
            self._log_event(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                contact_id=contact_id,
                message_id=response_message.get("id"),
                voice_note_id=voice_note_id,
                stage="reply_orchestration",
                status="queued_audio",
                details={"outbox_id": outbox.get("id"), "reply_mode": reply_mode},
            )
        else:
            payload = {
                "message_type": "text",
                "body": response_text,
                "message_id": response_message["id"],
                "contact_id": contact_id,
                "source": "ai_voice_reply",
            }
            outbox = self._enqueue_reply(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                contact_id=contact_id,
                response_message=response_message,
                execution_run_id=((ai_result.get("execution_run") or {}).get("id")),
                payload=payload,
                status="queued",
            )
            self._log_event(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                conversation_id=conversation_id,
                contact_id=contact_id,
                message_id=response_message.get("id"),
                voice_note_id=voice_note_id,
                stage="reply_orchestration",
                status="queued_text",
                details={"outbox_id": outbox.get("id"), "reply_mode": reply_mode},
            )
        execute(conn, "UPDATE voice_notes SET reply_mode = ? WHERE id = ?", (reply_mode, voice_note_id))
        refreshed = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (response_message["id"],)) or response_message
        return {"reply_mode": reply_mode, "response_message": refreshed, "outbox": outbox}


voice_pipeline_service = VoicePipelineService()
