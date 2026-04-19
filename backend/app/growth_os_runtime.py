from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from .db import execute, fetch_all, fetch_one, table_exists
from .proactive_reasoning_runtime import evaluate_proactive_candidates, list_proactive_runs, materialize_proactive_candidate
from .utils import add_minutes, from_json, new_id, parse_iso, to_json, utcnow, utcnow_iso


DEFAULT_GROWTH_OS_CONFIG: dict[str, Any] = {
    "enabled": True,
    "scheduler": {
        "enabled": True,
        "mode": "recommend",
        "interval_minutes": 30,
        "goals": ["payments", "reactivation", "retention", "appointments"],
        "max_targets": 5,
        "auto_execute": False,
        "include_suppressed": False,
        "scorecard_window": "28d",
    },
    "runtime_priority": {
        "enabled": True,
        "contact_focus_hours": 72,
        "prioritize_specialist": True,
        "prioritize_tools": True,
        "prioritize_handoffs": True,
        "prioritize_playbooks": True,
    },
}

GROWTH_PRIORITIES: dict[str, dict[str, Any]] = {
    "recover_failed_payment": {"goal": "payments", "weight": 1.3, "recommended_runtime_action": "execute_tool"},
    "recover_pending_payment": {"goal": "payments", "weight": 1.2, "recommended_runtime_action": "execute_tool"},
    "reactivate_stalled_lead": {"goal": "reactivation", "weight": 1.0, "recommended_runtime_action": "trigger_playbook"},
    "drive_repeat_purchase": {"goal": "retention", "weight": 0.95, "recommended_runtime_action": "trigger_playbook"},
    "prevent_churn": {"goal": "retention", "weight": 1.05, "recommended_runtime_action": "trigger_playbook"},
    "confirm_upcoming_appointment": {"goal": "appointments", "weight": 0.9, "recommended_runtime_action": "trigger_playbook"},
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def default_growth_os_config() -> dict[str, Any]:
    return deepcopy(DEFAULT_GROWTH_OS_CONFIG)


def resolve_growth_os_config(bot_config: dict[str, Any] | None = None, *, override: dict[str, Any] | None = None) -> dict[str, Any]:
    config = default_growth_os_config()
    if bot_config:
        config = _deep_merge(config, (bot_config.get("growth_os") or {}))
    if override:
        config = _deep_merge(config, override)
    return config


def ensure_growth_os_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS growth_os_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'recommend',
            status TEXT NOT NULL DEFAULT 'completed',
            goals_json TEXT NOT NULL DEFAULT '[]',
            summary_json TEXT NOT NULL DEFAULT '{}',
            decision_policy_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_growth_os_runs_org ON growth_os_runs(organization_id, bot_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS growth_os_targets (
            id TEXT PRIMARY KEY,
            growth_run_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            candidate_id TEXT,
            proactive_run_id TEXT,
            contact_id TEXT,
            conversation_id TEXT,
            objective TEXT NOT NULL,
            goal TEXT NOT NULL,
            specialist_agent_key TEXT NOT NULL,
            timing_decision TEXT,
            channel TEXT NOT NULL DEFAULT 'whatsapp',
            action_type TEXT NOT NULL DEFAULT 'materialize_playbook',
            priority_score REAL NOT NULL DEFAULT 0,
            expected_value REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'selected',
            scorecard_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (growth_run_id) REFERENCES growth_os_runs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_growth_os_targets_run ON growth_os_targets(growth_run_id, priority_score DESC);
        CREATE INDEX IF NOT EXISTS idx_growth_os_targets_contact ON growth_os_targets(organization_id, contact_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS growth_os_control_states (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL UNIQUE,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            scheduler_enabled INTEGER NOT NULL DEFAULT 1,
            scheduler_mode TEXT NOT NULL DEFAULT 'recommend',
            cycle_interval_minutes INTEGER NOT NULL DEFAULT 30,
            default_goals_json TEXT NOT NULL DEFAULT '[]',
            max_targets INTEGER NOT NULL DEFAULT 5,
            auto_execute INTEGER NOT NULL DEFAULT 0,
            include_suppressed INTEGER NOT NULL DEFAULT 0,
            scorecard_window TEXT NOT NULL DEFAULT '28d',
            prioritize_specialist INTEGER NOT NULL DEFAULT 1,
            prioritize_tools INTEGER NOT NULL DEFAULT 1,
            prioritize_handoffs INTEGER NOT NULL DEFAULT 1,
            prioritize_playbooks INTEGER NOT NULL DEFAULT 1,
            contact_focus_hours INTEGER NOT NULL DEFAULT 72,
            latest_run_id TEXT,
            last_started_at TEXT,
            last_completed_at TEXT,
            next_scheduled_at TEXT,
            last_status TEXT NOT NULL DEFAULT 'idle',
            last_summary_json TEXT NOT NULL DEFAULT '{}',
            config_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_growth_os_control_states_due ON growth_os_control_states(is_enabled, scheduler_enabled, next_scheduled_at);
        """
    )


def _serialize_target(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        **row,
        "scorecard": from_json(row.get("scorecard_json"), {}),
        "evidence": from_json(row.get("evidence_json"), {}),
        "metadata": from_json(row.get("metadata_json"), {}),
    }


def _serialize_run(row: dict[str, Any] | None, *, targets: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        **row,
        "goals": from_json(row.get("goals_json"), []),
        "summary": from_json(row.get("summary_json"), {}),
        "decision_policy": from_json(row.get("decision_policy_json"), {}),
        "metadata": from_json(row.get("metadata_json"), {}),
        "targets": targets or [],
    }


def _serialize_control(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    config = from_json(row.get("config_json"), {})
    return {
        **row,
        "default_goals": from_json(row.get("default_goals_json"), []),
        "last_summary": from_json(row.get("last_summary_json"), {}),
        "config": config,
        "metadata": from_json(row.get("metadata_json"), {}),
    }


def _control_fields_from_config(config: dict[str, Any]) -> dict[str, Any]:
    scheduler = config.get("scheduler") or {}
    runtime_priority = config.get("runtime_priority") or {}
    return {
        "is_enabled": 1 if config.get("enabled", True) else 0,
        "scheduler_enabled": 1 if scheduler.get("enabled", True) else 0,
        "scheduler_mode": str(scheduler.get("mode") or "recommend"),
        "cycle_interval_minutes": max(5, int(scheduler.get("interval_minutes") or 30)),
        "default_goals": list(scheduler.get("goals") or []),
        "max_targets": max(1, int(scheduler.get("max_targets") or 5)),
        "auto_execute": 1 if scheduler.get("auto_execute") else 0,
        "include_suppressed": 1 if scheduler.get("include_suppressed") else 0,
        "scorecard_window": str(scheduler.get("scorecard_window") or "28d"),
        "prioritize_specialist": 1 if runtime_priority.get("prioritize_specialist", True) else 0,
        "prioritize_tools": 1 if runtime_priority.get("prioritize_tools", True) else 0,
        "prioritize_handoffs": 1 if runtime_priority.get("prioritize_handoffs", True) else 0,
        "prioritize_playbooks": 1 if runtime_priority.get("prioritize_playbooks", True) else 0,
        "contact_focus_hours": max(1, int(runtime_priority.get("contact_focus_hours") or 72)),
        "config_json": to_json(config),
    }


def ensure_growth_os_control_state(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    bot_config: dict[str, Any] | None = None,
    override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_growth_os_schema(conn)
    config = resolve_growth_os_config(bot_config, override=override)
    fields = _control_fields_from_config(config)
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
                organization_id,
                fields["is_enabled"],
                fields["scheduler_enabled"],
                fields["scheduler_mode"],
                fields["cycle_interval_minutes"],
                to_json(fields["default_goals"]),
                fields["max_targets"],
                fields["auto_execute"],
                fields["include_suppressed"],
                fields["scorecard_window"],
                fields["prioritize_specialist"],
                fields["prioritize_tools"],
                fields["prioritize_handoffs"],
                fields["prioritize_playbooks"],
                fields["contact_focus_hours"],
                fields["config_json"],
                next_scheduled_at,
                now,
                bot_id,
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
                new_id("growthctl"),
                organization_id,
                bot_id,
                fields["is_enabled"],
                fields["scheduler_enabled"],
                fields["scheduler_mode"],
                fields["cycle_interval_minutes"],
                to_json(fields["default_goals"]),
                fields["max_targets"],
                fields["auto_execute"],
                fields["include_suppressed"],
                fields["scorecard_window"],
                fields["prioritize_specialist"],
                fields["prioritize_tools"],
                fields["prioritize_handoffs"],
                fields["prioritize_playbooks"],
                fields["contact_focus_hours"],
                next_scheduled_at,
                fields["config_json"],
                now,
                now,
            ),
        )
    return _serialize_control(fetch_one(conn, "SELECT * FROM growth_os_control_states WHERE bot_id = ?", (bot_id,))) or {}


def _latest_scorecards(conn, *, organization_id: str, bot_id: str | None, window: str) -> dict[tuple[str, str], dict[str, Any]]:
    if not table_exists(conn, "outcome_scorecard_snapshots"):
        return {}
    rows = fetch_all(
        conn,
        """
        SELECT *
        FROM outcome_scorecard_snapshots
        WHERE organization_id = ? AND (? IS NULL OR bot_id = ?) AND scorecard_window = ?
        ORDER BY computed_at DESC
        """,
        (organization_id, bot_id, bot_id, window),
    )
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("entity_type")), str(row.get("entity_id")))
        if key not in latest:
            latest[key] = {
                **row,
                "metrics": from_json(row.get("metrics_json"), {}),
                "guardrails": from_json(row.get("guardrails_json"), {}),
                "rationale": from_json(row.get("rationale_json"), {}),
            }
    return latest


def _goal_for_objective(objective: str) -> str:
    return str(GROWTH_PRIORITIES.get(objective, {}).get("goal") or "growth")


def _recommended_runtime_action(objective: str) -> str:
    return str(GROWTH_PRIORITIES.get(objective, {}).get("recommended_runtime_action") or "trigger_playbook")


def _score_candidate(candidate: dict[str, Any], *, scorecards: dict[tuple[str, str], dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    objective = str(candidate.get("objective") or "growth")
    base_priority = float(candidate.get("priority_score") or 0.0)
    weight = float(GROWTH_PRIORITIES.get(objective, {}).get("weight") or 1.0)
    goal = _goal_for_objective(objective)

    playbook_scorecard = scorecards.get(("playbook", str(candidate.get("playbook_id") or "")))
    specialist_scorecard = scorecards.get(("specialist_agent", str(candidate.get("specialist_agent_key") or "")))
    channel_scorecard = scorecards.get(("channel", str(candidate.get("channel") or "whatsapp")))

    positive_rate = 0.0
    confidence = 0.0
    revenue_sum = 0.0
    guardrail_penalty = 0.0
    evidence_sources: list[str] = []
    for label, row in (("playbook", playbook_scorecard), ("specialist", specialist_scorecard), ("channel", channel_scorecard)):
        if not row:
            continue
        metrics = row.get("metrics") or {}
        positive_rate += float(metrics.get("positive_outcome_rate") or 0.0) * (0.5 if label == "playbook" else 0.25)
        confidence += float(row.get("confidence_score") or 0.0) * (0.5 if label == "playbook" else 0.25)
        revenue_sum += float(metrics.get("revenue_sum") or 0.0)
        if str(row.get("guardrail_state") or "pass") == "fail":
            guardrail_penalty += 18.0
        evidence_sources.append(label)

    expected_value = round((base_priority * weight) + (positive_rate * 0.35) + min(20.0, revenue_sum / 250.0) + (confidence * 0.08) - guardrail_penalty, 2)
    evidence = {
        "objective": objective,
        "goal": goal,
        "priority_score": base_priority,
        "weight": weight,
        "playbook_scorecard": playbook_scorecard,
        "specialist_scorecard": specialist_scorecard,
        "channel_scorecard": channel_scorecard,
        "evidence_sources": evidence_sources,
        "guardrail_penalty": round(guardrail_penalty, 2),
        "recommended_runtime_action": _recommended_runtime_action(objective),
    }
    return expected_value, evidence


def _timing_decision(candidate: dict[str, Any]) -> str:
    suggested = str(candidate.get("suggested_send_at") or "")
    if not suggested:
        return "send_now"
    return f"send_at:{suggested}"


def _touch_control_state_after_run(conn, *, organization_id: str, bot_id: str, run_id: str, summary: dict[str, Any], status: str = "completed") -> None:
    if not table_exists(conn, "growth_os_control_states"):
        return
    now = utcnow_iso()
    control = fetch_one(conn, "SELECT * FROM growth_os_control_states WHERE bot_id = ?", (bot_id,))
    if not control:
        return
    interval_minutes = int(control.get("cycle_interval_minutes") or 30)
    execute(
        conn,
        """
        UPDATE growth_os_control_states
        SET latest_run_id = ?, last_completed_at = ?, next_scheduled_at = ?, last_status = ?, last_summary_json = ?, updated_at = ?
        WHERE bot_id = ? AND organization_id = ?
        """,
        (run_id, now, add_minutes(now, interval_minutes), status, to_json(summary), now, bot_id, organization_id),
    )


def run_growth_os_cycle(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    goals: list[str] | None = None,
    mode: str = "recommend",
    limit: int = 100,
    max_targets: int = 10,
    auto_execute: bool = False,
    include_suppressed: bool = False,
    scorecard_window: str = "28d",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_growth_os_schema(conn)
    evaluated = evaluate_proactive_candidates(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        persist=True,
        include_suppressed=include_suppressed,
        limit=limit,
        metadata={**(metadata or {}), "source": "growth_os"},
    )
    scorecards = _latest_scorecards(conn, organization_id=organization_id, bot_id=bot_id, window=scorecard_window)
    wanted_goals = set(goals or [])

    ranked: list[dict[str, Any]] = []
    for candidate in list(evaluated.get("items") or []):
        objective = str(candidate.get("objective") or "growth")
        goal = _goal_for_objective(objective)
        if wanted_goals and goal not in wanted_goals and objective not in wanted_goals:
            continue
        expected_value, evidence = _score_candidate(candidate, scorecards=scorecards)
        ranked.append(
            {
                "candidate": candidate,
                "goal": goal,
                "objective": objective,
                "expected_value": expected_value,
                "evidence": evidence,
                "timing_decision": _timing_decision(candidate),
            }
        )

    ranked.sort(key=lambda item: (item["expected_value"], float(item["candidate"].get("priority_score") or 0.0)), reverse=True)
    chosen = ranked[:max_targets]

    now = utcnow_iso()
    run_id = new_id("growthrun")
    summary = {
        "engine_version": "growth_os_v1",
        "candidate_count": len(ranked),
        "selected_count": len(chosen),
        "auto_execute": bool(auto_execute and mode in {"autopilot", "execute"}),
        "top_goals": sorted({item["goal"] for item in chosen}),
    }
    decision_policy = {
        "ranking": ["candidate.priority_score", "playbook.scorecard", "specialist.scorecard", "channel.scorecard"],
        "scorecard_window": scorecard_window,
        "mode": mode,
    }
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

    materialized_runs: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    for item in chosen:
        candidate = item["candidate"]
        materialized = None
        target_status = "selected"
        proactive_run_id = None
        if auto_execute and mode in {"autopilot", "execute"}:
            materialized = materialize_proactive_candidate(
                conn,
                candidate_id=str(candidate.get("id")),
                actor_user_id=None,
                record_exposure=True,
                metadata={"source": "growth_os", "growth_run_id": run_id},
            )
            proactive_run_id = ((materialized or {}).get("run") or {}).get("id")
            target_status = "executed" if proactive_run_id else "selected"
            if materialized:
                materialized_runs.append(materialized)
        target_id = new_id("growthtarget")
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
                run_id,
                organization_id,
                bot_id,
                candidate.get("id"),
                proactive_run_id,
                candidate.get("contact_id"),
                candidate.get("conversation_id"),
                item["objective"],
                item["goal"],
                candidate.get("specialist_agent_key"),
                item["timing_decision"],
                candidate.get("channel") or "whatsapp",
                "materialize_playbook",
                float(candidate.get("priority_score") or 0.0),
                float(item["expected_value"] or 0.0),
                target_status,
                to_json(
                    {
                        "playbook": item["evidence"].get("playbook_scorecard"),
                        "specialist": item["evidence"].get("specialist_scorecard"),
                        "channel": item["evidence"].get("channel_scorecard"),
                    }
                ),
                to_json(item["evidence"]),
                to_json({"candidate": candidate, "materialized": materialized}),
                now,
                now,
            ),
        )
        target_rows.append(fetch_one(conn, "SELECT * FROM growth_os_targets WHERE id = ?", (target_id,)) or {})

    run_row = fetch_one(conn, "SELECT * FROM growth_os_runs WHERE id = ?", (run_id,)) or {}
    result = {
        "run": _serialize_run(run_row, targets=[_serialize_target(row) for row in target_rows]),
        "candidate_count": len(ranked),
        "selected_count": len(target_rows),
        "materialized_count": len(materialized_runs),
        "top_candidates": [item["candidate"] for item in chosen],
        "materialized_runs": materialized_runs,
    }
    _touch_control_state_after_run(conn, organization_id=organization_id, bot_id=bot_id, run_id=run_id, summary=summary)
    return result


def _row_due(now_iso: str, row: dict[str, Any]) -> bool:
    next_scheduled_at = row.get("next_scheduled_at")
    if not next_scheduled_at:
        return True
    next_dt = parse_iso(str(next_scheduled_at))
    return bool(next_dt is None or next_dt <= parse_iso(now_iso))


def list_due_growth_os_controls(conn, *, limit: int = 25) -> list[dict[str, Any]]:
    ensure_growth_os_schema(conn)
    now = utcnow_iso()
    bots = fetch_all(
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
    due: list[dict[str, Any]] = []
    for bot in bots:
        if int(bot.get("ai_paused") or 0) == 1:
            continue
        bot_config = from_json(bot.get("config_draft_json"), {})
        state = ensure_growth_os_control_state(conn, organization_id=bot["organization_id"], bot_id=bot["id"], bot_config=bot_config)
        if not state.get("is_enabled") or not state.get("scheduler_enabled"):
            continue
        if _row_due(now, state):
            due.append(state)
        if len(due) >= limit:
            break
    return due


def run_growth_os_master_scheduler(conn, *, limit: int = 25) -> list[dict[str, Any]]:
    ensure_growth_os_schema(conn)
    due_controls = list_due_growth_os_controls(conn, limit=limit)
    processed: list[dict[str, Any]] = []
    for state in due_controls:
        now = utcnow_iso()
        execute(
            conn,
            "UPDATE growth_os_control_states SET last_started_at = ?, last_status = 'running', updated_at = ? WHERE bot_id = ?",
            (now, now, state["bot_id"]),
        )
        try:
            result = run_growth_os_cycle(
                conn,
                organization_id=state["organization_id"],
                bot_id=state["bot_id"],
                goals=state.get("default_goals") or [],
                mode=str(state.get("scheduler_mode") or "recommend"),
                max_targets=int(state.get("max_targets") or 5),
                auto_execute=bool(state.get("auto_execute")),
                include_suppressed=bool(state.get("include_suppressed")),
                scorecard_window=str(state.get("scorecard_window") or "28d"),
                metadata={"source": "growth_os_master_scheduler", "scheduler": True},
            )
            run_id = ((result.get("run") or {}).get("id"))
            execute(
                conn,
                """
                UPDATE growth_os_control_states
                SET latest_run_id = ?, last_completed_at = ?, next_scheduled_at = ?, last_status = 'completed', last_summary_json = ?, updated_at = ?
                WHERE bot_id = ?
                """,
                (
                    run_id,
                    now,
                    add_minutes(now, int(state.get("cycle_interval_minutes") or 30)),
                    to_json(
                        {
                            "selected_count": result.get("selected_count"),
                            "materialized_count": result.get("materialized_count"),
                            "candidate_count": result.get("candidate_count"),
                        }
                    ),
                    now,
                    state["bot_id"],
                ),
            )
            processed.append(
                {
                    "bot_id": state["bot_id"],
                    "organization_id": state["organization_id"],
                    "status": "completed",
                    "run_id": run_id,
                    "selected_count": result.get("selected_count"),
                    "materialized_count": result.get("materialized_count"),
                }
            )
        except Exception as exc:
            execute(
                conn,
                """
                UPDATE growth_os_control_states
                SET last_completed_at = ?, next_scheduled_at = ?, last_status = 'failed',
                    metadata_json = ?, updated_at = ?
                WHERE bot_id = ?
                """,
                (
                    now,
                    add_minutes(now, int(state.get("cycle_interval_minutes") or 30)),
                    to_json({"last_error": str(exc)}),
                    now,
                    state["bot_id"],
                ),
            )
            processed.append(
                {
                    "bot_id": state["bot_id"],
                    "organization_id": state["organization_id"],
                    "status": "failed",
                    "error": str(exc),
                }
            )
    return processed


def active_growth_os_focus(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    contact_id: str | None = None,
    conversation_id: str | None = None,
    bot_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_growth_os_schema(conn)
    control = ensure_growth_os_control_state(conn, organization_id=organization_id, bot_id=bot_id, bot_config=bot_config)
    config = control.get("config") or resolve_growth_os_config(bot_config)
    runtime_priority = (config.get("runtime_priority") or {})
    if not config.get("enabled", True) or not runtime_priority.get("enabled", True):
        return {"enabled": False, "focus_target": None, "scope": "disabled", "recommended_runtime_action": None}

    lookback_hours = max(1, int(control.get("contact_focus_hours") or runtime_priority.get("contact_focus_hours") or 72))
    cutoff = utcnow() - __import__("datetime").timedelta(hours=lookback_hours)
    cutoff_iso = cutoff.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _fetch(where_sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        return fetch_one(
            conn,
            f"""
            SELECT * FROM growth_os_targets
            WHERE organization_id = ? AND bot_id = ? AND created_at >= ? AND status IN ('selected','executed') {where_sql}
            ORDER BY expected_value DESC, priority_score DESC, created_at DESC
            LIMIT 1
            """,
            (organization_id, bot_id, cutoff_iso, *params),
        )

    row = None
    scope = "global"
    if contact_id and conversation_id:
        row = _fetch("AND contact_id = ? AND conversation_id = ?", (contact_id, conversation_id))
        scope = "conversation" if row else scope
    if row is None and contact_id:
        row = _fetch("AND contact_id = ?", (contact_id,))
        scope = "contact" if row else scope
    if row is None:
        row = _fetch("", ())
    target = _serialize_target(row)
    if not target:
        return {"enabled": True, "focus_target": None, "scope": scope, "recommended_runtime_action": None, "config": config}

    objective = str(target.get("objective") or "growth")
    recommended_runtime_action = _recommended_runtime_action(objective)
    return {
        "enabled": True,
        "scope": scope,
        "focus_target": target,
        "objective": objective,
        "goal": target.get("goal"),
        "preferred_specialist": target.get("specialist_agent_key"),
        "preferred_channel": target.get("channel") or "whatsapp",
        "timing_decision": target.get("timing_decision"),
        "recommended_runtime_action": recommended_runtime_action,
        "config": config,
    }


def apply_growth_os_specialist_focus(route: dict[str, Any], *, focus: dict[str, Any] | None) -> dict[str, Any]:
    updated = dict(route or {})
    target = (focus or {}).get("focus_target") or {}
    if not target:
        return updated
    config = ((focus or {}).get("config") or {}).get("runtime_priority") or {}
    if not config.get("prioritize_specialist", True):
        return updated
    specialist = target.get("specialist_agent_key")
    if specialist:
        updated["specialist_agent_key"] = specialist
        updated["growth_os_priority_applied"] = True
        updated["growth_os_focus_goal"] = target.get("goal")
    return updated


def apply_growth_os_execution_focus(plan: dict[str, Any], *, focus: dict[str, Any] | None) -> dict[str, Any]:
    updated = dict(plan or {})
    target = (focus or {}).get("focus_target") or {}
    if not target:
        return updated
    rendering_hints = dict(updated.get("rendering_hints") or {})
    response_contract = dict(updated.get("response_contract") or {})
    planner_notes = dict(updated.get("planner_notes") or {})
    response_contract["target_channel"] = target.get("channel") or response_contract.get("target_channel") or "whatsapp"
    rendering_hints["prefer_growth_objective"] = target.get("objective")
    planner_notes["growth_os_focus"] = {
        "goal": target.get("goal"),
        "objective": target.get("objective"),
        "timing_decision": target.get("timing_decision"),
        "specialist_agent_key": target.get("specialist_agent_key"),
    }
    updated["response_contract"] = response_contract
    updated["rendering_hints"] = rendering_hints
    updated["planner_notes"] = planner_notes
    return updated


def growth_os_overview(conn, *, organization_id: str, bot_id: str, scorecard_window: str = "28d", bot_config: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_growth_os_schema(conn)
    control = ensure_growth_os_control_state(conn, organization_id=organization_id, bot_id=bot_id, bot_config=bot_config)
    scorecards = _latest_scorecards(conn, organization_id=organization_id, bot_id=bot_id, window=scorecard_window)
    latest_run = fetch_one(
        conn,
        "SELECT * FROM growth_os_runs WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 1",
        (organization_id, bot_id),
    )
    latest_targets = fetch_all(
        conn,
        "SELECT * FROM growth_os_targets WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 20",
        (organization_id, bot_id),
    )
    proactive_runs = list_proactive_runs(conn, organization_id=organization_id, bot_id=bot_id, limit=20)
    counts_by_goal: dict[str, int] = defaultdict(int)
    for row in latest_targets:
        counts_by_goal[str(row.get("goal") or "growth")] += 1
    return {
        "engine_version": "growth_os_v1",
        "organization_id": organization_id,
        "bot_id": bot_id,
        "scorecard_window": scorecard_window,
        "control": control,
        "latest_run": _serialize_run(latest_run, targets=[_serialize_target(row) for row in latest_targets[:10]]) if latest_run else None,
        "goal_distribution": dict(sorted(counts_by_goal.items())),
        "scorecard_summary": {
            "playbooks": [row for (entity_type, _), row in scorecards.items() if entity_type == "playbook"][:5],
            "specialists": [row for (entity_type, _), row in scorecards.items() if entity_type == "specialist_agent"][:5],
            "channels": [row for (entity_type, _), row in scorecards.items() if entity_type == "channel"][:5],
        },
        "recent_proactive_runs": proactive_runs[:10],
        "active_focus": active_growth_os_focus(conn, organization_id=organization_id, bot_id=bot_id, bot_config=bot_config),
    }


def list_growth_os_runs(conn, *, organization_id: str, bot_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    ensure_growth_os_schema(conn)
    if bot_id:
        rows = fetch_all(conn, "SELECT * FROM growth_os_runs WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, bot_id, limit))
    else:
        rows = fetch_all(conn, "SELECT * FROM growth_os_runs WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, limit))
    items: list[dict[str, Any]] = []
    for row in rows:
        targets = fetch_all(conn, "SELECT * FROM growth_os_targets WHERE growth_run_id = ? ORDER BY priority_score DESC, created_at ASC", (row["id"],))
        items.append(_serialize_run(row, targets=[_serialize_target(target) for target in targets]))
    return items
