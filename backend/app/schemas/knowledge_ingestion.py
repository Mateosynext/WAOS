from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeSourceUpsertRequest(BaseModel):
    organization_id: str
    bot_id: str
    source_key: str
    connector_key: str
    label: str
    source_uri: str | None = None
    owner_user_id: str | None = None
    watch_mode: str = "manual"
    sync_interval_minutes: int = 60
    publish_policy: str = "auto_publish"
    validation_policy: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSourceSyncRequest(BaseModel):
    organization_id: str
    trigger_kind: str = "manual"
    full_refresh: bool = True
    validate_only: bool = False
    items: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
