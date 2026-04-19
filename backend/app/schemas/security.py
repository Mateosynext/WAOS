from __future__ import annotations

from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, Field, StringConstraints
from typing_extensions import Annotated


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class SecurityPolicyUpsertRequest(BaseModel):
    organization_id: NonEmptyStr
    require_mfa: bool = False
    require_sso: bool = False
    session_ttl_minutes: int = Field(default=720, ge=15, le=43200)
    session_idle_timeout_minutes: int = Field(default=120, ge=5, le=43200)
    step_up_window_minutes: int = Field(default=15, ge=1, le=1440)
    max_sessions_per_user: int = Field(default=5, ge=1, le=50)
    require_dual_approval_releases: bool = True
    webhook_signature_required: bool = True
    strict_idempotency: bool = True
    ip_allowlist: list[str] = Field(default_factory=list, max_length=100)
    allowed_origins: list[AnyHttpUrl] = Field(default_factory=list, max_length=50)


class SSOProviderUpsertRequest(BaseModel):
    organization_id: NonEmptyStr
    provider: Literal["oidc", "google_workspace", "okta", "azure_ad"] = "oidc"
    issuer: str = ""
    client_id: str = ""
    status: Literal["draft", "configured", "active", "paused"] = "configured"
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"], max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RateLimitPolicyRequest(BaseModel):
    organization_id: NonEmptyStr
    bot_id: str | None = None
    scope: Literal["bot", "contact_phone"] = "bot"
    window_seconds: int = Field(default=60, ge=1, le=86400)
    max_requests: int = Field(default=30, ge=1, le=100000)
    is_active: bool = True


class SecretCreateRequest(BaseModel):
    organization_id: NonEmptyStr
    bot_id: str | None = None
    scope: Literal["tenant", "bot"] = "tenant"
    key_name: NonEmptyStr
    secret_value: str = Field(min_length=1, max_length=10000)
