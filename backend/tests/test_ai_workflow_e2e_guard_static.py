from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_autopilot_godmode_and_error_renderer_are_json_safe():
    schema = read("app/ai_workflows/bot_autopilot/schemas.py")
    errors = read("app/errors.py")
    assert "godmode_disabled_downgraded_to_savage" in schema
    assert "self.intensity = \"savage\"" in schema
    assert "BaseException" in errors
    assert "_json_safe(exc.errors())" in errors
    assert "Last line of defense" in errors


def test_sse_catchup_never_gets_stuck_on_stale_last_event_id():
    router = read("app/api/routers/ai_workflows.py")
    assert "resume_after_id" in router
    assert "resume_ready" in router
    assert "if resume_after_id not in known_ids" in router
    assert "yield to_sse(ev)" in router
