from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any

MODULES = [
    "eval_wizard_generation",
    "eval_autofix_safety",
    "eval_runtime_reply_safety",
    "eval_simulation_judge",
    "eval_vertical_detection",
    "eval_agent_policy_pack",
    "eval_whatsapp_template_pack",
    "eval_go_live_readiness",
]

LIVE_MODULES = [
    "eval_live_provider_sandbox",
]

DEFAULT_MIN_SCORE = 0.95
DEFAULT_CATEGORY_MIN_SCORE = 0.85


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_baseline(path: str | None) -> dict[str, float]:
    if path and path.lower() in {"none", "off", "disabled"}:
        return {}
    baseline_path = Path(path) if path else Path(__file__).with_name("baseline.json")
    if not baseline_path.exists() and not path:
        return {}
    if not baseline_path.exists():
        raise SystemExit(f"[ai-evals:fail] baseline file not found: {baseline_path}")
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("module_scores"), dict):
        return {str(k): float(v) for k, v in payload["module_scores"].items()}
    if isinstance(payload, dict):
        return {str(k): float(v) for k, v in payload.items()}
    raise SystemExit("[ai-evals:fail] baseline must be a JSON object or contain module_scores")


def _selected_modules() -> list[str]:
    modules = list(MODULES)
    if _env_bool("WAOS_AI_EVAL_LIVE", False) or _env_bool("WAOS_REQUIRE_LIVE_AI_EVALS", False):
        modules.extend(module for module in LIVE_MODULES if module not in modules)
    return modules


def run_all() -> dict[str, Any]:
    min_score = float(os.environ.get("WAOS_AI_EVAL_MIN_SCORE", DEFAULT_MIN_SCORE))
    category_min_score = float(os.environ.get("WAOS_AI_EVAL_CATEGORY_MIN_SCORE", DEFAULT_CATEGORY_MIN_SCORE))
    baseline = _load_baseline(os.environ.get("WAOS_AI_EVAL_BASELINE"))
    selected_modules = _selected_modules()
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    critical_failures: list[dict[str, Any]] = []

    for module_name in selected_modules:
        result = importlib.import_module(f"backend.app.ai_evals.{module_name}").run_eval()
        results.append(result)
        module_score = float(result.get("score") or 0)
        module_failures = list(result.get("failures") or [])
        module_critical = list(result.get("critical_failures") or [])
        failures.extend({"module": module_name, **failure} for failure in module_failures)
        critical_failures.extend({"module": module_name, **failure} for failure in module_critical)

        if module_score < min_score:
            item = {
                "module": module_name,
                "case_id": "aggregate",
                "category": "module_threshold",
                "assertion": "module_min_score",
                "expected": min_score,
                "actual": round(module_score, 4),
                "critical": True,
                "details": "module score below release threshold",
            }
            failures.append(item)
            critical_failures.append(item)

        for category, category_score in (result.get("category_scores") or {}).items():
            if float(category_score) < category_min_score:
                item = {
                    "module": module_name,
                    "case_id": "aggregate",
                    "category": category,
                    "assertion": "category_min_score",
                    "expected": category_min_score,
                    "actual": category_score,
                    "critical": True,
                    "details": "category score below release threshold",
                }
                failures.append(item)
                critical_failures.append(item)

        if module_name in baseline and module_score < baseline[module_name]:
            item = {
                "module": module_name,
                "case_id": "aggregate",
                "category": "regression",
                "assertion": "baseline_score_regression",
                "expected": baseline[module_name],
                "actual": round(module_score, 4),
                "critical": True,
                "details": "score regressed below configured baseline",
            }
            failures.append(item)
            critical_failures.append(item)

    aggregate_score = sum(float(result.get("score") or 0) for result in results) / max(1, len(results))
    module_scores = {str(result.get("name")): float(result.get("score") or 0) for result in results}
    passed = not failures and aggregate_score >= min_score
    if aggregate_score < min_score:
        item = {
            "module": "all",
            "case_id": "aggregate",
            "category": "suite_threshold",
            "assertion": "suite_min_score",
            "expected": min_score,
            "actual": round(aggregate_score, 4),
            "critical": True,
            "details": "AI eval suite score below release threshold",
        }
        failures.append(item)
        critical_failures.append(item)
        passed = False

    return {
        "suite": "waos_ai_evals",
        "score": round(aggregate_score, 4),
        "threshold": min_score,
        "category_threshold": category_min_score,
        "module_scores": module_scores,
        "deterministic_modules": MODULES,
        "live_modules": LIVE_MODULES,
        "selected_modules": selected_modules,
        "failures": failures,
        "critical_failures": critical_failures,
        "passed": passed,
        "results": results,
    }


def main() -> int:
    report = run_all()
    if os.environ.get("WAOS_AI_EVAL_VERBOSE") == "1":
        output = report
    else:
        output = {
            "suite": report["suite"],
            "score": report["score"],
            "threshold": report["threshold"],
            "category_threshold": report["category_threshold"],
            "module_scores": report["module_scores"],
            "selected_modules": report["selected_modules"],
            "failures": report["failures"],
            "critical_failures": report["critical_failures"],
            "passed": report["passed"],
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if not report.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
