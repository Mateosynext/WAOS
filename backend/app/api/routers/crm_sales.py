from __future__ import annotations

from fastapi import APIRouter
from ..handlers.crm_sales import list_crm_leads, upsert_crm_lead_route, list_payments, create_payment_link_route, confirm_payment_route, refresh_payment_route, get_seller_mode, list_whatsapp_flows, create_whatsapp_flow_route, list_reactivation, create_voice_note, list_voice_notes, create_feedback, list_feedback, create_portal_request, list_portal_requests, create_playbook_route, list_playbooks

router = APIRouter(tags=["crm_sales"])

router.add_api_route('/api/v1/crm/leads', list_crm_leads, methods=["GET"])
router.add_api_route('/api/v1/crm/leads', upsert_crm_lead_route, methods=["POST"])
router.add_api_route('/api/v1/sales/payments', list_payments, methods=["GET"])
router.add_api_route('/api/v1/sales/payments', create_payment_link_route, methods=["POST"])
router.add_api_route('/api/v1/sales/payments/{payment_id}/confirm', confirm_payment_route, methods=["POST"])
router.add_api_route('/api/v1/sales/payments/{payment_id}/refresh', refresh_payment_route, methods=["POST"])
router.add_api_route('/api/v1/sales/mode/{conversation_id}', get_seller_mode, methods=["GET"])
router.add_api_route('/api/v1/whatsapp/flows', list_whatsapp_flows, methods=["GET"])
router.add_api_route('/api/v1/whatsapp/flows', create_whatsapp_flow_route, methods=["POST"])
router.add_api_route('/api/v1/reactivation/recommendations', list_reactivation, methods=["GET"])
router.add_api_route('/api/v1/voice/notes', create_voice_note, methods=["POST"])
router.add_api_route('/api/v1/voice/notes', list_voice_notes, methods=["GET"])
router.add_api_route('/api/v1/feedback', create_feedback, methods=["POST"])
router.add_api_route('/api/v1/feedback', list_feedback, methods=["GET"])
router.add_api_route('/api/v1/portal/requests', create_portal_request, methods=["POST"])
router.add_api_route('/api/v1/portal/requests', list_portal_requests, methods=["GET"])
router.add_api_route('/api/v1/playbooks', create_playbook_route, methods=["POST"])
router.add_api_route('/api/v1/playbooks', list_playbooks, methods=["GET"])
