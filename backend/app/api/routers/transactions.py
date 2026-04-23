from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...application.transaction_service import transaction_service
from ...schemas import (
    ApiEnvelope,
    FlexibleSchema,
    VerticalTransactionAccountCreateRequest,
    VerticalTransactionCommandRequest,
    VerticalTransactionPlaybookRequest,
)
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["vertical-transactions"])


@router.post("/api/v1/vertical-transactions/accounts", response_model=ApiEnvelope[FlexibleSchema])
def create_vertical_transaction_account(payload: VerticalTransactionAccountCreateRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return transaction_service.create_account(uow, payload=payload, user=user)


@router.get("/api/v1/vertical-transactions/accounts/{account_id}", response_model=ApiEnvelope[FlexibleSchema])
def get_vertical_transaction_account(account_id: str, user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    return transaction_service.get_account(uow, organization_id=organization_id, account_id=account_id, user=user)


@router.post("/api/v1/vertical-transactions/accounts/{account_id}/commands", response_model=ApiEnvelope[FlexibleSchema])
def apply_vertical_transaction_command(account_id: str, payload: VerticalTransactionCommandRequest, user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    return transaction_service.dispatch_command(uow, organization_id=organization_id, account_id=account_id, payload=payload, user=user)


@router.post("/api/v1/vertical-transactions/accounts/{account_id}/execute-playbook", response_model=ApiEnvelope[FlexibleSchema])
def execute_vertical_transaction_playbook(account_id: str, payload: VerticalTransactionPlaybookRequest, user: CurrentUser, uow: CurrentUoW) -> dict[str, Any]:
    return transaction_service.execute_playbook(uow, account_id=account_id, payload=payload, user=user)
