from __future__ import annotations

from .integration_support import IntegrationSupportMixin
from .uow import UnitOfWork


class IntegrationService(IntegrationSupportMixin):
    def list_integrations(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, limit: int, offset: int, user: dict, clamp_limit, clamp_offset) -> list[dict]:
        from .integration_handlers.queries import list_integrations as _handle
        return _handle(self, uow=uow, organization_id=organization_id, bot_id=bot_id, limit=limit, offset=offset, user=user, clamp_limit=clamp_limit, clamp_offset=clamp_offset)

    def upsert_integration(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .integration_handlers.commands import upsert_integration as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def configure_whatsapp(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .integration_handlers.commands import configure_whatsapp as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def configure_google_calendar(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .integration_handlers.commands import configure_google_calendar as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def configure_stripe(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .integration_handlers.commands import configure_stripe as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def test_integration(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> dict:
        from .integration_handlers.commands import test_integration as _handle
        return _handle(self, uow=uow, integration_id=integration_id, user=user)

    def list_secrets(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, user: dict) -> list[dict]:
        from .integration_handlers.queries import list_secrets as _handle
        return _handle(self, uow=uow, organization_id=organization_id, bot_id=bot_id, user=user)

    def create_secret(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .integration_handlers.commands import create_secret as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def rotate_secret(self, uow: UnitOfWork, *, secret_id: str, payload, user: dict) -> dict:
        from .integration_handlers.commands import rotate_secret as _handle
        return _handle(self, uow=uow, secret_id=secret_id, payload=payload, user=user)

    def get_rate_limits(self, uow: UnitOfWork, *, organization_id: str, bot_id: str | None, user: dict) -> list[dict]:
        from .integration_handlers.queries import get_rate_limits as _handle
        return _handle(self, uow=uow, organization_id=organization_id, bot_id=bot_id, user=user)

    def upsert_rate_limit(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .integration_handlers.commands import upsert_rate_limit as _handle
        return _handle(self, uow=uow, payload=payload, user=user)

    def integration_sync_runs(self, uow: UnitOfWork, *, organization_id: str, integration_id: str | None, user: dict) -> list[dict]:
        from .integration_handlers.queries import integration_sync_runs as _handle
        return _handle(self, uow=uow, organization_id=organization_id, integration_id=integration_id, user=user)

    def trigger_integration_sync(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> dict:
        from .integration_handlers.commands import trigger_integration_sync as _handle
        return _handle(self, uow=uow, integration_id=integration_id, user=user)

    def integration_availability(self, uow: UnitOfWork, *, integration_id: str, time_min: str, time_max: str, user: dict) -> dict:
        from .integration_handlers.queries import integration_availability as _handle
        return _handle(self, uow=uow, integration_id=integration_id, time_min=time_min, time_max=time_max, user=user)

    def start_meta_signup(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> dict:
        from .integration_handlers.commands import start_meta_signup as _handle
        return _handle(self, uow=uow, integration_id=integration_id, user=user)

    def complete_meta_signup(self, uow: UnitOfWork, *, integration_id: str, payload, user: dict) -> dict:
        from .integration_handlers.commands import complete_meta_signup as _handle
        return _handle(self, uow=uow, integration_id=integration_id, payload=payload, user=user)

    def start_google_oauth(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> dict:
        from .integration_handlers.commands import start_google_oauth as _handle
        return _handle(self, uow=uow, integration_id=integration_id, user=user)

    def finish_google_oauth(self, uow: UnitOfWork, *, state: str, code: str) -> dict:
        from .integration_handlers.commands import finish_google_oauth as _handle
        return _handle(self, uow=uow, state=state, code=code)

    def list_google_calendars(self, uow: UnitOfWork, *, integration_id: str, user: dict) -> list[dict]:
        from .integration_handlers.queries import list_google_calendars as _handle
        return _handle(self, uow=uow, integration_id=integration_id, user=user)

    def integration_events(self, uow: UnitOfWork, *, organization_id: str, integration_id: str | None, user: dict) -> list[dict]:
        from .integration_handlers.queries import integration_events as _handle
        return _handle(self, uow=uow, organization_id=organization_id, integration_id=integration_id, user=user)

    def integration_observability(self, uow: UnitOfWork, *, organization_id: str, integration_id: str | None, user: dict) -> dict:
        from .integration_handlers.queries import integration_observability as _handle
        return _handle(self, uow=uow, organization_id=organization_id, integration_id=integration_id, user=user)

    def integration_center(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict:
        from .integration_handlers.queries import integration_center as _handle
        return _handle(self, uow=uow, organization_id=organization_id, user=user)

    def replay_webhook_receipt(self, uow: UnitOfWork, *, receipt_id: str, payload, user: dict) -> dict:
        from .integration_handlers.commands import replay_webhook_receipt as _handle
        return _handle(self, uow=uow, receipt_id=receipt_id, payload=payload, user=user)


integration_service = IntegrationService()
