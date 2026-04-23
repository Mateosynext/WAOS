from __future__ import annotations

from .outcomes_support import OutcomesSupport
from .uow import UnitOfWork


class OutcomesApplicationService(OutcomesSupport):
    def record_exposure(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .outcomes_handlers.record_exposure import handle as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def record_event(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .outcomes_handlers.record_event import handle as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def record_operator_signal(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .outcomes_handlers.record_operator_signal import handle as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def scorecards(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, entity_type: str | None, entity_id: str | None, scorecard_window: str, user: dict) -> dict:
        from .outcomes_handlers.scorecards import handle as _handle
        return _handle(self, uow=uow, organization_id=organization_id, bot_id=bot_id, entity_type=entity_type, entity_id=entity_id, scorecard_window=scorecard_window, user=user)

    def attribution(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, entity_type: str | None, entity_id: str | None, outcome_event_id: str | None, limit: int, user: dict) -> dict:
        from .outcomes_handlers.attribution import handle as _handle
        return _handle(self, uow=uow, organization_id=organization_id, bot_id=bot_id, entity_type=entity_type, entity_id=entity_id, outcome_event_id=outcome_event_id, limit=limit, user=user)

    def entity_detail(self, uow: UnitOfWork, *, organization_id: str, entity_type: str, entity_id: str, user: dict) -> dict:
        from .outcomes_handlers.entity_detail import handle as _handle
        return _handle(self, uow=uow, organization_id=organization_id, entity_type=entity_type, entity_id=entity_id, user=user)

    def recompute(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .outcomes_handlers.recompute import handle as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def list_decisions(self, uow: UnitOfWork, *, organization_id: str, entity_type: str | None, entity_id: str | None, status: str | None, user: dict) -> dict:
        from .outcomes_handlers.list_decisions import handle as _handle
        return _handle(self, uow=uow, organization_id=organization_id, entity_type=entity_type, entity_id=entity_id, status=status, user=user)

    def apply_decision(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .outcomes_handlers.apply_decision import handle as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def rollback_decision(self, uow: UnitOfWork, *, decision_id: str, payload, user: dict) -> dict:
        from .outcomes_handlers.rollback_decision import handle as _handle
        return _handle(self, uow=uow, decision_id=decision_id, payload=payload, user=user)


outcomes_service = OutcomesApplicationService()
