from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class SecurityPolicyUpsertRequest(BaseModel):
    organization_id: str
    require_mfa: bool = False
    require_sso: bool = False
    session_ttl_minutes: int = 720
    session_idle_timeout_minutes: int = 120
    step_up_window_minutes: int = 15
    max_sessions_per_user: int = 5
    require_dual_approval_releases: bool = True
    webhook_signature_required: bool = True
    strict_idempotency: bool = True
    ip_allowlist: list[str] = Field(default_factory=list)
    allowed_origins: list[str] = Field(default_factory=list)


class SSOProviderUpsertRequest(BaseModel):
    organization_id: str
    provider: Literal["oidc", "google_workspace", "okta", "azure_ad"] = "oidc"
    issuer: str = ""
    client_id: str = ""
    status: Literal["draft", "configured", "active", "paused"] = "configured"
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    metadata: dict[str, Any] = Field(default_factory=dict)


class RateLimitPolicyRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    scope: Literal["bot", "contact_phone"] = "bot"
    window_seconds: int = 60
    max_requests: int = 30
    is_active: bool = True


class SecretCreateRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    scope: Literal["tenant", "bot"] = "tenant"
    key_name: str
    secret_value: str
