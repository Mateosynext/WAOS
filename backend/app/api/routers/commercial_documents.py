from __future__ import annotations

from fastapi import APIRouter

from ..handlers.commercial_documents import (
    commercial_document_convert_to_work_order_route,
    commercial_document_create_route,
    commercial_document_draft_from_catalog_route,
    commercial_document_draft_from_conversation_route,
    commercial_document_generate_pdf_route,
    commercial_document_pdf_download_route,
    commercial_document_status_route,
    commercial_document_send_route,
    commercial_document_accept_route,
    commercial_document_payment_route,
    commercial_documents_list_route,
    commercial_documents_overview_route,
    organization_branding_get_route,
    organization_branding_upsert_route,
    catalog_quote_rules_list_route,
    catalog_quote_rules_create_route,
)

router = APIRouter(tags=["commercial_documents"])

router.add_api_route("/api/v1/commercial-documents/overview", commercial_documents_overview_route, methods=["GET"])
router.add_api_route("/api/v1/commercial-documents", commercial_documents_list_route, methods=["GET"])
router.add_api_route("/api/v1/commercial-documents", commercial_document_create_route, methods=["POST"])
router.add_api_route("/api/v1/commercial-documents/draft-from-catalog", commercial_document_draft_from_catalog_route, methods=["POST"])
router.add_api_route("/api/v1/commercial-documents/draft-from-conversation", commercial_document_draft_from_conversation_route, methods=["POST"])
router.add_api_route("/api/v1/commercial-documents/{document_id}/pdf", commercial_document_pdf_download_route, methods=["GET"])
router.add_api_route("/api/v1/commercial-documents/{document_id}/generate-pdf", commercial_document_generate_pdf_route, methods=["POST"])
router.add_api_route("/api/v1/commercial-documents/{document_id}/status", commercial_document_status_route, methods=["POST"])
router.add_api_route("/api/v1/commercial-documents/{document_id}/convert-to-work-order", commercial_document_convert_to_work_order_route, methods=["POST"])
router.add_api_route("/api/v1/commercial-documents/{document_id}/send", commercial_document_send_route, methods=["POST"])
router.add_api_route("/api/v1/commercial-documents/{document_id}/accept", commercial_document_accept_route, methods=["POST"])
router.add_api_route("/api/v1/commercial-documents/{document_id}/payment", commercial_document_payment_route, methods=["POST"])
router.add_api_route("/api/v1/organization-branding", organization_branding_get_route, methods=["GET"])
router.add_api_route("/api/v1/catalog/quote-rules", catalog_quote_rules_list_route, methods=["GET"])
router.add_api_route("/api/v1/catalog/quote-rules", catalog_quote_rules_create_route, methods=["POST"])
router.add_api_route("/api/v1/organization-branding", organization_branding_upsert_route, methods=["POST"])
