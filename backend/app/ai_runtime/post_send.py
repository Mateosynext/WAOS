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



def maybe_schedule_followups(conn, *, organization_id: str, bot_id: str, conversation_id: str, contact_id: str, classification: dict, decision: dict, bot_config: dict) -> list[dict]:
    scheduled = []
    if decision["action"] not in {"respond", "respond_and_schedule_followup"}:
        return scheduled

    optimizer_context = load_optimizer_runtime_context(conn, organization_id=organization_id, bot_id=bot_id)
    rules = list(bot_config.get("followups", {}).get("rules", []) or [])
    intent = str(classification.get('intent') or 'general')
    lower_intent = intent.lower()
    if not any(str(rule.get('type')) == 'smart_scheduling' for rule in rules) and lower_intent == 'schedule':
        rules.append({'type': 'smart_scheduling', 'delay_minutes': 30, 'max_attempts': 2, 'message_template': '¿Te aparto un horario tentativo y si te funciona lo confirmamos aquí mismo?'})
    if not any(str(rule.get('type')) == 'abandoned_quote' for rule in rules) and lower_intent in {'pricing', 'payment'}:
        rules.append({'type': 'abandoned_quote', 'delay_minutes': 120, 'max_attempts': 2, 'message_template': 'Te dejo esto abierto por si quieres retomar. Si te sirve, revisamos opción, promoción o forma de pago y lo cerramos contigo.'})
    if not any(str(rule.get('type')) == 'payment_recovery' for rule in rules) and lower_intent == 'payment':
        rules.append({'type': 'payment_recovery', 'delay_minutes': 45, 'max_attempts': 3, 'message_template': 'Veo tu pago pendiente. Si quieres, te ayudo a retomarlo o te mando otra opción para completarlo.'})
    if not any(str(rule.get('type')) == 'winback' for rule in rules) and lower_intent in {'general', 'faq'}:
        rules.append({'type': 'winback', 'delay_minutes': 1440, 'max_attempts': 1, 'message_template': 'Solo vuelvo a escribirte para no dejar esto en el aire. Si te interesa, lo retomamos en dos mensajes.'})

    selected_types = {'no_response'}
    if lower_intent == 'pricing':
        selected_types.update({'post_quote', 'abandoned_quote'})
    if lower_intent == 'payment':
        selected_types.update({'payment_recovery', 'abandoned_quote'})
    if lower_intent == 'schedule':
        selected_types.update({'smart_scheduling'})
    if lower_intent in {'general', 'faq'}:
        selected_types.update({'winback'})

    for rule in rules:
        rule_type = str(rule.get("type") or '')
        if rule_type not in selected_types:
            continue
        rule = followup_override(rule, context=optimizer_context, intent=lower_intent)
        dedupe_key = f"{conversation_id}:{rule_type}"
        exists = fetch_one(
            conn,
            """
            SELECT id FROM automation_jobs
            WHERE dedupe_key = ? AND status IN ('queued', 'locked', 'retry', 'scheduled')
            """,
            (dedupe_key,),
        )
        if exists:
            continue
        delay = int(rule.get("delay_minutes", 120))
        job_id = new_id("job")
        scheduled_for = add_minutes(utcnow_iso(), delay)
        template = rule.get('message_template') or 'Solo dando seguimiento a tu consulta.'
        execute(
            conn,
            """
            INSERT INTO automation_jobs
            (id, organization_id, bot_id, conversation_id, contact_id, rule_id, job_type, dedupe_key, scheduled_for, status, attempts, payload_json, priority, created_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, 'queued', 0, ?, ?, ?)
            """,
            (
                job_id,
                organization_id,
                bot_id,
                conversation_id,
                contact_id,
                rule_type,
                dedupe_key,
                scheduled_for,
                to_json(
                    {
                        'message_template': template,
                        'max_attempts': rule.get('max_attempts', 2),
                        'recommendation_type': rule_type,
                        'classification_intent': lower_intent,
                        'channel': rule.get('channel') or 'whatsapp',
                        'timing_policy_id': rule.get('timing_policy_id'),
                        'template_version_id': rule.get('template_version_id'),
                    }
                ),
                90 if rule_type in {'payment_recovery', 'smart_scheduling'} else (80 if rule_type in {'abandoned_quote', 'post_quote'} else 45),
                utcnow_iso(),
            ),
        )
        record_revenue_event(conn, organization_id=organization_id, bot_id=bot_id, conversation_id=conversation_id, contact_id=contact_id, event_type=rule_type, recommendation={'scheduled_for': scheduled_for, 'delay_minutes': delay, 'template': template}, expected_value=float(classification.get('urgency_score') or 0))
        scheduled.append(fetch_one(conn, "SELECT * FROM automation_jobs WHERE id = ?", (job_id,)))
    return scheduled


