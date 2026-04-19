from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class OrganizationCreateRequest(BaseModel):
    name: str
    vertical: str = ""
    timezone: str = "America/Mexico_City"


class OrganizationUpdateRequest(BaseModel):
    name: str | None = None
    vertical: str | None = None
    subvertical: str | None = None
    timezone: str | None = None
    status: str | None = None
