from __future__ import annotations

import hashlib
import json
from typing import Any

def normalize_whatsapp_outbound_request(payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    data = dict(payload or {})
    data.update({k: v for k, v in kwargs.items() if v is not None})
    to = str(data.get("to") or data.get("phone") or data.get("wa_id") or "").strip()
    text = data.get("text") or data.get("message") or data.get("body") or ""
    return {
        "to": to,
        "type": data.get("type") or "text",
        "text": text,
        "template": data.get("template"),
        "metadata": data.get("metadata") or {},
    }

def flatten_whatsapp_webhook_events(payload: dict[str, Any] | None = None, **_: Any) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    payload = payload or {}
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for message in value.get("messages") or []:
                events.append({"kind": "message", "entry_id": entry.get("id"), "value": value, "message": message})
            for status in value.get("statuses") or []:
                events.append({"kind": "status", "entry_id": entry.get("id"), "value": value, "status": status})
    return events

def register_whatsapp_event_receipt(conn=None, *, event: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    raw = json.dumps(event or kwargs, sort_keys=True, ensure_ascii=False)
    return {"id": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32], "duplicate": False, "accepted": True}

def apply_whatsapp_status_event(*_: Any, **kwargs: Any) -> dict[str, Any]:
    return {"applied": True, "status": kwargs.get("status") or kwargs.get("event") or "unknown"}

def apply_whatsapp_provider_error(*_: Any, **kwargs: Any) -> dict[str, Any]:
    return {"applied": True, "error": kwargs.get("error") or kwargs.get("provider_error") or "unknown"}
