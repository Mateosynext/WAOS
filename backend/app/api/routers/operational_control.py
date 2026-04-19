from __future__ import annotations

from fastapi import APIRouter, Query

from ...application.operational_control_service import operational_control_service as service
from ...schemas import (
    AuthorizedOperationalNumberRequest,
    OperationalCommandApproveRequest,
    OperationalCommandCancelRequest,
    OperationalCommandConfirmRequest,
    OperationalCommandCreateRequest,
    OperationalCommandPreviewRequest,
    OperationalCommandUndoRequest,
    OperationalRescheduleBatchExecuteRequest,
    OperationalRescheduleBatchPreviewRequest,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["operational_control"])


@router.get('/api/v1/client/operations/summary')
def client_operations_summary(organization_id: str, bot_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.summary(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.get('/api/v1/client/operations/availability')
def client_operations_availability(organization_id: str, bot_id: str, day: str | None = Query(default='today'), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.availability(uow, user=user, organization_id=organization_id, bot_id=bot_id, day=day)


@router.get('/api/v1/client/operations/metrics')
def client_operations_metrics(organization_id: str, bot_id: str, window_days: int = Query(default=7, ge=1, le=30), user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.metrics(uow, user=user, organization_id=organization_id, bot_id=bot_id, window_days=window_days)


@router.get('/api/v1/client/operations/alerts')
def client_operations_alerts(organization_id: str, bot_id: str, user: CurrentUser, uow: CurrentUoW) -> list[dict]:
    return service.list_alerts(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.get('/api/v1/client/operations/commands')
def client_operations_commands(organization_id: str, bot_id: str, user: CurrentUser, uow: CurrentUoW) -> list[dict]:
    return service.list_commands(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.post('/api/v1/client/operations/commands/preview')
def client_operations_preview(payload: OperationalCommandPreviewRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.preview_command(uow, user=user, payload=payload)


@router.post('/api/v1/client/operations/commands')
def client_operations_create(payload: OperationalCommandCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.submit_command(uow, user=user, payload=payload)


@router.post('/api/v1/client/operations/commands/{command_id}/confirm')
def client_operations_confirm(command_id: str, payload: OperationalCommandConfirmRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.confirm_command(uow, user=user, command_id=command_id, confirmation_code=payload.confirmation_code)


@router.post('/api/v1/client/operations/commands/{command_id}/approve')
def client_operations_approve(command_id: str, payload: OperationalCommandApproveRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.approve_command(uow, user=user, command_id=command_id, note=payload.note)


@router.post('/api/v1/client/operations/commands/{command_id}/cancel')
def client_operations_cancel(command_id: str, payload: OperationalCommandCancelRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.cancel_command(uow, user=user, command_id=command_id, reason=payload.reason)


@router.post('/api/v1/client/operations/commands/{command_id}/undo')
def client_operations_undo(command_id: str, payload: OperationalCommandUndoRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.undo_command(uow, user=user, command_id=command_id, reason=payload.reason)


@router.get('/api/v1/client/operations/authorized-numbers')
def client_operations_authorized_numbers(organization_id: str, bot_id: str, user: CurrentUser, uow: CurrentUoW) -> list[dict]:
    return service.list_authorized_numbers(uow, user=user, organization_id=organization_id, bot_id=bot_id)


@router.post('/api/v1/client/operations/authorized-numbers')
def client_operations_authorized_numbers_create(payload: AuthorizedOperationalNumberRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create_authorized_number(uow, user=user, payload=payload)


@router.post('/api/v1/client/operations/reschedule-batches/preview')
def client_operations_reschedule_preview(payload: OperationalRescheduleBatchPreviewRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.preview_reschedule_batch(uow, user=user, payload=payload)


@router.post('/api/v1/client/operations/reschedule-batches/execute')
def client_operations_reschedule_execute(payload: OperationalRescheduleBatchExecuteRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.execute_reschedule_batch(uow, user=user, payload=payload)
