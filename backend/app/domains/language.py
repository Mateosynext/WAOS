from __future__ import annotations

from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ..db import execute, fetch_all, fetch_one
from ..repositories import create_audit_log, create_message, get_bot, get_contact, get_conversation
from ..utils import add_minutes, from_json, new_id, parse_iso, to_json, utcnow_iso


DEFAULT_LANGUAGE_TEMPLATES: dict[str, Any] = {
    "es": {
        "welcome": "Hola, te ayudo por aquí.",
        "payment_reminder": "Aún tengo tu link de pago listo.",
        "human_handoff": "Te paso con una persona manteniendo tu idioma.",
        "voice_profile": {
            "persona": "cercano, claro, ágil y bien presentado",
            "avoid": ["corporativo", "demasiado tecnico", "traducido raro", "robotico"],
            "style_rules": [
                "hablar simple y natural",
                "sonar como alguien que entiende negocio",
                "usar humor ligero solo cuando suma",
                "cerrar con siguiente paso",
            ],
        },
        "tone_matrix": {
            "formal": {"ack": "con gusto", "bridge": "te lo explico claro y sin rollo", "close": "si quieres, lo aterrizamos a tu caso"},
            "casual": {"ack": "va", "bridge": "te lo aterrizo fácil", "close": "si quieres, lo vemos a tu caso"},
            "playful": {"ack": "jajaja, sí te sigo", "bridge": "pero justo ahí está el detalle", "close": "¿dónde se te atora más ahorita?"},
            "overwhelmed": {"ack": "sí te creo", "bridge": "cuando ya traes todo encima, ahí es donde más se fugan ventas y tiempo", "close": "¿qué te está drenando más hoy?"},
            "direct": {"ack": "de una", "bridge": "voy al punto", "close": "dime y lo movemos"},
        },
        "phrase_bank": {
            "safe_openers": ["sí te creo", "va", "con gusto", "te sigo"],
            "safe_bridges": ["justo ahí está el detalle", "ahí es donde entra bien", "te lo aterrizo fácil"],
            "safe_closes": ["¿qué te está atorando más?", "¿te lo bajo a tu caso?", "¿prefieres que te diga el siguiente paso?"],
        },
    },
    "en": {
        "welcome": "Hey, I can help you here.",
        "payment_reminder": "I still have your payment link ready.",
        "human_handoff": "I can hand you off to a person and keep the conversation in your language.",
        "voice_profile": {
            "persona": "clear, sharp, friendly, and commercial without sounding pushy",
            "avoid": ["corporate", "too technical", "literal translation", "robotic"],
            "style_rules": [
                "sound native in English",
                "keep replies short and useful",
                "use light humor only when it helps",
                "always leave a next step",
            ],
        },
        "tone_matrix": {
            "formal": {"ack": "happy to help", "bridge": "let me keep this clear and simple", "close": "if you want, I can map it to your case"},
            "casual": {"ack": "got you", "bridge": "here is the simple version", "close": "if you want, I can make it specific to your setup"},
            "playful": {"ack": "haha, fair", "bridge": "but that is usually where the real business issue shows up", "close": "where is it getting stuck more right now?"},
            "overwhelmed": {"ack": "I get you", "bridge": "when everything piles up, that is where time and sales start leaking", "close": "what is draining you the most right now?"},
            "direct": {"ack": "got it", "bridge": "straight to it", "close": "tell me and we can move it forward"},
        },
        "phrase_bank": {
            "safe_openers": ["I got you", "happy to help", "got it", "fair"],
            "safe_bridges": ["that is the real issue underneath", "that is where this helps most", "here is the simple version"],
            "safe_closes": ["what is getting stuck the most?", "want me to map it to your case?", "want the next step?"],
        },
    },
}


def default_language_templates() -> dict[str, Any]:
    return {
        code: {
            **payload,
            "voice_profile": dict(payload.get("voice_profile") or {}),
            "tone_matrix": {key: dict(value) for key, value in (payload.get("tone_matrix") or {}).items()},
            "phrase_bank": {key: list(value) for key, value in (payload.get("phrase_bank") or {}).items()},
        }
        for code, payload in DEFAULT_LANGUAGE_TEMPLATES.items()
    }


def _merge_language_templates(templates: dict[str, Any] | None) -> dict[str, Any]:
    merged = default_language_templates()
    for code, payload in (templates or {}).items():
        base = merged.get(code, {})
        if isinstance(base, dict) and isinstance(payload, dict):
            merged[code] = {
                **base,
                **payload,
                "voice_profile": {**base.get("voice_profile", {}), **(payload.get("voice_profile") or {})},
                "tone_matrix": {**base.get("tone_matrix", {}), **(payload.get("tone_matrix") or {})},
                "phrase_bank": {**base.get("phrase_bank", {}), **(payload.get("phrase_bank") or {})},
            }
        else:
            merged[code] = payload
    return merged

def upsert_language_config(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    default_language: str = "es",
    supported_languages: list[str] | None = None,
    detect_contact_language: bool = True,
    templates: dict[str, Any] | None = None,
    fallback_language: str = "en",
    handoff_respect_language: bool = True,
) -> dict:
    supported_languages = list(dict.fromkeys(supported_languages or [default_language, "es", "en"]))
    templates = _merge_language_templates(templates)
    now = utcnow_iso()
    existing = fetch_one(conn, "SELECT * FROM bot_language_configs WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id))
    if existing:
        execute(
            conn,
            """
            UPDATE bot_language_configs
            SET default_language = ?, supported_languages_json = ?, detect_contact_language = ?, templates_json = ?, fallback_language = ?, handoff_respect_language = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                default_language,
                to_json(supported_languages),
                1 if detect_contact_language else 0,
                to_json(templates),
                fallback_language,
                1 if handoff_respect_language else 0,
                now,
                existing["id"],
            ),
        )
        return fetch_one(conn, "SELECT * FROM bot_language_configs WHERE id = ?", (existing["id"],)) or {}
    config_id = new_id("lang")
    execute(
        conn,
        """
        INSERT INTO bot_language_configs (id, organization_id, bot_id, default_language, supported_languages_json, detect_contact_language, templates_json, fallback_language, handoff_respect_language, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            config_id,
            organization_id,
            bot_id,
            default_language,
            to_json(supported_languages),
            1 if detect_contact_language else 0,
            to_json(templates),
            fallback_language,
            1 if handoff_respect_language else 0,
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM bot_language_configs WHERE id = ?", (config_id,)) or {}


def get_language_config(conn, organization_id: str, bot_id: str) -> dict[str, Any]:
    row = fetch_one(conn, "SELECT * FROM bot_language_configs WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id))
    if not row:
        bot = get_bot(conn, bot_id)
        row = upsert_language_config(conn, organization_id=organization_id, bot_id=bot_id, default_language=(bot or {}).get("language") or "es", supported_languages=[(bot or {}).get("language") or "es", "en"])
    templates = _merge_language_templates(from_json(row.get("templates_json"), {}))
    return {
        **row,
        "supported_languages": from_json(row.get("supported_languages_json"), []),
        "templates": templates,
    }


def language_analytics(conn, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = [organization_id]
    bot_clause = ""
    if bot_id:
        bot_clause = " AND bot_id = ?"
        params.append(bot_id)
    lead_rows = fetch_all(conn, f"SELECT language, COUNT(*) AS total FROM crm_leads WHERE organization_id = ?{bot_clause} GROUP BY language ORDER BY total DESC", params)
    voice_rows = fetch_all(conn, f"SELECT detected_language AS language, COUNT(*) AS total FROM voice_notes WHERE organization_id = ?{bot_clause} GROUP BY detected_language ORDER BY total DESC", params)
    flow_rows = fetch_all(conn, f"SELECT language, COUNT(*) AS total FROM whatsapp_flows WHERE organization_id = ?{bot_clause} GROUP BY language ORDER BY total DESC", params)
    counter: Counter[str] = Counter()
    for bucket in (lead_rows, voice_rows, flow_rows):
        for row in bucket:
            counter.update({row.get("language") or "unknown": int(row.get("total") or 0)})
    top = [{"language": language, "total": total} for language, total in counter.most_common(10)]
    return {
        "summary": {
            "detected_languages": len(counter),
            "top_language": top[0]["language"] if top else None,
            "total_language_events": sum(counter.values()),
        },
        "breakdown": {
            "crm": lead_rows,
            "voice": voice_rows,
            "flows": flow_rows,
            "global": top,
        },
    }
