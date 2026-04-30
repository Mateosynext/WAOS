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
    preview_execution_id: str | None = None
    confirmation_token: str | None = None
    idempotency_key: str | None = None
    client_request_id: str | None = None
    confirm: bool = True
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
    status: Literal["draft", "active", "paused"] = "draft"
    language: str = "es"
    screens: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    flow_json: dict[str, Any] | None = None
    categories: list[str] = Field(default_factory=list)
    endpoint_uri: str | None = None
    fallback: dict[str, Any] = Field(default_factory=dict)
    runtime_config: dict[str, Any] = Field(default_factory=dict)
    compatibility: dict[str, Any] = Field(default_factory=dict)


class WhatsAppFlowVersionCreateRequest(BaseModel):
    flow_json: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    compatibility: dict[str, Any] = Field(default_factory=dict)
    cloned_from_version_id: str | None = None


class WhatsAppFlowPublishRequest(BaseModel):
    version_id: str | None = None
    register_encryption_public_key: str | None = None


class WhatsAppFlowRollbackRequest(BaseModel):
    target_version_id: str
    register_encryption_public_key: str | None = None


class WhatsAppFlowExecutionRequest(BaseModel):
    conversation_id: str | None = None
    contact_id: str | None = None
    flow_token: str | None = None
    version_id: str | None = None
    client_capabilities: dict[str, Any] = Field(default_factory=dict)
    source: str = "api"
    send_message: bool = False


class WhatsAppFlowRuntimeRequest(BaseModel):
    execution_id: str
    action: Literal["init", "navigate", "next", "submit", "complete"] = "navigate"
    screen_id: str | None = None
    submitted_data: dict[str, Any] = Field(default_factory=dict)
    client_capabilities: dict[str, Any] = Field(default_factory=dict)


class WhatsAppFlowTelemetryRequest(BaseModel):
    execution_id: str | None = None
    event_type: str
    screen_id: str | None = None
    step_index: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class WhatsAppFlowExperimentCreateRequest(BaseModel):
    version_a_id: str
    version_b_id: str
    rollout_percentage: int = 50
    status: Literal["draft", "active", "paused"] = "active"
    note: str | None = None


class WhatsAppTemplateVariableDefinition(BaseModel):
    component: Literal["body", "header"] = "body"
    index: int
    name: str | None = None
    sample: str | None = None


class WhatsAppTemplateVersionSpec(BaseModel):
    language_code: str = "es_MX"
    category: Literal["marketing", "utility", "authentication"] = "utility"
    body_text: str
    header_type: Literal["NONE", "TEXT", "IMAGE", "VIDEO", "DOCUMENT"] = "NONE"
    header_text: str | None = None
    footer_text: str | None = None
    buttons: list[dict[str, Any]] = Field(default_factory=list)
    variables: list[WhatsAppTemplateVariableDefinition] = Field(default_factory=list)
    assets: dict[str, Any] = Field(default_factory=dict)
    sample_values: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    approval_status: Literal["draft", "pending", "approved", "rejected", "paused", "disabled"] = "draft"
    fallback_template_id: str | None = None


class WhatsAppTemplateCreateRequest(BaseModel):
    organization_id: str
    bot_id: str
    name: str
    category: Literal["marketing", "utility", "authentication"] = "utility"
    default_language: str = "es_MX"
    metadata: dict[str, Any] = Field(default_factory=dict)
    fallback_template_id: str | None = None
    version: WhatsAppTemplateVersionSpec


class WhatsAppTemplateVersionCreateRequest(WhatsAppTemplateVersionSpec):
    pass


class WhatsAppTemplateSyncRequest(BaseModel):
    version_id: str | None = None
    action: Literal["publish", "sync", "resubmit"] = "publish"


class WhatsAppTemplateApprovalUpdateRequest(BaseModel):
    version_id: str | None = None
    approval_status: Literal["draft", "pending", "approved", "rejected", "paused", "disabled"]
    rejection_reason: str | None = None
    remote_status: str | None = None
    remote_quality_rating: str | None = None


class WhatsAppTemplateLintRequest(BaseModel):
    name: str
    version: WhatsAppTemplateVersionSpec


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
    promo_type: Literal["discount", "bundle", "seasonal", "launch", "coupon", "upsell"] = "discount"
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
    trigger_type: Literal["keyword", "cart_value", "first_visit", "intent", "schedule", "manual"] = "keyword"
    conditions: dict[str, Any] = Field(default_factory=dict)
    action: dict[str, Any] = Field(default_factory=dict)
    priority: int = 50
    is_active: bool = True


class VerticalSubverticalPackApplyRequest(BaseModel):
    organization_id: str
    bot_id: str
    vertical: str
    subvertical: str | None = None


class CustomerExperiencePreviewRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    query: str
    conversation_id: str | None = None
    contact_id: str | None = None
    source_channel: str = "whatsapp"
