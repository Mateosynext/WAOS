from __future__ import annotations

import time
from typing import Any

from ..config import settings
from ..repositories.base import execute, fetch_all, fetch_one
from ..utils import from_json, sign_payload, to_json, utcnow_iso, verify_signed_payload
from .commercial_documents import (
    DEFAULT_TERMS,
    DOC_TYPE_LABEL,
    _document_with_items,
    _money,
    _record_event,
    build_commercial_document_pdf,
    convert_quote_to_work_order,
    create_commercial_document,
    draft_commercial_document_from_conversation,
    ensure_commercial_document_pdf,
    get_organization_branding,
    update_commercial_document_status,
)


def _base_url() -> str:
    return (settings.api_base_url or settings.public_app_url or "").rstrip("/")


def _latest_document_by_metadata(
    conn,
    *,
    organization_id: str,
    key: str,
    value: Any,
    document_type: str | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    if value is None:
        return {}
    where = ["organization_id = ?"]
    params: list[Any] = [organization_id]
    if document_type:
        where.append("document_type = ?")
        params.append(document_type)
    if conversation_id:
        where.append("conversation_id = ?")
        params.append(conversation_id)
    rows = fetch_all(
        conn,
        f"SELECT * FROM commercial_documents WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 100",
        params,
    )
    expected = str(value)
    for row in rows:
        metadata = from_json(row.get("metadata_json"), {})
        if str(metadata.get(key)) == expected:
            return row
    return {}


def _public_token(document: dict[str, Any], *, days: int = 30) -> str:
    return sign_payload(
        {
            "sub": "commercial_document",
            "document_id": document.get("id"),
            "organization_id": document.get("organization_id"),
            "action": "view",
            "exp": int(time.time()) + max(1, int(days)) * 24 * 60 * 60,
        },
        settings.app_secret,
    )


def ensure_public_url(conn, document_or_id: dict | str) -> str:
    document = _document_with_items(conn, document_or_id) if isinstance(document_or_id, str) else dict(document_or_id)
    if not document:
        return ""
    if document.get("public_url"):
        return str(document.get("public_url"))
    token = _public_token(document)
    public_url = f"{_base_url()}/api/public/commercial-documents/{document['id']}?token={token}"
    execute(conn, "UPDATE commercial_documents SET public_url = ?, updated_at = ? WHERE id = ?", (public_url, utcnow_iso(), document["id"]))
    _record_event(conn, organization_id=document["organization_id"], document_id=document["id"], event_type="public_url.created", metadata={"expires_days": 30})
    return public_url


def _verify_public_token(document: dict[str, Any], token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    payload = verify_signed_payload(token, settings.app_secret)
    if not payload:
        return None
    if payload.get("sub") != "commercial_document":
        return None
    if payload.get("document_id") != document.get("id"):
        return None
    if payload.get("organization_id") != document.get("organization_id"):
        return None
    return payload


def get_public_document(conn, document_id: str, token: str | None) -> dict:
    document = _document_with_items(conn, document_id)
    if not document or not _verify_public_token(document, token):
        return {}
    if document.get("status") == "sent":
        update_commercial_document_status(conn, document_id, status="viewed", metadata={"source": "public_link"})
        document = _document_with_items(conn, document_id)
    return document


def public_pdf_path(conn, document_id: str, token: str | None) -> dict:
    document = get_public_document(conn, document_id, token)
    if not document:
        return {}
    if not document.get("pdf_path"):
        document = ensure_commercial_document_pdf(conn, document_id)
    return document


def create_payment_for_document(conn, document_id: str, *, actor_user: dict | None = None, amount_mode: str = "deposit") -> dict:
    document = _document_with_items(conn, document_id)
    if not document:
        return {}
    metadata = dict(document.get("metadata") or {})
    existing_payment_id = metadata.get("payment_id")
    if existing_payment_id:
        existing = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (existing_payment_id,))
        if existing:
            return existing
    if not document.get("conversation_id") or not document.get("contact_id") or not document.get("bot_id"):
        _record_event(conn, organization_id=document["organization_id"], document_id=document_id, event_type="payment.skipped", metadata={"reason": "missing_context"})
        return {}
    amount = float(document.get("deposit_required") or 0) if amount_mode == "deposit" else 0.0
    if amount <= 0:
        amount = float(document.get("balance_due") or document.get("total") or 0)
    if amount <= 0:
        _record_event(conn, organization_id=document["organization_id"], document_id=document_id, event_type="payment.skipped", metadata={"reason": "amount_zero"})
        return {}
    from .payments import create_payment_request

    payment = create_payment_request(
        conn,
        organization_id=document["organization_id"],
        bot_id=document["bot_id"],
        conversation_id=document["conversation_id"],
        contact_id=document["contact_id"],
        title=f"{document.get('folio')} - {document.get('title')}",
        amount=amount,
        currency=document.get("currency") or "MXN",
        reminder_minutes=60,
        send_receipt_on_confirm=True,
        actor_user=actor_user,
        metadata={
            "commercial_document_id": document_id,
            "commercial_document_folio": document.get("folio"),
            "amount_mode": amount_mode,
            "source": "waos_smart_docs",
        },
    )
    payment_url = payment.get("payment_link_url") or payment.get("checkout_url") or payment.get("payment_url")
    execute(
        conn,
        "UPDATE commercial_documents SET payment_url = ?, metadata_json = ?, updated_at = ? WHERE id = ?",
        (payment_url, to_json({**metadata, "payment_id": payment.get("id"), "payment_status": payment.get("status"), "payment_amount": amount}), utcnow_iso(), document_id),
    )
    _record_event(conn, organization_id=document["organization_id"], document_id=document_id, event_type="payment.created", actor_type="user" if actor_user else "system", actor_id=actor_user.get("id") if actor_user else None, metadata={"payment_id": payment.get("id"), "amount": amount, "payment_url": payment_url})
    return payment


def compose_customer_message(document: dict[str, Any], *, public_url: str | None = None, payment_url: str | None = None) -> str:
    currency = document.get("currency") or "MXN"
    label = DOC_TYPE_LABEL.get(document.get("document_type"), "Documento comercial")
    lines = [
        f"Te comparto tu {label.lower()} {document.get('folio')}.",
        f"Total: {_money(document.get('total'), currency)}.",
    ]
    if float(document.get("deposit_required") or 0) > 0:
        lines.append(f"Anticipo para avanzar: {_money(document.get('deposit_required'), currency)}.")
    if public_url:
        lines.append(f"Ver documento: {public_url}")
    if payment_url:
        lines.append(f"Pagar anticipo: {payment_url}")
    if document.get("status") in {"requires_data", "requires_approval"}:
        lines.append("Este borrador queda sujeto a validacion antes de enviarse como precio final.")
    return "\n".join(lines)


def send_document(conn, document_id: str, *, actor_user: dict | None = None, message_body: str | None = None, create_payment: bool = True) -> dict:
    document = _document_with_items(conn, document_id)
    if not document:
        return {}
    public_url = ensure_public_url(conn, document)
    payment = {}
    if create_payment and float(document.get("deposit_required") or 0) > 0 and document.get("status") not in {"requires_data", "requires_approval"}:
        payment = create_payment_for_document(conn, document_id, actor_user=actor_user, amount_mode="deposit")
        document = _document_with_items(conn, document_id)
    if not document.get("conversation_id") or not document.get("bot_id"):
        _record_event(conn, organization_id=document["organization_id"], document_id=document_id, event_type="send.skipped", metadata={"reason": "missing_conversation_or_bot"})
        return {"document": document, "payment": payment, "sent": False, "reason": "missing_context"}
    body = message_body or compose_customer_message(document, public_url=public_url, payment_url=document.get("payment_url") or payment.get("payment_link_url"))
    from ..whatsapp import enqueue_manual_whatsapp_message

    queued = enqueue_manual_whatsapp_message(
        conn,
        organization_id=document["organization_id"],
        bot_id=document["bot_id"],
        conversation_id=document["conversation_id"],
        contact_id=document.get("contact_id"),
        body=body,
        author_user_id=actor_user.get("id") if actor_user else None,
    )
    update_commercial_document_status(conn, document_id, status="sent", actor_user=actor_user, metadata={"outbox_id": queued.get("outbox_id"), "message_id": (queued.get("message") or {}).get("id"), "source": "smart_docs_send"})
    return {"document": _document_with_items(conn, document_id), "payment": payment, "sent": True, "outbox": queued, "body": body}


def accept_document(conn, document_id: str, *, actor_user: dict | None = None, token: str | None = None, metadata: dict[str, Any] | None = None) -> dict:
    document = _document_with_items(conn, document_id)
    if not document:
        return {}
    if token and not _verify_public_token(document, token):
        return {}
    document = update_commercial_document_status(conn, document_id, status="accepted", actor_user=actor_user, metadata={"source": "public_accept" if token else "internal_accept", **(metadata or {})})
    payment = {}
    work_order = {}
    if float(document.get("deposit_required") or 0) > 0 or float(document.get("total") or 0) > 0:
        payment = create_payment_for_document(conn, document_id, actor_user=actor_user, amount_mode="deposit")
    if not payment and document.get("document_type") == "quote":
        work_order = convert_quote_to_work_order(conn, document_id, actor_user=actor_user)
    return {"document": _document_with_items(conn, document_id), "payment": payment, "work_order": work_order}


def mark_document_paid_from_payment(conn, payment: dict[str, Any]) -> dict:
    metadata = from_json(payment.get("metadata_json"), {})
    document_id = metadata.get("commercial_document_id")
    if not document_id:
        return {}
    document = _document_with_items(conn, document_id)
    if not document:
        return {}
    document = update_commercial_document_status(conn, document_id, status="paid", metadata={"payment_id": payment.get("id"), "source": "payment_confirmed"})
    work_order = {}
    if document.get("document_type") == "quote":
        existing_work_order = _latest_document_by_metadata(conn, organization_id=document["organization_id"], key="source_quote_id", value=document_id, document_type="work_order")
        work_order = _document_with_items(conn, existing_work_order["id"]) if existing_work_order else convert_quote_to_work_order(conn, document_id)
    existing_receipt = _latest_document_by_metadata(conn, organization_id=document["organization_id"], key="source_payment_id", value=payment.get("id"), document_type="receipt")
    if existing_receipt:
        receipt = _document_with_items(conn, existing_receipt["id"])
    else:
        receipt = create_commercial_document(
            conn,
            organization_id=document["organization_id"],
            bot_id=document.get("bot_id"),
            conversation_id=document.get("conversation_id"),
            contact_id=document.get("contact_id"),
            document_type="receipt",
            status="paid",
            title=f"Recibo de pago de {document.get('folio')}",
            customer_name=document.get("customer_name"),
            customer_phone=document.get("customer_phone"),
            customer_email=document.get("customer_email"),
            customer_address=document.get("customer_address"),
            summary=f"Pago confirmado para {document.get('folio')}. Referencia: {payment.get('provider_reference') or payment.get('id')}.",
            currency=payment.get("currency") or document.get("currency") or "MXN",
            terms=DEFAULT_TERMS["receipt"],
            next_actions=["Enviar recibo al cliente.", "Mantener orden de trabajo y garantia conectadas al folio original."],
            metadata={"source_document_id": document_id, "source_document_folio": document.get("folio"), "source_payment_id": payment.get("id")},
            items=[{
                "source_type": "custom",
                "source_id": payment.get("id"),
                "name": f"Pago confirmado - {document.get('folio')}",
                "description": payment.get("title") or document.get("title") or "Pago confirmado",
                "quantity": 1,
                "unit": "pago",
                "unit_price": float(payment.get("amount") or 0),
                "discount": 0,
                "tax": 0,
                "metadata": {"payment_id": payment.get("id"), "provider_reference": payment.get("provider_reference")},
            }],
        )
    receipt = ensure_commercial_document_pdf(conn, receipt)
    receipt_public_url = ensure_public_url(conn, receipt)
    if document.get("conversation_id") and document.get("bot_id") and not metadata.get("smart_docs_receipt_sent_at"):
        queued = {}
        try:
            from ..whatsapp import enqueue_manual_whatsapp_message

            queued = enqueue_manual_whatsapp_message(
                conn,
                organization_id=document["organization_id"],
                bot_id=document["bot_id"],
                conversation_id=document["conversation_id"],
                contact_id=document.get("contact_id"),
                body=f"Gracias, tu pago de {payment.get('currency') or document.get('currency') or 'MXN'} {float(payment.get('amount') or 0):,.2f} quedo confirmado. Te comparto tu recibo formal: {receipt_public_url}",
                author_user_id=None,
            )
        except Exception as exc:
            queued = {"error": str(exc)}
        metadata = {**metadata, "smart_docs_receipt_sent_at": utcnow_iso(), "smart_docs_receipt_id": receipt.get("id")}
        execute(conn, "UPDATE commerce_payments SET metadata_json = ?, updated_at = ? WHERE id = ?", (to_json(metadata), utcnow_iso(), payment.get("id")))
        _record_event(conn, organization_id=document["organization_id"], document_id=receipt["id"], event_type="receipt.sent", metadata={"payment_id": payment.get("id"), "public_url": receipt_public_url, "outbox_id": queued.get("outbox_id")})
    return {"document": _document_with_items(conn, document_id), "work_order": work_order, "receipt": receipt}


def _commercial_intent_detected(text: str, classification: dict[str, Any]) -> bool:
    lower = (text or "").lower()
    if classification.get("intent") in {"pricing", "payment"}:
        return True
    return any(token in lower for token in [
        "cotiz", "presupuesto", "cuanto cuesta", "precio", "orden de trabajo", "recibo", "comprobante", "propuesta", "garantia", "pagar", "anticipo"
    ])


def build_reply_addendum(document: dict[str, Any]) -> str:
    if not document:
        return ""
    if document.get("status") == "requires_data":
        questions = document.get("missing_questions") or []
        if questions:
            return "\n\nPara prepararte el presupuesto formal necesito confirmar: " + "; ".join(questions[:3]) + "."
        return "\n\nYa abri un borrador de presupuesto, pero necesito algunos datos antes de cerrarlo."
    if document.get("status") == "requires_approval":
        reasons = document.get("approval_reasons") or []
        detail = f" Motivo: {reasons[0]}" if reasons else ""
        return f"\n\nYa prepare el borrador {document.get('folio')} para revision interna antes de enviarlo como precio final.{detail}"
    public_url = document.get("public_url") or ""
    payment_url = document.get("payment_url") or ""
    parts = [f"\n\nTe prepare el documento formal {document.get('folio')} con desglose y condiciones."]
    if public_url:
        parts.append(f"Ver documento: {public_url}")
    if payment_url:
        parts.append(f"Pagar anticipo: {payment_url}")
    return "\n".join(parts)


def maybe_run_runtime(
    conn,
    *,
    incoming_message: dict[str, Any],
    conversation: dict[str, Any],
    bot: dict[str, Any],
    contact: dict[str, Any],
    classification: dict[str, Any],
    bot_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bot_config = bot_config or {}
    smart_config = bot_config.get("commercial_documents") or bot_config.get("smart_docs") or {}
    if smart_config.get("enabled") is False:
        return {"triggered": False, "reason": "disabled"}
    text = str(incoming_message.get("body") or "")
    if not _commercial_intent_detected(text, classification):
        return {"triggered": False, "reason": "no_commercial_intent"}
    existing = _latest_document_by_metadata(
        conn,
        organization_id=conversation["organization_id"],
        conversation_id=conversation.get("id"),
        key="source_message_id",
        value=incoming_message.get("id"),
    )
    if existing:
        return {"triggered": False, "reason": "already_processed", "document": _document_with_items(conn, existing["id"])}
    document_type = "receipt" if any(token in text.lower() for token in ["recibo", "comprobante"]) else "quote"
    document = draft_commercial_document_from_conversation(
        conn,
        organization_id=conversation["organization_id"],
        bot_id=bot["id"],
        conversation_id=conversation["id"],
        contact_id=contact.get("id"),
        request_text=text,
        document_type=document_type,
        customer_name=contact.get("name"),
        customer_phone=contact.get("phone"),
        auto_generate_pdf=True,
        metadata={"source": "ai_runtime", "source_message_id": incoming_message.get("id"), "classification_intent": classification.get("intent")},
    )
    ensure_public_url(conn, document)
    document = _document_with_items(conn, document["id"])
    auto_send = bool(smart_config.get("auto_send_quotes", True))
    send_result = {}
    if auto_send and document.get("status") not in {"requires_data", "requires_approval"} and float(document.get("total") or 0) > 0:
        send_result = send_document(conn, document["id"], create_payment=True)
        document = send_result.get("document") or _document_with_items(conn, document["id"])
    return {"triggered": True, "document": document, "send_result": send_result, "reply_addendum": build_reply_addendum(document)}
