from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from .repositories.growth_os import (
    create_growth_run as repo_create_growth_run,
    create_growth_target as repo_create_growth_target,
    find_focus_target as repo_find_focus_target,
    get_latest_growth_run as repo_get_latest_growth_run,
    list_active_bot_rows as repo_list_active_bot_rows,
    list_candidate_target_rows as repo_list_candidate_target_rows,
    list_growth_run_rows as repo_list_growth_run_rows,
    list_growth_targets_for_run as repo_list_growth_targets_for_run,
    load_latest_scorecards as repo_load_latest_scorecards,
    mark_control_state_completed as repo_mark_control_state_completed,
    mark_control_state_failed as repo_mark_control_state_failed,
    mark_control_state_running as repo_mark_control_state_running,
    touch_control_state_after_run as repo_touch_control_state_after_run,
    upsert_growth_control_state,
)
from .proactive_reasoning_runtime import evaluate_proactive_candidates, list_proactive_runs, materialize_proactive_candidate
from .utils import from_json, parse_iso, to_json, utcnow, utcnow_iso
from .runtime_schema_guards import assert_schema_ready


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
    assert_schema_ready(
        conn,
        owner="growth_os_runtime",
        tables=("growth_os_runs", "growth_os_targets", "growth_os_control_states"),
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
    return _serialize_control(upsert_growth_control_state(conn, organization_id=organization_id, bot_id=bot_id, fields=fields)) or {}


def _latest_scorecards(conn, *, organization_id: str, bot_id: str | None, window: str) -> dict[tuple[str, str], dict[str, Any]]:
    rows = repo_load_latest_scorecards(conn, organization_id=organization_id, bot_id=bot_id, window=window)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("entity_type")), str(row.get("entity_id")))
        if key not in latest:
            latest[key] = {
                **row,
                "metrics": from_json(row.get("metrics_json"), {}),
                "recs": from_json(row.get("recommendations_json"), []),
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
    repo_touch_control_state_after_run(conn, organization_id=organization_id, bot_id=bot_id, run_id=run_id, summary=summary, status=status)


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
    run_row = repo_create_growth_run(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        mode=mode,
        goals=goals or [],
        summary=summary,
        decision_policy=decision_policy,
        metadata=metadata,
    )
    run_id = run_row["id"]

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
        target_rows.append(
            repo_create_growth_target(
                conn,
                growth_run_id=run_id,
                organization_id=organization_id,
                bot_id=bot_id,
                candidate=candidate,
                proactive_run_id=proactive_run_id,
                objective=item["objective"],
                goal=item["goal"],
                timing_decision=item["timing_decision"],
                expected_value=float(item["expected_value"] or 0.0),
                status=target_status,
                evidence=item["evidence"],
                materialized=materialized,
            )
        )

    run_row = repo_get_latest_growth_run(conn, organization_id=organization_id, bot_id=bot_id) or {}
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
    bots = repo_list_active_bot_rows(conn, limit=limit)
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
        repo_mark_control_state_running(conn, bot_id=state["bot_id"], started_at=now)
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
            repo_mark_control_state_completed(
                conn,
                bot_id=state["bot_id"],
                run_id=run_id,
                completed_at=now,
                cycle_interval_minutes=int(state.get("cycle_interval_minutes") or 30),
                summary={
                    "selected_count": result.get("selected_count"),
                    "materialized_count": result.get("materialized_count"),
                    "candidate_count": result.get("candidate_count"),
                },
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
            conn.rollback()
            repo_mark_control_state_failed(
                conn,
                bot_id=state["bot_id"],
                failed_at=now,
                cycle_interval_minutes=int(state.get("cycle_interval_minutes") or 30),
                error=str(exc),
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

    row = None
    scope = "global"
    if contact_id and conversation_id:
        row = repo_find_focus_target(conn, organization_id=organization_id, bot_id=bot_id, cutoff_iso=cutoff_iso, contact_id=contact_id, conversation_id=conversation_id)
        scope = "conversation" if row else scope
    if row is None and contact_id:
        row = repo_find_focus_target(conn, organization_id=organization_id, bot_id=bot_id, cutoff_iso=cutoff_iso, contact_id=contact_id)
        scope = "contact" if row else scope
    if row is None:
        row = repo_find_focus_target(conn, organization_id=organization_id, bot_id=bot_id, cutoff_iso=cutoff_iso)
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
    latest_run = repo_get_latest_growth_run(conn, organization_id=organization_id, bot_id=bot_id)
    latest_targets = repo_list_candidate_target_rows(conn, organization_id=organization_id, bot_id=bot_id, limit=20)
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
    rows = repo_list_growth_run_rows(conn, organization_id=organization_id, bot_id=bot_id, limit=limit)
    items: list[dict[str, Any]] = []
    for row in rows:
        targets = repo_list_growth_targets_for_run(conn, growth_run_id=row["id"])
        items.append(_serialize_run(row, targets=[_serialize_target(target) for target in targets]))
    return items
