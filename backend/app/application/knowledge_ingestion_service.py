from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..db import fetch_one
from ..job_idempotency import begin_job_execution, mark_job_completed
from ..live_knowledge_runtime import (
    list_knowledge_source_connections,
    list_knowledge_source_runs,
    run_knowledge_source_sync,
    upsert_knowledge_source_connection,
)
from ..repositories import get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..utils import from_json, hash_value, to_json
from .support import require_permission
from .uow import UnitOfWork


class KnowledgeIngestionService:
    def register_source(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "integration.manage")
        bot = get_bot(uow.conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != payload.organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        row = upsert_knowledge_source_connection(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            source_key=payload.source_key,
            connector_key=payload.connector_key,
            label=payload.label,
            source_uri=payload.source_uri,
            owner_user_id=payload.owner_user_id,
            watch_mode=payload.watch_mode,
            sync_interval_minutes=payload.sync_interval_minutes,
            publish_policy=payload.publish_policy,
            validation_policy=payload.validation_policy,
            config=payload.config,
            metadata=payload.metadata,
        )
        uow.commit()
        return ok(
            {
                "source": {
                    **row,
                    "validation_policy": payload.validation_policy,
                    "config": payload.config,
                    "metadata": payload.metadata,
                }
            }
        )

    def list_sources(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        items = list_knowledge_source_connections(uow.conn, organization_id=organization_id, bot_id=bot_id)
        return ok({"items": items, "count": len(items)})

    def sync_source(self, uow: UnitOfWork, *, source_connection_id: str, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "integration.manage")
        source = fetch_one(uow.conn, "SELECT * FROM knowledge_source_connections WHERE id = ?", (source_connection_id,))
        if not source:
            raise HTTPException(status_code=404, detail="Knowledge source not found")
        if source.get("organization_id") != payload.organization_id:
            raise HTTPException(status_code=403, detail="Knowledge source does not belong to organization")
        if source.get("bot_id"):
            bot = get_bot(uow.conn, source["bot_id"])
            if bot:
                ensure_bot_access(user, bot)
        sync_payload = {"source_connection_id": source_connection_id, "trigger_kind": payload.trigger_kind, "items": payload.items, "full_refresh": payload.full_refresh, "validate_only": payload.validate_only}
        request_key = str((payload.metadata or {}).get("idempotency_key") or hash_value(to_json(sync_payload)))
        job_key = f"knowledge:sync:{payload.organization_id}:{source_connection_id}:{request_key}"
        claim = begin_job_execution(uow.conn, job_type="knowledge:sync", dedupe_key=job_key, payload=sync_payload)
        if claim.get("_payload_mismatch"):
            raise HTTPException(status_code=409, detail="knowledge_sync_idempotency_key_payload_mismatch")
        if claim.get("_already_existing") and claim.get("status") == "running":
            raise HTTPException(status_code=409, detail="knowledge_sync_already_running")
        if claim.get("status") == "completed":
            return ok({**from_json(claim.get("result_json"), {}), "idempotent": True})
        result = run_knowledge_source_sync(
            uow.conn,
            source_connection_id=source_connection_id,
            trigger_kind=payload.trigger_kind,
            items=payload.items,
            full_refresh=payload.full_refresh,
            validate_only=payload.validate_only,
            metadata={**payload.metadata, "idempotency_key": request_key},
        )
        mark_job_completed(uow.conn, dedupe_key=job_key, result=result)
        uow.commit()
        return ok(result)

    def list_runs(self, uow: UnitOfWork, *, organization_id: str, source_connection_id: str, limit: int, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        source = fetch_one(uow.conn, "SELECT * FROM knowledge_source_connections WHERE id = ?", (source_connection_id,))
        if not source:
            raise HTTPException(status_code=404, detail="Knowledge source not found")
        if source.get("organization_id") != organization_id:
            raise HTTPException(status_code=403, detail="Knowledge source does not belong to organization")
        items = list_knowledge_source_runs(uow.conn, source_connection_id=source_connection_id, limit=limit)
        return ok({"items": items, "count": len(items)})


knowledge_ingestion_service = KnowledgeIngestionService()
