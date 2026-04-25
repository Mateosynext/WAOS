from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from ...schemas import CookieConsentUpsertRequest, LegalAcceptanceRequest, PrivacyRightsRequest
from ..handlers.legal import create_privacy_rights_request, get_public_legal_doc, get_public_subprocessors, list_public_legal_docs, record_legal_acceptance, upsert_cookie_consent
from ..handlers.commercial_documents import public_commercial_document_view_route, public_commercial_document_pdf_route, public_commercial_document_accept_route
from ..handlers.public import root, app_console, health, health_live, health_ready, public_sso_providers, public_sdk_manifest_handler, public_channel_event_ingest, public_verticals_catalog, public_vertical_profile, public_subvertical_profile

router = APIRouter(tags=["public"])

router.add_api_route('/', root, methods=["GET"], response_class=HTMLResponse)
router.add_api_route('/app', app_console, methods=["GET"])
router.add_api_route('/health', health, methods=["GET"])
router.add_api_route('/health/live', health_live, methods=["GET"])
router.add_api_route('/health/ready', health_ready, methods=["GET"])
router.add_api_route('/api/public/sso/providers', public_sso_providers, methods=["GET"])

router.add_api_route("/api/public/legal/docs", list_public_legal_docs, methods=["GET"])
router.add_api_route("/api/public/legal/docs/{slug}", get_public_legal_doc, methods=["GET"])
router.add_api_route("/api/public/legal/subprocessors", get_public_subprocessors, methods=["GET"])
router.add_api_route("/api/public/legal/consents/cookies", upsert_cookie_consent, methods=["POST"])
router.add_api_route("/api/public/legal/acceptances", record_legal_acceptance, methods=["POST"])
router.add_api_route("/api/public/legal/privacy-requests", create_privacy_rights_request, methods=["POST"])

router.add_api_route('/api/public/sdk/manifest', public_sdk_manifest_handler, methods=['GET'])
router.add_api_route('/api/public/v1/channels/events', public_channel_event_ingest, methods=['POST'])

router.add_api_route('/api/public/verticals', public_verticals_catalog, methods=['GET'])
router.add_api_route('/api/public/verticals/profile', public_vertical_profile, methods=['GET'])
router.add_api_route('/api/public/verticals/subvertical-profile', public_subvertical_profile, methods=['GET'])

router.add_api_route('/api/public/commercial-documents/{document_id}', public_commercial_document_view_route, methods=['GET'])
router.add_api_route('/api/public/commercial-documents/{document_id}/pdf', public_commercial_document_pdf_route, methods=['GET'])
router.add_api_route('/api/public/commercial-documents/{document_id}/accept', public_commercial_document_accept_route, methods=['GET', 'POST'])
