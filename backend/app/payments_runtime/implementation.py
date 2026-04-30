from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any
from urllib.parse import urlencode

import httpx

from ..config import settings
from ..db import execute, fetch_one
from ..integration_observability import record_integration_event
from ..platform import resolve_secret
from ..utils import RetryableProviderError, add_minutes, from_json, parse_iso, to_json, utcnow_iso

STRIPE_API_BASE = "https://api.stripe.com/v1"


def _fake_providers_enabled() -> bool:
    from ..config import settings
    if settings.is_production and settings.waos_e2e_fake_providers:
        raise RuntimeError("WAOS_E2E_FAKE_PROVIDERS cannot be enabled in production")
    return bool(settings.waos_e2e_fake_providers)


def _payment_metadata(payment: dict[str, Any]) -> dict[str, Any]:
    return from_json(payment.get("metadata_json"), {})


def _payment_integration(conn, *, organization_id: str, bot_id: str | None) -> dict[str, Any] | None:
    if bot_id:
        row = fetch_one(
            conn,
            """
            SELECT * FROM integration_connections
            WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '')
              AND integration_type IN ('payments', 'commerce', 'crm')
              AND provider IN ('stripe')
              AND status IN ('active', 'configured')
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (organization_id, bot_id),
        )
        if row:
            return row
    return fetch_one(
        conn,
        """
        SELECT * FROM integration_connections
        WHERE organization_id = ?
          AND bot_id IS NULL
          AND integration_type IN ('payments', 'commerce', 'crm')
          AND provider IN ('stripe')
          AND status IN ('active', 'configured')
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (organization_id,),
    )


def _integration_config(integration: dict[str, Any]) -> dict[str, Any]:
    if isinstance(integration.get("config"), dict):
        return integration["config"]
    return from_json(integration.get("config_json"), {})


def _stripe_secret_key(conn, integration: dict[str, Any]) -> str | None:
    config = _integration_config(integration)
    return config.get("secret_key") or resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="STRIPE_SECRET_KEY")


def _stripe_webhook_secret(conn, integration: dict[str, Any]) -> str | None:
    config = _integration_config(integration)
    return config.get("webhook_secret") or resolve_secret(conn, organization_id=integration["organization_id"], bot_id=integration.get("bot_id"), key_name="STRIPE_WEBHOOK_SECRET")


def _stripe_headers(conn, integration: dict[str, Any], *, idempotency_key: str | None = None) -> dict[str, str]:
    secret = _stripe_secret_key(conn, integration)
    if not secret:
        raise RetryableProviderError("missing_stripe_secret_key", retryable=False)
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = str(idempotency_key)[:255]
    return headers


def _flatten(prefix: str, value: Any, out: dict[str, str]) -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            _flatten(f"{prefix}[{key}]", inner, out)
    elif isinstance(value, list):
        for idx, inner in enumerate(value):
            _flatten(f"{prefix}[{idx}]", inner, out)
    elif value is None:
        return
    else:
        out[prefix] = str(value)


def _encode_form(data: dict[str, Any]) -> str:
    flat: dict[str, str] = {}
    for key, value in data.items():
        _flatten(key, value, flat)
    return urlencode(flat)


def _update_payment(conn, payment_id: str, **fields: Any) -> dict[str, Any]:
    if not fields:
        return fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
    assignments = []
    params: list[Any] = []
    for key, value in fields.items():
        assignments.append(f"{key} = ?")
        params.append(value)
    assignments.append("updated_at = ?")
    params.append(utcnow_iso())
    params.append(payment_id)
    execute(conn, f"UPDATE commerce_payments SET {', '.join(assignments)} WHERE id = ?", params)
    return fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))


def _reconcile_payment_with_appointments(conn, payment: dict[str, Any]) -> dict[str, Any]:
    appointment = None
    metadata = _payment_metadata(payment)
    appointment_id = payment.get("appointment_id") or metadata.get("appointment_id")
    if appointment_id:
        appointment = fetch_one(conn, "SELECT * FROM appointments WHERE id = ? AND organization_id = ?", (appointment_id, payment["organization_id"]))
    if not appointment and payment.get("conversation_id"):
        appointment = fetch_one(
            conn,
            "SELECT * FROM appointments WHERE organization_id = ? AND conversation_id = ? ORDER BY scheduled_for ASC LIMIT 1",
            (payment["organization_id"], payment.get("conversation_id")),
        )
    if not appointment and payment.get("contact_id"):
        appointment = fetch_one(
            conn,
            "SELECT * FROM appointments WHERE organization_id = ? AND contact_id = ? ORDER BY scheduled_for ASC LIMIT 1",
            (payment["organization_id"], payment.get("contact_id")),
        )
    status = "matched" if appointment else "unmatched"
    if appointment:
        execute(
            conn,
            "UPDATE appointments SET payment_id = ?, payment_status = ?, reconciliation_status = ?, updated_at = ? WHERE id = ?",
            (payment["id"], payment.get("status") or "pending", status, utcnow_iso(), appointment["id"]),
        )
    updated = _update_payment(
        conn,
        payment["id"],
        appointment_id=appointment.get("id") if appointment else payment.get("appointment_id"),
        reconciliation_status=status,
        reconciled_at=utcnow_iso(),
    )
    return {"appointment_id": appointment.get("id") if appointment else None, "reconciliation_status": status, "payment": updated}


def create_provider_checkout(conn, payment: dict[str, Any]) -> dict[str, Any]:
    if payment.get("payment_link_status") == "ready" and payment.get("payment_link_url") and payment.get("external_payment_id"):
        return {"payment": payment, "provider_ready": True, "provider": payment.get("provider") or "existing", "idempotent": True}
    integration = _payment_integration(conn, organization_id=payment["organization_id"], bot_id=payment.get("bot_id"))
    if not integration:
        updated = _update_payment(
            conn,
            payment["id"],
            provider="unconfigured",
            payment_link_status="provider_required",
            status="pending_provider",
            operational_status="provider_pending",
            provider_status="missing_provider",
            provider_response_json=to_json({"error": "missing_payment_integration"}),
            next_reconciliation_at=add_minutes(utcnow_iso(), 10),
            last_reconciliation_error="missing_payment_integration",
        )
        return {"payment": updated, "provider_ready": False, "reason": "missing_payment_integration"}
    if integration.get("provider") != "stripe":
        raise RetryableProviderError("unsupported_payment_provider", retryable=False, details={"provider": integration.get("provider")})
    config = _integration_config(integration)
    metadata = _payment_metadata(payment)
    provider_idempotency_key = str(metadata.get("tool_execution_idempotency_key") or metadata.get("idempotency_key") or f"payment:{payment['id']}").strip()
    if _fake_providers_enabled():
        fake_session_id = f"cs_fake_{payment['id']}"
        fake_intent = f"pi_fake_{payment['id']}"
        fake_url = f"{settings.public_app_url.rstrip('/')}/revenue?checkout_session_id={fake_session_id}"
        updated = _update_payment(
            conn,
            payment["id"],
            provider="stripe",
            integration_id=integration["id"],
            payment_link_url=fake_url,
            payment_link_status="ready",
            provider_reference=fake_intent,
            external_payment_id=fake_session_id,
            provider_status="open",
            provider_status_code=200,
            provider_response_json=to_json({"id": fake_session_id, "payment_intent": fake_intent, "url": fake_url, "status": "open", "payment_status": "unpaid"}),
            checkout_expires_at=add_minutes(utcnow_iso(), int(config.get("checkout_ttl_minutes") or 60)),
            next_reconciliation_at=add_minutes(utcnow_iso(), 10),
            reconciliation_attempts=0,
            last_reconciliation_error=None,
            status="pending",
            operational_status="provider_confirmed",
        )
        record_integration_event(
            conn,
            organization_id=payment["organization_id"],
            integration_id=integration["id"],
            bot_id=payment.get("bot_id"),
            provider="stripe",
            event_type="checkout.create",
            status="ok",
            summary="fake stripe checkout created for browser e2e",
            request_payload={"payment_id": payment["id"], "amount": payment.get("amount"), "idempotency_key": provider_idempotency_key},
            response_payload={"session_id": fake_session_id, "payment_intent": fake_intent, "url": fake_url},
            external_reference=fake_session_id,
            provider_status_code=200,
        )
        return {"payment": updated, "provider_ready": True, "provider": "stripe", "fake": True}
    success_url = config.get("success_url") or f"{settings.public_app_url.rstrip('/')}/revenue?payment={{CHECKOUT_SESSION_ID}}"
    cancel_url = config.get("cancel_url") or f"{settings.public_app_url.rstrip('/')}/revenue?payment_cancelled={payment['id']}"
    expires_at = add_minutes(utcnow_iso(), int(config.get("checkout_ttl_minutes") or 60))
    form = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "expires_at": int(parse_iso(expires_at).timestamp()) if parse_iso(expires_at) else "",
        "client_reference_id": payment["id"],
        "metadata": {
            "payment_id": payment["id"],
            "organization_id": payment["organization_id"],
            "conversation_id": payment.get("conversation_id") or "",
            "contact_id": payment.get("contact_id") or "",
            "appointment_id": payment.get("appointment_id") or _payment_metadata(payment).get("appointment_id") or "",
        },
        "line_items": [
            {
                "quantity": 1,
                "price_data": {
                    "currency": (payment.get("currency") or "MXN").lower(),
                    "unit_amount": int(round(float(payment.get("amount") or 0) * 100)),
                    "product_data": {"name": payment.get("title") or f"Pago {payment['id']}"},
                },
            }
        ],
        "payment_intent_data": {
            "metadata": {
                "payment_id": payment["id"],
                "organization_id": payment["organization_id"],
            }
        },
    }
    body = _encode_form(form)
    try:
        response = httpx.post(
            f"{STRIPE_API_BASE}/checkout/sessions",
            headers=_stripe_headers(conn, integration, idempotency_key=provider_idempotency_key),
            content=body,
            timeout=30.0,
        )
        data = response.json()
    except Exception as exc:
        record_integration_event(
            conn,
            organization_id=payment["organization_id"],
            integration_id=integration["id"],
            bot_id=payment.get("bot_id"),
            provider="stripe",
            event_type="checkout.create",
            status="failed",
            severity="error",
            summary="stripe checkout request failed",
            error_payload={"message": str(exc)},
        )
        updated = _update_payment(
            conn,
            payment["id"],
            provider="stripe",
            integration_id=integration["id"],
            payment_link_status="provider_timeout",
            provider_status="timeout",
            provider_response_json=to_json({"error": str(exc)}),
            status="pending_provider",
            operational_status="retrying",
            next_reconciliation_at=add_minutes(utcnow_iso(), 5),
            last_reconciliation_error=str(exc),
        )
        return {"payment": updated, "provider_ready": False, "reason": "provider_timeout", "retryable": True}
    if response.status_code >= 400:
        record_integration_event(
            conn,
            organization_id=payment["organization_id"],
            integration_id=integration["id"],
            bot_id=payment.get("bot_id"),
            provider="stripe",
            event_type="checkout.create",
            status="failed",
            severity="error",
            summary="stripe checkout rejected",
            request_payload={"payment_id": payment["id"], "amount": payment.get("amount"), "idempotency_key": provider_idempotency_key},
            response_payload=data,
            error_payload=data,
            provider_status_code=response.status_code,
        )
        updated = _update_payment(
            conn,
            payment["id"],
            provider="stripe",
            integration_id=integration["id"],
            payment_link_status="provider_error",
            provider_status="failed",
            provider_status_code=response.status_code,
            provider_response_json=to_json(data),
            status="pending_provider",
            operational_status="provider_failed",
            next_reconciliation_at=add_minutes(utcnow_iso(), 15),
            last_reconciliation_error=str(data),
        )
        return {"payment": updated, "provider_ready": False, "reason": "provider_error", "provider_response": data}
    updated = _update_payment(
        conn,
        payment["id"],
        provider="stripe",
        integration_id=integration["id"],
        payment_link_url=data.get("url"),
        payment_link_status="ready",
        provider_reference=data.get("payment_intent") or data.get("id"),
        external_payment_id=data.get("id"),
        provider_status=data.get("payment_status") or data.get("status") or "open",
        provider_status_code=response.status_code,
        provider_response_json=to_json(data),
        checkout_expires_at=expires_at,
        next_reconciliation_at=add_minutes(utcnow_iso(), 10),
        reconciliation_attempts=0,
        last_reconciliation_error=None,
        status="pending",
        operational_status="provider_confirmed",
    )
    execute(
        conn,
        "UPDATE integration_connections SET health_status = 'healthy', credential_status = 'connected', last_error = NULL, last_provider_event_at = ?, last_provider_status_code = ?, updated_at = ? WHERE id = ?",
        (utcnow_iso(), response.status_code, utcnow_iso(), integration["id"]),
    )
    record_integration_event(
        conn,
        organization_id=payment["organization_id"],
        integration_id=integration["id"],
        bot_id=payment.get("bot_id"),
        provider="stripe",
        event_type="checkout.create",
        status="ok",
        summary="stripe checkout created",
        request_payload={"payment_id": payment["id"], "amount": payment.get("amount"), "idempotency_key": provider_idempotency_key},
        response_payload={"session_id": data.get("id"), "payment_intent": data.get("payment_intent"), "url": data.get("url")},
        external_reference=data.get("id"),
        provider_status_code=response.status_code,
    )
    return {"payment": updated, "provider_ready": True, "provider": "stripe"}


def _mark_payment_paid(conn, payment: dict[str, Any], *, provider_reference: str | None, provider_payload: dict[str, Any] | None, provider_status: str = "paid") -> dict[str, Any]:
    metadata = _payment_metadata(payment)
    metadata.update({"provider_payload": provider_payload or {}, "provider_reference": provider_reference})
    updated = _update_payment(
        conn,
        payment["id"],
        status="paid",
        operational_status="provider_confirmed",
        payment_link_status="paid",
        provider_status=provider_status,
        provider_reference=provider_reference,
        provider_response_json=to_json(provider_payload or {}),
        confirmed_at=utcnow_iso(),
        paid_at=utcnow_iso(),
        next_reconciliation_at=None,
        last_reconciliation_error=None,
        metadata_json=to_json(metadata),
    )
    updated = _reconcile_payment_with_appointments(conn, updated)["payment"]
    account_id = metadata.get("vertical_transaction_account_id")
    if account_id:
        from .vertical_transactions import sync_account_payment_status
        sync_account_payment_status(conn, account_id=account_id, payment_id=updated["id"])

    # Smart Docs E2E bridge: when Stripe or reconciliation confirms a payment,
    # close the linked commercial document flow as well. This makes provider
    # webhooks, manual refreshes and scheduled reconciliation produce the same
    # outcome as an internal payment confirmation: quote -> paid -> work order -> receipt PDF.
    try:
        commercial_document_id = metadata.get("commercial_document_id")
        if commercial_document_id:
            from ..domains.commercial_documents_e2e import mark_document_paid_from_payment

            mark_document_paid_from_payment(conn, updated)
    except Exception:
        # Payment confirmation must remain durable even if a document side-effect fails.
        # The event can be repaired by refreshing/reconciling the payment again.
        pass
    return updated

def refresh_payment_status(conn, payment_id: str) -> dict[str, Any]:
    payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
    if not payment:
        raise ValueError("payment_not_found")
    if payment.get("provider") != "stripe":
        return payment
    integration = _payment_integration(conn, organization_id=payment["organization_id"], bot_id=payment.get("bot_id"))
    if not integration:
        return payment
    external_id = payment.get("external_payment_id")
    if not external_id:
        return payment
    if _fake_providers_enabled():
        if payment.get("status") == "paid":
            return payment
        return _update_payment(conn, payment_id, provider_status=payment.get("provider_status") or "open", provider_response_json=payment.get("provider_response_json"), provider_status_code=200, next_reconciliation_at=add_minutes(utcnow_iso(), 10), reconciliation_attempts=int(payment.get("reconciliation_attempts") or 0) + 1, last_reconciliation_error=None)
    response = httpx.get(f"{STRIPE_API_BASE}/checkout/sessions/{external_id}", headers={"Authorization": _stripe_headers(conn, integration)["Authorization"]}, timeout=30.0)
    data = response.json()
    if response.status_code >= 400:
        record_integration_event(
            conn,
            organization_id=payment["organization_id"],
            integration_id=integration["id"],
            bot_id=payment.get("bot_id"),
            provider="stripe",
            event_type="checkout.refresh",
            status="failed",
            severity="error",
            summary="stripe payment refresh failed",
            response_payload=data,
            error_payload=data,
            provider_status_code=response.status_code,
            external_reference=external_id,
        )
        return _update_payment(conn, payment_id, provider_status=data.get("status") or payment.get("provider_status"), provider_status_code=response.status_code, provider_response_json=to_json(data), next_reconciliation_at=add_minutes(utcnow_iso(), 15), reconciliation_attempts=int(payment.get("reconciliation_attempts") or 0) + 1, last_reconciliation_error=str(data))
    payment_status = data.get("payment_status") or data.get("status") or "open"
    if payment_status == "paid" and payment.get("status") != "paid":
        updated = _mark_payment_paid(conn, payment, provider_reference=data.get("payment_intent") or data.get("id"), provider_payload=data, provider_status=payment_status)
    elif data.get("status") == "expired":
        updated = _update_payment(conn, payment_id, provider_status="expired", payment_link_status="expired", status="expired", provider_response_json=to_json(data), checkout_expires_at=payment.get("checkout_expires_at"), next_reconciliation_at=None, last_reconciliation_error=None)
    else:
        updated = _update_payment(conn, payment_id, provider_status=payment_status, provider_response_json=to_json(data), provider_status_code=response.status_code, next_reconciliation_at=add_minutes(utcnow_iso(), 10), reconciliation_attempts=int(payment.get("reconciliation_attempts") or 0) + 1, last_reconciliation_error=None)
    record_integration_event(
        conn,
        organization_id=payment["organization_id"],
        integration_id=integration["id"],
        bot_id=payment.get("bot_id"),
        provider="stripe",
        event_type="checkout.refresh",
        status="paid" if updated.get("status") == "paid" else "ok",
        summary="stripe payment status refreshed",
        response_payload={"session_id": external_id, "payment_status": payment_status, "status": data.get("status")},
        external_reference=external_id,
        provider_status_code=response.status_code,
    )
    return updated


def _verify_stripe_signature(payload: bytes, signature_header: str | None, webhook_secret: str | None) -> bool:
    if not webhook_secret:
        return False
    if not signature_header:
        return False
    items = {}
    for part in signature_header.split(','):
        if '=' not in part:
            continue
        key, value = part.split('=', 1)
        items[key.strip()] = value.strip()
    timestamp = items.get('t')
    sent = items.get('v1')
    if not timestamp or not sent:
        return False
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode('utf-8')
    expected = hmac.new(webhook_secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sent)


def handle_stripe_webhook(conn, *, payload: bytes, signature: str | None) -> dict[str, Any]:
    event = json.loads(payload.decode('utf-8'))
    obj = ((event.get('data') or {}).get('object') or {})
    payment_id = ((obj.get('metadata') or {}).get('payment_id')) or obj.get('client_reference_id')
    payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,)) if payment_id else None
    integration = _payment_integration(conn, organization_id=payment["organization_id"], bot_id=payment.get("bot_id")) if payment else None
    if integration and not _fake_providers_enabled() and not _verify_stripe_signature(payload, signature, _stripe_webhook_secret(conn, integration)):
        record_integration_event(
            conn,
            organization_id=payment["organization_id"],
            integration_id=integration["id"],
            bot_id=payment.get("bot_id"),
            provider="stripe",
            event_type="webhook.signature",
            status="failed",
            severity="error",
            summary="invalid stripe webhook signature",
            response_payload=event,
        )
        raise RetryableProviderError("invalid_stripe_signature", retryable=False, status_code=401)
    if not payment:
        return {"ok": True, "ignored": True, "reason": "payment_not_found"}
    event_type = event.get('type') or 'unknown'
    if event_type in {'checkout.session.completed', 'payment_intent.succeeded'}:
        updated = _mark_payment_paid(conn, payment, provider_reference=obj.get('payment_intent') or obj.get('id'), provider_payload=obj, provider_status='paid')
        status = 'paid'
    elif event_type in {'checkout.session.expired'}:
        updated = _update_payment(conn, payment['id'], provider_status='expired', payment_link_status='expired', status='expired', provider_response_json=to_json(obj), next_reconciliation_at=None, last_reconciliation_error=None)
        status = 'expired'
    elif event_type in {'payment_intent.payment_failed'}:
        updated = _update_payment(conn, payment['id'], provider_status='failed', payment_link_status='provider_error', status='pending', provider_response_json=to_json(obj), next_reconciliation_at=add_minutes(utcnow_iso(), 15), last_reconciliation_error='payment_failed')
        status = 'failed'
    else:
        updated = _update_payment(conn, payment['id'], provider_status=obj.get('status') or payment.get('provider_status'), provider_response_json=to_json(obj), next_reconciliation_at=add_minutes(utcnow_iso(), 10) if payment.get('status') not in {'paid', 'expired'} else None)
        status = 'ok'
    if integration:
        record_integration_event(
            conn,
            organization_id=payment['organization_id'],
            integration_id=integration['id'],
            bot_id=payment.get('bot_id'),
            provider='stripe',
            event_type=f"webhook.{event_type}",
            status=status,
            severity='error' if status in {'failed'} else 'info',
            summary=f"stripe webhook processed: {event_type}",
            response_payload=obj,
            external_reference=obj.get('id'),
        )
    return {"ok": True, "event_type": event_type, "payment_id": payment['id'], "status": updated.get('status'), "provider_status": updated.get('provider_status')}



def reconcile_pending_provider_payments(conn, *, integration: dict[str, Any], limit: int = 25) -> dict[str, Any]:
    rows = fetch_all(
        conn,
        """
        SELECT * FROM commerce_payments
        WHERE organization_id = ?
          AND COALESCE(bot_id,'') = COALESCE(?, '')
          AND provider = 'stripe'
          AND status IN ('pending', 'pending_provider')
          AND (next_reconciliation_at IS NULL OR next_reconciliation_at <= ?)
        ORDER BY COALESCE(next_reconciliation_at, updated_at) ASC
        LIMIT ?
        """,
        (integration['organization_id'], integration.get('bot_id'), utcnow_iso(), limit),
    )
    refreshed = 0
    paid = 0
    expired = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    for row in rows:
        try:
            updated = refresh_payment_status(conn, row['id'])
            refreshed += 1
            if updated.get('status') == 'paid':
                paid += 1
            elif updated.get('status') == 'expired':
                expired += 1
            elif updated.get('provider_status') == 'failed':
                failed += 1
        except Exception as exc:
            failed += 1
            errors.append({'payment_id': row['id'], 'error': str(exc)})
            _update_payment(
                conn,
                row['id'],
                next_reconciliation_at=add_minutes(utcnow_iso(), 15),
                reconciliation_attempts=int(row.get('reconciliation_attempts') or 0) + 1,
                last_reconciliation_error=str(exc),
            )
    return {
        'provider': 'stripe',
        'mode': 'payment_reconciliation',
        'payments_scanned': len(rows),
        'payments_refreshed': refreshed,
        'paid': paid,
        'expired': expired,
        'failed': failed,
        'errors': errors[:20],
    }
