from __future__ import annotations

from typing import Any

from .utils import from_json, utcnow_iso

RELATIONSHIP_KEYWORDS = {
    "family": [
        "mamá", "mama", "papá", "papa", "hermana", "hermano", "prima", "primo", "tía", "tia", "tio", "tío",
        "sobrina", "sobrino", "esposa", "esposo", "novia", "novio", "familia", "hija", "hijo",
        "mom", "dad", "brother", "sister", "cousin", "wife", "husband", "family",
    ],
    "personal": [
        "amigo", "amiga", "conocido", "conocida", "compa", "bro", "carnal", "veci", "vecino", "vecina",
        "favor", "personal", "me ayudas", "te encargo", "te marco", "nos vimos", "te conozco",
        "friend", "buddy", "pal", "personal favor",
    ],
    "provider": [
        "proveedor", "factura", "facturacion", "inventario", "entrega", "recoleccion", "cotizacion de mayoreo",
        "insumo", "pedido interno", "orden de compra", "supplier", "invoice", "stock", "warehouse", "logistica",
    ],
    "team": [
        "equipo", "interno", "colaborador", "empleado", "soy de ventas", "soy del equipo", "staff",
        "manager", "gerencia", "operaciones", "soporte interno",
    ],
    "customer": [
        "precio", "cotizacion", "cotizar", "servicio", "producto", "comprar", "agenda", "cita", "pedido",
        "seguimiento", "promocion", "cliente", "quiero", "me interesa", "quote", "buy", "book", "pricing",
        "order", "service", "product", "appointment",
    ],
}

TOPIC_KEYWORDS = {
    "pricing": ["precio", "cotizacion", "cotizar", "price", "pricing", "quote", "cost"],
    "schedule": ["agenda", "agendar", "cita", "reservar", "schedule", "book", "appointment"],
    "support": ["ayuda", "soporte", "problema", "falla", "error", "support", "issue", "bug"],
    "payment": ["pago", "transferencia", "factura", "deposito", "payment", "invoice"],
    "personal": ["favor", "personal", "familia", "amigo", "friend", "family"],
    "operations": ["entrega", "inventario", "proveedor", "logistica", "delivery", "supplier", "stock"],
}

URGENCY_KEYWORDS = {
    "critical": ["emergencia", "emergency", "ahora mismo", "ya mismo", "911", "hospital", "accidente", "me urge demasiado"],
    "high": ["urge", "urgente", "ya", "asap", "hoy", "en corto", "lo antes posible", "rapidito", "cuanto antes"],
    "medium": ["cuando puedas", "pendiente", "seguimiento", "follow up", "followup", "avisame", "avísame"],
}

RELATIONSHIP_LABELS = {
    "family": "familia",
    "personal": "conocido",
    "provider": "proveedor",
    "team": "interno",
    "customer": "cliente",
    "unknown": "nuevo",
}

MODE_MAP = {
    "family": "personal_assistant",
    "personal": "personal_assistant",
    "provider": "operations",
    "team": "operations",
    "customer": "sales",
    "unknown": "universal",
}

INTENT_TO_MODE = {
    "pricing": "sales",
    "schedule": "sales",
    "followup": "sales",
    "payment": "sales",
    "support": "support",
    "complaint": "support",
    "human": "human_handoff",
    "personal": "personal_assistant",
}


def _text_has_any(lower: str, options: list[str]) -> bool:
    return any(item in lower for item in options)


def _score_hits(lower: str, options: list[str], amount: int) -> int:
    return sum(amount for item in options if item in lower)


def _extract_topics(lower: str, classification: dict[str, Any], existing_topics: list[str] | None = None) -> list[str]:
    topics: list[str] = []
    intent = str(classification.get("intent") or "").strip().lower()
    if intent and intent not in {"general", "greeting", "human"}:
        topics.append(intent)
    for topic, keywords in TOPIC_KEYWORDS.items():
        if _text_has_any(lower, keywords) and topic not in topics:
            topics.append(topic)
    for topic in existing_topics or []:
        if topic and topic not in topics:
            topics.append(topic)
    return topics[:5]


def _urgency_from_text(lower: str, relation_key: str, classification: dict[str, Any], recent_messages: list[dict[str, Any]] | None = None) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    for level, keywords in URGENCY_KEYWORDS.items():
        if _text_has_any(lower, keywords):
            if level == "critical":
                score += 65
            elif level == "high":
                score += 45
            else:
                score += 20
            reasons.append(level)
    if classification.get("intent") == "complaint":
        score += 25
        reasons.append("complaint")
    if str(classification.get("requested_human") or "").lower() in {"1", "true"} or classification.get("requested_human") is True:
        score += 20
        reasons.append("requested_human")
    message_burst = 0
    for item in reversed(recent_messages or []):
        if str(item.get("direction") or "").lower() == "inbound":
            message_burst += 1
        else:
            break
    if message_burst >= 2:
        score += 10
        reasons.append("message_burst")
    if relation_key in {"family", "personal"} and score > 0:
        score += 15
        reasons.append("known_person")
    return min(score, 100), reasons


def _urgency_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "normal"


def _merge_relation_scores(existing: dict[str, Any] | None, lower: str, classification: dict[str, Any]) -> dict[str, int]:
    base = {key: int((existing or {}).get(key, 0) or 0) for key in ["family", "personal", "provider", "team", "customer"]}
    for relation, keywords in RELATIONSHIP_KEYWORDS.items():
        amount = 14 if relation == "customer" else 30
        base[relation] += _score_hits(lower, keywords, amount)
    intent = str(classification.get("intent") or "").lower()
    if intent in {"pricing", "schedule", "payment", "followup"}:
        base["customer"] += 16
    if intent in {"support", "complaint"}:
        base["customer"] += 8
    if intent == "personal":
        base["personal"] += 20
    return {key: min(value, 100) for key, value in base.items()}


def _relation_confidence(scores: dict[str, int]) -> tuple[str, int]:
    relation_key = "unknown"
    confidence = 0
    for key, value in scores.items():
        if value > confidence:
            relation_key = key
            confidence = value
    if confidence < 15:
        return "unknown", confidence
    return relation_key, confidence


def _resolve_mode(relation_key: str, classification: dict[str, Any]) -> str:
    intent = str(classification.get("intent") or "").lower()
    if intent in INTENT_TO_MODE:
        return INTENT_TO_MODE[intent]
    return MODE_MAP.get(relation_key, "universal")


def _attention_tier(relation_key: str, urgency_level: str, known_contact: bool) -> str:
    if urgency_level == "critical" and relation_key in {"family", "personal", "team"}:
        return "owner_now"
    if urgency_level in {"critical", "high"} and known_contact:
        return "priority"
    if urgency_level in {"critical", "high"}:
        return "expedite"
    if known_contact:
        return "known_watch"
    return "normal"


def _trim_topics(topics: list[str]) -> list[str]:
    unique: list[str] = []
    for topic in topics:
        clean = str(topic or "").strip().lower()
        if clean and clean not in unique:
            unique.append(clean)
    return unique[:5]


def relationship_snapshot(memory: dict[str, Any] | None) -> dict[str, Any]:
    payload = memory or {}
    memory_data = payload.get("memory") if isinstance(payload.get("memory"), dict) else from_json(payload.get("memory_json"), {})
    existing = memory_data.get("relationship_intelligence") if isinstance(memory_data, dict) else None
    existing = existing if isinstance(existing, dict) else {}
    scores = existing.get("relation_scores") if isinstance(existing.get("relation_scores"), dict) else {}
    relation_key, confidence = _relation_confidence({
        "family": int(scores.get("family", 0) or 0),
        "personal": int(scores.get("personal", 0) or 0),
        "provider": int(scores.get("provider", 0) or 0),
        "team": int(scores.get("team", 0) or 0),
        "customer": int(scores.get("customer", 0) or 0),
    })
    urgency_score = int(existing.get("urgency_score", 0) or 0)
    urgency_level = existing.get("urgency_level") or _urgency_level(urgency_score)
    return {
        "status": existing.get("status") or ("known" if confidence >= 35 else "universal"),
        "known_contact": bool(existing.get("known_contact", confidence >= 35)),
        "relation_key": relation_key,
        "relation_label": existing.get("relation_label") or RELATIONSHIP_LABELS.get(relation_key, "nuevo"),
        "relation_confidence": confidence,
        "relation_scores": {
            "family": int(scores.get("family", 0) or 0),
            "personal": int(scores.get("personal", 0) or 0),
            "provider": int(scores.get("provider", 0) or 0),
            "team": int(scores.get("team", 0) or 0),
            "customer": int(scores.get("customer", 0) or 0),
        },
        "current_intent": existing.get("current_intent") or "general",
        "current_mode": existing.get("current_mode") or MODE_MAP.get(relation_key, "universal"),
        "urgency_level": urgency_level,
        "urgency_score": urgency_score,
        "urgency_reasons": list(existing.get("urgency_reasons") or []),
        "attention_tier": existing.get("attention_tier") or _attention_tier(relation_key, urgency_level, confidence >= 35),
        "top_topics": _trim_topics(list(existing.get("top_topics") or [])),
        "last_topic": existing.get("last_topic") or None,
        "known_name": existing.get("known_name") or None,
        "profile_version": existing.get("profile_version") or 1,
        "last_inferred_at": existing.get("last_inferred_at") or None,
    }


def build_relationship_intelligence(
    *,
    memory: dict[str, Any] | None,
    classification: dict[str, Any],
    incoming_text: str,
    contact: dict[str, Any] | None = None,
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    lower = str(incoming_text or "").lower()
    snapshot = relationship_snapshot(memory)
    relation_scores = _merge_relation_scores(snapshot.get("relation_scores"), lower, classification)
    relation_key, confidence = _relation_confidence(relation_scores)
    urgency_score, urgency_reasons = _urgency_from_text(lower, relation_key, classification, recent_messages=recent_messages)
    urgency_level = _urgency_level(urgency_score)
    current_mode = _resolve_mode(relation_key, classification)
    top_topics = _extract_topics(lower, classification, snapshot.get("top_topics"))
    last_topic = top_topics[0] if top_topics else str(classification.get("intent") or "general")
    known_contact = confidence >= 35 or relation_key in {"family", "personal", "provider", "team"}
    status = "known" if known_contact else "universal"
    return {
        "profile_version": 1,
        "status": status,
        "known_contact": known_contact,
        "relation_key": relation_key,
        "relation_label": RELATIONSHIP_LABELS.get(relation_key, "nuevo"),
        "relation_confidence": confidence,
        "relation_scores": relation_scores,
        "current_intent": str(classification.get("intent") or "general"),
        "current_mode": current_mode,
        "urgency_level": urgency_level,
        "urgency_score": urgency_score,
        "urgency_reasons": urgency_reasons,
        "attention_tier": _attention_tier(relation_key, urgency_level, known_contact),
        "top_topics": top_topics,
        "last_topic": last_topic,
        "known_name": (contact or {}).get("name") or snapshot.get("known_name"),
        "last_inferred_at": utcnow_iso(),
    }


def merge_memory_json(memory: dict[str, Any] | None, profile: dict[str, Any]) -> dict[str, Any]:
    payload = memory or {}
    existing = payload.get("memory") if isinstance(payload.get("memory"), dict) else from_json(payload.get("memory_json"), {})
    if not isinstance(existing, dict):
        existing = {}
    history = existing.get("intent_history") if isinstance(existing.get("intent_history"), dict) else {}
    intent = str(profile.get("current_intent") or "general")
    history[intent] = int(history.get(intent, 0) or 0) + 1
    return {
        **existing,
        "intent_history": history,
        "relationship_intelligence": profile,
    }


def enrich_conversation_row(row: dict[str, Any]) -> dict[str, Any]:
    snapshot = relationship_snapshot(row)
    return {
        **row,
        "relationship_label": snapshot.get("relation_label"),
        "relationship_key": snapshot.get("relation_key"),
        "relationship_status": snapshot.get("status"),
        "relationship_confidence": snapshot.get("relation_confidence"),
        "attention_tier": snapshot.get("attention_tier"),
        "urgency_level": snapshot.get("urgency_level"),
        "urgency_score": snapshot.get("urgency_score"),
        "recommended_mode": snapshot.get("current_mode"),
        "known_contact": snapshot.get("known_contact"),
        "top_topics": snapshot.get("top_topics"),
    }
