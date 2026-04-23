from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..db import execute, fetch_all, fetch_one, table_exists
from ..repositories import create_audit_log
from ..security import ensure_org_access
from ..utils import from_json, new_id, to_json, utcnow_iso
from .optimizer_constants import DEFAULT_TARGETS
from .support import require_permission

class OptimizerPresentersMixin:
    def _serialize_scorecard(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            **row,
            "metrics": from_json(row.get("metrics_json"), {}),
            "guardrails": from_json(row.get("guardrails_json"), {}),
            "rationale": from_json(row.get("rationale_json"), {}),
        }

    def _serialize_cycle(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {**row, "targets": from_json(row.get("targets_json"), []), "summary": from_json(row.get("summary_json"), {})}

    def _serialize_proposal(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            **row,
            "rationale": from_json(row.get("rationale_json"), {}),
            "change_set": from_json(row.get("change_set_json"), {}),
            "evidence": from_json(row.get("evidence_json"), {}),
        }

    def _serialize_experiment(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            **row,
            "guardrails": from_json(row.get("guardrails_json"), {}),
            "evidence": from_json(row.get("evidence_json"), {}),
        }

    def _serialize_state(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {**row, "current_state": from_json(row.get("current_state_json"), {})}

    def _serialize_decision(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        return {
            **row,
            "previous_state": from_json(row.get("previous_state_json"), {}),
            "new_state": from_json(row.get("new_state_json"), {}),
            "evidence_snapshot": from_json(row.get("evidence_snapshot_json"), {}),
        }
