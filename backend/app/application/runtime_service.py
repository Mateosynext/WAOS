from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from ..contracts import dead_letter_row, ok
from ..db import execute, fetch_all, fetch_one
from ..observability import capture_message
from ..platform import compute_observability_overview, list_runtime_callbacks, queue_overview, scheduler_overview
from ..repositories import create_audit_log, get_bot
from ..security import ensure_bot_access, ensure_org_access
from ..services import bot_health_summary, integration_health_summary, runtime_overview
from ..utils import from_json, utcnow_iso
from .support import require_permission
from .uow import UnitOfWork


class RuntimeService:
    def runtime_overview(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        return runtime_overview(uow.conn, organization_id=organization_id, bot_id=bot_id)

    def bot_health(self, uow: UnitOfWork, *, bot_id: str, organization_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        bot = get_bot(uow.conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if bot["organization_id"] != organization_id:
            raise HTTPException(status_code=403, detail="Bot does not belong to organization")
        ensure_bot_access(user, bot)
        return ok(bot_health_summary(uow.conn, organization_id=organization_id, bot_id=bot_id))

    def integrations_health(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        return ok(integration_health_summary(uow.conn, organization_id=organization_id, bot_id=bot_id))

    def observability_overview(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        if bot_id:
            bot = get_bot(uow.conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if organization_id and bot["organization_id"] != organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)
        return compute_observability_overview(uow.conn, organization_id=organization_id, bot_id=bot_id)

    def frontend_errors(self, *, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        message = str(payload.get("message") or "frontend error")
        capture_message(
            message,
            level="error",
            source=str(payload.get("source") or "frontend"),
            request_id=getattr(request.state, "request_id", None),
            organization_id=payload.get("organization_id") or getattr(request.state, "organization_id", None),
            bot_id=payload.get("bot_id") or getattr(request.state, "bot_id", None),
            user_id=payload.get("user_id") or getattr(request.state, "user_id", None),
            path=payload.get("path"),
            digest=payload.get("digest"),
        )
        return {"ok": True, "request_id": getattr(request.state, "request_id", None)}

    def runtime_queue(self, uow: UnitOfWork, *, organization_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "scheduler.read")
        return queue_overview(uow.conn, organization_id)

    def runtime_scheduler(self, uow: UnitOfWork, *, organization_id: str | None, user: dict) -> dict[str, Any]:
        if organization_id:
            ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "runs.read")
        return scheduler_overview(uow.conn, organization_id=organization_id)

    def runtime_callbacks(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> list[dict[str, Any]]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "runs.read")
        if bot_id:
            bot = get_bot(uow.conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if bot["organization_id"] != organization_id:
                raise HTTPException(status_code=403, detail="Bot does not belong to organization")
            ensure_bot_access(user, bot)
        return list_runtime_callbacks(uow.conn, organization_id=organization_id, bot_id=bot_id)

    def list_dead_letters(self, uow: UnitOfWork, *, organization_id: str, kind: str | None, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "operations.read")
        jobs: list[dict[str, Any]] = []
        outbox: list[dict[str, Any]] = []
        if kind in (None, "jobs"):
            jobs = fetch_all(uow.conn, "SELECT * FROM automation_jobs WHERE organization_id = ? AND status = 'dead_letter' ORDER BY created_at DESC LIMIT 100", (organization_id,))
        if kind in (None, "outbox"):
            outbox = fetch_all(uow.conn, "SELECT * FROM outbox_messages WHERE organization_id = ? AND status = 'dead_letter' ORDER BY created_at DESC LIMIT 100", (organization_id,))
        return {
            "jobs": [dead_letter_row(row, channel="job") for row in jobs],
            "outbox": [dead_letter_row(row, channel="outbox") for row in outbox],
        }

    def requeue_dead_letter(self, uow: UnitOfWork, *, kind: str, item_id: str, payload, user: dict) -> dict[str, Any]:
        if kind not in {"jobs", "outbox"}:
            raise HTTPException(status_code=400, detail="Unsupported dead letter kind")
        table = "automation_jobs" if kind == "jobs" else "outbox_messages"
        row = fetch_one(uow.conn, f"SELECT * FROM {table} WHERE id = ?", (item_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Dead letter item not found")
        ensure_org_access(user, row["organization_id"])
        require_permission(user, row["organization_id"], "operations.requeue")
        scheduled_for = payload.scheduled_for or utcnow_iso()
        execute(uow.conn, f"UPDATE {table} SET status = 'retry', scheduled_for = ?, last_error = NULL WHERE id = ?", (scheduled_for, item_id))
        create_audit_log(
            uow.conn,
            organization_id=row["organization_id"],
            actor_user_id=user["id"],
            actor_type="user",
            entity_type=table,
            entity_id=item_id,
            action="dead_letter.requeued",
            metadata={"kind": kind, "scheduled_for": scheduled_for},
        )
        uow.commit()
        return fetch_one(uow.conn, f"SELECT * FROM {table} WHERE id = ?", (item_id,))


runtime_service = RuntimeService()
