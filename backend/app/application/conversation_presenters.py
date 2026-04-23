from __future__ import annotations

from ..contact_intelligence import enrich_conversation_row
from .conversation_policies import queue_role_for_item, sla_for_item


def decorate_conversation_item(item: dict) -> dict:
    item = enrich_conversation_row(item)
    priority_score = min(100, int(item.get("urgency_score") or 0) + int(item.get("lead_score") or 0) + min(20, int(item.get("close_probability") or 0) // 5))
    item["priority_score"] = priority_score
    item["priority_band"] = "critical" if priority_score >= 90 else "high" if priority_score >= 70 else "medium" if priority_score >= 40 else "normal"
    item["next_best_action"] = item.get("lead_best_next_action") or item.get("next_action") or ("Responder con humano" if str(item.get("status") or "").lower() == "human_takeover" else "Enviar siguiente paso" if int(item.get("lead_score") or 0) >= 70 else "Dar seguimiento")
    item["requires_human"] = bool(str(item.get("status") or "").lower() == "human_takeover" or str(item.get("attention_tier") or "").lower() == "owner_now")
    item["attention_class"] = "requires_human" if item["requires_human"] else "follow_up_only" if item.get("followup_at") else "ai_or_operator"
    item["stalled"] = bool(item.get("followup_at") and (item.get("last_outbound_at") or item.get("updated_at")) and str(item.get("status") or "").lower() not in {"closed", "resolved"})
    queue_role, queue_reason = queue_role_for_item(item)
    item["work_queue_role"] = queue_role
    item["work_queue_reason"] = queue_reason
    sla = sla_for_item(item)
    item["sla_status"] = sla["status"]
    item["sla_due_at"] = sla["due_at"]
    item["sla_target_minutes"] = sla["target_minutes"]
    item["sla_overdue_minutes"] = sla["overdue_minutes"]
    return item
