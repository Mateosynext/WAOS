from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import fetch_one, get_connection, init_db
from backend.tests.test_activation_foundations import _auth_headers
from backend.app.main import app

client = TestClient(app)


def test_twilio_voice_inbound_creates_voice_session() -> None:
    init_db()
    _auth_headers()
    response = client.post(
        '/webhooks/twilio/voice?bot_id=bot_activation',
        data={
            'CallSid': 'CA_TEST_001',
            'From': '+5215512345678',
            'To': '+525500011122',
            'CallerName': 'Cliente Demo',
        },
    )
    assert response.status_code == 200
    assert '/webhooks/twilio/voice/turn?bot_id=bot_activation' in response.text
    assert 'session_id=' in response.text
    assert 'Cuéntame en qué te ayudo hoy' in response.text
    with get_connection() as conn:
        row = fetch_one(conn, "SELECT * FROM voice_channel_sessions WHERE channel = 'twilio_voice' ORDER BY updated_at DESC LIMIT 1")
    assert row is not None


def test_twilio_voice_turn_plays_ready_audio_and_closes_on_status() -> None:
    init_db()
    _auth_headers()
    response = client.post(
        '/webhooks/twilio/voice?bot_id=bot_activation',
        data={
            'CallSid': 'CA_TEST_002',
            'From': '+5215512349999',
            'To': '+525500011122',
        },
    )
    assert response.status_code == 200
    with get_connection() as conn:
        row = fetch_one(conn, "SELECT * FROM voice_channel_sessions WHERE channel = 'twilio_voice' ORDER BY updated_at DESC LIMIT 1")
        session_id = row['id']

    import backend.app.voice_channel_runtime as voice_runtime

    original = voice_runtime._render_assistant_audio
    voice_runtime._render_assistant_audio = lambda *args, **kwargs: {
        'status': 'ready',
        'asset': {'audio_url': 'https://cdn.example.com/owner-voice.mp3'},
        'provider': 'test',
    }
    try:
        turn = client.post(
            f'/webhooks/twilio/voice/turn?session_id={session_id}',
            data={'CallSid': 'CA_TEST_002', 'CallStatus': 'in-progress', 'SpeechResult': 'Quiero saber el precio y agendar hoy'},
        )
    finally:
        voice_runtime._render_assistant_audio = original
    assert turn.status_code == 200
    assert '<Play>https://cdn.example.com/owner-voice.mp3</Play>' in turn.text

    status = client.post(
        f'/webhooks/twilio/voice/status?session_id={session_id}',
        data={'CallSid': 'CA_TEST_002', 'CallStatus': 'completed'},
    )
    assert status.status_code == 200
    with get_connection() as conn:
        ended = fetch_one(conn, 'SELECT ended_at, state FROM voice_channel_sessions WHERE id = ?', (session_id,))
    assert ended['ended_at'] is not None
    assert ended['state'] == 'ended'
