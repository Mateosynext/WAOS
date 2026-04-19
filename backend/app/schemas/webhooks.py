from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppWebhookText(BaseModel):
    model_config = ConfigDict(extra="allow")
    body: str = ""


class WhatsAppWebhookAudio(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    mime_type: str | None = None
    voice: bool | None = None


class WhatsAppWebhookImage(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    mime_type: str | None = None
    caption: str | None = None
    sha256: str | None = None


class WhatsAppWebhookDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    caption: str | None = None
    sha256: str | None = None


class WhatsAppWebhookVideo(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    mime_type: str | None = None
    caption: str | None = None
    sha256: str | None = None


class WhatsAppWebhookLocation(BaseModel):
    model_config = ConfigDict(extra="allow")
    latitude: float | None = None
    longitude: float | None = None
    name: str | None = None
    address: str | None = None


class WhatsAppWebhookContactName(BaseModel):
    model_config = ConfigDict(extra="allow")
    formatted_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class WhatsAppWebhookSharedContact(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: WhatsAppWebhookContactName | None = None
    phones: list[dict[str, Any]] = Field(default_factory=list)
    emails: list[dict[str, Any]] = Field(default_factory=list)


class WhatsAppWebhookButtonReply(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    title: str | None = None


class WhatsAppWebhookListReply(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    title: str | None = None
    description: str | None = None


class WhatsAppWebhookNfmReply(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str | None = None
    body: str | None = None
    response_json: str | None = None


class WhatsAppWebhookInteractive(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str | None = None
    button_reply: WhatsAppWebhookButtonReply | None = None
    list_reply: WhatsAppWebhookListReply | None = None
    nfm_reply: WhatsAppWebhookNfmReply | None = None


class WhatsAppWebhookContext(BaseModel):
    model_config = ConfigDict(extra="allow")
    from_: str | None = Field(default=None, alias="from")
    id: str | None = None
    forwarded: bool | None = None
    frequently_forwarded: bool | None = None


class WhatsAppWebhookMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    from_: str | None = Field(default=None, alias="from")
    timestamp: str | None = None
    type: str
    text: WhatsAppWebhookText | None = None
    audio: WhatsAppWebhookAudio | None = None
    image: WhatsAppWebhookImage | None = None
    document: WhatsAppWebhookDocument | None = None
    video: WhatsAppWebhookVideo | None = None
    location: WhatsAppWebhookLocation | None = None
    contacts: list[WhatsAppWebhookSharedContact] = Field(default_factory=list)
    interactive: WhatsAppWebhookInteractive | None = None
    context: WhatsAppWebhookContext | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)


class WhatsAppWebhookProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str | None = None


class WhatsAppWebhookContact(BaseModel):
    model_config = ConfigDict(extra="allow")
    wa_id: str | None = None
    profile: WhatsAppWebhookProfile | None = None


class WhatsAppWebhookConversation(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    expiration_timestamp: str | None = None
    origin: dict[str, Any] | None = None


class WhatsAppWebhookPricing(BaseModel):
    model_config = ConfigDict(extra="allow")
    billable: bool | None = None
    pricing_model: str | None = None
    category: str | None = None
    type: str | None = None


class WhatsAppWebhookStatus(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    status: str | None = None
    timestamp: str | None = None
    recipient_id: str | None = None
    conversation: WhatsAppWebhookConversation | None = None
    pricing: WhatsAppWebhookPricing | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)


class WhatsAppWebhookProviderError(BaseModel):
    model_config = ConfigDict(extra="allow")
    code: int | None = None
    title: str | None = None
    message: str | None = None
    error_data: dict[str, Any] | None = None
    href: str | None = None


class WhatsAppWebhookMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    display_phone_number: str | None = None
    phone_number_id: str | None = None


class WhatsAppWebhookValue(BaseModel):
    model_config = ConfigDict(extra="allow")
    messaging_product: str | None = None
    metadata: WhatsAppWebhookMetadata | None = None
    contacts: list[WhatsAppWebhookContact] = Field(default_factory=list)
    messages: list[WhatsAppWebhookMessage] = Field(default_factory=list)
    statuses: list[WhatsAppWebhookStatus] = Field(default_factory=list)
    errors: list[WhatsAppWebhookProviderError] = Field(default_factory=list)


class WhatsAppWebhookChange(BaseModel):
    model_config = ConfigDict(extra="allow")
    field: str | None = None
    value: WhatsAppWebhookValue


class WhatsAppWebhookEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    changes: list[WhatsAppWebhookChange] = Field(default_factory=list)


class WhatsAppWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    object: str | None = None
    entry: list[WhatsAppWebhookEntry] = Field(default_factory=list)
