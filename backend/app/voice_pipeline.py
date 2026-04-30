from __future__ import annotations

from typing import Any

class VoicePipelineService:
    def transcribe(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"text": "", "confidence": 0, "status": "not_configured", "mode": "rc_compatibility"}

    def synthesize(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"audio_url": None, "status": "not_configured", "mode": "rc_compatibility"}

    def handle_inbound_voice(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "accepted", "mode": "rc_compatibility"}

    def __getattr__(self, name: str):
        def _method(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"operation": name, "status": "not_configured", "mode": "rc_compatibility"}
        return _method

voice_pipeline_service = VoicePipelineService()
