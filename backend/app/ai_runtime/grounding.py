from __future__ import annotations

import re
from typing import Any

from ..contact_intelligence import relationship_snapshot
from ..knowledge_runtime import governed_knowledge_summary, search_governed_knowledge
from ..response_ranking_runtime import (
    build_ranking_summary,
    build_response_candidate_specs,
    infer_reply_language,
    score_response_candidate,
)
from ..multi_agent_runtime import (
    apply_specialist_plan,
    apply_supervisor_decision,
    build_shared_memory_context,
    route_intent_to_specialist,
    supervise_specialist_route,
)
from ..optimizer_runtime import (
    apply_candidate_spec_overrides,
    apply_execution_plan_overrides,
    apply_handoff_override,
    apply_specialist_route_override,
    create_runtime_optimizer_audit,
    load_optimizer_runtime_context,
    maybe_record_shadow_selection,
)
from ..growth_os_runtime import apply_growth_os_execution_focus, apply_growth_os_specialist_focus, active_growth_os_focus
from ..self_state_runtime import (
    apply_self_state_decision,
    build_conversation_self_state,
    build_turn_self_state,
)


_PRICE_PATTERN = re.compile(r"(?:\$|usd|mxn|eur|precio|price)\s*[:=]?\s*[0-9][0-9,\.]*", re.IGNORECASE)
_HOURS_PATTERN = re.compile(r"\b(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s*(?:am|pm|hrs?|h)?\b", re.IGNORECASE)



def _safe_lookup(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return []


def _normalize_topic(topic: str) -> str:
    value = str(topic or "").strip().lower()
    synonyms = {
        "quote": "pricing",
        "cotizacion": "pricing",
        "booking": "schedule",
        "faq": "faq",
        "support": "support",
        "payment": "payment",
        "direccion": "location",
        "ubicacion": "location",
        "horario": "schedule",
    }
    return synonyms.get(value, value)


def _source_record(*, source_type: str, label: str, content_text: str, supports: list[str], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "label": label,
        "content_text": str(content_text or "").strip(),
        "supports": [_normalize_topic(item) for item in supports if item],
        "metadata": metadata or {},
    }


def _business_knowledge_sources(bot_config: dict[str, Any]) -> list[dict[str, Any]]:
    business = (bot_config or {}).get("business_knowledge", {}) or {}
    sources: list[dict[str, Any]] = []
    services = business.get("services") or []
    if services:
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="services",
                content_text=", ".join(str(item) for item in services[:8]),
                supports=["faq", "general", "support"],
            )
        )
    prices = business.get("prices") or []
    if prices:
        rendered_prices: list[str] = []
        for item in prices[:6]:
            if isinstance(item, dict):
                rendered_prices.append(f"{item.get('name', 'Servicio')}: {item.get('price', '')}".strip(": "))
            else:
                rendered_prices.append(str(item))
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="prices",
                content_text=" | ".join(rendered_prices),
                supports=["pricing", "payment"],
            )
        )
    hours = str(business.get("hours") or "").strip()
    if hours:
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="hours",
                content_text=hours,
                supports=["schedule", "faq"],
            )
        )
    location = str(business.get("location") or "").strip()
    if location:
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="location",
                content_text=location,
                supports=["location", "faq"],
            )
        )
    faqs = business.get("faqs") or []
    faq_lines: list[str] = []
    for item in faqs[:6]:
        if isinstance(item, dict) and (item.get("q") or item.get("a")):
            faq_lines.append(f"Q: {item.get('q', '')} A: {item.get('a', '')}".strip())
    if faq_lines:
        sources.append(
            _source_record(
                source_type="business_knowledge",
                label="faqs",
                content_text=" | ".join(faq_lines),
                supports=["faq", "support", "location"],
            )
        )
    return [item for item in sources if item.get("content_text")]


def _support_status_for_topic(sources: list[dict[str, Any]], topic: str) -> str:
    relevant = [item for item in sources if topic in (item.get("supports") or [])]
    if not relevant:
        return "missing"
    statuses = [str((item.get("metadata") or {}).get("freshness_status") or "fresh") for item in relevant]
    if "fresh" in statuses:
        return "fresh"
    if "aging" in statuses:
        return "aging"
    if "stale" in statuses:
        return "stale"
    return "unknown"


def build_grounded_context(
    *,
    text: str,
    memory: dict[str, Any],
    bot_config: dict[str, Any],
    conn=None,
    organization_id: str | None = None,
    bot_id: str | None = None,
    contact_id: str | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    from ..world_class import recent_checkpoints, search_knowledge_embeddings, search_memory_vectors

    sources: list[dict[str, Any]] = []
    governed_hits: list[dict[str, Any]] = []
    if conn is not None and organization_id and bot_id:
        governed_hits = _safe_lookup(
            search_governed_knowledge,
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            query=text,
            intent=(memory or {}).get("current_intent") or None,
            limit=6,
        )
        for item in governed_hits:
            trace = dict(item.get("traceability") or {})
            sources.append(
                _source_record(
                    source_type="governed_knowledge",
                    label=item.get("title") or item.get("source_key") or "knowledge_document",
                    content_text=item.get("content_text") or "",
                    supports=item.get("supports") or [],
                    metadata={
                        "domain": item.get("domain"),
                        "score": item.get("score"),
                        "freshness_status": item.get("freshness_status"),
                        "traceability": trace,
                    },
                )
            )

    config_sources = _business_knowledge_sources(bot_config)
    if not governed_hits:
        sources.extend(config_sources)
    else:
        sources.extend(config_sources[:2])

    if conn is not None and organization_id:
        memory_hits = _safe_lookup(
            search_memory_vectors,
            conn,
            organization_id=organization_id,
            contact_id=contact_id,
            bot_id=bot_id,
            query=text,
            limit=4,
        )
        for item in memory_hits:
            sources.append(
                _source_record(
                    source_type="memory_vector",
                    label="memory_recall",
                    content_text=item.get("content_text") or "",
                    supports=["general", "support", "schedule", "pricing"],
                    metadata={"score": item.get("score")},
                )
            )
    if conn is not None and organization_id and bot_id:
        knowledge_hits = _safe_lookup(
            search_knowledge_embeddings,
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            query=text,
            limit=4,
        )
        for item in knowledge_hits:
            sources.append(
                _source_record(
                    source_type="knowledge_embedding",
                    label="knowledge_recall",
                    content_text=item.get("content_text") or "",
                    supports=["faq", "support", "pricing", "schedule", "payment"],
                    metadata={"source_key": item.get("source_key")},
                )
            )
    if conn is not None and conversation_id:
        checkpoints = _safe_lookup(recent_checkpoints, conn, conversation_id=conversation_id, limit=2)
        for item in checkpoints:
            summary = str(item.get("summary_text") or "").strip()
            if summary:
                sources.append(
                    _source_record(
                        source_type="conversation_checkpoint",
                        label="checkpoint",
                        content_text=summary,
                        supports=["general", "support", "followup"],
                        metadata={"facts": item.get("facts")},
                    )
                )

    limited_sources = sources[:16]
    coverage = {
        "pricing": any("pricing" in item.get("supports", []) for item in limited_sources),
        "schedule": any("schedule" in item.get("supports", []) for item in limited_sources),
        "location": any("location" in item.get("supports", []) for item in limited_sources),
        "faq": any("faq" in item.get("supports", []) for item in limited_sources),
        "support": any("support" in item.get("supports", []) for item in limited_sources),
        "payment": any("payment" in item.get("supports", []) for item in limited_sources),
        "memory": any(item.get("source_type") == "memory_vector" for item in limited_sources),
        "knowledge": any(item.get("source_type") == "knowledge_embedding" for item in limited_sources),
        "governed_knowledge": any(item.get("source_type") == "governed_knowledge" for item in limited_sources),
        "checkpoints": any(item.get("source_type") == "conversation_checkpoint" for item in limited_sources),
    }
    support_status = {
        topic: _support_status_for_topic(limited_sources, topic)
        for topic in ["pricing", "schedule", "location", "faq", "support", "payment"]
    }
    governed_summary = governed_knowledge_summary(governed_hits)
    return {
        "sources": limited_sources,
        "coverage": coverage,
        "support_status": support_status,
        "source_count": len(limited_sources),
        "grounding_mode": "governed_multi_source" if governed_hits else ("multi_source" if len(limited_sources) > 1 else ("single_source" if limited_sources else "none")),
        "verifiable": bool(limited_sources),
        "relationship": relationship_snapshot(memory),
        "knowledge_summary": governed_summary,
        "traceability": governed_summary.get("traceability", []),
        "freshness_status": governed_summary.get("overall_freshness", "fresh" if limited_sources else "none"),
    }


