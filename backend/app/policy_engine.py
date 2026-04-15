from __future__ import annotations

from typing import Any

from .contact_intelligence import relationship_snapshot

DEFAULT_INTENT_KEYWORDS = {
    "pricing": ["precio", "costa", "cuesta", "cotizacion", "cotizar", "presupuesto", "price", "pricing", "quote", "cost"],
    "schedule": ["cita", "agendar", "agendo", "reservar", "agenda", "disponibilidad", "schedule", "book", "booking", "appointment", "available", "availability"],
    "faq": ["horario", "horarios", "ubicacion", "direccion", "donde", "servicios", "promocion", "hours", "location", "where", "services", "service", "promotion"],
    "complaint": ["queja", "reclamo", "molesto", "malo", "pésimo", "pesimo", "enojado", "complaint", "upset", "bad", "terrible", "angry"],
    "human": ["humano", "asesor", "agente", "persona", "human", "agent", "person", "representative"],
    "greeting": ["hola", "buenas", "buen día", "buen dia", "hello", "hi", "hey"],
    "support": ["soporte", "ayuda", "problema", "error", "falla", "support", "issue", "help"],
    "payment": ["pago", "deposito", "depósito", "transferencia", "factura", "payment", "invoice", "charge"],
    "followup": ["seguimiento", "retomo", "retomar", "pendiente", "follow up", "followup", "checking in"],
    "personal": ["favor personal", "soy tu amigo", "soy tu prima", "soy tu primo", "tema personal", "personal favor"],
}


def resolve_intent_keywords(bot_config: dict[str, Any] | None) -> dict[str, list[str]]:
    resolved = {key: list(value) for key, value in DEFAULT_INTENT_KEYWORDS.items()}
    config = (bot_config or {}).get("runtime_policy", {}) or {}
    overrides = config.get("intent_keywords") or {}
    if not isinstance(overrides, dict):
        return resolved
    for key, value in overrides.items():
        if not isinstance(value, list):
            continue
        normalized = [str(item).strip().lower() for item in value if str(item).strip()]
        if normalized:
            resolved[str(key)] = normalized
    return resolved


def _matches_rule(rule: dict[str, Any], *, conversation: dict[str, Any], classification: dict[str, Any], memory: dict[str, Any]) -> bool:
    profile = relationship_snapshot(memory)
    intent = str(classification.get("intent") or "general")
    urgency_score = int(classification.get("urgency_score", profile.get("urgency_score", 0)) or 0)
    lead_score = int(memory.get("lead_score", 0) or 0)
    if rule.get("when_intent_in") and intent not in {str(item) for item in rule.get("when_intent_in", [])}:
        return False
    if "requested_human" in rule and bool(classification.get("requested_human")) != bool(rule.get("requested_human")):
        return False
    if rule.get("conversation_status_in") and str(conversation.get("status")) not in {str(item) for item in rule.get("conversation_status_in", [])}:
        return False
    if rule.get("relation_in") and str(profile.get("relation_key")) not in {str(item) for item in rule.get("relation_in", [])}:
        return False
    if urgency_score < int(rule.get("min_urgency_score", 0) or 0):
        return False
    if lead_score < int(rule.get("min_lead_score", 0) or 0):
        return False
    return True


def evaluate_policy_action(*, conversation: dict[str, Any], classification: dict[str, Any], memory: dict[str, Any], bot_config: dict[str, Any] | None) -> dict[str, Any] | None:
    policy = (bot_config or {}).get("runtime_policy", {}) or {}
    rules = policy.get("handoff_rules") or []
    if not isinstance(rules, list):
        return None
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        if not _matches_rule(rule, conversation=conversation, classification=classification, memory=memory):
            continue
        name = str(rule.get("name") or rule.get("id") or f"tenant_rule_{idx + 1}")
        return {
            "action": str(rule.get("action") or "handoff"),
            "reason": str(rule.get("reason") or name),
            "policy": name,
        }
    return None
