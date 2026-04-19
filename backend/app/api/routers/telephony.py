from __future__ import annotations

from fastapi import APIRouter

from ..handlers.telephony import twilio_voice_inbound, twilio_voice_status, twilio_voice_turn

router = APIRouter(tags=["telephony"])

router.add_api_route('/webhooks/twilio/voice', twilio_voice_inbound, methods=['POST'])
router.add_api_route('/webhooks/twilio/voice/turn', twilio_voice_turn, methods=['POST'])
router.add_api_route('/webhooks/twilio/voice/status', twilio_voice_status, methods=['POST'])
