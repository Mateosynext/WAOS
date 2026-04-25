from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Intensity = Literal["conservative", "balanced", "aggressive", "savage", "godmode"]


class BotAutopilotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    organization_id: str = Field(min_length=1, max_length=120)
    bot_id: str | None = Field(default=None, max_length=120)
    user_description: str = Field(min_length=20, max_length=12000)
    vertical_id: str | None = Field(default=None, max_length=120)
    subvertical: str | None = Field(default=None, max_length=120)
    primary_objective: str | None = Field(default="agendar", max_length=160)
    language: str | None = Field(default="es", max_length=16)
    timezone: str | None = Field(default="America/Mexico_City", max_length=80)
    intensity: Intensity = "balanced"
    auto_generate_knowledge: bool = True
    auto_generate_templates: bool = True
    auto_generate_tools: bool = True
    auto_run_simulations: bool = True
    auto_autofix: bool = True
    auto_prepare_go_live: bool = True
    auto_apply: bool = False
    max_cost_usd: float | None = Field(default=None, ge=0, le=250)

    @field_validator("organization_id", "bot_id", "vertical_id", "subvertical", "primary_objective", mode="before")
    @classmethod
    def _strip_empty(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value

    @model_validator(mode="after")
    def _validate_gates(self) -> "BotAutopilotRequest":
        if self.intensity == "godmode" and os.getenv("AI_ENABLE_GODMODE", "false").lower() != "true":
            raise ValueError("godmode requires AI_ENABLE_GODMODE=true")
        if self.auto_apply:
            # The endpoint still requires explicit launch permission later. This guard prevents hidden production changes.
            raise ValueError("auto_apply is disabled for AI Production Autopilot v3; use prepare/apply with human confirmation")
        return self


class BusinessProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business_name: str | None = None
    city: str | None = None
    vertical_id: str
    subvertical: str | None = None
    primary_objective: str
    language: str = "es"
    timezone: str = "America/Mexico_City"
    services: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    facts_to_confirm: list[str] = Field(default_factory=list)


class BotAutopilotResponse(BaseModel):
    run_id: str
    wizard_id: str | None = None
    bot_id: str | None = None
    status: str
    progress: int = 0
    vertical_profile: dict[str, Any] = Field(default_factory=dict)
    business_profile: dict[str, Any] = Field(default_factory=dict)
    wizard: dict[str, Any] = Field(default_factory=dict)
    validation_snapshot: dict[str, Any] = Field(default_factory=dict)
    simulation_report: dict[str, Any] = Field(default_factory=dict)
    agent_policy_pack: dict[str, Any] = Field(default_factory=dict)
    specialist_agents_config: dict[str, Any] = Field(default_factory=dict)
    knowledge_plan: dict[str, Any] = Field(default_factory=dict)
    whatsapp_template_pack: dict[str, Any] = Field(default_factory=dict)
    tool_execution_plan: dict[str, Any] = Field(default_factory=dict)
    go_live_readiness: dict[str, Any] = Field(default_factory=dict)
    human_confirmations: list[dict[str, Any]] = Field(default_factory=list)
    next_action: dict[str, Any] = Field(default_factory=dict)
