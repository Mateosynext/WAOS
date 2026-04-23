from __future__ import annotations

import re
from typing import Any

from ..contact_intelligence import relationship_snapshot
from ..runtime_settings import ai_optimization_settings
from ..talent_runtime import generate_talent_reply
from .generation_language import (
    _detect_contact_language,
    _detect_customer_tone,
    _looks_like_humor_or_odd_question,
    _looks_overwhelmed,
    _pair_by_language,
    _tone_phrase,
)


def _find_price(bot_config: dict) -> str | None:
    prices = bot_config.get("business_knowledge", {}).get("prices", [])
    if prices:
        first = prices[0]
        if isinstance(first, dict):
            return f"{first.get('name', 'Servicio')}: {first.get('price', '')}".strip(": ")
        return str(first)
    return None


def _find_faq_answer(text: str, bot_config: dict) -> str | None:
    faqs = bot_config.get("business_knowledge", {}).get("faqs", [])
    lower = text.lower()
    for faq in faqs:
        if isinstance(faq, dict):
            q = faq.get("q", "").lower()
            if q and any(term in lower for term in re.findall(r"\w+", q)[:3]):
                return faq.get("a")
    if any(token in lower for token in ["horario", "hours", "open", "opening"]):
        return bot_config.get("business_knowledge", {}).get("hours")
    if any(token in lower for token in ["ubic", "donde", "direcc", "where", "location", "address"]):
        return bot_config.get("business_knowledge", {}).get("location")
    return None


def _instant_knowledge_response(
    text: str,
    classification: dict[str, Any],
    bot_config: dict[str, Any],
    knowledge_hits: list[dict[str, Any]],
    language: str,
) -> dict[str, Any] | None:
    business = dict(bot_config.get("business_knowledge") or {})
    lower = text.lower()
    faq_threshold = float(ai_optimization_settings().get("faq_instant_match_threshold") or 0.92)
    for faq in business.get("faqs") or []:
        if not isinstance(faq, dict):
            continue
        question = str(faq.get("q") or "").strip().lower()
        answer = str(faq.get("a") or "").strip()
        if not question or not answer:
            continue
        q_tokens = {token for token in re.findall(r"\w+", question) if len(token) >= 4}
        t_tokens = {token for token in re.findall(r"\w+", lower) if len(token) >= 4}
        overlap = (len(q_tokens & t_tokens) / max(1, len(q_tokens))) if q_tokens else 0.0
        if question == lower or overlap >= 0.6:
            return {
                "text": answer,
                "source": "instant_knowledge",
                "matched": {"knowledge_type": "faq", "question": faq.get("q"), "score": round(overlap, 2)},
            }
    for hit in knowledge_hits:
        similarity = float(hit.get("similarity") or 0)
        content = str(hit.get("content_text") or "").strip()
        metadata = hit.get("metadata") or {}
        knowledge_type = str(hit.get("knowledge_type") or metadata.get("knowledge_type") or "")
        if knowledge_type == "faq" and similarity >= faq_threshold and content:
            answer = content.split(":", 1)[-1].strip() if ":" in content else content
            return {"text": answer, "source": "instant_knowledge", "matched": hit}
    if classification.get("intent") in {"faq", "greeting", "general"}:
        if any(token in lower for token in ["horario", "hora", "hours", "abren", "cierran", "open", "close"]) and business.get("hours"):
            return {
                "text": _pair_by_language(language, f"Nuestro horario es {business.get('hours')}.", f"Our hours are {business.get('hours')}."),
                "source": "instant_knowledge",
                "matched": {"knowledge_type": "hours"},
            }
        if any(token in lower for token in ["direccion", "ubicacion", "location", "where", "donde", "address"]) and business.get("location"):
            return {
                "text": _pair_by_language(language, f"Estamos en {business.get('location')}.", f"We are located at {business.get('location')}."),
                "source": "instant_knowledge",
                "matched": {"knowledge_type": "location"},
            }
    return None


def _build_general_reframe(
    text: str,
    bot_config: dict,
    business: str,
    language: str,
    tone_context: dict[str, Any] | None = None,
    voice_context: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
) -> str:
    services = bot_config.get("business_knowledge", {}).get("services", [])
    service_hint = services[0] if services else ("this" if language == "en" else "esto")
    lower = text.lower()
    tone_context = tone_context or {}
    voice_context = voice_context or []
    voice_note = voice_context[0] if voice_context else {}
    voice_summary = str(voice_note.get("summary") or "").strip()
    ack = _tone_phrase(language, tone_context, language_config, "ack")
    bridge = _tone_phrase(language, tone_context, language_config, "bridge")
    close_hint = _tone_phrase(language, tone_context, language_config, "close")
    if _looks_overwhelmed(text) or tone_context.get("overwhelmed"):
        base = _pair_by_language(
            language,
            f"{ack}, {bridge}. WAOS te ayuda a responder mejor, dar seguimiento y no dejar conversaciones tiradas.",
            f"{ack}. {bridge}. WAOS helps you reply better, follow up, and keep conversations from getting dropped.",
        )
        close = _pair_by_language(
            language,
            close_hint or "¿Qué te está drenando más ahorita: responder, cotizar, agendar o seguir clientes?",
            close_hint or "What is draining you the most right now: replying, quoting, booking, or following up?",
        )
        return f"{base} {close}".strip()
    if _looks_like_humor_or_odd_question(text):
        opener = _pair_by_language(
            language,
            ack if any(token in lower for token in ["jaja", "jeje"]) else "te sigo",
            ack if any(token in lower for token in ["haha", "lol", "lmao"]) else "I got you",
        )
        body = _pair_by_language(
            language,
            f"{bridge}. Aunque la pregunta venga medio rara, ahí también se ve el problema real del negocio: no conviene que una venta se enfríe por falta de respuesta o seguimiento. WAOS entra justo ahí para contestar con criterio, mover la conversación y ayudarte a vender sin que todo dependa de ti.",
            f"{bridge}. Even when the question comes in a little sideways, it still points to the real business issue: you do not want a sale cooling off because nobody handled the replies or follow-up. That is exactly where WAOS comes in to answer with judgment, move the conversation, and help you sell without everything depending on you.",
        )
        close = _pair_by_language(
            language,
            close_hint or "¿En tu caso dónde se atora más: respuestas, seguimiento o cierre?",
            close_hint or "In your case, where does it get stuck more: replies, follow-up, or closing?",
        )
        return f"{opener}. {body} {close}".strip()
    context_line = ""
    if voice_summary:
        context_line = _pair_by_language(
            language,
            f" También traigo contexto reciente de un audio: {voice_summary}.",
            f" I also have recent context from a voice note: {voice_summary}.",
        )
    base = _pair_by_language(language, f"{ack}. {bridge}. Te ayudo con {business}.", f"{ack}. {bridge}. I can help with {business}.")
    value = _pair_by_language(
        language,
        "WAOS te puede ayudar a responder mejor, ordenar conversaciones y mover gente hacia el siguiente paso.",
        "WAOS can help you reply better, organize conversations, and move people to the next step.",
    )
    close = _pair_by_language(
        language,
        close_hint or f"¿Quieres que te lo aterrice a {service_hint} o al proceso que hoy más se te atora?",
        close_hint or f"Do you want me to map it to {service_hint} or to the part of your process that gets stuck the most today?",
    )
    return f"{base}{context_line} {value} {close}".strip()


def heuristic_generate(
    text: str,
    classification: dict,
    bot_config: dict,
    memory: dict,
    recent_messages: list[dict[str, Any]] | None = None,
    voice_context: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
) -> str:
    talent_reply = generate_talent_reply(text, classification, bot_config, memory)
    if talent_reply:
        return talent_reply
    identity = bot_config.get("identity", {})
    business = identity.get("business_name", "the business")
    services = bot_config.get("business_knowledge", {}).get("services", [])
    hours = bot_config.get("business_knowledge", {}).get("hours", "")
    location = bot_config.get("business_knowledge", {}).get("location", "")
    promotions = bot_config.get("business_knowledge", {}).get("promotions", [])
    promo = promotions[0] if promotions else ""
    language = _detect_contact_language(text, recent_messages, bot_config, voice_context, language_config)
    tone_context = _detect_customer_tone(text, recent_messages, voice_context)

    intent = classification.get("intent")
    profile = relationship_snapshot(memory)
    known_contact = bool(profile.get("known_contact"))
    relation_label = str(profile.get("relation_label") or "")
    urgency_level = str(classification.get("urgency_level") or profile.get("urgency_level") or "normal").lower()
    if intent == "greeting":
        services_text = ", ".join(services[:3]) if services else _pair_by_language(language, "nuestros servicios", "our services")
        ack = _tone_phrase(language, tone_context, language_config, "ack")
        bridge = _tone_phrase(language, tone_context, language_config, "bridge")
        if known_contact and relation_label in {"familia", "conocido"}:
            return _pair_by_language(
                language,
                f"{ack}. Qué gusto leerte. Ya te ubico como {relation_label} y te ayudo rápido. ¿Qué necesitas hoy?",
                f"{ack}. Good to hear from you again. I already recognize you, and I can help quickly. What do you need today?",
            )
        return _pair_by_language(
            language,
            f"{ack}. Soy {identity.get('bot_name', 'tu asistente')} de {business}. Te ayudo con {services_text} y {bridge}. ¿Qué te gustaría resolver hoy?",
            f"{ack}. I'm {identity.get('bot_name', 'your assistant')} from {business}. I can help with {services_text}, and {bridge}. What would you like to solve today?",
        )
    if intent == "pricing":
        price = _find_price(bot_config)
        if price:
            return _pair_by_language(
                language,
                f"Claro. Tengo este dato disponible: {price}. Si te ayuda, tambien puedo revisar disponibilidad para agendar.{(' Además, ' + str(promo)) if promo and language == 'es' else ''}",
                f"Sure. I have this available right now: {price}. If it helps, I can also check availability and get the next step moving.{(' Also, ' + str(promo)) if promo and language == 'en' else ''}",
            )
        return _pair_by_language(
            language,
            "Con gusto te ayudo con precios. En este momento no tengo una tarifa exacta configurada para compartirte por este chat, pero puedo ayudarte a avanzar o pasarte con un asesor.",
            "Happy to help with pricing. I do not have an exact rate configured to share in this chat right now, but I can still help you move forward or hand you off to an advisor.",
        )
    if intent == "schedule":
        hours_text = _pair_by_language(language, f" Nuestro horario es {hours}." if hours else "", f" Our hours are {hours}." if hours else "")
        return _pair_by_language(
            language,
            f"Perfecto, te ayudo a agendar.{hours_text} ¿Que dia u horario te funciona mejor?",
            f"Perfect, I can help you book it.{hours_text} What day or time works best for you?",
        )
    if intent == "faq":
        answer = _find_faq_answer(text, bot_config)
        if answer:
            close = _pair_by_language(language, "¿Quieres que te ayude con algo más?", "Want help with anything else?")
            return f"{answer} {close}".strip()
    if classification.get("requested_human"):
        return _pair_by_language(
            language,
            "Claro, te paso con un asesor humano para que lo vean contigo.",
            "Of course, I can hand you off to a human advisor so they can review it with you.",
        )
    if classification.get("objection") == "price":
        return _pair_by_language(
            language,
            "Si, el precio pesa. Si quieres, te ayudo a ver la opcion que mejor te cuadre o revisar si aplica alguna promocion.",
            "Yes, price matters. If you want, I can help you find the option that fits best or check whether any promotion applies.",
        )
    if urgency_level in {"high", "critical"} and known_contact and relation_label in {"familia", "conocido"}:
        return _pair_by_language(
            language,
            "Ya lo vi y te doy prioridad. Cuéntame en una línea qué necesitas para moverlo rápido.",
            "I saw it and I am prioritizing it. Tell me in one line what you need so I can move it fast.",
        )
    if location:
        return _pair_by_language(
            language,
            f"Con gusto te ayudo con {business}. Estamos en {location}. Y si la duda viene medio rara tambien te la aterrizo. ¿Buscas precio, horario, agendar o seguimiento?",
            f"Happy to help with {business}. We are located at {location}. And if the question comes in sideways, I can still ground it for you. Are you looking for pricing, hours, booking, or follow-up?",
        )
    return _build_general_reframe(text, bot_config, business, language, tone_context, voice_context, language_config)
