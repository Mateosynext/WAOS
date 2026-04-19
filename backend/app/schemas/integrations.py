from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class IntegrationUpsertRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    integration_type: Literal["whatsapp", "calendar", "crm", "webhook", "meta_embedded_signup", "payments", "commerce"]
    provider: str
    name: str
    status: Literal["draft", "configured", "active", "paused"] = "configured"
    config: dict[str, Any] = Field(default_factory=dict)


class WhatsAppIntegrationConfigRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    name: str = "WhatsApp Cloud API"
    provider: Literal["meta_cloud_api"] = "meta_cloud_api"
    phone_number: str = ""
    phone_number_id: str = ""
    waba_id: str | None = None
    access_token: str | None = None
    app_secret: str | None = None
    webhook_verify_token: str | None = None
    status: Literal["draft", "configured", "active", "paused"] = "configured"


class GoogleCalendarConfigRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    name: str = "Google Calendar"
    client_id: str = ""
    client_secret: str | None = None
    redirect_uri: str
    frontend_redirect_uri: str | None = None
    calendar_id: str | None = None
    scopes: list[str] = Field(default_factory=lambda: ["openid", "email", "profile", "https://www.googleapis.com/auth/calendar"])
    timezone: str | None = None
    auto_sync_enabled: bool = True
    sync_frequency_minutes: int = 30
    status: Literal["draft", "configured", "active", "paused"] = "configured"


class StripeIntegrationConfigRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    name: str = "Stripe Payments"
    success_url: str
    cancel_url: str
    webhook_url: str | None = None
    publishable_key: str | None = None
    secret_key: str | None = None
    webhook_secret: str | None = None
    auto_sync_enabled: bool = True
    sync_frequency_minutes: int = 10
    status: Literal["draft", "configured", "active", "paused"] = "configured"


class MetaEmbeddedSignupCompleteRequest(BaseModel):
    state: str
    phone_number_id: str
    phone_number: str | None = None
    waba_id: str | None = None
    access_token: str | None = None
    app_secret: str | None = None
    webhook_verify_token: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class WebhookReplayRequest(BaseModel):
    dry_run: bool = True
    note: str | None = None
