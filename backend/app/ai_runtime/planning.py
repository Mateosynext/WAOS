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



def decide_action(*, conversation: dict, bot: dict, classification: dict, memory: dict, bot_config: dict | None = None) -> dict[str, Any]:
    bot_config = bot_config or {}
    now = parse_iso(utcnow_iso())
    paused_until = parse_iso(conversation.get("paused_until"))
    freeze_until = parse_iso(conversation.get("automation_freeze_until"))

    if bot["status"] != "active":
        return {"action": "no_reply", "reason": "bot_inactive"}
    if int(bot["ai_paused"]) == 1:
        return {"action": "no_reply", "reason": "bot_ai_paused"}
    if conversation["status"] in {"paused", "blocked", "closed"}:
        return {"action": "no_reply", "reason": f"conversation_{conversation['status']}"}
    if int(conversation["human_takeover"]) == 1 or int(conversation["ai_active"]) == 0:
        return {"action": "no_reply", "reason": "human_takeover"}
    if paused_until and now and now < paused_until:
        return {"action": "no_reply", "reason": "paused_until"}
    profile = relationship_snapshot(memory)
    talent_config = talent_config_from_bot_config(bot_config)
    if classification.get("profile_type") == "worker" and (talent_config.get("worker_recognition", {}) or {}).get("route_worker_to_human"):
        return {"action": "handoff", "reason": "worker_detected", "policy": "talent_worker_route"}
    policy_decision = evaluate_policy_action(conversation=conversation, classification=classification, memory=memory, bot_config=bot_config or {})
    if policy_decision:
        return policy_decision
    if classification.get("requested_human"):
        return {"action": "handoff", "reason": "requested_human"}

    next_score = max(0, min(100, int(memory.get("lead_score", 0)) + int(classification.get("score_delta", 0))))
    urgency_score = int(classification.get("urgency_score", profile.get("urgency_score", 0)) or 0)
    if classification.get("intent") == "complaint" and urgency_score >= 60:
        return {"action": "handoff", "reason": "complaint_high_urgency"}
    if next_score >= 90 and classification.get("intent") == "schedule":
        return {"action": "respond_and_schedule_followup", "reason": "hot_lead_schedule"}
    if urgency_score >= 85 and profile.get("relation_key") in {"family", "personal", "team"}:
        return {"action": "respond", "reason": "known_contact_critical"}
    if freeze_until and now and now < freeze_until:
        return {"action": "respond", "reason": "respond_during_freeze_no_job"}
    return {"action": "respond", "reason": "default"}


