from __future__ import annotations

from backend.app.ai_evals.harness import EvalCase, evaluate_cases, flatten_text, ok
from backend.app.ai_workflows.agent_policy_pack.generator import AGENTS, generate_agent_policy_pack
from backend.app.ai_workflows.bot_autopilot.vertical_intelligence import build_vertical_intelligence_pack, detect_vertical


def _pack(text: str) -> dict:
    vertical_pack = build_vertical_intelligence_pack(detect_vertical(text))
    return generate_agent_policy_pack(vertical_pack, intensity="balanced")


def _check_policy_pack(actual: dict) -> list:
    agents = actual.get("agents") or []
    by_key = {agent.get("agent_key"): agent for agent in agents}
    flattened = flatten_text(actual).lower()
    assertions = [
        ok("all_required_agents", set(AGENTS) <= set(by_key), expected=AGENTS, actual=sorted(by_key), critical=True),
        ok("policy_version", actual.get("policy_version") == "agent_policy_pack.v1", expected="agent_policy_pack.v1", actual=actual.get("policy_version")),
    ]
    for key in ["sales", "booking", "support", "collections"]:
        agent = by_key.get(key, {})
        allowed = set(agent.get("allowed_actions") or [])
        forbidden = flatten_text(agent.get("forbidden_actions") or []).lower()
        confirmations = set(agent.get("confirmation_required_actions") or [])
        assertions.extend([
            ok(f"{key}_handoff_allowed", "handoff_to_human" in allowed, expected="handoff_to_human", actual=sorted(allowed), critical=key in {"booking", "sales"}),
            ok(f"{key}_forbids_invention", "inventar" in forbidden, expected="inventar* in forbidden_actions", actual=agent.get("forbidden_actions"), critical=True),
            ok(f"{key}_requires_confirmation", bool(confirmations & {"book_appointment", "create_payment_link", "reschedule"}), expected="dangerous tools require confirmation", actual=sorted(confirmations), critical=key in {"booking", "collections"}),
        ])
    assertions.append(ok("risk_phrases_carried", any(token in flattened for token in ["diagnóstico", "garantizados", "certificaciones no confirmadas", "resultado físico garantizado", "condición médica"]), expected="vertical risk phrases in policy", actual=actual, critical=True))
    return assertions


CASES = [
    EvalCase("dental_policy_pack", "policy", {"text": "dentista con dolor y agenda"}, {"agents": AGENTS}, lambda: _pack("dentista dental con agenda y dolor fuerte"), _check_policy_pack, critical=True),
    EvalCase("fitness_policy_pack", "policy", {"text": "fitness membresías"}, {"agents": AGENTS}, lambda: _pack("gym fitness membresias y lesiones"), _check_policy_pack),
]


def run_eval() -> dict:
    return evaluate_cases("eval_agent_policy_pack", CASES, min_score=0.94)
