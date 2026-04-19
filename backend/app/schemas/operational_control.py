from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AuthorizedOperationalNumberRequest(BaseModel):
    organization_id: str
    bot_id: str
    phone_e164: str
    role: str = "owner"
    allowed_intents: list[str] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "verified", "revoked"] = "verified"


class OperationalCommandPreviewRequest(BaseModel):
    organization_id: str
    bot_id: str
    text: str
    source_channel: Literal["portal", "whatsapp"] = "portal"
    dry_run: bool = True


class OperationalCommandCreateRequest(BaseModel):
    organization_id: str
    bot_id: str
    text: str
    source_channel: Literal["portal", "whatsapp"] = "portal"
    dry_run: bool = False
    actor_phone_e164: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalCommandConfirmRequest(BaseModel):
    confirmation_code: str | None = None


class OperationalCommandApproveRequest(BaseModel):
    note: str = ""


class OperationalCommandCancelRequest(BaseModel):
    reason: str = ""


class OperationalCommandUndoRequest(BaseModel):
    reason: str = "undo_requested"


class OperationalRescheduleBatchPreviewRequest(BaseModel):
    organization_id: str
    bot_id: str
    scope_day: Literal["today", "tomorrow", "custom"] = "tomorrow"
    target_date: str | None = None
    target_start_time: str = "09:00"
    target_end_time: str = "18:00"
    strategy: Literal["next_available_window", "shift_minutes"] = "next_available_window"
    delay_minutes: int = 30
    notify_clients: bool = False


class OperationalRescheduleBatchExecuteRequest(OperationalRescheduleBatchPreviewRequest):
    confirm_large_impact: bool = False
