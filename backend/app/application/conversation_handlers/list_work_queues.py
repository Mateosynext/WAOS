from __future__ import annotations

from fastapi import HTTPException

from ...config import settings
from ...human_ops_runtime import build_human_reply_suggestion, build_supervisor_console, build_takeover_brief, detect_failed_takeover, qa_scorecard, recommend_ai_reactivation, save_structured_internal_note
from ...contracts import ok
from ...db import fetch_all, fetch_one, table_exists
from ...performance import clamp_limit, clamp_offset
from ...repositories import create_audit_log, create_message, get_bot, get_contact_memory, get_conversation
from ...security import ensure_bot_access, ensure_org_access
from ...serializers import serialize_conversation_details
from ...utils import add_minutes, from_json, new_id, to_json, utcnow_iso
from ...whatsapp import enqueue_manual_whatsapp_message
from ..conversation_presenters import decorate_conversation_item
from ..support import org_filter_sql, require_permission
from ..uow import UnitOfWork


from typing import Any

def handle(service, uow: UnitOfWork, *, user: dict, organization_id: str) -> dict:
    conn = uow.conn
    ensure_org_access(user, organization_id)
    require_permission(user, organization_id, "conversation.manage")
    rows = service._base_list_rows(conn, user=user, organization_id=organization_id, bot_id=None, status=None, sort="priority", limit=500, offset=0)
    buckets: dict[str, dict] = {}
    for row in rows:
        item = service._decorate_item(row)
        bucket = buckets.setdefault(item["work_queue_role"], {"role_key": item["work_queue_role"], "count": 0, "requires_human": 0, "stalled": 0, "sla_breached": 0, "top_priority": 0})
        bucket["count"] += 1
        bucket["requires_human"] += 1 if item.get("requires_human") else 0
        bucket["stalled"] += 1 if item.get("stalled") else 0
        bucket["sla_breached"] += 1 if item.get("sla_status") == "breached" else 0
        bucket["top_priority"] = max(bucket["top_priority"], int(item.get("priority_score") or 0))
    return ok({
        "organization_id": organization_id,
        "queues": sorted(buckets.values(), key=lambda item: (-int(item.get("sla_breached") or 0), -int(item.get("count") or 0), item.get("role_key") or "")),
    })
