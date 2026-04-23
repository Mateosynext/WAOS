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

class OptimizerDecisionsSupportMixin:
    def _is_material_delta(self, winner: dict[str, Any], loser: dict[str, Any], *, min_delta: float) -> bool:
        delta = float(winner.get("outcome_score") or 0) - float(loser.get("outcome_score") or 0)
        if delta < float(min_delta or 1.5):
            return False
        if winner.get("guardrail_state") == "fail":
            return False
        return True

    def _experiment_mode(self, requested_mode: str, *, winner: dict[str, Any], loser: dict[str, Any]) -> str:
        if requested_mode != "auto":
            return requested_mode
        if float(winner.get("confidence_score") or 0) >= 80 and loser.get("guardrail_state") == "fail":
            return "ab"
        return "shadow"

    def _create_proposal(self, conn, *, cycle_id: str, target_name: str, organization_id: str, bot_id: str | None, winner: dict[str, Any], loser: dict[str, Any], delta: float, user_id: str | None) -> dict[str, Any]:
        now = utcnow_iso()
        proposal_id = new_id("optimizer_proposal")
        proposal_kind = "promote_and_degrade"
        summary = self._proposal_summary(target_name, winner, loser, delta)
        rationale = self._rationale(target_name, winner, loser, delta)
        change_set = self._change_set(target_name, winner, loser, delta)
        execute(
            conn,
            """
            INSERT INTO optimizer_proposals (
                id, organization_id, bot_id, cycle_id, target_name, proposal_kind, status,
                champion_entity_type, champion_entity_id, challenger_entity_type, challenger_entity_id,
                summary, rationale_json, change_set_json, evidence_json, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'proposed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal_id,
                organization_id,
                bot_id,
                cycle_id,
                target_name,
                proposal_kind,
                winner.get("entity_type"),
                winner.get("entity_id"),
                loser.get("entity_type"),
                loser.get("entity_id"),
                summary,
                to_json(rationale),
                to_json(change_set),
                to_json({"winner": self._serialize_scorecard(winner), "loser": self._serialize_scorecard(loser)}),
                user_id,
                now,
                now,
            ),
        )
        self._record_change_audit(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            proposal_id=proposal_id,
            event_type="proposal_created",
            action="optimizer.proposal.created",
            payload={"target_name": target_name, "summary": summary, "rationale": rationale, "change_set": change_set},
            user_id=user_id,
        )
        return fetch_one(conn, "SELECT * FROM optimizer_proposals WHERE id = ?", (proposal_id,)) or {}

    def _create_experiment(self, conn, *, proposal: dict[str, Any], winner: dict[str, Any], loser: dict[str, Any], mode: str, user_id: str | None, auto_start: bool) -> dict[str, Any] | None:
        if not proposal:
            return None
        now = utcnow_iso()
        experiment_id = new_id("optimizer_experiment")
        experiment_key = f"optimizer:{proposal['target_name']}:{proposal['id']}"
        rollout = 0 if mode == "shadow" else 20
        status = "running" if auto_start else "planned"
        execute(
            conn,
            """
            INSERT INTO optimizer_experiments (
                id, organization_id, bot_id, proposal_id, experiment_key, mode, status,
                champion_entity_type, champion_entity_id, candidate_entity_type, candidate_entity_id,
                rollout_percentage, guardrails_json, evidence_json, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                proposal.get("organization_id"),
                proposal.get("bot_id"),
                proposal.get("id"),
                experiment_key,
                mode,
                status,
                loser.get("entity_type"),
                loser.get("entity_id"),
                winner.get("entity_type"),
                winner.get("entity_id"),
                rollout,
                to_json(self._guardrails_for_experiment(winner, loser, mode)),
                to_json({"winner": self._serialize_scorecard(winner), "loser": self._serialize_scorecard(loser)}),
                user_id,
                now,
                now,
            ),
        )
        self._record_change_audit(
            conn,
            organization_id=proposal.get("organization_id"),
            bot_id=proposal.get("bot_id"),
            proposal_id=proposal.get("id"),
            experiment_id=experiment_id,
            event_type="experiment_created",
            action="optimizer.experiment.created",
            payload={"mode": mode, "rollout_percentage": rollout, "experiment_key": experiment_key},
            user_id=user_id,
        )
        return fetch_one(conn, "SELECT * FROM optimizer_experiments WHERE id = ?", (experiment_id,)) or {}

    def _should_auto_promote(self, winner: dict[str, Any], loser: dict[str, Any], *, min_confidence: float, min_delta: float) -> bool:
        delta = float(winner.get("outcome_score") or 0) - float(loser.get("outcome_score") or 0)
        return (
            winner.get("guardrail_state") == "pass"
            and float(winner.get("confidence_score") or 0) >= float(min_confidence or 70)
            and delta >= float(min_delta or 1.5)
            and loser.get("guardrail_state") in {"warn", "fail"}
        )

    def _should_auto_degrade(self, loser: dict[str, Any]) -> bool:
        return loser.get("guardrail_state") == "fail" or float(loser.get("outcome_score") or 0) < 0

    def _apply_control_state(self, conn, *, proposal: dict[str, Any], winner: dict[str, Any], loser: dict[str, Any], action: str, user_id: str | None, reason_code: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        now = utcnow_iso()
        state_key = proposal.get("target_name")
        previous = fetch_one(
            conn,
            "SELECT * FROM optimizer_control_states WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') AND target_name = ?",
            (proposal.get("organization_id"), proposal.get("bot_id"), state_key),
        )
        new_state = {
            "target_name": state_key,
            "preferred_entity": {"entity_type": winner.get("entity_type"), "entity_id": winner.get("entity_id")},
            "degraded_entity": {"entity_type": loser.get("entity_type"), "entity_id": loser.get("entity_id")},
            "action": action,
            "applied_at": now,
        }
        if previous:
            execute(
                conn,
                "UPDATE optimizer_control_states SET current_state_json = ?, last_decision_action = ?, updated_at = ? WHERE id = ?",
                (to_json(new_state), action, now, previous["id"]),
            )
            state_row_id = previous["id"]
        else:
            state_row_id = new_id("optimizer_state")
            execute(
                conn,
                "INSERT INTO optimizer_control_states (id, organization_id, bot_id, target_name, current_state_json, last_decision_action, updated_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (state_row_id, proposal.get("organization_id"), proposal.get("bot_id"), state_key, to_json(new_state), action, now, now),
            )

        decision_id = new_id("outcome_decision")
        execute(
            conn,
            """
            INSERT INTO outcome_optimization_decisions (
                id, organization_id, bot_id, entity_type, entity_id, action, decision_source, reason_code, status,
                previous_state_json, new_state_json, evidence_snapshot_json, created_by, created_at, applied_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'waos_optimizer', ?, 'applied', ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                proposal.get("organization_id"),
                proposal.get("bot_id"),
                winner.get("entity_type") or proposal.get("champion_entity_type"),
                winner.get("entity_id") or proposal.get("champion_entity_id"),
                action,
                reason_code,
                to_json(self._serialize_state(previous) if previous else {}),
                to_json(new_state),
                to_json(evidence or {"proposal": self._serialize_proposal(proposal), "winner": self._serialize_scorecard(winner), "loser": self._serialize_scorecard(loser)}),
                user_id,
                now,
                now,
            ),
        )
        execute(conn, "UPDATE optimizer_proposals SET status = ?, applied_decision_id = ?, updated_at = ? WHERE id = ?", ("applied", decision_id, now, proposal["id"]))
        self._record_change_audit(
            conn,
            organization_id=proposal.get("organization_id"),
            bot_id=proposal.get("bot_id"),
            proposal_id=proposal.get("id"),
            decision_id=decision_id,
            event_type="decision_applied",
            action=f"optimizer.{action}.applied",
            payload={"new_state": new_state, "reason_code": reason_code, "state_row_id": state_row_id},
            user_id=user_id,
        )
        return fetch_one(conn, "SELECT * FROM outcome_optimization_decisions WHERE id = ?", (decision_id,)) or {}

    def _experiment_verdict(self, *, candidate: dict[str, Any] | None, champion: dict[str, Any] | None, shadow: dict[str, Any], min_confidence: float, min_shadow_runs: int) -> dict[str, Any]:
        candidate = candidate or {}
        champion = champion or {}
        candidate_score = float(candidate.get("outcome_score") or 0)
        champion_score = float(champion.get("outcome_score") or 0)
        candidate_conf = float(candidate.get("confidence_score") or 0)
        if shadow.get("runs", 0) < min_shadow_runs:
            return {"status": "running", "action": "hold"}
        if candidate.get("guardrail_state") == "fail":
            return {"status": "stopped", "action": "degrade"}
        if candidate_score > champion_score and candidate_conf >= min_confidence and shadow.get("agree_rate", 0) >= 60:
            return {"status": "winner_selected", "action": "promote"}
        if champion and champion.get("guardrail_state") == "pass":
            return {"status": "completed", "action": "hold"}
        return {"status": "running", "action": "hold"}

    def _proposal_summary(self, target_name: str, winner: dict[str, Any], loser: dict[str, Any], delta: float) -> str:
        return (
            f"Promote {winner.get('entity_type')}:{winner.get('entity_id')} and degrade "
            f"{loser.get('entity_type')}:{loser.get('entity_id')} for {target_name} (delta {delta:+.2f})."
        )

    def _rationale(self, target_name: str, winner: dict[str, Any], loser: dict[str, Any], delta: float) -> dict[str, Any]:
        return {
            "optimizer": "waos_optimizer_v1",
            "target_name": target_name,
            "winner_outcome_score": float(winner.get("outcome_score") or 0),
            "winner_confidence": float(winner.get("confidence_score") or 0),
            "winner_guardrail": winner.get("guardrail_state"),
            "loser_outcome_score": float(loser.get("outcome_score") or 0),
            "loser_confidence": float(loser.get("confidence_score") or 0),
            "loser_guardrail": loser.get("guardrail_state"),
            "delta": delta,
            "guardrails": self._guardrails_for_experiment(winner, loser, "auto"),
        }

    def _change_set(self, target_name: str, winner: dict[str, Any], loser: dict[str, Any], delta: float) -> dict[str, Any]:
        rollout = 100 if self._should_auto_promote(winner, loser, min_confidence=70, min_delta=1.5) else 20
        return {
            "target_name": target_name,
            "preferred_entity_type": winner.get("entity_type"),
            "preferred_entity_id": winner.get("entity_id"),
            "degraded_entity_type": loser.get("entity_type"),
            "degraded_entity_id": loser.get("entity_id"),
            "rollout_percentage": rollout,
            "routing_weight_shift": 25 if target_name in {"routing_specialist", "playbook_proactive", "handoff_policy"} else None,
            "template_swap": target_name in {"cta", "collections_template", "reactivation_template", "scheduling_template"},
            "shadow_first": rollout < 100,
            "delta": delta,
        }

    def _guardrails_for_experiment(self, winner: dict[str, Any], loser: dict[str, Any], mode: str) -> dict[str, Any]:
        return {
            "mode": mode,
            "winner_guardrail_state": winner.get("guardrail_state"),
            "loser_guardrail_state": loser.get("guardrail_state"),
            "block_if_candidate_fails": True,
            "require_positive_delta": True,
            "require_confidence_above": 70,
            "shadow_agree_rate_min": 60,
        }

    def _record_change_audit(self, conn, *, organization_id: str | None, bot_id: str | None, proposal_id: str | None = None, experiment_id: str | None = None, decision_id: str | None = None, event_type: str, action: str, payload: dict[str, Any], user_id: str | None) -> None:
        if not table_exists(conn, "optimizer_change_audits"):
            return
        execute(
            conn,
            "INSERT INTO optimizer_change_audits (id, organization_id, bot_id, proposal_id, experiment_id, decision_id, event_type, payload_json, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id("optimizer_audit"), organization_id, bot_id, proposal_id, experiment_id, decision_id, event_type, to_json(payload), user_id, utcnow_iso()),
        )
        create_audit_log(
            conn,
            organization_id=organization_id,
            actor_user_id=None,
            actor_type="system",
            entity_type="waos_optimizer",
            entity_id=proposal_id or experiment_id or decision_id,
            action=action,
            metadata=payload,
        )
