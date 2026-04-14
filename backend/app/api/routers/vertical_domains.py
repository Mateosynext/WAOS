from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ...security import ensure_org_access
from ...vertical_domain_runtime import get_vertical_domain_snapshot
from ...vertical_transactions import vertical_transaction_service
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=['vertical-domains'])


@router.get('/api/v1/vertical-domains/accounts/{account_id}')
def get_account_vertical_domain(account_id: str, user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict[str, Any]:
    ensure_org_access(user, organization_id)
    account = vertical_transaction_service.get_account(uow.conn, organization_id=organization_id, account_id=account_id)
    return get_vertical_domain_snapshot(uow.conn, organization_id=organization_id, account_id=account_id, vertical_id=account['vertical_id'])
