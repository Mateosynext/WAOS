from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException

from ..contracts import ok
from ..db import execute, fetch_all, fetch_one, table_exists
from ..repositories import create_audit_log
from ..security import ensure_org_access
from ..utils import from_json, new_id, to_json, utcnow_iso
from .support import require_permission
from .uow import UnitOfWork

DEFAULT_TARGETS: dict[str, tuple[str, ...]] = {
    "prompt_base": ("prompt_version", "prompt_run", "specialist_prompt"),
    "response_variant": ("response_variant",),
    "cta": ("template", "template_version", "nba_policy"),
    "timing": ("timing_policy", "channel"),
    "routing_specialist": ("specialist_agent", "routing_rule", "agent_routing_run"),
    "playbook_proactive": ("playbook", "playbook_version"),
    "handoff_policy": ("handoff", "escalation_policy", "policy_profile"),
    "preferred_channel": ("channel",),
    "collections_template": ("template", "template_version"),
    "reactivation_template": ("template", "template_version"),
    "scheduling_template": ("template", "template_version"),
}

AUTO_ENTITY_TYPES = {entity for items in DEFAULT_TARGETS.values() for entity in items}


class OptimizerApplicationService:
    def overview(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> dict[str, Any]:
        self._authorize(user, organization_id)
        latest_cycle = fetch_one(
            uow.conn,
            "SELECT * FROM optimizer_cycles WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY created_at DESC LIMIT 1",
            (organization_id, bot_id),
        ) if table_exists(uow.conn, "optimizer_cycles") else None
        proposals = fetch_all(
            uow.conn,
            "SELECT * FROM optimizer_proposals WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY created_at DESC LIMIT 50",
            (organization_id, bot_id),
        ) if table_exists(uow.conn, "optimizer_proposals") else []
        experiments = fetch_all(
            uow.conn,
            "SELECT * FROM optimizer_experiments WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY updated_at DESC LIMIT 50",
            (organization_id, bot_id),
        ) if table_exists(uow.conn, "optimizer_experiments") else []
        states = fetch_all(
            uow.conn,
            "SELECT * FROM optimizer_control_states WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') ORDER BY updated_at DESC LIMIT 50",
            (organization_id, bot_id),
        ) if table_exists(uow.conn, "optimizer_control_states") else []
        return ok({
            "optimizer": "waos_optimizer_v1",
            "organization_id": organization_id,
            "bot_id": bot_id,
            "latest_cycle": self._serialize_cycle(latest_cycle),
            "proposals": [self._serialize_proposal(item) for item in proposals],
            "experiments": [self._serialize_experiment(item) for item in experiments],
            "control_states": [self._serialize_state(item) for item in states],
        })

    def list_proposals(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, status: str | None, user: dict) -> dict[str, Any]:
        self._authorize(user, organization_id)
        where = ["organization_id = ?"]
        params: list[Any] = [organization_id]
        if bot_id:
            where.append("bot_id = ?")
            params.append(bot_id)
        if status:
            where.append("status = ?")
            params.append(status)
        rows = fetch_all(
            uow.conn,
            f"SELECT * FROM optimizer_proposals WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 200",
            tuple(params),
        ) if table_exists(uow.conn, "optimizer_proposals") else []
        return ok({"items": [self._serialize_proposal(item) for item in rows], "count": len(rows)})

    def run_cycle(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        self._authorize(user, payload.organization_id)
        targets = payload.targets or list(DEFAULT_TARGETS.keys())
        scorecard_window = payload.scorecard_window or "28d"
        now = utcnow_iso()
        cycle_id = new_id("optimizer_cycle")
        execute(
            uow.conn,
            "INSERT INTO optimizer_cycles (id, organization_id, bot_id, mode, targets_json, scorecard_window, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?, ?)",
            (cycle_id, payload.organization_id, payload.bot_id, payload.mode, to_json(targets), scorecard_window, user.get("id"), now, now),
        )

        scorecards = self._load_scorecards(
            uow.conn,
            organization_id=payload.organization_id,
            bot_id=payload.bot_id,
            entity_types=self._entity_types_for_targets(targets),
            scorecard_window=scorecard_window,
        )
        grouped = self._group_scorecards(scorecards)
        proposals: list[dict[str, Any]] = []
        experiments: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        summary = {"winners": 0, "losers": 0, "proposals": 0, "experiments": 0, "auto_promoted": 0, "auto_degraded": 0}

        for target_name in targets:
            peer_rows = [row for entity_type in DEFAULT_TARGETS.get(target_name, ()) for row in grouped.get(entity_type, [])]
            if len(peer_rows) < 2:
                continue
            peer_rows = sorted(peer_rows, key=self._scorecard_rank, reverse=True)
            winner = peer_rows[0]
            loser = peer_rows[-1]
            delta = round(float(winner.get("outcome_score") or 0) - float(loser.get("outcome_score") or 0), 4)
            if not self._is_material_delta(winner, loser, min_delta=payload.min_delta):
                continue
            summary["winners"] += 1
            summary["losers"] += 1
            proposal = self._create_proposal(
                uow.conn,
                cycle_id=cycle_id,
                target_name=target_name,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                winner=winner,
                loser=loser,
                delta=delta,
                user_id=user.get("id"),
            )
            proposals.append(proposal)
            summary["proposals"] += 1

            experiment = self._create_experiment(
                uow.conn,
                proposal=proposal,
                winner=winner,
                loser=loser,
                mode=self._experiment_mode(payload.mode, winner=winner, loser=loser),
                user_id=user.get("id"),
                auto_start=payload.auto_shadow or payload.auto_ab,
            )
            if experiment:
                experiments.append(experiment)
                summary["experiments"] += 1

            if payload.auto_promote and self._should_auto_promote(winner, loser, min_confidence=payload.min_confidence, min_delta=payload.min_delta):
                decision = self._apply_control_state(
                    uow.conn,
                    proposal=proposal,
                    winner=winner,
                    loser=loser,
                    action="promote",
                    user_id=user.get("id"),
                    reason_code="optimizer.auto_promote",
                )
                decisions.append(decision)
                summary["auto_promoted"] += 1
            elif payload.auto_degrade and self._should_auto_degrade(loser):
                decision = self._apply_control_state(
                    uow.conn,
                    proposal=proposal,
                    winner=winner,
                    loser=loser,
                    action="degrade",
                    user_id=user.get("id"),
                    reason_code="optimizer.auto_degrade",
                )
                decisions.append(decision)
                summary["auto_degraded"] += 1

        cycle_status = "completed"
        execute(
            uow.conn,
            "UPDATE optimizer_cycles SET status = ?, summary_json = ?, updated_at = ? WHERE id = ?",
            (cycle_status, to_json(summary), utcnow_iso(), cycle_id),
        )
        create_audit_log(
            uow.conn,
            organization_id=payload.organization_id,
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="optimizer_cycle",
            entity_id=cycle_id,
            action="optimizer.cycle.executed",
            metadata={
                "bot_id": payload.bot_id,
                "targets": targets,
                "scorecard_window": scorecard_window,
                "summary": summary,
            },
        )
        uow.commit()
        cycle = fetch_one(uow.conn, "SELECT * FROM optimizer_cycles WHERE id = ?", (cycle_id,))
        return ok({
            "cycle": self._serialize_cycle(cycle),
            "proposals": [self._serialize_proposal(item) for item in proposals],
            "experiments": [self._serialize_experiment(item) for item in experiments],
            "decisions": [self._serialize_decision(item) for item in decisions],
            "summary": summary,
        })

    def evaluate_experiments(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        self._authorize(user, payload.organization_id)
        rows = fetch_all(
            uow.conn,
            "SELECT * FROM optimizer_experiments WHERE organization_id = ? AND status IN ('running', 'planned') ORDER BY updated_at DESC LIMIT 100",
            (payload.organization_id,),
        ) if table_exists(uow.conn, "optimizer_experiments") else []
        evaluated: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        for row in rows:
            candidate = self._find_scorecard(uow.conn, payload.organization_id, row.get("candidate_entity_type"), row.get("candidate_entity_id"), payload.scorecard_window)
            champion = self._find_scorecard(uow.conn, payload.organization_id, row.get("champion_entity_type"), row.get("champion_entity_id"), payload.scorecard_window)
            shadow_runs = self._shadow_signal(uow.conn, payload.organization_id, row.get("experiment_key"))
            evidence = {
                "candidate": self._serialize_scorecard(candidate),
                "champion": self._serialize_scorecard(champion),
                "shadow": shadow_runs,
            }
            verdict = self._experiment_verdict(candidate=candidate, champion=champion, shadow=shadow_runs, min_confidence=payload.min_confidence, min_shadow_runs=payload.min_shadow_runs)
            execute(
                uow.conn,
                "UPDATE optimizer_experiments SET status = ?, evidence_json = ?, updated_at = ? WHERE id = ?",
                (verdict["status"], to_json(evidence), utcnow_iso(), row["id"]),
            )
            refreshed = fetch_one(uow.conn, "SELECT * FROM optimizer_experiments WHERE id = ?", (row["id"],))
            evaluated.append(refreshed or row)
            if payload.auto_apply and verdict["action"] in {"promote", "degrade"}:
                proposal = fetch_one(uow.conn, "SELECT * FROM optimizer_proposals WHERE id = ?", (row.get("proposal_id"),))
                if proposal:
                    decision = self._apply_control_state(
                        uow.conn,
                        proposal=proposal,
                        winner=candidate or {},
                        loser=champion or {},
                        action=verdict["action"],
                        user_id=user.get("id"),
                        reason_code=f"optimizer.{verdict['action']}.from_experiment",
                        evidence=evidence,
                    )
                    decisions.append(decision)
        uow.commit()
        return ok({
            "items": [self._serialize_experiment(item) for item in evaluated],
            "decisions": [self._serialize_decision(item) for item in decisions],
            "count": len(evaluated),
        })

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


optimizer_service = OptimizerApplicationService()
