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

class OptimizerQueriesSupportMixin:
    def _authorize(self, user: dict, organization_id: str) -> None:
        ensure_org_access(user, organization_id)
        require_permission(user, organization_id, "conversation.manage")

    def _entity_types_for_targets(self, targets: list[str]) -> list[str]:
        entity_types: list[str] = []
        for target in targets:
            entity_types.extend(DEFAULT_TARGETS.get(target, ()))
        return sorted(set(entity_types))

    def _load_scorecards(self, conn, *, organization_id: str, bot_id: str | None, entity_types: list[str], scorecard_window: str) -> list[dict[str, Any]]:
        if not entity_types or not table_exists(conn, "outcome_scorecard_snapshots"):
            return []
        placeholders = ", ".join("?" for _ in entity_types)
        params: list[Any] = [organization_id, scorecard_window, *entity_types]
        sql = f"SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND scorecard_window = ? AND entity_type IN ({placeholders})"
        if bot_id:
            sql += " AND COALESCE(bot_id, '') = COALESCE(?, '')"
            params.append(bot_id)
        sql += " ORDER BY computed_at DESC"
        rows = fetch_all(conn, sql, tuple(params))
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (row["entity_type"], row["entity_id"])
            latest.setdefault(key, row)
        return list(latest.values())

    def _group_scorecards(self, rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row.get("entity_type"))].append(row)
        return grouped

    def _scorecard_rank(self, row: dict[str, Any]) -> tuple[float, float, float]:
        return (
            float(row.get("outcome_score") or 0),
            float(row.get("confidence_score") or 0),
            float(row.get("primary_metric_value") or 0),
        )

    def _find_scorecard(self, conn, organization_id: str, entity_type: str | None, entity_id: str | None, scorecard_window: str) -> dict[str, Any] | None:
        if not entity_type or not entity_id or not table_exists(conn, "outcome_scorecard_snapshots"):
            return None
        return fetch_one(
            conn,
            "SELECT * FROM outcome_scorecard_snapshots WHERE organization_id = ? AND entity_type = ? AND entity_id = ? AND scorecard_window = ? ORDER BY computed_at DESC LIMIT 1",
            (organization_id, entity_type, entity_id, scorecard_window),
        )

    def _shadow_signal(self, conn, organization_id: str, experiment_key: str | None) -> dict[str, Any]:
        if not experiment_key or not table_exists(conn, "shadow_runs"):
            return {"runs": 0, "agree_rate": 0.0, "winner": None}
        rows = fetch_all(conn, "SELECT verdict FROM shadow_runs WHERE organization_id = ? AND experiment_key = ? ORDER BY created_at DESC LIMIT 200", (organization_id, experiment_key))
        total = len(rows)
        agrees = sum(1 for row in rows if str(row.get("verdict") or "").lower() in {"agree", "pass", "candidate_better"})
        return {"runs": total, "agree_rate": round((agrees / total) * 100, 2) if total else 0.0, "winner": "candidate" if agrees > (total / 2) else None}
