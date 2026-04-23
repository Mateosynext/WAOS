from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from ..db import execute, fetch_all
from ..utils import new_id, parse_iso, to_json, utcnow, utcnow_iso
from .outcomes_policy import guardrail_state, recommendation
from .outcomes_presenters import serialize_attribution_row, serialize_decision, serialize_event, serialize_exposure, serialize_scorecard


OUTCOME_BASE_SCORES: dict[str, float] = {
    "appointment_scheduled": 8.0,
    "appointment_confirmed": 10.0,
    "payment_started": 9.0,
    "payment_completed": 18.0,
    "appointment_attended": 14.0,
    "attended": 14.0,
    "no_show": -12.0,
    "appointment_no_show": -12.0,
    "reactivated": 11.0,
    "sale_closed": 25.0,
    "human_handoff_resolved": 6.0,
    "appointment_rescheduled": 5.0,
    "lead_stage_progressed": 7.0,
    "receipt_sent": 2.0,
}

POSITIVE_OUTCOMES = {
    "appointment_scheduled",
    "appointment_confirmed",
    "payment_started",
    "payment_completed",
    "appointment_attended",
    "attended",
    "reactivated",
    "sale_closed",
    "human_handoff_resolved",
    "appointment_rescheduled",
    "lead_stage_progressed",
    "receipt_sent",
}

NEGATIVE_OUTCOMES = {"no_show", "appointment_no_show", "lost", "refund", "handoff_failed"}

ENTITY_FIELDS: list[tuple[str, str]] = [
    ("prompt_run", "prompt_run_id"),
    ("prompt_version", "prompt_version_id"),
    ("flow", "flow_id"),
    ("flow_version", "flow_version_id"),
    ("template", "template_id"),
    ("template_version", "template_version_id"),
    ("routing_rule", "routing_rule_id"),
    ("decision_path", "decision_path_id"),
    ("timing_policy", "timing_policy_id"),
    ("tone_policy", "tone_policy_id"),
    ("nba_policy", "nba_policy_id"),
    ("escalation_policy", "escalation_policy_id"),
    ("playbook", "playbook_id"),
    ("playbook_version", "playbook_version_id"),
    ("handoff", "handoff_id"),
    ("specialist_agent", "specialist_agent_key"),
    ("specialist_prompt", "specialist_prompt_id"),
    ("agent_routing_run", "agent_routing_run_id"),
    ("policy_profile", "policy_profile_key"),
    ("operator_user", "operator_user_id"),
    ("response_variant", "assigned_variant"),
    ("channel", "channel"),
    ("source_type", "source_type"),
]

WINDOWS_TO_DAYS = {"7d": 7, "28d": 28, "90d": 90}


class OutcomesSupport:
    def _build_dedupe_key(self, payload: dict[str, Any]) -> str:
        basis = {
            "organization_id": payload.get("organization_id"),
            "bot_id": payload.get("bot_id"),
            "conversation_id": payload.get("conversation_id"),
            "contact_id": payload.get("contact_id"),
            "lead_id": payload.get("lead_id"),
            "appointment_id": payload.get("appointment_id"),
            "payment_id": payload.get("payment_id"),
            "event_name": payload.get("event_name"),
            "event_category": payload.get("event_category"),
            "event_timestamp": payload.get("event_timestamp") or utcnow_iso(),
            "source_system": payload.get("source_system"),
            "external_event_id": payload.get("external_event_id"),
            "value_number": payload.get("value_number"),
            "value_text": payload.get("value_text"),
            "value": payload.get("value") or {},
        }
        raw = json.dumps(basis, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _materialize_attribution_for_event(self, conn, *, event_row: dict[str, Any], attribution_window_hours: int) -> dict[str, Any]:
        execute(conn, "DELETE FROM outcome_attribution_facts WHERE outcome_event_id = ?", (event_row["id"],))
        exposures = self._find_candidate_exposures(conn, event_row=event_row, attribution_window_hours=attribution_window_hours)
        if not exposures:
            return {
                "model": "last_touch",
                "matched_exposures": 0,
                "facts_created": 0,
                "event_id": event_row["id"],
            }
        winning = exposures[0]
        contribution_value = self._event_score(event_row)
        created = 0
        now = utcnow_iso()
        for entity_type, entity_id in self._entities_for_exposure(winning):
            execute(
                conn,
                """
                INSERT INTO outcome_attribution_facts (
                    id, organization_id, outcome_event_id, exposure_id, entity_type, entity_id, metric_name,
                    attribution_model, attribution_window_hours, attribution_weight, contribution_value,
                    details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    new_id("outcome_attr"),
                    event_row["organization_id"],
                    event_row["id"],
                    winning["id"],
                    entity_type,
                    entity_id,
                    event_row["event_name"],
                    "last_touch",
                    attribution_window_hours,
                    contribution_value,
                    to_json(
                        {
                            "event_name": event_row["event_name"],
                            "event_category": event_row["event_category"],
                            "exposure_source_type": winning.get("source_type"),
                            "channel": winning.get("channel"),
                            "vertical": winning.get("vertical") or event_row.get("vertical"),
                            "funnel_stage": winning.get("funnel_stage") or event_row.get("funnel_stage"),
                        }
                    ),
                    now,
                ),
            )
            created += 1
        return {
            "model": "last_touch",
            "matched_exposures": len(exposures),
            "facts_created": created,
            "event_id": event_row["id"],
            "winning_exposure_id": winning["id"],
        }

    def _find_candidate_exposures(self, conn, *, event_row: dict[str, Any], attribution_window_hours: int) -> list[dict[str, Any]]:
        from datetime import datetime, timedelta

        event_ts = parse_iso(event_row.get("event_timestamp")) or utcnow()
        created_ts = parse_iso(event_row.get("created_at")) or event_ts
        delayed_ingestion_cap = event_ts + timedelta(hours=6)
        upper_bound_dt = max(event_ts, min(created_ts, delayed_ingestion_cap))
        upper_bound_iso = upper_bound_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        conditions = ["organization_id = ?", "sent_at <= ?"]
        params: list[Any] = [event_row["organization_id"], upper_bound_iso]
        if event_row.get("bot_id"):
            conditions.append("(bot_id = ? OR bot_id IS NULL)")
            params.append(event_row["bot_id"])
        identifiers: list[tuple[str, Any]] = []
        for key in ("conversation_id", "contact_id", "lead_id", "appointment_id", "payment_id"):
            value = event_row.get(key)
            if value:
                identifiers.append((key, value))
        if not identifiers:
            return []
        conditions.append("(" + " OR ".join(f"{field} = ?" for field, _ in identifiers) + ")")
        params.extend(value for _, value in identifiers)
        since_ts = event_ts.timestamp() - (attribution_window_hours * 3600)
        since_iso = datetime.fromtimestamp(since_ts, tz=event_ts.tzinfo).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        conditions.append("sent_at >= ?")
        params.append(since_iso)
        rows = fetch_all(
            conn,
            f"SELECT * FROM outcome_exposures WHERE {' AND '.join(conditions)} LIMIT 100",
            tuple(params),
        )

        def _rank(exposure: dict[str, Any]) -> tuple[float, float, float]:
            score = 0.0
            if event_row.get("source_execution_run_id") and exposure.get("tool_execution_run_id") == event_row.get("source_execution_run_id"):
                score += 5000.0
            for field, weight in (("payment_id", 1000.0), ("appointment_id", 800.0), ("lead_id", 600.0), ("contact_id", 400.0), ("conversation_id", 200.0)):
                if event_row.get(field) and exposure.get(field) == event_row.get(field):
                    score += weight
            if event_row.get("bot_id") and exposure.get("bot_id") == event_row.get("bot_id"):
                score += 50.0
            sent_at = parse_iso(exposure.get("sent_at")) or utcnow()
            created_at = parse_iso(exposure.get("created_at")) or sent_at
            return (score, sent_at.timestamp(), created_at.timestamp())

        rows.sort(key=_rank, reverse=True)
        return rows

    def _recompute_scorecards(self, conn, *, organization_id: str, bot_id: str | None, windows: list[str], attribution_window_hours: int) -> dict[str, Any]:
        valid_windows = [window for window in windows if window in WINDOWS_TO_DAYS]
        if not valid_windows:
            valid_windows = ["7d", "28d"]
        computed_at = utcnow_iso()
        created_snapshots = 0
        for window in valid_windows:
            days = WINDOWS_TO_DAYS[window]
            execute(
                conn,
                "DELETE FROM outcome_scorecard_snapshots WHERE organization_id = ? AND ((bot_id IS NULL AND ? IS NULL) OR bot_id = ?) AND scorecard_window = ?",
                (organization_id, bot_id, bot_id, window),
            )
            since_iso = utcnow().replace(microsecond=0).isoformat().replace("+00:00", "Z")
            from datetime import timedelta
            since_dt = utcnow() - timedelta(days=days)
            since_iso = since_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            facts = fetch_all(
                conn,
                """
                SELECT af.*, oe.event_name, oe.event_category, oe.value_number, oe.bot_id
                FROM outcome_attribution_facts af
                JOIN outcome_events oe ON oe.id = af.outcome_event_id
                WHERE af.organization_id = ? AND oe.event_timestamp >= ? AND (? IS NULL OR oe.bot_id = ?)
                """,
                (organization_id, since_iso, bot_id, bot_id),
            )
            exposures = fetch_all(
                conn,
                """
                SELECT *
                FROM outcome_exposures
                WHERE organization_id = ? AND sent_at >= ? AND (? IS NULL OR bot_id = ? OR bot_id IS NULL)
                """,
                (organization_id, since_iso, bot_id, bot_id),
            )
            traffic: dict[tuple[str, str], int] = defaultdict(int)
            for exposure in exposures:
                seen_entities = set(self._entities_for_exposure(exposure))
                for key in seen_entities:
                    traffic[key] += 1
            metrics_by_entity: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {
                "outcome_events": 0,
                "positive_outcomes": 0,
                "negative_outcomes": 0,
                "contribution_sum": 0.0,
                "revenue_sum": 0.0,
                "by_event": defaultdict(int),
            })
            for fact in facts:
                key = (fact["entity_type"], fact["entity_id"])
                metrics = metrics_by_entity[key]
                metrics["outcome_events"] += 1
                metrics["contribution_sum"] += float(fact.get("contribution_value") or 0)
                event_name = str(fact.get("event_name") or fact.get("metric_name") or "unknown")
                metrics["by_event"][event_name] += 1
                if event_name in POSITIVE_OUTCOMES or float(fact.get("contribution_value") or 0) > 0:
                    metrics["positive_outcomes"] += 1
                if event_name in NEGATIVE_OUTCOMES or float(fact.get("contribution_value") or 0) < 0:
                    metrics["negative_outcomes"] += 1
                if event_name in {"payment_completed", "sale_closed"} and fact.get("value_number") is not None:
                    metrics["revenue_sum"] += float(fact.get("value_number") or 0)
            all_entities = set(traffic.keys()) | set(metrics_by_entity.keys())
            for entity_type, entity_id in all_entities:
                metrics = metrics_by_entity[(entity_type, entity_id)]
                traffic_count = int(traffic.get((entity_type, entity_id), 0))
                positive_rate = round((metrics["positive_outcomes"] / traffic_count) * 100, 2) if traffic_count else 0.0
                outcome_score = round(metrics["contribution_sum"] / max(1, traffic_count), 4)
                confidence_score = round(min(100.0, (traffic_count * 12.0) + (metrics["outcome_events"] * 8.0)), 2)
                guardrail = self._guardrail_state(traffic_count=traffic_count, metrics=metrics)
                recommendation_value = self._recommendation(outcome_score=outcome_score, confidence_score=confidence_score, guardrail_state=guardrail)
                execute(
                    conn,
                    """
                    INSERT INTO outcome_scorecard_snapshots (
                        id, organization_id, bot_id, entity_type, entity_id, scorecard_window, computed_at,
                        traffic_count, primary_metric, primary_metric_value, outcome_score, confidence_score,
                        guardrail_state, metrics_json, guardrails_json, recommendation, rationale_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id("outcome_scorecard"),
                        organization_id,
                        bot_id,
                        entity_type,
                        entity_id,
                        window,
                        computed_at,
                        traffic_count,
                        "positive_outcome_rate",
                        positive_rate,
                        outcome_score,
                        confidence_score,
                        guardrail,
                        to_json({
                            "outcome_events": metrics["outcome_events"],
                            "positive_outcomes": metrics["positive_outcomes"],
                            "negative_outcomes": metrics["negative_outcomes"],
                            "positive_outcome_rate": positive_rate,
                            "revenue_sum": round(metrics["revenue_sum"], 2),
                            "by_event": dict(sorted(metrics["by_event"].items())),
                        }),
                        to_json({
                            "low_traffic": traffic_count < 3,
                            "negative_outcomes": metrics["negative_outcomes"],
                            "recommendation_blocked": guardrail == "fail",
                        }),
                        recommendation_value,
                        to_json({
                            "contribution_sum": round(metrics["contribution_sum"], 4),
                            "attribution_window_hours": attribution_window_hours,
                        }),
                    ),
                )
                created_snapshots += 1
        return {
            "organization_id": organization_id,
            "bot_id": bot_id,
            "windows": valid_windows,
            "scorecards_created": created_snapshots,
            "computed_at": computed_at,
        }

    def _guardrail_state(self, *, traffic_count: int, metrics: dict[str, Any]) -> str:
        return guardrail_state(traffic_count=traffic_count, metrics=metrics)

    def _recommendation(self, *, outcome_score: float, confidence_score: float, guardrail_state: str) -> str:
        return recommendation(outcome_score=outcome_score, confidence_score=confidence_score, guardrail_state_value=guardrail_state)

    def _event_score(self, event_row: dict[str, Any]) -> float:
        event_name = str(event_row.get("event_name") or "").strip().lower()
        base = OUTCOME_BASE_SCORES.get(event_name)
        if base is None:
            value_number = event_row.get("value_number")
            if value_number is not None:
                return float(value_number)
            return 1.0
        value_number = event_row.get("value_number")
        if value_number is not None and event_name in {"payment_completed", "sale_closed"}:
            return round(base + min(float(value_number) / 1000.0, 20.0), 4)
        return base

    def _entities_for_exposure(self, exposure: dict[str, Any]) -> list[tuple[str, str]]:
        entities: list[tuple[str, str]] = []
        for entity_type, field_name in ENTITY_FIELDS:
            value = exposure.get(field_name)
            if value:
                entities.append((entity_type, str(value)))
        if exposure.get("vertical"):
            entities.append(("vertical", str(exposure["vertical"])))
        if exposure.get("funnel_stage"):
            entities.append(("funnel_stage", str(exposure["funnel_stage"])))
        if exposure.get("tool_execution_run_id"):
            entities.append(("tool_execution_run", str(exposure["tool_execution_run_id"])))
        if exposure.get("tool_action"):
            entities.append(("tool_action", str(exposure["tool_action"])))
        if exposure.get("tool_adapter_key"):
            entities.append(("tool_adapter", str(exposure["tool_adapter_key"])))
        if exposure.get("tool_provider"):
            entities.append(("tool_provider", str(exposure["tool_provider"])))
        if exposure.get("policy_profile_key"):
            entities.append(("policy_profile", str(exposure["policy_profile_key"])))
        return entities

    def _serialize_exposure(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        return serialize_exposure(row)

    def _serialize_event(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        return serialize_event(row)

    def _serialize_scorecard(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        return serialize_scorecard(row)

    def _serialize_decision(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        return serialize_decision(row)

    def _list_attribution_rows(self, conn, *, organization_id: str, bot_id: str | None = None, entity_type: str | None = None, entity_id: str | None = None, outcome_event_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where = ["af.organization_id = ?"]
        params: list[Any] = [organization_id]
        if bot_id:
            where.append("(oe.bot_id = ? OR ox.bot_id = ?)")
            params.extend([bot_id, bot_id])
        if entity_type:
            where.append("af.entity_type = ?")
            params.append(entity_type)
        if entity_id:
            where.append("af.entity_id = ?")
            params.append(entity_id)
        if outcome_event_id:
            where.append("af.outcome_event_id = ?")
            params.append(outcome_event_id)
        params.append(int(limit))
        rows = fetch_all(
            conn,
            f"""
            SELECT af.*, oe.event_name, oe.event_category, oe.event_timestamp, oe.value_number, oe.value_text,
                   oe.value_json, ox.source_type, ox.channel, ox.prompt_run_id, ox.prompt_version_id,
                   ox.flow_id, ox.flow_version_id, ox.template_id, ox.template_version_id, ox.routing_rule_id,
                   ox.decision_path_id, ox.handoff_id, ox.handoff_kind, ox.specialist_agent_key,
                   ox.specialist_agent_version, ox.specialist_prompt_id, ox.intent_family,
                   ox.agent_routing_run_id, ox.operator_user_id,
                   ox.vertical, ox.funnel_stage, ox.tool_execution_run_id, ox.tool_action,
                   ox.tool_adapter_key, ox.tool_provider, oe.source_execution_run_id,
                   oe.source_tool_action, oe.source_tool_provider
            FROM outcome_attribution_facts af
            JOIN outcome_events oe ON oe.id = af.outcome_event_id
            JOIN outcome_exposures ox ON ox.id = af.exposure_id
            WHERE {' AND '.join(where)}
            ORDER BY oe.event_timestamp DESC, af.created_at DESC
            LIMIT ?
            """,
            tuple(params),
        )
        return [serialize_attribution_row(row) for row in rows]
