from __future__ import annotations

import html as _html
import secrets

from .common import *
from .common import _require_permission
from ...domains.commercial_documents import (
    commercial_documents_overview,
    convert_quote_to_work_order,
    create_catalog_quote_rule,
    create_commercial_document,
    draft_commercial_document_from_catalog,
    draft_commercial_document_from_conversation,
    ensure_commercial_document_pdf,
    get_organization_branding,
    list_commercial_documents,
    list_catalog_quote_rules,
    update_commercial_document_status,
    upsert_organization_branding,
)
from ...domains.commercial_documents_e2e import (
    accept_document,
    create_payment_for_document,
    ensure_public_url,
    get_public_document,
    public_pdf_path,
    send_document,
)


def _smart_docs_style_nonce() -> str:
    return secrets.token_urlsafe(18)


def _smart_docs_security_headers(*, style_nonce: str) -> dict[str, str]:
    # Public Smart Docs render tenant/customer-controlled document fields. Keep
    # the page display-only: no scripts, no embeds, no framing and no data leaks.
    csp = "; ".join([
        "default-src 'none'",
        "base-uri 'none'",
        "object-src 'none'",
        "script-src 'none'",
        f"style-src 'self' 'nonce-{style_nonce}'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        "connect-src 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
    ])
    return {
        "Content-Security-Policy": csp,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
        "Cross-Origin-Opener-Policy": "same-origin",
    }


def _resolve_org_or_400(user: dict, organization_id: str | None) -> str:
    if not organization_id:
        org_ids = accessible_org_ids(user)
        organization_id = org_ids[0] if org_ids else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    return organization_id


def commercial_documents_overview_route(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    org_id = _resolve_org_or_400(user, organization_id)
    with get_connection() as conn:
        return commercial_documents_overview(conn, org_id, bot_id)


def commercial_documents_list_route(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    org_id = _resolve_org_or_400(user, organization_id)
    with get_connection() as conn:
        return list_commercial_documents(conn, org_id, bot_id=bot_id, document_type=document_type, status=status, limit=limit)


def commercial_document_create_route(payload: CommercialDocumentCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "crm.manage")
    with get_connection() as conn:
        return create_commercial_document(conn, actor_user=user, **payload.model_dump())


def commercial_document_draft_from_catalog_route(payload: CommercialDocumentDraftRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "crm.manage")
    with get_connection() as conn:
        return draft_commercial_document_from_catalog(conn, actor_user=user, **payload.model_dump())


def commercial_document_draft_from_conversation_route(payload: CommercialDocumentDraftRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "conversation.manage")
    with get_connection() as conn:
        return draft_commercial_document_from_conversation(conn, actor_user=user, **payload.model_dump())


def commercial_document_generate_pdf_route(document_id: str, payload: CommercialDocumentPdfRequest | None = None, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        doc = fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,))
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        ensure_org_access(user, doc["organization_id"])
        _require_permission(user, doc["organization_id"], "crm.manage")
        return ensure_commercial_document_pdf(conn, document_id)


def commercial_document_pdf_download_route(document_id: str, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        doc = fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,))
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        ensure_org_access(user, doc["organization_id"])
        pdf_path = doc.get("pdf_path")
        if not pdf_path or not Path(str(pdf_path)).exists():
            doc = ensure_commercial_document_pdf(conn, document_id)
            pdf_path = doc.get("pdf_path")
        return FileResponse(str(pdf_path), media_type="application/pdf", filename=doc.get("pdf_filename") or f"waos-documento-{document_id}.pdf")


def commercial_document_status_route(document_id: str, payload: CommercialDocumentStatusUpdateRequest, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        doc = fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,))
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        ensure_org_access(user, doc["organization_id"])
        _require_permission(user, doc["organization_id"], "crm.manage")
        return update_commercial_document_status(conn, document_id, status=payload.status, actor_user=user, note=payload.note, metadata=payload.metadata)


def commercial_document_convert_to_work_order_route(document_id: str, user: dict = Depends(get_current_user)) -> dict:
    with get_connection() as conn:
        doc = fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,))
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        ensure_org_access(user, doc["organization_id"])
        _require_permission(user, doc["organization_id"], "crm.manage")
        return convert_quote_to_work_order(conn, document_id, actor_user=user)


def organization_branding_get_route(organization_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict:
    org_id = _resolve_org_or_400(user, organization_id)
    with get_connection() as conn:
        return get_organization_branding(conn, org_id)


def organization_branding_upsert_route(payload: OrganizationBrandingRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return upsert_organization_branding(conn, actor_user=user, **payload.model_dump())


def catalog_quote_rules_list_route(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    catalog_item_type: str | None = Query(default=None),
    catalog_item_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    org_id = _resolve_org_or_400(user, organization_id)
    with get_connection() as conn:
        return list_catalog_quote_rules(conn, org_id, bot_id=bot_id, catalog_item_type=catalog_item_type, catalog_item_id=catalog_item_id)


def catalog_quote_rules_create_route(payload: CatalogQuoteRuleRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return create_catalog_quote_rule(conn, actor_user=user, **payload.model_dump())


def commercial_document_send_route(document_id: str, payload: CommercialDocumentSendRequest | None = None, user: dict = Depends(get_current_user)) -> dict:
    payload = payload or CommercialDocumentSendRequest()
    with get_connection() as conn:
        doc = fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,))
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        ensure_org_access(user, doc["organization_id"])
        _require_permission(user, doc["organization_id"], "crm.manage")
        return send_document(conn, document_id, actor_user=user, message_body=payload.message_body, create_payment=payload.create_payment)


def commercial_document_accept_route(document_id: str, payload: CommercialDocumentAcceptRequest | None = None, user: dict = Depends(get_current_user)) -> dict:
    payload = payload or CommercialDocumentAcceptRequest()
    with get_connection() as conn:
        doc = fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,))
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        ensure_org_access(user, doc["organization_id"])
        _require_permission(user, doc["organization_id"], "crm.manage")
        return accept_document(conn, document_id, actor_user=user, metadata=payload.metadata)


def commercial_document_payment_route(document_id: str, payload: CommercialDocumentPaymentRequest | None = None, user: dict = Depends(get_current_user)) -> dict:
    payload = payload or CommercialDocumentPaymentRequest()
    with get_connection() as conn:
        doc = fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,))
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        ensure_org_access(user, doc["organization_id"])
        _require_permission(user, doc["organization_id"], "revenue.manage")
        return create_payment_for_document(conn, document_id, actor_user=user, amount_mode=payload.amount_mode)


def public_commercial_document_view_route(document_id: str, token: str | None = Query(default=None)) -> HTMLResponse:
    with get_connection() as conn:
        doc = get_public_document(conn, document_id, token)
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        pdf_url = f"/api/public/commercial-documents/{document_id}/pdf?token={token or ''}"
        accept_url = f"/api/public/commercial-documents/{document_id}/accept?token={token or ''}"
        payment = doc.get("payment_url") or ""
        rows = "".join(f"<tr><td>{_html.escape(str(item.get('name') or ''))}</td><td>{_html.escape(str(item.get('quantity') or 1))}</td><td>{_html.escape(str(item.get('unit') or ''))}</td><td>{_html.escape(str(item.get('total') or 0))}</td></tr>" for item in doc.get("items", []))
        payment_link = f"<a class='btn secondary' href='{_html.escape(str(payment), quote=True)}'>Pagar anticipo</a>" if payment else ""
        style_nonce = _smart_docs_style_nonce()
        html = f"""
        <html><head><meta charset='utf-8'><title>{_html.escape(str(doc.get('folio') or 'Documento'))}</title>
        <style nonce='{_html.escape(style_nonce, quote=True)}'>body{{font-family:Arial,sans-serif;background:#f6f7fb;color:#111827;margin:0;padding:32px}}.card{{max-width:860px;margin:auto;background:white;border-radius:24px;padding:28px;box-shadow:0 20px 50px rgba(15,23,42,.12)}}.muted{{color:#6b7280}}.btn{{display:inline-block;margin:8px 8px 0 0;padding:12px 16px;border-radius:999px;background:#111827;color:white;text-decoration:none;font-weight:700}}.secondary{{background:#25D366;color:#07110b}}table{{width:100%;border-collapse:collapse;margin-top:16px}}td,th{{padding:10px;border-bottom:1px solid #e5e7eb;text-align:left}}</style></head>
        <body><main class='card'><p class='muted'>WAOS Smart Docs</p><h1>{_html.escape(str(doc.get('folio') or ''))} - {_html.escape(str(doc.get('title') or 'Documento comercial'))}</h1><p>{_html.escape(str(doc.get('summary') or ''))}</p><h2>Total: {_html.escape(str(doc.get('currency') or 'MXN'))} {float(doc.get('total') or 0):,.2f}</h2><p>Estado: <b>{_html.escape(str(doc.get('status') or ''))}</b></p><table><thead><tr><th>Concepto</th><th>Cantidad</th><th>Unidad</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table><p class='muted'>{_html.escape(str(doc.get('terms') or ''))}</p><a class='btn' href='{_html.escape(pdf_url, quote=True)}'>Abrir PDF</a><a class='btn secondary' href='{_html.escape(accept_url, quote=True)}'>Aceptar presupuesto</a>{payment_link}</main></body></html>
        """
        return HTMLResponse(html, headers=_smart_docs_security_headers(style_nonce=style_nonce))


def public_commercial_document_pdf_route(document_id: str, token: str | None = Query(default=None)):
    with get_connection() as conn:
        doc = public_pdf_path(conn, document_id, token)
        if not doc:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        return FileResponse(str(doc.get("pdf_path")), media_type="application/pdf", filename=doc.get("pdf_filename") or f"waos-{document_id}.pdf")


def public_commercial_document_accept_route(document_id: str, token: str | None = Query(default=None)) -> HTMLResponse:
    with get_connection() as conn:
        result = accept_document(conn, document_id, token=token)
        if not result:
            raise HTTPException(status_code=404, detail="commercial_document_not_found")
        doc = result.get("document") or {}
        payment = result.get("payment") or {}
        payment_url = doc.get("payment_url") or payment.get("payment_link_url") or ""
        payment_html = f"<p><a class='btn' href='{_html.escape(str(payment_url), quote=True)}'>Pagar anticipo</a></p>" if payment_url else ""
        style_nonce = _smart_docs_style_nonce()
        html = f"""<html><head><meta charset='utf-8'><style nonce='{_html.escape(style_nonce, quote=True)}'>body{{font-family:Arial,sans-serif;background:#f6f7fb;color:#111827;padding:32px}}.card{{max-width:680px;margin:auto;background:white;border-radius:24px;padding:28px;box-shadow:0 20px 50px rgba(15,23,42,.12)}}.btn{{display:inline-block;padding:12px 16px;border-radius:999px;background:#25D366;color:#07110b;text-decoration:none;font-weight:700}}</style></head><body><main class='card'><h1>Presupuesto aceptado</h1><p>Gracias. El documento {_html.escape(str(doc.get('folio') or ''))} quedo aceptado.</p>{payment_html}<p>El equipo puede continuar con el siguiente paso operativo.</p></main></body></html>"""
        return HTMLResponse(html, headers=_smart_docs_security_headers(style_nonce=style_nonce))
