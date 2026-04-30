from __future__ import annotations

from typing import Any

def build_whatsapp_delivery_truth_report(*_: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "status": "review_required",
        "provider_truth": "not_checked",
        "organization_id": kwargs.get("organization_id"),
        "bot_id": kwargs.get("bot_id"),
        "items": [],
        "mode": "rc_compatibility",
    }
