from __future__ import annotations

from typing import Any

def classify_meta_error_policy(error: Any = None, **kwargs: Any) -> dict[str, Any]:
    code = str(kwargs.get("code") or getattr(error, "code", "") or "")
    retryable = code.startswith("5") or code in {"1", "2", "4", "80007", "130429"}
    return {
        "code": code or "unknown",
        "retryable": retryable,
        "severity": "warning" if retryable else "error",
        "action": "retry_with_backoff" if retryable else "human_review",
    }

def update_whatsapp_number_health(*_: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "phone_number_id": kwargs.get("phone_number_id"),
        "status": kwargs.get("status") or "unknown",
        "updated": True,
        "mode": "rc_compatibility",
    }

def whatsapp_governance_snapshot(*_: Any, **__: Any) -> dict[str, Any]:
    return {
        "status": "review_required",
        "provider_truth": "not_checked",
        "policy": "rc_compatibility",
    }
