from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class DeadLetterRequeueRequest(BaseModel):
    scheduled_for: str | None = None


class SettingsUpdateRequest(BaseModel):
    global_policy: str | None = None
    default_model: str | None = None
    freeze_minutes_after_takeover: int | None = None
