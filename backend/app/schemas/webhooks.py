from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppWebhookText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = ""


class WhatsAppWebhookMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    from_: str | None = Field(default=None, alias="from")
    type: str
    text: WhatsAppWebhookText | None = None


class WhatsAppWebhookProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None


class WhatsAppWebhookContact(BaseModel):
    model_config = ConfigDict(extra="allow")
    wa_id: str | None = None
    profile: WhatsAppWebhookProfile | None = None


class WhatsAppWebhookValue(BaseModel):
    model_config = ConfigDict(extra="allow")
    contacts: list[WhatsAppWebhookContact] = []
    messages: list[WhatsAppWebhookMessage] = []


class WhatsAppWebhookChange(BaseModel):
    model_config = ConfigDict(extra="allow")
    value: WhatsAppWebhookValue


class WhatsAppWebhookEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    changes: list[WhatsAppWebhookChange] = []


class WhatsAppWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    entry: list[WhatsAppWebhookEntry] = []
