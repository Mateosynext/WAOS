from __future__ import annotations

from typing import Any

from ..utils import from_json


def serialize_exposure(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {**row, "metadata": from_json(row.get("metadata_json"), {})}


def serialize_event(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {**row, "value": from_json(row.get("value_json"), {})}


def serialize_scorecard(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        **row,
        "metrics": from_json(row.get("metrics_json"), {}),
        "guardrails": from_json(row.get("guardrails_json"), {}),
        "rationale": from_json(row.get("rationale_json"), {}),
    }


def serialize_decision(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        **row,
        "previous_state": from_json(row.get("previous_state_json"), {}),
        "new_state": from_json(row.get("new_state_json"), {}),
        "evidence_snapshot": from_json(row.get("evidence_snapshot_json"), {}),
    }


def serialize_attribution_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "value": from_json(row.get("value_json"), {}),
        "details": from_json(row.get("details_json"), {}),
    }
