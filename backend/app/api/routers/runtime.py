from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from ...application.runtime_service import runtime_service
from ...schemas import ApiEnvelope, DeadLetterRequeueRequest, FlexibleSchema
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["runtime"])


@router.get("/api/v1/runtime/overview", response_model=ApiEnvelope[FlexibleSchema])
def runtime_operations_overview(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return runtime_service.runtime_overview(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/bots/{bot_id}/health", response_model=ApiEnvelope[FlexibleSchema])
def get_bot_health(bot_id: str, user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    return runtime_service.bot_health(uow, bot_id=bot_id, organization_id=organization_id, user=user)


@router.get("/api/v1/integrations/health", response_model=ApiEnvelope[FlexibleSchema])
def get_integrations_health(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.integrations_health(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/observability/overview", response_model=ApiEnvelope[FlexibleSchema])
def observability_overview(
    user: CurrentUser,
    uow: CurrentUoW,
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return runtime_service.observability_overview(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.post("/api/v1/observability/frontend-errors", response_model=FlexibleSchema)
def frontend_errors(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    return runtime_service.frontend_errors(payload=payload, request=request)


@router.get("/api/v1/runtime/queue", response_model=FlexibleSchema)
def runtime_queue(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.runtime_queue(uow, organization_id=organization_id, user=user)


@router.get("/api/v1/runtime/scheduler", response_model=FlexibleSchema)
def runtime_scheduler(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.runtime_scheduler(uow, organization_id=organization_id, user=user)

@router.get("/api/v1/runtime/autoscaling", response_model=ApiEnvelope[FlexibleSchema])
def runtime_autoscaling(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.runtime_autoscaling(uow, organization_id=organization_id, user=user)


@router.get("/api/v1/runtime/health/modules", response_model=ApiEnvelope[FlexibleSchema])
def runtime_health_modules(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.runtime_module_health(uow, organization_id=organization_id, user=user)


@router.get("/api/v1/runtime/callbacks", response_model=list[FlexibleSchema])
def get_runtime_callbacks(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    return runtime_service.runtime_callbacks(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/operations/dead-letters", response_model=FlexibleSchema)
def list_dead_letters(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), kind: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.list_dead_letters(uow, organization_id=organization_id, kind=kind, user=user)


@router.post("/api/v1/operations/dead-letters/{kind}/{item_id}/requeue", response_model=FlexibleSchema)
def requeue_dead_letter(kind: str, item_id: str, payload: DeadLetterRequeueRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.requeue_dead_letter(uow, kind=kind, item_id=item_id, payload=payload, user=user)


@router.get("/api/v1/ai/dashboard", response_model=FlexibleSchema)
def ai_dashboard(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.ai_dashboard(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/conversations/{conversation_id}/ai/stream-preview", response_model=FlexibleSchema)
def ai_stream_preview(conversation_id: str, message: str, user: CurrentUser, uow: CurrentUoW):
    return runtime_service.ai_stream_preview(uow, conversation_id=conversation_id, message=message, user=user)


@router.get("/api/v1/logs/search", response_model=ApiEnvelope[FlexibleSchema])
def search_logs(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None), q: str = Query(...)) -> dict[str, Any]:
    return runtime_service.searchable_logs(uow, organization_id=organization_id, query=q, user=user)


@router.get("/api/v1/traces/{trace_id}", response_model=ApiEnvelope[FlexibleSchema])
def get_trace(trace_id: str, user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.trace_explorer(uow, organization_id=organization_id, trace_id=trace_id, user=user)


@router.get("/api/v1/observability/otel", response_model=ApiEnvelope[FlexibleSchema])
def observability_otel(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.observability_otel(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/observability/otel/flush", response_model=ApiEnvelope[FlexibleSchema])
def observability_otel_flush(user: CurrentUser, uow: CurrentUoW, organization_id: str | None = Query(default=None), dry_run: bool = Query(default=False)) -> dict[str, Any]:
    return runtime_service.observability_otel_flush(uow, organization_id=organization_id, dry_run=dry_run, user=user)


@router.post("/api/v1/shadow/runs", response_model=ApiEnvelope[FlexibleSchema])
def create_shadow(payload: dict[str, Any], user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.shadow_run_create(uow, payload=payload, user=user)


@router.get("/api/v1/shadow/overview", response_model=ApiEnvelope[FlexibleSchema])
def get_shadow_overview(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), experiment_key: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.shadow_run_overview(uow, organization_id=organization_id, experiment_key=experiment_key, user=user)


@router.post("/api/v1/prompts/artifacts", response_model=ApiEnvelope[FlexibleSchema])
def upsert_prompt_artifact_route(payload: dict[str, Any], user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.prompt_artifact_upsert(uow, payload=payload, user=user)


@router.get("/api/v1/prompts/analytics", response_model=ApiEnvelope[FlexibleSchema])
def get_prompt_analytics(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.prompt_analytics(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.post("/api/v1/public-api/credentials", response_model=ApiEnvelope[FlexibleSchema])
def issue_public_api_credential_route(payload: dict[str, Any], user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.public_api_credential_issue(uow, payload=payload, user=user)


@router.get("/api/v1/unified-inbox/overview", response_model=ApiEnvelope[FlexibleSchema])
def unified_inbox_overview_route(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.unified_inbox(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/revenue/optimization", response_model=ApiEnvelope[FlexibleSchema])
def revenue_optimization_route(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.revenue_optimization(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/compliance/overview", response_model=ApiEnvelope[FlexibleSchema])
def compliance_overview_route(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    return runtime_service.compliance_world_class(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/compliance/deletion-workflows", response_model=ApiEnvelope[FlexibleSchema])
def create_deletion_workflow_route(payload: dict[str, Any], user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.deletion_workflow_create(uow, payload=payload, user=user)


@router.post("/api/v1/quality/chaos-runs", response_model=ApiEnvelope[FlexibleSchema])
def create_chaos_run_route(payload: dict[str, Any], user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.chaos_run_create(uow, payload=payload, user=user)


@router.get("/api/v1/quality/chaos-overview", response_model=ApiEnvelope[FlexibleSchema])
def chaos_overview_route(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    return runtime_service.chaos_runs_overview(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/quality/load-tests", response_model=ApiEnvelope[FlexibleSchema])
def create_load_test_route(payload: dict[str, Any], user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.load_test_create(uow, payload=payload, user=user)


@router.get("/api/v1/quality/load-overview", response_model=ApiEnvelope[FlexibleSchema])
def load_overview_route(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    return runtime_service.load_tests_overview(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/prompts/experiments", response_model=ApiEnvelope[FlexibleSchema])
def create_prompt_experiment_route(payload: dict[str, Any], user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return runtime_service.prompt_experiment_create(uow, payload=payload, user=user)


@router.get("/api/v1/prompts/experiments", response_model=ApiEnvelope[FlexibleSchema])
def list_prompt_experiments_route(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), bot_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.prompt_experiments(uow, organization_id=organization_id, bot_id=bot_id, user=user)


@router.get("/api/v1/prompts/experiments/{experiment_key}/assignment", response_model=ApiEnvelope[FlexibleSchema])
def prompt_experiment_assignment_route(experiment_key: str, user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...), conversation_id: str | None = Query(default=None), contact_id: str | None = Query(default=None)) -> dict[str, Any]:
    return runtime_service.prompt_experiment_assignment(uow, organization_id=organization_id, experiment_key=experiment_key, conversation_id=conversation_id, contact_id=contact_id, user=user)
