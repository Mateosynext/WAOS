from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.db import fetch_all, fetch_one, get_connection, init_db
from backend.app.main import app
from backend.tests.test_activation_foundations import _auth_headers


client = TestClient(app)


def test_voice_channel_session_turn_keeps_shared_memory_and_policy() -> None:
    headers = _auth_headers()
    start = client.post(
        '/api/v1/voice-channel/sessions/start',
        json={
            'organization_id': 'org_activation',
            'bot_id': 'bot_activation',
            'contact_id': 'ct_activation',
            'conversation_id': 'conv_activation',
            'channel': 'whatsapp_voice',
            'requested_modality': 'voice',
        },
        headers=headers,
    )
    assert start.status_code == 200
    session = start.json()['data']
    assert session['state'] == 'listening'
    assert session['continuity_mode'] == 'shared_runtime_memory'

    turn = client.post(
        f"/api/v1/voice-channel/sessions/{session['id']}/turns",
        json={
            'actor': 'contact',
            'transcript_text': 'Hola, es urgente, falló mi pago y necesito el link ahora mismo',
            'requested_reply_mode': 'voice',
        },
        headers=headers,
    )
    assert turn.status_code == 200
    data = turn.json()['data']
    assert data['route']['specialist_agent_key'] == 'collections'
    assert data['policy']['policy_profile_key'] == 'collections_ops'
    assert data['shared_memory']['payments']
    assert data['input_turn']['urgency_level'] == 'high'
    assert data['assistant_turn']['modality'] == 'voice'
    assert data['assistant_turn']['response']['render']['status'] in {'ready', 'queued_render', 'text_fallback'}
    assert data['session']['latest_specialist_agent_key'] == 'collections'

    with get_connection() as conn:
        turns = fetch_all(conn, 'SELECT actor, modality, state FROM voice_channel_turns WHERE session_id = ? ORDER BY turn_index ASC', (session['id'],))
        notes = fetch_all(conn, 'SELECT * FROM voice_notes WHERE conversation_id = ? ORDER BY created_at DESC', ('conv_activation',))
    assert len(turns) >= 2
    assert turns[0]['actor'] == 'contact'
    assert any(note.get('message_id') for note in notes)


def test_voice_channel_interrupt_and_handoff_to_text() -> None:
    init_db()
    headers = _auth_headers()
    start = client.post(
        '/api/v1/voice-channel/sessions/start',
        json={
            'organization_id': 'org_activation',
            'bot_id': 'bot_activation',
            'contact_id': 'ct_activation',
            'conversation_id': 'conv_activation',
            'channel': 'voice_web',
            'requested_modality': 'voice',
        },
        headers=headers,
    )
    session_id = start.json()['data']['id']
    first_turn = client.post(
        f'/api/v1/voice-channel/sessions/{session_id}/turns',
        json={
            'actor': 'contact',
            'transcript_text': 'Quiero reagendar mi cita para mañana temprano',
            'requested_reply_mode': 'voice',
        },
        headers=headers,
    )
    assert first_turn.status_code == 200

    interrupted = client.post(
        f'/api/v1/voice-channel/sessions/{session_id}/interrupt',
        json={'reason': 'customer_barge_in'},
        headers=headers,
    )
    assert interrupted.status_code == 200
    interrupted_data = interrupted.json()['data']
    assert interrupted_data['reason'] == 'customer_barge_in'
    assert interrupted_data['session']['state'] == 'listening'
    assert interrupted_data['interrupted_turn']['state'] == 'interrupted'

    handoff = client.post(
        f'/api/v1/voice-channel/sessions/{session_id}/handoff',
        json={
            'to_channel': 'text',
            'reason': 'needs_async_followup',
            'summary_text': 'Continuar por texto con opciones de reagenda',
            'target_queue': 'booking_followup',
        },
        headers=headers,
    )
    assert handoff.status_code == 200
    payload = handoff.json()['data']
    assert payload['handoff']['to_channel'] == 'text'
    assert payload['session']['handoff_state'] == 'completed'
    assert payload['session']['handoff_channel'] == 'text'

    fetched = client.get(f'/api/v1/voice-channel/sessions/{session_id}', headers=headers)
    assert fetched.status_code == 200
    fetched_data = fetched.json()['data']
    assert fetched_data['handoffs']
    assert fetched_data['turns']
