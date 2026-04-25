from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DocumentType = Literal["quote", "work_order", "receipt", "proposal", "warranty"]
DocumentStatus = Literal[
    "draft",
    "requires_data",
    "requires_approval",
    "approved",
    "sent",
    "viewed",
    "accepted",
    "rejected",
    "expired",
    "paid",
    "converted",
    "completed",
    "cancelled",
]


class OrganizationBrandingRequest(BaseModel):
    organization_id: str
    business_name: str = ""
    legal_name: str | None = None
    logo_url: str | None = None
    primary_color: str = "#25D366"
    secondary_color: str = "#111827"
    phone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    footer_note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommercialDocumentItemRequest(BaseModel):
    source_type: Literal["product", "service", "custom", "fee", "discount"] = "custom"
    source_id: str | None = None
    name: str
    description: str = ""
    quantity: float = 1
    unit: str = "unidad"
    unit_price: float = 0
    discount: float = 0
    tax: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommercialDocumentCreateRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    template_id: str | None = None
    document_type: DocumentType = "quote"
    status: DocumentStatus = "draft"
    title: str = "Presupuesto comercial"
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    customer_address: str | None = None
    summary: str = ""
    currency: str = "MXN"
    valid_until: str | None = None
    deposit_required: float = 0
    payment_url: str | None = None
    terms: str = ""
    notes: str = ""
    missing_questions: list[str] = Field(default_factory=list)
    approval_reasons: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    items: list[CommercialDocumentItemRequest] = Field(default_factory=list)


class CommercialDocumentDraftRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    request_text: str = ""
    document_type: DocumentType = "quote"
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    customer_address: str | None = None
    catalog_item_ids: list[str] = Field(default_factory=list)
    preferred_option_count: int = 1
    auto_generate_pdf: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommercialDocumentStatusUpdateRequest(BaseModel):
    status: DocumentStatus
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommercialDocumentPdfRequest(BaseModel):
    regenerate: bool = False

class CatalogQuoteRuleRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    catalog_item_type: Literal["product", "service"]
    catalog_item_id: str
    pricing_model: Literal["fixed", "hourly", "per_hour", "per_visit", "home_service", "m2", "per_unit", "package", "variable", "from", "custom"] = "fixed"
    unit_label: str = "unidad"
    base_price: float | None = None
    minimum_quantity: float = 1
    travel_fee: float = 0
    urgency_modifier_percent: float = 0
    deposit_percent: float = 0
    required_questions: list[str] = Field(default_factory=list)
    approval_rules: dict[str, Any] = Field(default_factory=dict)
    terms: str | None = None
    is_active: bool = True


class CommercialDocumentSendRequest(BaseModel):
    message_body: str | None = None
    create_payment: bool = True


class CommercialDocumentAcceptRequest(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommercialDocumentPaymentRequest(BaseModel):
    amount_mode: Literal["deposit", "balance", "total"] = "deposit"
