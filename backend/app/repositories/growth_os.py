from __future__ import annotations

from collections import defaultdict
from typing import Any

from .base import ConnectionLike
from ..db import execute, fetch_all, fetch_one, table_exists
from ..utils import add_minutes, from_json, new_id, parse_iso, to_json, utcnow_iso


def upsert_growth_control_state(conn: ConnectionLike, *, organization_id: str, bot_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    existing = fetch_one(conn, "SELECT * FROM growth_os_control_states WHERE bot_id = ?", (bot_id,))
    now = utcnow_iso()
    next_scheduled_at = now
    if existing:
        execute(
            conn,
            """
            UPDATE growth_os_control_states
            SET organization_id = ?, is_enabled = ?, scheduler_enabled = ?, scheduler_mode = ?, cycle_interval_minutes = ?,
                default_goals_json = ?, max_targets = ?, auto_execute = ?, include_suppressed = ?, scorecard_window = ?,
                prioritize_specialist = ?, prioritize_tools = ?, prioritize_handoffs = ?, prioritize_playbooks = ?,
                contact_focus_hours = ?, config_json = ?, next_scheduled_at = COALESCE(next_scheduled_at, ?), updated_at = ?
            WHERE bot_id = ?
            """,
            (
                organization_id, fields["is_enabled"], fields["scheduler_enabled"], fields["scheduler_mode"], fields["cycle_interval_minutes"],
                to_json(fields["default_goals"]), fields["max_targets"], fields["auto_execute"], fields["include_suppressed"], fields["scorecard_window"],
                fields["prioritize_specialist"], fields["prioritize_tools"], fields["prioritize_handoffs"], fields["prioritize_playbooks"],
                fields["contact_focus_hours"], fields["config_json"], next_scheduled_at, now, bot_id,
            ),
        )
    else:
        execute(
            conn,
            """
            INSERT INTO growth_os_control_states (
                id, organization_id, bot_id, is_enabled, scheduler_enabled, scheduler_mode, cycle_interval_minutes,
                default_goals_json, max_targets, auto_execute, include_suppressed, scorecard_window,
                prioritize_specialist, prioritize_tools, prioritize_handoffs, prioritize_playbooks, contact_focus_hours,
                latest_run_id, last_started_at, last_completed_at, next_scheduled_at, last_status,
                last_summary_json, config_json, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, 'idle', '{}', ?, '{}', ?, ?)
            """,
            (
                new_id("growthctl"), organization_id, bot_id, fields["is_enabled"], fields["scheduler_enabled"], fields["scheduler_mode"], fields["cycle_interval_minutes"],
                to_json(fields["default_goals"]), fields["max_targets"], fields["auto_execute"], fields["include_suppressed"], fields["scorecard_window"],
                fields["prioritize_specialist"], fields["prioritize_tools"], fields["prioritize_handoffs"], fields["prioritize_playbooks"], fields["contact_focus_hours"],
                next_scheduled_at, fields["config_json"], now, now,
            ),
        )
    return fetch_one(conn, "SELECT * FROM growth_os_control_states WHERE bot_id = ?", (bot_id,)) or {}


def load_latest_scorecards(conn: ConnectionLike, *, organization_id: str, bot_id: str | None, window: str) -> list[dict[str, Any]]:
    if not table_exists(conn, "outcome_scorecard_snapshots"):
        return []
    return fetch_all(conn, """
        SELECT * FROM outcome_scorecard_snapshots
        WHERE organization_id = ? AND (? IS NULL OR bot_id = ?) AND scorecard_window = ?
        ORDER BY computed_at DESC
        """, (organization_id, bot_id, bot_id, window))


def touch_control_state_after_run(conn: ConnectionLike, *, organization_id: str, bot_id: str, run_id: str, summary: dict[str, Any], status: str = 'completed') -> None:
    if not table_exists(conn, "growth_os_control_states"):
        return
    now = utcnow_iso()
    control = fetch_one(conn, "SELECT * FROM growth_os_control_states WHERE bot_id = ?", (bot_id,))
    if not control:
        return
    interval_minutes = int(control.get("cycle_interval_minutes") or 30)
    execute(conn, """
        UPDATE growth_os_control_states
        SET latest_run_id = ?, last_completed_at = ?, next_scheduled_at = ?, last_status = ?, last_summary_json = ?, updated_at = ?
        WHERE bot_id = ? AND organization_id = ?
        """, (run_id, now, add_minutes(now, interval_minutes), status, to_json(summary), now, bot_id, organization_id))


def create_growth_run(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str,
    mode: str,
    goals: list[str],
    summary: dict[str, Any],
    decision_policy: dict[str, Any],
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    run_id = new_id("growthrun")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO growth_os_runs (
            id, organization_id, bot_id, mode, status, goals_json, summary_json, decision_policy_json, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            organization_id,
            bot_id,
            mode,
            "completed",
            to_json(goals or []),
            to_json(summary),
            to_json(decision_policy),
            to_json(metadata or {}),
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM growth_os_runs WHERE id = ?", (run_id,)) or {}


def create_growth_target(
    conn: ConnectionLike,
    *,
    growth_run_id: str,
    organization_id: str,
    bot_id: str,
    candidate: dict[str, Any],
    proactive_run_id: str | None,
    objective: str,
    goal: str,
    timing_decision: str,
    expected_value: float,
    status: str,
    evidence: dict[str, Any],
    materialized: dict[str, Any] | None,
) -> dict[str, Any]:
    target_id = new_id("growthtarget")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO growth_os_targets (
            id, growth_run_id, organization_id, bot_id, candidate_id, proactive_run_id, contact_id, conversation_id,
            objective, goal, specialist_agent_key, timing_decision, channel, action_type, priority_score,
            expected_value, status, scorecard_json, evidence_json, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            target_id,
            growth_run_id,
            organization_id,
            bot_id,
            candidate.get("id"),
            proactive_run_id,
            candidate.get("contact_id"),
            candidate.get("conversation_id"),
            objective,
            goal,
            candidate.get("specialist_agent_key"),
            timing_decision,
            candidate.get("channel") or "whatsapp",
            "materialize_playbook",
            float(candidate.get("priority_score") or 0.0),
            float(expected_value or 0.0),
            status,
            to_json(
                {
                    "playbook": evidence.get("playbook_scorecard"),
                    "specialist": evidence.get("specialist_scorecard"),
                    "channel": evidence.get("channel_scorecard"),
                }
            ),
            to_json(evidence),
            to_json({"candidate": candidate, "materialized": materialized}),
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM growth_os_targets WHERE id = ?", (target_id,)) or {}


def list_candidate_target_rows(conn: ConnectionLike, *, organization_id: str, bot_id: str, limit: int = 20) -> list[dict[str, Any]]:
    return fetch_all(
        conn,
        "SELECT * FROM growth_os_targets WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT ?",
        (organization_id, bot_id, limit),
    )


def get_latest_growth_run(conn: ConnectionLike, *, organization_id: str, bot_id: str) -> dict[str, Any] | None:
    return fetch_one(
        conn,
        "SELECT * FROM growth_os_runs WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 1",
        (organization_id, bot_id),
    )


def list_growth_run_rows(conn: ConnectionLike, *, organization_id: str, bot_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if bot_id:
        return fetch_all(conn, "SELECT * FROM growth_os_runs WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, bot_id, limit))
    return fetch_all(conn, "SELECT * FROM growth_os_runs WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, limit))


def list_growth_targets_for_run(conn: ConnectionLike, *, growth_run_id: str) -> list[dict[str, Any]]:
    return fetch_all(conn, "SELECT * FROM growth_os_targets WHERE growth_run_id = ? ORDER BY priority_score DESC, created_at ASC", (growth_run_id,))


def list_active_bot_rows(conn: ConnectionLike, *, limit: int) -> list[dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT id, organization_id, status, ai_paused, config_draft_json
        FROM bots
        WHERE deleted_at IS NULL AND status IN ('active', 'published', 'draft')
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (max(limit * 5, 20),),
    )


def mark_control_state_running(conn: ConnectionLike, *, bot_id: str, started_at: str) -> None:
    execute(
        conn,
        "UPDATE growth_os_control_states SET last_started_at = ?, last_status = 'running', updated_at = ? WHERE bot_id = ?",
        (started_at, started_at, bot_id),
    )


def mark_control_state_completed(
    conn: ConnectionLike,
    *,
    bot_id: str,
    run_id: str | None,
    completed_at: str,
    cycle_interval_minutes: int,
    summary: dict[str, Any],
) -> None:
    execute(
        conn,
        """
        UPDATE growth_os_control_states
        SET latest_run_id = ?, last_completed_at = ?, next_scheduled_at = ?, last_status = 'completed', last_summary_json = ?, updated_at = ?
        WHERE bot_id = ?
        """,
        (run_id, completed_at, add_minutes(completed_at, cycle_interval_minutes), to_json(summary), completed_at, bot_id),
    )


def mark_control_state_failed(conn: ConnectionLike, *, bot_id: str, failed_at: str, cycle_interval_minutes: int, error: str) -> None:
    execute(
        conn,
        """
        UPDATE growth_os_control_states
        SET last_completed_at = ?, next_scheduled_at = ?, last_status = 'failed', metadata_json = ?, updated_at = ?
        WHERE bot_id = ?
        """,
        (failed_at, add_minutes(failed_at, cycle_interval_minutes), to_json({"last_error": error}), failed_at, bot_id),
    )


def find_focus_target(
    conn: ConnectionLike,
    *,
    organization_id: str,
    bot_id: str,
    cutoff_iso: str,
    contact_id: str | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any] | None:
    where_sql = ""
    params: list[Any] = [organization_id, bot_id, cutoff_iso]
    if contact_id and conversation_id:
        where_sql = "AND contact_id = ? AND conversation_id = ?"
        params.extend([contact_id, conversation_id])
    elif contact_id:
        where_sql = "AND contact_id = ?"
        params.append(contact_id)
    return fetch_one(
        conn,
        f"""
        SELECT * FROM growth_os_targets
        WHERE organization_id = ? AND bot_id = ? AND created_at >= ? AND status IN ('selected','executed') {where_sql}
        ORDER BY expected_value DESC, priority_score DESC, created_at DESC
        LIMIT 1
        """,
        tuple(params),
    )
