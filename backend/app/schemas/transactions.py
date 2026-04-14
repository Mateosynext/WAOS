from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VerticalTransactionAccountCreateRequest(BaseModel):
    organization_id: str
    vertical_id: str
    bot_id: str | None = None
    contact_id: str | None = None
    external_reference: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)


class VerticalTransactionCommandRequest(BaseModel):
    command_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class VerticalTransactionPlaybookRequest(BaseModel):
    organization_id: str
