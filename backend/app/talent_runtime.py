from __future__ import annotations

from copy import deepcopy
from typing import Any

from .utils import new_id, to_json, utcnow_iso
from .runtime_schema_guards import assert_schema_ready

_DEFAULT_WORKER_KEYWORDS = [
    "soy trabajador",
    "soy empleado",
    "trabajo aqui",
    "trabajo ahí",
    "trabajo ahi",
    "mi turno",
    "mi horario",
    "rh",
    "recursos humanos",
    "nomina",
    "nómina",
    "entrada",
    "salida",
    "jefe",
    "encargado",
]

_DEFAULT_TALENT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "scope": "bot",
    "inherit_from_organization": False,
    "vacancies_enabled": True,
    "worker_recognition_enabled": True,
    "never_silent": True,
    "default_handoff_on_unknown": False,
    "salary_policy": {
        "source": "portal",
        "visible_only_if_defined": True,
        "hide_message": "El sueldo se comparte durante el proceso de selección.",
    },
    "interview_policy": {
        "source": "portal",
        "allow_manual_text_fallback": True,
        "no_schedule_message": "Por ahora no cuento con horarios definidos para entrevista. En cuanto estén disponibles te lo confirmaremos.",
        "allow_interest_capture_without_schedule": True,
    },
    "candidate_policy": {
        "register_only_after_interview_confirmation": True,
        "prelead_enabled": True,
        "confirmation_message": "Perfecto. Ya dejé registrada tu confirmación para entrevista.",
    },
    "worker_recognition": {
        "enabled": True,
        "keywords": list(_DEFAULT_WORKER_KEYWORDS),
        "known_contacts": [],
        "confidence_threshold_auto_worker": 0.8,
        "confidence_threshold_soft_worker": 0.55,
        "worker_fallback_message": "Gracias por escribir. Ya detecté que hablas como parte del equipo. Te ayudaremos a canalizar esto con RH o con la persona responsable.",
        "route_worker_to_human": True,
    },
    "fallback_messages": {
        "generic": "Te ayudo con gusto. Si me dices la vacante o lo que quieres saber, te respondo de forma más precisa.",
        "unknown_vacancy": "Sí te puedo ayudar con vacantes, pero necesito que me digas cuál te interesa para darte información correcta.",
        "no_interview_schedule": "Por ahora no cuento con horarios definidos para entrevista. En cuanto estén disponibles te lo confirmaremos.",
    },
    "vacancies": [],
}


_TALENT_KEYWORDS = [
    "vacante",
    "vacantes",
    "empleo",
    "trabajo",
    "puesto",
    "postular",
    "postulación",
    "postulacion",
    "entrevista",
    "requisitos",
    "sueldo",
    "salario",
    "horario",
]


_INTERVIEW_CONFIRM_MARKERS = [
    "confirmo",
    "confirmar",
    "si asisto",
    "sí asisto",
    "ahi estare",
    "ahí estaré",
    "ahi estaré",
    "alli estare",
    "allí estaré",
    "ok asisto",
    "asisto",
    "puedo asistir",
]


_PROFILE_WORKER = "worker"
_PROFILE_CANDIDATE = "candidate"


def _normalize_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def _fetch_one(conn, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    return _normalize_row(conn.execute(sql, params).fetchone())


def _fetch_all(conn, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [_normalize_row(row) or {} for row in conn.execute(sql, params).fetchall()]


def _execute(conn, sql: str, params: tuple[Any, ...] = ()) -> None:
    conn.execute(sql, params)
    conn.commit()


def _table_exists(conn, table: str) -> bool:
    backend = getattr(conn, "backend", "sqlite")
    if backend == "sqlite":
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
        return bool(row)
    row = conn.execute(
        "SELECT 1 AS present FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = ? LIMIT 1",
        (table,),
    ).fetchone()
    return bool(row)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def default_talent_config() -> dict[str, Any]:
    return deepcopy(_DEFAULT_TALENT_CONFIG)


def normalize_talent_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    config = _deep_merge(default_talent_config(), raw)
    vacancies: list[dict[str, Any]] = []
    for item in config.get("vacancies", []) or []:
        if not isinstance(item, dict):
            continue
        vacancy = {
            "id": str(item.get("id") or new_id("vac")),
            "title": str(item.get("title") or item.get("name") or "Vacante").strip(),
            "status": str(item.get("status") or "draft").strip().lower(),
            "summary": str(item.get("summary") or "").strip(),
            "description": str(item.get("description") or "").strip(),
            "requirements": [str(req).strip() for req in (item.get("requirements") or []) if str(req).strip()],
            "benefits": [str(req).strip() for req in (item.get("benefits") or []) if str(req).strip()],
            "location_label": str(item.get("location_label") or "").strip(),
            "address": str(item.get("address") or "").strip(),
            "modality": str(item.get("modality") or "presencial").strip().lower(),
            "work_days": str(item.get("work_days") or "").strip(),
            "work_hours": str(item.get("work_hours") or "").strip(),
            "salary_visible": bool(item.get("salary_visible")),
            "salary_min": item.get("salary_min"),
            "salary_max": item.get("salary_max"),
            "currency": str(item.get("currency") or "MXN").strip(),
            "interview_slots_enabled": bool(item.get("interview_slots_enabled")),
            "interview_schedule": str(item.get("interview_schedule") or "").strip(),
            "interview_location": str(item.get("interview_location") or "").strip(),
            "interview_notes": str(item.get("interview_notes") or "").strip(),
            "documents_required": [str(req).strip() for req in (item.get("documents_required") or []) if str(req).strip()],
            "faqs": [faq for faq in (item.get("faqs") or []) if isinstance(faq, dict)],
        }
        vacancies.append(vacancy)
    config["vacancies"] = vacancies
    return config


def talent_config_from_bot_config(bot_config: dict[str, Any]) -> dict[str, Any]:
    return normalize_talent_config((bot_config.get("talent") or {}))


def active_vacancies(bot_config: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in talent_config_from_bot_config(bot_config).get("vacancies", []) if item.get("status") in {"active", "published"}]


def _contains_any(text: str, markers: list[str]) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in markers)


def detect_worker_profile(text: str, memory: dict[str, Any], bot_config: dict[str, Any]) -> dict[str, Any] | None:
    config = talent_config_from_bot_config(bot_config)
    worker = config.get("worker_recognition", {}) or {}
    if not config.get("enabled") or not config.get("worker_recognition_enabled") or not worker.get("enabled", True):
        return None
    memory_mode = str(memory.get("current_mode") or "").lower()
    keywords = [str(item).strip().lower() for item in worker.get("keywords", []) if str(item).strip()]
    confidence = 0.0
    matched: list[str] = []
    lower = text.lower()
    if memory_mode == _PROFILE_WORKER:
        confidence = max(confidence, 0.7)
    for marker in keywords:
        if marker and marker in lower:
            matched.append(marker)
    if matched:
        confidence = max(confidence, 0.9 if len(matched) > 1 else 0.65)
    if confidence <= 0:
        return None
    return {
        "profile_type": _PROFILE_WORKER,
        "confidence": confidence,
        "matched_keywords": matched,
        "handoff": bool(worker.get("route_worker_to_human", True)),
    }


def find_relevant_vacancy(text: str, bot_config: dict[str, Any], memory: dict[str, Any] | None = None) -> dict[str, Any] | None:
    lower = text.lower()
    active = active_vacancies(bot_config)
    if len(active) == 1:
        return active[0]
    best: tuple[int, dict[str, Any] | None] = (0, None)
    for vacancy in active:
        score = 0
        title = str(vacancy.get("title") or "").lower()
        summary = str(vacancy.get("summary") or "").lower()
        for token in [part for part in title.replace("/", " ").split() if len(part) >= 3]:
            if token in lower:
                score += 2
        for token in [part for part in summary.replace("/", " ").split() if len(part) >= 5][:5]:
            if token in lower:
                score += 1
        if score > best[0]:
            best = (score, vacancy)
    if best[1] is not None and best[0] > 0:
        return best[1]
    hinted = str((memory or {}).get("interest") or "").lower().strip()
    for vacancy in active:
        if hinted and hinted in str(vacancy.get("title") or "").lower():
            return vacancy
    return None


def detect_talent_intent(text: str, memory: dict[str, Any], bot_config: dict[str, Any]) -> dict[str, Any] | None:
    config = talent_config_from_bot_config(bot_config)
    if not config.get("enabled"):
        return None
    lower = text.lower().strip()
    worker_profile = detect_worker_profile(text, memory, bot_config)
    if worker_profile:
        intent = "worker_schedule" if _contains_any(lower, ["horario", "turno", "entrada", "salida"]) else "worker_support"
        return {
            "intent": intent,
            "lead_stage": memory.get("lead_stage") or "contacted",
            "objection": "",
            "score_delta": 0,
            "requested_human": bool(worker_profile.get("handoff")),
            "sentiment": "neutral",
            "interest": memory.get("interest"),
            "urgency_level": "medium",
            "urgency_score": 55,
            "current_mode": _PROFILE_WORKER,
            "profile_type": _PROFILE_WORKER,
            "talent_module": True,
            "worker_confidence": worker_profile.get("confidence"),
        }

    employment_signal = _contains_any(lower, _TALENT_KEYWORDS) or any(
        str(vacancy.get("title") or "").lower() in lower for vacancy in active_vacancies(bot_config) if str(vacancy.get("title") or "").strip()
    )
    if not employment_signal:
        return None

    vacancy = find_relevant_vacancy(text, bot_config, memory)
    if _contains_any(lower, _INTERVIEW_CONFIRM_MARKERS):
        intent = "job_confirm_interview"
        score_delta = 25
    elif _contains_any(lower, ["entrevista", "ubicacion entrevista", "ubicación entrevista", "donde es la entrevista", "a que hora", "a qué hora"]):
        intent = "job_interview_details"
        score_delta = 10
    elif _contains_any(lower, ["requisito", "requisitos", "piden", "experiencia", "documentos"]):
        intent = "job_requirements"
        score_delta = 8
    elif _contains_any(lower, ["sueldo", "salario", "pagan", "cuanto pagan", "cuánto pagan"]):
        intent = "job_salary"
        score_delta = 10
    elif _contains_any(lower, ["donde", "dónde", "ubicacion", "ubicación", "direccion", "dirección", "zona"]):
        intent = "job_location"
        score_delta = 8
    elif _contains_any(lower, ["horario", "hora", "dias", "días", "turno"]):
        intent = "job_schedule"
        score_delta = 8
    elif _contains_any(lower, ["me interesa", "quiero aplicar", "quiero postular", "como aplico", "cómo aplico", "postularme", "aplicar"]):
        intent = "job_apply"
        score_delta = 12
    else:
        intent = "job_info"
        score_delta = 8

    urgency = "medium" if intent in {"job_apply", "job_confirm_interview", "job_interview_details"} else "normal"
    urgency_score = 55 if urgency == "medium" else 20
    return {
        "intent": intent,
        "lead_stage": "qualified" if intent in {"job_apply", "job_confirm_interview"} else (memory.get("lead_stage") or "contacted"),
        "objection": "",
        "score_delta": score_delta,
        "requested_human": False,
        "sentiment": "positive" if intent in {"job_apply", "job_confirm_interview"} else "neutral",
        "interest": vacancy.get("title") if vacancy else (memory.get("interest") or None),
        "urgency_level": urgency,
        "urgency_score": urgency_score,
        "current_mode": _PROFILE_CANDIDATE,
        "profile_type": _PROFILE_CANDIDATE,
        "vacancy_id": vacancy.get("id") if vacancy else None,
        "vacancy_title": vacancy.get("title") if vacancy else None,
        "talent_module": True,
    }


def _salary_text(vacancy: dict[str, Any], config: dict[str, Any]) -> str:
    salary_policy = config.get("salary_policy", {}) or {}
    visible = bool(vacancy.get("salary_visible"))
    salary_min = vacancy.get("salary_min")
    salary_max = vacancy.get("salary_max")
    currency = vacancy.get("currency") or "MXN"
    if visible and (salary_min is not None or salary_max is not None):
        if salary_min is not None and salary_max is not None:
            return f"El sueldo va de {salary_min} a {salary_max} {currency}."
        if salary_min is not None:
            return f"El sueldo parte de {salary_min} {currency}."
        return f"El sueldo puede llegar a {salary_max} {currency}."
    return str(salary_policy.get("hide_message") or "El sueldo se comparte durante el proceso de selección.")


def _pick_vacancy_or_none(bot_config: dict[str, Any], classification: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any] | None:
    vacancy_id = classification.get("vacancy_id")
    if vacancy_id:
        for vacancy in active_vacancies(bot_config):
            if vacancy.get("id") == vacancy_id:
                return vacancy
    interest = str(classification.get("vacancy_title") or memory.get("interest") or "").lower().strip()
    for vacancy in active_vacancies(bot_config):
        if interest and interest in str(vacancy.get("title") or "").lower():
            return vacancy
    return find_relevant_vacancy(interest, bot_config, memory) if interest else find_relevant_vacancy("", bot_config, memory)


def generate_talent_reply(text: str, classification: dict[str, Any], bot_config: dict[str, Any], memory: dict[str, Any]) -> str | None:
    del text
    config = talent_config_from_bot_config(bot_config)
    if not config.get("enabled"):
        return None
    intent = str(classification.get("intent") or "")
    if intent.startswith("worker_"):
        fallback = str((config.get("worker_recognition", {}) or {}).get("worker_fallback_message") or "").strip()
        if intent == "worker_schedule":
            return fallback + " Si me compartes el área o el turno, lo dejamos mejor dirigido."
        return fallback

    vacancy = _pick_vacancy_or_none(bot_config, classification, memory)
    if vacancy is None:
        return str((config.get("fallback_messages", {}) or {}).get("unknown_vacancy") or (config.get("fallback_messages", {}) or {}).get("generic") or "Te ayudo con vacantes. Dime cuál te interesa y te comparto la información disponible.")

    interview_policy = config.get("interview_policy", {}) or {}
    interview_message = str(interview_policy.get("no_schedule_message") or config.get("fallback_messages", {}).get("no_interview_schedule") or "Por ahora no cuento con horarios definidos para entrevista.")
    title = str(vacancy.get("title") or "Vacante")
    location = str(vacancy.get("location_label") or vacancy.get("address") or "").strip()
    schedule = " ".join(part for part in [str(vacancy.get("work_days") or "").strip(), str(vacancy.get("work_hours") or "").strip()] if part).strip()
    summary = str(vacancy.get("summary") or vacancy.get("description") or "").strip()

    if intent == "job_info":
        chunks = [f"La vacante {title} trata de {summary or 'apoyar la operación del negocio'}." ]
        if location:
            chunks.append(f"La ubicación es {location}.")
        if schedule:
            chunks.append(f"El horario es {schedule}.")
        chunks.append(_salary_text(vacancy, config))
        chunks.append("Si quieres, también te comparto requisitos o detalles de entrevista.")
        return " ".join(part for part in chunks if part)
    if intent == "job_requirements":
        requirements = vacancy.get("requirements") or []
        if requirements:
            return f"Para la vacante {title}, los requisitos son: " + "; ".join(str(item) for item in requirements) + "."
        return f"Sí te puedo ayudar con la vacante {title}, pero por ahora no tengo requisitos específicos cargados en portal. Si quieres, dejo tu interés registrado para seguimiento."
    if intent == "job_salary":
        return _salary_text(vacancy, config)
    if intent == "job_location":
        if location or vacancy.get("address"):
            address = str(vacancy.get("address") or "").strip()
            return " ".join(part for part in [f"La vacante {title} se maneja en {location or address}.", f"Dirección: {address}." if address and address != location else ""] if part)
        return f"Sí tengo registrada la vacante {title}, pero por ahora no tengo una ubicación cargada en portal. En cuanto esté disponible te la confirmamos."
    if intent == "job_schedule":
        if schedule:
            return f"El horario para {title} es {schedule}."
        return f"Sí tengo registrada la vacante {title}, pero por ahora no tengo horario laboral definido en portal. En cuanto esté listo te lo confirmamos."
    if intent == "job_apply":
        return f"Perfecto. Ya vi que te interesa la vacante {title}. Si quieres avanzar, también te puedo compartir requisitos o detalles de entrevista."
    if intent == "job_confirm_interview":
        schedule_text = str(vacancy.get("interview_schedule") or "").strip()
        location_text = str(vacancy.get("interview_location") or vacancy.get("address") or "").strip()
        parts = [str((config.get("candidate_policy", {}) or {}).get("confirmation_message") or "Perfecto. Ya quedó registrada tu confirmación de entrevista.")]
        if schedule_text:
            parts.append(f"Horario confirmado: {schedule_text}.")
        elif config.get("never_silent", True):
            parts.append(interview_message)
        if location_text:
            parts.append(f"Ubicación: {location_text}.")
        return " ".join(part for part in parts if part)
    if intent == "job_interview_details":
        schedule_text = str(vacancy.get("interview_schedule") or "").strip()
        location_text = str(vacancy.get("interview_location") or vacancy.get("address") or "").strip()
        notes = str(vacancy.get("interview_notes") or "").strip()
        docs = [str(item) for item in (vacancy.get("documents_required") or []) if str(item).strip()]
        if not schedule_text:
            parts = [interview_message]
            if location_text:
                parts.append(f"La entrevista se maneja en {location_text}.")
            return " ".join(parts)
        parts = [f"La entrevista para {title} está definida para {schedule_text}."]
        if location_text:
            parts.append(f"Ubicación: {location_text}.")
        if docs:
            parts.append("Documentos sugeridos: " + ", ".join(docs) + ".")
        if notes:
            parts.append(notes)
        return " ".join(parts)
    if config.get("never_silent", True):
        return str((config.get("fallback_messages", {}) or {}).get("generic") or "Te ayudo con vacantes. Dime qué quieres saber y te respondo con lo que ya está cargado en portal.")
    return None


def ensure_talent_schema(conn) -> None:
    assert_schema_ready(
        conn,
        owner="talent_runtime",
        tables=("talent_candidates",),
    )


def confirm_candidate(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str | None,
    contact_id: str,
    vacancy_id: str | None,
    vacancy_title: str | None,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_talent_schema(conn)
    now = utcnow_iso()
    existing = _fetch_one(
        conn,
        "SELECT * FROM talent_candidates WHERE bot_id = ? AND contact_id = ? AND COALESCE(vacancy_id, '') = COALESCE(?, '') LIMIT 1",
        (bot_id, contact_id, vacancy_id),
    )
    payload = profile or {}
    if existing:
        _execute(
            conn,
            "UPDATE talent_candidates SET conversation_id = ?, vacancy_title = ?, status = 'interview_confirmed', interview_confirmed_at = ?, profile_json = ?, updated_at = ? WHERE id = ?",
            (conversation_id, vacancy_title, now, to_json(payload), now, existing["id"]),
        )
        return _fetch_one(conn, "SELECT * FROM talent_candidates WHERE id = ?", (existing["id"],)) or {}
    candidate_id = new_id("cand")
    _execute(
        conn,
        "INSERT INTO talent_candidates (id, organization_id, bot_id, conversation_id, contact_id, vacancy_id, vacancy_title, status, source, interview_confirmed_at, profile_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'interview_confirmed', 'bot', ?, ?, ?, ?)",
        (candidate_id, organization_id, bot_id, conversation_id, contact_id, vacancy_id, vacancy_title, now, to_json(payload), now, now),
    )
    return _fetch_one(conn, "SELECT * FROM talent_candidates WHERE id = ?", (candidate_id,)) or {}


def maybe_register_candidate_confirmation(conn, *, organization_id: str, bot_id: str, conversation_id: str | None, contact_id: str, classification: dict[str, Any], memory: dict[str, Any], bot_config: dict[str, Any]) -> dict[str, Any] | None:
    config = talent_config_from_bot_config(bot_config)
    policy = config.get("candidate_policy", {}) or {}
    if not config.get("enabled") or not policy.get("register_only_after_interview_confirmation", True):
        return None
    if classification.get("intent") != "job_confirm_interview":
        return None
    vacancy = _pick_vacancy_or_none(bot_config, classification, memory)
    return confirm_candidate(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        vacancy_id=vacancy.get("id") if vacancy else classification.get("vacancy_id"),
        vacancy_title=vacancy.get("title") if vacancy else classification.get("vacancy_title"),
        profile={
            "intent": classification.get("intent"),
            "interest": classification.get("interest"),
            "profile_type": classification.get("profile_type"),
            "registered_at": utcnow_iso(),
        },
    )


def list_candidates(conn, *, bot_id: str) -> list[dict[str, Any]]:
    if not _table_exists(conn, "talent_candidates"):
        return []
    return _fetch_all(conn, "SELECT * FROM talent_candidates WHERE bot_id = ? ORDER BY updated_at DESC", (bot_id,))
