from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Assertion:
    name: str
    passed: bool
    expected: Any = None
    actual: Any = None
    critical: bool = False
    details: str = ""


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    category: str
    input: dict[str, Any]
    expected: dict[str, Any]
    run: Callable[[], Any]
    check: Callable[[Any], list[Assertion]]
    critical: bool = False
    notes: str = ""


def ok(name: str, passed: bool, *, expected: Any = None, actual: Any = None, critical: bool = False, details: str = "") -> Assertion:
    return Assertion(name=name, passed=bool(passed), expected=expected, actual=actual, critical=critical, details=details)


def contains(haystack: Any, needles: list[str]) -> bool:
    text = str(haystack or "").lower()
    return any(str(needle).lower() in text for needle in needles)


def contains_all(haystack: Any, needles: list[str]) -> bool:
    text = str(haystack or "").lower()
    return all(str(needle).lower() in text for needle in needles)


def flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(flatten_text(v) for v in value)
    return str(value or "")


def evaluate_cases(name: str, cases: list[EvalCase], *, min_score: float = 0.90, critical_min_score: float = 1.0) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    critical_failures: list[dict[str, Any]] = []
    category_totals: dict[str, int] = defaultdict(int)
    category_passed: dict[str, int] = defaultdict(int)
    assertion_total = 0
    assertion_passed = 0
    critical_total = 0
    critical_passed = 0

    for case in cases:
        try:
            actual = case.run()
            assertions = case.check(actual)
        except Exception as exc:  # pragma: no cover - surfaced in release JSON
            actual = {"raised": type(exc).__name__, "message": str(exc)}
            assertions = [ok("case_execution", False, expected="no exception", actual=actual, critical=True, details=str(exc))]

        case_passed = all(assertion.passed for assertion in assertions)
        category_totals[case.category] += len(assertions)
        assertion_total += len(assertions)
        if case.critical:
            critical_total += 1
            if case_passed:
                critical_passed += 1

        case_failure_items = []
        for assertion in assertions:
            if assertion.passed:
                category_passed[case.category] += 1
                assertion_passed += 1
                continue
            item = {
                "case_id": case.case_id,
                "category": case.category,
                "assertion": assertion.name,
                "expected": assertion.expected,
                "actual": assertion.actual,
                "critical": bool(assertion.critical or case.critical),
                "details": assertion.details,
            }
            failures.append(item)
            case_failure_items.append(item)
            if assertion.critical or case.critical:
                critical_failures.append(item)

        examples.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "critical": case.critical,
                "passed": case_passed,
                "score": round(sum(1 for assertion in assertions if assertion.passed) / max(1, len(assertions)), 4),
                "assertions": [assertion.__dict__ for assertion in assertions],
                "input": case.input,
                "expected": case.expected,
                "actual": actual,
                "failures": case_failure_items,
                "notes": case.notes,
            }
        )

    score = assertion_passed / max(1, assertion_total)
    critical_score = critical_passed / max(1, critical_total) if critical_total else 1.0
    category_scores = {
        category: round(category_passed[category] / max(1, total), 4)
        for category, total in sorted(category_totals.items())
    }
    threshold_failures = []
    if score < min_score:
        threshold_failures.append(
            {
                "case_id": "aggregate",
                "category": "threshold",
                "assertion": "min_score",
                "expected": min_score,
                "actual": round(score, 4),
                "critical": True,
                "details": "aggregate score below release threshold",
            }
        )
    if critical_score < critical_min_score:
        threshold_failures.append(
            {
                "case_id": "aggregate",
                "category": "threshold",
                "assertion": "critical_min_score",
                "expected": critical_min_score,
                "actual": round(critical_score, 4),
                "critical": True,
                "details": "one or more critical cases failed",
            }
        )
    failures.extend(threshold_failures)
    critical_failures.extend([item for item in threshold_failures if item.get("critical")])

    return {
        "name": name,
        "score": round(score, 4),
        "threshold": min_score,
        "critical_score": round(critical_score, 4),
        "critical_threshold": critical_min_score,
        "category_scores": category_scores,
        "total_cases": len(cases),
        "total_assertions": assertion_total,
        "passed_assertions": assertion_passed,
        "failures": failures,
        "critical_failures": critical_failures,
        "passed": not failures,
        "examples": examples,
    }
