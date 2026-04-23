from __future__ import annotations

from .operational_control_support import OperationalControlSupportMixin


class OperationalControlService(OperationalControlSupportMixin):
    HIGH_IMPACT_INTENTS = {
        "bot.shutdown",
        "bot.restart",
        "bot.human_only",
        "availability.block_day",
        "availability.vacation_set",
        "appointment.notify_affected",
        "appointment.reschedule_mass",
        "appointment.reschedule_request_mass",
    }
    DUAL_APPROVAL_INTENTS = {"bot.shutdown", "appointment.reschedule_mass"}

    def summary(self, uow, *, user: dict, organization_id: str, bot_id: str) -> dict:
        from .operational_control_handlers.summary import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id)

    def availability(self, uow, *, user: dict, organization_id: str, bot_id: str, day: str | None = None) -> dict:
        from .operational_control_handlers.availability import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id, day=day)

    def metrics(self, uow, *, user: dict, organization_id: str, bot_id: str, window_days: int = 7) -> dict:
        from .operational_control_handlers.metrics import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id, window_days=window_days)

    def list_alerts(self, uow, *, user: dict, organization_id: str, bot_id: str) -> list[dict]:
        from .operational_control_handlers.list_alerts import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id)

    def list_authorized_numbers(self, uow, *, user: dict, organization_id: str, bot_id: str) -> list[dict]:
        from .operational_control_handlers.list_authorized_numbers import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id)

    def create_authorized_number(self, uow, *, user: dict, payload) -> dict:
        from .operational_control_handlers.create_authorized_number import handle as _handle
        return _handle(self, uow=uow, user=user, payload=payload)

    def list_commands(self, uow, *, user: dict, organization_id: str, bot_id: str) -> list[dict]:
        from .operational_control_handlers.list_commands import handle as _handle
        return _handle(self, uow=uow, user=user, organization_id=organization_id, bot_id=bot_id)

    def preview_command(self, uow, *, user: dict, payload) -> dict:
        from .operational_control_handlers.preview_command import handle as _handle
        return _handle(self, uow=uow, user=user, payload=payload)

    def submit_command(self, uow, *, user: dict, payload) -> dict:
        from .operational_control_handlers.submit_command import handle as _handle
        return _handle(self, uow=uow, user=user, payload=payload)

    def confirm_command(self, uow, *, user: dict, command_id: str, confirmation_code: str | None = None) -> dict:
        from .operational_control_handlers.confirm_command import handle as _handle
        return _handle(self, uow=uow, user=user, command_id=command_id, confirmation_code=confirmation_code)

    def approve_command(self, uow, *, user: dict, command_id: str, note: str = '') -> dict:
        from .operational_control_handlers.approve_command import handle as _handle
        return _handle(self, uow=uow, user=user, command_id=command_id, note=note)

    def cancel_command(self, uow, *, user: dict, command_id: str, reason: str = '') -> dict:
        from .operational_control_handlers.cancel_command import handle as _handle
        return _handle(self, uow=uow, user=user, command_id=command_id, reason=reason)

    def undo_command(self, uow, *, user: dict, command_id: str, reason: str = 'undo_requested') -> dict:
        from .operational_control_handlers.undo_command import handle as _handle
        return _handle(self, uow=uow, user=user, command_id=command_id, reason=reason)

    def preview_reschedule_batch(self, uow, *, user: dict, payload) -> dict:
        from .operational_control_handlers.preview_reschedule_batch import handle as _handle
        return _handle(self, uow=uow, user=user, payload=payload)

    def execute_reschedule_batch(self, uow, *, user: dict, payload) -> dict:
        from .operational_control_handlers.execute_reschedule_batch import handle as _handle
        return _handle(self, uow=uow, user=user, payload=payload)

    def handle_chat_command(self, conn, *, bot_id: str, phone: str, body: str, conversation_id: str, contact_id: str | None, inbound_message_id: str | None = None, external_id: str | None = None, correlation_id: str | None = None) -> dict | None:
        from .operational_control_handlers.handle_chat_command import handle as _handle
        return _handle(self, conn=conn, bot_id=bot_id, phone=phone, body=body, conversation_id=conversation_id, contact_id=contact_id, inbound_message_id=inbound_message_id, external_id=external_id, correlation_id=correlation_id)

    def execute_scheduled_action(self, conn, *, action_id: str | None = None, command_id: str | None = None) -> dict:
        from .operational_control_handlers.execute_scheduled_action import handle as _handle
        return _handle(self, conn=conn, action_id=action_id, command_id=command_id)


operational_control_service = OperationalControlService()
