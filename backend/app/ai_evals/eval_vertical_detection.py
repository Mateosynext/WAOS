from __future__ import annotations

from backend.app.ai_workflows.bot_autopilot.vertical_intelligence import build_vertical_intelligence_pack, detect_vertical
from backend.app.ai_evals.harness import EvalCase, evaluate_cases, ok


def _case(case_id: str, text: str, expected: dict, *, critical: bool = False) -> EvalCase:
    return EvalCase(
        case_id=case_id,
        category="classification",
        input={"text": text},
        expected=expected,
        critical=critical,
        run=lambda: {"profile": detect_vertical(text), "pack": build_vertical_intelligence_pack(detect_vertical(text))},
        check=lambda actual: [
            ok("vertical_id", actual["profile"].get("vertical_id") == expected["vertical_id"], expected=expected["vertical_id"], actual=actual["profile"].get("vertical_id"), critical=True),
            ok("primary_objective", actual["profile"].get("primary_objective") == expected["primary_objective"], expected=expected["primary_objective"], actual=actual["profile"].get("primary_objective")),
            ok("confidence_floor", float(actual["profile"].get("confidence") or 0) >= expected.get("min_confidence", 0.70), expected=expected.get("min_confidence", 0.70), actual=actual["profile"].get("confidence")),
            ok("risk_intents_present", bool(actual["pack"].get("risk_intents")), expected="non-empty risk_intents", actual=actual["pack"].get("risk_intents")),
            ok("required_facts_present", set(expected.get("required_facts", [])) <= set(actual["pack"].get("required_facts", [])), expected=expected.get("required_facts", []), actual=actual["pack"].get("required_facts", [])),
        ],
    )


CASES = [
    _case("dental_agenda", "Clínica dental de ortodoncia: quiero agenda y valoración", {"vertical_id": "dental", "primary_objective": "agendar", "min_confidence": 0.80, "required_facts": ["precios reales", "destino humano"]}, critical=True),
    _case("fitness_sales", "Gym fitness con membresías mensuales y seguimiento", {"vertical_id": "fitness", "primary_objective": "vender", "min_confidence": 0.80, "required_facts": ["precios reales", "destino humano"]}, critical=True),
    _case("generic_negative", "Tienda local de servicios sin vertical explícita", {"vertical_id": "generic_service", "primary_objective": "vender", "min_confidence": 0.80, "required_facts": ["precios reales", "destino humano"]}),
]


def run_eval() -> dict:
    return evaluate_cases("eval_vertical_detection", CASES, min_score=0.92)
