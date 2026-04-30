from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ToolAction = Literal[
    "book_appointment",
    "reschedule",
    "create_payment_link",
    "update_contact_stage",
    "send_receipt",
]


class ToolExecutionRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    action: ToolAction
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    client_request_id: str | None = None
    preview_execution_id: str | None = None
    confirmation_token: str | None = None
    confirm: bool = False
    force_retry_failed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionListQuery(BaseModel):
    organization_id: str
    action: ToolAction | None = None
    status: str | None = None
    limit: int = Field(default=100, ge=1, le=500)
