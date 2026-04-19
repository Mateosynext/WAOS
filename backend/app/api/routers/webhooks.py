from __future__ import annotations

from fastapi import APIRouter
from ..handlers.webhooks import simulate_inbound, stripe_webhook, whatsapp_quality_webhook, whatsapp_verify, whatsapp_webhook

router = APIRouter(tags=["webhooks"])

router.add_api_route('/api/v1/simulate/inbound', simulate_inbound, methods=["POST"])
router.add_api_route('/webhooks/whatsapp/{number_id}', whatsapp_verify, methods=["GET"])
router.add_api_route('/webhooks/whatsapp/{number_id}', whatsapp_webhook, methods=["POST"])
router.add_api_route('/webhooks/whatsapp/{number_id}/quality', whatsapp_quality_webhook, methods=["POST"])
router.add_api_route('/webhooks/stripe', stripe_webhook, methods=["POST"])
