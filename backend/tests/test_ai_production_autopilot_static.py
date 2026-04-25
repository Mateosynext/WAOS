from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def read(path: str) -> str: return (ROOT / path).read_text(encoding="utf-8")
def test_ai_workflow_engine_tables_and_routes_are_registered() -> None:
    migrations=read("backend/app/migrations.py"); persistence=read("backend/app/ai_workflows/persistence.py"); router=read("backend/app/api/router.py"); api=read("backend/app/api/routers/ai_workflows.py")
    assert "phase32-ai-workflow-engine" in migrations
    for table in ["ai_workflow_runs","ai_workflow_steps","ai_workflow_events","ai_cost_ledger","simulation_reports","go_live_readiness_reports","human_confirmation_items","ai_runtime_turn_inspections","ai_provider_health_snapshots"]: assert table in persistence
    assert "ai_workflows_router" in router
    for route in ["/api/v1/ai/bot-autopilot","/api/v1/ai/workflows/{run_id}","/api/v1/ai/workflows/{run_id}/events","/api/v1/ai/workflows/{run_id}/simulate","/api/v1/ai/workflows/{run_id}/apply","/api/v1/internal/ai-ops/runs"]: assert route in api
def test_autopilot_workflow_contains_required_production_events() -> None:
    service=read("backend/app/ai_workflows/bot_autopilot/service.py")
    for event in ["workflow.started","intent.normalized","vertical.detected","business_profile.generated","wizard.created","vertical_pack.generated","policy_pack.generated","knowledge_plan.generated","whatsapp_pack.generated","tool_plan.generated","dry_run.completed","autofix.round_completed","simulation.completed","go_live_readiness.completed","human_confirmation.required","apply.prepared","workflow.completed"]: assert event in service
    assert "auto_apply" in service and "apply_plan" in service
def test_safety_rules_are_hard_blocking() -> None:
    autofix=read("backend/app/ai_workflows/bot_autopilot/autofix.py"); judge=read("backend/app/ai_workflows/simulation/judge.py"); readiness=read("backend/app/ai_workflows/go_live/readiness.py")
    for forbidden in ["inventar precios","inventar horarios","inventar promociones","inventar integraciones"]: assert forbidden in autofix
    for blocker in ["invented_price","forbidden_medical_claim","missing_urgent_handoff","tool_without_confirmation","opt_out_ignored"]: assert blocker in judge
    assert "blocked" in readiness
def test_platform_model_router_prompt_registry_cost_and_provider_health_exist() -> None:
    for path in ["backend/app/ai_platform/model_router.py","backend/app/ai_platform/provider_health.py","backend/app/ai_platform/cost_governor.py","backend/app/ai_platform/prompts/registry.py","backend/app/ai_workflows/cost_governor.py"]: assert (ROOT/path).exists(), path
    registry=read("backend/app/ai_platform/prompts/registry.py")
    for prompt in ["vertical_detector","wizard_answers_builder","simulation_judge","go_live_readiness","runtime_verifier"]: assert prompt in registry
