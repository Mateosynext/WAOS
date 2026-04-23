from __future__ import annotations

import json
import re
import time
from typing import Any, Iterator

import httpx

from ..config import settings
from ..contact_intelligence import build_relationship_intelligence, merge_memory_json, relationship_snapshot
from ..db import execute, fetch_all, fetch_one, has_column, table_exists
from ..domain_events import emit_domain_event
from ..policy_engine import DEFAULT_INTENT_KEYWORDS, evaluate_policy_action, resolve_intent_keywords
from ..domains.language import default_language_templates, get_language_config
from ..platform import append_technical_log, finish_execution_run, start_execution_run
from ..telemetry_runtime import record_stage_metric
from ..world_class import finish_trace_span, start_trace_span
from ..repositories import create_audit_log, create_message
from ..utils import add_minutes, from_json, hash_value, new_id, parse_iso, to_json, utcnow_iso
from ..talent_runtime import generate_talent_reply, maybe_register_candidate_confirmation, talent_config_from_bot_config
from ..runtime_settings import ai_optimization_settings, memory_runtime_settings
from ..world_class import append_memory_episode, cache_efficiency_overview, choose_model, circuit_allow, circuit_record_failure, circuit_record_success, compress_prompt_payload, index_bot_knowledge, lookup_ai_cache, maybe_create_conversation_checkpoint, recent_checkpoints, record_ai_usage, search_knowledge_embeddings, search_knowledge_embeddings_cached, search_memory_episodes, search_memory_vectors, store_ai_cache, upsert_memory_vector, record_revenue_event
from ..knowledge_runtime import search_governed_knowledge, sync_config_knowledge
from ..response_ranking_runtime import style_response_candidate


INTENT_KEYWORDS = DEFAULT_INTENT_KEYWORDS



def update_memory(conn, *, organization_id: str, contact_id: str, bot_id: str, incoming_text: str, classification: dict, contact: dict | None = None, recent_messages: list[dict[str, Any]] | None = None, conversation_id: str | None = None, source_message_id: str | None = None) -> dict:
    memory = fetch_one(conn, "SELECT * FROM contact_memory WHERE contact_id = ? AND bot_id = ?", (contact_id, bot_id))
    old_score = int(memory.get("lead_score", 0)) if memory else 0
    new_score = max(0, min(100, old_score + int(classification.get("score_delta", 0))))
    summary_parts = []
    if memory and memory.get("summary"):
        summary_parts.append(memory["summary"])
    summary_parts.append(f"Último mensaje: {incoming_text[:140]}")
    summary = " | ".join(summary_parts[-3:])
    objection = classification.get("objection") or ""
    interest = classification.get("interest") or (memory.get("interest") if memory else None)
    relation_profile = build_relationship_intelligence(
        memory=memory,
        classification=classification,
        incoming_text=incoming_text,
        contact=contact,
        recent_messages=recent_messages,
    )
    next_action = "owner_attention" if relation_profile.get("attention_tier") == "owner_now" else ("priority_followup" if relation_profile.get("urgency_level") in {"critical", "high"} else ("human_handoff" if classification.get("requested_human") else "reply"))
    followup_at = add_minutes(utcnow_iso(), 30) if relation_profile.get("urgency_level") == "critical" else (add_minutes(utcnow_iso(), 120) if classification.get("intent") in {"pricing", "schedule", "payment", "followup"} else None)
    memory_payload = merge_memory_json(memory, relation_profile)
    memory_version = "v2"
    memory_etag = hash_value(to_json(memory_payload))
    now = utcnow_iso()
    base_sql = """
        UPDATE contact_memory
        SET lead_stage = ?, lead_score = ?, interest = ?, objections = ?, summary = ?, next_action = ?, followup_at = ?, memory_json = ?, last_updated_at = ?
    """
    params = [
        classification.get("lead_stage") or "contacted",
        new_score,
        interest,
        objection,
        summary,
        next_action,
        followup_at,
        to_json(memory_payload),
        now,
    ]
    if has_column(conn, "contact_memory", "memory_version"):
        base_sql += ", memory_version = ?"
        params.append(memory_version)
    if has_column(conn, "contact_memory", "memory_etag"):
        base_sql += ", memory_etag = ?"
        params.append(memory_etag)
    if has_column(conn, "contact_memory", "operational_state_json"):
        base_sql += ", operational_state_json = ?"
        params.append(to_json({
            "intent_detected": classification.get("intent"),
            "urgency_level": relation_profile.get("urgency_level"),
            "urgency_score": relation_profile.get("urgency_score"),
            "next_action": next_action,
            "classifier_source": classification.get("_classifier_source") or "heuristic",
            "generator_source": classification.get("_generator_source"),
            "updated_at": now,
        }))
    for column, value in [
        ("urgency_level", relation_profile.get("urgency_level") or "normal"),
        ("urgency_score", int(relation_profile.get("urgency_score", 0) or 0)),
        ("known_contact", 1 if relation_profile.get("known_contact") else 0),
        ("current_intent", classification.get("intent") or relation_profile.get("current_intent")),
        ("current_mode", classification.get("current_mode") or relation_profile.get("current_mode")),
        ("last_classifier_source", classification.get("_classifier_source") or "heuristic"),
        ("last_generator_source", classification.get("_generator_source")),
    ]:
        if has_column(conn, "contact_memory", column):
            base_sql += f", {column} = ?"
            params.append(value)
    base_sql += " WHERE contact_id = ? AND bot_id = ?"
    params.extend([contact_id, bot_id])
    execute(conn, base_sql, params)
    updated = fetch_one(conn, "SELECT * FROM contact_memory WHERE contact_id = ? AND bot_id = ?", (contact_id, bot_id))
    memory_text = " | ".join([str(summary or ''), str(interest or ''), str(objection or ''), str(next_action or '')]).strip()
    if memory_text:
        upsert_memory_vector(conn, organization_id=organization_id, contact_id=contact_id, bot_id=bot_id, scope='contact_memory', content_text=memory_text, metadata={'lead_stage': classification.get('lead_stage'), 'intent': classification.get('intent'), 'next_action': next_action}, score=float(new_score))
    memory_profile = memory_runtime_settings()
    if memory_profile.get('episodic_memory_enabled', True):
        append_memory_episode(
            conn,
            organization_id=organization_id,
            contact_id=contact_id,
            bot_id=bot_id if not memory_profile.get('cross_bot_intelligence_enabled', True) else None,
            conversation_id=conversation_id,
            source_message_id=source_message_id,
            episode_type=str(classification.get('intent') or 'conversation_turn'),
            summary_text=memory_text or incoming_text[:220],
            metadata={
                'intent': classification.get('intent'),
                'lead_stage': classification.get('lead_stage'),
                'next_action': next_action,
                'cross_bot': bool(memory_profile.get('cross_bot_intelligence_enabled', True)),
                'bot_scope': 'cross_bot' if memory_profile.get('cross_bot_intelligence_enabled', True) else 'bot_only',
                'classifier_source': classification.get('_classifier_source') or 'heuristic',
            },
            score=float(new_score),
        )
    return updated


