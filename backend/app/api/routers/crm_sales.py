from __future__ import annotations

from fastapi import APIRouter
from ..handlers.crm_sales import (
    create_feedback,
    create_payment_link_route,
    create_playbook_route,
    create_portal_request,
    create_voice_note,
    create_whatsapp_flow_route,
    create_whatsapp_flow_version_route,
    create_whatsapp_template_route,
    create_whatsapp_template_version_route,
    execute_whatsapp_flow_route,
    get_crm_funnel_summary,
    get_crm_pipeline_summary,
    get_seller_mode,
    get_whatsapp_flow_route,
    get_whatsapp_template_route,
    list_crm_leads,
    list_feedback,
    list_payments,
    list_playbooks,
    list_portal_requests,
    list_reactivation,
    list_voice_notes,
    list_whatsapp_flows,
    list_whatsapp_templates,
    publish_whatsapp_flow_route,
    refresh_payment_route,
    rollback_whatsapp_flow_route,
    sync_whatsapp_flow_route,
    sync_whatsapp_template_route,
    sync_whatsapp_template_status_route,
    upsert_crm_lead_route,
    update_whatsapp_template_approval_route,
    whatsapp_flow_analytics_route,
    whatsapp_flow_event_route,
    whatsapp_flow_experiment_route,
    whatsapp_flow_runtime_route,
    whatsapp_template_analytics_route,
    lint_whatsapp_template_route,
    confirm_payment_route,
)

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
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}', get_whatsapp_flow_route, methods=["GET"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/versions', create_whatsapp_flow_version_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/publish', publish_whatsapp_flow_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/sync', sync_whatsapp_flow_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/rollback', rollback_whatsapp_flow_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/execute', execute_whatsapp_flow_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/runtime', whatsapp_flow_runtime_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/events', whatsapp_flow_event_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/experiments', whatsapp_flow_experiment_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/flows/{flow_id}/analytics', whatsapp_flow_analytics_route, methods=["GET"])
router.add_api_route('/api/v1/whatsapp/templates/lint', lint_whatsapp_template_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/templates', list_whatsapp_templates, methods=["GET"])
router.add_api_route('/api/v1/whatsapp/templates', create_whatsapp_template_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/templates/{template_id}', get_whatsapp_template_route, methods=["GET"])
router.add_api_route('/api/v1/whatsapp/templates/{template_id}/versions', create_whatsapp_template_version_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/templates/{template_id}/sync', sync_whatsapp_template_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/templates/{template_id}/sync-status', sync_whatsapp_template_status_route, methods=["POST", "GET"])
router.add_api_route('/api/v1/whatsapp/templates/{template_id}/approval', update_whatsapp_template_approval_route, methods=["POST"])
router.add_api_route('/api/v1/whatsapp/templates/{template_id}/analytics', whatsapp_template_analytics_route, methods=["GET"])
router.add_api_route('/api/v1/reactivation/recommendations', list_reactivation, methods=["GET"])
router.add_api_route('/api/v1/voice/notes', create_voice_note, methods=["POST"])
router.add_api_route('/api/v1/voice/notes', list_voice_notes, methods=["GET"])
router.add_api_route('/api/v1/feedback', create_feedback, methods=["POST"])
router.add_api_route('/api/v1/feedback', list_feedback, methods=["GET"])
router.add_api_route('/api/v1/portal/requests', create_portal_request, methods=["POST"])
router.add_api_route('/api/v1/portal/requests', list_portal_requests, methods=["GET"])
router.add_api_route('/api/v1/playbooks', create_playbook_route, methods=["POST"])
router.add_api_route('/api/v1/playbooks', list_playbooks, methods=["GET"])
router.add_api_route('/api/v1/crm/pipeline-summary', get_crm_pipeline_summary, methods=["GET"])
router.add_api_route('/api/v1/crm/funnel-summary', get_crm_funnel_summary, methods=["GET"])
