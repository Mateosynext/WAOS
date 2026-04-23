from __future__ import annotations

from typing import Any

from .base import ConnectionLike
from ..db import execute
from ..utils import new_id, to_json, utcnow_iso


def create_message_ai_run(
    conn: ConnectionLike,
    *,
    ai_run_id: str,
    organization_id: str,
    message_id: str,
    conversation_id: str,
    bot_id: str,
    classifier_input: dict[str, Any],
    classifier_output: dict[str, Any],
    decision_input: dict[str, Any],
    decision_output: dict[str, Any],
    generator_input: dict[str, Any],
    generator_output: dict[str, Any],
    action_taken: str | None,
    error: str | None,
    correlation_id: str | None = None,
    classifier_source: str | None = None,
    decision_policy: str | None = None,
    generator_source: str | None = None,
    fallback_chain: list[Any] | None = None,
    selected_variant: str | None = None,
    candidate_count: int = 0,
    ranking_version: str | None = None,
    ranking_summary: dict[str, Any] | None = None,
    include_extended_fields: bool = True,
) -> None:
    if include_extended_fields:
        execute(conn, """
            INSERT INTO message_ai_runs
            (id, organization_id, message_id, conversation_id, bot_id, classifier_input, classifier_output, decision_input, decision_output, generator_input, generator_output, action_taken, error, created_at, correlation_id, classifier_source, decision_policy, generator_source, fallback_chain_json, selected_variant, candidate_count, ranking_version, ranking_summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ai_run_id, organization_id, message_id, conversation_id, bot_id,
            to_json(classifier_input), to_json(classifier_output), to_json(decision_input), to_json(decision_output),
            to_json(generator_input), to_json(generator_output), action_taken, error, utcnow_iso(), correlation_id,
            classifier_source, decision_policy, generator_source, to_json(fallback_chain or []), selected_variant,
            int(candidate_count or 0), ranking_version, to_json(ranking_summary or {}),
        ))
    else:
        execute(conn, """
            INSERT INTO message_ai_runs
            (id, organization_id, message_id, conversation_id, bot_id, classifier_input, classifier_output, decision_input, decision_output, generator_input, generator_output, action_taken, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ai_run_id, organization_id, message_id, conversation_id, bot_id,
            to_json(classifier_input), to_json(classifier_output), to_json(decision_input), to_json(decision_output),
            to_json(generator_input), to_json(generator_output), action_taken, error, utcnow_iso(),
        ))


def create_response_candidate_ranking(
    conn: ConnectionLike,
    *,
    organization_id: str,
    ai_run_id: str,
    message_id: str,
    conversation_id: str,
    bot_id: str,
    item: dict[str, Any],
) -> None:
    execute(conn, """
        INSERT INTO response_candidate_rankings (
            id, organization_id, message_ai_run_id, message_id, conversation_id, bot_id, candidate_index, variant_key,
            tone, cta_style, length, framing, source, response_text, verification_status, verification_json,
            score_total, score_json, selected, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_id('resp_rank'), organization_id, ai_run_id, message_id, conversation_id, bot_id,
        int(item.get('candidate_index') or 0), item.get('variant_key'), item.get('tone'), item.get('cta_style'),
        item.get('length'), item.get('framing'), item.get('source'), item.get('text'),
        (item.get('verification') or {}).get('status'), to_json(item.get('verification') or {}),
        float(item.get('score_total') or 0.0), to_json(item.get('score') or {}),
        1 if item.get('selected') else 0, utcnow_iso(),
    ))


def create_message_operational_reasoning(
    conn: ConnectionLike,
    *,
    organization_id: str,
    message_id: str,
    conversation_id: str,
    bot_id: str,
    classification: dict[str, Any],
    decision: dict[str, Any],
    execution_plan: dict[str, Any],
    grounded_context: dict[str, Any],
    verification: dict[str, Any],
    candidate_ranking: dict[str, Any],
    post_send_evaluation: dict[str, Any],
    memory_curation: dict[str, Any],
    self_state: dict[str, Any],
) -> None:
    execute(conn, "INSERT INTO message_operational_reasoning (id, organization_id, message_id, conversation_id, bot_id, intent_detected, urgency_level, urgency_score, takeover_reason, policy_applied, classifier_source, generator_source, summary_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
        new_id('mreason'), organization_id, message_id, conversation_id, bot_id,
        classification.get('intent'), classification.get('urgency_level'), int(classification.get('urgency_score', 0) or 0),
        decision.get('reason') if decision.get('action') == 'handoff' else None,
        decision.get('policy') or 'heuristic', classification.get('_classifier_source'), classification.get('_generator_source'),
        to_json({
            'intention_detected': classification.get('intent'),
            'urgency': {'level': classification.get('urgency_level'), 'score': classification.get('urgency_score')},
            'takeover_reason': decision.get('reason') if decision.get('action') == 'handoff' else None,
            'policy_applied': decision.get('policy') or 'heuristic',
            'planner': execution_plan,
            'grounded_context': {'source_count': grounded_context.get('source_count'), 'coverage': grounded_context.get('coverage')},
            'verification': verification,
            'candidate_ranking': candidate_ranking,
            'post_send_evaluation': post_send_evaluation,
            'memory_curation': memory_curation,
            'self_state': self_state,
        }),
        utcnow_iso(),
    ))
