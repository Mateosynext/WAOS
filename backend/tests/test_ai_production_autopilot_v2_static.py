from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def read(path: str) -> str: return (ROOT / path).read_text(encoding="utf-8")

def test_v2_autopilot_is_async_streamed_and_backgrounded() -> None:
    api = read("backend/app/api/routers/ai_workflows.py")
    service = read("backend/app/ai_workflows/bot_autopilot/service.py")
    assert "BackgroundTasks" in api
    assert "async_mode: bool = Query(True)" in api
    assert "background_tasks.add_task(run_bot_autopilot_background" in api
    assert "time.sleep(0.25)" in api
    assert "TERMINAL" in api
    assert "start_bot_autopilot_run" in service
    assert "execute_bot_autopilot_run" in service
    assert "run_bot_autopilot_background" in service


def test_v2_persists_artifacts_costs_confirmations_and_reports() -> None:
    service = read("backend/app/ai_workflows/bot_autopilot/service.py")
    persistence = read("backend/app/ai_workflows/persistence.py")
    for fn in ["record_cost", "save_json_artifact", "save_simulation_report", "save_go_live_readiness", "upsert_human_confirmation", "list_human_confirmations"]:
        assert f"def {fn}" in persistence
        assert fn in service or fn in read("backend/app/api/routers/ai_workflows.py")
    for table in ["agent_policy_packs", "knowledge_grounding_plans", "whatsapp_production_packs", "tool_execution_plans", "simulation_reports", "go_live_readiness_reports", "human_confirmation_items", "ai_cost_ledger"]:
        assert table in persistence


def test_v2_apply_requires_explicit_confirmation_and_readiness() -> None:
    api = read("backend/app/api/routers/ai_workflows.py")
    assert "explicit_confirmation_required" in api
    assert "payload.get(\"confirm\") is not True" in api
    assert "readiness_blocked" in api
    assert "/api/v1/ai/workflows/{run_id}/human-confirmations" in api
    assert "go_live_readiness.completed" in api


def test_frontend_consumes_streamed_final_payload_and_no_fake_timers() -> None:
    center = read("frontend/features/ai-command-center/AiCommandCenter.tsx")
    stream = read("frontend/features/ai-command-center/useAiWorkflowStream.ts")
    assistant = read("frontend/features/bot-studio/create/AiSetupAssistant.tsx")
    assert "streamedResult" in center
    assert "workflow.completed_partial" in stream
    assert "EventSource" in stream
    assert "setTimeout" not in assistant
