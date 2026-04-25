from __future__ import annotations

import json
from typing import Any


def to_sse(event: dict[str, Any]) -> str:
    event_type = str(event.get("event_type") or "workflow.event")
    event_id = str(event.get("id") or "")
    payload = json.dumps(event, ensure_ascii=False, default=str)
    lines = ["retry: 2500"]
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"
