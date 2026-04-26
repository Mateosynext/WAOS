from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ...config import settings

Intensity = Literal["conservative", "balanced", "aggressive", "savage", "godmode"]
_SAFE_INTENSITIES = {"conservative", "balanced", "aggressive", "savage"}
_ALL_INTENSITIES = {*_SAFE_INTENSITIES, "godmode"}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "si", "sí"}
    return False


def _clean_intensity(value: Any) -> str:
    if value is None:
        return "balanced"
    cleaned = str(value).strip().lower()
    return cleaned or "balanced"


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
    requested_intensity: str | None = Field(default=None, max_length=40)
    safety_warnings: list[str] = Field(default_factory=list, max_length=20)
    auto_generate_knowledge: bool = True
    auto_generate_templates: bool = True
    auto_generate_tools: bool = True
    auto_run_simulations: bool = True
    auto_autofix: bool = True
    auto_prepare_go_live: bool = True
    auto_apply: bool = False
    max_cost_usd: float | None = Field(default=None, ge=0, le=250)

    @model_validator(mode="before")
    @classmethod
    def _normalize_feature_gates(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        normalized = dict(data)
        warnings: list[str] = []

        raw_intensity = _clean_intensity(normalized.get("intensity", "balanced"))
        requested_intensity = _clean_intensity(normalized.get("requested_intensity") or raw_intensity)
        effective_intensity = raw_intensity

        if raw_intensity not in _ALL_INTENSITIES:
            effective_intensity = "balanced"
            warnings.append("invalid_intensity_downgraded_to_balanced")
        elif raw_intensity == "godmode" and not settings.ai_enable_godmode:
            effective_intensity = "savage"
            warnings.append("godmode_disabled_downgraded_to_savage")

        # AI Production Autopilot may prepare a release, but creation must remain
        # human-gated. Do not reject a stale/mutated client payload; normalize it.
        if _truthy(normalized.get("auto_apply")):
            normalized["auto_apply"] = False
            warnings.append("auto_apply_disabled_for_autopilot_start")

        existing_warnings = normalized.get("safety_warnings")
        if isinstance(existing_warnings, list):
            warnings.extend(str(item)[:120] for item in existing_warnings if item)

        normalized["intensity"] = effective_intensity
        normalized["requested_intensity"] = requested_intensity
        normalized["safety_warnings"] = list(dict.fromkeys(warnings))[:20]
        return normalized

    @field_validator("intensity")
    @classmethod
    def _validate_intensity(cls, value: str) -> str:
        # The before-validator normalizes untrusted client values into a safe
        # supported intensity. This fallback keeps the field JSON-safe even if a
        # future caller bypasses that pre-normalization path.
        return value if value in _ALL_INTENSITIES else "balanced"

    @field_validator("organization_id", "bot_id", "vertical_id", "subvertical", "primary_objective", mode="before")
    @classmethod
    def _strip_empty(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, Mapping):
            # Some frontend selectors/cookies can accidentally serialize an
            # unselected optional id as `{}`. Treat empty objects as unset and
            # recover common object-shaped ids (`{ id }`, `{ bot_id }`, `{ value }`).
            for key in ("id", "bot_id", "organization_id", "value"):
                candidate = value.get(key)
                if isinstance(candidate, str):
                    cleaned = candidate.strip()
                    if cleaned:
                        return cleaned
                elif isinstance(candidate, (int, float, bool)):
                    return str(candidate)
            return None if not value else value
        return value

    @model_validator(mode="after")
    def _validate_safe_state(self) -> "BotAutopilotRequest":
        # Defense in depth: the before-validator should have downgraded this.
        # Keeping the invariant here prevents accidental future regressions.
        if self.intensity == "godmode" and not settings.ai_enable_godmode:
            self.intensity = "savage"  # type: ignore[assignment]
            self.requested_intensity = self.requested_intensity or "godmode"
            if "godmode_disabled_downgraded_to_savage" not in self.safety_warnings:
                self.safety_warnings.append("godmode_disabled_downgraded_to_savage")
        if self.auto_apply:
            self.auto_apply = False
            if "auto_apply_disabled_for_autopilot_start" not in self.safety_warnings:
                self.safety_warnings.append("auto_apply_disabled_for_autopilot_start")
        return self

    @property
    def effective_intensity(self) -> str:
        return self.intensity


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
