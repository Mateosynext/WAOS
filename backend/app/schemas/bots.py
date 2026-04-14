from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class FAQItem(BaseModel):
    q: str
    a: str


class BotCreateRequest(BaseModel):
    organization_id: str
    business_name: str
    vertical: str
    bot_name: str
    primary_objective: Literal["vender", "calificar", "agendar", "responder", "reactivar", "agendar"] = "agendar"
    tone: str = "amable"
    language: str = "es"
    timezone: str = "America/Mexico_City"
    services: list[str] = Field(default_factory=list)
    hours: str = ""
    faqs: list[FAQItem] = Field(default_factory=list)
    whatsapp_number: str = ""
    publish_now: bool = True


class BotUpdateRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    ai_paused: bool | None = None
    vertical: str | None = None
    apply_vertical_defaults: bool | None = None
    config_draft: dict[str, Any] | None = None


class PublishRequest(BaseModel):
    notes: str = ""


class CloneBotRequest(BaseModel):
    target_organization_id: str | None = None
    new_name: str | None = None


class BotResponseTemplateRequest(BaseModel):
    organization_id: str
    bot_id: str
    template_key: Literal["welcome", "out_of_hours", "no_stock", "promotion", "booking", "followup", "handoff", "close_sale", "post_sale", "custom"] = "custom"
    channel: str = "whatsapp"
    title: str | None = None
    content: str
    variables: list[str] = Field(default_factory=list)
    is_active: bool = True


class BotBehaviorSettingsRequest(BaseModel):
    organization_id: str
    bot_id: str
    tone: Literal["formal", "cercano", "vendedor", "premium", "tecnico"] = "cercano"
    response_length: Literal["corta", "media", "detallada"] = "media"
    use_emojis: bool = False
    sales_intensity: Literal["baja", "media", "alta"] = "media"
    offer_promotions_when: str = "when_relevant"
    escalate_when: list[str] = Field(default_factory=list)
    insistence_policy: str = "respectful"
    can_share_price_directly: bool = True
    can_negotiate: bool = False
    can_mention_stock: bool = True
    auto_send_images: bool = True
    bot_mode: Literal["bot", "human_only", "hybrid", "schedule_based"] = "hybrid"
    active_hours: list[dict[str, Any]] = Field(default_factory=list)
    active_channels: list[str] = Field(default_factory=lambda: ["whatsapp"])
    forbidden_topics: list[str] = Field(default_factory=list)
    required_phrases: list[str] = Field(default_factory=list)
    fallback_message: str = "Te ayudo con gusto, pero necesito un poco mas de detalle para responderte bien."
