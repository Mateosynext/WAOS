from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

import httpx

from .config import settings
from .utils import to_json, utcnow_iso
from .vertical_onboarding_runtime import (
    apply_guided_onboarding_wizard,
    build_guided_onboarding_blueprint,
    dry_run_guided_onboarding_wizard,
    get_guided_onboarding_wizard,
    start_guided_onboarding_wizard,
    update_guided_onboarding_step,
)
from .verticals import get_vertical_profile, list_vertical_profiles, normalize_vertical_key
from .world_class import fetch_one

AI_PREFILL_STEPS = [
    "vertical_fit",
    "business_basics",
    "catalog_offer",
    "knowledge_seed",
    "integrations_rules",
    "launch_review",
]

DEFAULT_CONFIRMATION_FIELDS = [
    "vertical_fit.vertical_id",
    "vertical_fit.subvertical",
    "vertical_fit.primary_objective",
    "business_basics.business_name",
    "business_basics.whatsapp_number",
    "business_basics.hours",
    "catalog_offer.services",
    "catalog_offer.pricing_notes",
    "knowledge_seed.policies",
    "integrations_rules.human_destination_channel",
    "integrations_rules.selected_integrations",
]

VERTICAL_KEYWORDS: dict[str, list[str]] = {
    "dental": ["dental", "dentista", "odont", "ortodon", "implante", "limpieza", "endodon", "muela", "caries"],
    "fitness": ["gym", "fitness", "gimnasio", "coach", "membres", "clase", "pilates", "yoga", "cross", "entrenamiento"],
    "aesthetic": ["estet", "facial", "laser", "depil", "botox", "spa", "wellness", "rejuvenec", "aparatologia"],
}

OBJECTIVE_KEYWORDS: dict[str, list[str]] = {
    "agendar": ["agenda", "cita", "reserv", "valoracion", "valoración", "booking", "apart"],
    "vender": ["vender", "venta", "cerrar", "cierre", "cobrar", "pago", "anticipo", "checkout"],
    "calificar": ["filtrar", "calificar", "triage", "elegibilidad", "perfil", "urgencia"],
    "responder": ["faq", "responder", "preguntas", "soporte", "dudas"],
    "reactivar": ["reactivar", "recall", "seguimiento", "regresar", "retomar", "renovar"],
}


def _safe_text(value: Any, fallback: str = "") -> str:
    rendered = str(value or "").strip()
    return rendered or fallback


def _as_record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _unique_strings(values: list[Any], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _safe_text(value)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result


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


def _profile_subverticals(profile: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for item in list(profile.get("subverticals") or []) + list(profile.get("recommended_subverticals") or []):
        if isinstance(item, dict):
            values.append(_safe_text(item.get("name") or item.get("label")))
        else:
            values.append(_safe_text(item))
    return _unique_strings(values)


def _detect_vertical_id(description: str, requested_vertical_id: str | None) -> str:
    requested = normalize_vertical_key(requested_vertical_id)
    if requested:
        return requested
    normalized = description.lower()
    for vertical_id, tokens in VERTICAL_KEYWORDS.items():
        if any(token in normalized for token in tokens):
            return vertical_id
    profiles = list_vertical_profiles()
    best_id = ""
    best_score = 0
    for profile in profiles:
        blob = " ".join([
            _safe_text(profile.get("id")),
            _safe_text(profile.get("name")),
            _safe_text(profile.get("short_name")),
            _safe_text(profile.get("description")),
            " ".join(_profile_subverticals(profile)),
        ]).lower()
        score = sum(1 for token in re.findall(r"[a-záéíóúñ0-9]{4,}", normalized) if token in blob)
        if score > best_score:
            best_score = score
            best_id = _safe_text(profile.get("id"))
    return normalize_vertical_key(best_id or "dental")


def _detect_objective(description: str, requested_objective: str | None) -> str:
    requested = _safe_text(requested_objective).lower()
    if requested in OBJECTIVE_KEYWORDS:
        return requested
    normalized = description.lower()
    scores = {key: sum(1 for token in tokens if token in normalized) for key, tokens in OBJECTIVE_KEYWORDS.items()}
    best = max(scores.items(), key=lambda item: item[1])
    return best[0] if best[1] else "agendar"


def _detect_subvertical(profile: dict[str, Any], description: str, requested_subvertical: str | None) -> str:
    requested = _safe_text(requested_subvertical)
    if requested:
        return requested
    normalized = description.lower()
    for subvertical in _profile_subverticals(profile):
        if subvertical.lower() in normalized:
            return subvertical
    tokens = set(re.findall(r"[a-záéíóúñ0-9]{4,}", normalized))
    best = ""
    best_score = 0
    for subvertical in _profile_subverticals(profile):
        score = sum(1 for token in tokens if token in subvertical.lower())
        if score > best_score:
            best = subvertical
            best_score = score
    return best or (_profile_subverticals(profile)[0] if _profile_subverticals(profile) else "operación principal")


def _extract_business_name(description: str, fallback: str) -> str:
    patterns = [
        r"(?:se llama|somos|negocio llamado|clinica llamada|clínica llamada|empresa llamada)\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÜÑáéíóúüñ&'.\- ]{2,55})",
        r"(?:de|para)\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÜÑáéíóúüñ&'.\- ]{2,55})(?:,|\.|\s+en\s+|\s+vendemos\s+|\s+queremos\s+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, description, flags=re.IGNORECASE)
        if match:
            candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
            if 2 <= len(candidate) <= 60:
                return candidate
    return fallback


def _extract_hours(description: str) -> str:
    match = re.search(r"(?:horario|abrimos|atienden|atendemos)[:\s]+([^\.\n]{8,90})", description, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" .")
    return "Lunes a viernes 9:00-18:00; sábado con disponibilidad limitada"


def _extract_whatsapp(description: str) -> str:
    match = re.search(r"(?:\+?\d[\d\s().-]{8,}\d)", description)
    return match.group(0).strip() if match else ""


def _sentence_items(description: str) -> list[str]:
    chunks = re.split(r"[\n.;]", description)
    return [_safe_text(chunk) for chunk in chunks if _safe_text(chunk)]


def _extract_services(description: str, defaults: list[Any], vertical_id: str) -> list[str]:
    normalized = description.lower()
    services = [_safe_text(item) for item in defaults]
    if "vendemos" in normalized or "servicios" in normalized or "ofrecemos" in normalized:
        match = re.search(r"(?:vendemos|servicios|ofrecemos|manejamos|damos)\s+([^\.\n]{4,160})", description, flags=re.IGNORECASE)
        if match:
            raw = re.split(r",|\sy\s|/|\+", match.group(1))
            services = [item.strip(" .") for item in raw if item.strip(" .")]
    hints = {
        "dental": ["valoración", "limpieza", "ortodoncia", "implantes", "urgencias", "radiografía", "endodoncia"],
        "fitness": ["clase muestra", "membresía", "personal training", "evaluación inicial", "renovación"],
        "aesthetic": ["valoración estética", "facial avanzado", "depilación láser", "paquetes", "aftercare"],
    }
    for hint in hints.get(vertical_id, []):
        if hint.lower() in normalized or len(services) < 5:
            services.append(hint)
    return _unique_strings(services, limit=8)


def _objective_ctas(objective: str, vertical_id: str) -> list[dict[str, Any]]:
    ctas = {
        "agendar": [
            {"key": "book_now", "label": "Agendar ahora", "goal": "booking"},
            {"key": "see_availability", "label": "Ver horarios disponibles", "goal": "booking"},
        ],
        "vender": [
            {"key": "see_offer", "label": "Ver paquete recomendado", "goal": "pricing"},
            {"key": "pay_or_reserve", "label": "Apartar con anticipo", "goal": "payment"},
        ],
        "calificar": [
            {"key": "qualify_case", "label": "Validar mi caso", "goal": "qualification"},
            {"key": "human_review", "label": "Pasar con especialista", "goal": "handoff"},
        ],
        "responder": [
            {"key": "answer_faq", "label": "Resolver mi duda", "goal": "support"},
            {"key": "talk_to_human", "label": "Hablar con asesor", "goal": "handoff"},
        ],
        "reactivar": [
            {"key": "restart", "label": "Retomar seguimiento", "goal": "reactivation"},
            {"key": "book_return", "label": "Agendar regreso", "goal": "booking"},
        ],
    }.get(objective, [])
    if vertical_id in {"dental", "aesthetic"}:
        ctas.insert(0, {"key": "assessment", "label": "Agendar valoración", "goal": "assessment"})
    ctas.append({"key": "human_help", "label": "Hablar con asesor", "goal": "handoff"})
    return ctas[:5]


def _vertical_specific_enrichment(vertical_id: str, business_name: str) -> dict[str, Any]:
    if vertical_id == "dental":
        return {
            "featured_offers": ["Valoración inicial", "Limpieza preventiva", "Plan por fases para tratamientos grandes"],
            "faqs": [
                {"q": "¿Me pueden dar diagnóstico por WhatsApp?", "a": "Podemos orientar y filtrar urgencia, pero el diagnóstico definitivo lo confirma el especialista en valoración."},
                {"q": "¿Qué pasa si tengo dolor fuerte o sangrado?", "a": "El bot debe escalarlo de inmediato al equipo humano para priorizar atención."},
                {"q": "¿Puedo financiar mi tratamiento?", "a": "Podemos explicar anticipo, fases y opciones disponibles, siempre sujeto a confirmación del negocio."},
            ],
            "policies": ["No dar diagnóstico clínico definitivo por chat", "No recetar medicamentos", "Escalar dolor fuerte, sangrado, trauma o contraindicaciones"],
            "escalate_when": ["dolor fuerte", "sangrado", "trauma", "infección", "contraindicación", "paciente molesto"],
            "handoff_keywords": ["urgencia", "dolor", "sangrado", "infección", "medicamento", "embarazo"],
            "can_say": ["orientación general", "rango orientativo", "agendar valoración", "opciones de financiamiento si están confirmadas"],
            "cannot_say": ["diagnóstico definitivo", "receta médica", "promesa clínica absoluta", "precio final sin valoración"],
            "launch_notes": ["Playbook de triage dental", "Playbook de valoración y cierre", "Seguimiento de tratamiento por fases", "Recall de limpieza/control"],
        }
    if vertical_id == "fitness":
        return {
            "featured_offers": ["Clase muestra", "Plan recomendado por objetivo", "Membresía mensual"],
            "faqs": [
                {"q": "¿Qué plan me conviene?", "a": "El bot pregunta objetivo, nivel y frecuencia para sugerir un plan inicial."},
                {"q": "¿Puedo tomar clase muestra?", "a": "Sí, el bot puede ayudar a elegir horario y apartar la clase muestra."},
            ],
            "policies": ["No prometer resultados físicos garantizados", "Escalar lesiones, temas médicos y cancelaciones sensibles"],
            "escalate_when": ["lesión", "dolor físico", "cancelación", "reclamo", "tema médico"],
            "handoff_keywords": ["lesión", "lastimado", "cancelar", "reembolso", "molestia"],
            "can_say": ["planes", "horarios", "clase muestra", "coaches", "promociones confirmadas"],
            "cannot_say": ["diagnóstico médico", "rutina clínica", "promesa de transformación garantizada"],
            "launch_notes": ["Playbook de clase muestra", "Playbook de inscripción", "Recuperación de ausencias", "Renovación de membresía"],
        }
    return {
        "featured_offers": ["Valoración inicial", "Paquete recomendado", "Seguimiento post-servicio"],
        "faqs": [
            {"q": "¿Qué servicio me conviene?", "a": "El bot puede orientar según objetivo y llevar a una valoración o asesor humano."},
            {"q": "¿Cuánto cuesta?", "a": "Puede compartir rangos o paquetes confirmados, evitando prometer precio final si depende del caso."},
        ],
        "policies": ["No prometer resultados garantizados", "Escalar casos sensibles, quejas o contraindicaciones"],
        "escalate_when": ["queja", "caso sensible", "contraindicación", "reembolso", "urgencia"],
        "handoff_keywords": ["queja", "urgente", "contraindicación", "reembolso", "humano"],
        "can_say": ["orientación general", "servicios", "rangos confirmados", "agendar o pasar con asesor"],
        "cannot_say": ["promesas absolutas", "diagnóstico definitivo", "información no confirmada"],
        "launch_notes": ["Playbook de lead intake", "Playbook de cierre", "Playbook de seguimiento", "Playbook de reactivación"],
    }


def _base_answers_patch(
    *,
    organization: dict[str, Any] | None,
    vertical_id: str | None,
    subvertical: str | None,
    primary_objective: str | None,
    user_description: str,
    existing_answers: dict[str, Any] | None,
    intensity: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    detected_vertical_id = _detect_vertical_id(user_description, vertical_id)
    profile = get_vertical_profile(detected_vertical_id)
    detected_subvertical = _detect_subvertical(profile, user_description, subvertical)
    detected_objective = _detect_objective(user_description, primary_objective)
    organization_name = _safe_text((organization or {}).get("name"), _safe_text(profile.get("short_name") or profile.get("name"), "Negocio WAOS"))
    business_name = _extract_business_name(user_description, organization_name)
    bot_name = f"Asistente {business_name}"[:80]
    tone = _safe_text((profile.get("behavior") or {}).get("tone"), "claro y directo")
    if intensity == "savage":
        tone = f"{tone}, muy proactivo, preciso, vendedor y obsesionado con el siguiente paso"
    elif intensity == "aggressive":
        tone = f"{tone}, vendedor y orientado al cierre"
    elif intensity == "conservative":
        tone = f"{tone}, prudente y seguro"
    hours = _extract_hours(user_description)
    whatsapp_number = _extract_whatsapp(user_description)

    blueprint = build_guided_onboarding_blueprint(
        vertical_id=detected_vertical_id,
        subvertical=detected_subvertical,
        business_name=business_name,
        bot_name=bot_name,
        tone=tone,
        language="es",
        timezone=_safe_text((organization or {}).get("timezone"), "America/Mexico_City"),
        primary_objective=detected_objective,
        hours=hours,
        whatsapp_number=whatsapp_number,
        answers=existing_answers or {},
    )
    defaults = deepcopy(blueprint.get("prefill_answers") or blueprint.get("answers") or {})
    catalog = _as_record(defaults.get("catalog_offer"))
    knowledge = _as_record(defaults.get("knowledge_seed"))
    integrations = _as_record(defaults.get("integrations_rules"))
    rule_overrides = _as_record(integrations.get("rule_overrides"))
    launch = _as_record(defaults.get("launch_review"))
    enrichment = _vertical_specific_enrichment(detected_vertical_id, business_name)
    services = _extract_services(user_description, list(catalog.get("services") or []), detected_vertical_id)
    featured_offers = _unique_strings([*(catalog.get("featured_offers") or []), *enrichment["featured_offers"]], limit=6)
    pricing_notes = [
        "Usar solo precios, promociones y financiamiento confirmados por el negocio.",
        "Si falta precio final, compartir rango orientativo y cerrar a valoración/humano.",
    ]
    if intensity in {"aggressive", "savage"}:
        pricing_notes.append("Empujar anticipo, apartado o siguiente paso cuando el lead muestre intención clara.")
    if intensity == "savage":
        pricing_notes.append("Si el lead no está listo, cerrar micro-compromiso: horario, presupuesto, urgencia o canal humano.")
    if intensity == "conservative":
        pricing_notes.append("Evitar presión comercial cuando haya dudas legales, médicas o políticas no confirmadas.")

    faqs = list(knowledge.get("faqs") or []) + list(enrichment["faqs"])
    launch_notes = _unique_strings([*(launch.get("launch_notes") or []), *enrichment["launch_notes"]], limit=8)
    patch = _deep_merge(defaults, {
        "vertical_fit": {
            "vertical_id": detected_vertical_id,
            "subvertical": detected_subvertical,
            "primary_objective": detected_objective,
        },
        "business_basics": {
            "business_name": business_name,
            "bot_name": bot_name,
            "tone": tone,
            "language": "es",
            "timezone": _safe_text((organization or {}).get("timezone"), "America/Mexico_City"),
            "hours": hours,
            "whatsapp_number": whatsapp_number,
        },
        "catalog_offer": {
            "services": services,
            "featured_offers": featured_offers,
            "primary_ctas": _objective_ctas(detected_objective, detected_vertical_id),
            "pricing_notes": pricing_notes,
            "qualification_questions": [
                "¿Qué resultado quieres lograr y para cuándo?",
                "¿Ya comparaste opciones o es primera vez que preguntas?",
                "¿Prefieres agendar, recibir rango orientativo o hablar con asesor?",
                "¿Qué tan urgente es resolverlo: hoy, esta semana o este mes?",
            ],
            "objection_handlers": [
                {"objection": "precio", "response_goal": "dar rango confirmado o explicar que depende de valoración", "next_step": "agendar o pasar con asesor"},
                {"objection": "tiempo", "response_goal": "ofrecer horarios concretos", "next_step": "reservar espacio"},
                {"objection": "desconfianza", "response_goal": "explicar proceso, límites y handoff", "next_step": "resolver duda específica"},
            ],
        },
        "knowledge_seed": {
            "faqs": faqs[:8],
            "policies": _unique_strings([*(knowledge.get("policies") or []), *enrichment["policies"]], limit=8),
            "knowledge_sources": knowledge.get("knowledge_sources") or [
                {"connector_key": "url", "required": True, "label": "Sitio / landing principal", "publish_policy": "auto_publish"},
                {"connector_key": "drive", "required": True, "label": "Drive con servicios, precios y políticas", "publish_policy": "manual_review"},
            ],
            "owner_user_id": knowledge.get("owner_user_id"),
        },
        "integrations_rules": {
            "selected_integrations": integrations.get("selected_integrations") or ["whatsapp", "calendar", "crm"],
            "escalate_when": _unique_strings([*(integrations.get("escalate_when") or []), *enrichment["escalate_when"]], limit=10),
            "handoff_keywords": _unique_strings([*(integrations.get("handoff_keywords") or []), *enrichment["handoff_keywords"]], limit=10),
            "expected_handoff_sla": integrations.get("expected_handoff_sla") or "15 minutos",
            "human_destination_channel": integrations.get("human_destination_channel") or "Equipo humano por WhatsApp / CRM",
            "rule_overrides": {
                **rule_overrides,
                "can_say": _unique_strings([*_as_list(rule_overrides.get("can_say")), *enrichment["can_say"]], limit=10),
                "cannot_say": _unique_strings([*_as_list(rule_overrides.get("cannot_say")), *enrichment["cannot_say"]], limit=10),
                "must_collect_before_handoff": ["nombre", "servicio de interés", "urgencia", "canal/teléfono", "horario preferido"],
                "never_autopromise": ["precio final", "resultado garantizado", "diagnóstico definitivo", "integración conectada", "descuento no confirmado"],
            },
            "lead_score_rules": [
                {"score": "+30", "when": "pide cita, horario o disponibilidad"},
                {"score": "+20", "when": "menciona urgencia o intención clara"},
                {"score": "+15", "when": "acepta rango/precio orientativo"},
                {"score": "handoff", "when": "caso sensible, queja, riesgo médico/legal o datos no confirmados"},
            ],
            "handoff_matrix": [
                {"trigger": "urgencia o riesgo", "priority": "alta", "owner": "equipo humano", "sla": "inmediato / 15 minutos"},
                {"trigger": "precio final o promoción no confirmada", "priority": "media", "owner": "ventas", "sla": "15 minutos"},
                {"trigger": "lead listo para cita", "priority": "alta", "owner": "agenda", "sla": "15 minutos"},
            ],
        },
        "launch_review": {
            "recommended_playbooks": launch.get("recommended_playbooks") or [],
            "launch_notes": launch_notes,
            "autopublish_knowledge": bool(launch.get("autopublish_knowledge") if launch.get("autopublish_knowledge") is not None else True),
            "ai_autopilot_plan": [
                "Detectar industria, subvertical y objetivo con evidencia del usuario",
                "Generar draft completo de identidad, oferta, knowledge, integraciones, handoff y launch",
                "Guardar los 6 pasos en batch desde backend",
                "Correr dry run inmediatamente",
                "Autofix iterativo hasta eliminar bloqueos rellenables",
                "Dejar precios, horarios, políticas delicadas e integraciones reales para confirmación humana",
            ],
            "critical_confirmation_cards": [
                {"key": "industry", "label": "Industria / subvertical", "reason": "Si está mal, todo el pack queda mal calibrado."},
                {"key": "objective", "label": "Objetivo principal", "reason": "Cambia CTAs, followups, cierre y simulación."},
                {"key": "pricing", "label": "Precios / promociones", "reason": "No deben inventarse ni publicarse sin confirmación."},
                {"key": "handoff", "label": "Handoff humano", "reason": "Define quién toma casos urgentes o sensibles."},
                {"key": "integrations", "label": "Integraciones reales", "reason": "La IA puede sugerir, pero no debe asumir conexión real."},
            ],
            "simulation_scenarios": [
                "Lead frío pide precio sin querer agendar",
                "Lead caliente quiere cita hoy",
                "Caso sensible que requiere humano",
                "Objeción por precio o financiamiento",
                "Pregunta que el bot no debe contestar con certeza",
            ],
            "dry_run_acceptance_criteria": [
                "Todos los pasos requeridos tienen payload no vacío",
                "Handoff tiene keywords, SLA y destino humano",
                "Knowledge tiene FAQs, políticas y fuentes sugeridas",
                "Integraciones críticas están planeadas sin fingir conexión real",
                "Los campos delicados quedan marcados para confirmación humana",
            ],
        },
    })
    context = {
        "profile": profile,
        "vertical_id": detected_vertical_id,
        "subvertical": detected_subvertical,
        "primary_objective": detected_objective,
        "business_name": business_name,
        "sentences": _sentence_items(user_description),
    }
    return {step: _as_record(patch.get(step)) for step in AI_PREFILL_STEPS}, context


def _schema() -> dict[str, Any]:
    return {
        "name": "waos_ai_wizard_prefill",
        "schema": {
            "type": "object",
            "properties": {
                "confidence": {"type": "number"},
                "summary": {"type": "string"},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "requires_user_confirmation": {"type": "array", "items": {"type": "string"}},
                "answers_patch": {"type": "object"},
            },
            "required": ["confidence", "summary", "assumptions", "requires_user_confirmation", "answers_patch"],
            "additionalProperties": False,
        },
        "strict": True,
    }



def _openai_output_text(data: dict[str, Any]) -> str:
    direct = _safe_text(data.get("output_text"))
    if direct:
        return direct
    for item in _as_list(data.get("output")):
        record = _as_record(item)
        for content in _as_list(record.get("content")):
            content_record = _as_record(content)
            text = _safe_text(content_record.get("text"))
            if text:
                return text
    return ""

def _call_openai_prefill(*, base_patch: dict[str, Any], context: dict[str, Any], user_description: str, intensity: str) -> dict[str, Any] | None:
    if not settings.openai_api_key:
        return None
    profile = _as_record(context.get("profile"))
    payload = {
        "user_description": user_description,
        "intensity": intensity,
        "detected_context": {
            "vertical_id": context.get("vertical_id"),
            "subvertical": context.get("subvertical"),
            "primary_objective": context.get("primary_objective"),
            "business_name": context.get("business_name"),
        },
        "vertical_profile": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "short_name": profile.get("short_name"),
            "default_services": profile.get("default_services"),
            "default_faqs": profile.get("default_faqs"),
            "recommended_integrations": profile.get("recommended_integrations"),
            "behavior": profile.get("behavior"),
            "config_overrides": profile.get("config_overrides"),
            "flows": profile.get("flows"),
        },
        "safe_base_patch": base_patch,
    }
    request = {
        "model": settings.openai_model,
        "instructions": (
            "Eres el AI Autopilot de WAOS para crear bots de WhatsApp. "
            "Devuelve un JSON estructurado para completar un wizard, no texto libre. "
            "Sé opinionated: servicios, CTAs, FAQs, policies, handoff, can_say/cannot_say, playbooks y launch notes. "
            "Blindaje: no inventes precios finales, horarios reales, WhatsApp real ni integraciones conectadas. Márcalos para confirmación. "
            "Mantén los keys del wizard: vertical_fit, business_basics, catalog_offer, knowledge_seed, integrations_rules, launch_review."
        ),
        "input": [{"role": "user", "content": [{"type": "input_text", "text": to_json(payload)}]}],
        "text": {"format": {"type": "json_schema", **_schema()}},
    }
    started = time.perf_counter()
    try:
        response = httpx.post(
            f"{settings.openai_base_url}/responses",
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            json=request,
            timeout=float(settings.openai_timeout_seconds),
        )
        response.raise_for_status()
        data = response.json()
        output_text = _openai_output_text(data)
        parsed = json.loads(output_text) if output_text else None
        if isinstance(parsed, dict):
            parsed["latency_ms"] = int((time.perf_counter() - started) * 1000)
            return parsed
    except Exception:
        return None
    return None


def _normalized_prefill_response(*, generated: dict[str, Any] | None, base_patch: dict[str, Any], context: dict[str, Any], source: str, intensity: str) -> dict[str, Any]:
    generated = generated if isinstance(generated, dict) else {}
    answers_patch = _deep_merge(base_patch, _as_record(generated.get("answers_patch")))
    answers_patch = {step: _as_record(answers_patch.get(step)) for step in AI_PREFILL_STEPS}
    profile = _as_record(context.get("profile"))
    assumptions = _unique_strings([
        *list(generated.get("assumptions") or []),
        f"Asumí que el canal principal será WhatsApp para {context.get('business_name') or 'el negocio'}.",
        "Los precios, promociones, horarios reales e integraciones conectadas quedan como campos de confirmación humana.",
    ], limit=8)
    requires = _unique_strings([*list(generated.get("requires_user_confirmation") or []), *DEFAULT_CONFIRMATION_FIELDS], limit=14)
    summary = _safe_text(
        generated.get("summary"),
        f"Setup generado para {profile.get('short_name') or profile.get('name') or context.get('vertical_id')} enfocado en {context.get('primary_objective')} y {context.get('subvertical')}.",
    )
    confidence = generated.get("confidence")
    try:
        confidence_value = float(confidence)
    except Exception:
        confidence_value = 0.78 if source == "heuristic" else 0.86
    return {
        "source": source,
        "intensity": intensity,
        "confidence": max(0.0, min(1.0, confidence_value)),
        "summary": summary,
        "assumptions": assumptions,
        "requires_user_confirmation": requires,
        "critical_fields": DEFAULT_CONFIRMATION_FIELDS,
        "answers_patch": answers_patch,
        "generated_cards": _cards_from_patch(answers_patch),
        "generated_at": utcnow_iso(),
    }


def _cards_from_patch(patch: dict[str, Any]) -> list[dict[str, Any]]:
    fit = _as_record(patch.get("vertical_fit"))
    basics = _as_record(patch.get("business_basics"))
    catalog = _as_record(patch.get("catalog_offer"))
    knowledge = _as_record(patch.get("knowledge_seed"))
    integrations = _as_record(patch.get("integrations_rules"))
    launch = _as_record(patch.get("launch_review"))
    return [
        {"key": "context", "title": "Contexto detectado", "items": [fit.get("vertical_id"), fit.get("subvertical"), fit.get("primary_objective")]},
        {"key": "identity", "title": "Identidad", "items": [basics.get("business_name"), basics.get("bot_name"), basics.get("tone")]},
        {"key": "offer", "title": "Oferta", "items": [*list(catalog.get("services") or [])[:4], f"{len(list(catalog.get('qualification_questions') or []))} preguntas de calificación"]},
        {"key": "knowledge", "title": "Knowledge y políticas", "items": [f"{len(list(knowledge.get('faqs') or []))} FAQs", *list(knowledge.get("policies") or [])[:3]]},
        {"key": "handoff", "title": "Handoff blindado", "items": [integrations.get("expected_handoff_sla"), integrations.get("human_destination_channel"), *list(integrations.get("handoff_keywords") or [])[:3], f"{len(list(integrations.get('lead_score_rules') or []))} reglas de score"]},
        {"key": "launch", "title": "Playbooks", "items": list(launch.get("launch_notes") or [])[:5]},
    ]


def generate_ai_wizard_prefill(
    conn: Any,
    *,
    organization_id: str,
    bot_id: str | None = None,
    vertical_id: str | None = None,
    subvertical: str | None = None,
    primary_objective: str | None = None,
    user_description: str = "",
    existing_answers: dict[str, Any] | None = None,
    intensity: str = "balanced",
) -> dict[str, Any]:
    organization = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (organization_id,)) if conn and organization_id else {}
    normalized_intensity = _safe_text(intensity, "balanced").lower()
    if normalized_intensity not in {"balanced", "aggressive", "conservative", "savage"}:
        normalized_intensity = "balanced"
    base_patch, context = _base_answers_patch(
        organization=organization,
        vertical_id=vertical_id,
        subvertical=subvertical,
        primary_objective=primary_objective,
        user_description=user_description,
        existing_answers=existing_answers,
        intensity=normalized_intensity,
    )
    generated = _call_openai_prefill(base_patch=base_patch, context=context, user_description=user_description, intensity=normalized_intensity)
    return _normalized_prefill_response(
        generated=generated,
        base_patch=base_patch,
        context=context,
        source="openai" if generated else "heuristic",
        intensity=normalized_intensity,
    )


def _answers_for_autofix(wizard: dict[str, Any]) -> dict[str, Any]:
    answers = deepcopy(_as_record(wizard.get("answers")))
    setup_blueprint = build_guided_onboarding_blueprint(
        vertical_id=wizard.get("vertical_id"),
        subvertical=wizard.get("subvertical"),
        business_name=wizard.get("business_name") or "",
        bot_name=wizard.get("bot_name") or "",
        tone=wizard.get("tone") or "",
        language=wizard.get("language") or "es",
        timezone=wizard.get("timezone") or "America/Mexico_City",
        primary_objective=wizard.get("primary_objective") or "agendar",
        answers=answers,
        bot_id=wizard.get("bot_id"),
    )
    defaults = _as_record(setup_blueprint.get("prefill_answers"))
    patch: dict[str, Any] = {}
    for step in AI_PREFILL_STEPS:
        current = _as_record(answers.get(step))
        fallback = _as_record(defaults.get(step))
        patch[step] = _deep_merge(fallback, current)

    fit = _as_record(patch.get("vertical_fit"))
    if not fit.get("vertical_id"):
        fit["vertical_id"] = wizard.get("vertical_id") or "dental"
    if not fit.get("subvertical"):
        profile = get_vertical_profile(fit.get("vertical_id"))
        fit["subvertical"] = (_profile_subverticals(profile) or ["operación principal"])[0]
    if not fit.get("primary_objective"):
        fit["primary_objective"] = wizard.get("primary_objective") or "agendar"
    patch["vertical_fit"] = fit

    catalog = _as_record(patch.get("catalog_offer"))
    if not catalog.get("services"):
        catalog["services"] = list(_as_record(defaults.get("catalog_offer")).get("services") or ["servicio principal", "atención inicial"])
    if not catalog.get("primary_ctas"):
        catalog["primary_ctas"] = _objective_ctas(_safe_text(fit.get("primary_objective"), "agendar"), _safe_text(fit.get("vertical_id"), "dental"))
    patch["catalog_offer"] = catalog

    knowledge = _as_record(patch.get("knowledge_seed"))
    if not knowledge.get("faqs"):
        knowledge["faqs"] = list(_as_record(defaults.get("knowledge_seed")).get("faqs") or [])
    if not knowledge.get("policies"):
        knowledge["policies"] = list(_as_record(defaults.get("knowledge_seed")).get("policies") or ["Confirmar información sensible antes de prometerla", "Escalar casos delicados a humano"])
    if not knowledge.get("knowledge_sources"):
        knowledge["knowledge_sources"] = [
            {"connector_key": "url", "required": True, "label": "Sitio / landing principal", "publish_policy": "auto_publish"},
            {"connector_key": "drive", "required": True, "label": "Drive con servicios, precios y políticas", "publish_policy": "manual_review"},
        ]
    patch["knowledge_seed"] = knowledge

    integrations = _as_record(patch.get("integrations_rules"))
    if not integrations.get("selected_integrations"):
        integrations["selected_integrations"] = ["whatsapp", "calendar", "crm"]
    if not integrations.get("escalate_when"):
        integrations["escalate_when"] = ["lead pide humano", "caso sensible", "queja", "precio o política no confirmada"]
    if not integrations.get("handoff_keywords"):
        integrations["handoff_keywords"] = ["humano", "asesor", "urgente", "queja", "cancelar"]
    integrations["expected_handoff_sla"] = integrations.get("expected_handoff_sla") or "15 minutos"
    integrations["human_destination_channel"] = integrations.get("human_destination_channel") or "Equipo humano por WhatsApp / CRM"
    patch["integrations_rules"] = integrations

    launch = _as_record(patch.get("launch_review"))
    if not launch.get("launch_notes"):
        launch["launch_notes"] = ["Validar campos críticos", "Correr dry run", "Publicar knowledge confirmado", "Probar handoff humano"]
    patch["launch_review"] = launch
    return patch



def _apply_answers_patch_to_wizard(conn: Any, *, wizard: dict[str, Any], answers_patch: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    current = wizard
    applied_steps: list[str] = []
    for step in AI_PREFILL_STEPS:
        next_payload = _as_record(answers_patch.get(step))
        if not next_payload:
            continue
        existing_payload = _as_record(_as_record(current.get("answers")).get(step))
        if json.dumps(existing_payload, sort_keys=True, ensure_ascii=False) == json.dumps(next_payload, sort_keys=True, ensure_ascii=False):
            continue
        current = update_guided_onboarding_step(
            conn,
            wizard_id=str(current.get("id") or ""),
            step_key=step,
            payload=next_payload,
            expected_revision=int(current.get("wizard_revision") or 1),
        )
        applied_steps.append(step)
    return current, applied_steps


def _dry_run_apply_ready(dry_run: dict[str, Any] | None) -> bool:
    record = _as_record(dry_run)
    summary = _as_record(record.get("summary"))
    snapshot = _as_record(record.get("validation_snapshot"))
    return bool(summary.get("apply_ready") or snapshot.get("apply_ready"))


def _dry_run_blocking_items(dry_run: dict[str, Any] | None) -> list[dict[str, Any]]:
    record = _as_record(dry_run)
    items: list[dict[str, Any]] = []
    for conflict in _as_list(record.get("conflicts")):
        conflict_record = _as_record(conflict)
        if conflict_record:
            items.append({
                "source": "conflict",
                "key": conflict_record.get("key"),
                "label": conflict_record.get("label") or conflict_record.get("key"),
                "detail": conflict_record.get("detail"),
                "severity": conflict_record.get("severity") or "blocking",
            })
    snapshot = _as_record(record.get("validation_snapshot"))
    for item in _as_list(snapshot.get("checklist")):
        item_record = _as_record(item)
        if item_record.get("blocking") and item_record.get("status") == "red":
            items.append({
                "source": "checklist",
                "key": item_record.get("key"),
                "label": item_record.get("label") or item_record.get("key"),
                "detail": item_record.get("detail"),
                "severity": "blocking",
            })
    return items[:10]


def _autopilot_next_action(*, dry_run: dict[str, Any] | None, applied: dict[str, Any] | None, auto_apply: bool) -> dict[str, Any]:
    if applied:
        return {
            "key": "applied",
            "label": "Aplicado en draft",
            "detail": "El setup fue generado, validado y aplicado porque auto_apply estaba habilitado.",
        }
    if _dry_run_apply_ready(dry_run):
        return {
            "key": "human_confirm_then_apply",
            "label": "Confirmar críticos y aplicar",
            "detail": "El backend ya generó, guardó, validó y reparó lo reparable. Falta confirmación humana antes del apply final.",
        }
    blocking = _dry_run_blocking_items(dry_run)
    if blocking:
        return {
            "key": "human_review_blockers",
            "label": "Revisar bloqueos no rellenables por IA",
            "detail": "Quedan bloqueos que requieren datos reales, conexión o decisión humana.",
            "blocking_items": blocking,
        }
    return {
        "key": "review_generated_setup",
        "label": "Revisar setup generado",
        "detail": "El setup quedó guardado; revisa los campos críticos y vuelve a validar.",
    }


def apply_ai_autofix_to_wizard(conn: Any, *, wizard_id: str, user_description: str = "", max_rounds: int = 3) -> dict[str, Any]:
    wizard = get_guided_onboarding_wizard(conn, wizard_id)
    if not wizard:
        raise ValueError("wizard_not_found")
    before_snapshot = _as_record(wizard.get("validation_snapshot"))
    current = wizard
    all_applied_steps: list[str] = []
    rounds: list[dict[str, Any]] = []
    dry_run: dict[str, Any] | None = None
    safe_rounds = max(1, min(5, int(max_rounds or 3)))
    for round_index in range(safe_rounds):
        patch = _answers_for_autofix(current)
        current, applied_steps = _apply_answers_patch_to_wizard(conn, wizard=current, answers_patch=patch)
        all_applied_steps.extend([step for step in applied_steps if step not in all_applied_steps])
        dry_run = dry_run_guided_onboarding_wizard(conn, wizard_id=wizard_id)
        ready = _dry_run_apply_ready(dry_run)
        blockers = _dry_run_blocking_items(dry_run)
        rounds.append({
            "round": round_index + 1,
            "applied_steps": applied_steps,
            "apply_ready": ready,
            "blocking_items": blockers,
        })
        current = _as_record(dry_run.get("wizard")) or current
        if ready or not applied_steps:
            break
    return {
        "source": "heuristic_autofix",
        "summary": "La IA rellenó pendientes bloqueantes, corrió autofix iterativo y volvió a ejecutar dry run.",
        "applied_steps": all_applied_steps,
        "autofix_rounds": rounds,
        "answers_patch": _answers_for_autofix(current),
        "before_snapshot": before_snapshot,
        "dry_run_result": dry_run or {},
        "wizard": _as_record(dry_run).get("wizard") if dry_run else current,
        "validation_snapshot": _as_record(dry_run).get("validation_snapshot") if dry_run else {},
        "blocking_items": _dry_run_blocking_items(dry_run),
        "apply_ready": _dry_run_apply_ready(dry_run),
        "generated_at": utcnow_iso(),
    }


def _build_ai_wizard_start_payload(*, organization_id: str, bot_id: str | None, prefill: dict[str, Any], fallback_vertical_id: str | None, fallback_subvertical: str | None, fallback_primary_objective: str | None) -> dict[str, Any]:
    answers = _as_record(prefill.get("answers_patch"))
    fit = _as_record(answers.get("vertical_fit"))
    basics = _as_record(answers.get("business_basics"))
    vertical_id = _safe_text(fit.get("vertical_id"), _safe_text(fallback_vertical_id, "dental"))
    subvertical = _safe_text(fit.get("subvertical"), _safe_text(fallback_subvertical, "operación principal"))
    primary_objective = _safe_text(fit.get("primary_objective"), _safe_text(fallback_primary_objective, "agendar"))
    business_name = _safe_text(basics.get("business_name"), "Negocio WAOS")
    return {
        "organization_id": organization_id,
        "bot_id": bot_id,
        "vertical_id": vertical_id,
        "subvertical": subvertical,
        "business_name": business_name,
        "bot_name": _safe_text(basics.get("bot_name"), f"Asistente {business_name}"),
        "tone": _safe_text(basics.get("tone"), "claro, proactivo y seguro"),
        "language": _safe_text(basics.get("language"), "es"),
        "timezone": _safe_text(basics.get("timezone"), "America/Mexico_City"),
        "primary_objective": primary_objective,
        "hours": _safe_text(basics.get("hours")),
        "whatsapp_number": _safe_text(basics.get("whatsapp_number")),
        "answers": answers,
    }


def generate_ai_wizard_autopilot(
    conn: Any,
    *,
    organization_id: str,
    bot_id: str | None = None,
    vertical_id: str | None = None,
    subvertical: str | None = None,
    primary_objective: str | None = None,
    user_description: str = "",
    existing_answers: dict[str, Any] | None = None,
    intensity: str = "aggressive",
    max_autofix_rounds: int | None = None,
    auto_apply: bool = False,
    actor_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    max_autofix_rounds = min(int(max_autofix_rounds or settings.autopilot_max_autofix_rounds), settings.autopilot_max_autofix_rounds)
    normalized_intensity = _safe_text(intensity, "aggressive").lower()
    if normalized_intensity == "balanced":
        # El endpoint end-to-end debe sentirse más decidido que el prefill suelto.
        normalized_intensity = "aggressive"
    if normalized_intensity not in {"aggressive", "savage", "conservative"}:
        normalized_intensity = "aggressive"

    prefill = generate_ai_wizard_prefill(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        vertical_id=vertical_id,
        subvertical=subvertical,
        primary_objective=primary_objective,
        user_description=user_description,
        existing_answers=existing_answers,
        intensity=normalized_intensity,
    )
    answers_patch = _as_record(prefill.get("answers_patch"))
    start_payload = _build_ai_wizard_start_payload(
        organization_id=organization_id,
        bot_id=bot_id,
        prefill=prefill,
        fallback_vertical_id=vertical_id,
        fallback_subvertical=subvertical,
        fallback_primary_objective=primary_objective,
    )
    wizard = start_guided_onboarding_wizard(
        conn,
        organization_id=str(start_payload["organization_id"]),
        bot_id=start_payload.get("bot_id"),
        actor_user_id=(actor_user or {}).get("id"),
        vertical_id=str(start_payload["vertical_id"]),
        subvertical=str(start_payload["subvertical"]),
        business_name=str(start_payload["business_name"]),
        bot_name=str(start_payload["bot_name"]),
        tone=str(start_payload["tone"]),
        language=str(start_payload["language"]),
        timezone=str(start_payload["timezone"]),
        primary_objective=str(start_payload["primary_objective"]),
        hours=str(start_payload.get("hours") or ""),
        whatsapp_number=str(start_payload.get("whatsapp_number") or ""),
        answers=answers_patch,
    )
    wizard, saved_steps = _apply_answers_patch_to_wizard(conn, wizard=wizard, answers_patch=answers_patch)
    dry_run = dry_run_guided_onboarding_wizard(conn, wizard_id=str(wizard.get("id") or ""))
    autofix_result: dict[str, Any] | None = None
    if not _dry_run_apply_ready(dry_run):
        autofix_result = apply_ai_autofix_to_wizard(
            conn,
            wizard_id=str(wizard.get("id") or ""),
            user_description=user_description,
            max_rounds=max_autofix_rounds,
        )
        dry_run = _as_record(autofix_result.get("dry_run_result")) or dry_run
        wizard = _as_record(autofix_result.get("wizard")) or _as_record(dry_run.get("wizard")) or wizard

    applied_result: dict[str, Any] | None = None
    if auto_apply and _dry_run_apply_ready(dry_run):
        applied_result = apply_guided_onboarding_wizard(conn, wizard_id=str(wizard.get("id") or ""), actor_user=actor_user)
        wizard = _as_record(applied_result.get("wizard")) or wizard

    apply_ready = _dry_run_apply_ready(dry_run)
    next_action = _autopilot_next_action(dry_run=dry_run, applied=applied_result, auto_apply=auto_apply)
    return {
        "source": prefill.get("source") or "heuristic",
        "intensity": normalized_intensity,
        "confidence": prefill.get("confidence"),
        "summary": "AI Autopilot generó, guardó, validó y reparó el wizard de punta a punta.",
        "prefill": prefill,
        "answers_patch": answers_patch,
        "generated_cards": prefill.get("generated_cards") or _cards_from_patch(answers_patch),
        "assumptions": prefill.get("assumptions") or [],
        "requires_user_confirmation": prefill.get("requires_user_confirmation") or DEFAULT_CONFIRMATION_FIELDS,
        "critical_fields": prefill.get("critical_fields") or DEFAULT_CONFIRMATION_FIELDS,
        "wizard": wizard,
        "wizard_id": wizard.get("id"),
        "steps_saved": saved_steps or AI_PREFILL_STEPS,
        "dry_run_result": dry_run,
        "validation_snapshot": _as_record(dry_run.get("validation_snapshot")),
        "autofix_result": autofix_result,
        "apply_ready": apply_ready,
        "auto_apply_requested": bool(auto_apply),
        "applied_result": applied_result,
        "next_action": next_action,
        "blocking_items": _dry_run_blocking_items(dry_run),
        "pipeline": [
            {"key": "detect", "label": "Detectar negocio", "status": "done"},
            {"key": "generate", "label": "Generar setup completo", "status": "done"},
            {"key": "batch_save", "label": "Guardar 6 pasos en backend", "status": "done"},
            {"key": "dry_run", "label": "Validar con dry run", "status": "done"},
            {"key": "autofix", "label": "Autofix iterativo", "status": "done" if autofix_result else "skipped"},
            {"key": "apply", "label": "Apply final", "status": "done" if applied_result else "waiting_human"},
        ],
        "generated_at": utcnow_iso(),
    }
