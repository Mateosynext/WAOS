from __future__ import annotations

import json
from typing import Any


def to_sse(event: dict[str, Any]) -> str:
    """Serialize a workflow event for browser EventSource clients.

    The UI consumes progress through EventSource.onmessage. If every domain
    event is emitted as a custom SSE event name, browsers will not deliver it to
    onmessage unless the client registers every possible event type. Keep the
    semantic type inside the JSON payload as event_type and use the default SSE
    message channel on the wire so new workflow event types keep working.
    """
    event_id = str(event.get("id") or "")
    payload = json.dumps(event, ensure_ascii=False, default=str)
    lines = ["retry: 2500"]
    if event_id:
        lines.append(f"id: {event_id}")
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"
