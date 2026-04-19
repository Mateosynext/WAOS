from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class CookieConsentUpsertRequest(BaseModel):
    anonymous_id: str | None = Field(default=None, max_length=128)
    organization_id: str | None = Field(default=None, max_length=80)
    contact_id: str | None = Field(default=None, max_length=80)
    user_id: str | None = Field(default=None, max_length=80)
    source: str = Field(default="cookie_banner", max_length=80)
    page_url: str | None = Field(default=None, max_length=1000)
    consent_version: str = Field(default="1.0.0", max_length=40)
    categories: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LegalAcceptanceRequest(BaseModel):
    slug: NonEmptyStr
    version: str = Field(default="1.0.0", max_length=40)
    anonymous_id: str | None = Field(default=None, max_length=128)
    organization_id: str | None = Field(default=None, max_length=80)
    contact_id: str | None = Field(default=None, max_length=80)
    user_id: str | None = Field(default=None, max_length=80)
    acceptance_type: Literal["terms", "privacy_notice", "dpa", "msa", "cookie_notice", "other"] = "other"
    source: str = Field(default="product", max_length=80)
    page_url: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PrivacyRightsRequest(BaseModel):
    request_type: Literal["access", "rectification", "cancellation", "opposition", "revocation", "portability", "restriction", "other"]
    name: NonEmptyStr
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    organization_id: str | None = Field(default=None, max_length=80)
    contact_id: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=4000)
    source: str = Field(default="privacy_center", max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)
