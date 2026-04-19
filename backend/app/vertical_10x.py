from __future__ import annotations

from copy import deepcopy
from typing import Any

from .domains.bot_behavior import create_audit_log, upsert_bot_behavior_settings, upsert_bot_response_template
from .domains.catalog import create_catalog_service, list_catalog_services
from .utils import from_json, slugify, to_json, utcnow_iso

_STRONGEST_VERTICAL_IDS = ["fitness", "dental", "aesthetic", "vet", "auto-service"]
_VERTICAL_SCORES = {
    "fitness": 100,
    "dental": 99,
    "aesthetic": 97,
    "vet": 94,
    "auto-service": 92,
}
_VERTICAL_NARRATIVES = {
    "fitness": "WAOS Fitness gana cuando controla captacion, trial, asistencia, freeze, renovacion y reactivacion desde WhatsApp.",
    "dental": "WAOS Dental gana cuando convierte valoracion en tratamiento por fases, anticipo, documentos y recall.",
    "aesthetic": "WAOS Aesthetic gana cuando sube valor percibido, vende paquete, sostiene aftercare y crea mantenimiento.",
    "vet": "WAOS Vet gana cuando trata a la mascota como cuenta recurrente con consulta, prevencion, grooming y plan.",
    "auto-service": "WAOS Auto Service gana cuando ordena intake, cotizacion, aprobacion, estatus y mantenimiento futuro sin caos operativo.",
}
_VERTICAL_GROWTH_LOOPS = {
    "fitness": ["trial a membresia", "ausencia a reactivacion", "renovacion a upgrade", "coach match a permanencia"],
    "dental": ["urgencia a valoracion", "valoracion a plan", "plan a anticipo", "fase cerrada a recall"],
    "aesthetic": ["lead aspiracional a valoracion", "valoracion a paquete", "sesion a recompras", "aftercare a mantenimiento"],
    "vet": ["consulta a plan preventivo", "vacuna a proxima vacuna", "grooming a frecuencia", "mascota activa a recordatorio"],
    "auto-service": ["intake a orden", "cotizacion a aprobacion", "servicio a mantenimiento", "entrega a siguiente visita"],
}
_VERTICAL_COMMANDS = {
    "fitness": ["pausar reactivaciones", "abrir cupo extraordinario", "avisar clase de hoy", "solo humano en lesiones"],
    "dental": ["avisar recalls vencidos", "bloquear agenda de cirugia", "modo solo humano por urgencia", "reactivar seguimiento de presupuestos"],
    "aesthetic": ["abrir bloque premium", "avisar sesiones de mantenimiento", "pausar promo especifica", "solo humano por contraindicacion"],
    "vet": ["avisar siguiente vacuna", "bloquear guardia", "modo humano para urgencias", "reactivar plan preventivo"],
    "auto-service": ["avisar entregas del dia", "bloquear taller", "pausar bot por contingencia", "reactivar mantenimiento de 6 meses"],
}

_SUBVERTICAL_OVERRIDES: dict[str, dict[str, dict[str, Any]]] = {
    "fitness": {
        "gym tradicional": {
            "promise": "Llenar pruebas, convertirlas en membresias y sostener asistencia semanal.",
            "service_bundle": ["clase muestra", "evaluacion inicial", "membresia mensual", "freeze controlado"],
            "objections": ["precio", "me da pena empezar", "no tengo horario", "ya he fallado antes"],
            "growth_motion": "trial_conversion",
        },
        "pilates": {
            "promise": "Vender cupos premium y continuidad por bloques de sesiones.",
            "service_bundle": ["clase muestra pilates", "paquete 4 sesiones", "paquete 8 sesiones", "seguimiento post clase"],
            "objections": ["es caro", "soy principiante", "no se si me sirva", "solo puedo ciertos horarios"],
            "growth_motion": "package_retention",
        },
        "boxeo": {
            "promise": "Convertir energia de primer contacto en prueba inmediata y permanencia por coach/horario.",
            "service_bundle": ["clase de prueba", "inscripcion", "membresia combate", "personal boxing"],
            "objections": ["nunca he boxeado", "me da miedo lesionarme", "quiero bajar peso", "solo puedo noches"],
            "growth_motion": "show_up_and_upgrade",
        },
        "personal training": {
            "promise": "Vender evaluacion, plan y continuidad de sesiones con ticket alto.",
            "service_bundle": ["assessment", "plan inicial", "bloque 8 sesiones", "nutricion complementaria"],
            "objections": ["quiero pensarlo", "es caro", "no se si tendre constancia", "prefiero empezar despues"],
            "growth_motion": "high_ticket_package",
        },
    },
    "dental": {
        "ortodoncia": {
            "promise": "Mover valoracion a diagnostico, plan y anticipo con seguimiento disciplinado.",
            "service_bundle": ["valoracion ortodoncia", "diagnostico digital", "plan por fases", "control mensual"],
            "objections": ["quiero comparar", "esta caro", "me da miedo el tiempo de tratamiento", "necesito hablarlo"],
            "growth_motion": "diagnosis_to_advance",
        },
        "implantologia": {
            "promise": "Sostener confianza clinica y financiera en tratamientos de alto valor.",
            "service_bundle": ["valoracion implantologia", "estudio radiografico", "plan quirurgico", "control post quirurgico"],
            "objections": ["me da miedo", "quiero pensarlo", "cuanto tarda", "necesito financiamiento"],
            "growth_motion": "high_ticket_financing",
        },
        "estetica dental": {
            "promise": "Convertir interes aspiracional en valoracion, sonrisa planificada y cierre rapido.",
            "service_bundle": ["valoracion estetica", "diseno de sonrisa", "blanqueamiento", "alineadores esteticos"],
            "objections": ["quiero ver opciones", "cuanto se nota", "es caro", "no se si soy candidato"],
            "growth_motion": "aspirational_package",
        },
        "odontopediatria": {
            "promise": "Reducir no-show y sostener control preventivo con padres bien guiados.",
            "service_bundle": ["primera visita", "limpieza infantil", "selladores", "control preventivo"],
            "objections": ["mi hijo se asusta", "no se deja", "solo quiero cotizar", "no tengo horario"],
            "growth_motion": "preventive_recall",
        },
    },
    "aesthetic": {
        "med spa": {
            "promise": "Vender valoracion premium y paquetes de mayor margen con seguimiento elegante.",
            "service_bundle": ["valoracion premium", "paquete body", "paquete facial", "mantenimiento"],
            "objections": ["quiero saber si soy candidata", "esta caro", "me da miedo un mal resultado", "quiero verlo despues"],
            "growth_motion": "premium_package",
        },
        "depilacion láser": {
            "promise": "Mover interes inmediato a paquete completo y continuidad de sesiones.",
            "service_bundle": ["valoracion laser", "sesion zona chica", "sesion zona grande", "paquete 6 sesiones"],
            "objections": ["duele", "quiero empezar con una zona", "esta caro", "no se cuantas necesito"],
            "growth_motion": "session_package",
        },
        "contouring corporal": {
            "promise": "Llevar una expectativa aspiracional a un plan realista y mantenible.",
            "service_bundle": ["valoracion corporal", "paquete contouring", "seguimiento fotografico", "mantenimiento"],
            "objections": ["quiero resultados rapidos", "no se si funcione", "esta caro", "solo quiero informacion"],
            "growth_motion": "expectation_to_plan",
        },
        "wellness premium": {
            "promise": "Convertir tratamientos premium en membresia o frecuencia ideal.",
            "service_bundle": ["diagnostico wellness", "experiencia premium", "membresia mensual", "mantenimiento"],
            "objections": ["quiero pensarlo", "es lujo", "no tengo tiempo", "que incluye exactamente"],
            "growth_motion": "membership_frequency",
        },
    },
    "vet": {
        "clínica veterinaria": {
            "promise": "Ordenar consulta, seguimiento y control preventivo alrededor de la mascota.",
            "service_bundle": ["consulta general", "seguimiento", "vacunacion", "control anual"],
            "objections": ["quiero saber si es urgente", "solo quiero precio", "no tengo como moverme", "prefiero observarlo"],
            "growth_motion": "consult_to_prevention",
        },
        "grooming": {
            "promise": "Llenar agenda recurrente con recompra y paquetes por frecuencia.",
            "service_bundle": ["grooming basico", "spa pet", "paquete mensual", "recordatorio de siguiente cita"],
            "objections": ["se estresa", "solo quiero una vez", "esta caro", "no se porta bien"],
            "growth_motion": "grooming_recurrence",
        },
        "hotel": {
            "promise": "Convertir estancias en una operacion confiable con upsell de servicios complementarios.",
            "service_bundle": ["estancia corta", "estancia larga", "guarderia", "grooming antes de salida"],
            "objections": ["me da pendiente dejarlo", "quiero ver instalaciones", "es caro", "no se adapta"],
            "growth_motion": "stay_and_addons",
        },
        "planes preventivos": {
            "promise": "Convertir una consulta en relacion recurrente con proxima accion clara.",
            "service_bundle": ["plan preventivo", "vacunas", "desparasitacion", "recordatorio automatico"],
            "objections": ["luego lo veo", "no sabia que tocaba", "es mucho gasto", "mi mascota esta bien"],
            "growth_motion": "preventive_membership",
        },
    },
    "auto-service": {
        "taller mecánico": {
            "promise": "Convertir WhatsApp en intake claro, aprobacion rapida y seguimiento sin friccion.",
            "service_bundle": ["diagnostico", "servicio preventivo", "reparacion correctiva", "recordatorio de mantenimiento"],
            "objections": ["solo quiero cotizar", "no confio en talleres", "cuanto tarda", "lo pensare"],
            "growth_motion": "intake_to_approval",
        },
        "llantera": {
            "promise": "Mover cotizacion inmediata a cita o visita con stock y tiempos claros.",
            "service_bundle": ["cotizacion llantas", "alineacion", "balanceo", "revision express"],
            "objections": ["quiero comparar", "solo una llanta", "esta caro", "voy despues"],
            "growth_motion": "quote_to_visit",
        },
        "hojalatería y pintura": {
            "promise": "Ordenar intake con evidencia, avance y aprobaciones complementarias.",
            "service_bundle": ["valuacion inicial", "diagnostico visual", "autorizacion extra", "entrega"],
            "objections": ["quiero saber si conviene", "cuanto tarda", "puedo pagarlo despues", "quiero comparar"],
            "growth_motion": "estimate_to_authorization",
        },
        "detailing": {
            "promise": "Llenar agenda premium y convertir cada visita en frecuencia o paquete.",
            "service_bundle": ["detailing basico", "detailing premium", "mantenimiento mensual", "add-on interior"],
            "objections": ["solo queria precio", "me da igual hoy", "esta caro", "no se que incluye"],
            "growth_motion": "premium_recurrence",
        },
    },
}


def strongest_vertical_ids() -> list[str]:
    return list(_STRONGEST_VERTICAL_IDS)


def _extract_selected_subvertical(*, org: dict[str, Any] | None = None, bot: dict[str, Any] | None = None) -> str | None:
    bot_config = from_json((bot or {}).get("config_draft_json"), {}) if bot else {}
    if isinstance(bot_config, dict):
        value = str(bot_config.get("selected_subvertical") or bot_config.get("subvertical") or "").strip()
        if value:
            return value
    org_settings = from_json((org or {}).get("settings_json"), {}) if org else {}
    if isinstance(org_settings, dict):
        value = str(org_settings.get("active_subvertical") or org_settings.get("subvertical") or "").strip()
        if value:
            return value
    return None


def _vertical_pack_status(conn: Any, *, organization_id: str | None, bot_id: str | None, sub_profile: dict[str, Any] | None) -> dict[str, Any]:
    if not organization_id or not bot_id or not sub_profile:
        return {
            "selected_subvertical": sub_profile.get("name") if sub_profile else None,
            "services_seeded": 0,
            "services_expected": len(list(sub_profile.get("service_bundle") or [])) if sub_profile else 0,
            "templates_seeded": 0,
            "templates_expected": len(list(sub_profile.get("templates") or [])) if sub_profile else 0,
            "behavior_ready": False,
            "pack_applied": False,
            "coverage_score": 0,
        }
    service_names = [str(item).strip().lower() for item in list(sub_profile.get("service_bundle") or []) if str(item).strip()]
    template_suffix = slugify(str(sub_profile.get("name") or "pack"))
    service_count = 0
    template_count = 0
    if service_names:
        placeholders = ",".join("?" for _ in service_names)
        row = conn.execute(f"SELECT COUNT(*) AS total FROM catalog_services WHERE organization_id = ? AND bot_id = ? AND LOWER(name) IN ({placeholders})", (organization_id, bot_id, *service_names)).fetchone()
        service_count = int((dict(row) if row else {}).get("total") or 0)
    row = conn.execute("SELECT COUNT(*) AS total FROM bot_response_templates WHERE organization_id = ? AND bot_id = ? AND template_key LIKE ?", (organization_id, bot_id, f"%{template_suffix}")).fetchone()
    template_count = int((dict(row) if row else {}).get("total") or 0)
    row = conn.execute("SELECT id FROM bot_behavior_settings WHERE organization_id = ? AND bot_id = ? LIMIT 1", (organization_id, bot_id)).fetchone()
    behavior_ready = bool(row)
    expected_services = len(service_names)
    expected_templates = len(list(sub_profile.get("templates") or []))
    coverage_numerator = service_count + template_count + (1 if behavior_ready else 0)
    coverage_denominator = max(1, expected_services + expected_templates + 1)
    coverage_score = int(round((coverage_numerator / coverage_denominator) * 100))
    return {
        "selected_subvertical": sub_profile.get("name"),
        "services_seeded": service_count,
        "services_expected": expected_services,
        "templates_seeded": template_count,
        "templates_expected": expected_templates,
        "behavior_ready": behavior_ready,
        "pack_applied": bool(service_count or template_count or behavior_ready),
        "coverage_score": coverage_score,
    }


def enrich_vertical_profile_for_runtime(conn: Any, *, profile: dict[str, Any], organization_id: str | None = None, bot: dict[str, Any] | None = None, org: dict[str, Any] | None = None, subvertical: str | None = None) -> dict[str, Any]:
    enriched = enrich_vertical_profile(profile)
    resolved = subvertical or _extract_selected_subvertical(org=org, bot=bot) or (enriched.get("recommended_subverticals") or [None])[0]
    selected = get_subvertical_profile(enriched, resolved)
    if selected:
        enriched["selected_subvertical"] = selected
        enriched["runtime_connection"] = {
            "active_vertical": enriched.get("id"),
            "active_subvertical": selected.get("name"),
            "pack_status": _vertical_pack_status(conn, organization_id=organization_id, bot_id=(bot or {}).get("id"), sub_profile=selected),
            "surface_focus": {
                "onboarding": f"Lanzar {selected.get('name')}",
                "inbox": safe_focus(selected.get("qualification_questions"), default="calificacion operativa"),
                "agenda": safe_focus(selected.get("service_bundle"), default="agenda vertical"),
                "portal": safe_focus(selected.get("kpi_pack"), default="resumen vertical"),
                "commercial": safe_focus(selected.get("automation_priorities"), default="seguimiento"),
            },
        }
    return enriched


def safe_focus(values: Any, *, default: str = "foco") -> str:
    items = list(values or [])
    return str(items[0]) if items else default


def _base_service_bundle(vertical_id: str, subvertical: str) -> list[str]:
    mapping = {
        "fitness": [f"valoracion {subvertical}", f"clase muestra {subvertical}", f"paquete {subvertical}", "seguimiento de asistencia"],
        "dental": [f"valoracion {subvertical}", f"plan {subvertical}", f"control {subvertical}", "recall"],
        "aesthetic": [f"valoracion {subvertical}", f"sesion {subvertical}", f"paquete {subvertical}", "mantenimiento"],
        "vet": [f"servicio {subvertical}", f"seguimiento {subvertical}", "recordatorio preventivo", "proxima visita"],
        "auto-service": [f"diagnostico {subvertical}", f"servicio {subvertical}", "autorizacion extra", "mantenimiento siguiente"],
    }
    return mapping.get(vertical_id, [subvertical])


def _base_questions(vertical_id: str, subvertical: str) -> list[str]:
    common = {
        "fitness": ["cual es tu objetivo principal", "en que horario puedes venir", "has entrenado antes", "quieres clase muestra o plan directo"],
        "dental": ["es urgencia o valoracion", "que te preocupa mas", "cuando te gustaria venir", "necesitas facilidades de pago"],
        "aesthetic": ["que objetivo buscas", "ya te has hecho algo parecido", "cuando quieres empezar", "prefieres sesion o paquete"],
        "vet": ["que especie y edad tiene", "que sintomas o necesidad hay", "es urgencia", "cuando puedes venir"],
        "auto-service": ["que le notas al vehiculo", "es preventivo o falla", "cuando lo puedes traer", "necesitas cotizacion o cita"],
    }
    return common.get(vertical_id, [f"que necesitas sobre {subvertical}"])


def _base_kpis(profile: dict[str, Any], subvertical: str) -> list[str]:
    base = list(profile.get("kpis", []))[:4]
    extras = [f"conversion {subvertical}", f"revenue {subvertical}"]
    result: list[str] = []
    for item in base + extras:
        if item not in result:
            result.append(item)
    return result


def _build_subvertical_profile(profile: dict[str, Any], subvertical: str) -> dict[str, Any]:
    vertical_id = str(profile.get("id") or "")
    overrides = _SUBVERTICAL_OVERRIDES.get(vertical_id, {}).get(subvertical, {})
    service_bundle = list(overrides.get("service_bundle") or _base_service_bundle(vertical_id, subvertical))
    promise = overrides.get("promise") or f"Convertir conversaciones de {subvertical} en siguiente paso claro, cobro y recurrencia."
    objections = list(overrides.get("objections") or list(profile.get("bot_playbook", {}).get("objections", []))[:4])
    score = int(overrides.get("strength_score") or max(70, _VERTICAL_SCORES.get(vertical_id, 80) - max(0, profile.get("subverticals", []).index(subvertical) * 2 if subvertical in profile.get("subverticals", []) else 0)))
    templates = [
        {"key": f"{slugify(subvertical)}-lead", "title": f"Captacion {subvertical}", "content": f"Hola, te ayudo con {subvertical}. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."},
        {"key": f"{slugify(subvertical)}-followup", "title": f"Seguimiento {subvertical}", "content": f"Te sigo con {subvertical}. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."},
        {"key": f"{slugify(subvertical)}-reactivation", "title": f"Reactivacion {subvertical}", "content": f"Te escribo porque todavia podemos mover {subvertical} a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"},
    ]
    return {
        "id": slugify(subvertical),
        "name": subvertical,
        "strength_score": score,
        "promise": promise,
        "growth_motion": overrides.get("growth_motion") or "capture_followup_close",
        "buyer": profile.get("buyer", {}).get("primary"),
        "monetizes": list(profile.get("one_pager", {}).get("monetizes", []))[:4],
        "service_bundle": service_bundle,
        "qualification_questions": _base_questions(vertical_id, subvertical),
        "objections": objections,
        "automation_priorities": [f"seguimiento {subvertical}", "recordatorios", "winback", "upsell"],
        "kpi_pack": _base_kpis(profile, subvertical),
        "recommended_commands": list(_VERTICAL_COMMANDS.get(vertical_id, []))[:4],
        "launch_assets": ["guion whatsapp", "playbook de handoff", "servicios seed", "templates seed"],
        "templates": templates,
        "behavior_overrides": {
            "tone": profile.get("behavior", {}).get("tone") or "cercano",
            "sales_intensity": profile.get("behavior", {}).get("sales_intensity") or "media",
            "required_phrases": [f"te lo aterrizo a tu caso de {subvertical}", "te sigo para moverlo al siguiente paso"],
            "fallback_message": f"Te ayudo con {subvertical}. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso.",
        },
    }


def enrich_vertical_profile(profile: dict[str, Any]) -> dict[str, Any]:
    enriched = deepcopy(profile)
    vertical_id = str(enriched.get("id") or "")
    if vertical_id not in _STRONGEST_VERTICAL_IDS:
        enriched.setdefault("subvertical_profiles", [])
        enriched.setdefault("recommended_subverticals", [])
        return enriched
    sub_profiles = [_build_subvertical_profile(enriched, item) for item in enriched.get("subverticals", [])]
    sub_profiles.sort(key=lambda item: int(item.get("strength_score") or 0), reverse=True)
    enriched["is_strongest_vertical"] = True
    enriched["strongest_rank"] = _STRONGEST_VERTICAL_IDS.index(vertical_id) + 1
    enriched["ten_x_score"] = _VERTICAL_SCORES.get(vertical_id, 80)
    enriched["ten_x_narrative"] = _VERTICAL_NARRATIVES.get(vertical_id)
    enriched["ten_x_growth_loops"] = list(_VERTICAL_GROWTH_LOOPS.get(vertical_id, []))
    enriched["recommended_subverticals"] = [item["name"] for item in sub_profiles[:4]]
    enriched["subvertical_profiles"] = sub_profiles
    enriched["ten_x_operational_pack"] = {
        "recommended_commands": list(_VERTICAL_COMMANDS.get(vertical_id, [])),
        "launch_sequence": ["escoger subvertical", "aplicar pack", "simular conversaciones", "publicar y medir"],
        "why_this_vertical": _VERTICAL_NARRATIVES.get(vertical_id),
    }
    return enriched


def build_strongest_verticals(profiles: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    items = [enrich_vertical_profile(item) for item in profiles if str(item.get("id") or "") in _STRONGEST_VERTICAL_IDS]
    items.sort(key=lambda item: int(item.get("strongest_rank") or 999))
    return items[:limit]


def get_subvertical_profile(profile: dict[str, Any], subvertical: str | None = None) -> dict[str, Any] | None:
    enriched = enrich_vertical_profile(profile)
    sub_profiles = list(enriched.get("subvertical_profiles") or [])
    if not sub_profiles:
        return None
    if not subvertical:
        preferred = str((enriched.get("recommended_subverticals") or [sub_profiles[0].get("name")])[0])
        subvertical = preferred
    normalized = str(subvertical or "").strip().lower()
    for item in sub_profiles:
        if str(item.get("name") or "").strip().lower() == normalized or str(item.get("id") or "") == slugify(normalized):
            return item
    return sub_profiles[0]


def apply_subvertical_pack(conn: Any, *, profile: dict[str, Any], organization_id: str, bot_id: str, subvertical: str | None, actor_user: dict[str, Any] | None = None) -> dict[str, Any]:
    enriched = enrich_vertical_profile(profile)
    sub_profile = get_subvertical_profile(enriched, subvertical)
    if not sub_profile:
        raise ValueError("No subvertical profile available")

    behavior = deepcopy(enriched.get("behavior", {}))
    behavior.update(deepcopy(sub_profile.get("behavior_overrides", {})))
    behavior_row = upsert_bot_behavior_settings(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        tone=str(behavior.get("tone") or "cercano"),
        response_length=str(behavior.get("response_length") or "media"),
        use_emojis=bool(behavior.get("use_emojis") or False),
        sales_intensity=str(behavior.get("sales_intensity") or "media"),
        offer_promotions_when=str(behavior.get("offer_promotions_when") or "when_relevant"),
        escalate_when=list(behavior.get("escalate_when") or []),
        insistence_policy=str(behavior.get("insistence_policy") or "respectful"),
        can_share_price_directly=bool(behavior.get("can_share_price_directly") if behavior.get("can_share_price_directly") is not None else True),
        can_negotiate=bool(behavior.get("can_negotiate") or False),
        can_mention_stock=bool(behavior.get("can_mention_stock") if behavior.get("can_mention_stock") is not None else True),
        auto_send_images=bool(behavior.get("auto_send_images") if behavior.get("auto_send_images") is not None else True),
        bot_mode=str(behavior.get("bot_mode") or "hybrid"),
        active_hours=list(behavior.get("active_hours") or []),
        active_channels=list(behavior.get("active_channels") or ["whatsapp"]),
        forbidden_topics=list(behavior.get("forbidden_topics") or []),
        required_phrases=list(behavior.get("required_phrases") or []),
        fallback_message=str(behavior.get("fallback_message") or "Te ayudo con gusto."),
        actor_user=actor_user,
    )

    template_keys: list[str] = []
    for item in list(enriched.get("templates") or [])[:2] + list(sub_profile.get("templates") or []):
        key = f"{slugify(str(item.get('template_key') or item.get('key') or item.get('title') or 'template'))}-{slugify(str(sub_profile.get('name') or 'pack'))}"
        template_keys.append(key)
        upsert_bot_response_template(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            template_key=key,
            channel="whatsapp",
            title=str(item.get("title") or item.get("name") or key),
            content=str(item.get("content") or ""),
            variables=list(item.get("variables") or []),
            actor_user=actor_user,
        )

    existing_services = {str(item.get("name") or "").strip().lower() for item in list_catalog_services(conn, organization_id, bot_id)}
    created_services: list[str] = []
    for name in list(sub_profile.get("service_bundle") or []):
        if name.strip().lower() in existing_services:
            continue
        created = create_catalog_service(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            category_id=None,
            name=name,
            duration_minutes=45 if enriched.get("id") != "auto-service" else 60,
            price=0,
            currency="MXN",
            preparation="",
            restrictions="",
            availability={},
            photos=[],
            associated_staff=None,
            branch=None,
            status="active",
            actor_user=actor_user,
        )
        created_services.append(str(created.get("name") or name))
        existing_services.add(name.strip().lower())

    bot_row = conn.execute("SELECT * FROM bots WHERE id = ? AND organization_id = ?", (bot_id, organization_id)).fetchone()
    org_row = conn.execute("SELECT * FROM organizations WHERE id = ?", (organization_id,)).fetchone()
    bot_dict = dict(bot_row) if bot_row else {}
    org_dict = dict(org_row) if org_row else {}
    bot_config = from_json(bot_dict.get("config_draft_json"), {}) if bot_dict else {}
    if not isinstance(bot_config, dict):
        bot_config = {}
    bot_config["selected_subvertical"] = sub_profile.get("name")
    bot_config["vertical_pack_applied_at"] = utcnow_iso()
    bot_config["vertical_pack_strength_score"] = sub_profile.get("strength_score")
    conn.execute("UPDATE bots SET config_draft_json = ?, updated_at = ? WHERE id = ?", (to_json(bot_config), utcnow_iso(), bot_id))
    org_settings = from_json(org_dict.get("settings_json"), {}) if org_dict else {}
    if not isinstance(org_settings, dict):
        org_settings = {}
    org_settings["subvertical"] = sub_profile.get("name")
    org_settings["active_subvertical"] = sub_profile.get("name")
    conn.execute("UPDATE organizations SET settings_json = ?, updated_at = ? WHERE id = ?", (to_json(org_settings), utcnow_iso(), organization_id))
    create_audit_log(
        conn,
        organization_id=organization_id,
        actor_user_id=(actor_user or {}).get("id"),
        actor_type="user",
        entity_type="vertical_pack",
        entity_id=bot_id,
        action="vertical.subvertical_pack_applied",
        metadata={
            "vertical_id": enriched.get("id"),
            "subvertical": sub_profile.get("name"),
            "template_keys": template_keys,
            "created_services": created_services,
        },
    )
    return {
        "vertical_id": enriched.get("id"),
        "vertical_name": enriched.get("name"),
        "subvertical": sub_profile.get("name"),
        "strength_score": sub_profile.get("strength_score"),
        "behavior": behavior_row,
        "created_services": created_services,
        "template_keys": template_keys,
        "runtime_connection": {
            "active_vertical": enriched.get("id"),
            "active_subvertical": sub_profile.get("name"),
            "pack_status": _vertical_pack_status(conn, organization_id=organization_id, bot_id=bot_id, sub_profile=sub_profile),
        },
        "launch_checklist": ["revisar servicios creados", "simular conversaciones", "publicar el bot", "medir conversion por subvertical"],
    }
