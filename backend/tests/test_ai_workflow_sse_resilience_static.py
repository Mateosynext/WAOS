from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_sse_events_use_default_message_channel_for_eventsource_onmessage():
    events_py = read("app/ai_workflows/events.py")
    assert "def to_sse" in events_py
    assert "event_type" in events_py
    assert "event: {event_type}" not in events_py
    assert "event: workflow.event" not in events_py
    assert "data:" in events_py


def test_workflow_events_keepalive_and_connection_headers():
    router = read("app/api/routers/ai_workflows.py")
    assert "last_event_id" in router
    assert "workflow.keepalive" in router
    assert "Connection" in router and "keep-alive" in router
    assert "X-Accel-Buffering" in router
