from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MarketplacePackagePublishRequest(BaseModel):
    package_type: Literal["vertical", "playbook", "onboarding_pack", "prompt_pack", "automation_pack"] = "vertical"
    package_slug: str | None = None
    title: str = Field(min_length=1, max_length=140)
    summary: str = Field(default="", max_length=1000)
    version: str = Field(min_length=1, max_length=40)
    vertical_key: str | None = None
    subvertical: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)
    compatibility: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[Any] = Field(default_factory=list)
    checklist: list[Any] = Field(default_factory=list)
    metrics_expected: dict[str, Any] = Field(default_factory=dict)
    monetization_model: str = "internal"
    price_amount: float = 0
    currency: str = "USD"
    release_notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "published"


class MarketplaceInstallRequest(BaseModel):
    organization_id: str
    bot_id: str | None = None
    package_id: str | None = None
    package_slug: str | None = None
    version: str | None = None
    install_scope: str = "organization"
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketplaceUpgradeRequest(BaseModel):
    organization_id: str
    target_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
