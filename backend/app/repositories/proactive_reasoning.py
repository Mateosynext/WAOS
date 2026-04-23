from __future__ import annotations

from typing import Any

from .base import ConnectionLike
from ..db import execute, fetch_all, fetch_one, table_exists
from ..utils import add_minutes, from_json, new_id, to_json, utcnow_iso


def select_contacts(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str,
    contact_ids: list[str] | None,
    conversation_ids: list[str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    scoped_ids = [str(item) for item in (contact_ids or []) if str(item).strip()]
    if scoped_ids:
        placeholders = ", ".join("?" for _ in scoped_ids)
        return fetch_all(conn, f"SELECT * FROM contacts WHERE organization_id = ? AND id IN ({placeholders}) ORDER BY updated_at DESC LIMIT ?", (organization_id, *scoped_ids, limit))
    if conversation_ids:
        conv_placeholders = ", ".join("?" for _ in conversation_ids)
        return fetch_all(conn, f"SELECT DISTINCT c.* FROM contacts c JOIN conversations v ON v.contact_id = c.id WHERE c.organization_id = ? AND v.bot_id = ? AND v.id IN ({conv_placeholders}) ORDER BY c.updated_at DESC LIMIT ?", (organization_id, bot_id, *conversation_ids, limit))
    return fetch_all(
        conn,
        """
        SELECT c.*
        FROM contacts c
        JOIN (
            SELECT c0.id,
                   (
                       SELECT MAX(activity.ts)
                       FROM (
                           SELECT v.updated_at AS ts FROM conversations v WHERE v.contact_id = c0.id AND v.bot_id = ?
                           UNION ALL
                           SELECT p.updated_at AS ts FROM commerce_payments p WHERE p.contact_id = c0.id AND p.bot_id = ?
                           UNION ALL
                           SELECT a.updated_at AS ts FROM appointments a WHERE a.contact_id = c0.id AND a.bot_id = ?
                           UNION ALL
                           SELECT c0.updated_at AS ts
                       ) activity
                   ) AS sort_updated
            FROM contacts c0
            WHERE c0.organization_id = ?
        ) ranked ON ranked.id = c.id
        ORDER BY ranked.sort_updated DESC, c.updated_at DESC, c.id DESC
        LIMIT ?
        """,
        (bot_id, bot_id, bot_id, organization_id, limit),
    )


def load_contact_context(conn: ConnectionLike, *, organization_id: str, bot_id: str, contact_id: str, preferred_conversation_id: str | None) -> dict[str, Any]:
    contact = fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (contact_id,)) or {}
    conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (preferred_conversation_id,)) if preferred_conversation_id else None
    if conversation is None:
        conversation = fetch_one(conn, "SELECT * FROM conversations WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY updated_at DESC LIMIT 1", (organization_id, bot_id, contact_id)) or {}
    lead = fetch_one(conn, "SELECT * FROM crm_leads WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY updated_at DESC LIMIT 1", (organization_id, bot_id, contact_id)) or {}
    appointment = fetch_one(conn, "SELECT * FROM appointments WHERE organization_id = ? AND bot_id = ? AND contact_id = ? AND status IN ('scheduled', 'confirmed') ORDER BY scheduled_for ASC LIMIT 1", (organization_id, bot_id, contact_id)) or {}
    payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY updated_at DESC LIMIT 1", (organization_id, bot_id, contact_id)) or {}
    memory = fetch_one(conn, "SELECT * FROM contact_memory WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY last_updated_at DESC LIMIT 1", (organization_id, bot_id, contact_id)) or {}
    last_positive = fetch_one(conn, """
        SELECT * FROM outcome_events
        WHERE organization_id = ? AND contact_id = ? AND event_name IN ('appointment_attended', 'attended', 'sale_closed', 'payment_completed')
        ORDER BY event_timestamp DESC, created_at DESC LIMIT 1
        """, (organization_id, contact_id)) or {}
    completed_payments = fetch_one(conn, "SELECT COUNT(*) AS total, COALESCE(SUM(value_number), 0) AS revenue_sum FROM outcome_events WHERE organization_id = ? AND contact_id = ? AND event_name = 'payment_completed'", (organization_id, contact_id)) or {"total": 0, "revenue_sum": 0}
    return {
        "contact": contact,
        "conversation": conversation,
        "lead": lead,
        "appointment": appointment,
        "payment": payment,
        "memory": {**memory, **from_json(memory.get("memory_json"), {})},
        "last_positive": last_positive,
        "completed_payments": completed_payments,
    }


def recent_run_counts(conn: ConnectionLike, *, contact_id: str, objective: str, candidate_key: str, since_24h: str, since_7d: str) -> dict[str, int]:
    objective_24h = 0
    if table_exists(conn, "proactive_playbook_runs"):
        objective_24h_row = fetch_one(conn, "SELECT COUNT(*) AS total FROM proactive_playbook_runs WHERE contact_id = ? AND objective = ? AND created_at >= ?", (contact_id, objective, since_24h)) or {"total": 0}
        objective_24h = int(objective_24h_row.get("total") or 0)
        total_7d_row = fetch_one(conn, "SELECT COUNT(*) AS total FROM proactive_playbook_runs WHERE contact_id = ? AND created_at >= ?", (contact_id, since_7d)) or {"total": 0}
        total_7d = int(total_7d_row.get("total") or 0)
    else:
        total_7d = 0
    existing_candidate = fetch_one(conn, "SELECT status FROM proactive_contact_candidates WHERE candidate_key = ?", (candidate_key,)) or {}
    return {"objective_24h": objective_24h, "total_7d": total_7d, "existing_materialized": 1 if existing_candidate.get("status") == "materialized" else 0}


def list_proactive_run_rows(conn: ConnectionLike, *, organization_id: str, bot_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    if bot_id:
        return fetch_all(conn, "SELECT * FROM proactive_playbook_runs WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, bot_id, limit))
    return fetch_all(conn, "SELECT * FROM proactive_playbook_runs WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, limit))


def find_preferred_conversation(
    conn: ConnectionLike,
    *,
    contact_id: str,
    conversation_ids: list[str],
) -> dict[str, Any] | None:
    if not conversation_ids:
        return None
    placeholders = ", ".join("?" for _ in conversation_ids)
    return fetch_one(
        conn,
        f"SELECT id FROM conversations WHERE contact_id = ? AND id IN ({placeholders}) LIMIT 1",
        (contact_id, *conversation_ids),
    )



def insert_proactive_signal(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str,
    contact_id: str,
    signal: dict[str, Any],
    signal_family: str,
    event_at: str,
) -> dict[str, Any]:
    row_id = new_id("psig")
    execute(
        conn,
        """
        INSERT INTO proactive_signal_events (
            id, organization_id, bot_id, contact_id, conversation_id, appointment_id, payment_id, lead_id,
            signal_key, signal_family, strength_score, facts_json, event_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            organization_id,
            bot_id,
            contact_id,
            signal.get("conversation_id"),
            signal.get("appointment_id"),
            signal.get("payment_id"),
            signal.get("lead_id"),
            signal["signal_key"],
            signal_family,
            float(signal.get("strength_score") or 0),
            to_json(signal.get("facts") or {}),
            event_at,
            utcnow_iso(),
        ),
    )
    return fetch_one(conn, "SELECT * FROM proactive_signal_events WHERE id = ?", (row_id,)) or {}



def upsert_proactive_candidate(
    conn: ConnectionLike,
    *,
    candidate_key: str,
    organization_id: str,
    bot_id: str,
    contact_id: str,
    signal_row: dict[str, Any],
    playbook_id: str,
    playbook_version_id: str,
    specialist_agent_key: str,
    policy_profile_key: str | None,
    policy_profile_version: str | None,
    objective: str,
    recommended_action: str,
    channel: str,
    priority_score: float,
    priority_band: str,
    eligible: bool,
    suppression_reason: str | None,
    suggested_send_at: str,
    title: str,
    message_text: str,
    timing_policy_id: str | None,
    nba_policy_id: str | None,
    policy: dict[str, Any],
    reasoning: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    now = utcnow_iso()
    existing = fetch_one(conn, "SELECT * FROM proactive_contact_candidates WHERE candidate_key = ?", (candidate_key,))
    payload = (
        organization_id,
        bot_id,
        contact_id,
        signal_row.get("conversation_id"),
        signal_row.get("appointment_id"),
        signal_row.get("payment_id"),
        signal_row.get("lead_id"),
        signal_row.get("id"),
        signal_row.get("signal_key"),
        signal_row.get("signal_family"),
        playbook_id,
        playbook_version_id,
        specialist_agent_key,
        policy_profile_key,
        policy_profile_version,
        objective,
        recommended_action,
        channel,
        priority_score,
        priority_band,
        1 if eligible else 0,
        suppression_reason,
        suggested_send_at,
        title,
        message_text,
        timing_policy_id,
        nba_policy_id,
        to_json(policy),
        to_json(reasoning),
        to_json(metadata),
    )
    if existing:
        execute(
            conn,
            """
            UPDATE proactive_contact_candidates
            SET organization_id = ?, bot_id = ?, contact_id = ?, conversation_id = ?, appointment_id = ?, payment_id = ?, lead_id = ?,
                signal_event_id = ?, signal_key = ?, signal_family = ?, playbook_id = ?, playbook_version_id = ?,
                specialist_agent_key = ?, policy_profile_key = ?, policy_profile_version = ?, objective = ?, recommended_action = ?,
                channel = ?, priority_score = ?, priority_band = ?, eligible = ?, suppression_reason = ?, suggested_send_at = ?,
                title = ?, message_text = ?, timing_policy_id = ?, nba_policy_id = ?, policy_json = ?, reasoning_json = ?, metadata_json = ?, updated_at = ?
            WHERE candidate_key = ?
            """,
            (*payload, now, candidate_key),
        )
    else:
        execute(
            conn,
            """
            INSERT INTO proactive_contact_candidates (
                id, organization_id, bot_id, contact_id, conversation_id, appointment_id, payment_id, lead_id,
                signal_event_id, signal_key, signal_family, playbook_id, playbook_version_id, specialist_agent_key,
                policy_profile_key, policy_profile_version, objective, recommended_action, channel,
                priority_score, priority_band, eligible, suppression_reason, suggested_send_at,
                title, message_text, timing_policy_id, nba_policy_id, policy_json, reasoning_json, metadata_json,
                candidate_key, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (new_id("pcand"), *payload, candidate_key, now, now),
        )
    return fetch_one(conn, "SELECT * FROM proactive_contact_candidates WHERE candidate_key = ?", (candidate_key,)) or {}



def list_candidate_rows(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str | None = None,
    status: str | None = None,
    specialist_agent_key: str | None = None,
    eligible: bool | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    conditions = ["organization_id = ?"]
    params: list[Any] = [organization_id]
    if bot_id:
        conditions.append("bot_id = ?")
        params.append(bot_id)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if specialist_agent_key:
        conditions.append("specialist_agent_key = ?")
        params.append(specialist_agent_key)
    if eligible is not None:
        conditions.append("eligible = ?")
        params.append(1 if eligible else 0)
    where = " AND ".join(conditions)
    return fetch_all(
        conn,
        f"SELECT * FROM proactive_contact_candidates WHERE {where} ORDER BY priority_score DESC, updated_at DESC LIMIT ?",
        (*params, limit),
    )



def insert_outcome_exposure_for_playbook(
    conn: ConnectionLike,
    *,
    candidate: dict[str, Any],
    run_id: str,
    actor_user_id: str | None,
) -> dict[str, Any] | None:
    if not table_exists(conn, "outcome_exposures"):
        return None
    now = utcnow_iso()
    profile = (candidate.get("policy") or {}).get("profile") or {}
    row_id = new_id("outcome_exposure")
    execute(
        conn,
        """
        INSERT INTO outcome_exposures (
            id, organization_id, bot_id, conversation_id, contact_id, lead_id, appointment_id, payment_id,
            message_id, source_type, channel, prompt_run_id, prompt_version_id, flow_id, flow_version_id,
            template_id, template_version_id, routing_rule_id, decision_path_id, timing_policy_id,
            tone_policy_id, nba_policy_id, escalation_policy_id, playbook_id, playbook_version_id,
            handoff_id, handoff_kind, specialist_agent_key, specialist_agent_version, specialist_prompt_id,
            intent_family, agent_routing_run_id, policy_profile_key, policy_profile_version, policy_evaluation_id, operator_user_id, assigned_variant, vertical, funnel_stage,
            metadata_json, sent_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            candidate.get("organization_id"),
            candidate.get("bot_id"),
            candidate.get("conversation_id"),
            candidate.get("contact_id"),
            candidate.get("lead_id"),
            candidate.get("appointment_id"),
            candidate.get("payment_id"),
            None,
            "proactive_playbook",
            candidate.get("channel") or "whatsapp",
            run_id,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            candidate.get("timing_policy_id"),
            None,
            candidate.get("nba_policy_id"),
            None,
            candidate.get("playbook_id"),
            candidate.get("playbook_version_id"),
            None,
            None,
            candidate.get("specialist_agent_key"),
            None,
            None,
            candidate.get("specialist_agent_key"),
            None,
            profile.get("key"),
            profile.get("version"),
            None,
            actor_user_id,
            None,
            None,
            candidate.get("objective") or candidate.get("signal_family"),
            to_json({"candidate_id": candidate.get("id"), "run_id": run_id, "reasoning": candidate.get("reasoning")}),
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM outcome_exposures WHERE id = ?", (row_id,))



def get_candidate_by_id(conn: ConnectionLike, candidate_id: str) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM proactive_contact_candidates WHERE id = ?", (candidate_id,))



def get_latest_run_for_candidate(conn: ConnectionLike, candidate_id: str) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM proactive_playbook_runs WHERE candidate_id = ? ORDER BY created_at DESC LIMIT 1", (candidate_id,))



def get_outcome_exposure_by_id(conn: ConnectionLike, exposure_id: str | None) -> dict[str, Any] | None:
    if not exposure_id:
        return None
    return fetch_one(conn, "SELECT * FROM outcome_exposures WHERE id = ?", (exposure_id,))



def insert_playbook_run(
    conn: ConnectionLike,
    *,
    candidate: dict[str, Any],
    scheduled_for: str,
    action_payload: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    run_id = new_id("prun")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO proactive_playbook_runs (
            id, organization_id, bot_id, candidate_id, contact_id, conversation_id, appointment_id, payment_id, lead_id,
            specialist_agent_key, playbook_id, playbook_version_id, objective, recommended_action, channel,
            status, scheduled_for, message_text, action_payload_json, outcome_exposure_id, tool_execution_run_id,
            metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'materialized', ?, ?, ?, NULL, NULL, ?, ?, ?)
        """,
        (
            run_id,
            candidate.get("organization_id"),
            candidate.get("bot_id"),
            candidate.get("id"),
            candidate.get("contact_id"),
            candidate.get("conversation_id"),
            candidate.get("appointment_id"),
            candidate.get("payment_id"),
            candidate.get("lead_id"),
            candidate.get("specialist_agent_key"),
            candidate.get("playbook_id"),
            candidate.get("playbook_version_id"),
            candidate.get("objective"),
            candidate.get("recommended_action"),
            candidate.get("channel") or "whatsapp",
            scheduled_for,
            candidate.get("message_text"),
            to_json(action_payload),
            to_json(metadata),
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM proactive_playbook_runs WHERE id = ?", (run_id,)) or {}



def attach_exposure_to_run(conn: ConnectionLike, *, run_id: str, exposure_id: str, updated_at: str | None = None) -> dict[str, Any] | None:
    now = updated_at or utcnow_iso()
    execute(conn, "UPDATE proactive_playbook_runs SET outcome_exposure_id = ?, updated_at = ? WHERE id = ?", (exposure_id, now, run_id))
    return fetch_one(conn, "SELECT * FROM proactive_playbook_runs WHERE id = ?", (run_id,))



def mark_candidate_materialized(conn: ConnectionLike, *, candidate_id: str, updated_at: str | None = None) -> dict[str, Any] | None:
    now = updated_at or utcnow_iso()
    execute(conn, "UPDATE proactive_contact_candidates SET status = 'materialized', updated_at = ? WHERE id = ?", (now, candidate_id))
    return fetch_one(conn, "SELECT * FROM proactive_contact_candidates WHERE id = ?", (candidate_id,))
