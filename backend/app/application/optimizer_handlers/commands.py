from __future__ import annotations

from typing import Any

from ...contracts import ok
from ...db import execute, fetch_all, fetch_one, table_exists
from ...repositories import create_audit_log
from ...utils import new_id, to_json, utcnow_iso
from ..uow import UnitOfWork
from ..optimizer_support import DEFAULT_TARGETS

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

