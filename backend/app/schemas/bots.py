from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_string_list(value: Any, *, limit: int = 50, item_limit: int = 240) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Expected a list")
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value[:limit]:
        text = str(item or "").strip()
        if not text:
            continue
        text = text[:item_limit]
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


class FAQItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    q: str = Field(min_length=1, max_length=500)
    a: str = Field(min_length=1, max_length=2000)


class BotCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    organization_id: str = Field(min_length=1, max_length=120)
    business_name: str = Field(min_length=1, max_length=180)
    vertical: str = Field(min_length=1, max_length=120)
    bot_name: str = Field(min_length=1, max_length=120)
    primary_objective: Literal["vender", "calificar", "agendar", "responder", "reactivar"] = "agendar"
    tone: str = Field(default="amable", min_length=1, max_length=80)
    language: str = Field(default="es", min_length=2, max_length=16)
    timezone: str = Field(default="America/Mexico_City", min_length=1, max_length=80)
    services: list[str] = Field(default_factory=list, max_length=50)
    hours: str = Field(default="", max_length=1000)
    faqs: list[FAQItem] = Field(default_factory=list, max_length=50)
    whatsapp_number: str = Field(default="", max_length=40)
    # Backend is the source of truth: when the frontend omits publish_now, creation publishes by default.
    publish_now: bool = True
    client_request_id: str | None = Field(default=None, min_length=8, max_length=160)

    @field_validator("services", mode="before")
    @classmethod
    def _normalize_services(cls, value: Any) -> list[str]:
        return _clean_string_list(value, limit=50, item_limit=180)

    @field_validator("client_request_id", mode="before")
    @classmethod
    def _normalize_client_request_id(cls, value: Any) -> str | None:
        cleaned = str(value or "").strip()[:160]
        return cleaned or None

    @field_validator("whatsapp_number", mode="before")
    @classmethod
    def _normalize_whatsapp(cls, value: Any) -> str:
        return str(value or "").strip()[:40]


class BotCreateWorkflowRequest(BotCreateRequest):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subvertical: str | None = Field(default=None, max_length=120)

    @field_validator("subvertical", mode="before")
    @classmethod
    def _normalize_subvertical(cls, value: Any) -> str | None:
        cleaned = str(value or "").strip()[:120]
        return cleaned or None


class BotUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = Field(default=None, max_length=40)
    ai_paused: bool | None = None
    vertical: str | None = Field(default=None, max_length=120)
    apply_vertical_defaults: bool | None = None
    config_draft: dict[str, Any] | None = None


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    notes: str = Field(default="", max_length=1000)


class CloneBotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_organization_id: str | None = Field(default=None, max_length=120)
    new_name: str | None = Field(default=None, min_length=1, max_length=120)


class BotResponseTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    organization_id: str = Field(min_length=1, max_length=120)
    bot_id: str = Field(min_length=1, max_length=120)
    template_key: Literal["welcome", "out_of_hours", "no_stock", "promotion", "booking", "followup", "handoff", "close_sale", "post_sale", "custom"] = "custom"
    channel: str = Field(default="whatsapp", min_length=1, max_length=80)
    title: str | None = Field(default=None, max_length=180)
    content: str = Field(min_length=1, max_length=4000)
    variables: list[str] = Field(default_factory=list, max_length=100)
    is_active: bool = True

    @field_validator("variables", mode="before")
    @classmethod
    def _normalize_variables(cls, value: Any) -> list[str]:
        return _clean_string_list(value, limit=100, item_limit=80)


class BotBehaviorSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    organization_id: str = Field(min_length=1, max_length=120)
    bot_id: str = Field(min_length=1, max_length=120)
    tone: Literal["formal", "cercano", "vendedor", "premium", "tecnico"] = "cercano"
    response_length: Literal["corta", "media", "detallada"] = "media"
    use_emojis: bool = False
    sales_intensity: Literal["baja", "media", "alta"] = "media"
    offer_promotions_when: str = Field(default="when_relevant", max_length=120)
    escalate_when: list[str] = Field(default_factory=list, max_length=100)
    insistence_policy: str = Field(default="respectful", max_length=120)
    can_share_price_directly: bool = True
    can_negotiate: bool = False
    can_mention_stock: bool = True
    auto_send_images: bool = True
    bot_mode: Literal["bot", "human_only", "hybrid", "schedule_based"] = "hybrid"
    active_hours: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    active_channels: list[str] = Field(default_factory=lambda: ["whatsapp"], max_length=20)
    forbidden_topics: list[str] = Field(default_factory=list, max_length=100)
    required_phrases: list[str] = Field(default_factory=list, max_length=100)
    fallback_message: str = Field(default="Te ayudo con gusto, pero necesito un poco mas de detalle para responderte bien.", max_length=1000)

    @field_validator("escalate_when", "active_channels", "forbidden_topics", "required_phrases", mode="before")
    @classmethod
    def _normalize_lists(cls, value: Any) -> list[str]:
        return _clean_string_list(value, limit=100, item_limit=160)


class BotSimulationCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    organization_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=180)
    scenario_text: str = Field(min_length=1, max_length=4000)
    expected_action: str | None = Field(default=None, max_length=160)
    expected_queue: str | None = Field(default=None, max_length=160)
    expected_must_escalate: bool | None = None
    tags: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: Any) -> list[str]:
        return _clean_string_list(value, limit=50, item_limit=80)


class BotSimulationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    compare_target: Literal["draft", "published", "version"] = "draft"
    case_ids: list[str] = Field(default_factory=list, max_length=100)
    right_version_id: str | None = Field(default=None, max_length=120)

    @field_validator("case_ids", mode="before")
    @classmethod
    def _normalize_case_ids(cls, value: Any) -> list[str]:
        return _clean_string_list(value, limit=100, item_limit=120)


class BotDraftSnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    notes: str = Field(default="", max_length=1000)
