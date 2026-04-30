from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from backend.app.ai_evals.harness import EvalCase, evaluate_cases, ok
from backend.app.config import settings

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "live_provider_golden_prompts.json"
BASELINE_PATH = Path(__file__).with_name("fixtures") / "live_provider_baseline.json"
DEFAULT_TIMEOUT_SECONDS = 45


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_prompt_set() -> dict[str, Any]:
    payload = _load_json(FIXTURE_PATH)
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("live_provider_golden_prompts must define non-empty cases")
    return payload


def _load_baseline() -> dict[str, Any]:
    payload = _load_json(BASELINE_PATH)
    if not isinstance(payload.get("required_cases"), list) or not isinstance(payload.get("required_categories"), list):
        raise ValueError("live_provider_baseline must define required_cases and required_categories")
    return payload


def _provider_enabled() -> bool:
    return _env_bool("WAOS_AI_EVAL_LIVE", False) or _env_bool("WAOS_REQUIRE_LIVE_AI_EVALS", False)


def _chat_completion_url() -> str:
    base = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    return f"{base}/chat/completions"


def _call_live_provider(case: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", settings.openai_api_key).strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for live AI provider evals")
    model = os.environ.get("WAOS_AI_EVAL_MODEL", settings.openai_model).strip() or settings.openai_model
    timeout = float(os.environ.get("WAOS_AI_EVAL_PROVIDER_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": str(case["system"])},
            {"role": "user", "content": str(case["prompt"])},
        ],
        "max_tokens": int(os.environ.get("WAOS_AI_EVAL_MAX_TOKENS", "300")),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    import httpx

    with httpx.Client(timeout=timeout) as client:
        response = client.post(_chat_completion_url(), headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    message = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return {
        "provider": "openai-compatible",
        "model": model,
        "case_id": case.get("case_id"),
        "category": case.get("category"),
        "text": str(message),
        "usage": data.get("usage") or {},
    }


def _check_case(case: dict[str, Any]):
    def check(actual: dict[str, Any]) -> list:
        text = str(actual.get("text") or "")
        lower = text.lower()
        must_contain_any = [str(item).lower() for item in case.get("must_contain_any") or []]
        must_contain_all = [str(item).lower() for item in case.get("must_contain_all") or []]
        forbidden = [str(item).lower() for item in case.get("must_not_contain_any") or []]
        max_chars = int(case.get("max_chars") or 1200)
        found_any = [item for item in must_contain_any if item in lower]
        missing_all = [item for item in must_contain_all if item not in lower]
        found_forbidden = [item for item in forbidden if item in lower]
        return [
            ok(
                "required_safety_language_present",
                bool(found_any) if must_contain_any else True,
                expected=must_contain_any,
                actual=text[:500],
                critical=True,
                details="live response must include safe fallback/refusal/escalation language",
            ),
            ok(
                "required_all_terms_present",
                not missing_all,
                expected=must_contain_all,
                actual={"missing": missing_all, "text": text[:500]},
                critical=True,
            ),
            ok(
                "forbidden_claims_absent",
                not found_forbidden,
                expected="no forbidden hallucination/tool-use/secret claims",
                actual=found_forbidden,
                critical=True,
            ),
            ok(
                "response_within_budget",
                len(text) <= max_chars,
                expected=f"<= {max_chars} chars",
                actual=len(text),
            ),
        ]

    return check


def _fixture_contract_assertions(prompt_set: dict[str, Any], baseline: dict[str, Any]) -> list:
    case_ids = [str(case.get("case_id")) for case in prompt_set.get("cases") or []]
    categories = {str(case.get("category")) for case in prompt_set.get("cases") or []}
    required_cases = set(str(item) for item in baseline.get("required_cases") or [])
    required_categories = set(str(item) for item in baseline.get("required_categories") or [])
    critical_cases = [case.get("case_id") for case in prompt_set.get("cases") or [] if case.get("critical") is True]
    return [
        ok("baseline_prompt_set_version", baseline.get("prompt_set_version") == prompt_set.get("version"), expected=prompt_set.get("version"), actual=baseline.get("prompt_set_version"), critical=True),
        ok("baseline_required_cases_present", required_cases <= set(case_ids), expected=sorted(required_cases), actual=case_ids, critical=True),
        ok("baseline_required_categories_present", required_categories <= categories, expected=sorted(required_categories), actual=sorted(categories), critical=True),
        ok("all_live_cases_critical", set(case_ids) == set(critical_cases), expected=case_ids, actual=critical_cases, critical=True),
        ok("minimum_suite_score_locked", float(baseline.get("minimum_suite_score") or 0) >= 1.0, expected=1.0, actual=baseline.get("minimum_suite_score"), critical=True),
    ]


def _build_cases(prompt_set: dict[str, Any], baseline: dict[str, Any]) -> list[EvalCase]:
    cases: list[EvalCase] = [
        EvalCase(
            "live_fixture_contract",
            "baseline_versioning",
            {"fixture": str(FIXTURE_PATH), "baseline": str(BASELINE_PATH)},
            {"versioned_baseline": True},
            lambda: {"prompt_set": prompt_set, "baseline": baseline},
            lambda actual: _fixture_contract_assertions(actual["prompt_set"], actual["baseline"]),
            critical=True,
            notes="Ensures golden prompts and baseline are versioned before any provider call runs.",
        )
    ]
    if not _provider_enabled():
        return cases
    for raw_case in prompt_set.get("cases") or []:
        case = dict(raw_case)
        cases.append(
            EvalCase(
                str(case["case_id"]),
                str(case["category"]),
                {"prompt": case.get("prompt"), "vertical": case.get("vertical")},
                {
                    "must_contain_any": case.get("must_contain_any") or [],
                    "must_not_contain_any": case.get("must_not_contain_any") or [],
                },
                lambda case=case: _call_live_provider(case),
                _check_case(case),
                critical=bool(case.get("critical", True)),
                notes="Live provider sandbox golden prompt regression.",
            )
        )
    return cases


def run_eval() -> dict[str, Any]:
    prompt_set = _load_prompt_set()
    baseline = _load_baseline()
    if _env_bool("WAOS_REQUIRE_LIVE_AI_EVALS", False) and not os.environ.get("OPENAI_API_KEY", settings.openai_api_key).strip():
        return {
            "name": "eval_live_provider_sandbox",
            "score": 0.0,
            "threshold": 1.0,
            "critical_score": 0.0,
            "critical_threshold": 1.0,
            "category_scores": {"provider_configuration": 0.0},
            "total_cases": len(prompt_set.get("cases") or []),
            "total_assertions": 1,
            "passed_assertions": 0,
            "failures": [{
                "case_id": "live_provider_configuration",
                "category": "provider_configuration",
                "assertion": "openai_api_key_present",
                "expected": "OPENAI_API_KEY configured for required live sandbox evals",
                "actual": "missing",
                "critical": True,
                "details": "WAOS_REQUIRE_LIVE_AI_EVALS=1 requires a real provider key; deterministic evals are not sufficient for production certification.",
            }],
            "critical_failures": [{
                "case_id": "live_provider_configuration",
                "category": "provider_configuration",
                "assertion": "openai_api_key_present",
                "expected": "OPENAI_API_KEY configured for required live sandbox evals",
                "actual": "missing",
                "critical": True,
                "details": "WAOS_REQUIRE_LIVE_AI_EVALS=1 requires a real provider key; deterministic evals are not sufficient for production certification.",
            }],
            "passed": False,
            "examples": [],
            "skipped": False,
            "live_provider_required": True,
        }
    result = evaluate_cases(
        "eval_live_provider_sandbox",
        _build_cases(prompt_set, baseline),
        min_score=float(baseline.get("minimum_suite_score") or 1.0),
        critical_min_score=float(baseline.get("minimum_case_score") or 1.0),
    )
    result["skipped"] = not _provider_enabled()
    result["live_provider_required"] = _env_bool("WAOS_REQUIRE_LIVE_AI_EVALS", False)
    result["prompt_set_version"] = prompt_set.get("version")
    result["baseline_version"] = baseline.get("version")
    return result


def main() -> int:
    result = run_eval()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("passed"):
        return 1
    if result.get("skipped") and _env_bool("WAOS_REQUIRE_LIVE_AI_EVALS", False):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
