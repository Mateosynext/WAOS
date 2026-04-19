from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.knowledge_ingestion_service import knowledge_ingestion_service
from ...schemas import KnowledgeSourceSyncRequest, KnowledgeSourceUpsertRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["knowledge_ingestion"])


@router.get("/api/v1/knowledge/sources")
def list_knowledge_sources(
    organization_id: str = Query(...),
    bot_id: str | None = Query(default=None),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return knowledge_ingestion_service.list_sources(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.post("/api/v1/knowledge/sources")
def register_knowledge_source(payload: KnowledgeSourceUpsertRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return knowledge_ingestion_service.register_source(uow, payload=payload, user=user)


@router.post("/api/v1/knowledge/sources/{source_connection_id}/sync")
def sync_knowledge_source(source_connection_id: str, payload: KnowledgeSourceSyncRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return knowledge_ingestion_service.sync_source(uow, source_connection_id=source_connection_id, payload=payload, user=user)


@router.get("/api/v1/knowledge/sources/{source_connection_id}/runs")
def list_knowledge_source_runs(
    source_connection_id: str,
    organization_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = None,
    uow: CurrentUoW = None,
) -> dict[str, Any]:
    return knowledge_ingestion_service.list_runs(uow, organization_id=organization_id, source_connection_id=source_connection_id, limit=limit, user=user)
