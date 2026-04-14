from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class PaymentRequestCreate(BaseModel):
    organization_id: str
    bot_id: str
    conversation_id: str
    contact_id: str
    title: str
    amount: float
    currency: str = "MXN"
    reminder_minutes: int = 60
    send_receipt_on_confirm: bool = True
    appointment_id: str | None = None
    provider: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaymentConfirmRequest(BaseModel):
    provider_reference: str | None = None


class WhatsAppFlowCreateRequest(BaseModel):
    organization_id: str
    bot_id: str
    name: str
    flow_type: Literal[
        "lead_prequalification",
        "appointment_booking",
        "guided_quote",
        "data_update",
        "post_sale_survey",
        "client_onboarding",
    ]
    status: Literal["draft", "active", "paused"] = "active"
    language: str = "es"
    screens: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceRequestCreate(BaseModel):
    organization_id: str
    bot_id: str
    contact_id: str
    request_type: Literal[
        "order_status",
        "balance",
        "invoice_download",
        "upcoming_appointments",
        "profile_update",
        "payment_confirmation",
        "support_case",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)


class PlaybookCreateRequest(BaseModel):
    organization_id: str
    industry: Literal["clinicas", "inmobiliaria", "educacion", "ecommerce", "estetica", "automotriz"]
    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class CatalogCategoryRequest(BaseModel):
    organization_id: str
    name: str
    kind: Literal["product", "service", "mixed"] = "product"
    description: str = ""
    sort_order: int = 0
    is_active: bool = True


class CatalogProductRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    category_id: str | None = None
    name: str
    sku: str | None = None
    short_description: str = ""
    long_description: str = ""
    price: float = 0
    promotional_price: float | None = None
    currency: str = "MXN"
    status: Literal["draft", "active", "paused", "agotado"] = "active"
    priority: int = 50
    tags: list[str] = Field(default_factory=list)
    specs: dict[str, Any] = Field(default_factory=dict)
    benefits: list[str] = Field(default_factory=list)
    faq: list[dict[str, Any]] = Field(default_factory=list)
    related_product_ids: list[str] = Field(default_factory=list)
    checkout_url: str | None = None
    availability: dict[str, Any] = Field(default_factory=dict)
    delivery_eta: str | None = None
    stock_visibility: Literal["visible", "hidden"] = "visible"
    variants: list[dict[str, Any]] = Field(default_factory=list)
    inventory: list[dict[str, Any]] = Field(default_factory=list)


class CatalogServiceRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    category_id: str | None = None
    name: str
    duration_minutes: int = 30
    price: float = 0
    currency: str = "MXN"
    preparation: str = ""
    restrictions: str = ""
    availability: dict[str, Any] = Field(default_factory=dict)
    photos: list[str] = Field(default_factory=list)
    associated_staff: str | None = None
    branch: str | None = None
    status: Literal["draft", "active", "paused"] = "active"


class MediaAssetRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    product_id: str | None = None
    service_id: str | None = None
    promotion_id: str | None = None
    asset_type: Literal["image", "video", "pdf", "banner", "menu", "logo"] = "image"
    file_name: str
    file_url: str
    mime_type: str | None = None
    file_size: int = 0
    format: str | None = None
    alt_text: str = ""
    label: str = ""
    category: str = ""
    usage_scope: str = "general"
    preview_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    is_active: bool = True


class CatalogPromotionRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    name: str
    promo_type: Literal["discount", "2x1", "bundle", "gift", "free_shipping", "upgrade"] = "discount"
    message_short: str = ""
    message_long: str = ""
    banner_asset_id: str | None = None
    applies_to: dict[str, Any] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=lambda: ["whatsapp"])
    starts_at: str | None = None
    ends_at: str | None = None
    stock_limit: int | None = None
    branch: str | None = None
    priority: int = 50
    cta_label: str | None = None
    cta_url: str | None = None
    legal_terms: str | None = None
    promo_code: str | None = None
    status: Literal["draft", "active", "paused", "expired"] = "draft"
    auto_offer_enabled: bool = True


class PromotionRuleRequest(BaseModel):
    organization_id: str
    promotion_id: str
    name: str
    trigger_type: Literal["intent_and_score", "inventory_push", "returning_customer", "post_no_purchase"] = "intent_and_score"
    conditions: dict[str, Any] = Field(default_factory=dict)
    action: dict[str, Any] = Field(default_factory=dict)
    priority: int = 50
    is_active: bool = True


class CustomerExperiencePreviewRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    query: str
    conversation_id: str | None = None
    contact_id: str | None = None
    source_channel: Literal["whatsapp", "instagram_dm", "webchat"] = "whatsapp"
