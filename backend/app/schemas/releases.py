from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class ReleaseRequestCreate(BaseModel):
    title: str = ""
    notes: str = ""


class ReleaseApprovalRequest(BaseModel):
    note: str = ""


class PublishScheduleRequest(BaseModel):
    organization_id: str
    bot_id: str
    version_id: str | None = None
    scheduled_for: str
    notes: str = ""
