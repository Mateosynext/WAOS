from __future__ import annotations

from .onboarding_support import OnboardingSupport
from .uow import UnitOfWork


class OnboardingService(OnboardingSupport):
    def list_guided_verticals(self, uow: UnitOfWork, *, user: dict) -> dict:
        from .onboarding_handlers.queries import list_guided_verticals as _handle
        return _handle(self, uow, user=user)

    def wizard_blueprint(self, uow: UnitOfWork, *, organization_id: str | None, bot_id: str | None, vertical_id: str | None, subvertical: str | None, primary_objective: str | None, user: dict) -> dict:
        from .onboarding_handlers.queries import wizard_blueprint as _handle
        return _handle(self, uow, organization_id=organization_id, bot_id=bot_id, vertical_id=vertical_id, subvertical=subvertical, primary_objective=primary_objective, user=user)

    def start_wizard(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .onboarding_handlers.commands import start_wizard as _handle
        return _handle(self, uow, payload=payload, user=user)

    def ai_prefill_wizard(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .onboarding_handlers.commands import ai_prefill_wizard as _handle
        return _handle(self, uow, payload=payload, user=user)

    def ai_autofix_wizard(self, uow: UnitOfWork, *, wizard_id: str, payload, user: dict) -> dict:
        from .onboarding_handlers.commands import ai_autofix_wizard as _handle
        return _handle(self, uow, wizard_id=wizard_id, payload=payload, user=user)

    def ai_autopilot_wizard(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .onboarding_handlers.commands import ai_autopilot_wizard as _handle
        return _handle(self, uow, payload=payload, user=user)

    def get_wizard(self, uow: UnitOfWork, *, wizard_id: str, user: dict) -> dict:
        from .onboarding_handlers.queries import get_wizard as _handle
        return _handle(self, uow, wizard_id=wizard_id, user=user)

    def update_wizard_step(self, uow: UnitOfWork, *, wizard_id: str, step_key: str, payload, user: dict) -> dict:
        from .onboarding_handlers.commands import update_wizard_step as _handle
        return _handle(self, uow, wizard_id=wizard_id, step_key=step_key, payload=payload, user=user)

    def dry_run_wizard(self, uow: UnitOfWork, *, wizard_id: str, user: dict) -> dict:
        from .onboarding_handlers.commands import dry_run_wizard as _handle
        return _handle(self, uow, wizard_id=wizard_id, user=user)

    def apply_wizard(self, uow: UnitOfWork, *, wizard_id: str, payload, user: dict) -> dict:
        from .onboarding_handlers.commands import apply_wizard as _handle
        return _handle(self, uow, wizard_id=wizard_id, payload=payload, user=user)

    def summary(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> dict:
        from .onboarding_handlers.queries import summary as _handle
        return _handle(self, uow, user=user, organization_id=organization_id, bot_id=bot_id)

    def set_tenant_mode(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .onboarding_handlers.commands import set_tenant_mode as _handle
        return _handle(self, uow, payload=payload, user=user)

    def list_saved_views(self, uow: UnitOfWork, *, organization_id: str, user: dict) -> dict:
        from .onboarding_handlers.queries import list_saved_views as _handle
        return _handle(self, uow, organization_id=organization_id, user=user)

    def create_saved_view(self, uow: UnitOfWork, *, payload, user: dict) -> dict:
        from .onboarding_handlers.commands import create_saved_view as _handle
        return _handle(self, uow, payload=payload, user=user)


onboarding_service = OnboardingService()
