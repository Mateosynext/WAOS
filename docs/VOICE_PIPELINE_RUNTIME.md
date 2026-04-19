# Voice pipeline runtime

This release upgrades voice handling from transcript-only ingestion to an end-to-end runtime path:

1. WhatsApp audio message intake
2. Optional media retrieval from Meta Cloud API
3. Optional raw media storage with TTL metadata
4. Real transcription path via provider transcript or configurable STT webhook
5. Confidence, diarization/segments, quality and noise signals persisted on `voice_notes`
6. AI reply orchestration with dynamic text vs audio fallback
7. Optional TTS webhook that can return `media_id` or `audio_url` for WhatsApp delivery
8. Outbox enqueue for real WhatsApp delivery instead of leaving voice replies as simulated only

## New env vars

- `VOICE_MEDIA_STORAGE_DIR`
- `VOICE_MEDIA_TTL_MINUTES`
- `VOICE_TRANSCRIPTION_WEBHOOK_URL`
- `VOICE_TRANSCRIPTION_TIMEOUT_SECONDS`
- `VOICE_TTS_WEBHOOK_URL`
- `VOICE_TTS_TIMEOUT_SECONDS`
- `VOICE_MIN_AUDIO_REPLY_CONFIDENCE`

## Notes

- If Meta media download is unavailable, the pipeline still records the voice note and keeps processing status explicit.
- If transcription is unavailable, the conversation is not blocked; the system marks `transcription_pending`.
- If TTS is unavailable, voice replies gracefully fall back to text while still using the real WhatsApp outbox.
