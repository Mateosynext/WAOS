from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from .domains.bot_behavior import get_bot_behavior_settings, list_bot_response_templates, upsert_bot_behavior_settings, upsert_bot_response_template
from .domains.catalog import create_catalog_service, list_catalog_services
from .knowledge_runtime import ingest_knowledge_document
from .utils import from_json, new_id, slugify, to_json, utcnow_iso
from .vertical_10x import apply_subvertical_pack, get_subvertical_profile
from .verticals import build_vertical_bot_setup, get_vertical_profile, list_vertical_profiles, normalize_vertical_key
from .world_class import execute, fetch_all, fetch_one, has_column, table_exists
from .runtime_schema_guards import assert_schema_ready


GUIDED_ONBOARDING_VERSION = "guided_vertical_onboarding_v1"
_GUIDED_STEPS = [
    {
        "key": "vertical_fit",
        "label": "Vertical y objetivo",
        "required": True,
        "fields": ["vertical_id", "subvertical", "primary_objective"],
    },
    {
        "key": "business_basics",
        "label": "Datos base del negocio",
        "required": True,
        "fields": ["business_name", "bot_name", "tone", "language", "timezone"],
    },
    {
        "key": "catalog_offer",
        "label": "Oferta, catalogo y CTAs",
        "required": True,
        "fields": ["services", "primary_ctas"],
    },
    {
        "key": "knowledge_seed",
        "label": "Knowledge base viva",
        "required": True,
        "fields": ["faqs", "policies", "knowledge_sources"],
    },
    {
        "key": "integrations_rules",
        "label": "Integraciones, reglas y escalamiento",
        "required": True,
        "fields": ["selected_integrations", "escalate_when"],
    },
    {
        "key": "launch_review",
        "label": "Automatizaciones y salida a produccion",
        "required": False,
        "fields": ["recommended_playbooks", "launch_notes", "autopublish_knowledge"],
    },
]
_GUIDED_STEP_INDEX = {str(step.get("key") or ""): index for index, step in enumerate(_GUIDED_STEPS)}

_DEFAULT_INTEGRATION_PROVIDERS = {
    "whatsapp": {"integration_type": "whatsapp", "provider": "meta_cloud_api", "name": "WhatsApp Cloud API"},
    "google_calendar": {"integration_type": "calendar", "provider": "google_calendar", "name": "Google Calendar"},
    "calendar": {"integration_type": "calendar", "provider": "google_calendar", "name": "Google Calendar"},
    "payments": {"integration_type": "payments", "provider": "stripe", "name": "Stripe"},
    "crm": {"integration_type": "crm", "provider": "waos_crm", "name": "WAOS CRM"},
    "drive": {"integration_type": "knowledge", "provider": "google_drive", "name": "Google Drive"},
    "notion": {"integration_type": "knowledge", "provider": "notion", "name": "Notion"},
    "url": {"integration_type": "knowledge", "provider": "url_sync", "name": "Website URLs"},
    "pdf": {"integration_type": "knowledge", "provider": "pdf_drop", "name": "PDF uploads"},
    "form": {"integration_type": "knowledge", "provider": "internal_form", "name": "Internal form"},
}

_VERTICAL_SCORECARD_RULES = {
    "dental": {
        "label": "Dental",
        "intent_signals": [
            {"label": "Agendar valoracion", "tokens": ["valoracion", "valoración", "diagnostico", "diagnóstico", "consulta inicial", "revision inicial"]},
            {"label": "Urgencia", "tokens": ["urgencia", "urgente", "dolor", "emergencia"]},
            {"label": "Anticipo", "tokens": ["anticipo", "depósito", "deposito", "reserva", "pago inicial"]},
        ],
        "objection_signals": [
            {"label": "Precio / costo", "tokens": ["precio", "costo", "cuanto cuesta", "cuánto cuesta"]},
            {"label": "Dolor / miedo", "tokens": ["dolor", "miedo", "molestia", "anestesia"]},
            {"label": "Agenda / tiempo", "tokens": ["horario", "agenda", "esta semana", "tiempo"]},
        ],
    },
    "fitness": {
        "label": "Fitness",
        "intent_signals": [
            {"label": "Trial", "tokens": ["trial", "prueba", "clase muestra", "sesion muestra", "sesión muestra"]},
            {"label": "Plan recomendado", "tokens": ["plan recomendado", "plan ideal", "objetivo", "plan sugerido"]},
            {"label": "Recuperacion", "tokens": ["recuperacion", "recuperación", "volver", "retomar", "reenganche"]},
        ],
        "objection_signals": [
            {"label": "Precio / membresia", "tokens": ["precio", "membresia", "membresía", "costo"]},
            {"label": "Tiempo / asistencia", "tokens": ["horario", "tiempo", "asistencia", "constancia"]},
            {"label": "Lesion / condicion", "tokens": ["lesion", "lesión", "condicion", "condición", "recuperacion", "recuperación"]},
        ],
    },
    "aesthetic": {
        "label": "Estetica",
        "intent_signals": [
            {"label": "Elegibilidad", "tokens": ["elegibilidad", "elegible", "candidata", "apta", "valoracion"]},
            {"label": "Paquete", "tokens": ["paquete", "bundle", "sesiones", "plan"]},
            {"label": "Mantenimiento", "tokens": ["mantenimiento", "retoque", "seguimiento", "sesion de control", "sesión de control"]},
        ],
        "objection_signals": [
            {"label": "Precio / sesiones", "tokens": ["precio", "costo", "sesiones", "paquete"]},
            {"label": "Resultados / seguridad", "tokens": ["resultado", "seguro", "seguridad", "efecto"]},
            {"label": "Recuperacion / cuidado", "tokens": ["recuperacion", "recuperación", "cuidado", "mantenimiento"]},
        ],
    },
    "estetica": {
        "label": "Estetica",
        "intent_signals": [
            {"label": "Elegibilidad", "tokens": ["elegibilidad", "elegible", "candidata", "apta", "valoracion"]},
            {"label": "Paquete", "tokens": ["paquete", "bundle", "sesiones", "plan"]},
            {"label": "Mantenimiento", "tokens": ["mantenimiento", "retoque", "seguimiento", "sesion de control", "sesión de control"]},
        ],
        "objection_signals": [
            {"label": "Precio / sesiones", "tokens": ["precio", "costo", "sesiones", "paquete"]},
            {"label": "Resultados / seguridad", "tokens": ["resultado", "seguro", "seguridad", "efecto"]},
            {"label": "Recuperacion / cuidado", "tokens": ["recuperacion", "recuperación", "cuidado", "mantenimiento"]},
        ],
    },
}

def _default_handoff_sla(primary_objective: str | None) -> str:
    objective = _safe_text(primary_objective).lower()
    if objective in {"agendar", "vender", "calificar"}:
        return "15 minutos"
    if objective == "reactivar":
        return "30 minutos"
    return "20 minutos"


def _default_handoff_channel(profile: dict[str, Any] | None = None) -> str:
    recommended = [str(item or "").strip().lower() for item in list((profile or {}).get("recommended_integrations") or [])]
    if "crm" in recommended:
        return "Equipo humano / CRM"
    if "whatsapp" in recommended:
        return "Equipo humano por WhatsApp"
    return "Equipo humano / operaciones"


def _json_summary(value: Any) -> str:
    record = _as_record(value)
    if not record:
        return "Sin overrides visibles"
    keys = sorted(record.keys())
    summary = [f"{len(keys)} reglas override"]
    if isinstance(record.get("can_say"), list):
        summary.append(f"puede decir {len([item for item in record.get('can_say') or [] if _safe_text(item)])}")
    if isinstance(record.get("cannot_say"), list):
        summary.append(f"no puede decir {len([item for item in record.get('cannot_say') or [] if _safe_text(item)])}")
    extras = [key for key in keys if key not in {"can_say", "cannot_say"}]
    if extras:
        summary.append("extras: " + ", ".join(extras[:3]))
    return " · ".join(summary)




def _collect_scorecard_text(value: Any, bucket: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            bucket.append(cleaned)
        return
    if isinstance(value, (int, float)):
        bucket.append(str(value))
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"id", "key", "created_at", "updated_at", "organization_id", "bot_id"}:
                continue
            _collect_scorecard_text(nested, bucket)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_scorecard_text(item, bucket)


def _scorecard_blob(*values: Any) -> str:
    bucket: list[str] = []
    for value in values:
        _collect_scorecard_text(value, bucket)
    return "\n".join(bucket).lower()


def _scorecard_match(blob: str, tokens: list[str]) -> bool:
    normalized = blob.lower()
    return any(_safe_text(token).lower() and _safe_text(token).lower() in normalized for token in tokens)


def _scorecard_item_status(covered: int, total: int, *, green_min: int | None = None, yellow_min: int = 1) -> str:
    if total <= 0:
        return "yellow"
    if green_min is None:
        green_min = total
    if covered >= green_min:
        return "green"
    if covered >= yellow_min:
        return "yellow"
    return "red"


def _build_vertical_scorecard(*, wizard: dict[str, Any], setup: dict[str, Any], bot_row: dict[str, Any] | None) -> dict[str, Any]:
    vertical_key = normalize_vertical_key(_safe_text(wizard.get("vertical_id")))
    rules = _VERTICAL_SCORECARD_RULES.get(vertical_key) or _VERTICAL_SCORECARD_RULES.get(_safe_text(wizard.get("vertical_id")).lower())
    if not rules:
        return {
            "vertical_id": vertical_key or _safe_text(wizard.get("vertical_id")),
            "label": _safe_text(wizard.get("vertical_id"), "Vertical"),
            "status": "yellow",
            "summary": "Todavía no hay una scorecard específica para esta industria. Usa la checklist formal y la simulación como puerta de salida.",
            "counts": {"green": 0, "yellow": 1, "red": 0},
            "items": [
                {
                    "key": "generic_scorecard",
                    "label": "Scorecard específica pendiente",
                    "status": "yellow",
                    "detail": "La vertical actual todavía no tiene scorecard de negocio específica. Antes de publicar, revisa intents, objeciones, handoff y CTA visibles con la checklist formal.",
                    "covered_signals": [],
                    "missing_signals": [],
                }
            ],
        }

    answers = _as_record(wizard.get("answers"))
    catalog_offer = _as_record(answers.get("catalog_offer"))
    integrations = _as_record(answers.get("integrations_rules"))
    bot_config = from_json((bot_row or {}).get("config_draft_json"), {}) if bot_row else {}
    bot_config = bot_config if isinstance(bot_config, dict) else {}
    cta_blob = _scorecard_blob(
        catalog_offer.get("primary_ctas"),
        _as_record(setup.get("wizard")).get("recommended_ctas"),
        catalog_offer.get("featured_offers"),
        setup.get("response_templates"),
    )
    seed_blob = _scorecard_blob(
        catalog_offer,
        answers.get("knowledge_seed"),
        setup.get("services"),
        setup.get("faqs"),
        _as_record(setup.get("business_knowledge")).get("policies"),
        _as_record(setup.get("wizard")).get("policies"),
        _as_record(setup.get("wizard")).get("launch_notes"),
        _as_record(setup.get("wizard")).get("recommended_playbooks"),
        _as_record(setup.get("wizard")).get("knowledge_sources"),
        bot_config,
    )
    handoff_blob = _scorecard_blob(
        integrations.get("escalate_when"),
        integrations.get("handoff_keywords"),
        integrations.get("expected_handoff_sla"),
        integrations.get("human_destination_channel"),
        _as_record(setup.get("handoff")),
        _as_record(setup.get("rules")),
    )

    intent_signals = list(rules.get("intent_signals") or [])
    covered_intents = [signal.get("label") for signal in intent_signals if _scorecard_match(seed_blob, list(signal.get("tokens") or []))]
    missing_intents = [signal.get("label") for signal in intent_signals if signal.get("label") not in covered_intents]
    intent_status = _scorecard_item_status(len(covered_intents), len(intent_signals), green_min=len(intent_signals), yellow_min=max(1, len(intent_signals) - 1))

    objection_signals = list(rules.get("objection_signals") or [])
    covered_objections = [signal.get("label") for signal in objection_signals if _scorecard_match(seed_blob, list(signal.get("tokens") or []))]
    missing_objections = [signal.get("label") for signal in objection_signals if signal.get("label") not in covered_objections]
    objection_status = _scorecard_item_status(len(covered_objections), len(objection_signals), green_min=len(objection_signals), yellow_min=max(1, len(objection_signals) - 1))

    handoff_hits = len([signal for signal in intent_signals if _scorecard_match(handoff_blob, list(signal.get("tokens") or []))])
    handoff_signals = sum(1 for value in [
        _as_record(setup.get("rules")).get("escalate_when") or integrations.get("escalate_when"),
        _as_record(setup.get("handoff")).get("sensitive_keywords") or integrations.get("handoff_keywords"),
        integrations.get("expected_handoff_sla") or _as_record(setup.get("handoff")).get("expected_sla"),
        integrations.get("human_destination_channel") or _as_record(setup.get("handoff")).get("destination_channel"),
    ] if value)
    handoff_status = "green" if handoff_signals >= 3 and handoff_hits >= 1 else "yellow" if handoff_signals >= 2 else "red"
    handoff_missing = [signal.get("label") for signal in intent_signals if not _scorecard_match(handoff_blob, list(signal.get("tokens") or []))][:2]

    covered_ctas = [signal.get("label") for signal in intent_signals if _scorecard_match(cta_blob, list(signal.get("tokens") or []))]
    missing_ctas = [signal.get("label") for signal in intent_signals if signal.get("label") not in covered_ctas]
    cta_status = _scorecard_item_status(len(covered_ctas), len(intent_signals), green_min=max(2, len(intent_signals) - 1), yellow_min=1)

    items = [
        {
            "key": "intent_coverage",
            "label": "Cobertura de intents",
            "status": intent_status,
            "detail": f"La propuesta cubre {len(covered_intents)}/{len(intent_signals)} señales de negocio esperadas para {rules.get('label')}: {', '.join(covered_intents) if covered_intents else 'ninguna señal visible' }.",
            "covered_signals": covered_intents,
            "missing_signals": missing_intents,
        },
        {
            "key": "objection_coverage",
            "label": "Cobertura de objeciones",
            "status": objection_status,
            "detail": f"La knowledge y los templates cubren {len(covered_objections)}/{len(objection_signals)} objeciones típicas: {', '.join(covered_objections) if covered_objections else 'sin objeciones visibles' }.",
            "covered_signals": covered_objections,
            "missing_signals": missing_objections,
        },
        {
            "key": "handoff_safe",
            "label": "Handoff seguro",
            "status": handoff_status,
            "detail": "Las reglas de handoff ya muestran triggers, keywords, SLA y canal humano suficientes para escalar sin sorpresas." if handoff_status == "green" else "Hay base de handoff, pero todavía falta más visibilidad de triggers o escalamiento seguro." if handoff_status == "yellow" else "El handoff todavía no muestra suficientes señales de seguridad operativa para esta vertical.",
            "covered_signals": [rules.get("label")] if handoff_hits else [],
            "missing_signals": handoff_missing,
        },
        {
            "key": "cta_visible",
            "label": "CTA visible",
            "status": cta_status,
            "detail": f"Las CTAs visibles cubren {len(covered_ctas)}/{len(intent_signals)} movimientos principales de negocio: {', '.join(covered_ctas) if covered_ctas else 'sin CTA fuerte visible'}.",
            "covered_signals": covered_ctas,
            "missing_signals": missing_ctas,
        },
    ]
    counts = _counts_from_validation_items(items)
    overall_status = "green" if counts.get("red", 0) == 0 and counts.get("yellow", 0) <= 1 else "red" if counts.get("red", 0) >= 2 else "yellow"
    summary = "La vertical ya llega con cobertura de negocio suficiente para pensar en publish." if overall_status == "green" else "La vertical tiene base sólida, pero todavía necesita reforzar algunas señales antes de publicar." if overall_status == "yellow" else "La scorecard de negocio todavía deja huecos importantes para un go-live seguro."
    return {
        "vertical_id": vertical_key,
        "label": rules.get("label"),
        "status": overall_status,
        "summary": summary,
        "counts": counts,
        "items": items,
    }


def _upsert_guided_integration(
    conn: Any,
    *,
    organization_id: str,
    bot_id: str | None,
    integration_type: str,
    provider: str,
    name: str,
    status: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    existing = fetch_one(
        conn,
        "SELECT * FROM integration_connections WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND integration_type = ? AND provider = ? AND name = ?",
        (organization_id, bot_id, integration_type, provider, name),
    )
    now = utcnow_iso()
    if existing:
        execute(conn, "UPDATE integration_connections SET status = ?, config_json = ?, updated_at = ? WHERE id = ?", (status, to_json(config), now, existing["id"]))
        return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (existing["id"],)) or existing
    row_id = new_id("int")
    execute(
        conn,
        "INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'unknown', 'pending', ?, ?, ?)",
        (row_id, organization_id, bot_id, integration_type, provider, name, status, to_json(config), now, now),
    )
    return fetch_one(conn, "SELECT * FROM integration_connections WHERE id = ?", (row_id,)) or {"id": row_id, "provider": provider, "status": status}

def ensure_guided_vertical_onboarding_schema(conn: Any) -> None:
    assert_schema_ready(
        conn,
        owner="migrations.py / db/migrations/012_guided_vertical_onboarding.sql",
        tables=(
            "vertical_onboarding_wizards",
            "vertical_onboarding_step_runs",
            "vertical_onboarding_wizard_events",
        ),
        columns=(
            ("vertical_onboarding_wizards", "validation_snapshot_json"),
            ("vertical_onboarding_wizards", "recompute_state_json"),
            ("vertical_onboarding_wizards", "wizard_revision"),
        ),
    )


def _deep_merge(base: Any, updates: Any) -> Any:
    if isinstance(base, dict) and isinstance(updates, dict):
        merged = deepcopy(base)
        for key, value in updates.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    return deepcopy(updates)


def _default_step_payloads(profile: dict[str, Any], *, subvertical: str | None, business_name: str, bot_name: str, tone: str, language: str, timezone: str, primary_objective: str, hours: str, whatsapp_number: str) -> dict[str, dict[str, Any]]:
    knowledge_sources = [
        {"connector_key": "drive", "required": True, "label": "Drive / docs operativos", "publish_policy": "auto_publish"},
        {"connector_key": "url", "required": True, "label": "Sitio y landing pages", "publish_policy": "auto_publish"},
        {"connector_key": "pdf", "required": False, "label": "PDFs comerciales y politicas", "publish_policy": "manual_review"},
        {"connector_key": "form", "required": False, "label": "Formulario interno de cambios", "publish_policy": "auto_publish"},
    ]
    if "notion" in [str(item).lower() for item in profile.get("recommended_integrations", [])]:
        knowledge_sources.insert(0, {"connector_key": "notion", "required": False, "label": "Notion operativo", "publish_policy": "auto_publish"})
    return {
        "vertical_fit": {
            "vertical_id": profile["id"],
            "subvertical": subvertical,
            "primary_objective": primary_objective,
        },
        "business_basics": {
            "business_name": business_name,
            "bot_name": bot_name,
            "tone": tone,
            "language": language,
            "timezone": timezone,
            "hours": hours,
            "whatsapp_number": whatsapp_number,
        },
        "catalog_offer": {
            "services": list(profile.get("default_services") or []),
            "featured_offers": [],
            "primary_ctas": _recommended_ctas(profile=profile, primary_objective=primary_objective),
            "pricing_notes": [],
        },
        "knowledge_seed": {
            "faqs": list(profile.get("default_faqs") or []),
            "policies": list((profile.get("config_overrides") or {}).get("policies") or []),
            "knowledge_sources": knowledge_sources,
            "owner_user_id": None,
        },
        "integrations_rules": {
            "selected_integrations": _recommended_integrations(profile),
            "escalate_when": list(profile.get("behavior", {}).get("escalate_when") or []),
            "handoff_keywords": list((profile.get("config_overrides") or {}).get("handoff_keywords") or []),
            "expected_handoff_sla": _default_handoff_sla(primary_objective),
            "human_destination_channel": _default_handoff_channel(profile),
            "rule_overrides": {
                "can_say": list((profile.get("config_overrides") or {}).get("can_say") or []),
                "cannot_say": list((profile.get("config_overrides") or {}).get("cannot_say") or []),
            },
        },
        "launch_review": {
            "recommended_playbooks": _recommended_playbooks(profile),
            "launch_notes": list(profile.get("flows") or []),
            "autopublish_knowledge": True,
        },
    }


def _recommended_ctas(*, profile: dict[str, Any], primary_objective: str) -> list[dict[str, Any]]:
    objective = str(primary_objective or "agendar").strip().lower()
    ctas = [
        {"key": "book_now", "label": "Agendar ahora", "goal": "booking"},
        {"key": "pricing", "label": "Ver plan o precio", "goal": "pricing"},
        {"key": "human_help", "label": "Hablar con asesor", "goal": "handoff"},
    ]
    if objective in {"cobrar", "cobranza", "payment", "cierre"}:
        ctas.insert(0, {"key": "pay_now", "label": "Enviar link de pago", "goal": "payment"})
    if profile.get("id") in {"dental", "aesthetic"}:
        ctas.insert(0, {"key": "assessment", "label": "Agendar valoracion", "goal": "assessment"})
    return ctas[:4]


def _recommended_playbooks(profile: dict[str, Any]) -> list[dict[str, Any]]:
    playbooks = []
    for idx, item in enumerate(list(profile.get("flows") or [])[:5], start=1):
        playbooks.append(
            {
                "key": f"guided_{slugify(item)}",
                "label": str(item),
                "priority": idx,
                "goal": "conversion",
            }
        )
    for item in list(profile.get("automation_sequences") or [])[:3]:
        if isinstance(item, dict):
            label = str(item.get("name") or item.get("title") or item.get("trigger") or "automation")
            playbooks.append({"key": f"auto_{slugify(label)}", "label": label, "priority": len(playbooks) + 1, "goal": "retention"})
    return playbooks[:6]


def _recommended_integrations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    recommended = list(profile.get("recommended_integrations") or [])
    for key in recommended + ["drive", "url", "pdf", "form"]:
        normalized = str(key or "").strip().lower()
        provider = _DEFAULT_INTEGRATION_PROVIDERS.get(normalized)
        if not provider or provider["provider"] in seen:
            continue
        seen.add(provider["provider"])
        items.append({
            "integration_key": normalized,
            "integration_type": provider["integration_type"],
            "provider": provider["provider"],
            "name": provider["name"],
            "status": "planned",
            "required": normalized in {"whatsapp", "google_calendar", "calendar", "payments", "crm", "drive", "url"},
        })
    return items


def _step_state(step: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_step_payload(_safe_text(step.get("key")), answers.get(step["key"], {})) if isinstance(answers, dict) else {}
    completed = True
    for field in step.get("fields") or []:
        value = payload.get(field) if isinstance(payload, dict) else None
        if step.get("required") and not _has_required_value(value):
            completed = False
            break
    status = "completed" if completed else ("in_progress" if payload else "pending")
    return {
        **step,
        "status": status,
        "completed": completed,
        "payload": payload,
    }


def _progress_summary(steps: list[dict[str, Any]]) -> tuple[int, str | None]:
    if not steps:
        return 0, None
    completed = len([item for item in steps if item.get("completed")])
    percent = round((completed / len(steps)) * 100)
    current_step = next((item["key"] for item in steps if not item.get("completed")), steps[-1]["key"])
    return percent, current_step


def _step_rank_key(step_key: str | None) -> int:
    return _GUIDED_STEP_INDEX.get(_safe_text(step_key), -1)


def _payload_fingerprint(value: Any) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:16]


def _captured_step_seed(*, vertical_id: str | None, subvertical: str | None, primary_objective: str | None, business_name: str | None, bot_name: str | None, tone: str | None, language: str | None, timezone: str | None, hours: str | None, whatsapp_number: str | None) -> dict[str, Any]:
    seeded: dict[str, Any] = {}
    vertical_fit = {
        "vertical_id": _safe_text(vertical_id),
        "subvertical": _safe_text(subvertical),
        "primary_objective": _safe_text(primary_objective),
    }
    if any(_has_required_value(value) for value in vertical_fit.values()):
        seeded["vertical_fit"] = vertical_fit
    return seeded


def _first_incomplete_required_step_key(answers: dict[str, Any] | None) -> str | None:
    normalized_answers = _normalize_answers(answers)
    for step in _GUIDED_STEPS:
        state = _step_state(step, normalized_answers)
        if step.get("required") and not state.get("completed"):
            return _safe_text(step.get("key")) or None
    return None


def _max_updateable_step_key(answers: dict[str, Any] | None) -> str | None:
    first_incomplete = _first_incomplete_required_step_key(answers)
    if first_incomplete:
        return first_incomplete
    if not _GUIDED_STEPS:
        return None
    return _safe_text(_GUIDED_STEPS[-1].get("key")) or None


def _required_step_fields(step_key: str) -> list[str]:
    normalized_step_key = _safe_text(step_key)
    step = next((item for item in _GUIDED_STEPS if _safe_text(item.get("key")) == normalized_step_key), None)
    if not step or not step.get("required"):
        return []
    return [str(field).strip() for field in list(step.get("fields") or []) if str(field).strip()]


def _preserve_required_step_fields(step_key: str, existing_payload: dict[str, Any] | None, next_payload: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    existing = _as_record(existing_payload)
    guarded = deepcopy(_as_record(next_payload))
    preserved_fields: list[str] = []
    for field in _required_step_fields(step_key):
        if _has_required_value(guarded.get(field)):
            continue
        if not _has_required_value(existing.get(field)):
            continue
        guarded[field] = deepcopy(existing.get(field))
        preserved_fields.append(field)
    return guarded, preserved_fields


def _step_update_allowed(answers: dict[str, Any] | None, step_key: str) -> bool:
    allowed_until = _max_updateable_step_key(answers)
    if not allowed_until:
        return True
    return _step_rank_key(step_key) <= _step_rank_key(allowed_until)


def _wizard_blueprint_from_wizard_state(wizard: dict[str, Any]) -> dict[str, Any]:
    normalized_answers = _normalize_answers(_as_record(wizard.get("answers")))
    fit = _as_record(normalized_answers.get("vertical_fit"))
    basics = _as_record(normalized_answers.get("business_basics"))
    return build_guided_onboarding_blueprint(
        vertical_id=fit.get("vertical_id") or wizard.get("vertical_id"),
        subvertical=fit.get("subvertical") or wizard.get("subvertical"),
        business_name=basics.get("business_name") or wizard.get("business_name") or "",
        bot_name=basics.get("bot_name") or wizard.get("bot_name") or "",
        tone=basics.get("tone") or wizard.get("tone") or "",
        language=basics.get("language") or wizard.get("language") or "es",
        timezone=basics.get("timezone") or wizard.get("timezone") or "America/Mexico_City",
        primary_objective=fit.get("primary_objective") or wizard.get("primary_objective") or "agendar",
        hours=basics.get("hours") or "",
        whatsapp_number=basics.get("whatsapp_number") or "",
        answers=normalized_answers,
        bot_id=wizard.get("bot_id"),
    )



def _step_run_drift_summary(step_runs: list[dict[str, Any]] | None, expected_steps: list[dict[str, Any]]) -> dict[str, Any]:
    existing_by_key = {_safe_text(item.get("step_key")): item for item in list(step_runs or []) if _safe_text(item.get("step_key"))}
    missing: list[str] = []
    mismatched: list[str] = []
    extra = [key for key in existing_by_key.keys() if key not in _GUIDED_STEP_INDEX]
    for expected in expected_steps:
        step_key = _safe_text(expected.get("key"))
        if not step_key:
            continue
        row = existing_by_key.get(step_key)
        if not row:
            missing.append(step_key)
            continue
        normalized_payload = _normalize_step_payload(step_key, row.get("payload"))
        if (
            _payload_fingerprint(normalized_payload) != _payload_fingerprint(expected.get("payload") or {})
            or _safe_text(row.get("step_status"), "pending") != _safe_text(expected.get("status"), "pending")
            or bool(row.get("completed_at")) != bool(expected.get("completed"))
            or bool(int(row.get("is_required") or 0)) != bool(expected.get("required"))
        ):
            mismatched.append(step_key)
    return {
        "missing": missing,
        "mismatched": mismatched,
        "extra": extra,
        "count": len(missing) + len(mismatched) + len(extra),
    }



def _build_wizard_diagnostics(*, wizard: dict[str, Any], steps: list[dict[str, Any]], events: list[dict[str, Any]], step_runs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    required_completed = [_safe_text(step.get("key")) for step in steps if step.get("required") and step.get("completed")]
    required_pending = [_safe_text(step.get("key")) for step in steps if step.get("required") and not step.get("completed")]
    recompute_state = _as_record(wizard.get("recompute_state"))
    last_event = events[-1] if events else {}
    blueprint = _wizard_blueprint_from_wizard_state(wizard)
    expected_subvertical = blueprint.get("selected_subvertical", {}).get("name") if blueprint.get("selected_subvertical") else _read_nested_string(blueprint.get("answers"), ["vertical_fit", "subvertical"])
    stored_answers = _normalize_answers(_as_record(wizard.get("answers")))
    stored_setup = _as_record(wizard.get("setup"))
    stored_checklist = list(wizard.get("checklist") or [])
    step_run_drift = _step_run_drift_summary(step_runs or list(wizard.get("step_runs") or []), list(blueprint.get("steps") or []))
    mismatch_fields: list[str] = []
    if _safe_text(wizard.get("current_step")) != _safe_text(blueprint.get("current_step")):
        mismatch_fields.append("current_step")
    if int(wizard.get("progress_percent") or 0) != int(blueprint.get("progress_percent") or 0):
        mismatch_fields.append("progress_percent")
    if _safe_text(wizard.get("subvertical")) != _safe_text(expected_subvertical):
        mismatch_fields.append("subvertical")
    if _payload_fingerprint(stored_answers) != _payload_fingerprint(blueprint.get("answers") or {}):
        mismatch_fields.append("answers")
    if _payload_fingerprint(stored_setup) != _payload_fingerprint(blueprint.get("setup") or {}):
        mismatch_fields.append("setup")
    if _payload_fingerprint(stored_checklist) != _payload_fingerprint(blueprint.get("checklist") or []):
        mismatch_fields.append("checklist")
    if step_run_drift.get("count"):
        mismatch_fields.append("step_runs")
    integrity_signature = _payload_fingerprint(
        {
            "wizard_id": wizard.get("id"),
            "answers": blueprint.get("answers") or {},
            "current_step": blueprint.get("current_step"),
            "progress_percent": blueprint.get("progress_percent") or 0,
            "step_run_drift": step_run_drift,
        }
    )
    return {
        "first_incomplete_required_step": required_pending[0] if required_pending else None,
        "required_steps_completed": [item for item in required_completed if item],
        "required_steps_pending": [item for item in required_pending if item],
        "can_update_up_to_step": _max_updateable_step_key(wizard.get("answers")),
        "validation_snapshot_pending": bool(recompute_state.get("validation_snapshot_pending")),
        "dry_run_pending": bool(recompute_state.get("dry_run_pending")),
        "last_event_type": _safe_text(last_event.get("event_type")) or None,
        "event_count": len(events),
        "step_statuses": [
            {
                "key": _safe_text(step.get("key")),
                "status": _safe_text(step.get("status"), "pending"),
                "completed": bool(step.get("completed")),
            }
            for step in steps
        ],
        "stored_current_step": _safe_text(wizard.get("current_step")) or None,
        "computed_current_step": _safe_text(blueprint.get("current_step")) or None,
        "stored_progress_percent": int(wizard.get("progress_percent") or 0),
        "computed_progress_percent": int(blueprint.get("progress_percent") or 0),
        "stored_subvertical": _safe_text(wizard.get("subvertical")) or None,
        "computed_subvertical": _safe_text(expected_subvertical) or None,
        "integrity_signature": integrity_signature,
        "integrity_mismatch": bool(mismatch_fields),
        "integrity_mismatch_fields": mismatch_fields,
        "step_run_drift": step_run_drift,
    }


def _blueprint_prefill_step_payload(blueprint: dict[str, Any], step_key: str) -> dict[str, Any]:
    return _as_record(_as_record(blueprint.get("prefill_answers")).get(step_key))


def _build_setup_payload(*, profile: dict[str, Any], subvertical: str | None, answers: dict[str, Any], bot_id: str | None) -> dict[str, Any]:
    basics = answers.get("business_basics") or {}
    fit = answers.get("vertical_fit") or {}
    catalog = answers.get("catalog_offer") or {}
    knowledge = answers.get("knowledge_seed") or {}
    integrations = answers.get("integrations_rules") or {}
    launch = answers.get("launch_review") or {}

    business_name = str(basics.get("business_name") or "Negocio WAOS").strip()
    bot_name = str(basics.get("bot_name") or ("Bot " + business_name)).strip()
    tone = str(basics.get("tone") or profile.get("behavior", {}).get("tone") or "cercano").strip()
    language = str(basics.get("language") or "es").strip()
    timezone = str(basics.get("timezone") or "America/Mexico_City").strip()
    primary_objective = str(fit.get("primary_objective") or "agendar").strip()
    services = list(catalog.get("services") or profile.get("default_services") or [])
    faqs = list(knowledge.get("faqs") or profile.get("default_faqs") or [])
    hours = str(basics.get("hours") or "").strip()
    whatsapp_number = str(basics.get("whatsapp_number") or "").strip()

    setup = build_vertical_bot_setup(
        fit.get("vertical_id") or profile.get("id"),
        business_name=business_name,
        bot_name=bot_name,
        tone=tone,
        language=language,
        timezone=timezone,
        primary_objective=primary_objective,
        services=services,
        faqs=faqs,
        hours=hours,
        whatsapp_number=whatsapp_number,
    )
    selected_sub = get_subvertical_profile(profile, subvertical)
    setup["handoff"] = {
        **_as_record(setup.get("handoff")),
        "sensitive_keywords": list(integrations.get("handoff_keywords") or _as_record(setup.get("handoff")).get("sensitive_keywords") or []),
        "expected_sla": _safe_text(integrations.get("expected_handoff_sla"), _safe_text(_as_record(setup.get("handoff")).get("expected_sla"), _default_handoff_sla(primary_objective))),
        "destination_channel": _safe_text(integrations.get("human_destination_channel"), _safe_text(_as_record(setup.get("handoff")).get("destination_channel"), _default_handoff_channel(profile))),
        "override_rules": deepcopy(integrations.get("rule_overrides") or {}),
    }
    setup["wizard"] = {
        "wizard_version": GUIDED_ONBOARDING_VERSION,
        "selected_subvertical": selected_sub.get("name") if selected_sub else subvertical,
        "knowledge_sources": list(knowledge.get("knowledge_sources") or []),
        "recommended_integrations": list(integrations.get("selected_integrations") or _recommended_integrations(profile)),
        "recommended_playbooks": list(launch.get("recommended_playbooks") or _recommended_playbooks(profile)),
        "recommended_ctas": list(catalog.get("primary_ctas") or _recommended_ctas(profile=profile, primary_objective=primary_objective)),
        "featured_offers": list(catalog.get("featured_offers") or []),
        "pricing_notes": list(catalog.get("pricing_notes") or []),
        "policies": list(knowledge.get("policies") or []),
        "launch_notes": list(launch.get("launch_notes") or []),
        "autopublish_knowledge": bool(launch.get("autopublish_knowledge") if launch.get("autopublish_knowledge") is not None else True),
        "rule_overrides": deepcopy(integrations.get("rule_overrides") or {}),
        "owner_user_id": knowledge.get("owner_user_id"),
        "bot_id": bot_id,
    }
    return setup


def build_guided_onboarding_blueprint(
    *,
    vertical_id: str | None,
    subvertical: str | None = None,
    business_name: str = "",
    bot_name: str = "",
    tone: str = "",
    language: str = "es",
    timezone: str = "America/Mexico_City",
    primary_objective: str = "agendar",
    hours: str = "",
    whatsapp_number: str = "",
    answers: dict[str, Any] | None = None,
    bot_id: str | None = None,
) -> dict[str, Any]:
    profile = get_vertical_profile(vertical_id)
    selected_sub = get_subvertical_profile(profile, subvertical)
    defaults = _default_step_payloads(
        profile,
        subvertical=selected_sub.get("name") if selected_sub else subvertical,
        business_name=business_name or profile.get("name") or "Negocio WAOS",
        bot_name=bot_name or f"Bot {business_name or profile.get('short_name') or profile.get('name')}",
        tone=tone or str(profile.get("behavior", {}).get("tone") or "cercano"),
        language=language,
        timezone=timezone,
        primary_objective=primary_objective,
        hours=hours,
        whatsapp_number=whatsapp_number,
    )
    raw_captured_answers = _deep_merge(
        _captured_step_seed(
            vertical_id=profile.get("id"),
            subvertical=selected_sub.get("name") if selected_sub else subvertical,
            primary_objective=primary_objective,
            business_name=business_name,
            bot_name=bot_name,
            tone=tone,
            language=language,
            timezone=timezone,
            hours=hours,
            whatsapp_number=whatsapp_number,
        ),
        answers or {},
    )
    captured_answers = _normalize_answers(raw_captured_answers)
    display_answers = _normalize_answers(_deep_merge(defaults, raw_captured_answers))
    steps = [_step_state(step, captured_answers) for step in _GUIDED_STEPS]
    progress_percent, current_step = _progress_summary(steps)
    setup = _build_setup_payload(profile=profile, subvertical=selected_sub.get("name") if selected_sub else subvertical, answers=display_answers, bot_id=bot_id)
    step_status_by_key = {str(step.get("key") or ""): step for step in steps}
    checklist = [
        {"key": "vertical_pack", "label": "Vertical y subvertical definidas", "completed": bool(step_status_by_key.get("vertical_fit", {}).get("completed"))},
        {"key": "services", "label": "Catalogo minimo listo", "completed": bool(step_status_by_key.get("catalog_offer", {}).get("completed"))},
        {"key": "knowledge", "label": "Knowledge base inicial lista", "completed": bool(step_status_by_key.get("knowledge_seed", {}).get("completed"))},
        {"key": "integrations", "label": "Integraciones planificadas", "completed": bool(step_status_by_key.get("integrations_rules", {}).get("completed"))},
        {"key": "automation", "label": "Playbooks sugeridos seleccionados", "completed": bool(step_status_by_key.get("launch_review", {}).get("completed"))},
    ]
    return {
        "wizard_version": GUIDED_ONBOARDING_VERSION,
        "profile": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "short_name": profile.get("short_name"),
            "description": profile.get("description"),
            "problem": profile.get("problem"),
            "recommended_integrations": profile.get("recommended_integrations", []),
            "subverticals": profile.get("subverticals", []),
            "recommended_subverticals": profile.get("recommended_subverticals", []),
        },
        "selected_subvertical": selected_sub,
        "steps": steps,
        "progress_percent": progress_percent,
        "current_step": current_step,
        "answers": captured_answers,
        "prefill_answers": display_answers,
        "setup": setup,
        "checklist": checklist,
    }


def list_guided_onboarding_verticals() -> list[dict[str, Any]]:
    items = []
    for profile in list_vertical_profiles():
        items.append(
            {
                "id": profile.get("id"),
                "name": profile.get("name"),
                "short_name": profile.get("short_name"),
                "description": profile.get("description"),
                "problem": profile.get("problem"),
                "recommended_integrations": profile.get("recommended_integrations", []),
                "subverticals": profile.get("subverticals", []),
                "recommended_subverticals": profile.get("recommended_subverticals", []),
                "kpis": profile.get("kpis", []),
            }
        )
    return items


def _parse_wizard_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    payload = dict(row)
    for key, default in {
        "answers_json": {},
        "setup_json": {},
        "checklist_json": [],
        "recommended_integrations_json": [],
        "recommended_playbooks_json": [],
        "recommended_ctas_json": [],
        "applied_summary_json": {},
        "validation_snapshot_json": {},
        "recompute_state_json": {},
    }.items():
        clean_key = key[:-5] if key.endswith("_json") else key
        payload[clean_key] = from_json(payload.get(key), default)
    try:
        payload["wizard_revision"] = int(payload.get("wizard_revision") or 1)
    except Exception:
        payload["wizard_revision"] = 1
    return payload


def _parse_step_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["payload"] = from_json(payload.get("payload_json"), {})
    payload["generated_patch"] = from_json(payload.get("generated_patch_json"), {})
    return payload


def _parse_event_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["payload"] = from_json(payload.get("payload_json"), {})
    return payload


def _append_wizard_event(
    conn: Any,
    *,
    wizard_id: str,
    organization_id: str,
    bot_id: str | None,
    event_type: str,
    step_key: str | None = None,
    payload: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> None:
    ensure_guided_vertical_onboarding_schema(conn)
    execute(
        conn,
        "INSERT INTO vertical_onboarding_wizard_events (id, wizard_id, organization_id, bot_id, event_type, step_key, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            new_id("vwevt"),
            wizard_id,
            organization_id,
            bot_id,
            event_type,
            step_key,
            to_json(payload or {}),
            created_at or utcnow_iso(),
        ),
    )


def _load_guided_onboarding_wizard(conn: Any, wizard_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    row = _parse_wizard_row(fetch_one(conn, "SELECT * FROM vertical_onboarding_wizards WHERE id = ?", (wizard_id,)))
    if not row:
        return None, [], []
    steps = [_parse_step_row(item) for item in fetch_all(conn, "SELECT * FROM vertical_onboarding_step_runs WHERE wizard_id = ? ORDER BY created_at ASC", (wizard_id,))]
    events = [_parse_event_row(item) for item in fetch_all(conn, "SELECT * FROM vertical_onboarding_wizard_events WHERE wizard_id = ? ORDER BY created_at ASC", (wizard_id,))]
    return row, steps, events



def get_guided_onboarding_wizard(conn: Any, wizard_id: str) -> dict[str, Any] | None:
    ensure_guided_vertical_onboarding_schema(conn)
    row, steps, events = _load_guided_onboarding_wizard(conn, wizard_id)
    if not row:
        return None
    row["step_runs"] = steps
    row["event_log"] = events
    row["diagnostics"] = _build_wizard_diagnostics(wizard=row, steps=[_step_state(step, row.get("answers") or {}) for step in _GUIDED_STEPS], events=events, step_runs=steps)
    return row


def latest_guided_onboarding_wizard(conn: Any, *, organization_id: str, bot_id: str | None = None) -> dict[str, Any] | None:
    ensure_guided_vertical_onboarding_schema(conn)
    if bot_id:
        row = fetch_one(
            conn,
            "SELECT * FROM vertical_onboarding_wizards WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') ORDER BY updated_at DESC LIMIT 1",
            (organization_id, bot_id),
        )
        parsed = _parse_wizard_row(row)
        if parsed:
            return parsed
    row = fetch_one(conn, "SELECT * FROM vertical_onboarding_wizards WHERE organization_id = ? ORDER BY updated_at DESC LIMIT 1", (organization_id,))
    return _parse_wizard_row(row)


def _find_matching_guided_onboarding_draft(
    conn: Any,
    *,
    organization_id: str,
    bot_id: str | None,
    vertical_id: str | None,
    subvertical: str | None,
    primary_objective: str | None,
) -> dict[str, Any] | None:
    ensure_guided_vertical_onboarding_schema(conn)
    normalized_vertical = normalize_vertical_key(vertical_id)
    normalized_subvertical = (subvertical or "").strip().lower()
    normalized_objective = (primary_objective or "").strip().lower()
    row = fetch_one(
        conn,
        """
        SELECT * FROM vertical_onboarding_wizards
        WHERE organization_id = ?
          AND status = 'draft'
          AND COALESCE(bot_id, '') = COALESCE(?, '')
          AND COALESCE(vertical_id, '') = COALESCE(?, '')
          AND LOWER(TRIM(COALESCE(subvertical, ''))) = ?
          AND LOWER(TRIM(COALESCE(primary_objective, ''))) = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (organization_id, bot_id, normalized_vertical, normalized_subvertical, normalized_objective),
    )
    parsed = _parse_wizard_row(row)
    if not parsed:
        return None
    return get_guided_onboarding_wizard(conn, parsed["id"])


def reconcile_guided_onboarding_wizard_integrity(conn: Any, *, wizard_id: str, source: str = "integrity_check") -> dict[str, Any]:
    ensure_guided_vertical_onboarding_schema(conn)
    wizard, step_runs, events = _load_guided_onboarding_wizard(conn, wizard_id)
    if not wizard:
        raise ValueError("wizard_not_found")
    wizard["step_runs"] = step_runs
    wizard["event_log"] = events
    diagnostics = _build_wizard_diagnostics(wizard=wizard, steps=[_step_state(step, wizard.get("answers") or {}) for step in _GUIDED_STEPS], events=events, step_runs=step_runs)
    wizard["diagnostics"] = diagnostics
    if not diagnostics.get("integrity_mismatch"):
        return wizard

    blueprint = _wizard_blueprint_from_wizard_state(wizard)
    answers = _normalize_answers(_as_record(blueprint.get("answers")))
    basics = _blueprint_prefill_step_payload(blueprint, "business_basics")
    fit = _as_record(answers.get("vertical_fit"))
    expected_subvertical = blueprint.get("selected_subvertical", {}).get("name") if blueprint.get("selected_subvertical") else fit.get("subvertical") or wizard.get("subvertical")
    setup = _as_record(blueprint.get("setup"))
    checklist = list(blueprint.get("checklist") or [])
    now = utcnow_iso()
    execute(
        conn,
        """
        UPDATE vertical_onboarding_wizards
        SET subvertical = ?, current_step = ?, progress_percent = ?, business_name = ?, bot_name = ?, tone = ?, language = ?, timezone = ?, primary_objective = ?,
            answers_json = ?, setup_json = ?, checklist_json = ?, recommended_integrations_json = ?, recommended_playbooks_json = ?, recommended_ctas_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            expected_subvertical,
            blueprint.get("current_step"),
            int(blueprint.get("progress_percent") or 0),
            basics.get("business_name"),
            basics.get("bot_name"),
            basics.get("tone"),
            basics.get("language"),
            basics.get("timezone"),
            fit.get("primary_objective"),
            to_json(answers),
            to_json(setup),
            to_json(checklist),
            to_json(_as_record(setup.get("wizard")).get("recommended_integrations") or []),
            to_json(_as_record(setup.get("wizard")).get("recommended_playbooks") or []),
            to_json(_as_record(setup.get("wizard")).get("recommended_ctas") or []),
            wizard.get("updated_at") or now,
            wizard_id,
        ),
    )

    expected_by_key = {_safe_text(step.get("key")): step for step in list(blueprint.get("steps") or []) if _safe_text(step.get("key"))}
    existing_by_key = {_safe_text(item.get("step_key")): item for item in step_runs if _safe_text(item.get("step_key"))}
    for step_key, step in expected_by_key.items():
        row = existing_by_key.get(step_key)
        completed_at = row.get("completed_at") if row and row.get("completed_at") and step.get("completed") else (now if step.get("completed") else None)
        if row:
            execute(
                conn,
                """
                UPDATE vertical_onboarding_step_runs
                SET step_status = ?, is_required = ?, payload_json = ?, generated_patch_json = ?, updated_at = ?, completed_at = ?
                WHERE wizard_id = ? AND step_key = ?
                """,
                (
                    step.get("status") or "pending",
                    1 if step.get("required") else 0,
                    to_json(step.get("payload") or {}),
                    to_json({"step_label": step.get("label"), "source": source}),
                    now,
                    completed_at,
                    wizard_id,
                    step_key,
                ),
            )
        else:
            execute(
                conn,
                """
                INSERT INTO vertical_onboarding_step_runs (
                    id, wizard_id, organization_id, bot_id, step_key, step_status, is_required, payload_json, generated_patch_json, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("vstep"),
                    wizard_id,
                    wizard.get("organization_id"),
                    wizard.get("bot_id"),
                    step_key,
                    step.get("status") or "pending",
                    1 if step.get("required") else 0,
                    to_json(step.get("payload") or {}),
                    to_json({"step_label": step.get("label"), "source": source}),
                    now,
                    now,
                    completed_at,
                ),
            )
    extra_keys = [key for key in existing_by_key.keys() if key not in expected_by_key]
    if extra_keys:
        placeholders = ",".join("?" for _ in extra_keys)
        execute(conn, f"DELETE FROM vertical_onboarding_step_runs WHERE wizard_id = ? AND step_key IN ({placeholders})", (wizard_id, *extra_keys))

    _append_wizard_event(
        conn,
        wizard_id=wizard_id,
        organization_id=wizard.get("organization_id"),
        bot_id=wizard.get("bot_id"),
        event_type="wizard.integrity_reconciled",
        payload={
            "source": source,
            "mismatch_fields": list(diagnostics.get("integrity_mismatch_fields") or []),
            "step_run_drift": diagnostics.get("step_run_drift") or {},
            "stored_current_step": diagnostics.get("stored_current_step"),
            "computed_current_step": diagnostics.get("computed_current_step"),
        },
        created_at=now,
    )
    return get_guided_onboarding_wizard(conn, wizard_id) or wizard


def start_guided_onboarding_wizard(
    conn: Any,
    *,
    organization_id: str,
    bot_id: str | None,
    actor_user_id: str | None,
    vertical_id: str | None,
    subvertical: str | None = None,
    business_name: str = "",
    bot_name: str = "",
    tone: str = "",
    language: str = "es",
    timezone: str = "America/Mexico_City",
    primary_objective: str = "agendar",
    hours: str = "",
    whatsapp_number: str = "",
    answers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_guided_vertical_onboarding_schema(conn)
    normalized_vertical = normalize_vertical_key(vertical_id)
    existing_draft = _find_matching_guided_onboarding_draft(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        vertical_id=normalized_vertical,
        subvertical=subvertical,
        primary_objective=primary_objective,
    )
    if existing_draft:
        return existing_draft
    blueprint = build_guided_onboarding_blueprint(
        vertical_id=normalized_vertical,
        subvertical=subvertical,
        business_name=business_name,
        bot_name=bot_name,
        tone=tone,
        language=language,
        timezone=timezone,
        primary_objective=primary_objective,
        hours=hours,
        whatsapp_number=whatsapp_number,
        answers=answers,
        bot_id=bot_id,
    )
    wizard_id = new_id("vwiz")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO vertical_onboarding_wizards (
            id, organization_id, bot_id, vertical_id, subvertical, wizard_version, status, current_step, progress_percent,
            business_name, bot_name, tone, language, timezone, primary_objective,
            answers_json, setup_json, checklist_json, recommended_integrations_json, recommended_playbooks_json, recommended_ctas_json,
            applied_summary_json, validation_snapshot_json, recompute_state_json, wizard_revision, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', '{}', '{}', 1, ?, ?, ?)
        """,
        (
            wizard_id,
            organization_id,
            bot_id,
            normalized_vertical,
            blueprint.get("selected_subvertical", {}).get("name") if blueprint.get("selected_subvertical") else subvertical,
            GUIDED_ONBOARDING_VERSION,
            blueprint.get("current_step"),
            blueprint.get("progress_percent") or 0,
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("business_name"),
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("bot_name"),
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("tone"),
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("language"),
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("timezone"),
            ((blueprint.get("answers") or {}).get("vertical_fit") or {}).get("primary_objective"),
            to_json(blueprint.get("answers") or {}),
            to_json(blueprint.get("setup") or {}),
            to_json(blueprint.get("checklist") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_integrations") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_playbooks") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_ctas") or []),
            actor_user_id,
            now,
            now,
        ),
    )
    for step in blueprint.get("steps") or []:
        execute(
            conn,
            """
            INSERT INTO vertical_onboarding_step_runs (
                id, wizard_id, organization_id, bot_id, step_key, step_status, is_required, payload_json, generated_patch_json, created_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("vstep"),
                wizard_id,
                organization_id,
                bot_id,
                step["key"],
                step["status"],
                1 if step.get("required") else 0,
                to_json(step.get("payload") or {}),
                to_json({"step_label": step.get("label")}),
                now,
                now,
                now if step.get("completed") else None,
            ),
        )
    _append_wizard_event(
        conn,
        wizard_id=wizard_id,
        organization_id=organization_id,
        bot_id=bot_id,
        event_type="wizard.started",
        payload={
            "current_step": blueprint.get("current_step"),
            "progress_percent": blueprint.get("progress_percent") or 0,
            "vertical_id": normalized_vertical,
            "subvertical": blueprint.get("selected_subvertical", {}).get("name") if blueprint.get("selected_subvertical") else subvertical,
        },
        created_at=now,
    )
    return get_guided_onboarding_wizard(conn, wizard_id) or {"id": wizard_id}


def _stale_validation_state(*, wizard: dict[str, Any], step_key: str, now: str) -> tuple[dict[str, Any], dict[str, Any]]:
    stale_snapshot = {
        "generated_at": wizard.get("updated_at") or wizard.get("created_at") or now,
        "source": "stale_after_save",
        "apply_ready": False,
        "gate": {"status": "yellow", "label": "Pendiente de revalidación", "detail": "Se guardó el paso, pero la validación y el dry run quedaron pendientes de recomputarse."},
        "warnings": [{"code": "validation_pending", "message": "El wizard cambió y necesita refrescar snapshot/dry run antes de aplicar."}],
    }
    recompute_state = {
        "summary_pending": False,
        "checklist_pending": False,
        "validation_snapshot_pending": True,
        "dry_run_pending": True,
        "last_saved_step": step_key,
        "last_saved_at": now,
    }
    return stale_snapshot, recompute_state


def update_guided_onboarding_step(conn: Any, *, wizard_id: str, step_key: str, payload: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
    ensure_guided_vertical_onboarding_schema(conn)
    wizard = get_guided_onboarding_wizard(conn, wizard_id)
    if not wizard:
        raise ValueError("wizard_not_found")
    if not any(_safe_text(step.get("key")) == step_key for step in (_GUIDED_STEPS or [])):
        raise ValueError("invalid_step_key")
    current_revision = int(wizard.get("wizard_revision") or 1)
    if expected_revision is not None and int(expected_revision) != current_revision:
        raise ValueError("wizard_revision_conflict")

    answers = _normalize_answers(deepcopy(wizard.get("answers") or {}))
    existing_payload = _normalize_step_payload(step_key, _as_record(answers.get(step_key)))
    requested_payload = _normalize_step_payload(step_key, payload or {})
    normalized_payload, preserved_required_fields = _preserve_required_step_fields(
        step_key,
        existing_payload,
        requested_payload,
    )
    if not _step_update_allowed(answers, step_key):
        raise ValueError("wizard_step_out_of_sequence")
    merged_payload, preserved_required_fields_after_merge = _preserve_required_step_fields(
        step_key,
        existing_payload,
        _deep_merge(_as_record(existing_payload), normalized_payload),
    )
    preserved_required_fields = _unique_strings([*preserved_required_fields, *preserved_required_fields_after_merge])
    existing_fingerprint = _payload_fingerprint(existing_payload)
    requested_fingerprint = _payload_fingerprint(requested_payload)
    merged_fingerprint = _payload_fingerprint(merged_payload)
    validation_before_save = _as_record(answers.get("dry_run_validation"))
    touch_requires_revalidation = bool(validation_before_save) and requested_fingerprint != existing_fingerprint and merged_fingerprint == existing_fingerprint
    if merged_fingerprint == existing_fingerprint and not touch_requires_revalidation:
        return wizard
    answers[step_key] = merged_payload
    answers = _normalize_answers(answers)
    answers.pop("dry_run_validation", None)
    blueprint = build_guided_onboarding_blueprint(
        vertical_id=wizard.get("vertical_id"),
        subvertical=(answers.get("vertical_fit") or {}).get("subvertical") or wizard.get("subvertical"),
        business_name=(answers.get("business_basics") or {}).get("business_name") or wizard.get("business_name") or "",
        bot_name=(answers.get("business_basics") or {}).get("bot_name") or wizard.get("bot_name") or "",
        tone=(answers.get("business_basics") or {}).get("tone") or wizard.get("tone") or "",
        language=(answers.get("business_basics") or {}).get("language") or wizard.get("language") or "es",
        timezone=(answers.get("business_basics") or {}).get("timezone") or wizard.get("timezone") or "America/Mexico_City",
        primary_objective=(answers.get("vertical_fit") or {}).get("primary_objective") or wizard.get("primary_objective") or "agendar",
        hours=(answers.get("business_basics") or {}).get("hours") or "",
        whatsapp_number=(answers.get("business_basics") or {}).get("whatsapp_number") or "",
        answers=answers,
        bot_id=wizard.get("bot_id"),
    )
    now = utcnow_iso()
    step_payload = next((step for step in (blueprint.get("steps") or []) if _safe_text(step.get("key")) == step_key), None)
    if not step_payload:
        raise ValueError("invalid_step_key")

    next_revision = current_revision + 1
    stale_snapshot, recompute_state = _stale_validation_state(wizard=wizard, step_key=step_key, now=now)
    cursor = conn.execute(
        """
        UPDATE vertical_onboarding_wizards
        SET subvertical = ?, current_step = ?, progress_percent = ?, business_name = ?, bot_name = ?, tone = ?, language = ?, timezone = ?, primary_objective = ?,
            answers_json = ?, setup_json = ?, checklist_json = ?, recommended_integrations_json = ?, recommended_playbooks_json = ?, recommended_ctas_json = ?,
            validation_snapshot_json = ?, recompute_state_json = ?, wizard_revision = ?, updated_at = ?
        WHERE id = ? AND wizard_revision = ?
        """,
        (
            blueprint.get("selected_subvertical", {}).get("name") if blueprint.get("selected_subvertical") else wizard.get("subvertical"),
            blueprint.get("current_step"),
            blueprint.get("progress_percent") or 0,
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("business_name"),
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("bot_name"),
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("tone"),
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("language"),
            _blueprint_prefill_step_payload(blueprint, "business_basics").get("timezone"),
            ((blueprint.get("answers") or {}).get("vertical_fit") or {}).get("primary_objective"),
            to_json(blueprint.get("answers") or {}),
            to_json(blueprint.get("setup") or {}),
            to_json(blueprint.get("checklist") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_integrations") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_playbooks") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_ctas") or []),
            to_json(stale_snapshot),
            to_json(recompute_state),
            next_revision,
            now,
            wizard_id,
            current_revision,
        ),
    )
    if getattr(cursor, "rowcount", 1) == 0:
        raise ValueError("wizard_revision_conflict")

    execute(
        conn,
        """
        UPDATE vertical_onboarding_step_runs
        SET step_status = ?, payload_json = ?, generated_patch_json = ?, updated_at = ?, completed_at = ?
        WHERE wizard_id = ? AND step_key = ?
        """,
        (
            step_payload.get("status") or "pending",
            to_json(step_payload.get("payload") or {}),
            to_json({"step_label": step_payload.get("label")}),
            now,
            now if step_payload.get("completed") else None,
            wizard_id,
            step_key,
        ),
    )
    _append_wizard_event(
        conn,
        wizard_id=wizard_id,
        organization_id=wizard.get("organization_id"),
        bot_id=wizard.get("bot_id"),
        event_type="wizard.step_saved",
        step_key=step_key,
        payload={
            "wizard_revision": next_revision,
            "current_step": blueprint.get("current_step"),
            "progress_percent": blueprint.get("progress_percent") or 0,
            "completed": bool(step_payload.get("completed")),
            "status": step_payload.get("status") or "pending",
            "preserved_required_fields": preserved_required_fields,
            "revalidation_forced": touch_requires_revalidation,
        },
        created_at=now,
    )
    updated = get_guided_onboarding_wizard(conn, wizard_id) or wizard
    updated["validation_snapshot"] = stale_snapshot
    updated["recompute_state"] = recompute_state
    updated["wizard_revision"] = next_revision
    return updated


def _safe_text(value: Any, fallback: str = "") -> str:
    result = str(value or "").strip()
    return result or fallback


def _unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = _safe_text(value)
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _summarize_strings(values: list[Any], fallback: str, limit: int = 4) -> str:
    items = _unique_strings(values)[:limit]
    return " · ".join(items) if items else fallback


def _as_record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _read_nested_string(value: Any, path: list[str], fallback: str = "") -> str:
    current: Any = value
    for key in path:
        current = _as_record(current).get(key)
    return _safe_text(current, fallback)


def _read_nested_strings(value: Any, path: list[str]) -> list[str]:
    current: Any = value
    for key in path:
        current = _as_record(current).get(key)
    if not isinstance(current, list):
        return []
    return _unique_strings(list(current))


def _pick_template_labels(payload: dict[str, Any]) -> list[str]:
    arrays: list[Any] = []
    for key in ("response_templates", "templates"):
        current = payload.get(key)
        if isinstance(current, list):
            arrays.extend(current)
    pipeline_templates = _as_record(payload.get("pipeline")).get("templates")
    if isinstance(pipeline_templates, list):
        arrays.extend(pipeline_templates)
    labels: list[str] = []
    for item in arrays:
        record = _as_record(item)
        labels.append(_safe_text(record.get("title") or record.get("template_key") or record.get("key") or record.get("name")))
    return _unique_strings(labels)


def _integration_identity(item: Any) -> str:
    if isinstance(item, str):
        return _safe_text(item)
    record = _as_record(item)
    return _safe_text(record.get("provider") or record.get("integration_key") or record.get("name"))


def _has_required_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return _unique_strings([value])
    if isinstance(value, (list, tuple, set)):
        return _unique_strings(list(value))
    return []


def _normalize_faq_items(value: Any) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    raw_items = list(value) if isinstance(value, (list, tuple, set)) else [value] if value is not None else []
    for raw in raw_items:
        if isinstance(raw, str):
            question, sep, answer = raw.partition("|")
            q = _safe_text(question)
            a = _safe_text(answer if sep else "")
        else:
            record = _as_record(raw)
            q = _safe_text(record.get("q") or record.get("question") or record.get("label"))
            a = _safe_text(record.get("a") or record.get("answer") or record.get("value"))
        if q and a:
            items.append({"q": q, "a": a})
    unique_items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item["q"].lower(), item["a"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items


def _normalize_primary_ctas(value: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    raw_items = list(value) if isinstance(value, (list, tuple, set)) else [value] if value is not None else []
    for idx, item in enumerate(raw_items, start=1):
        if isinstance(item, str):
            label = _safe_text(item)
            record = {"key": f"cta_{idx}", "label": label, "goal": "support"}
        else:
            raw = _as_record(item)
            label = _safe_text(raw.get("label") or raw.get("name") or raw.get("key") or raw.get("goal"))
            record = {
                "key": _safe_text(raw.get("key"), f"cta_{idx}"),
                "label": label,
                "goal": _safe_text(raw.get("goal"), "support"),
            }
        if record.get("label"):
            normalized.append(record)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in normalized:
        key = _safe_text(item.get("label")).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_knowledge_sources(value: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    raw_items = list(value) if isinstance(value, (list, tuple, set)) else [value] if value is not None else []
    for item in raw_items:
        if isinstance(item, str):
            label = _safe_text(item)
            connector_key = slugify(label).replace("-", "_") or "source"
            record = {"connector_key": connector_key, "label": label, "publish_policy": "manual_review", "required": False}
        else:
            raw = _as_record(item)
            label = _safe_text(raw.get("label") or raw.get("connector_key") or raw.get("provider") or raw.get("name"))
            connector_key = _safe_text(raw.get("connector_key"), slugify(label).replace("-", "_")) or "source"
            record = {
                "connector_key": connector_key,
                "label": label or connector_key,
                "publish_policy": _safe_text(raw.get("publish_policy"), "manual_review"),
                "required": bool(raw.get("required")),
            }
        if record.get("label"):
            normalized.append(record)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in normalized:
        key = _safe_text(item.get("connector_key") or item.get("label")).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_selected_integrations(value: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    raw_items = list(value) if isinstance(value, (list, tuple, set)) else [value] if value is not None else []
    for item in raw_items:
        if isinstance(item, str):
            key = _safe_text(item).lower()
            provider_defaults = _DEFAULT_INTEGRATION_PROVIDERS.get(key, {})
            record = {
                "integration_key": key or "custom",
                "integration_type": _safe_text(provider_defaults.get("integration_type"), "custom"),
                "provider": _safe_text(provider_defaults.get("provider"), key or "custom"),
                "name": _safe_text(provider_defaults.get("name"), item),
                "status": "planned",
                "required": bool(provider_defaults and key in {"whatsapp", "google_calendar", "calendar", "payments", "crm", "drive", "url"}),
            }
        else:
            raw = _as_record(item)
            integration_key = _safe_text(raw.get("integration_key") or raw.get("provider") or raw.get("name"))
            provider_defaults = _DEFAULT_INTEGRATION_PROVIDERS.get(integration_key.lower(), {}) if integration_key else {}
            record = {
                "integration_key": integration_key or _safe_text(provider_defaults.get("provider"), "custom"),
                "integration_type": _safe_text(raw.get("integration_type"), _safe_text(provider_defaults.get("integration_type"), "custom")),
                "provider": _safe_text(raw.get("provider"), _safe_text(provider_defaults.get("provider"), integration_key or "custom")),
                "name": _safe_text(raw.get("name"), _safe_text(provider_defaults.get("name"), integration_key or "custom")),
                "status": _safe_text(raw.get("status"), "planned"),
                "required": bool(raw.get("required")) if raw.get("required") is not None else bool(provider_defaults and integration_key.lower() in {"whatsapp", "google_calendar", "calendar", "payments", "crm", "drive", "url"}),
            }
        if record.get("provider") or record.get("integration_key"):
            normalized.append(record)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in normalized:
        key = _safe_text(item.get("provider") or item.get("integration_key")).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_playbooks(value: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    raw_items = list(value) if isinstance(value, (list, tuple, set)) else [value] if value is not None else []
    for idx, item in enumerate(raw_items, start=1):
        if isinstance(item, str):
            label = _safe_text(item)
            record = {"key": slugify(label) or f"playbook_{idx}", "label": label, "priority": idx, "goal": "launch"}
        else:
            raw = _as_record(item)
            label = _safe_text(raw.get("label") or raw.get("name") or raw.get("key"))
            record = {
                "key": _safe_text(raw.get("key"), slugify(label) or f"playbook_{idx}"),
                "label": label,
                "priority": int(raw.get("priority") or idx),
                "goal": _safe_text(raw.get("goal"), "launch"),
            }
        if record.get("label"):
            normalized.append(record)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in normalized:
        key = _safe_text(item.get("key") or item.get("label")).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_step_payload(step_key: str, payload: Any) -> dict[str, Any]:
    record = _as_record(payload)
    if step_key == "vertical_fit":
        return {
            "vertical_id": _safe_text(record.get("vertical_id")),
            "subvertical": _safe_text(record.get("subvertical")),
            "primary_objective": _safe_text(record.get("primary_objective")),
        }
    if step_key == "business_basics":
        return {
            "business_name": _safe_text(record.get("business_name")),
            "bot_name": _safe_text(record.get("bot_name")),
            "tone": _safe_text(record.get("tone")),
            "language": _safe_text(record.get("language")),
            "timezone": _safe_text(record.get("timezone")),
            "hours": _safe_text(record.get("hours")),
            "whatsapp_number": _safe_text(record.get("whatsapp_number")),
        }
    if step_key == "catalog_offer":
        return {
            "services": _normalize_string_list(record.get("services")),
            "featured_offers": _normalize_string_list(record.get("featured_offers")),
            "primary_ctas": _normalize_primary_ctas(record.get("primary_ctas")),
            "pricing_notes": _normalize_string_list(record.get("pricing_notes")),
        }
    if step_key == "knowledge_seed":
        owner_user_id = _safe_text(record.get("owner_user_id"))
        return {
            "faqs": _normalize_faq_items(record.get("faqs")),
            "policies": _normalize_string_list(record.get("policies")),
            "knowledge_sources": _normalize_knowledge_sources(record.get("knowledge_sources")),
            "owner_user_id": owner_user_id or None,
        }
    if step_key == "integrations_rules":
        return {
            "selected_integrations": _normalize_selected_integrations(record.get("selected_integrations")),
            "escalate_when": _normalize_string_list(record.get("escalate_when")),
            "handoff_keywords": _normalize_string_list(record.get("handoff_keywords")),
            "expected_handoff_sla": _safe_text(record.get("expected_handoff_sla")),
            "human_destination_channel": _safe_text(record.get("human_destination_channel")),
            "rule_overrides": _as_record(record.get("rule_overrides")),
        }
    if step_key == "launch_review":
        return {
            "recommended_playbooks": _normalize_playbooks(record.get("recommended_playbooks")),
            "launch_notes": _normalize_string_list(record.get("launch_notes")),
            "autopublish_knowledge": bool(record.get("autopublish_knowledge")) if record.get("autopublish_knowledge") is not None else True,
        }
    return record


def _normalize_answers(answers: dict[str, Any] | None) -> dict[str, Any]:
    source = _as_record(answers)
    normalized: dict[str, Any] = {}
    for step in _GUIDED_STEPS:
        key = _safe_text(step.get("key"))
        if key:
            normalized[key] = _normalize_step_payload(key, source.get(key))
    for key, value in source.items():
        if key not in normalized:
            normalized[key] = deepcopy(value)
    return normalized


def _build_dry_run_signature(wizard: dict[str, Any]) -> str:
    answers = deepcopy(wizard.get("answers") or {})
    answers.pop("dry_run_validation", None)
    payload = {
        "organization_id": wizard.get("organization_id"),
        "bot_id": wizard.get("bot_id"),
        "vertical_id": wizard.get("vertical_id"),
        "subvertical": wizard.get("subvertical"),
        "primary_objective": _as_record(answers.get("vertical_fit")).get("primary_objective") or wizard.get("primary_objective"),
        "business_basics": _as_record(answers.get("business_basics")),
        "catalog_offer": _as_record(answers.get("catalog_offer")),
        "knowledge_seed": _as_record(answers.get("knowledge_seed")),
        "integrations_rules": _as_record(answers.get("integrations_rules")),
        "launch_review": _as_record(answers.get("launch_review")),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _faq_labels(items: Any) -> list[str]:
    labels: list[str] = []
    for item in list(items or []):
        if isinstance(item, dict):
            label = _safe_text(item.get("q") or item.get("question") or item.get("label"))
        else:
            label = _safe_text(item)
        if label:
            labels.append(label)
    return _unique_strings(labels)


def _cta_labels(items: Any) -> list[str]:
    labels: list[str] = []
    for item in list(items or []):
        if isinstance(item, dict):
            label = _safe_text(item.get("label") or item.get("key") or item.get("goal") or item.get("name"))
        else:
            label = _safe_text(item)
        if label:
            labels.append(label)
    return _unique_strings(labels)


def _template_labels_from_rows(items: Any) -> list[str]:
    labels: list[str] = []
    for item in list(items or []):
        record = _as_record(item)
        label = _safe_text(record.get("title") or record.get("template_key") or record.get("name"))
        if label:
            labels.append(label)
    return _unique_strings(labels)


def _counter_badges(*, added: int = 0, removed: int = 0, replaced: int = 0, unit: str) -> list[str]:
    badges: list[str] = []
    if added > 0:
        badges.append(f"+{added} {unit}")
    if removed > 0:
        badges.append(f"-{removed} {unit}")
    if replaced > 0:
        badges.append(f"reemplaza {replaced} {unit}")
    return badges


def _merge_counters(items: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"added": 0, "removed": 0, "replaced": 0, "kept": 0}
    for item in items:
        counters = _as_record(item.get("counters"))
        for key in totals:
            totals[key] += int(counters.get(key) or 0)
    return totals


def _resolve_status(items: list[dict[str, Any]]) -> str:
    statuses = [str(item.get("status") or "").strip() for item in items]
    if any(status == "replace" for status in statuses):
        return "replace"
    if any(status == "add" for status in statuses):
        return "add"
    if any(status == "remove" for status in statuses):
        return "remove"
    if any(status == "suggest" for status in statuses):
        return "suggest"
    return "keep"


def _scalar_diff_item(*, key: str, label: str, before: str, after: str, detail: str, unit: str | None = None) -> dict[str, Any]:
    clean_before = _safe_text(before, "Sin valor visible")
    clean_after = _safe_text(after, "Sin valor visible")
    if clean_before.strip().lower() == clean_after.strip().lower():
        status = "keep"
        counters = {"added": 0, "removed": 0, "replaced": 0, "kept": 1}
    elif clean_before and clean_after:
        status = "replace"
        counters = {"added": 0, "removed": 0, "replaced": 1, "kept": 0}
    elif clean_after:
        status = "add"
        counters = {"added": 1, "removed": 0, "replaced": 0, "kept": 0}
    elif clean_before:
        status = "remove"
        counters = {"added": 0, "removed": 1, "replaced": 0, "kept": 0}
    else:
        status = "suggest"
        counters = {"added": 0, "removed": 0, "replaced": 0, "kept": 0}
    item = {
        "key": key,
        "label": label,
        "status": status,
        "before": clean_before,
        "after": clean_after,
        "detail": detail,
        "counters": counters,
    }
    if unit:
        item["badges"] = _counter_badges(added=counters["added"], removed=counters["removed"], replaced=counters["replaced"], unit=unit)
    return item


def _list_diff_item(*, key: str, label: str, before: list[str], after: list[str], detail: str, unit: str, empty_before: str, empty_after: str) -> dict[str, Any]:
    before_clean = _unique_strings(before)
    after_clean = _unique_strings(after)
    before_map = {item.strip().lower(): item for item in before_clean}
    after_map = {item.strip().lower(): item for item in after_clean}
    kept = [before_map[item] for item in before_map if item in after_map]
    added = [after_map[item] for item in after_map if item not in before_map]
    removed = [before_map[item] for item in before_map if item not in after_map]
    if not before_clean and after_clean:
        status = "add"
    elif before_clean and not after_clean:
        status = "remove"
    elif added or removed:
        status = "replace"
    elif before_clean or after_clean:
        status = "keep"
    else:
        status = "suggest"
    counters = {"added": len(added), "removed": len(removed), "replaced": 0, "kept": len(kept)}
    return {
        "key": key,
        "label": label,
        "status": status,
        "before": _summarize_strings(before_clean, empty_before, 6),
        "after": _summarize_strings(after_clean, empty_after, 6),
        "detail": detail,
        "counters": counters,
        "badges": _counter_badges(added=len(added), removed=len(removed), replaced=0, unit=unit),
    }


def _build_diff_domain(*, key: str, label: str, detail: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    counters = _merge_counters(items)
    badges: list[str] = []
    for item in items:
        badges.extend(list(item.get("badges") or []))
    summary_parts = [badge for badge in badges[:3]]
    if not summary_parts:
        summary_parts.append("Sin cambio material visible")
    return {
        "key": key,
        "label": label,
        "status": _resolve_status(items),
        "detail": detail,
        "summary": " · ".join(summary_parts),
        "counters": counters,
        "badges": badges[:6],
        "items": items,
    }


def _parse_timestamp(value: Any) -> int | None:
    rendered = _safe_text(value)
    if not rendered:
        return None
    try:
        import datetime as _dt
        normalized = rendered.replace("Z", "+00:00")
        return int(_dt.datetime.fromisoformat(normalized).timestamp() * 1000)
    except Exception:
        return None


def _happened_after(value: Any, reference: Any) -> bool:
    value_ts = _parse_timestamp(value)
    if value_ts is None:
        return False
    reference_ts = _parse_timestamp(reference)
    return True if reference_ts is None else value_ts >= reference_ts


def _connected_state(value: Any) -> bool:
    return _safe_text(value).lower() in {"send_ready", "connected", "active", "ready", "live", "verified", "ok", "published", "synced"}


def _has_connected_operational_channel(bot_row: dict[str, Any] | None, bot_config: dict[str, Any]) -> bool:
    if not bot_row:
        return False
    if _safe_text(bot_row.get("connection_status")).lower() == "send_ready":
        return True
    # A captured WhatsApp number or provider id alone is not an operational channel.
    # It must reach send_ready through provider credentials + webhook verification.
    if _safe_text(bot_row.get("primary_channel")):
        return True
    channels = list(bot_config.get("channels") or [])
    if channels:
        return True
    integrations = _as_record(bot_config.get("integrations"))
    for key, value in integrations.items():
        record = _as_record(value)
        rendered = f"{key} {_safe_text(record.get('provider'))} {_safe_text(record.get('status'))} {_safe_text(record.get('channel'))}".lower()
        if not any(token in rendered for token in ["whatsapp", "instagram", "telegram", "webchat", "email", "voice", "sms", "messenger", "twilio"]):
            continue
        if _connected_state(record.get("status")):
            return True
    return False


def _simulation_result_for_snapshot(conn: Any, *, bot_id: str | None, applied_at: Any) -> dict[str, Any]:
    default = {"status": "pending", "approved": False, "pass_rate": 0, "cases_total": 0, "created_at": None, "run_id": None}
    if not bot_id or not table_exists(conn, "bot_simulation_runs"):
        return default
    runs = fetch_all(conn, "SELECT * FROM bot_simulation_runs WHERE bot_id = ? ORDER BY created_at DESC LIMIT 20", (bot_id,))
    if applied_at:
        runs = [row for row in runs if _happened_after(row.get("created_at"), applied_at)]
    row = runs[0] if runs else None
    if not row:
        return default
    summary = from_json(row.get("summary_json"), {}) if row.get("summary_json") else {}
    summary = summary if isinstance(summary, dict) else {}
    pass_rate = float(summary.get("pass_rate") or 0)
    cases_total = int(summary.get("cases_total") or row.get("cases_total") or 0)
    status = _safe_text(row.get("status"), "pending").lower()
    approved = status == "completed" and pass_rate >= 80
    effective_status = "approved" if approved else "needs_review" if status == "completed" else status or "pending"
    return {
        "status": effective_status,
        "approved": approved,
        "pass_rate": pass_rate,
        "cases_total": cases_total,
        "created_at": row.get("created_at"),
        "compare_target": summary.get("compare_target"),
        "run_id": row.get("id"),
    }


def _release_state_for_snapshot(conn: Any, *, bot_id: str | None, applied_at: Any) -> dict[str, Any]:
    default = {"has_request": False, "has_published": False, "latest_status": "pending", "latest_id": None}
    if not bot_id or not table_exists(conn, "release_requests"):
        return default
    rows = fetch_all(conn, "SELECT * FROM release_requests WHERE bot_id = ? ORDER BY created_at DESC", (bot_id,))
    if applied_at:
        rows = [row for row in rows if _happened_after(row.get("updated_at") or row.get("created_at"), applied_at)]
    if not rows:
        return default
    latest = rows[0]
    latest_status = _safe_text(latest.get("status"), "pending").lower() or "pending"
    return {
        "has_request": True,
        "has_published": any(_safe_text(row.get("status")).lower() == "published" for row in rows),
        "latest_status": latest_status,
        "latest_id": latest.get("id"),
        "latest_href": f"/releases?stage=draft&bot_id={bot_id}",
    }


def _bot_is_live_or_ready(bot_row: dict[str, Any] | None) -> bool:
    row = bot_row or {}
    signals = [
        _safe_text(row.get("status")).lower(),
        _safe_text(row.get("current_state")).lower(),
        _safe_text(row.get("connection_status")).lower(),
    ]
    if _safe_text(row.get("published_version_id")):
        signals.append("published")
    return any(value in {"published", "live", "active", "ready", "operating", "released", "connected", "send_ready"} for value in signals if value)


def _next_cta_for_snapshot(*, bot_id: str | None, bot_row: dict[str, Any] | None, has_connected_channel: bool, simulation_approved: bool, has_release_request: bool, has_published_release: bool) -> dict[str, Any]:
    encoded_bot = _safe_text(bot_id)
    if not has_connected_channel:
        return {
            "key": "connect_channel",
            "title": "Conectar canal",
            "description": "Todavía no hay un canal operativo claro. Antes de publicar o pedir pruebas finales, conecta el canal principal.",
            "cta_label": "Conectar canal",
            "href": "/integrations?section=configuracion",
        }
    if not simulation_approved:
        return {
            "key": "run_simulation",
            "title": "Correr simulación",
            "description": "Todavía no existe una simulación básica aprobada para este cambio. Corre la verificación antes de publicar.",
            "cta_label": "Correr simulación",
        }
    if has_published_release or _bot_is_live_or_ready(bot_row):
        return {
            "key": "open_inbox",
            "title": "Abrir inbox",
            "description": "El canal ya está conectado y la simulación básica pasó. Si el asistente ya está publicado o listo para operar, Inbox se vuelve el destino natural de primer nivel.",
            "cta_label": "Abrir inbox",
            "href": "/inbox",
        }
    return {
        "key": "publish_release",
        "title": "Publicar release",
        "description": "El canal está listo y la simulación básica ya pasó. El siguiente paso operativo es publicar el release de este cambio.",
        "cta_label": "Publicar release",
        "href": f"/releases?stage=draft&bot_id={encoded_bot}" if encoded_bot else "/releases?stage=draft",
        "has_release_request": has_release_request,
    }


def _validation_item(*, key: str, label: str, status: str, detail: str, blocking: bool = True) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "detail": detail,
        "blocking": blocking,
    }


def _compact_diff_summary(diff_domains: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for domain in diff_domains:
        children = list(domain.get("items") or [])
        if not children:
            children = [domain]
        for item in children:
            compact.append(
                {
                    "key": item.get("key") or domain.get("key"),
                    "label": item.get("label") or domain.get("label"),
                    "status": item.get("status") or domain.get("status"),
                    "summary": item.get("summary") or item.get("detail") or domain.get("summary") or domain.get("detail"),
                    "counters": item.get("counters") or {},
                }
            )
    return compact


def _counts_from_validation_items(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"green": 0, "yellow": 0, "red": 0}
    for item in items:
        status = _safe_text(item.get("status")).lower()
        if status in counts:
            counts[status] += 1
    return counts


def _build_validation_snapshot(
    conn: Any,
    *,
    wizard: dict[str, Any],
    bot_row: dict[str, Any] | None,
    org_row: dict[str, Any] | None,
    setup: dict[str, Any],
    diff_summary: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    apply_ready: bool,
    validation_hash: str,
    source: str,
    exit_score: dict[str, Any] | None,
) -> dict[str, Any]:
    _ = org_row
    answers = _as_record(wizard.get("answers"))
    basics = _as_record(answers.get("business_basics"))
    fit = _as_record(answers.get("vertical_fit"))
    integrations = _as_record(answers.get("integrations_rules"))
    bot_config = from_json((bot_row or {}).get("config_draft_json"), {}) if bot_row else {}
    bot_config = bot_config if isinstance(bot_config, dict) else {}
    applied_at = wizard.get("applied_at")
    simulation = _simulation_result_for_snapshot(conn, bot_id=wizard.get("bot_id"), applied_at=applied_at)
    release_state = _release_state_for_snapshot(conn, bot_id=wizard.get("bot_id"), applied_at=applied_at)
    integration_rows = fetch_all(conn, "SELECT * FROM integration_connections WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') ORDER BY updated_at DESC", (wizard.get("organization_id"), wizard.get("bot_id"))) if table_exists(conn, "integration_connections") else []
    has_connected_channel = _has_connected_operational_channel(bot_row, bot_config) or any(
        any(token in f"{_safe_text(row.get('integration_type')).lower()} {_safe_text(row.get('provider')).lower()} {_safe_text(row.get('name')).lower()}" for token in ["whatsapp", "instagram", "telegram", "webchat", "email", "voice", "sms", "messenger", "twilio"])
        and (_connected_state(row.get("status")) or _connected_state(row.get("credential_status")) or _connected_state(row.get("health_status")))
        for row in integration_rows
    )
    selected_integrations = list(integrations.get("selected_integrations") or _as_record(setup.get("wizard")).get("recommended_integrations") or [])
    required_integrations = [item for item in selected_integrations if bool(_as_record(item).get("required"))]

    def _integration_match(connection: dict[str, Any], item: Any) -> bool:
        record = _as_record(item)
        provider = _safe_text(record.get("provider")).lower()
        integration_type = _safe_text(record.get("integration_type")).lower()
        name = _safe_text(record.get("name")).lower()
        return bool(
            provider and provider == _safe_text(connection.get("provider")).lower()
            or integration_type and integration_type == _safe_text(connection.get("integration_type")).lower()
            or name and name == _safe_text(connection.get("name")).lower()
        )

    connected_required = 0
    planned_required = 0
    for item in required_integrations:
        matches = [row for row in integration_rows if _integration_match(row, item)]
        if matches:
            planned_required += 1
        if any(_connected_state(row.get("status")) or _connected_state(row.get("credential_status")) or _connected_state(row.get("health_status")) for row in matches):
            connected_required += 1
    if not planned_required and required_integrations:
        planned_required = len(required_integrations)

    handoff_keywords = _unique_strings(list(integrations.get("handoff_keywords") or _as_record(setup.get("handoff")).get("sensitive_keywords") or []))
    escalate_when = _unique_strings(list(integrations.get("escalate_when") or _as_record(setup.get("rules")).get("escalate_when") or []))
    handoff_sla = _safe_text(integrations.get("expected_handoff_sla") or _as_record(setup.get("handoff")).get("expected_sla"))
    human_channel = _safe_text(integrations.get("human_destination_channel") or _as_record(setup.get("handoff")).get("destination_channel") or _safe_text((bot_row or {}).get("primary_channel")))
    handoff_signals = sum(1 for value in [handoff_keywords, escalate_when, handoff_sla, human_channel] if value)

    pack_generated = bool(
        wizard.get("setup")
        or _as_record(wizard.get("applied_summary")).get("pack_result")
        or _as_record(wizard.get("applied_summary")).get("template_count")
        or setup.get("services")
        or setup.get("response_templates")
        or _as_record(setup.get("wizard")).get("recommended_playbooks")
    )
    has_defined_channel = bool(has_connected_channel or selected_integrations or human_channel or _as_record(setup.get("integrations")))
    simulation_approved = bool(simulation.get("approved"))
    next_cta = _next_cta_for_snapshot(
        bot_id=wizard.get("bot_id"),
        bot_row=bot_row,
        has_connected_channel=has_connected_channel,
        simulation_approved=simulation_approved,
        has_release_request=bool(release_state.get("has_request")),
        has_published_release=bool(release_state.get("has_published")),
    )

    checklist = [
        _validation_item(key="organization_confirmed", label="Organización confirmada", status="green" if _safe_text(wizard.get("organization_id")) else "red", detail="El contexto organizacional ya quedó definido explícitamente." if _safe_text(wizard.get("organization_id")) else "Falta una organización explícita para operar este wizard."),
        _validation_item(key="assistant_confirmed", label="Asistente operativo confirmado", status="green" if bot_row else "yellow" if _safe_text(basics.get("bot_name") or wizard.get("bot_name")) else "red", detail="El asistente operativo ya existe y pertenece a la organización seleccionada." if bot_row else "El nombre ya está definido y se creará al aplicar." if _safe_text(basics.get("bot_name") or wizard.get("bot_name")) else "Falta definir o crear el asistente operativo que operará este flujo."),
        _validation_item(key="industry_confirmed", label="Industria / tipo de operación confirmados", status="green" if _safe_text(wizard.get("vertical_id")) and _safe_text(wizard.get("subvertical") or fit.get("subvertical")) else "yellow" if _safe_text(wizard.get("vertical_id")) else "red", detail="Industria y tipo de operación ya están confirmados." if _safe_text(wizard.get("vertical_id")) and _safe_text(wizard.get("subvertical") or fit.get("subvertical")) else "La industria existe, pero todavía falta cerrar el tipo de operación." if _safe_text(wizard.get("vertical_id")) else "Falta confirmar la industria y el tipo de operación."),
        _validation_item(key="pack_generated", label="Pack generado", status="green" if pack_generated else "red", detail="El pack ya tiene estructura sembrable para templates, servicios, knowledge y reglas." if pack_generated else "Todavía no existe un pack suficientemente armado para aplicar o auditar."),
        _validation_item(key="handoff_defined", label="Handoff definido", status="green" if handoff_signals >= 3 else "yellow" if handoff_signals else "red", detail="Escalamiento, keywords, SLA y canal humano quedaron suficientemente explícitos." if handoff_signals >= 3 else "Hay señales de handoff, pero todavía no está completo el paquete de operación humana." if handoff_signals else "Faltan reglas visibles de escalamiento y handoff antes de operar."),
        _validation_item(key="primary_channel_defined", label="Canal principal definido", status="green" if has_connected_channel else "yellow" if has_defined_channel else "red", detail="Ya se detecta un canal operativo conectado." if has_connected_channel else "El canal está planeado o sugerido, pero todavía no aparece conectado." if has_defined_channel else "Todavía no hay canal principal definido para salida."),
        _validation_item(key="critical_integration", label="Integración crítica conectada o planeada", status="green" if connected_required > 0 or (has_connected_channel and not required_integrations) else "yellow" if planned_required > 0 or selected_integrations else "red", detail="Al menos una integración crítica ya aparece conectada." if connected_required > 0 or (has_connected_channel and not required_integrations) else "La integración crítica ya está planeada, pero todavía no aparece conectada." if planned_required > 0 or selected_integrations else "No se ve integración crítica conectada ni planeada."),
        _validation_item(key="basic_simulation", label="Simulación básica aprobada", status="green" if simulation_approved else "yellow" if simulation.get("status") == "needs_review" else "red", detail="La simulación básica ya pasó con evidencia posterior al apply actual." if simulation_approved else "Ya hay una simulación, pero todavía no alcanza una aprobación clara de salida." if simulation.get("status") == "needs_review" else "Todavía no existe una simulación básica aprobada."),
        _validation_item(key="release_ready", label="Release listo", status="green" if release_state.get("has_published") else "yellow" if simulation_approved and has_connected_channel and (wizard.get("status") == "applied" or apply_ready or release_state.get("has_request")) else "red", detail="El release ya fue publicado y el cambio puede operar en vivo." if release_state.get("has_published") else "El cambio ya quedó listo para publicar, pero todavía no sale a producción." if simulation_approved and has_connected_channel and (wizard.get("status") == "applied" or apply_ready or release_state.get("has_request")) else "Todavía no está listo para publicar este cambio con seguridad."),
    ]
    counts = _counts_from_validation_items(checklist)
    blocking_reds = [item for item in checklist if item.get("blocking") and item.get("status") == "red"]
    gate_status = "green" if release_state.get("has_published") and has_connected_channel and simulation_approved and not blocking_reds else "red" if blocking_reds or (wizard.get("bot_id") and not apply_ready and wizard.get("status") != "applied") else "yellow"
    gate_label = "Listo para operar" if gate_status == "green" else "Salida parcial o pendiente" if gate_status == "yellow" else "Bloqueado para salida"
    gate_detail = "El cambio ya tiene contexto, canal, simulación y release suficientes para operar." if gate_status == "green" else "Todavía faltan pasos operativos antes de salir a producción." if gate_status == "yellow" else "La checklist todavía tiene bloqueos importantes para operar sin riesgo."
    scorecard = _build_vertical_scorecard(wizard=wizard, setup=setup, bot_row=bot_row)
    return {
        "generated_at": utcnow_iso(),
        "source": source,
        "mode": "reconfigure" if wizard.get("bot_id") else "create",
        "validation_hash": validation_hash,
        "apply_ready": bool(apply_ready),
        "gate": {"status": gate_status, "label": gate_label, "detail": gate_detail},
        "counts": counts,
        "diff_summary": diff_summary,
        "checklist": checklist,
        "simulation_result": simulation,
        "warnings": warnings,
        "next_cta": next_cta,
        "scorecard": scorecard,
        "exit_score": exit_score or {},
    }


def refresh_guided_onboarding_validation_snapshot(conn: Any, *, wizard_id: str, source: str = "refresh") -> dict[str, Any]:
    ensure_guided_vertical_onboarding_schema(conn)
    wizard = get_guided_onboarding_wizard(conn, wizard_id)
    if not wizard:
        raise ValueError("wizard_not_found")
    previous_snapshot = _as_record(wizard.get("validation_snapshot"))
    answers = _as_record(wizard.get("answers"))
    validation = _as_record(answers.get("dry_run_validation"))
    profile = get_vertical_profile(wizard.get("vertical_id"))
    setup = wizard.get("setup") or _build_setup_payload(
        profile=profile,
        subvertical=wizard.get("subvertical"),
        answers=wizard.get("answers") or {},
        bot_id=wizard.get("bot_id"),
    )
    bot_row = fetch_one(conn, "SELECT * FROM bots WHERE id = ? AND organization_id = ?", (wizard.get("bot_id"), wizard.get("organization_id"))) if wizard.get("bot_id") else None
    org_row = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (wizard.get("organization_id"),)) if wizard.get("organization_id") else None
    snapshot = _build_validation_snapshot(
        conn,
        wizard=wizard,
        bot_row=bot_row,
        org_row=org_row,
        setup=setup,
        diff_summary=list(previous_snapshot.get("diff_summary") or []),
        warnings=list(previous_snapshot.get("warnings") or []),
        apply_ready=bool(validation.get("apply_ready") if validation else wizard.get("status") == "applied"),
        validation_hash=_safe_text(validation.get("validation_hash") or previous_snapshot.get("validation_hash")),
        source=source,
        exit_score=_as_record(previous_snapshot.get("exit_score")),
    )
    recompute_state = _as_record(wizard.get("recompute_state"))
    recompute_state["validation_snapshot_pending"] = False
    recompute_state["dry_run_pending"] = False if validation else bool(recompute_state.get("dry_run_pending"))
    recompute_state["last_snapshot_source"] = source
    if snapshot != previous_snapshot or recompute_state != _as_record(wizard.get("recompute_state")):
        execute(conn, "UPDATE vertical_onboarding_wizards SET validation_snapshot_json = ?, recompute_state_json = ? WHERE id = ?", (to_json(snapshot), to_json(recompute_state), wizard_id))
        _append_wizard_event(
            conn,
            wizard_id=wizard_id,
            organization_id=wizard.get("organization_id"),
            bot_id=wizard.get("bot_id"),
            event_type="wizard.validation_snapshot_refreshed",
            payload={"source": source, "gate_status": _as_record(snapshot.get("gate")).get("status"), "apply_ready": bool(snapshot.get("apply_ready"))},
        )
        wizard = get_guided_onboarding_wizard(conn, wizard_id) or wizard
    else:
        wizard["validation_snapshot"] = snapshot
        wizard["recompute_state"] = recompute_state
    return wizard


def dry_run_guided_onboarding_wizard(conn: Any, *, wizard_id: str) -> dict[str, Any]:
    ensure_guided_vertical_onboarding_schema(conn)
    wizard = get_guided_onboarding_wizard(conn, wizard_id)
    if not wizard:
        raise ValueError("wizard_not_found")

    profile = get_vertical_profile(wizard.get("vertical_id"))
    setup = wizard.get("setup") or _build_setup_payload(
        profile=profile,
        subvertical=wizard.get("subvertical"),
        answers=wizard.get("answers") or {},
        bot_id=wizard.get("bot_id"),
    )
    answers = deepcopy(wizard.get("answers") or {})
    fit = _as_record(answers.get("vertical_fit"))
    basics = _as_record(answers.get("business_basics"))
    catalog = _as_record(answers.get("catalog_offer"))
    knowledge = _as_record(answers.get("knowledge_seed"))
    integrations = _as_record(answers.get("integrations_rules"))
    launch = _as_record(answers.get("launch_review"))

    org_row = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (wizard["organization_id"],)) or {}
    bot_row = fetch_one(conn, "SELECT * FROM bots WHERE id = ? AND organization_id = ?", (wizard.get("bot_id"), wizard["organization_id"])) if wizard.get("bot_id") else None
    bot_config = from_json(bot_row.get("config_draft_json"), {}) if bot_row else {}
    bot_config = bot_config if isinstance(bot_config, dict) else {}
    behavior_row = get_bot_behavior_settings(conn, wizard["organization_id"], wizard["bot_id"]) if wizard.get("bot_id") and bot_row else {}
    current_catalog_rows = list_catalog_services(conn, wizard["organization_id"], wizard.get("bot_id")) if wizard.get("bot_id") and bot_row else []
    current_template_rows = list_bot_response_templates(conn, wizard["organization_id"], wizard.get("bot_id")) if wizard.get("bot_id") and bot_row else []

    current_vertical = _safe_text(bot_row.get("vertical") if bot_row else None, "Sin vertical")
    next_vertical = _safe_text(profile.get("name") or wizard.get("vertical_id"), _safe_text(wizard.get("vertical_id"), "Sin vertical"))
    current_subvertical = _safe_text(bot_config.get("selected_subvertical") or bot_config.get("subvertical") or org_row.get("subvertical"), "Sin subvertical")
    next_subvertical = _safe_text(wizard.get("subvertical") or fit.get("subvertical"), "Sin subvertical")
    current_objective = _safe_text(bot_config.get("primary_objective") or _as_record(bot_config.get("objective")).get("primary") or (bot_row or {}).get("objective"), "Sin objetivo visible")
    next_objective = _safe_text(fit.get("primary_objective") or wizard.get("primary_objective"), "Sin objetivo definido")
    current_tone = _safe_text(_read_nested_string(bot_config, ["personality", "tone"], "") or _read_nested_string(bot_config, ["behavior_settings", "tone"], "") or behavior_row.get("tone"), "Sin tono visible")
    next_tone = _safe_text(_read_nested_string(setup, ["personality", "tone"], "") or _read_nested_string(setup, ["behavior_settings", "tone"], "") or wizard.get("tone"), "Segun defaults")
    current_response_length = _safe_text(_read_nested_string(bot_config, ["personality", "response_length"], "") or _read_nested_string(bot_config, ["behavior_settings", "response_length"], "") or behavior_row.get("response_length"), "Sin longitud visible")
    next_response_length = _safe_text(_read_nested_string(setup, ["personality", "response_length"], "") or _read_nested_string(setup, ["behavior_settings", "response_length"], ""), "Segun defaults")
    current_sales_intensity = _safe_text(_read_nested_string(bot_config, ["personality", "sales_intensity"], "") or _read_nested_string(bot_config, ["behavior_settings", "sales_intensity"], "") or behavior_row.get("sales_intensity"), "Sin intensidad visible")
    next_sales_intensity = _safe_text(_read_nested_string(setup, ["personality", "sales_intensity"], "") or _read_nested_string(setup, ["behavior_settings", "sales_intensity"], ""), "Segun defaults")

    current_services = _unique_strings([*( _read_nested_strings(bot_config, ["business_knowledge", "services"])), *[str(item.get("name") or "").strip() for item in current_catalog_rows]])
    next_services = _unique_strings(list(catalog.get("services") or setup.get("services") or []))
    current_featured_offers = _read_nested_strings(bot_config, ["business_knowledge", "promotions"])
    next_featured_offers = _unique_strings(list(_as_record(setup.get("wizard")).get("featured_offers") or []))
    current_ctas = _cta_labels(bot_config.get("recommended_ctas") or [])
    next_ctas = _cta_labels(_as_record(setup.get("wizard")).get("recommended_ctas") or [])

    current_faqs = _faq_labels(_as_record(bot_config.get("business_knowledge")).get("faqs") or [])
    next_faqs = _faq_labels(knowledge.get("faqs") or [])
    current_policies = _read_nested_strings(bot_config, ["business_knowledge", "policies"])
    next_policies = _unique_strings(list(knowledge.get("policies") or _as_record(setup.get("wizard")).get("policies") or []))
    current_knowledge_sources = _unique_strings([_safe_text(_as_record(item).get("label") or _as_record(item).get("connector_key") or _as_record(item).get("provider") or item) for item in list(bot_config.get("knowledge_sources") or [])])
    next_knowledge_sources = _unique_strings([_safe_text(_as_record(item).get("label") or _as_record(item).get("connector_key") or _as_record(item).get("provider") or item) for item in list(_as_record(setup.get("wizard")).get("knowledge_sources") or [])])

    current_templates = _unique_strings([*(_pick_template_labels(bot_config)), *(_template_labels_from_rows(current_template_rows))])
    next_templates = _pick_template_labels(_as_record(setup))

    current_escalate = _unique_strings([*(_read_nested_strings(bot_config, ["rules", "escalate_when"])), *(list(behavior_row.get("escalate_when") or []))])
    next_escalate = _unique_strings(list((_as_record(setup.get("rules")).get("escalate_when") or []) or []))
    current_handoff = _unique_strings(_read_nested_strings(bot_config, ["handoff", "sensitive_keywords"]))
    next_handoff = _unique_strings(list(integrations.get("handoff_keywords") or _as_record(setup.get("handoff")).get("sensitive_keywords") or []))
    current_handoff_sla = _safe_text(_read_nested_string(bot_config, ["handoff", "expected_sla"]), "Sin SLA visible")
    next_handoff_sla = _safe_text(integrations.get("expected_handoff_sla"), _safe_text(_as_record(setup.get("handoff")).get("expected_sla"), _default_handoff_sla(next_objective)))
    current_handoff_channel = _safe_text(_read_nested_string(bot_config, ["handoff", "destination_channel"]), _safe_text(_read_nested_string(bot_config, ["handoff", "channel"]), "Sin canal humano visible"))
    next_handoff_channel = _safe_text(integrations.get("human_destination_channel"), _safe_text(_as_record(setup.get("handoff")).get("destination_channel"), _default_handoff_channel(profile)))
    current_override_rules = _as_record(_as_record(bot_config.get("handoff")).get("override_rules")) or _as_record(bot_config.get("rules"))
    next_override_rules = _as_record(integrations.get("rule_overrides")) or _as_record(_as_record(setup.get("handoff")).get("override_rules"))
    current_followups = _unique_strings([_safe_text(_as_record(item).get("type") or _as_record(item).get("message_template")) for item in list(_as_record(bot_config.get("followups")).get("rules") or [])])
    next_followups = _unique_strings([_safe_text(_as_record(item).get("type") or _as_record(item).get("message_template")) for item in list(_as_record(setup.get("followups")).get("rules") or [])])

    current_integrations = _unique_strings(list(_as_record(bot_config.get("integrations")).keys()))
    next_integrations = _unique_strings([_integration_identity(item) for item in list(integrations.get("selected_integrations") or _as_record(setup.get("wizard")).get("recommended_integrations") or [])])
    current_channels = _unique_strings(list(behavior_row.get("active_channels") or []) or list(_as_record(bot_config.get("integrations")).keys()))
    next_channels = _unique_strings(list(_as_record(setup.get("integrations")).keys()) or list(_as_record(setup.get("behavior_settings")).get("active_channels") or []))

    diff_domains = [
        _build_diff_domain(
            key="tone_prompt",
            label="Tono y prompt",
            detail="Aquí ves si cambia la manera de hablar del asistente, la longitud de respuesta o la presión comercial antes de tocar el draft.",
            items=[
                _scalar_diff_item(key="tone", label="Tono", before=current_tone if bot_row else "Se definirá al crear", after=next_tone, detail="Cambio principal de voz y encuadre conversacional.", unit="tono base"),
                _scalar_diff_item(key="response_length", label="Longitud de respuesta", before=current_response_length if bot_row else "Se definirá al crear", after=next_response_length, detail="Afecta qué tan breve o extensa suena la respuesta.", unit="ajuste de respuesta"),
                _scalar_diff_item(key="sales_intensity", label="Intensidad comercial", before=current_sales_intensity if bot_row else "Se definirá al crear", after=next_sales_intensity, detail="Hace explícito si el pack empuja más o menos al cierre.", unit="ajuste comercial"),
            ],
        ),
        _build_diff_domain(
            key="services_catalog",
            label="Servicios y catálogo",
            detail="Separa oferta, bundles y CTAs para que el usuario entienda exactamente qué parte comercial va a mutar.",
            items=[
                _list_diff_item(key="services", label="Servicios", before=current_services, after=next_services, detail="Servicios operativos o de catálogo sembrados en el draft.", unit="servicios", empty_before="Sin servicios visibles", empty_after="No se agregarán servicios nuevos"),
                _list_diff_item(key="offers", label="Ofertas destacadas", before=current_featured_offers, after=next_featured_offers, detail="Promesas comerciales o bundles destacados que aparecerán en el pack.", unit="ofertas", empty_before="Sin ofertas destacadas visibles", empty_after="No se sembrarán ofertas destacadas"),
                _list_diff_item(key="ctas", label="CTAs principales", before=current_ctas, after=next_ctas, detail="Acciones sugeridas para mover la conversación al siguiente paso.", unit="CTAs", empty_before="Sin CTAs visibles", empty_after="No cambia el set de CTAs"),
            ],
        ),
        _build_diff_domain(
            key="knowledge",
            label="FAQs / knowledge",
            detail="Muestra si el pack agrega, quita o reemplaza conocimiento operativo antes del apply real.",
            items=[
                _list_diff_item(key="faqs", label="FAQs", before=current_faqs, after=next_faqs, detail="Preguntas y respuestas rápidas visibles para el asistente.", unit="FAQs", empty_before="Sin FAQs visibles", empty_after="No se sembrarán FAQs nuevas"),
                _list_diff_item(key="policies", label="Policy pack", before=current_policies, after=next_policies, detail="Políticas operativas, comerciales o de compliance del pack.", unit="policy pack", empty_before="Sin policy pack visible", empty_after="No habrá policy pack nuevo"),
                _list_diff_item(key="sources", label="Fuentes de knowledge", before=current_knowledge_sources, after=next_knowledge_sources, detail="Repositorios o fuentes desde donde el pack espera leer contenido vivo.", unit="fuentes", empty_before="Sin fuentes visibles", empty_after="No hay fuentes nuevas priorizadas"),
            ],
        ),
        _build_diff_domain(
            key="templates",
            label="Templates",
            detail="Hace operable el impacto sobre mensajes sembrados y respuestas reutilizables.",
            items=[
                _list_diff_item(key="templates", label="Templates del pack", before=current_templates, after=next_templates, detail="Mensajes sembrados o respuestas sugeridas que pueden reemplazar el set actual.", unit="templates", empty_before="Sin templates visibles hoy", empty_after="No se aplicarán templates del pack"),
            ],
        ),
        _build_diff_domain(
            key="handoff_rules_followups",
            label="Handoff / reglas / followups",
            detail="Aclara qué cambia en escalamiento, protección operacional y seguimiento automático.",
            items=[
                _list_diff_item(key="escalate", label="Escalar cuando", before=current_escalate, after=next_escalate, detail="Condiciones que obligan a elevar a humano o a una revisión más estricta.", unit="reglas de escalamiento", empty_before="Sin reglas de escalamiento visibles", empty_after="No cambian las reglas de escalamiento"),
                _list_diff_item(key="handoff", label="Palabras de handoff", before=current_handoff, after=next_handoff, detail="Palabras o señales que disparan traspaso a humano.", unit="palabras de handoff", empty_before="Sin keywords visibles", empty_after="No cambian los keywords de handoff"),
                _scalar_diff_item(key="handoff_sla", label="SLA esperado", before=current_handoff_sla, after=next_handoff_sla, detail="Tiempo esperado para que el caso llegue a humano una vez detectado el handoff.", unit="SLA"),
                _scalar_diff_item(key="handoff_channel", label="Canal humano destino", before=current_handoff_channel, after=next_handoff_channel, detail="Equipo o superficie humana a la que se debe escalar el caso.", unit="canal humano"),
                _scalar_diff_item(key="override_rules", label="Reglas override", before=_json_summary(current_override_rules), after=_json_summary(next_override_rules), detail="Resumen de reglas que el operador permite o restringe además del pack base.", unit="override pack"),
                _list_diff_item(key="followups", label="Followups", before=current_followups, after=next_followups, detail="Tipos de seguimiento automático que el pack deja listos.", unit="followups", empty_before="Sin followups visibles", empty_after="No cambia el set de followups"),
            ],
        ),
        _build_diff_domain(
            key="integrations",
            label="Integraciones",
            detail="Separa dependencias técnicas y paquetes de integración sugeridos para que el apply no sorprenda después.",
            items=[
                _list_diff_item(key="integrations", label="Integraciones sugeridas", before=current_integrations, after=next_integrations, detail="Conectores o integraciones que el pack prioriza revisar o activar.", unit="integraciones", empty_before="Sin integraciones visibles", empty_after="No hay nuevas integraciones sugeridas"),
            ],
        ),
        _build_diff_domain(
            key="objective",
            label="Objetivo principal",
            detail="Este bloque deja claro si la operación apunta a agendar, vender, calificar, responder o reactivar.",
            items=[
                _scalar_diff_item(key="objective", label="Objetivo operativo", before=current_objective if bot_row else "Se definirá al crear", after=next_objective, detail="El objetivo altera followups, calificadores, handoff y rutas de cierre.", unit="objetivo"),
                _scalar_diff_item(key="vertical", label="Vertical", before=current_vertical if bot_row else "Bot nuevo", after=next_vertical, detail="La vertical define el marco principal del pack y sus defaults fuertes.", unit="vertical"),
                _scalar_diff_item(key="subvertical", label="Subvertical", before=current_subvertical if bot_row else "Se confirmará al crear", after=next_subvertical, detail="La subvertical aterriza el bundle y los ejemplos operativos sembrados.", unit="subvertical"),
            ],
        ),
        _build_diff_domain(
            key="channels",
            label="Canales",
            detail="Se ve por separado para que el usuario no confunda activación de canales con integraciones sugeridas.",
            items=[
                _list_diff_item(key="channels", label="Canales activos", before=current_channels, after=next_channels, detail="Superficies donde el asistente quedará visible o activo tras aplicar el pack.", unit="canales", empty_before="Sin canales visibles", empty_after="No cambia el set de canales"),
            ],
        ),
    ]

    diff_summary = _compact_diff_summary(diff_domains)

    checklist = [
        {"key": "bot_scope", "label": "Asistente operativo explicitamente seleccionado", "completed": bool(bot_row) if wizard.get("bot_id") else True, "required": bool(wizard.get("bot_id"))},
        {"key": "vertical", "label": "Vertical confirmada", "completed": bool(wizard.get("vertical_id")), "required": True},
        {"key": "subvertical", "label": "Subvertical confirmada", "completed": bool(wizard.get("subvertical") or fit.get("subvertical")), "required": True},
        {"key": "objective", "label": "Objetivo operativo definido", "completed": bool(fit.get("primary_objective") or wizard.get("primary_objective")), "required": True},
        {"key": "catalog", "label": "Oferta y servicios base visibles", "completed": bool(next_services), "required": not bool(bot_row)},
        {"key": "knowledge", "label": "FAQ o politicas listas para validar", "completed": bool(parse := (list(knowledge.get("faqs") or []) or next_policies)), "required": not bool(bot_row)},
        {"key": "integrations", "label": "Integraciones o canales priorizados", "completed": bool(next_integrations), "required": True},
        {"key": "launch_review", "label": "Launch review preparado", "completed": bool(launch.get("launch_notes") or launch.get("recommended_playbooks") or wizard.get("current_step") == "launch_review"), "required": False},
    ]

    conflicts: list[dict[str, Any]] = []
    if wizard.get("bot_id") and not bot_row:
        conflicts.append({"key": "bot_missing", "severity": "blocking", "label": "No existe el bot a reconfigurar", "detail": "El dry-run no puede validar impacto real porque el asistente operativo seleccionado ya no existe o no pertenece al tenant."})
    if not wizard.get("vertical_id"):
        conflicts.append({"key": "vertical_missing", "severity": "blocking", "label": "Falta confirmar la vertical", "detail": "Antes de aplicar debes fijar una vertical explicita."})
    if not (wizard.get("subvertical") or fit.get("subvertical")):
        conflicts.append({"key": "subvertical_missing", "severity": "blocking", "label": "Falta confirmar la subvertical", "detail": "El flujo queda bloqueado hasta que el usuario confirme explicitamente el tipo de operacion."})
    if wizard.get("bot_id") and bot_row and current_vertical.lower() == next_vertical.lower() and current_subvertical.lower() == next_subvertical.lower() and current_objective.lower() == next_objective.lower():
        conflicts.append({"key": "no_material_change", "severity": "blocking", "label": "No hay cambio material que aplicar", "detail": "La prevalidacion detecta que vertical, subvertical y objetivo siguen iguales. No conviene aplicar una reconfiguracion dura sin cambio real."})

    risks: list[dict[str, Any]] = []
    if bot_row:
        risks.append({"key": "snapshot", "severity": "high", "label": "Snapshot preventivo obligatorio", "detail": "Como es una reconfiguracion sobre un bot existente, el apply debe mantener snapshot previo para rollback."})
    if bot_row and current_vertical.lower() != next_vertical.lower():
        risks.append({"key": "vertical_shift", "severity": "high", "label": "Cambio de vertical con defaults fuertes", "detail": "Cambiar industria puede recalcular reglas, agenda, followups, personality y otras superficies duras."})
    if next_templates:
        risks.append({"key": "templates_replace", "severity": "high", "label": "Templates y respuestas pueden cambiar", "detail": "El pack candidato trae templates visibles que pueden reemplazar o complementar los existentes."})
    if next_services or next_policies:
        risks.append({"key": "knowledge_reset", "severity": "medium", "label": "Servicios, FAQ o politicas pueden resembrarse", "detail": "La oferta y la knowledge base visible deben revisarse porque el apply puede mover el encuadre operativo."})
    if not next_integrations:
        risks.append({"key": "integration_gap", "severity": "medium", "label": "No hay integraciones priorizadas", "detail": "El dry-run no ve canales o integraciones marcadas. El apply quedaria menos verificable operativamente."})

    completed_required = sum(1 for item in checklist if item.get("required") and item.get("completed"))
    total_required = sum(1 for item in checklist if item.get("required")) or len(checklist)
    base_score = round((completed_required / total_required) * 100)
    penalty = sum(18 for _ in conflicts) + sum(10 if item.get("severity") == "high" else 5 for item in risks)
    exit_value = max(0, min(100, base_score - penalty))
    exit_tone = "success" if not conflicts and exit_value >= 80 else "warning" if not conflicts and exit_value >= 60 else "danger"
    exit_label = "Listo para aplicar" if exit_tone == "success" else "Aplicable con atencion" if exit_tone == "warning" else "Bloqueado o riesgoso"
    validation_hash = _build_dry_run_signature(wizard)
    apply_ready = not conflicts and exit_value >= 60
    validated_at = utcnow_iso()

    answers["dry_run_validation"] = {
        "validated_at": validated_at,
        "validation_hash": validation_hash,
        "wizard_revision": int(wizard.get("wizard_revision") or 1),
        "apply_ready": apply_ready,
        "exit_score": exit_value,
        "conflicts": len(conflicts),
        "risks": len(risks),
    }
    validation_snapshot = _build_validation_snapshot(
        conn,
        wizard=wizard,
        bot_row=bot_row,
        org_row=org_row,
        setup=setup,
        diff_summary=_compact_diff_summary(diff_domains),
        warnings=[*conflicts, *risks],
        apply_ready=apply_ready,
        validation_hash=validation_hash,
        source="dry_run",
        exit_score={"value": exit_value, "label": exit_label, "tone": exit_tone},
    )
    recompute_state = _as_record(wizard.get("recompute_state"))
    recompute_state["validation_snapshot_pending"] = False
    recompute_state["dry_run_pending"] = False
    recompute_state["last_snapshot_source"] = "dry_run"
    execute(conn, "UPDATE vertical_onboarding_wizards SET answers_json = ?, validation_snapshot_json = ?, recompute_state_json = ?, updated_at = ? WHERE id = ?", (to_json(answers), to_json(validation_snapshot), to_json(recompute_state), validated_at, wizard_id))
    _append_wizard_event(
        conn,
        wizard_id=wizard_id,
        organization_id=wizard.get("organization_id"),
        bot_id=wizard.get("bot_id"),
        event_type="wizard.dry_run_completed",
        payload={"apply_ready": bool(apply_ready), "validation_hash": validation_hash, "exit_score": exit_value, "conflicts": len(conflicts), "risks": len(risks)},
        created_at=validated_at,
    )
    updated_wizard = get_guided_onboarding_wizard(conn, wizard_id) or wizard

    return {
        "wizard": updated_wizard,
        "validation_snapshot": validation_snapshot,
        "validation_hash": validation_hash,
        "diff_summary": diff_summary,
        "diff_domains": diff_domains,
        "handoff_preview": {
            "current": {
                "escalate_when": current_escalate,
                "handoff_keywords": current_handoff,
                "expected_handoff_sla": current_handoff_sla,
                "human_destination_channel": current_handoff_channel,
                "rule_overrides": current_override_rules,
            },
            "proposed": {
                "escalate_when": next_escalate,
                "handoff_keywords": next_handoff,
                "expected_handoff_sla": next_handoff_sla,
                "human_destination_channel": next_handoff_channel,
                "rule_overrides": next_override_rules,
            },
        },
        "risks": risks,
        "conflicts": conflicts,
        "checklist": checklist,
        "exit_score": {"value": exit_value, "label": exit_label, "tone": exit_tone},
        "summary": {
            "mode": "reconfigure" if bot_row else "create",
            "snapshot_required": bool(bot_row),
            "apply_ready": apply_ready,
            "validated_at": validated_at,
            "bot_id": updated_wizard.get("bot_id"),
            "organization_id": updated_wizard.get("organization_id"),
        },
    }


def _knowledge_seed_documents(*, wizard: dict[str, Any], setup: dict[str, Any]) -> list[dict[str, Any]]:
    answers = wizard.get("answers") or {}
    basics = answers.get("business_basics") or {}
    knowledge = answers.get("knowledge_seed") or {}
    catalog = answers.get("catalog_offer") or {}
    business_name = str(basics.get("business_name") or wizard.get("business_name") or "Negocio WAOS")
    docs: list[dict[str, Any]] = []

    faqs = list(knowledge.get("faqs") or [])
    if faqs:
        lines = [f"{item.get('q')}: {item.get('a')}" for item in faqs if item.get("q") and item.get("a")]
        docs.append({
            "title": f"FAQ base {business_name}",
            "source_key": f"guided-onboarding:{wizard['id']}:faq",
            "source_kind": "faq",
            "domain": "support",
            "supports": ["faq", "support"],
            "content_text": "\n".join(lines),
            "tags": ["guided_onboarding", "faq", wizard.get("vertical_id")],
            "metadata": {"wizard_id": wizard["id"], "kind": "faq_seed"},
        })

    policies = list(knowledge.get("policies") or [])
    if policies:
        docs.append({
            "title": f"Politicas operativas {business_name}",
            "source_key": f"guided-onboarding:{wizard['id']}:policies",
            "source_kind": "policy",
            "domain": "support",
            "supports": ["support", "schedule", "payment"],
            "content_text": "\n".join(f"- {item}" for item in policies),
            "tags": ["guided_onboarding", "policies", wizard.get("vertical_id")],
            "metadata": {"wizard_id": wizard["id"], "kind": "policy_seed"},
        })

    facts = []
    if basics.get("hours"):
        facts.append(f"Horario: {basics.get('hours')}")
    if catalog.get("pricing_notes"):
        facts.extend([f"Nota de precio: {item}" for item in catalog.get("pricing_notes") or []])
    if catalog.get("featured_offers"):
        facts.extend([f"Oferta destacada: {item}" for item in catalog.get("featured_offers") or []])
    if setup.get("services"):
        facts.append("Servicios base: " + ", ".join(str(item) for item in setup.get("services") or []))
    if facts:
        docs.append({
            "title": f"Contexto base {business_name}",
            "source_key": f"guided-onboarding:{wizard['id']}:facts",
            "source_kind": "config_seed",
            "domain": "operational",
            "supports": ["schedule", "pricing", "support"],
            "content_text": "\n".join(facts),
            "tags": ["guided_onboarding", "facts", wizard.get("vertical_id")],
            "metadata": {"wizard_id": wizard["id"], "kind": "facts_seed"},
        })
    return docs



def _require_fresh_guided_onboarding_apply_validation(wizard: dict[str, Any]) -> dict[str, Any]:
    recompute_state = _as_record(wizard.get("recompute_state"))
    answers = _as_record(wizard.get("answers"))
    validation = _as_record(answers.get("dry_run_validation"))
    validated_revision = int(validation.get("wizard_revision") or 0)
    current_revision = int(wizard.get("wizard_revision") or 0)
    if recompute_state.get("validation_snapshot_pending") or recompute_state.get("dry_run_pending"):
        raise ValueError("dry_run_required")
    if not validation or not validated_revision or validated_revision != current_revision:
        raise ValueError("dry_run_required")
    if validation.get("validation_hash") != _build_dry_run_signature(wizard):
        raise ValueError("dry_run_required")
    if not bool(validation.get("apply_ready")):
        raise ValueError("dry_run_blocked")
    return validation

def apply_guided_onboarding_wizard(conn: Any, *, wizard_id: str, actor_user: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_guided_vertical_onboarding_schema(conn)
    wizard = get_guided_onboarding_wizard(conn, wizard_id)
    if not wizard:
        raise ValueError("wizard_not_found")
    if not _as_record(wizard.get("validation_snapshot")):
        preflight = dry_run_guided_onboarding_wizard(conn, wizard_id=wizard_id)
        wizard = preflight.get("wizard") or get_guided_onboarding_wizard(conn, wizard_id) or wizard
    _require_fresh_guided_onboarding_apply_validation(wizard)
    profile = get_vertical_profile(wizard.get("vertical_id"))
    setup = wizard.get("setup") or _build_setup_payload(
        profile=profile,
        subvertical=wizard.get("subvertical"),
        answers=wizard.get("answers") or {},
        bot_id=wizard.get("bot_id"),
    )
    answers = wizard.get("answers") or {}
    basics = answers.get("business_basics") or {}
    fit = answers.get("vertical_fit") or {}
    integrations = answers.get("integrations_rules") or {}

    now = utcnow_iso()
    org_row = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (wizard["organization_id"],)) or {}
    bot_row = fetch_one(conn, "SELECT * FROM bots WHERE id = ? AND organization_id = ?", (wizard.get("bot_id"), wizard["organization_id"])) if wizard.get("bot_id") else None
    if not bot_row:
        if not actor_user:
            raise ValueError("wizard_requires_bot")
        from .repositories.bots import create_bot

        created = create_bot(
            conn,
            organization_id=wizard["organization_id"],
            business_name=str(basics.get("business_name") or wizard.get("business_name") or org_row.get("name") or "Negocio WAOS"),
            vertical=str(wizard.get("vertical_id") or profile.get("id") or "general"),
            bot_name=str(basics.get("bot_name") or wizard.get("bot_name") or f"Bot {org_row.get('name') or 'WAOS'}"),
            primary_objective=str(fit.get("primary_objective") or wizard.get("primary_objective") or "agendar"),
            tone=str(basics.get("tone") or wizard.get("tone") or "amable"),
            language=str(basics.get("language") or wizard.get("language") or "es"),
            timezone=str(basics.get("timezone") or wizard.get("timezone") or org_row.get("timezone") or "America/Mexico_City"),
            services=list((setup.get("services") or [])[:12]),
            hours=str(basics.get("hours") or ""),
            faqs=list((answers.get("knowledge_seed") or {}).get("faqs") or []),
            whatsapp_number=str(basics.get("whatsapp_number") or ""),
            publish_now=False,
            created_by=actor_user,
        ) or {}
        bot_id = created.get("id")
        if not bot_id:
            raise ValueError("bot_not_found")
        execute(conn, "UPDATE vertical_onboarding_wizards SET bot_id = ?, updated_at = ? WHERE id = ?", (bot_id, now, wizard_id))
        execute(conn, "UPDATE vertical_onboarding_step_runs SET bot_id = ?, updated_at = ? WHERE wizard_id = ?", (bot_id, now, wizard_id))
        wizard["bot_id"] = bot_id
        bot_row = fetch_one(conn, "SELECT * FROM bots WHERE id = ? AND organization_id = ?", (bot_id, wizard["organization_id"])) or {}
    if not bot_row:
        raise ValueError("bot_not_found")

    if wizard.get("bot_id") and actor_user:
        versions = fetch_all(conn, "SELECT * FROM bot_versions WHERE bot_id = ? ORDER BY version_number DESC", (wizard["bot_id"],))
        next_number = 1 if not versions else max(int(item.get("version_number") or 0) for item in versions) + 1
        execute(
            conn,
            "INSERT INTO bot_versions (id, organization_id, bot_id, version_number, status, config_json, created_by, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id("bver"),
                wizard["organization_id"],
                wizard["bot_id"],
                next_number,
                "draft_snapshot",
                bot_row.get("config_draft_json") or "{}",
                actor_user.get("id"),
                f"Guided onboarding snapshot before apply {wizard_id}",
                now,
            ),
        )

    org_settings = from_json(org_row.get("settings_json"), {}) if org_row else {}
    org_settings = org_settings if isinstance(org_settings, dict) else {}
    org_settings["guided_onboarding"] = {
        "wizard_id": wizard_id,
        "vertical_id": wizard.get("vertical_id"),
        "subvertical": wizard.get("subvertical"),
        "applied_at": now,
        "version": GUIDED_ONBOARDING_VERSION,
    }
    execute(conn, "UPDATE organizations SET vertical = ?, settings_json = ?, updated_at = ? WHERE id = ?", (wizard.get("vertical_id"), to_json(org_settings), now, wizard["organization_id"]))

    bot_config = from_json(bot_row.get("config_draft_json"), {}) if bot_row else {}
    bot_config = bot_config if isinstance(bot_config, dict) else {}
    bot_config.update({
        "guided_onboarding": {"wizard_id": wizard_id, "applied_at": now, "version": GUIDED_ONBOARDING_VERSION},
        "primary_objective": fit.get("primary_objective") or wizard.get("primary_objective"),
        "selected_subvertical": wizard.get("subvertical"),
        "recommended_ctas": (setup.get("wizard") or {}).get("recommended_ctas") or [],
        "recommended_playbooks": (setup.get("wizard") or {}).get("recommended_playbooks") or [],
        "knowledge_sources": (setup.get("wizard") or {}).get("knowledge_sources") or [],
    })
    execute(
        conn,
        "UPDATE bots SET vertical = ?, name = ?, business_name = ?, language = ?, timezone = ?, config_draft_json = ?, updated_at = ? WHERE id = ?",
        (
            wizard.get("vertical_id"),
            basics.get("bot_name") or bot_row.get("name"),
            basics.get("business_name") or bot_row.get("business_name"),
            basics.get("language") or bot_row.get("language") or "es",
            basics.get("timezone") or bot_row.get("timezone") or "America/Mexico_City",
            to_json(bot_config),
            now,
            wizard["bot_id"],
        ),
    )

    pack_result = apply_subvertical_pack(
        conn,
        profile=profile,
        organization_id=wizard["organization_id"],
        bot_id=wizard["bot_id"],
        subvertical=wizard.get("subvertical") or fit.get("subvertical"),
        actor_user=actor_user,
    )

    personality = setup.get("personality") or {}
    behavior = setup.get("behavior_settings") or {}
    behavior_row = upsert_bot_behavior_settings(
        conn,
        organization_id=wizard["organization_id"],
        bot_id=wizard["bot_id"],
        tone=str(personality.get("tone") or behavior.get("tone") or wizard.get("tone") or "cercano"),
        response_length=str(personality.get("response_length") or behavior.get("response_length") or "media"),
        use_emojis=bool(personality.get("use_emojis") if personality.get("use_emojis") is not None else behavior.get("use_emojis") or False),
        sales_intensity=str(personality.get("sales_intensity") or behavior.get("sales_intensity") or "media"),
        offer_promotions_when=str(behavior.get("offer_promotions_when") or "when_relevant"),
        escalate_when=list((setup.get("rules") or {}).get("escalate_when") or behavior.get("escalate_when") or []),
        insistence_policy=str(behavior.get("insistence_policy") or "respectful"),
        can_share_price_directly=bool(behavior.get("can_share_price_directly") if behavior.get("can_share_price_directly") is not None else True),
        can_negotiate=bool(behavior.get("can_negotiate") or False),
        can_mention_stock=bool(behavior.get("can_mention_stock") if behavior.get("can_mention_stock") is not None else True),
        auto_send_images=bool(behavior.get("auto_send_images") if behavior.get("auto_send_images") is not None else True),
        bot_mode=str(behavior.get("bot_mode") or "hybrid"),
        active_hours=list(behavior.get("active_hours") or []),
        active_channels=list((setup.get("integrations") or {}).keys() or behavior.get("active_channels") or ["whatsapp"]),
        forbidden_topics=list(behavior.get("forbidden_topics") or []),
        required_phrases=list(behavior.get("required_phrases") or []),
        fallback_message=str(behavior.get("fallback_message") or "Te ayudo con gusto."),
        actor_user=actor_user,
    )

    template_count = 0
    for item in list(setup.get("response_templates") or [])[:8]:
        key = slugify(str(item.get("template_key") or item.get("title") or template_count or "template"))
        upsert_bot_response_template(
            conn,
            organization_id=wizard["organization_id"],
            bot_id=wizard["bot_id"],
            template_key=f"guided-{key}",
            channel="whatsapp",
            title=str(item.get("title") or key),
            content=str(item.get("content") or ""),
            variables=list(item.get("variables") or []),
            actor_user=actor_user,
        )
        template_count += 1

    existing_services = {str(item.get("name") or "").strip().lower() for item in list_catalog_services(conn, wizard["organization_id"], wizard["bot_id"]) }
    created_services: list[str] = []
    for service_name in list(setup.get("services") or [])[:12]:
        normalized_name = str(service_name or "").strip()
        if not normalized_name or normalized_name.lower() in existing_services:
            continue
        create_catalog_service(
            conn,
            organization_id=wizard["organization_id"],
            bot_id=wizard["bot_id"],
            name=normalized_name,
            duration_minutes=int((setup.get("agenda") or {}).get("appointment_duration_minutes") or 30),
            price=0,
            currency="MXN",
            availability={"hours": basics.get("hours") or "por configurar"},
            status="active",
            actor_user=actor_user,
        )
        existing_services.add(normalized_name.lower())
        created_services.append(normalized_name)

    docs_seeded = []
    for item in _knowledge_seed_documents(wizard=wizard, setup=setup):
        docs_seeded.append(
            ingest_knowledge_document(
                conn,
                organization_id=wizard["organization_id"],
                bot_id=wizard["bot_id"],
                title=item["title"],
                source_kind=item["source_kind"],
                source_key=item["source_key"],
                content_text=item["content_text"],
                domain=item["domain"],
                tags=item.get("tags") or [],
                metadata=item.get("metadata") or {},
                supports=item.get("supports") or [],
                owner_type="guided_onboarding",
                refresh_strategy="manual",
            )
        )

    integration_rows = []
    for item in list((setup.get("wizard") or {}).get("recommended_integrations") or [])[:10]:
        config = {"guided_onboarding": True, "wizard_id": wizard_id, "required": bool(item.get("required")), "status_hint": item.get("status") or "planned"}
        if item.get("provider") == "meta_cloud_api" and basics.get("whatsapp_number"):
            config["phone_number"] = basics.get("whatsapp_number")
        if item.get("provider") == "google_calendar":
            config["timezone"] = basics.get("timezone") or wizard.get("timezone") or "America/Mexico_City"
        integration_rows.append(
            _upsert_guided_integration(
                conn,
                organization_id=wizard["organization_id"],
                bot_id=wizard["bot_id"],
                integration_type=str(item.get("integration_type") or "general"),
                provider=str(item.get("provider") or slugify(str(item.get("name") or "integration"))),
                name=str(item.get("name") or item.get("provider") or "Integration"),
                status="planned",
                config=config,
            )
        )


    final_bot_row = fetch_one(conn, "SELECT * FROM bots WHERE id = ? AND organization_id = ?", (wizard["bot_id"], wizard["organization_id"])) or {}
    final_bot_config = from_json(final_bot_row.get("config_draft_json"), {}) if final_bot_row else {}
    final_bot_config = final_bot_config if isinstance(final_bot_config, dict) else {}
    final_bot_config["handoff"] = {
        **_as_record(final_bot_config.get("handoff")),
        "sensitive_keywords": list(integrations.get("handoff_keywords") or _as_record(setup.get("handoff")).get("sensitive_keywords") or []),
        "expected_sla": _safe_text(integrations.get("expected_handoff_sla"), _safe_text(_as_record(setup.get("handoff")).get("expected_sla"), _default_handoff_sla(fit.get("primary_objective") or wizard.get("primary_objective")))),
        "destination_channel": _safe_text(integrations.get("human_destination_channel"), _safe_text(_as_record(setup.get("handoff")).get("destination_channel"), _default_handoff_channel(profile))),
        "override_rules": deepcopy(integrations.get("rule_overrides") or {}),
    }
    execute(conn, "UPDATE bots SET config_draft_json = ?, updated_at = ? WHERE id = ?", (to_json(final_bot_config), now, wizard["bot_id"]))

    applied_summary = {
        "vertical_id": wizard.get("vertical_id"),
        "subvertical": wizard.get("subvertical"),
        "created_services": created_services,
        "template_count": template_count,
        "knowledge_documents": len(docs_seeded),
        "planned_integrations": len(integration_rows),
        "behavior_id": behavior_row.get("id") if behavior_row else None,
        "pack_result": pack_result,
    }
    execute(
        conn,
        "UPDATE vertical_onboarding_wizards SET status = 'applied', applied_at = ?, progress_percent = 100, current_step = 'launch_review', applied_summary_json = ?, updated_at = ? WHERE id = ?",
        (now, to_json(applied_summary), now, wizard_id),
    )
    _append_wizard_event(
        conn,
        wizard_id=wizard_id,
        organization_id=wizard.get("organization_id"),
        bot_id=wizard.get("bot_id"),
        event_type="wizard.applied",
        payload={
            "created_services": len(created_services),
            "knowledge_documents": len(docs_seeded),
            "planned_integrations": len(integration_rows),
            "template_count": template_count,
        },
        created_at=now,
    )
    final_wizard = refresh_guided_onboarding_validation_snapshot(conn, wizard_id=wizard_id, source="apply")
    return {
        "wizard": final_wizard,
        "validation_snapshot": _as_record(final_wizard.get("validation_snapshot")),
        "behavior": behavior_row,
        "pack_result": pack_result,
        "created_services": created_services,
        "knowledge_documents": [item.get("id") for item in docs_seeded],
        "planned_integrations": [{"id": row.get("id"), "provider": row.get("provider"), "status": row.get("status")} for row in integration_rows],
        "summary": applied_summary,
    }
