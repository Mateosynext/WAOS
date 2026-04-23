from __future__ import annotations

from typing import Any

from ..domains.language import default_language_templates


def _pair_by_language(language: str, es: str, en: str) -> str:
    return en if language == "en" else es


def _supported_languages(bot_config: dict, language_config: dict[str, Any] | None = None) -> list[str]:
    multilingual = (bot_config.get("v7_modules", {}) or {}).get("multilingual", {}) or {}
    configured = multilingual.get("supported_languages") or []
    if language_config:
        configured = list(configured) + list(language_config.get("supported_languages") or [])
    configured = [str(item).lower() for item in configured if item]
    if not configured:
        configured = [str(bot_config.get("identity", {}).get("language") or "es").lower(), "en"]
    unique: list[str] = []
    for item in configured + ["es", "en"]:
        if item not in unique:
            unique.append(item)
    return unique


def _looks_overwhelmed(text: str) -> bool:
    lower = text.lower()
    stress_markers = [
        "ahogado",
        "hasta el cuello",
        "harto",
        "caos",
        "prendido fuego",
        "incendio",
        "me quiero ir al monte",
        "satur",
        "cansado",
        "quema",
        "no doy abasto",
        "overwhelmed",
        "burned out",
        "too much",
        "drowning",
        "swamped",
        "chaos",
    ]
    return any(marker in lower for marker in stress_markers)


def _detect_contact_language(
    text: str,
    recent_messages: list[dict[str, Any]] | None = None,
    bot_config: dict | None = None,
    voice_context: list[dict[str, Any]] | None = None,
    language_config: dict[str, Any] | None = None,
) -> str:
    supported = _supported_languages(bot_config or {}, language_config)
    samples = [text.lower()]
    for message in recent_messages or []:
        body = str(message.get("body") or "").strip().lower()
        if body:
            samples.append(body)
    for note in voice_context or []:
        detected = str(note.get("detected_language") or "").lower().strip()
        if detected in supported:
            return detected
        transcript = str(note.get("transcript") or note.get("summary") or "").lower().strip()
        if transcript:
            samples.append(transcript)
    combined = " ".join(samples)
    english_markers = ["hello", "hi", "hey", "price", "pricing", "book", "booking", "hours", "where", "location", "need", "help", "can you", "please", "follow up"]
    spanish_markers = ["hola", "precio", "cotizacion", "agendar", "horario", "donde", "necesito", "ayuda", "puedes", "por favor", "seguimiento"]
    english_score = sum(1 for marker in english_markers if marker in combined)
    spanish_score = sum(1 for marker in spanish_markers if marker in combined)
    if english_score > spanish_score and "en" in supported:
        return "en"
    if spanish_score >= english_score and "es" in supported:
        return "es"
    default_language = str((language_config or {}).get("default_language") or (bot_config or {}).get("identity", {}).get("language") or "es").lower()
    return default_language if default_language in supported else supported[0]


def _detect_customer_tone(
    text: str,
    recent_messages: list[dict[str, Any]] | None = None,
    voice_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    combined_parts = [text.lower()]
    for message in recent_messages or []:
        body = str(message.get("body") or "").lower().strip()
        if body:
            combined_parts.append(body)
    combined = " ".join(combined_parts)
    formal = any(token in combined for token in ["buen día", "buen dia", "buenas tardes", "por favor", "could you", "please", "good morning"])
    humorous = any(token in combined for token in ["jaja", "jajaja", "jeje", "haha", "lol", "lmao", "trastes", "arregla la vida"])
    overwhelmed = _looks_overwhelmed(combined)
    direct = len(text.split()) <= 5 or any(token in combined for token in ["price", "precio", "book", "agenda", "quote", "cotiza"])
    voice_emotions = [str(note.get("emotion") or "").lower() for note in (voice_context or [])]
    voice_urgency = [str(note.get("urgency_level") or "").lower() for note in (voice_context or [])]
    emotion = "neutral"
    if "negativa" in voice_emotions or "negative" in voice_emotions:
        emotion = "negative"
    elif "positiva" in voice_emotions or "positive" in voice_emotions:
        emotion = "positive"
    if overwhelmed:
        emotion = "negative"
    return {
        "style": "formal" if formal and not humorous else "casual",
        "humor_open": humorous,
        "overwhelmed": overwhelmed,
        "direct": direct,
        "emotion": emotion,
        "urgency": "high" if any(item in {"alta", "high"} for item in voice_urgency) else "normal",
    }


def _language_voice_layer(language: str, language_config: dict[str, Any] | None = None) -> dict[str, Any]:
    templates = (language_config or {}).get("templates") or default_language_templates()
    default_language = str((language_config or {}).get("default_language") or "es").lower()
    selected = templates.get(language) or templates.get(default_language) or templates.get("es") or {}
    return {
        "language": language,
        "welcome": selected.get("welcome"),
        "human_handoff": selected.get("human_handoff"),
        "voice_profile": selected.get("voice_profile", {}),
        "tone_matrix": selected.get("tone_matrix", {}),
        "phrase_bank": selected.get("phrase_bank", {}),
    }


def _tone_mode(tone_context: dict[str, Any] | None = None) -> str:
    tone_context = tone_context or {}
    if tone_context.get("overwhelmed"):
        return "overwhelmed"
    if tone_context.get("humor_open"):
        return "playful"
    if tone_context.get("style") == "formal":
        return "formal"
    if tone_context.get("direct"):
        return "direct"
    return "casual"


def _tone_phrase(language: str, tone_context: dict[str, Any] | None, language_config: dict[str, Any] | None, slot: str) -> str:
    layer = _language_voice_layer(language, language_config)
    matrix = layer.get("tone_matrix", {})
    mode = _tone_mode(tone_context)
    selected = matrix.get(mode) or matrix.get("casual") or {}
    value = str(selected.get(slot) or "").strip()
    if value:
        return value
    fallback = {
        "ack": _pair_by_language(language, "te sigo", "I got you"),
        "bridge": _pair_by_language(language, "te lo aterrizo fácil", "here is the simple version"),
        "close": _pair_by_language(language, "¿quieres que lo vea en tu caso?", "want me to make it specific to your case?"),
    }
    return fallback.get(slot, "")


def _looks_like_humor_or_odd_question(text: str) -> bool:
    lower = text.lower()
    humor_markers = [
        "jaja",
        "jajaja",
        "jeje",
        "haha",
        "lol",
        "trastes",
        "arregla la vida",
        "fix my life",
        "3 am",
        "guaderia",
        "guarderia",
        "clon",
        "clone",
        "monte",
        "soñe",
        "sone",
        "o que",
        "or what",
    ]
    return any(marker in lower for marker in humor_markers) or text.strip().endswith("?")
