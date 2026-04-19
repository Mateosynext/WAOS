from __future__ import annotations

from copy import deepcopy
from typing import Any

from .domains.bot_behavior import upsert_bot_behavior_settings, upsert_bot_response_template
from .domains.catalog import create_catalog_service, list_catalog_services
from .knowledge_runtime import ingest_knowledge_document
from .utils import from_json, new_id, slugify, to_json, utcnow_iso
from .vertical_10x import apply_subvertical_pack, get_subvertical_profile
from .verticals import build_vertical_bot_setup, get_vertical_profile, list_vertical_profiles, normalize_vertical_key
from .world_class import execute, fetch_all, fetch_one


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
        "fields": ["business_name", "bot_name", "tone", "language", "timezone", "hours", "whatsapp_number"],
    },
    {
        "key": "catalog_offer",
        "label": "Oferta, catalogo y CTAs",
        "required": True,
        "fields": ["services", "featured_offers", "primary_ctas", "pricing_notes"],
    },
    {
        "key": "knowledge_seed",
        "label": "Knowledge base viva",
        "required": True,
        "fields": ["faqs", "policies", "knowledge_sources", "owner_user_id"],
    },
    {
        "key": "integrations_rules",
        "label": "Integraciones, reglas y escalamiento",
        "required": True,
        "fields": ["selected_integrations", "escalate_when", "handoff_keywords", "rule_overrides"],
    },
    {
        "key": "launch_review",
        "label": "Automatizaciones y salida a produccion",
        "required": False,
        "fields": ["recommended_playbooks", "launch_notes", "autopublish_knowledge"],
    },
]

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
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS vertical_onboarding_wizards (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            vertical_id TEXT NOT NULL,
            subvertical TEXT,
            wizard_version TEXT NOT NULL DEFAULT 'guided_vertical_onboarding_v1',
            status TEXT NOT NULL DEFAULT 'draft',
            current_step TEXT,
            progress_percent INTEGER NOT NULL DEFAULT 0,
            business_name TEXT,
            bot_name TEXT,
            tone TEXT,
            language TEXT,
            timezone TEXT,
            primary_objective TEXT,
            answers_json TEXT NOT NULL DEFAULT '{}',
            setup_json TEXT NOT NULL DEFAULT '{}',
            checklist_json TEXT NOT NULL DEFAULT '[]',
            recommended_integrations_json TEXT NOT NULL DEFAULT '[]',
            recommended_playbooks_json TEXT NOT NULL DEFAULT '[]',
            recommended_ctas_json TEXT NOT NULL DEFAULT '[]',
            applied_summary_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            applied_at TEXT,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS vertical_onboarding_step_runs (
            id TEXT PRIMARY KEY,
            wizard_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            step_key TEXT NOT NULL,
            step_status TEXT NOT NULL DEFAULT 'pending',
            is_required INTEGER NOT NULL DEFAULT 1,
            payload_json TEXT NOT NULL DEFAULT '{}',
            generated_patch_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            UNIQUE(wizard_id, step_key),
            FOREIGN KEY (wizard_id) REFERENCES vertical_onboarding_wizards(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id)
        );

        CREATE INDEX IF NOT EXISTS idx_vertical_onboarding_wizards_org ON vertical_onboarding_wizards(organization_id, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_vertical_onboarding_wizards_bot ON vertical_onboarding_wizards(bot_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_vertical_onboarding_step_runs_wizard ON vertical_onboarding_step_runs(wizard_id, step_key);
        """
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
    payload = answers.get(step["key"], {}) if isinstance(answers, dict) else {}
    completed = True
    for field in step.get("fields") or []:
        value = payload.get(field) if isinstance(payload, dict) else None
        if step.get("required") and (value is None or value == "" or value == [] or value == {}):
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
    merged_answers = _deep_merge(defaults, answers or {})
    steps = [_step_state(step, merged_answers) for step in _GUIDED_STEPS]
    progress_percent, current_step = _progress_summary(steps)
    setup = _build_setup_payload(profile=profile, subvertical=selected_sub.get("name") if selected_sub else subvertical, answers=merged_answers, bot_id=bot_id)
    checklist = [
        {"key": "vertical_pack", "label": "Vertical y subvertical definidas", "completed": bool(selected_sub or profile.get("id"))},
        {"key": "services", "label": "Catalogo minimo listo", "completed": len(setup.get("services") or []) > 0},
        {"key": "knowledge", "label": "Knowledge base inicial lista", "completed": len((merged_answers.get("knowledge_seed") or {}).get("faqs") or []) > 0},
        {"key": "integrations", "label": "Integraciones planificadas", "completed": len(setup.get("wizard", {}).get("recommended_integrations") or []) > 0},
        {"key": "automation", "label": "Playbooks sugeridos seleccionados", "completed": len(setup.get("wizard", {}).get("recommended_playbooks") or []) > 0},
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
        "answers": merged_answers,
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
    }.items():
        clean_key = key[:-5] if key.endswith("_json") else key
        payload[clean_key] = from_json(payload.get(key), default)
    return payload


def _parse_step_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["payload"] = from_json(payload.get("payload_json"), {})
    payload["generated_patch"] = from_json(payload.get("generated_patch_json"), {})
    return payload


def get_guided_onboarding_wizard(conn: Any, wizard_id: str) -> dict[str, Any] | None:
    ensure_guided_vertical_onboarding_schema(conn)
    row = _parse_wizard_row(fetch_one(conn, "SELECT * FROM vertical_onboarding_wizards WHERE id = ?", (wizard_id,)))
    if not row:
        return None
    steps = [_parse_step_row(item) for item in fetch_all(conn, "SELECT * FROM vertical_onboarding_step_runs WHERE wizard_id = ? ORDER BY created_at ASC", (wizard_id,))]
    row["step_runs"] = steps
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
            applied_summary_json, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?, ?)
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
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("business_name"),
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("bot_name"),
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("tone"),
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("language"),
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("timezone"),
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
    return get_guided_onboarding_wizard(conn, wizard_id) or {"id": wizard_id}


def update_guided_onboarding_step(conn: Any, *, wizard_id: str, step_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_guided_vertical_onboarding_schema(conn)
    wizard = get_guided_onboarding_wizard(conn, wizard_id)
    if not wizard:
        raise ValueError("wizard_not_found")
    answers = deepcopy(wizard.get("answers") or {})
    answers[step_key] = _deep_merge(answers.get(step_key, {}), payload or {})
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
    execute(
        conn,
        """
        UPDATE vertical_onboarding_wizards
        SET subvertical = ?, current_step = ?, progress_percent = ?, business_name = ?, bot_name = ?, tone = ?, language = ?, timezone = ?, primary_objective = ?,
            answers_json = ?, setup_json = ?, checklist_json = ?, recommended_integrations_json = ?, recommended_playbooks_json = ?, recommended_ctas_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            blueprint.get("selected_subvertical", {}).get("name") if blueprint.get("selected_subvertical") else wizard.get("subvertical"),
            blueprint.get("current_step"),
            blueprint.get("progress_percent") or 0,
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("business_name"),
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("bot_name"),
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("tone"),
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("language"),
            ((blueprint.get("answers") or {}).get("business_basics") or {}).get("timezone"),
            ((blueprint.get("answers") or {}).get("vertical_fit") or {}).get("primary_objective"),
            to_json(blueprint.get("answers") or {}),
            to_json(blueprint.get("setup") or {}),
            to_json(blueprint.get("checklist") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_integrations") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_playbooks") or []),
            to_json((blueprint.get("setup") or {}).get("wizard", {}).get("recommended_ctas") or []),
            now,
            wizard_id,
        ),
    )
    for step in blueprint.get("steps") or []:
        execute(
            conn,
            """
            UPDATE vertical_onboarding_step_runs
            SET step_status = ?, payload_json = ?, generated_patch_json = ?, updated_at = ?, completed_at = ?
            WHERE wizard_id = ? AND step_key = ?
            """,
            (
                step.get("status") or "pending",
                to_json(step.get("payload") or {}),
                to_json({"step_label": step.get("label")}),
                now,
                now if step.get("completed") else None,
                wizard_id,
                step.get("key"),
            ),
        )
    return get_guided_onboarding_wizard(conn, wizard_id) or wizard


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


def apply_guided_onboarding_wizard(conn: Any, *, wizard_id: str, actor_user: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_guided_vertical_onboarding_schema(conn)
    wizard = get_guided_onboarding_wizard(conn, wizard_id)
    if not wizard:
        raise ValueError("wizard_not_found")
    if not wizard.get("bot_id"):
        raise ValueError("wizard_requires_bot")
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
    bot_row = fetch_one(conn, "SELECT * FROM bots WHERE id = ? AND organization_id = ?", (wizard["bot_id"], wizard["organization_id"])) or {}
    if not bot_row:
        raise ValueError("bot_not_found")

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
    return {
        "wizard": get_guided_onboarding_wizard(conn, wizard_id),
        "behavior": behavior_row,
        "pack_result": pack_result,
        "created_services": created_services,
        "knowledge_documents": [item.get("id") for item in docs_seeded],
        "planned_integrations": [{"id": row.get("id"), "provider": row.get("provider"), "status": row.get("status")} for row in integration_rows],
        "summary": applied_summary,
    }
