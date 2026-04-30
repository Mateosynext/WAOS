from __future__ import annotations

from copy import deepcopy
from typing import Any

from .verticals import get_vertical_profile as _base_get_vertical_profile

_SUBVERTICALS: dict[str, dict[str, Any]] = {
    "default": {
        "key": "default",
        "name": "General",
        "capabilities": ["faq", "lead_capture", "handoff"],
        "guardrails": ["no_inventar_precios", "confirmar_datos_criticos"],
    },
    "restaurants": {
        "key": "restaurants",
        "name": "Restaurantes",
        "capabilities": ["reservations", "menu_faq", "delivery_followup"],
        "guardrails": ["no_confirmar_reserva_sin_slot", "confirmar_alergias_si_aplica"],
    },
    "clinics": {
        "key": "clinics",
        "name": "Clínicas",
        "capabilities": ["appointment_intake", "faq", "human_handoff"],
        "guardrails": ["no_diagnosticar", "escalar_urgencias_medicas"],
    },
}

def get_vertical_profile(vertical: str | None = None, **kwargs: Any) -> dict[str, Any]:
    return _base_get_vertical_profile(vertical, **kwargs)

def get_subvertical_profile(subvertical: str | None = None, **_: Any) -> dict[str, Any]:
    key = str(subvertical or "default").strip().lower().replace(" ", "_").replace("-", "_")
    return deepcopy(_SUBVERTICALS.get(key) or _SUBVERTICALS["default"])

def build_strongest_verticals(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return [deepcopy(item) for item in _SUBVERTICALS.values()]

def enrich_vertical_profile_for_runtime(profile: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    result = deepcopy(profile or get_vertical_profile(kwargs.get("vertical")))
    result.setdefault("runtime_capabilities", ["faq", "lead_capture", "handoff"])
    result.setdefault("guardrails", ["no_inventar", "confirmar_datos_criticos"])
    return result

def apply_subvertical_pack(base: dict[str, Any] | None = None, subvertical: str | None = None, **kwargs: Any) -> dict[str, Any]:
    result = deepcopy(base or {})
    pack = get_subvertical_profile(subvertical or kwargs.get("subvertical"))
    result["subvertical"] = pack["key"]
    result.setdefault("capabilities", [])
    for capability in pack.get("capabilities") or []:
        if capability not in result["capabilities"]:
            result["capabilities"].append(capability)
    result.setdefault("guardrails", [])
    for guardrail in pack.get("guardrails") or []:
        if guardrail not in result["guardrails"]:
            result["guardrails"].append(guardrail)
    return result
