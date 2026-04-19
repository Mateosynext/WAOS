# WAOS Voice as a First-Class Channel

This upgrade promotes voice from a secondary pipeline to a native runtime surface.

## What changed
- Added `voice_channel_sessions`, `voice_channel_turns`, and `voice_channel_handoffs`.
- Added `/api/v1/voice-channel/...` endpoints to start sessions, ingest turns, interrupt playback, and handoff between voice and text.
- Preserved continuity with the same contact, conversation, shared memory, specialist routing, and policy profiles already used by text runtime.
- Inbound contact turns are also written into `voice_notes`, so downstream AI and analytics can reuse the same context window.
- Barge-in is handled by interrupting the latest assistant turn and returning the session to `listening`.

## Runtime behavior
1. Start a voice session against an existing contact/conversation.
2. Ingest a contact turn with transcript or provider transcript.
3. Detect urgency, requested-human cues, entities, and specialist route.
4. Evaluate the same specialist policy profile used by the multi-agent runtime.
5. Generate one assistant turn, keep text continuity, and try TTS through the existing voice pipeline when available.
6. Allow explicit interruption and voice↔text handoff without losing conversation state.

## Main files
- `backend/app/voice_channel_runtime.py`
- `backend/app/application/voice_channel_service.py`
- `backend/app/api/routers/voice_channel.py`
- `backend/app/schemas/voice_channel.py`
- `backend/tests/test_voice_first_class_channel.py`
