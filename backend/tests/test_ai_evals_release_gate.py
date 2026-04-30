from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path

from backend.app.ai_evals.run_all import LIVE_MODULES, MODULES, run_all

ROOT = Path(__file__).resolve().parents[2]


def test_ai_eval_suite_blocks_on_real_thresholds() -> None:
    report = run_all()
    assert report["passed"] is True
    assert report["score"] >= report["threshold"]
    assert report["critical_failures"] == []
    assert set(report["module_scores"]) == set(MODULES)
    assert all(score >= 0.95 for score in report["module_scores"].values())


def test_ai_eval_modules_are_not_constant_green_stubs() -> None:
    for module_name in MODULES:
        path = ROOT / "backend" / "app" / "ai_evals" / f"{module_name}.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert "evaluate_cases" in source, f"{module_name} must use the shared assertion harness"
        assert "EvalCase" in source, f"{module_name} must define explicit fixtures"
        assert "critical=True" in source, f"{module_name} must contain critical release-blocking cases"
        for node in ast.walk(tree):
            assert not (
                isinstance(node, ast.FunctionDef)
                and node.name == "run_eval"
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Return)
                and "score" in ast.unparse(node.body[0]).lower()
                and "1.0" in ast.unparse(node.body[0])
                and "failures" in ast.unparse(node.body[0]).lower()
            ), f"{module_name} still looks like a constant green stub"


def test_each_ai_eval_reports_fixtures_and_category_scores() -> None:
    for module_name in MODULES:
        result = importlib.import_module(f"backend.app.ai_evals.{module_name}").run_eval()
        assert result["total_cases"] >= 2
        assert result["total_assertions"] >= result["total_cases"]
        assert result["category_scores"]
        assert all(example["assertions"] for example in result["examples"])


def test_live_provider_eval_contract_is_versioned_and_release_blocking() -> None:
    assert "eval_live_provider_sandbox" in LIVE_MODULES
    fixture_path = ROOT / "backend" / "app" / "ai_evals" / "fixtures" / "live_provider_golden_prompts.json"
    baseline_path = ROOT / "backend" / "app" / "ai_evals" / "fixtures" / "live_provider_baseline.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    cases = fixtures["cases"]
    categories = {case["category"] for case in cases}
    assert fixtures["version"].startswith("live_provider_golden_prompts.v1")
    assert baseline["prompt_set_version"] == fixtures["version"]
    assert baseline["minimum_suite_score"] == 1.0
    assert {case["case_id"] for case in cases} == set(baseline["required_cases"])
    assert set(baseline["required_categories"]) <= categories
    assert {"prompt_injection", "unauthorized_tool_use", "hallucination_prices_hours_certifications", "vertical_fixture_fallback"} <= categories
    assert all(case.get("critical") is True for case in cases)
    assert all(case.get("must_not_contain_any") for case in cases)


def test_live_provider_eval_is_opt_in_but_required_mode_fails_without_provider_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("WAOS_AI_EVAL_LIVE", raising=False)
    monkeypatch.setenv("WAOS_REQUIRE_LIVE_AI_EVALS", "1")
    result = importlib.import_module("backend.app.ai_evals.eval_live_provider_sandbox").run_eval()
    assert result["passed"] is False
    assert result["critical_failures"]
    assert result["critical_failures"][0]["assertion"] == "openai_api_key_present"
