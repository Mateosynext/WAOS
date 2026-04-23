from __future__ import annotations

from typing import Any

from ..db import fetch_all, fetch_one, table_exists
from ..utils import from_json
from .outcomes_presenters import serialize_scorecard


def serialize_tool_execution_run(conn, row: dict[str, Any]) -> dict[str, Any]:
    steps = fetch_all(conn, "SELECT * FROM tool_execution_step_logs WHERE execution_run_id = ? ORDER BY created_at ASC", (row["id"],))
    closed_loop = None
    if table_exists(conn, "outcome_exposures") and table_exists(conn, "outcome_attribution_facts") and table_exists(conn, "outcome_scorecard_snapshots"):
        exposure = fetch_one(conn, "SELECT * FROM outcome_exposures WHERE tool_execution_run_id = ? ORDER BY sent_at DESC LIMIT 1", (row["id"],))
        auto_events = fetch_all(conn, "SELECT * FROM outcome_events WHERE source_execution_run_id = ? ORDER BY event_timestamp DESC", (row["id"],)) if table_exists(conn, "outcome_events") else []
        attribution_rows = fetch_all(
            conn,
            """
            SELECT af.*, oe.event_name, oe.event_category, oe.event_timestamp, oe.value_number, oe.value_text, oe.value_json
            FROM outcome_attribution_facts af
            JOIN outcome_events oe ON oe.id = af.outcome_event_id
            JOIN outcome_exposures ox ON ox.id = af.exposure_id
            WHERE ox.tool_execution_run_id = ?
            ORDER BY oe.event_timestamp DESC, af.created_at DESC
            LIMIT 25
            """,
            (row["id"],),
        )
        action_scorecard = fetch_one(conn, "SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND entity_type = 'tool_action' AND entity_id = ? ORDER BY computed_at DESC LIMIT 1", (row["organization_id"], row["action"]))
        provider_scorecard = fetch_one(conn, "SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND entity_type = 'tool_provider' AND entity_id = ? ORDER BY computed_at DESC LIMIT 1", (row["organization_id"], row.get("provider") or "waos"))
        policy_scorecard = fetch_one(conn, "SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND entity_type = 'policy_profile' AND entity_id = ? ORDER BY computed_at DESC LIMIT 1", (row["organization_id"], row.get("policy_profile_key"))) if row.get("policy_profile_key") else None
        closed_loop = {
            "exposure": {**exposure, "metadata": from_json((exposure or {}).get("metadata_json"), {})} if exposure else None,
            "auto_events": [{**event, "value": from_json(event.get("value_json"), {})} for event in auto_events],
            "linked_attribution": [{**item, "value": from_json(item.get("value_json"), {}), "details": from_json(item.get("details_json"), {})} for item in attribution_rows],
            "action_scorecard": serialize_scorecard(action_scorecard) if action_scorecard else None,
            "provider_scorecard": serialize_scorecard(provider_scorecard) if provider_scorecard else None,
            "policy_scorecard": serialize_scorecard(policy_scorecard) if policy_scorecard else None,
        }
    return {
        **row,
        "request": from_json(row.get("request_json"), {}),
        "normalized_payload": from_json(row.get("normalized_payload_json"), {}),
        "validation": from_json(row.get("validation_json"), {}),
        "target_ref": from_json(row.get("target_ref_json"), {}),
        "result": from_json(row.get("result_json"), {}),
        "error": from_json(row.get("error_json"), {}),
        "metadata": from_json(row.get("metadata_json"), {}),
        "policy": from_json(row.get("policy_json"), {}),
        "requires_confirmation": bool(row.get("requires_confirmation")),
        "steps": [{**step, "payload": from_json(step.get("payload_json"), {})} for step in steps],
        "closed_loop": closed_loop,
    }
