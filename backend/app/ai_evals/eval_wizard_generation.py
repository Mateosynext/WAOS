from __future__ import annotations

from backend.app.ai_evals.harness import EvalCase, evaluate_cases, flatten_text, ok
from backend.app.ai_platform.prompts.registry import get_prompt
from backend.app.ai_workflows.bot_autopilot.vertical_intelligence import build_vertical_intelligence_pack, detect_vertical
from backend.app.ai_workflows.knowledge_plan.generator import generate_knowledge_plan
from backend.app.ai_workflows.tool_plan.generator import generate_tool_execution_plan


def _candidate(text: str) -> dict:
    profile = detect_vertical(text)
    vertical_pack = build_vertical_intelligence_pack(profile)
    business_profile = {"business_name": "Demo", "vertical_id": profile.get("vertical_id"), "services": ["valoración"], "prices": []}
    knowledge_plan = generate_knowledge_plan(vertical_pack, business_profile)
    tool_plan = generate_tool_execution_plan(vertical_pack, business_profile)
    prompt = get_prompt("wizard_answers_builder")
    return {"profile": profile, "vertical_pack": vertical_pack, "business_profile": business_profile, "knowledge_plan": knowledge_plan, "tool_plan": tool_plan, "prompt": prompt.__dict__}


def _check(actual: dict) -> list:
    text = flatten_text(actual).lower()
    required_facts = set(actual["vertical_pack"].get("required_facts") or [])
    missing_facts = set(actual["knowledge_plan"].get("missing_facts") or [])
    tool_plan_text = flatten_text(actual["tool_plan"]).lower()
    prompt_text = flatten_text(actual["prompt"]).lower()
    return [
        ok("vertical_profile_present", bool(actual["profile"].get("vertical_id")), expected="vertical_id", actual=actual["profile"]),
        ok("required_facts_mapped_to_knowledge_plan", bool(required_facts & missing_facts), expected=sorted(required_facts), actual=sorted(missing_facts), critical=True),
        ok("handoff_required", "destino humano" in text or "handoff" in text, expected="human handoff required", actual=actual, critical=True),
        ok("tool_confirmation_required", "confirm" in tool_plan_text or "confirmation" in tool_plan_text, expected="confirmation in tool execution plan", actual=actual["tool_plan"], critical=True),
        ok("prompt_json_only", actual["prompt"].get("json_only") is True, expected=True, actual=actual["prompt"].get("json_only")),
        ok("prompt_prohibits_invention", all(token in prompt_text for token in ["prices", "legal", "medical"]), expected="prompt safety rules mention prices/legal/medical", actual=actual["prompt"], critical=True),
    ]


CASES = [
    EvalCase("dental_wizard_candidate", "wizard_generation", {"text": "clínica dental con agenda"}, {"required_facts": True}, lambda: _candidate("clínica dental con agenda"), _check, critical=True),
    EvalCase("generic_wizard_candidate", "wizard_generation", {"text": "servicio local"}, {"required_facts": True}, lambda: _candidate("servicio local"), _check),
]


def run_eval() -> dict:
    return evaluate_cases("eval_wizard_generation", CASES, min_score=0.95)
