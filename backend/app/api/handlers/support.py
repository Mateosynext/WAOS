from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...config import settings

GLOBAL_SETTINGS_PATH = Path(__file__).resolve().parent / "global_settings.json"


def _default_global_settings() -> dict[str, Any]:
    return {
        "global_policy": "No inventar precios, políticas ni disponibilidad.",
        "default_model": settings.openai_model,
        "freeze_minutes_after_takeover": 30,
    }


def _read_global_settings() -> dict[str, Any]:
    if not GLOBAL_SETTINGS_PATH.exists():
        defaults = _default_global_settings()
        GLOBAL_SETTINGS_PATH.write_text(json.dumps(defaults, indent=2, ensure_ascii=False), encoding="utf-8")
        return defaults
    return json.loads(GLOBAL_SETTINGS_PATH.read_text(encoding="utf-8"))


def _write_global_settings(data: dict[str, Any]) -> dict[str, Any]:
    GLOBAL_SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data
