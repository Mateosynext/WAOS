from __future__ import annotations

from copy import deepcopy
from typing import Any

_PROFILES: dict[str, dict[str, Any]] = {
    "default": {
        "key": "default",
        "name": "General",
        "industry": "general",
        "description": "Asistente WAOS general para atención, ventas y operaciones.",
        "settings": {
            "tone": "profesional, claro y útil",
            "language": "es-MX",
            "handoff_policy": "Escalar a humano ante pagos, quejas sensibles o datos insuficientes.",
        },
        "starter_prompts": [
            "Saluda, identifica la necesidad y pide el dato mínimo para avanzar.",
            "No inventes disponibilidad, precios ni políticas.",
        ],
    },
    "commerce": {
        "key": "commerce",
        "name": "Commerce",
        "industry": "retail",
        "description": "Flujo base de catálogo, pedidos y seguimiento comercial.",
        "settings": {
            "tone": "vendedor consultivo",
            "language": "es-MX",
            "handoff_policy": "Escalar pagos fallidos, disputas o cambios de dirección.",
        },
        "starter_prompts": [
            "Recomienda productos con base en necesidad, presupuesto y disponibilidad confirmada.",
            "Confirma datos antes de cerrar pedido.",
        ],
    },
    "services": {
        "key": "services",
        "name": "Servicios",
        "industry": "services",
        "description": "Flujo base de agenda, cotización y seguimiento para servicios.",
        "settings": {
            "tone": "amable y resolutivo",
            "language": "es-MX",
            "handoff_policy": "Escalar urgencias, reclamos y cotizaciones fuera de rango.",
        },
        "starter_prompts": [
            "Identifica servicio, ubicación, horario deseado y urgencia.",
            "No prometas disponibilidad sin confirmación.",
        ],
    },
}

def normalize_vertical_key(value: str | None) -> str:
    key = str(value or "default").strip().lower().replace(" ", "_").replace("-", "_")
    return key if key in _PROFILES else "default"

def get_vertical_profile(vertical: str | None = None, **_: Any) -> dict[str, Any]:
    return deepcopy(_PROFILES[normalize_vertical_key(vertical)])

def list_vertical_profiles(*_: Any, **__: Any) -> list[dict[str, Any]]:
    return [deepcopy(item) for item in _PROFILES.values()]

def build_organization_settings(vertical: str | None = None, **overrides: Any) -> dict[str, Any]:
    profile = get_vertical_profile(vertical)
    settings = deepcopy(profile.get("settings") or {})
    settings.update({k: v for k, v in overrides.items() if v is not None})
    return {
        "vertical": profile["key"],
        "profile": profile,
        "runtime": {
            "language": settings.get("language", "es-MX"),
            "tone": settings.get("tone", "profesional"),
            "handoff_policy": settings.get("handoff_policy"),
        },
    }

def build_vertical_bot_setup(vertical: str | None = None, **kwargs: Any) -> dict[str, Any]:
    profile = get_vertical_profile(vertical)
    return {
        "vertical": profile["key"],
        "name": kwargs.get("name") or f"Bot {profile['name']}",
        "description": profile["description"],
        "settings": build_organization_settings(profile["key"], **kwargs),
        "starter_prompts": profile.get("starter_prompts") or [],
        "channels": kwargs.get("channels") or ["whatsapp"],
    }
