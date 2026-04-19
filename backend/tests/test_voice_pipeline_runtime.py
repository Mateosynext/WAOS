from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import execute, fetch_all, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.app.repositories.conversations import create_message
from backend.app.voice_pipeline import voice_pipeline_service
from backend.tests.test_activation_foundations import _auth_headers
from backend.tests.test_whatsapp_channel_runtime import _ensure_whatsapp_number


client = TestClient(app)


def test_audio_webhook_creates_voice_note_and_links_message(monkeypatch) -> None:
    _ensure_whatsapp_number(phone_number_id="wa_voice_runtime")
    monkeypatch.setattr("backend.app.application.inbound_service.run_ai_pipeline", lambda *args, **kwargs: {"reply": None})

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-voice",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"display_phone_number": "+52 1 555 000 9999", "phone_number_id": "wa_voice_runtime"},
                            "contacts": [{"wa_id": "5215551112222", "profile": {"name": "Mateo"}}],
                            "messages": [
                                {
                                    "id": "wamid-voice-1",
                                    "from": "5215551112222",
                                    "timestamp": "1710002001",
                                    "type": "audio",
                                    "audio": {"id": "aud-voice-1", "mime_type": "audio/ogg", "voice": True, "transcript": "Hola, quiero precio y agenda para hoy"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }

    response = client.post("/webhooks/whatsapp/wa_voice_runtime", json=payload)
    assert response.status_code == 200

    with get_connection() as conn:
        message = fetch_one(conn, "SELECT * FROM messages WHERE external_id = ?", ("wamid-voice-1",))
        note = fetch_one(conn, "SELECT * FROM voice_notes WHERE message_id = ?", (message["id"],))
        events = fetch_all(conn, "SELECT stage, status FROM voice_processing_events WHERE message_id = ? ORDER BY created_at ASC", (message["id"],))
    assert "precio" in message["body"].lower()
    assert note["intent"] == "pricing"
    assert note["message_id"] == message["id"]
    assert float(note["transcription_confidence"] or 0) >= 0.9
    assert any(item["stage"] == "transcription" for item in events)


def test_voice_reply_orchestration_queues_text_fallback_when_tts_missing() -> None:
    init_db()
    _auth_headers()
    with get_connection() as conn:
        inbound = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", ("msg_activation_in_1",))
        if not inbound:
            inbound = create_message(
                conn,
                organization_id="org_activation",
                conversation_id="conv_activation",
                contact_id="ct_activation",
                bot_id="bot_activation",
                direction="inbound",
                kind="audio",
                source="whatsapp",
                body="Necesito ayuda con una cita",
                status="received",
                metadata={"voice_pipeline": {"voice_note_id": "voice_test", "transcription_confidence": 0.95, "is_voice_note": True}},
            )
        execute(conn, "DELETE FROM voice_notes WHERE id = ?", ("voice_test",))
        execute(conn, "INSERT INTO voice_notes (id, organization_id, bot_id, conversation_id, contact_id, message_id, transcript, detected_language, intent, urgency_level, emotion, suggested_response_text, suggested_response_audio_text, summary, media_size_bytes, consent_status, transcription_source, transcription_confidence, diarization_json, segments_json, audio_quality, background_noise_level, processing_status, reply_mode, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'es', 'schedule', 'media', 'neutral', ?, ?, ?, 0, 'implicit_inbound_whatsapp', 'provider_transcript', 0.95, '[]', '[]', 'high', 'low', 'completed', 'text', '{}', datetime('now'))", ("voice_test", "org_activation", "bot_activation", "conv_activation", "ct_activation", inbound["id"], "Necesito ayuda con una cita", "Gracias por tu audio", "Gracias por tu audio", "Necesito ayuda con una cita"))
        execute(conn, "UPDATE messages SET metadata_json = ? WHERE id = ?", ('{"voice_pipeline":{"voice_note_id":"voice_test","transcription_confidence":0.95,"is_voice_note":true}}', inbound["id"]))
        response = create_message(
            conn,
            organization_id="org_activation",
            conversation_id="conv_activation",
            contact_id="ct_activation",
            bot_id="bot_activation",
            direction="outbound",
            kind="text",
            source="ai",
            body="Te ayudo a agendar por aquí",
            status="simulated",
            metadata={"provider": "simulated"},
        )
        result = voice_pipeline_service.orchestrate_ai_reply(
            conn,
            organization_id="org_activation",
            bot_id="bot_activation",
            conversation_id="conv_activation",
            contact_id="ct_activation",
            inbound_message=fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (inbound["id"],)),
            ai_result={"response_message": response, "execution_run": {"id": None}},
        )
        queued = fetch_one(conn, "SELECT * FROM outbox_messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1", ("conv_activation",))
        refreshed = fetch_one(conn, "SELECT * FROM messages WHERE id = ?", (response["id"],))
    assert result
    assert result["reply_mode"] == "text"
    assert queued["status"] == "queued"
    assert refreshed["status"] == "queued"
