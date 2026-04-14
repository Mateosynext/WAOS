from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from ..security import ensure_org_access
from ..vertical_transactions import vertical_transaction_service
from .uow import UnitOfWork


class TransactionApplicationService:
    def create_account(self, uow: UnitOfWork, *, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        return vertical_transaction_service.create_account(
            uow.conn,
            organization_id=payload.organization_id,
            vertical_id=payload.vertical_id,
            bot_id=payload.bot_id,
            contact_id=payload.contact_id,
            external_reference=payload.external_reference,
            metadata=payload.metadata,
            state=payload.state,
            actor_user=user,
        )

    def get_account(self, uow: UnitOfWork, *, organization_id: str, account_id: str, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        return vertical_transaction_service.get_account(uow.conn, organization_id=organization_id, account_id=account_id)

    def dispatch_command(self, uow: UnitOfWork, *, organization_id: str, account_id: str, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, organization_id)
        return vertical_transaction_service.dispatch_command(
            uow.conn,
            organization_id=organization_id,
            account_id=account_id,
            command_name=payload.command_name,
            payload=payload.payload,
            actor_user=user,
        )

    def execute_playbook(self, uow: UnitOfWork, *, account_id: str, payload, user: dict) -> dict[str, Any]:
        ensure_org_access(user, payload.organization_id)
        return vertical_transaction_service.execute_playbook(
            uow.conn,
            organization_id=payload.organization_id,
            account_id=account_id,
            actor_user=user,
        )


transaction_service = TransactionApplicationService()
