from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import settings

GLOBAL_SETTINGS_PATH = Path(__file__).resolve().parent / "global_settings.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def default_global_settings() -> dict[str, Any]:
    return {
        "global_policy": "No inventar precios, políticas ni disponibilidad.",
        "default_model": settings.openai_model,
        "freeze_minutes_after_takeover": 30,
        "ai_optimization": {
            "semantic_cache_similarity_classification": 0.96,
            "semantic_cache_similarity_generation": 0.94,
            "prompt_char_budget_classification": 2200,
            "prompt_char_budget_generation": 2600,
            "streaming_enabled": True,
            "micro_batch_enabled": True,
            "micro_batch_window_seconds": 45,
            "micro_batch_max_messages": 4,
            "knowledge_search_cache_ttl_seconds": 21600,
            "faq_instant_match_threshold": 0.9,
            "fast_model": "gpt-4o-mini",
            "complex_model": settings.openai_model,
        },
        "memory_runtime": {
            "episodic_memory_enabled": True,
            "cross_bot_intelligence_enabled": True,
            "checkpoint_every_n_messages": 6,
            "checkpoint_min_chars": 900,
            "session_window_hours": 72,
            "episode_search_limit": 5,
            "summarize_every_n_messages": 6,
        },
    }


def read_global_settings() -> dict[str, Any]:
    defaults = default_global_settings()
    if not GLOBAL_SETTINGS_PATH.exists():
        GLOBAL_SETTINGS_PATH.write_text(json.dumps(defaults, indent=2, ensure_ascii=False), encoding="utf-8")
        return defaults
    try:
        current = json.loads(GLOBAL_SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        current = {}
    merged = _deep_merge(defaults, current if isinstance(current, dict) else {})
    if merged != current:
        GLOBAL_SETTINGS_PATH.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return merged


def write_global_settings(data: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(default_global_settings(), data)
    GLOBAL_SETTINGS_PATH.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return merged


def ai_optimization_settings() -> dict[str, Any]:
    return dict(read_global_settings().get("ai_optimization") or {})


def memory_runtime_settings() -> dict[str, Any]:
    return dict(read_global_settings().get("memory_runtime") or {})
