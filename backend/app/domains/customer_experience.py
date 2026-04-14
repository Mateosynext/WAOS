from __future__ import annotations

from collections import Counter
from typing import Any

from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..repositories import create_audit_log, create_message, get_bot, get_contact, get_contact_memory, get_conversation, upsert_memory
from ..utils import add_minutes, new_id, parse_iso, to_json, from_json, utcnow_iso

BUY_KEYWORDS = [
    "quiero", "me interesa", "cotizacion", "cotización", "precio", "agendar", "comprar", "pagar", "hoy", "listo",
]


PRICE_OBJECTIONS = ["caro", "precio", "descuento", "más barato", "mas barato"]


TIMING_OBJECTIONS = ["luego", "después", "despues", "más tarde", "mas tarde", "no ahora"]


TRUST_OBJECTIONS = ["seguro", "confianza", "garantía", "garantia", "reseñas", "resenas"]


URGENT_WORDS = ["urgente", "urge", "hoy", "ya", "ahora"]


NEGATIVE_WORDS = ["molesto", "enojado", "frustrado", "mal", "pésimo", "pesimo"]


POSITIVE_WORDS = ["gracias", "excelente", "perfecto", "bien", "me encanta"]


def _json(row: dict | None, key: str, default: Any):
    if not row:
        return default
    return from_json(row.get(key), default)


def _keyword_hits(text: str, words: list[str]) -> int:
    lower = (text or "").lower()
    return sum(1 for word in words if word in lower)


def _detect_objections(text: str) -> list[str]:
    lower = (text or "").lower()
    objections: list[str] = []
    if any(word in lower for word in PRICE_OBJECTIONS):
        objections.append("precio")
    if any(word in lower for word in TIMING_OBJECTIONS):
        objections.append("timing")
    if any(word in lower for word in TRUST_OBJECTIONS):
        objections.append("confianza")
    return objections


def _conversation_messages(conn, conversation_id: str) -> list[dict]:
    return fetch_all(conn, "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))


def _ensure_crm_lead(conn, *, organization_id: str, bot_id: str, contact_id: str, conversation_id: str | None = None, defaults: dict[str, Any] | None = None) -> dict:
    existing = fetch_one(conn, "SELECT * FROM crm_leads WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY created_at DESC LIMIT 1", (organization_id, bot_id, contact_id))
    if existing:
        return existing
    defaults = defaults or {}
    lead_id = new_id("lead")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO crm_leads (
            id, organization_id, bot_id, conversation_id, contact_id, stage, estimated_amount, owner_user_id,
            next_action, followup_at, tags_json, notes, lost_reason, pipeline_json,
            score_buying_intent, close_probability, detected_objections_json, best_next_action,
            temperature_status, language, source_channel, source_campaign, last_qualification_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            defaults.get("stage", "nuevo"),
            float(defaults.get("estimated_amount") or 0),
            defaults.get("owner_user_id"),
            defaults.get("next_action", "Calificar lead"),
            defaults.get("followup_at"),
            to_json(defaults.get("tags") or []),
            defaults.get("notes", ""),
            defaults.get("lost_reason"),
            to_json(defaults.get("pipeline") or {"stage_history": [{"stage": defaults.get("stage", "nuevo"), "at": now}]}),
            int(defaults.get("score_buying_intent") or 0),
            int(defaults.get("close_probability") or 0),
            to_json(defaults.get("detected_objections") or []),
            defaults.get("best_next_action", "Enviar propuesta"),
            defaults.get("temperature_status", "templado"),
            defaults.get("language", "es"),
            defaults.get("source_channel", "whatsapp"),
            defaults.get("source_campaign", "orgánico"),
            now,
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM crm_leads WHERE id = ?", (lead_id,))


def seller_mode_summary(conn, conversation_id: str) -> dict[str, Any]:
    conversation = get_conversation(conn, conversation_id)
    if not conversation:
        raise ValueError("conversation_not_found")
    bot = get_bot(conn, conversation["bot_id"])
    contact = get_contact(conn, conversation["contact_id"])
    memory = get_contact_memory(conn, conversation["contact_id"], conversation["bot_id"]) or {}
    messages = _conversation_messages(conn, conversation_id)
    inbound_texts = [m["body"] for m in messages if m.get("direction") == "inbound"]
    joined = " \n".join(inbound_texts)
    keyword_score = min(100, 20 + _keyword_hits(joined, BUY_KEYWORDS) * 10 + int(memory.get("lead_score") or 0) // 2)
    objections = _detect_objections(joined)
    if not objections and memory.get("objections"):
        objections = [item.strip() for item in str(memory.get("objections") or "").split(",") if item.strip()]
    close_probability = min(97, max(5, keyword_score - (len(objections) * 8)))
    if close_probability >= 75:
        temperature = "caliente"
    elif close_probability >= 45:
        temperature = "templado"
    else:
        temperature = "frío"
    last_inbound = next((m for m in reversed(messages) if m.get("direction") == "inbound"), None)
    cooling_alert = False
    if last_inbound and parse_iso(last_inbound.get("created_at")):
        age_hours = (parse_iso(utcnow_iso()) - parse_iso(last_inbound.get("created_at"))).total_seconds() / 3600
        cooling_alert = age_hours >= 24 and close_probability >= 40
    next_action = "Enviar link de pago" if close_probability >= 80 else "Enviar cotización guiada" if keyword_score >= 55 else "Hacer follow-up con incentivo"
    objection_responses = {
        "precio": "Refuerza valor, ofrece promoción limitada y propone opción de entrada.",
        "timing": "Ofrece reservar hoy con recordatorio automático o fecha tentativa.",
        "confianza": "Envía prueba social, garantías y caso de éxito corto.",
    }
    summary = {
        "conversation_id": conversation_id,
        "contact": {"id": contact.get("id"), "name": contact.get("name"), "phone": contact.get("phone")},
        "lead_stage": memory.get("lead_stage") or "nuevo",
        "score_buying_intent": keyword_score,
        "close_probability": close_probability,
        "best_next_action": next_action,
        "temperature_status": temperature,
        "cooling_alert": cooling_alert,
        "detected_objections": objections,
        "suggested_responses": [{"objection": o, "suggestion": objection_responses.get(o, "Responder con claridad y CTA.")} for o in objections],
        "human_summary": f"{contact.get('name') or 'Lead'} con intención {temperature}, probabilidad de cierre {close_probability}%, siguiente paso: {next_action}.",
    }
    lead = _ensure_crm_lead(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=conversation["bot_id"],
        contact_id=conversation["contact_id"],
        conversation_id=conversation_id,
        defaults={
            "stage": memory.get("lead_stage") or "calificado",
            "score_buying_intent": keyword_score,
            "close_probability": close_probability,
            "detected_objections": objections,
            "best_next_action": next_action,
            "temperature_status": temperature,
        },
    )
    execute(
        conn,
        """
        UPDATE crm_leads
        SET conversation_id = ?, score_buying_intent = ?, close_probability = ?, detected_objections_json = ?, best_next_action = ?, temperature_status = ?, last_qualification_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (conversation_id, keyword_score, close_probability, to_json(objections), next_action, temperature, utcnow_iso(), utcnow_iso(), lead["id"]),
    )
    summary["crm_lead_id"] = lead["id"]
    return summary


def review_conversation(conn, *, organization_id: str, bot_id: str, conversation_id: str, agent_user_id: str | None = None, review_type: str = "commercial_quality") -> dict:
    messages = _conversation_messages(conn, conversation_id)
    response_deltas: list[float] = []
    for idx, item in enumerate(messages):
        if item.get("direction") != "inbound":
            continue
        for nxt in messages[idx + 1 :]:
            if nxt.get("direction") == "outbound":
                a = parse_iso(item.get("created_at"))
                b = parse_iso(nxt.get("created_at"))
                if a and b:
                    response_deltas.append((b - a).total_seconds())
                break
    avg_delay = int(sum(response_deltas) / len(response_deltas)) if response_deltas else 0
    joined = " ".join(item.get("body") or "" for item in messages)
    tone = "frío" if any(word in joined.lower() for word in NEGATIVE_WORDS) else "correcto"
    missed = []
    if "precio" in joined.lower() and "link de pago" not in joined.lower():
        missed.append("No se empujó cierre con link de pago")
    if "cita" in joined.lower() and "confirm" not in joined.lower():
        missed.append("Faltó confirmación de asistencia")
    quality = 92
    if avg_delay > 900:
        quality -= 18
    if tone == "frío":
        quality -= 12
    quality -= min(15, len(missed) * 5)
    review_id = new_id("qrev")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO conversation_reviews (id, organization_id, bot_id, conversation_id, agent_user_id, review_type, quality_score, response_delay_seconds, tone, missed_opportunities_json, checklist_json, recommendations_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            review_id,
            organization_id,
            bot_id,
            conversation_id,
            agent_user_id,
            review_type,
            max(0, quality),
            avg_delay,
            tone,
            to_json(missed),
            to_json([
                {"item": "Tiempo de respuesta", "ok": avg_delay <= 900},
                {"item": "Tono comercial", "ok": tone != "frío"},
                {"item": "Siguiente paso claro", "ok": len(missed) == 0},
            ]),
            to_json([
                "Responder en menos de 15 minutos cuando el lead esté caliente.",
                "Siempre cerrar con CTA concreto: pagar, agendar o hablar con asesor.",
            ]),
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM conversation_reviews WHERE id = ?", (review_id,))


def generate_reactivation_recommendations(conn, organization_id: str, bot_id: str | None = None) -> list[dict]:
    where = "WHERE organization_id = ?"
    params: list[Any] = [organization_id]
    if bot_id:
        where += " AND bot_id = ?"
        params.append(bot_id)
    leads = fetch_all(conn, f"SELECT * FROM crm_leads {where} ORDER BY updated_at DESC LIMIT 50", params)
    results: list[dict] = []
    now = utcnow_iso()
    for lead in leads:
        status = "draft"
        segment = None
        message = None
        incentive = None
        if lead.get("stage") == "pago_pendiente":
            segment = "clientes_que_preguntaron_precio_pero_nunca_pagaron"
            message = "Hola, te dejo nuevamente el link para completar tu pago. ¿Te ayudo a cerrarlo hoy?"
            incentive = "Recordatorio de disponibilidad"
        elif lead.get("stage") in {"cotizado", "propuesta"}:
            segment = "cotizaciones_enviadas_no_cerradas"
            message = "Quería retomar tu cotización. Tengo una opción para ayudarte a avanzar esta semana."
            incentive = "Bono de cierre"
        elif lead.get("temperature_status") == "caliente":
            segment = "leads_calientes_sin_respuesta"
            message = "Veo que sigues con interés. ¿Quieres que lo dejemos cerrado hoy mismo?"
            incentive = "Prioridad en atención"
        if not segment:
            continue
        existing = fetch_one(conn, "SELECT * FROM reactivation_recommendations WHERE crm_lead_id = ? AND segment = ?", (lead["id"], segment))
        if existing:
            results.append(existing)
            continue
        reco_id = new_id("reco")
        execute(
            conn,
            "INSERT INTO reactivation_recommendations (id, organization_id, bot_id, contact_id, crm_lead_id, segment, priority, suggested_channel, suggested_message, suggested_incentive, suggested_send_at, rationale, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'whatsapp', ?, ?, ?, ?, ?, ?, ?)",
            (
                reco_id,
                lead["organization_id"],
                lead["bot_id"],
                lead["contact_id"],
                lead["id"],
                segment,
                90 if lead.get("temperature_status") == "caliente" else 70,
                message,
                incentive,
                add_minutes(now, 30),
                f"Lead en etapa {lead.get('stage')} con probabilidad {lead.get('close_probability')}%.",
                status,
                now,
                now,
            ),
        )
        results.append(fetch_one(conn, "SELECT * FROM reactivation_recommendations WHERE id = ?", (reco_id,)))
    return results


def ingest_voice_note(conn, *, organization_id: str, bot_id: str, conversation_id: str, contact_id: str, transcript: str, language: str = "es") -> dict:
    note_id = new_id("voice")
    lower = transcript.lower()
    intent = "general"
    if any(word in lower for word in ["precio", "cotización", "cotizacion"]):
        intent = "pricing"
    elif any(word in lower for word in ["cita", "agenda", "agendar"]):
        intent = "schedule"
    urgency = "alta" if any(word in lower for word in URGENT_WORDS) else "media"
    emotion = "negativa" if any(word in lower for word in NEGATIVE_WORDS) else "positiva" if any(word in lower for word in POSITIVE_WORDS) else "neutral"
    summary = transcript[:160] + ("..." if len(transcript) > 160 else "")
    response_text = "Gracias por tu audio. Ya tomé tu solicitud y te ayudo a avanzar por aquí."
    execute(
        conn,
        "INSERT INTO voice_notes (id, organization_id, bot_id, conversation_id, contact_id, message_id, transcript, detected_language, intent, urgency_level, emotion, suggested_response_text, suggested_response_audio_text, summary, created_at) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (note_id, organization_id, bot_id, conversation_id, contact_id, transcript, language, intent, urgency, emotion, response_text, response_text, summary, utcnow_iso()),
    )
    return fetch_one(conn, "SELECT * FROM voice_notes WHERE id = ?", (note_id,))


def record_feedback(conn, *, organization_id: str, bot_id: str, conversation_id: str | None, contact_id: str | None, score_type: str, score_value: int, reason: str = "", agent_user_id: str | None = None) -> dict:
    feedback_id = new_id("fb")
    detractor = 1 if score_value <= 2 else 0
    recovery = "queued" if detractor else "not_needed"
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO customer_feedback (id, organization_id, bot_id, conversation_id, contact_id, score_type, score_value, reason, detractor_alert, recovery_status, agent_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (feedback_id, organization_id, bot_id, conversation_id, contact_id, score_type, score_value, reason, detractor, recovery, agent_user_id, now),
    )
    if detractor and contact_id:
        execute(
            conn,
            "INSERT INTO service_requests (id, organization_id, bot_id, contact_id, request_type, status, payload_json, response_json, created_at, updated_at) VALUES (?, ?, ?, ?, 'recovery_case', 'open', ?, '{}', ?, ?)",
            (new_id("srv"), organization_id, bot_id, contact_id, to_json({"conversation_id": conversation_id, "reason": reason, "score": score_value}), now, now),
        )
    return fetch_one(conn, "SELECT * FROM customer_feedback WHERE id = ?", (feedback_id,))


def create_service_request(conn, *, organization_id: str, bot_id: str, contact_id: str, request_type: str, payload: dict[str, Any]) -> dict:
    request_id = new_id("srv")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO service_requests (id, organization_id, bot_id, contact_id, request_type, status, payload_json, response_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'open', ?, '{}', ?, ?)",
        (request_id, organization_id, bot_id, contact_id, request_type, to_json(payload), now, now),
    )
    return fetch_one(conn, "SELECT * FROM service_requests WHERE id = ?", (request_id,))


def fetch_one(conn, sql: str, params=()):
    row = conn.execute(sql, tuple(params)).fetchone()
    return dict(row) if row else None


def fetch_all(conn, sql: str, params=()):
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def execute(conn, sql: str, params=()):
    conn.execute(sql, tuple(params))
    conn.commit()


def _parse_row(row: dict, mapping: dict[str, Any]) -> dict:
    parsed = dict(row)
    for key, default in mapping.items():
        clean_key = key[:-5] if key.endswith("_json") else key
        parsed[clean_key] = from_json(parsed.get(key), default)
    return parsed


def _parse_product(conn, row: dict) -> dict:
    product = _parse_row(
        row,
        {
            "tags_json": [],
            "specs_json": {},
            "benefits_json": [],
            "faq_json": [],
            "related_products_json": [],
            "availability_json": {},
        },
    )
    variants = fetch_all(conn, "SELECT * FROM catalog_product_variants WHERE product_id = ? ORDER BY created_at ASC", (row["id"],))
    product["variants"] = [_parse_row(v, {"attributes_json": {}}) for v in variants]
    assets = fetch_all(
        conn,
        """
        SELECT a.*, pa.asset_role, pa.variant_id, pa.sort_order AS link_sort_order
        FROM catalog_product_assets pa
        JOIN media_assets a ON a.id = pa.media_asset_id
        WHERE pa.product_id = ?
        ORDER BY pa.sort_order ASC, a.created_at ASC
        """,
        (row["id"],),
    )
    product["assets"] = [_parse_row(a, {"metadata_json": {}}) for a in assets]
    product["inventory"] = fetch_all(conn, "SELECT * FROM catalog_inventory WHERE product_id = ? ORDER BY updated_at DESC", (row["id"],))
    return product


def _parse_service(row: dict) -> dict:
    return _parse_row(row, {"availability_json": {}, "photos_json": []})


def _parse_media(row: dict) -> dict:
    return _parse_row(row, {"metadata_json": {}})


def _parse_promotion(row: dict) -> dict:
    return _parse_row(row, {"applies_to_json": {}, "channels_json": []})


def _parse_rule(row: dict) -> dict:
    return _parse_row(row, {"conditions_json": {}, "action_json": {}})


def _parse_template(row: dict) -> dict:
    return _parse_row(row, {"variables_json": []})


def _parse_behavior(row: dict) -> dict:
    return _parse_row(
        row,
        {
            "escalate_when_json": [],
            "active_hours_json": [],
            "active_channels_json": [],
            "forbidden_topics_json": [],
            "required_phrases_json": [],
        },
    )


def _guess_intent(query: str) -> str:
    text = query.lower()
    if any(word in text for word in ["promo", "descuento", "oferta", "2x1", "bundle"]):
        return "promotion"
    if any(word in text for word in ["agendar", "cita", "servicio", "consulta", "valoracion"]):
        return "service"
    return "product"


def _haystack_product(product: dict) -> str:
    parts = [str(product.get("name") or ""), str(product.get("sku") or ""), " ".join(product.get("tags", []))]
    specs = product.get("specs", {})
    if isinstance(specs, dict):
        parts.extend([f"{k} {v}" for k, v in specs.items()])
    parts.extend([v.get("name", "") for v in product.get("variants", [])])
    return " ".join(parts).lower()


def _match_product(conn, organization_id: str, bot_id: str | None, query: str) -> dict | None:
    candidates = list_catalog_products(conn, organization_id, bot_id)
    tokens = [token for token in query.lower().split() if len(token) > 2]
    for product in candidates:
        haystack = _haystack_product(product)
        if any(token in haystack for token in tokens):
            return product
    return candidates[0] if candidates else None


def _match_service(conn, organization_id: str, bot_id: str | None, query: str) -> dict | None:
    services = list_catalog_services(conn, organization_id, bot_id)
    tokens = [token for token in query.lower().split() if len(token) > 2]
    for service in services:
        haystack = " ".join([str(service.get("name") or ""), str(service.get("preparation") or ""), str(service.get("restrictions") or "")]).lower()
        if any(token in haystack for token in tokens):
            return service
    return services[0] if services else None


def _match_promotion(conn, organization_id: str, bot_id: str | None, query: str) -> dict | None:
    promos = list_catalog_promotions(conn, organization_id, bot_id)
    tokens = [token for token in query.lower().split() if len(token) > 2]
    for promo in promos:
        haystack = " ".join([str(promo.get("name") or ""), str(promo.get("message_short") or ""), str(promo.get("message_long") or "")]).lower()
        if any(token in haystack for token in tokens):
            return promo
    active = [item for item in promos if item.get("status") == "active"]
    return active[0] if active else (promos[0] if promos else None)


def customer_experience_preview(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    query: str,
    conversation_id: str | None = None,
    contact_id: str | None = None,
    source_channel: str = "whatsapp",
) -> dict:
    intent = _guess_intent(query)
    behavior = get_bot_behavior_settings(conn, organization_id, bot_id) if bot_id else {}
    if intent == "promotion":
        promo = _match_promotion(conn, organization_id, bot_id, query)
        if not promo:
            return {"intent": intent, "entity": None, "blocks": [{"type": "text", "text": "No encontre una promocion exacta. Puedo compartirte opciones vigentes o pasarte con un asesor."}]}
        banner = None
        if promo.get("banner_asset_id"):
            banner_row = fetch_one(conn, "SELECT * FROM media_assets WHERE id = ?", (promo["banner_asset_id"],))
            banner = _parse_media(banner_row) if banner_row else None
        blocks = []
        if banner:
            blocks.append({"type": "image", "url": banner.get("file_url"), "label": banner.get("label") or banner.get("file_name")})
        blocks.append({"type": "text", "text": promo.get("message_short") or promo.get("name")})
        blocks.append({"type": "promo", "name": promo.get("name"), "legal_terms": promo.get("legal_terms"), "validity": {"starts_at": promo.get("starts_at"), "ends_at": promo.get("ends_at")}})
        if promo.get("cta_label") or promo.get("cta_url"):
            blocks.append({"type": "cta", "label": promo.get("cta_label") or "Ver promo", "url": promo.get("cta_url")})
        entity = promo
        entity_type = "promotion"
    elif intent == "service":
        service = _match_service(conn, organization_id, bot_id, query)
        if not service:
            return {"intent": intent, "entity": None, "blocks": [{"type": "text", "text": "No encontre un servicio exacto. Puedo ayudarte a agendar o sugerirte el mas cercano."}]}
        blocks = []
        for photo in service.get("photos", [])[:1]:
            blocks.append({"type": "image", "url": photo, "label": service.get("name")})
        blocks.append({"type": "text", "text": f"{service.get('name')}: {service.get('preparation') or 'Servicio disponible para agendar.'}"})
        blocks.append({"type": "service_card", "price": service.get("price"), "currency": service.get("currency"), "duration_minutes": service.get("duration_minutes"), "branch": service.get("branch"), "availability": service.get("availability")})
        blocks.append({"type": "cta", "label": "Agendar cita", "action": "book_service"})
        entity = service
        entity_type = "service"
    else:
        product = _match_product(conn, organization_id, bot_id, query)
        if not product:
            return {"intent": intent, "entity": None, "blocks": [{"type": "text", "text": "No encontre un producto exacto. Dime marca, modelo o categoria y te sugiero opciones."}]}
        primary_asset = product.get("assets", [{}])[0] if product.get("assets") else None
        visible_inventory = [item for item in product.get("inventory", []) if int(item.get("visible_to_bot", 1)) == 1]
        stock_status = visible_inventory[0]["status"] if visible_inventory else "sin_dato"
        blocks = []
        if primary_asset and (behavior.get("auto_send_images", True) or "foto" in query.lower() or "imagen" in query.lower()):
            blocks.append({"type": "image", "url": primary_asset.get("file_url"), "label": primary_asset.get("label") or product.get("name")})
        specs = product.get("specs", {}) if isinstance(product.get("specs", {}), dict) else {}
        top_specs = dict(list(specs.items())[:5])
        blocks.append({"type": "text", "text": product.get("short_description") or product.get("name")})
        blocks.append({"type": "product_card", "name": product.get("name"), "price": product.get("price"), "promotional_price": product.get("promotional_price"), "currency": product.get("currency"), "stock_status": stock_status, "delivery_eta": product.get("delivery_eta")})
        if top_specs:
            blocks.append({"type": "specs", "items": top_specs})
        if product.get("variants"):
            blocks.append({"type": "variants", "items": [v.get("name") for v in product.get("variants", [])[:5]]})
        blocks.append({"type": "cta", "label": "Quiero apartarlo", "url": product.get("checkout_url") or "", "action": "checkout"})
        entity = product
        entity_type = "product"
    execute(
        conn,
        "INSERT INTO product_question_logs (id, organization_id, bot_id, conversation_id, contact_id, entity_type, entity_id, intent, requested_variant, source_channel, converted, unanswered, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)",
        (new_id("qlog"), organization_id, bot_id, conversation_id, contact_id, entity_type, entity.get("id") if entity else None, intent, None, source_channel, utcnow_iso()),
    )
    return {
        "intent": intent,
        "behavior": behavior,
        "entity_type": entity_type,
        "entity": entity,
        "blocks": blocks,
        "suggested_follow_up": "¿Quieres mas fotos, disponibilidad o te ayudo a comprar/agendar?",
    }
