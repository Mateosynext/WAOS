from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..db import execute, fetch_one
from ..domains.appointments import create_appointment_bundle, reschedule_appointment
from ..domains.payments import _ensure_crm_lead, create_payment_request, send_payment_receipt
from ..integrations_runtime import sync_google_calendar
from ..utils import new_id, to_json, utcnow_iso


@dataclass(frozen=True)
class ActionPolicy:
    permission: str
    requires_confirmation: bool = False
    high_impact: bool = False


DEFAULT_ACTION_POLICIES: dict[str, ActionPolicy] = {
    "book_appointment": ActionPolicy(permission="appointment.manage", requires_confirmation=True),
    "reschedule": ActionPolicy(permission="appointment.manage", requires_confirmation=True),
    "create_payment_link": ActionPolicy(permission="revenue.manage", requires_confirmation=True, high_impact=True),
    "update_contact_stage": ActionPolicy(permission="crm.manage", requires_confirmation=False),
    "send_receipt": ActionPolicy(permission="revenue.manage", requires_confirmation=True),
}


class BaseAdapter:
    key = "base"
    provider = "waos"

    def preview(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter_key": self.key,
            "provider": self.provider,
            "action": action,
            "target_ref": self.target_ref(conn, action=action, normalized_payload=normalized_payload, context=context),
            "summary": self.summary(action=action, normalized_payload=normalized_payload),
            "warnings": self.warnings(conn, action=action, normalized_payload=normalized_payload, context=context),
        }

    def execute(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any], actor_user: dict) -> dict[str, Any]:
        raise NotImplementedError

    def target_ref(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {}

    def summary(self, *, action: str, normalized_payload: dict[str, Any]) -> str:
        return f"{action}:{self.key}"

    def warnings(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any]) -> list[str]:
        return []


class WaosCalendarAdapter(BaseAdapter):
    key = "waos_calendar"
    provider = "waos"

    def target_ref(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if action == "book_appointment":
            return {
                "conversation_id": normalized_payload.get("conversation_id"),
                "contact_id": normalized_payload.get("contact_id"),
                "scheduled_for": normalized_payload.get("scheduled_for"),
            }
        appointment = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (normalized_payload["appointment_id"],))
        return {
            "appointment_id": normalized_payload["appointment_id"],
            "scheduled_for": normalized_payload.get("scheduled_for"),
            "current_status": (appointment or {}).get("status"),
        }

    def summary(self, *, action: str, normalized_payload: dict[str, Any]) -> str:
        if action == "book_appointment":
            return f"Reservar cita para {normalized_payload.get('scheduled_for')}"
        return f"Reprogramar cita {normalized_payload.get('appointment_id')} a {normalized_payload.get('scheduled_for')}"

    def execute(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any], actor_user: dict) -> dict[str, Any]:
        if action == "book_appointment":
            appointment = create_appointment_bundle(conn, actor_user=actor_user, **normalized_payload)
        else:
            appointment = reschedule_appointment(conn, normalized_payload["appointment_id"], scheduled_for=normalized_payload["scheduled_for"], actor_user=actor_user)
        return {
            "appointment": appointment,
            "target_ref": {"appointment_id": appointment.get("id"), "scheduled_for": appointment.get("scheduled_for")},
        }


class GoogleCalendarAdapter(WaosCalendarAdapter):
    key = "google_calendar"
    provider = "google_calendar"

    def warnings(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any]) -> list[str]:
        warnings = []
        integration = context.get("integration")
        if integration and str(integration.get("credential_status") or "missing") not in {"valid", "configured", "ok"}:
            warnings.append("google_calendar_credentials_not_validated")
        return warnings

    def execute(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any], actor_user: dict) -> dict[str, Any]:
        base = super().execute(conn, action=action, normalized_payload=normalized_payload, context=context, actor_user=actor_user)
        integration = context.get("integration")
        sync_summary = sync_google_calendar(conn, integration) if integration else {"provider": "google_calendar", "pushed": 0, "errors": ["missing_integration"]}
        appointment_id = (((base.get("appointment") or {}).get("id")) or normalized_payload.get("appointment_id"))
        appointment = fetch_one(conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,)) if appointment_id else base.get("appointment")
        return {
            **base,
            "appointment": appointment or base.get("appointment"),
            "calendar_sync": sync_summary,
            "target_ref": {
                "appointment_id": (appointment or base.get("appointment") or {}).get("id"),
                "scheduled_for": (appointment or base.get("appointment") or {}).get("scheduled_for"),
                "provider": self.provider,
                "external_id": (appointment or base.get("appointment") or {}).get("external_id"),
            },
        }


class StripePaymentsAdapter(BaseAdapter):
    key = "stripe_payments"
    provider = "stripe"

    def target_ref(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if action == "send_receipt":
            payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (normalized_payload["payment_id"],))
            return {"payment_id": normalized_payload["payment_id"], "status": (payment or {}).get("status")}
        return {
            "conversation_id": normalized_payload.get("conversation_id"),
            "contact_id": normalized_payload.get("contact_id"),
            "amount": normalized_payload.get("amount"),
            "currency": normalized_payload.get("currency"),
        }

    def summary(self, *, action: str, normalized_payload: dict[str, Any]) -> str:
        if action == "create_payment_link":
            return f"Generar link de cobro por {normalized_payload.get('currency')} {float(normalized_payload.get('amount') or 0):.2f}"
        return f"Enviar comprobante de pago {normalized_payload.get('payment_id')}"

    def execute(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any], actor_user: dict) -> dict[str, Any]:
        if action == "create_payment_link":
            metadata = dict(normalized_payload.get("metadata") or {})
            payment_payload = {**normalized_payload, "metadata": metadata}
            payment = create_payment_request(
                conn,
                actor_user=actor_user,
                preview_execution_id=metadata.get("preview_execution_id"),
                confirmation_token=metadata.get("confirmation_token"),
                idempotency_key=metadata.get("tool_execution_idempotency_key") or metadata.get("idempotency_key"),
                client_request_id=metadata.get("client_request_id"),
                **payment_payload,
            )
            return {
                "payment": payment,
                "provider_ready": bool(payment.get("payment_link_url")),
                "target_ref": {
                    "payment_id": payment.get("id"),
                    "checkout_url": payment.get("payment_link_url"),
                    "provider": payment.get("provider") or self.provider,
                },
            }
        payment, message = send_payment_receipt(
            conn,
            payment_id=normalized_payload["payment_id"],
            actor_user=actor_user,
            receipt_body=normalized_payload.get("receipt_body"),
            allow_unpaid=bool(normalized_payload.get("allow_unpaid_receipt")),
        )
        return {
            "payment": payment,
            "receipt_message": message,
            "target_ref": {
                "payment_id": payment.get("id"),
                "receipt_message_id": (message or {}).get("id"),
                "conversation_id": payment.get("conversation_id"),
            },
        }


class WaosCrmAdapter(BaseAdapter):
    key = "waos_crm"
    provider = "waos"

    def target_ref(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        lead = fetch_one(
            conn,
            "SELECT * FROM crm_leads WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY updated_at DESC LIMIT 1",
            (normalized_payload["organization_id"], normalized_payload["bot_id"], normalized_payload["contact_id"]),
        )
        return {
            "lead_id": (lead or {}).get("id"),
            "contact_id": normalized_payload.get("contact_id"),
            "stage": normalized_payload.get("stage"),
        }

    def summary(self, *, action: str, normalized_payload: dict[str, Any]) -> str:
        return f"Actualizar lead {normalized_payload.get('contact_id')} a etapa {normalized_payload.get('stage')}"

    def execute(self, conn, *, action: str, normalized_payload: dict[str, Any], context: dict[str, Any], actor_user: dict) -> dict[str, Any]:
        lead = _ensure_crm_lead(
            conn,
            organization_id=normalized_payload["organization_id"],
            bot_id=normalized_payload["bot_id"],
            contact_id=normalized_payload["contact_id"],
            conversation_id=normalized_payload.get("conversation_id"),
            defaults={
                "stage": normalized_payload.get("stage"),
                "estimated_amount": normalized_payload.get("estimated_amount") or 0,
                "owner_user_id": normalized_payload.get("owner_user_id"),
                "next_action": normalized_payload.get("next_action") or "Calificar lead",
                "followup_at": normalized_payload.get("followup_at"),
                "tags": normalized_payload.get("tags") or [],
                "notes": normalized_payload.get("notes") or "",
                "lost_reason": normalized_payload.get("lost_reason"),
                "language": normalized_payload.get("language") or "es",
                "source_channel": normalized_payload.get("source_channel") or "whatsapp",
                "source_campaign": normalized_payload.get("source_campaign") or "orgánico",
            },
        )
        previous_stage = lead.get("stage")
        now = utcnow_iso()
        execute(
            conn,
            """
            UPDATE crm_leads
            SET stage = ?, estimated_amount = ?, owner_user_id = ?, next_action = ?, followup_at = ?, tags_json = ?, notes = ?, lost_reason = ?, language = ?, source_channel = ?, source_campaign = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                normalized_payload["stage"],
                float(normalized_payload.get("estimated_amount") or 0),
                normalized_payload.get("owner_user_id"),
                normalized_payload.get("next_action") or "Calificar lead",
                normalized_payload.get("followup_at"),
                to_json(normalized_payload.get("tags") or []),
                normalized_payload.get("notes") or "",
                normalized_payload.get("lost_reason"),
                normalized_payload.get("language") or "es",
                normalized_payload.get("source_channel") or "whatsapp",
                normalized_payload.get("source_campaign") or "orgánico",
                now,
                lead["id"],
            ),
        )
        if previous_stage != normalized_payload["stage"] and table_exists(conn, "lead_stage_history"):
            execute(
                conn,
                "INSERT INTO lead_stage_history (id, organization_id, crm_lead_id, previous_stage, new_stage, reason, changed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id("lstg"),
                    normalized_payload["organization_id"],
                    lead["id"],
                    previous_stage,
                    normalized_payload["stage"],
                    normalized_payload.get("notes") or normalized_payload.get("next_action") or "tool_execution",
                    actor_user.get("id"),
                    now,
                ),
            )
        updated = fetch_one(conn, "SELECT * FROM crm_leads WHERE id = ?", (lead["id"],))
        return {
            "lead": updated,
            "target_ref": {"lead_id": lead["id"], "stage": updated.get("stage") if updated else normalized_payload["stage"]},
        }


def table_exists(conn, table: str) -> bool:
    row = fetch_one(conn, "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,))
    return bool(row)
