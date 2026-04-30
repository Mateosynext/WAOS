from __future__ import annotations


def evaluate_go_live_readiness(
    *,
    wizard: dict,
    dry_run_result: dict,
    validation_snapshot: dict,
    simulation_report: dict,
    knowledge_plan: dict,
    integration_status: dict | None = None,
    whatsapp_status: dict | None = None,
    template_status: dict | None = None,
    tool_execution_plan: dict | None = None,
    policy_pack: dict | None = None,
    human_handoff_config: dict | None = None,
) -> dict:
    blockers: list[str] = []
    warnings: list[str] = []
    confirmations: list[dict] = []
    production_risks: list[str] = []

    if not dry_run_result.get("apply_ready") and not validation_snapshot.get("apply_ready"):
        blockers.append("dry_run_not_apply_ready")
    if simulation_report.get("blocking_failures"):
        blockers.append("blocking_simulation_failures")
    if not human_handoff_config:
        confirmations.append(
            {
                "field_key": "human_handoff_destination",
                "label": "Destino humano",
                "reason": "handoff requerido para casos sensibles",
                "status": "pending",
            }
        )
        blockers.append("missing_handoff")

    for fact in knowledge_plan.get("missing_facts", []):
        field_key = str(fact).strip().replace(" ", "_")
        confirmations.append(
            {
                "field_key": field_key,
                "label": fact,
                "reason": "la IA no debe inventarlo",
                "status": "pending",
            }
        )
        production_risks.append(f"missing_confirmed_fact:{field_key}")

    if not whatsapp_status:
        warnings.append("whatsapp_status_not_confirmed")

    production_risks = blockers + warnings + production_risks
    status = "blocked" if blockers else "ready_with_warnings" if warnings or confirmations else "ready"
    score = max(0, 100 - 25 * len(blockers) - 5 * len(warnings) - 3 * len(confirmations))
    return {
        "status": status,
        "score": score,
        "blockers": blockers,
        "warnings": warnings,
        "human_confirmations_required": confirmations,
        "production_risks": production_risks,
        "recommended_next_action": "resolve_blockers" if blockers else ("confirm_pending_facts" if confirmations else "prepare_apply"),
        "can_apply": status != "blocked",
        "can_publish": status == "ready",
        "canary_required": True,
    }
