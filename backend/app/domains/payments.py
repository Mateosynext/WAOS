from __future__ import annotations

from collections import Counter
from typing import Any

from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..repositories import create_audit_log, create_message, get_bot, get_contact, get_contact_memory, get_conversation, upsert_memory
from ..utils import add_minutes, new_id, parse_iso, to_json, from_json, utcnow_iso

BUY_KEYWORDS = [
    "quiero", "me interesa", "cotizacion", "cotización", "precio", "agendar", "comprar", "pagar", "hoy", "listo",
]


PRICE_OBJECTIONS = ["caro", "precio", "descuento", "más barato", "mas barato"]


TIMING_OBJECTIONS = ["luego", "después", "despues", "más tarde", "mas tarde", "no ahora"]


TRUST_OBJECTIONS = ["seguro", "confianza", "garantía", "garantia", "reseñas", "resenas"]


URGENT_WORDS = ["urgente", "urge", "hoy", "ya", "ahora"]


NEGATIVE_WORDS = ["molesto", "enojado", "frustrado", "mal", "pésimo", "pesimo"]


POSITIVE_WORDS = ["gracias", "excelente", "perfecto", "bien", "me encanta"]


def _json(row: dict | None, key: str, default: Any):
    if not row:
        return default
    return from_json(row.get(key), default)


def _keyword_hits(text: str, words: list[str]) -> int:
    lower = (text or "").lower()
    return sum(1 for word in words if word in lower)


def _detect_objections(text: str) -> list[str]:
    lower = (text or "").lower()
    objections: list[str] = []
    if any(word in lower for word in PRICE_OBJECTIONS):
        objections.append("precio")
    if any(word in lower for word in TIMING_OBJECTIONS):
        objections.append("timing")
    if any(word in lower for word in TRUST_OBJECTIONS):
        objections.append("confianza")
    return objections


def _conversation_messages(conn, conversation_id: str) -> list[dict]:
    return fetch_all(conn, "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))


def _ensure_crm_lead(conn, *, organization_id: str, bot_id: str, contact_id: str, conversation_id: str | None = None, defaults: dict[str, Any] | None = None) -> dict:
    existing = fetch_one(conn, "SELECT * FROM crm_leads WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY created_at DESC LIMIT 1", (organization_id, bot_id, contact_id))
    if existing:
        return existing
    defaults = defaults or {}
    lead_id = new_id("lead")
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO crm_leads (
            id, organization_id, bot_id, conversation_id, contact_id, stage, estimated_amount, owner_user_id,
            next_action, followup_at, tags_json, notes, lost_reason, pipeline_json,
            score_buying_intent, close_probability, detected_objections_json, best_next_action,
            temperature_status, language, source_channel, source_campaign, last_qualification_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            defaults.get("stage", "nuevo"),
            float(defaults.get("estimated_amount") or 0),
            defaults.get("owner_user_id"),
            defaults.get("next_action", "Calificar lead"),
            defaults.get("followup_at"),
            to_json(defaults.get("tags") or []),
            defaults.get("notes", ""),
            defaults.get("lost_reason"),
            to_json(defaults.get("pipeline") or {"stage_history": [{"stage": defaults.get("stage", "nuevo"), "at": now}]}),
            int(defaults.get("score_buying_intent") or 0),
            int(defaults.get("close_probability") or 0),
            to_json(defaults.get("detected_objections") or []),
            defaults.get("best_next_action", "Enviar propuesta"),
            defaults.get("temperature_status", "templado"),
            defaults.get("language", "es"),
            defaults.get("source_channel", "whatsapp"),
            defaults.get("source_campaign", "orgánico"),
            now,
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM crm_leads WHERE id = ?", (lead_id,))


def _update_memory_closed(conn, *, organization_id: str, contact_id: str, bot_id: str, next_action: str):
    memory = upsert_memory(conn, organization_id=organization_id, contact_id=contact_id, bot_id=bot_id)
    execute(
        conn,
        """
        UPDATE contact_memory
        SET lead_stage = 'cerrado', next_action = ?, summary = ?, last_updated_at = ?
        WHERE id = ?
        """,
        (next_action, "Lead cerrado por pago confirmado", utcnow_iso(), memory["id"]),
    )


def create_payment_request(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    conversation_id: str,
    contact_id: str,
    title: str,
    amount: float,
    currency: str = "MXN",
    reminder_minutes: int = 60,
    send_receipt_on_confirm: bool = True,
    actor_user: dict | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict:
    metadata = metadata or {}
    lead = _ensure_crm_lead(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id, conversation_id=conversation_id, defaults={"stage": "propuesta"})
    payment_id = new_id("pay")
    now = utcnow_iso()
    appointment_id = metadata.get("appointment_id")
    execute(
        conn,
        """
        INSERT INTO commerce_payments (
            id, organization_id, bot_id, conversation_id, contact_id, crm_lead_id, title, amount, currency,
            status, payment_link_url, payment_link_status, reminder_scheduled_at, confirmed_at, receipt_sent_at,
            cart_recovery_status, send_receipt_on_confirm, metadata_json, created_at, updated_at,
            provider, integration_id, provider_reference, external_payment_id, provider_status, provider_status_code, provider_response_json,
            checkout_expires_at, paid_at, appointment_id, reconciliation_status, reconciled_at, next_reconciliation_at,
            reconciliation_attempts, last_reconciliation_error, locked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payment_id,
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            lead["id"],
            title,
            float(amount),
            currency,
            'pending',
            None,
            'requested',
            add_minutes(now, reminder_minutes),
            None,
            None,
            'active',
            1 if send_receipt_on_confirm else 0,
            to_json(metadata),
            now,
            now,
            None,
            None,
            None,
            None,
            None,
            None,
            '{}',
            None,
            None,
            appointment_id,
            'pending',
            None,
            None,
            0,
            None,
            None,
        ),
    )
    execute(
        conn,
        """
        INSERT INTO automation_jobs (id, organization_id, bot_id, conversation_id, contact_id, rule_id, job_type, dedupe_key, scheduled_for, status, attempts, payload_json, priority, last_error, locked_at, executed_at, created_at)
        VALUES (?, ?, ?, ?, ?, NULL, 'payment_reminder', ?, ?, 'queued', 0, ?, 90, NULL, NULL, NULL, ?)
        """,
        (
            new_id("job"),
            organization_id,
            bot_id,
            conversation_id,
            contact_id,
            f"payment_reminder:{payment_id}",
            add_minutes(now, reminder_minutes),
            to_json({
                "payment_id": payment_id,
                "message_template": f"Te comparto de nuevo tu link de pago para {title}.",
                "max_attempts": 2,
            }),
            now,
        ),
    )
    execute(
        conn,
        "UPDATE crm_leads SET stage = 'pago_pendiente', next_action = 'Confirmar pago', estimated_amount = ?, updated_at = ? WHERE id = ?",
        (float(amount), now, lead["id"]),
    )
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="commerce_payment", entity_id=payment_id, action="commerce.payment_link_created", metadata={"amount": amount, "currency": currency, "conversation_id": conversation_id})
    from ..payments_runtime import create_provider_checkout

    payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
    provider_result = create_provider_checkout(conn, payment)
    payment = provider_result.get("payment") or payment
    reminder_body = f"Te comparto de nuevo tu link de pago para {title}: {payment.get('payment_link_url') or payment.get('payment_link_status') or 'revisa tu pago pendiente'}"
    execute(
        conn,
        "UPDATE automation_jobs SET payload_json = ? WHERE dedupe_key = ?",
        (
            to_json({
                "payment_id": payment_id,
                "message_template": reminder_body,
                "max_attempts": 2,
            }),
            f"payment_reminder:{payment_id}",
        ),
    )
    return payment


def build_payment_receipt_body(payment: dict[str, Any]) -> str:
    return f"Pago confirmado por {payment['title']} por {payment['currency']} {payment['amount']:.2f}. Te compartimos tu comprobante por WhatsApp."


def send_payment_receipt(
    conn,
    *,
    payment_id: str,
    actor_user: dict | None = None,
    receipt_body: str | None = None,
    allow_unpaid: bool = False,
) -> tuple[dict, dict]:
    payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
    if not payment:
        raise ValueError("payment_not_found")
    if str(payment.get("status") or "").lower() != "paid" and not allow_unpaid:
        raise ValueError("payment_not_paid")
    now = utcnow_iso()
    body = receipt_body or build_payment_receipt_body(payment)
    message = create_message(
        conn,
        organization_id=payment["organization_id"],
        conversation_id=payment["conversation_id"],
        contact_id=payment["contact_id"],
        bot_id=payment["bot_id"],
        direction="outbound",
        kind="text",
        source="system",
        body=body,
        status="queued",
        metadata={"type": "payment_receipt", "payment_id": payment_id},
    )
    execute(
        conn,
        """
        INSERT INTO outbox_messages (id, organization_id, bot_id, execution_run_id, conversation_id, channel, payload_json, status, attempts, last_error, provider_response_json, priority, next_attempt_at, locked_at, scheduled_for, sent_at, created_at)
        VALUES (?, ?, ?, NULL, ?, 'whatsapp', ?, 'queued', 0, NULL, '{}', 100, NULL, NULL, ?, NULL, ?)
        """,
        (
            new_id("out"),
            payment["organization_id"],
            payment["bot_id"],
            payment["conversation_id"],
            to_json({"message_id": message["id"], "contact_id": payment["contact_id"], "body": body}),
            now,
            now,
        ),
    )
    execute(conn, "UPDATE commerce_payments SET receipt_sent_at = ?, updated_at = ? WHERE id = ?", (now, now, payment_id))
    updated = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,)) or payment
    if actor_user:
        create_audit_log(conn, organization_id=payment["organization_id"], actor_user_id=actor_user.get("id"), actor_type="user", entity_type="commerce_payment", entity_id=payment_id, action="commerce.payment_receipt_sent", metadata={"message_id": message["id"]})
    return updated, message


def confirm_payment(conn, payment_id: str, actor_user: dict | None = None, provider_reference: str | None = None) -> dict:
    payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
    if not payment:
        raise ValueError("payment_not_found")
    now = utcnow_iso()
    execute(
        conn,
        "UPDATE commerce_payments SET status = 'paid', payment_link_status = 'paid', confirmed_at = ?, paid_at = ?, provider_reference = ?, provider_status = 'paid', updated_at = ?, metadata_json = ? WHERE id = ?",
        (now, now, provider_reference, now, to_json({**_json(payment, "metadata_json", {}), "provider_reference": provider_reference}), payment_id),
    )
    execute(
        conn,
        "UPDATE crm_leads SET stage = 'cerrado_ganado', close_probability = 100, best_next_action = 'Upsell / onboarding', updated_at = ? WHERE id = ?",
        (now, payment["crm_lead_id"]),
    )
    _update_memory_closed(conn, organization_id=payment["organization_id"], contact_id=payment["contact_id"], bot_id=payment["bot_id"], next_action="Enviar onboarding / comprobante")
    updated_payment, _ = send_payment_receipt(conn, payment_id=payment_id, actor_user=actor_user)
    from ..payments_runtime import _reconcile_payment_with_appointments

    updated_payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
    updated_payment = _reconcile_payment_with_appointments(conn, updated_payment)["payment"]
    if actor_user:
        create_audit_log(conn, organization_id=payment["organization_id"], actor_user_id=actor_user.get("id"), actor_type="user", entity_type="commerce_payment", entity_id=payment_id, action="commerce.payment_confirmed", metadata={"provider_reference": provider_reference})
    return updated_payment


def create_whatsapp_flow(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    name: str,
    flow_type: str,
    language: str = "es",
    status: str = "draft",
    screens: list[dict] | None = None,
    metadata: dict[str, Any] | None = None,
    flow_json: dict[str, Any] | None = None,
    categories: list[str] | None = None,
    endpoint_uri: str | None = None,
    fallback: dict[str, Any] | None = None,
    runtime_config: dict[str, Any] | None = None,
    compatibility: dict[str, Any] | None = None,
) -> dict:
    from .whatsapp_flows import create_whatsapp_flow as create_whatsapp_flow_v2

    return create_whatsapp_flow_v2(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        name=name,
        flow_type=flow_type,
        language=language,
        status=status,
        screens=screens,
        metadata=metadata,
        flow_json=flow_json,
        categories=categories,
        endpoint_uri=endpoint_uri,
        fallback=fallback,
        runtime_config=runtime_config,
        compatibility=compatibility,
    )
