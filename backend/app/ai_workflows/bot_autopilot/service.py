from __future__ import annotations

from typing import Any

from ...db import DBConnection, get_connection
from ...vertical_onboarding_ai_prefill import generate_ai_wizard_autopilot
from ...ai_platform.model_router import model_router
from ..persistence import (
    create_run,
    get_run,
    list_human_confirmations,
    patch_run_result,
    record_cost,
    record_event,
    require_run,
    save_go_live_readiness,
    save_json_artifact,
    save_simulation_report,
    update_run,
    upsert_human_confirmation,
    upsert_step,
)
from ..cost_governor import CostGovernor, CostLimitExceeded
from .schemas import BotAutopilotRequest, BusinessProfile
from .intensity import get_intensity_profile
from .vertical_intelligence import build_vertical_intelligence_pack, detect_vertical
from ..agent_policy_pack.generator import generate_agent_policy_pack
from ..knowledge_plan.generator import generate_knowledge_plan
from ..whatsapp_pack.generator import generate_whatsapp_production_pack
from ..tool_plan.generator import generate_tool_execution_plan
from ..simulation.simulator import run_simulation_suite
from ..go_live.readiness import evaluate_go_live_readiness
from ..go_live.release import prepare_release_plan
from ..learning.service import generate_learning_recommendations

TERMINAL_STATUSES = {"completed", "completed_partial", "failed", "cancelled", "paused_cost_limit"}


def _commit_best_effort(conn: DBConnection) -> None:
    """Persist workflow telemetry between steps so SSE/polling can recover mid-run.

    The background worker owns its connection, so committing after each durable
    step is safe and prevents a long transaction from hiding progress events
    until the very end. If a request-scoped UoW passes a connection here, the
    worst case is a harmless early commit of workflow telemetry.
    """
    try:
        conn.commit()
    except Exception:
        pass


class WorkflowCancelled(RuntimeError):
    pass


def _check_cancelled(conn: DBConnection, run_id: str) -> None:
    current = get_run(conn, run_id)
    if current and current.get("status") == "cancelled":
        record_event(conn, run_id, "workflow.cancelled", "Workflow cancelado antes de continuar")
        raise WorkflowCancelled("workflow cancelled")


def _user_id(user: Any) -> str | None:
    if isinstance(user, dict):
        return str(user.get("id") or "") or None
    return str(getattr(user, "id", "") or "") or None


def _artifact_meta(task: str) -> dict[str, Any]:
    selected = model_router.select(task)
    return {
        "provider": selected.provider,
        "model": selected.model,
        "fallback_model": selected.fallback_model,
        "prompt_version": selected.prompt_version,
        "latency_ms": selected.latency_ms,
        "cost_estimate_usd": selected.cost_estimate_usd,
        "cache_hit": selected.cache_hit,
        "fallback_used": selected.fallback_used,
    }


def _charge(conn: DBConnection, governor: CostGovernor, run: dict, operation: str, amount: float) -> None:
    governor.charge(operation, amount)
    meta = _artifact_meta(operation)
    record_cost(
        conn,
        organization_id=run.get("organization_id"),
        bot_id=run.get("bot_id"),
        run_id=run["id"],
        provider=meta["provider"],
        model=meta["model"],
        operation=operation,
        estimated_cost_usd=amount,
        latency_ms=int(meta.get("latency_ms") or 0),
    )


def _record_step(conn: DBConnection, run_id: str, key: str, label: str, progress: int, output: dict, *, task: str | None = None) -> None:
    payload = dict(output or {})
    if task:
        payload.setdefault("ai_meta", _artifact_meta(task))
    upsert_step(conn, run_id, key, label, "completed", output_json=payload)
    record_event(conn, run_id, key if "." in key else f"{key}.completed", label, progress, payload_json=payload)
    patch_run_result(conn, run_id, key, payload)
    update_run(conn, run_id, current_step=key, progress=progress)
    _commit_best_effort(conn)


def start_bot_autopilot_run(conn: DBConnection, payload: BotAutopilotRequest, user: Any = None) -> dict:
    run = create_run(
        conn,
        organization_id=payload.organization_id,
        bot_id=payload.bot_id,
        user_id=_user_id(user),
        prompt=payload.user_description,
        intensity=payload.intensity,
        config=payload.model_dump(),
    )
    record_event(
        conn,
        run["id"],
        "workflow.started",
        "WAOS AI Production Autopilot v3 blindado iniciado",
        1,
        payload_json={"intensity": payload.intensity, "streaming": "real_sse"},
    )
    update_run(conn, run["id"], status="running", current_step="workflow.started", progress=1)
    _commit_best_effort(conn)
    return {
        "run_id": run["id"],
        "wizard_id": run.get("wizard_id"),
        "bot_id": run.get("bot_id"),
        "status": "running",
        "progress": 1,
        "next_action": {"type": "stream_events", "events_url": f"/api/v1/ai/workflows/{run['id']}/events"},
    }


def run_bot_autopilot(conn: DBConnection, payload: BotAutopilotRequest, user: Any = None) -> dict:
    starter = start_bot_autopilot_run(conn, payload, user=user)
    return execute_bot_autopilot_run(conn, starter["run_id"], user=user)


def run_bot_autopilot_background(run_id: str, user: Any = None) -> None:
    with get_connection() as conn:
        try:
            execute_bot_autopilot_run(conn, run_id, user=user)
        except Exception as exc:
            # Last-resort guard. execute_bot_autopilot_run normally records failures and returns,
            # but this keeps background tasks from rolling back all failure telemetry.
            try:
                update_run(conn, run_id, status="failed", error_json={"message": str(exc), "background_guard": True})
                record_event(conn, run_id, "workflow.failed", str(exc), payload_json={"error": str(exc), "background_guard": True})
                _commit_best_effort(conn)
            except Exception:
                pass


def execute_bot_autopilot_run(conn: DBConnection, run_id: str, user: Any = None) -> dict:
    run = require_run(conn, run_id)
    payload = BotAutopilotRequest.model_validate(run.get("config_json") or {})
    profile = get_intensity_profile(payload.intensity)
    governor = CostGovernor(payload.intensity, payload.max_cost_usd)
    update_run(conn, run_id, status="running")
    try:
        _check_cancelled(conn, run_id)
        _charge(conn, governor, run, "intent_normalization", 0.02)
        normalized = {"description": payload.user_description.strip(), "language": payload.language, "timezone": payload.timezone}
        _record_step(conn, run_id, "intent.normalized", "Descripcion normalizada", 5, normalized, task="intent_normalization")

        _check_cancelled(conn, run_id)
        _charge(conn, governor, run, "vertical_detection", 0.03)
        vertical = detect_vertical(payload.user_description, payload.vertical_id)
        vertical.update({"subvertical": payload.subvertical or vertical.get("subvertical"), "primary_objective": payload.primary_objective or vertical.get("primary_objective")})
        _record_step(conn, run_id, "vertical.detected", "Vertical detectada", 10, vertical, task="vertical_detection")

        _check_cancelled(conn, run_id)
        _charge(conn, governor, run, "business_profile", 0.04)
        business = BusinessProfile(
            vertical_id=vertical["vertical_id"],
            subvertical=vertical.get("subvertical"),
            primary_objective=vertical.get("primary_objective", "agendar"),
            language=payload.language or "es",
            timezone=payload.timezone or "America/Mexico_City",
            services=["servicio principal"],
            constraints=["no inventar precios", "no inventar horarios", "no inventar promociones"],
            facts_to_confirm=["precios reales", "horarios reales", "destino humano", "politicas legales"],
        ).model_dump()
        _record_step(conn, run_id, "business_profile.generated", "Business profile generado", 15, business, task="business_profile")

        _check_cancelled(conn, run_id)
        _charge(conn, governor, run, "wizard_generation", 0.18)
        try:
            legacy = generate_ai_wizard_autopilot(
                conn,
                organization_id=payload.organization_id,
                bot_id=payload.bot_id,
                user_description=payload.user_description,
                vertical_id=vertical["vertical_id"],
                subvertical=vertical.get("subvertical"),
                primary_objective=vertical.get("primary_objective"),
                intensity="savage" if payload.intensity in {"savage", "godmode"} else payload.intensity,
                auto_apply=False,
                max_autofix_rounds=min(profile.autofix_rounds, 2),
                actor_user=user,
            )
        except Exception as exc:
            legacy = {
                "wizard": {"id": None, "status": "fallback_draft", "source": "safe_fallback", "reason": str(exc)},
                "wizard_id": None,
                "dry_run_result": {"apply_ready": False, "blockers": ["legacy_wizard_generation_failed"]},
                "validation_snapshot": {"apply_ready": False, "blockers": ["legacy_wizard_generation_failed"]},
                "autofix": {"rounds": [], "blocked_items": ["legacy_wizard_generation_failed"], "safe_placeholders": []},
            }
            upsert_step(conn, run_id, "wizard_generation.failed_partial", "Wizard legacy fallo; fallback seguro creado", "failed", error_json={"message": str(exc)})
            record_event(conn, run_id, "wizard.failed_partial", "Wizard legacy fallo; se creo fallback seguro", 24, payload_json={"error": str(exc)})
        wizard = legacy.get("wizard") or {}
        wizard_id = str(legacy.get("wizard_id") or wizard.get("id") or "")
        bot_id = payload.bot_id or wizard.get("bot_id")
        update_run(conn, run_id, wizard_id=wizard_id, bot_id=bot_id)
        _record_step(conn, run_id, "wizard.created", "Wizard generado y guardado", 25, {"wizard_id": wizard_id, "wizard": wizard}, task="wizard_generation")

        _check_cancelled(conn, run_id)
        vertical_pack = build_vertical_intelligence_pack({**business, **vertical}, payload.intensity)
        _record_step(conn, run_id, "vertical_pack.generated", "Vertical Intelligence Pack generado", 32, vertical_pack, task="vertical_intelligence_pack")

        _check_cancelled(conn, run_id)
        policy_pack = generate_agent_policy_pack(vertical_pack, payload.intensity)
        save_json_artifact(conn, table="agent_policy_packs", json_column="pack_json", run_id=run_id, bot_id=bot_id, payload=policy_pack)
        _record_step(conn, run_id, "policy_pack.generated", "Agent Policy Pack generado", 40, policy_pack, task="policy_generation")

        specialist = {"specialists": [agent["agent_key"] for agent in policy_pack.get("agents", [])], "routing": "multi_agent_runtime", "default_agent": "general"}
        _record_step(conn, run_id, "specialist_agents_config.generated", "Specialist agents config generado", 46, specialist, task="policy_generation")

        _check_cancelled(conn, run_id)
        knowledge = generate_knowledge_plan(vertical_pack, business) if payload.auto_generate_knowledge else {}
        if knowledge:
            save_json_artifact(conn, table="knowledge_grounding_plans", json_column="plan_json", run_id=run_id, bot_id=bot_id, payload=knowledge)
        _record_step(conn, run_id, "knowledge_plan.generated", "Knowledge plan generado", 52, knowledge, task="knowledge_plan")

        _check_cancelled(conn, run_id)
        whatsapp = generate_whatsapp_production_pack(vertical_pack, business) if payload.auto_generate_templates else {}
        if whatsapp:
            save_json_artifact(conn, table="whatsapp_production_packs", json_column="pack_json", run_id=run_id, bot_id=bot_id, payload=whatsapp)
        _record_step(conn, run_id, "whatsapp_pack.generated", "WhatsApp Production Pack generado", 58, whatsapp, task="whatsapp_template_generation")

        _check_cancelled(conn, run_id)
        tool_plan = generate_tool_execution_plan(vertical_pack, payload.intensity) if payload.auto_generate_tools else {}
        if tool_plan:
            save_json_artifact(conn, table="tool_execution_plans", json_column="plan_json", run_id=run_id, bot_id=bot_id, payload=tool_plan)
        _record_step(conn, run_id, "tool_plan.generated", "Tool execution plan generado", 64, tool_plan, task="tool_execution_plan")

        dry = legacy.get("dry_run_result") or {}
        validation = legacy.get("validation_snapshot") or {}
        _record_step(conn, run_id, "dry_run.completed", "Dry run completado", 70, {"dry_run_result": dry, "validation_snapshot": validation})

        autofix = legacy.get("autofix") or {"rounds": [], "blocked_items": knowledge.get("missing_facts", [])}
        record_event(conn, run_id, "autofix.started", "Autofix iniciado", 72, payload_json={"max_rounds": profile.autofix_rounds})
        upsert_step(conn, run_id, "autofix.round_completed", "Autofix seguro completado", "completed", output_json=autofix)
        patch_run_result(conn, run_id, "autofix", autofix)
        record_event(conn, run_id, "autofix.round_completed", "Autofix legacy/seguro completado", 76, payload_json=autofix)
        update_run(conn, run_id, current_step="autofix.round_completed", progress=76)
        _commit_best_effort(conn)

        _check_cancelled(conn, run_id)
        simulation = run_simulation_suite(vertical_pack, wizard, profile.simulations) if payload.auto_run_simulations else {}
        if simulation:
            save_simulation_report(conn, run_id=run_id, wizard_id=wizard_id, bot_id=bot_id, report=simulation)
        _record_step(conn, run_id, "simulation.completed", "Simulation suite completada", 84, simulation, task="simulation_judge")

        _check_cancelled(conn, run_id)
        readiness = evaluate_go_live_readiness(
            wizard=wizard,
            dry_run_result=dry,
            validation_snapshot=validation,
            simulation_report=simulation,
            knowledge_plan=knowledge,
            tool_execution_plan=tool_plan,
            policy_pack=policy_pack,
            human_handoff_config=None,
        )
        save_go_live_readiness(conn, run_id=run_id, wizard_id=wizard_id, bot_id=bot_id, report=readiness)
        _record_step(conn, run_id, "go_live_readiness.completed", "Go-live readiness evaluado", 90, readiness, task="go_live_readiness")
        for item in readiness.get("human_confirmations_required", []):
            saved = upsert_human_confirmation(conn, run_id=run_id, wizard_id=wizard_id, bot_id=bot_id, field_key=item.get("field_key", "confirmation"), label=item.get("label"), reason=item.get("reason"), status=item.get("status", "pending"), suggested_value=str(item.get("suggested_value") or "") or None)
            record_event(conn, run_id, "human_confirmation.required", saved.get("label", "Confirmacion humana requerida"), 91, payload_json=dict(saved))

        apply_plan = prepare_release_plan(readiness) if payload.auto_prepare_go_live else {}
        record_event(conn, run_id, "apply.prepared", "Apply/canary plan preparado", 94, payload_json=apply_plan)
        patch_run_result(conn, run_id, "apply_plan", apply_plan)
        _commit_best_effort(conn)
        learning = generate_learning_recommendations([])
        confirmations = list_human_confirmations(conn, run_id)
        result = {
            "run_id": run_id,
            "wizard_id": wizard_id,
            "bot_id": bot_id,
            "status": "completed_partial" if readiness.get("status") == "blocked" else "completed",
            "progress": 100,
            "vertical_profile": vertical,
            "business_profile": business,
            "wizard": wizard,
            "validation_snapshot": validation,
            "simulation_report": simulation,
            "agent_policy_pack": policy_pack,
            "specialist_agents_config": specialist,
            "knowledge_plan": knowledge,
            "whatsapp_template_pack": whatsapp,
            "tool_execution_plan": tool_plan,
            "go_live_readiness": readiness,
            "human_confirmations": confirmations,
            "next_action": {"type": "resolve_blockers" if readiness.get("status") == "blocked" else "prepare_apply", "apply_plan": apply_plan, "learning": learning},
        }
        status = result["status"]
        update_run(conn, run_id, status=status, progress=100, current_step="workflow.completed", result_json=result, cost_estimate_usd=governor.spent)
        record_event(conn, run_id, "workflow.completed_partial" if status == "completed_partial" else "workflow.completed", "Workflow terminado", 100, payload_json=result)
        _commit_best_effort(conn)
        return result
    except CostLimitExceeded as exc:
        update_run(conn, run_id, status="paused_cost_limit", error_json={"message": str(exc)})
        record_event(conn, run_id, "workflow.paused_cost_limit", str(exc), payload_json={"error": str(exc)})
        _commit_best_effort(conn)
        return {"run_id": run_id, "status": "paused_cost_limit", "progress": 0, "next_action": {"type": "increase_cost_limit"}}
    except WorkflowCancelled:
        update_run(conn, run_id, status="cancelled", error_json={"message": "workflow cancelled"})
        _commit_best_effort(conn)
        return {"run_id": run_id, "status": "cancelled", "progress": 0, "next_action": {"type": "cancelled"}}
    except Exception as exc:
        update_run(conn, run_id, status="failed", error_json={"message": str(exc)})
        record_event(conn, run_id, "workflow.failed", str(exc), payload_json={"error": str(exc)})
        _commit_best_effort(conn)
        return {"run_id": run_id, "status": "failed", "progress": 0, "next_action": {"type": "inspect_failure"}, "error": {"message": str(exc)}}
