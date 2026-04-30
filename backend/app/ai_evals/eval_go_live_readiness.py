from __future__ import annotations

from backend.app.ai_evals.harness import EvalCase, evaluate_cases, ok
from backend.app.ai_workflows.go_live.readiness import evaluate_go_live_readiness

BASE = {
    "wizard": {"id": "wiz_1", "primary_objective": "agendar"},
    "dry_run_result": {"apply_ready": True},
    "validation_snapshot": {"apply_ready": True},
    "simulation_report": {"blocking_failures": []},
    "knowledge_plan": {"missing_facts": []},
    "whatsapp_status": {"configured": True},
    "human_handoff_config": {"destination": "ops@example.com"},
}


def _readiness(**overrides):
    data = dict(BASE)
    data.update(overrides)
    return evaluate_go_live_readiness(**data)


def _check_ready(actual: dict) -> list:
    return [
        ok("ready_status", actual.get("status") == "ready", expected="ready", actual=actual.get("status"), critical=True),
        ok("can_publish", actual.get("can_publish") is True, expected=True, actual=actual.get("can_publish"), critical=True),
        ok("can_apply", actual.get("can_apply") is True, expected=True, actual=actual.get("can_apply")),
    ]


def _check_blocked(blocker: str):
    def check(actual: dict) -> list:
        return [
            ok("blocked_status", actual.get("status") == "blocked", expected="blocked", actual=actual.get("status"), critical=True),
            ok("cannot_publish", actual.get("can_publish") is False, expected=False, actual=actual.get("can_publish"), critical=True),
            ok("blocker_present", blocker in set(actual.get("blockers") or []), expected=blocker, actual=actual.get("blockers"), critical=True),
            ok("next_action_resolve", actual.get("recommended_next_action") == "resolve_blockers", expected="resolve_blockers", actual=actual.get("recommended_next_action")),
        ]
    return check


def _check_confirmations(actual: dict) -> list:
    confirmations = actual.get("human_confirmations_required") or []
    keys = {item.get("field_key") for item in confirmations}
    return [
        ok("not_publishable", actual.get("can_publish") is False, expected=False, actual=actual.get("can_publish"), critical=True),
        ok("confirmation_created", "precio_exacto" in keys or "precio exacto" in keys, expected="precio_exacto confirmation", actual=confirmations, critical=True),
        ok("risk_list_includes_warning", bool(actual.get("production_risks")), expected="non-empty production risks", actual=actual.get("production_risks")),
    ]


CASES = [
    EvalCase("ready_happy_path", "readiness", {}, {"status": "ready"}, lambda: _readiness(), _check_ready, critical=True),
    EvalCase("missing_handoff_blocks", "readiness", {}, {"blocker": "missing_handoff"}, lambda: _readiness(human_handoff_config=None), _check_blocked("missing_handoff"), critical=True),
    EvalCase("simulation_blocks", "readiness", {}, {"blocker": "blocking_simulation_failures"}, lambda: _readiness(simulation_report={"blocking_failures": ["invented_price"]}), _check_blocked("blocking_simulation_failures"), critical=True),
    EvalCase("dry_run_blocks", "readiness", {}, {"blocker": "dry_run_not_apply_ready"}, lambda: _readiness(dry_run_result={"apply_ready": False}, validation_snapshot={"apply_ready": False}), _check_blocked("dry_run_not_apply_ready"), critical=True),
    EvalCase("missing_facts_require_confirmation", "readiness", {}, {"confirmation": "precio_exacto"}, lambda: _readiness(knowledge_plan={"missing_facts": ["precio exacto"]}), _check_confirmations, critical=True),
]


def run_eval() -> dict:
    return evaluate_cases("eval_go_live_readiness", CASES, min_score=0.95)
