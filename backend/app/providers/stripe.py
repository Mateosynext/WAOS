from __future__ import annotations
from ..payments_runtime import reconcile_pending_provider_payments
class StripeProvider:
    def reconcile_pending(self, conn, *, organization_id: str | None = None, bot_id: str | None = None) -> dict:
        return reconcile_pending_provider_payments(conn, organization_id=organization_id, bot_id=bot_id)
stripe_provider = StripeProvider()
