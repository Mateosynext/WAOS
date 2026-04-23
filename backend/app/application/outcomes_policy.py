from __future__ import annotations

from typing import Any


def guardrail_state(*, traffic_count: int, metrics: dict[str, Any]) -> str:
    if metrics["negative_outcomes"] >= max(2, metrics["positive_outcomes"] + 1):
        return "fail"
    if traffic_count < 3:
        return "warn"
    return "pass"


def recommendation(*, outcome_score: float, confidence_score: float, guardrail_state_value: str) -> str:
    if guardrail_state_value == "fail":
        return "rollback"
    if confidence_score < 45:
        return "hold"
    if outcome_score >= 8:
        return "scale"
    if outcome_score > 0:
        return "iterate"
    return "rollback"
