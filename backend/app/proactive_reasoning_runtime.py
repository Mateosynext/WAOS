from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from .agent_policy_runtime import get_policy_profile_for_specialist, serialize_policy_profile
from .db import execute, fetch_all, fetch_one, table_exists
from .optimizer_runtime import load_optimizer_runtime_context, proactive_override
from .utils import from_json, hash_value, new_id, parse_iso, to_json, utcnow, utcnow_iso


@dataclass(frozen=True)
class ProactivePlaybookDefinition:
    key: str
    version: str
    objective: str
    signal_key: str
    specialist_agent_key: str
    recommended_action: str | None
    funnel_stage: str
    timing_policy_id: str
    nba_policy_id: str
    base_score: float
    cooldown_hours: int
    max_runs_7d: int
    send_delay_minutes: int


PLAYBOOKS: dict[str, ProactivePlaybookDefinition] = {
    "appointment_upcoming": ProactivePlaybookDefinition(
        key="playbook_upcoming_appointment_confirmation",
        version="playbook_upcoming_appointment_confirmation_v1",
        objective="confirm_upcoming_appointment",
        signal_key="appointment_upcoming",
        specialist_agent_key="booking",
        recommended_action="reschedule",
        funnel_stage="appointment",
        timing_policy_id="timing_policy_appointment_upcoming_v1",
        nba_policy_id="nba_policy_confirm_appointment_v1",
        base_score=74.0,
        cooldown_hours=20,
        max_runs_7d=2,
        send_delay_minutes=0,
    ),
    "payment_failed": ProactivePlaybookDefinition(
        key="playbook_payment_retry_recovery",
        version="playbook_payment_retry_recovery_v1",
        objective="recover_failed_payment",
        signal_key="payment_failed",
        specialist_agent_key="collections",
        recommended_action="create_payment_link",
        funnel_stage="payment",
        timing_policy_id="timing_policy_failed_payment_v1",
        nba_policy_id="nba_policy_payment_retry_v1",
        base_score=92.0,
        cooldown_hours=6,
        max_runs_7d=4,
        send_delay_minutes=5,
    ),
    "payment_pending": ProactivePlaybookDefinition(
        key="playbook_pending_payment_followup",
        version="playbook_pending_payment_followup_v1",
        objective="recover_pending_payment",
        signal_key="payment_pending",
        specialist_agent_key="collections",
        recommended_action="create_payment_link",
        funnel_stage="payment",
        timing_policy_id="timing_policy_pending_payment_v1",
        nba_policy_id="nba_policy_payment_pending_v1",
        base_score=84.0,
        cooldown_hours=12,
        max_runs_7d=3,
        send_delay_minutes=15,
    ),
    "no_response_hot_lead": ProactivePlaybookDefinition(
        key="playbook_hot_lead_reactivation",
        version="playbook_hot_lead_reactivation_v1",
        objective="reactivate_stalled_lead",
        signal_key="no_response_hot_lead",
        specialist_agent_key="recovery",
        recommended_action="book_appointment",
        funnel_stage="reactivation",
        timing_policy_id="timing_policy_stalled_lead_v1",
        nba_policy_id="nba_policy_reactivation_v1",
        base_score=69.0,
        cooldown_hours=24,
        max_runs_7d=3,
        send_delay_minutes=10,
    ),
    "repeat_purchase_window": ProactivePlaybookDefinition(
        key="playbook_repeat_purchase_window",
        version="playbook_repeat_purchase_window_v1",
        objective="drive_repeat_purchase",
        signal_key="repeat_purchase_window",
        specialist_agent_key="recovery",
        recommended_action="book_appointment",
        funnel_stage="reactivation",
        timing_policy_id="timing_policy_repeat_purchase_v1",
        nba_policy_id="nba_policy_repeat_purchase_v1",
        base_score=66.0,
        cooldown_hours=72,
        max_runs_7d=2,
        send_delay_minutes=60,
    ),
    "churn_risk": ProactivePlaybookDefinition(
        key="playbook_churn_prevention",
        version="playbook_churn_prevention_v1",
        objective="prevent_churn",
        signal_key="churn_risk",
        specialist_agent_key="retention",
        recommended_action="update_contact_stage",
        funnel_stage="retention",
        timing_policy_id="timing_policy_churn_prevention_v1",
        nba_policy_id="nba_policy_churn_prevention_v1",
        base_score=78.0,
        cooldown_hours=48,
        max_runs_7d=2,
        send_delay_minutes=30,
    ),
}


def ensure_proactive_reasoning_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS proactive_signal_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            conversation_id TEXT,
            appointment_id TEXT,
            payment_id TEXT,
            lead_id TEXT,
            signal_key TEXT NOT NULL,
            signal_family TEXT NOT NULL,
            strength_score REAL NOT NULL DEFAULT 0,
            facts_json TEXT NOT NULL DEFAULT '{}',
            event_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_proactive_signal_events_contact ON proactive_signal_events(organization_id, bot_id, contact_id, event_at DESC);
        CREATE INDEX IF NOT EXISTS idx_proactive_signal_events_signal ON proactive_signal_events(signal_key, event_at DESC);

        CREATE TABLE IF NOT EXISTS proactive_contact_candidates (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            conversation_id TEXT,
            appointment_id TEXT,
            payment_id TEXT,
            lead_id TEXT,
            signal_event_id TEXT,
            signal_key TEXT NOT NULL,
            signal_family TEXT NOT NULL,
            playbook_id TEXT NOT NULL,
            playbook_version_id TEXT NOT NULL,
            specialist_agent_key TEXT NOT NULL,
            policy_profile_key TEXT,
            policy_profile_version TEXT,
            objective TEXT NOT NULL,
            recommended_action TEXT,
            channel TEXT NOT NULL DEFAULT 'whatsapp',
            priority_score REAL NOT NULL DEFAULT 0,
            priority_band TEXT NOT NULL DEFAULT 'medium',
            eligible INTEGER NOT NULL DEFAULT 1,
            suppression_reason TEXT,
            suggested_send_at TEXT,
            title TEXT,
            message_text TEXT,
            timing_policy_id TEXT,
            nba_policy_id TEXT,
            policy_json TEXT NOT NULL DEFAULT '{}',
            reasoning_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            candidate_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(candidate_key),
            FOREIGN KEY (signal_event_id) REFERENCES proactive_signal_events(id)
        );
        CREATE INDEX IF NOT EXISTS idx_proactive_contact_candidates_org ON proactive_contact_candidates(organization_id, bot_id, status, priority_score DESC, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_proactive_contact_candidates_contact ON proactive_contact_candidates(contact_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_proactive_contact_candidates_specialist ON proactive_contact_candidates(specialist_agent_key, priority_score DESC);

        CREATE TABLE IF NOT EXISTS proactive_playbook_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            candidate_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            conversation_id TEXT,
            appointment_id TEXT,
            payment_id TEXT,
            lead_id TEXT,
            specialist_agent_key TEXT NOT NULL,
            playbook_id TEXT NOT NULL,
            playbook_version_id TEXT NOT NULL,
            objective TEXT NOT NULL,
            recommended_action TEXT,
            channel TEXT NOT NULL DEFAULT 'whatsapp',
            status TEXT NOT NULL DEFAULT 'materialized',
            scheduled_for TEXT,
            message_text TEXT,
            action_payload_json TEXT NOT NULL DEFAULT '{}',
            outcome_exposure_id TEXT,
            tool_execution_run_id TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES proactive_contact_candidates(id)
        );
        CREATE INDEX IF NOT EXISTS idx_proactive_playbook_runs_org ON proactive_playbook_runs(organization_id, bot_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_proactive_playbook_runs_contact ON proactive_playbook_runs(contact_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_proactive_playbook_runs_playbook ON proactive_playbook_runs(playbook_id, created_at DESC);
        """
    )


def _iso(dt_value: dt.datetime) -> str:
    return dt_value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hours_ago(now: dt.datetime, hours: int) -> str:
    return _iso(now - dt.timedelta(hours=hours))


def _days_ago(now: dt.datetime, days: int) -> str:
    return _iso(now - dt.timedelta(days=days))


def _minutes_after(base: str | None, minutes: int) -> str:
    origin = parse_iso(base) or utcnow()
    return _iso(origin + dt.timedelta(minutes=minutes))


def _priority_band(score: float) -> str:
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def _contact_name(contact: dict[str, Any] | None) -> str:
    name = str((contact or {}).get("name") or "").strip()
    return name if name else "hola"


def _select_contacts(conn, *, organization_id: str, bot_id: str, contact_ids: list[str] | None, conversation_ids: list[str] | None, limit: int) -> list[dict[str, Any]]:
    scoped_ids = [str(item) for item in (contact_ids or []) if str(item).strip()]
    if scoped_ids:
        placeholders = ", ".join("?" for _ in scoped_ids)
        return fetch_all(
            conn,
            f"SELECT * FROM contacts WHERE organization_id = ? AND id IN ({placeholders}) ORDER BY updated_at DESC LIMIT ?",
            (organization_id, *scoped_ids, limit),
        )
    if conversation_ids:
        conv_placeholders = ", ".join("?" for _ in conversation_ids)
        return fetch_all(
            conn,
            f"SELECT DISTINCT c.* FROM contacts c JOIN conversations v ON v.contact_id = c.id WHERE c.organization_id = ? AND v.bot_id = ? AND v.id IN ({conv_placeholders}) ORDER BY c.updated_at DESC LIMIT ?",
            (organization_id, bot_id, *conversation_ids, limit),
        )
    return fetch_all(
        conn,
        """
        SELECT c.*
        FROM contacts c
        JOIN (
            SELECT c0.id,
                   (
                       SELECT MAX(activity.ts)
                       FROM (
                           SELECT v.updated_at AS ts
                           FROM conversations v
                           WHERE v.contact_id = c0.id AND v.bot_id = ?
                           UNION ALL
                           SELECT p.updated_at AS ts
                           FROM commerce_payments p
                           WHERE p.contact_id = c0.id AND p.bot_id = ?
                           UNION ALL
                           SELECT a.updated_at AS ts
                           FROM appointments a
                           WHERE a.contact_id = c0.id AND a.bot_id = ?
                           UNION ALL
                           SELECT c0.updated_at AS ts
                       ) activity
                   ) AS sort_updated
            FROM contacts c0
            WHERE c0.organization_id = ?
        ) ranked ON ranked.id = c.id
        ORDER BY ranked.sort_updated DESC, c.updated_at DESC, c.id DESC
        LIMIT ?
        """,
        (bot_id, bot_id, bot_id, organization_id, limit),
    )


def _contact_context(conn, *, organization_id: str, bot_id: str, contact_id: str, preferred_conversation_id: str | None) -> dict[str, Any]:
    contact = fetch_one(conn, "SELECT * FROM contacts WHERE id = ?", (contact_id,)) or {}
    conversation = None
    if preferred_conversation_id:
        conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (preferred_conversation_id,))
    if conversation is None:
        conversation = fetch_one(
            conn,
            "SELECT * FROM conversations WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY updated_at DESC LIMIT 1",
            (organization_id, bot_id, contact_id),
        ) or {}
    lead = fetch_one(
        conn,
        "SELECT * FROM crm_leads WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY updated_at DESC LIMIT 1",
        (organization_id, bot_id, contact_id),
    ) or {}
    appointment = fetch_one(
        conn,
        "SELECT * FROM appointments WHERE organization_id = ? AND bot_id = ? AND contact_id = ? AND status IN ('scheduled', 'confirmed') ORDER BY scheduled_for ASC LIMIT 1",
        (organization_id, bot_id, contact_id),
    ) or {}
    payment = fetch_one(
        conn,
        "SELECT * FROM commerce_payments WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY updated_at DESC LIMIT 1",
        (organization_id, bot_id, contact_id),
    ) or {}
    memory = fetch_one(
        conn,
        "SELECT * FROM contact_memory WHERE organization_id = ? AND bot_id = ? AND contact_id = ? ORDER BY last_updated_at DESC LIMIT 1",
        (organization_id, bot_id, contact_id),
    ) or {}
    last_positive = fetch_one(
        conn,
        """
        SELECT * FROM outcome_events
        WHERE organization_id = ? AND contact_id = ? AND event_name IN ('appointment_attended', 'attended', 'sale_closed', 'payment_completed')
        ORDER BY event_timestamp DESC, created_at DESC LIMIT 1
        """,
        (organization_id, contact_id),
    ) or {}
    completed_payments = fetch_one(
        conn,
        "SELECT COUNT(*) AS total, COALESCE(SUM(value_number), 0) AS revenue_sum FROM outcome_events WHERE organization_id = ? AND contact_id = ? AND event_name = 'payment_completed'",
        (organization_id, contact_id),
    ) or {"total": 0, "revenue_sum": 0}
    return {
        "contact": contact,
        "conversation": conversation,
        "lead": lead,
        "appointment": appointment,
        "payment": payment,
        "memory": {**memory, **from_json(memory.get("memory_json"), {})},
        "last_positive": last_positive,
        "completed_payments": completed_payments,
    }


def _signal_family(signal_key: str) -> str:
    if signal_key.startswith("payment"):
        return "collections"
    if signal_key.startswith("appointment"):
        return "booking"
    if signal_key in {"repeat_purchase_window", "churn_risk"}:
        return "retention"
    return "recovery"


def _build_signals(conn, *, organization_id: str, bot_id: str, contact_id: str, preferred_conversation_id: str | None, as_of: str | None) -> list[dict[str, Any]]:
    now = parse_iso(as_of) or utcnow()
    ctx = _contact_context(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id, preferred_conversation_id=preferred_conversation_id)
    contact = ctx["contact"]
    conversation = ctx["conversation"]
    lead = ctx["lead"]
    appointment = ctx["appointment"]
    payment = ctx["payment"]
    memory = ctx["memory"]
    last_positive = ctx["last_positive"]
    completed_payments = ctx["completed_payments"]

    signals: list[dict[str, Any]] = []

    appointment_at = parse_iso(appointment.get("scheduled_for"))
    if appointment and appointment_at and appointment.get("status") in {"scheduled", "confirmed"}:
        hours_until = (appointment_at - now).total_seconds() / 3600.0
        if 0 <= hours_until <= 48 and not appointment.get("confirmed_at"):
            signals.append(
                {
                    "signal_key": "appointment_upcoming",
                    "strength_score": round(0.65 + max(0.0, (48 - max(hours_until, 0)) / 48.0) * 0.2, 2),
                    "conversation_id": conversation.get("id"),
                    "appointment_id": appointment.get("id"),
                    "lead_id": lead.get("id"),
                    "facts": {
                        "scheduled_for": appointment.get("scheduled_for"),
                        "hours_until": round(hours_until, 1),
                        "status": appointment.get("status"),
                        "contact_name": _contact_name(contact),
                    },
                }
            )

    payment_updated_at = parse_iso(payment.get("updated_at") or payment.get("created_at"))
    payment_status = str(payment.get("status") or "").lower()
    if payment and payment_status in {"failed", "expired"}:
        signals.append(
            {
                "signal_key": "payment_failed",
                "strength_score": 0.97,
                "conversation_id": payment.get("conversation_id") or conversation.get("id"),
                "payment_id": payment.get("id"),
                "lead_id": lead.get("id") or payment.get("crm_lead_id"),
                "facts": {
                    "payment_id": payment.get("id"),
                    "title": payment.get("title"),
                    "amount": float(payment.get("amount") or 0),
                    "currency": payment.get("currency") or "MXN",
                    "status": payment_status,
                    "contact_name": _contact_name(contact),
                },
            }
        )
    elif payment and payment_status in {"pending", "generated", "requested"} and payment_updated_at:
        age_hours = max(0.0, (now - payment_updated_at).total_seconds() / 3600.0)
        if age_hours >= 6 and not payment.get("confirmed_at"):
            signals.append(
                {
                    "signal_key": "payment_pending",
                    "strength_score": round(min(0.94, 0.7 + min(age_hours, 72) / 100.0), 2),
                    "conversation_id": payment.get("conversation_id") or conversation.get("id"),
                    "payment_id": payment.get("id"),
                    "appointment_id": payment.get("appointment_id") if "appointment_id" in payment else None,
                    "lead_id": lead.get("id") or payment.get("crm_lead_id"),
                    "facts": {
                        "payment_id": payment.get("id"),
                        "title": payment.get("title"),
                        "amount": float(payment.get("amount") or 0),
                        "currency": payment.get("currency") or "MXN",
                        "age_hours": round(age_hours, 1),
                        "contact_name": _contact_name(contact),
                    },
                }
            )

    lead_stage = str(lead.get("stage") or memory.get("lead_stage") or "").strip().lower()
    last_message_at = parse_iso(conversation.get("last_message_at"))
    if conversation and last_message_at and str(conversation.get("status") or "open") == "open" and lead_stage in {"nuevo", "hot", "propuesta", "negociacion", "contacted"}:
        silence_hours = max(0.0, (now - last_message_at).total_seconds() / 3600.0)
        if silence_hours >= 24 and not conversation.get("human_takeover"):
            signals.append(
                {
                    "signal_key": "no_response_hot_lead",
                    "strength_score": round(min(0.88, 0.58 + min(silence_hours, 120) / 200.0), 2),
                    "conversation_id": conversation.get("id"),
                    "lead_id": lead.get("id"),
                    "facts": {
                        "silence_hours": round(silence_hours, 1),
                        "lead_stage": lead_stage or "unknown",
                        "close_probability": int(lead.get("close_probability") or 0),
                        "contact_name": _contact_name(contact),
                    },
                }
            )

    last_positive_at = parse_iso(last_positive.get("event_timestamp"))
    repeat_days = None
    if last_positive_at:
        repeat_days = max(0.0, (now - last_positive_at).total_seconds() / 86400.0)
        if 30 <= repeat_days <= 75:
            signals.append(
                {
                    "signal_key": "repeat_purchase_window",
                    "strength_score": round(min(0.82, 0.55 + (repeat_days - 30) / 100.0), 2),
                    "conversation_id": conversation.get("id"),
                    "lead_id": lead.get("id"),
                    "facts": {
                        "days_since_last_positive": int(repeat_days),
                        "last_event_name": last_positive.get("event_name"),
                        "completed_payments": int(completed_payments.get("total") or 0),
                        "contact_name": _contact_name(contact),
                    },
                }
            )
        if repeat_days >= 90 and int(completed_payments.get("total") or 0) >= 1:
            signals.append(
                {
                    "signal_key": "churn_risk",
                    "strength_score": round(min(0.9, 0.68 + min(repeat_days, 180) / 300.0), 2),
                    "conversation_id": conversation.get("id"),
                    "lead_id": lead.get("id"),
                    "facts": {
                        "days_since_last_positive": int(repeat_days),
                        "revenue_sum": float(completed_payments.get("revenue_sum") or 0),
                        "completed_payments": int(completed_payments.get("total") or 0),
                        "contact_name": _contact_name(contact),
                    },
                }
            )

    return signals


def _message_for_signal(playbook: ProactivePlaybookDefinition, *, facts: dict[str, Any]) -> tuple[str, str]:
    name = str(facts.get("contact_name") or "hola").strip()
    if playbook.signal_key == "payment_failed":
        amount = f"{facts.get('currency', 'MXN')} {float(facts.get('amount') or 0):.2f}"
        return (
            "Pago fallido por recuperar",
            f"Hola {name}, vi que el pago de {amount} no se completó. Si quieres, te comparto aquí un link actualizado para retomarlo sin perder tu avance.",
        )
    if playbook.signal_key == "payment_pending":
        amount = f"{facts.get('currency', 'MXN')} {float(facts.get('amount') or 0):.2f}"
        return (
            "Pago pendiente con alta intención",
            f"Hola {name}, sigo al pendiente con tu pago pendiente de {amount}. Si te sirve, te dejo el link de cobro actualizado para completarlo hoy mismo.",
        )
    if playbook.signal_key == "appointment_upcoming":
        return (
            "Cita próxima sin confirmar",
            f"Hola {name}, te recuerdo tu cita programada para {facts.get('scheduled_for')}. Si necesitas confirmarla o moverla, te ayudo por aquí para dejarla resuelta.",
        )
    if playbook.signal_key == "repeat_purchase_window":
        days = int(facts.get("days_since_last_positive") or 0)
        return (
            "Ventana ideal de recompra",
            f"Hola {name}, ya pasaron {days} días desde tu última visita/compra. Si quieres, te ayudo a apartar tu siguiente espacio antes de que se te cierre la mejor ventana.",
        )
    if playbook.signal_key == "churn_risk":
        days = int(facts.get("days_since_last_positive") or 0)
        return (
            "Riesgo de churn detectado",
            f"Hola {name}, noté que llevamos {days} días sin actividad. Puedo ayudarte a retomar seguimiento, reagendar o revisar la mejor opción para que no pierdas continuidad.",
        )
    silence = int(facts.get("silence_hours") or 0)
    return (
        "Lead caliente sin respuesta",
        f"Hola {name}, sigo al pendiente contigo. Vi que han pasado {silence} horas sin respuesta y todavía te puedo ayudar a avanzar hoy con la siguiente mejor opción.",
    )


def _candidate_key(*, organization_id: str, bot_id: str, contact_id: str, playbook: ProactivePlaybookDefinition, signal: dict[str, Any]) -> str:
    reference = signal.get("payment_id") or signal.get("appointment_id") or signal.get("lead_id") or signal.get("conversation_id") or contact_id
    digest = hash_value(f"{organization_id}|{bot_id}|{contact_id}|{playbook.key}|{signal['signal_key']}|{reference}")[:16]
    return f"proactive:{playbook.key}:{digest}"


def _recent_run_counts(conn, *, contact_id: str, objective: str, candidate_key: str, now: dt.datetime) -> dict[str, int]:
    since_24h = _hours_ago(now, 24)
    since_7d = _days_ago(now, 7)
    objective_24h = 0
    if table_exists(conn, "proactive_playbook_runs"):
        objective_24h_row = fetch_one(
            conn,
            "SELECT COUNT(*) AS total FROM proactive_playbook_runs WHERE contact_id = ? AND objective = ? AND created_at >= ?",
            (contact_id, objective, since_24h),
        ) or {"total": 0}
        objective_24h = int(objective_24h_row.get("total") or 0)
        total_7d_row = fetch_one(
            conn,
            "SELECT COUNT(*) AS total FROM proactive_playbook_runs WHERE contact_id = ? AND created_at >= ?",
            (contact_id, since_7d),
        ) or {"total": 0}
        total_7d = int(total_7d_row.get("total") or 0)
    else:
        total_7d = 0
    existing_candidate = fetch_one(conn, "SELECT status FROM proactive_contact_candidates WHERE candidate_key = ?", (candidate_key,)) or {}
    return {"objective_24h": objective_24h, "total_7d": total_7d, "existing_materialized": 1 if existing_candidate.get("status") == "materialized" else 0}


def _policy_for_candidate(conn, *, playbook: ProactivePlaybookDefinition, contact: dict[str, Any], conversation: dict[str, Any], candidate_key: str, now: dt.datetime) -> dict[str, Any]:
    profile = get_policy_profile_for_specialist(playbook.specialist_agent_key)
    serialized_profile = serialize_policy_profile(profile)
    counts = _recent_run_counts(conn, contact_id=contact.get("id"), objective=playbook.objective, candidate_key=candidate_key, now=now)
    eligible = True
    suppression_reason = None
    warnings: list[str] = []
    if conversation and int(conversation.get("human_takeover") or 0) == 1:
        eligible = False
        suppression_reason = "human_takeover_active"
    elif conversation and int(conversation.get("ai_active") or 1) == 0:
        eligible = False
        suppression_reason = "ai_paused"
    elif playbook.recommended_action and playbook.recommended_action not in set(profile.allowed_actions):
        eligible = False
        suppression_reason = "action_not_allowed_for_specialist"
    elif counts["objective_24h"] >= 1:
        eligible = False
        suppression_reason = "objective_already_touched_24h"
    elif counts["total_7d"] >= playbook.max_runs_7d:
        eligible = False
        suppression_reason = "frequency_cap_7d"
    if counts["total_7d"] == max(0, playbook.max_runs_7d - 1):
        warnings.append("near_frequency_cap_7d")
    return {
        "profile": serialized_profile,
        "decision": {
            "eligible": eligible,
            "suppression_reason": suppression_reason,
            "warnings": warnings,
            "counts": counts,
        },
    }


def _priority_score(playbook: ProactivePlaybookDefinition, *, signal_strength: float, facts: dict[str, Any]) -> float:
    bonus = 0.0
    if playbook.signal_key.startswith("payment"):
        amount = float(facts.get("amount") or 0)
        bonus += min(8.0, amount / 500.0)
    if playbook.signal_key == "appointment_upcoming":
        hours_until = float(facts.get("hours_until") or 48)
        bonus += max(0.0, 8.0 - min(hours_until, 48) / 6.0)
    if playbook.signal_key in {"repeat_purchase_window", "churn_risk"}:
        bonus += min(6.0, float(facts.get("revenue_sum") or 0) / 2000.0)
    return round(min(99.0, playbook.base_score + signal_strength * 10.0 + bonus), 2)


def _persist_signal(conn, *, organization_id: str, bot_id: str, contact_id: str, signal: dict[str, Any], event_at: str) -> dict[str, Any]:
    row_id = new_id("psig")
    execute(
        conn,
        """
        INSERT INTO proactive_signal_events (
            id, organization_id, bot_id, contact_id, conversation_id, appointment_id, payment_id, lead_id,
            signal_key, signal_family, strength_score, facts_json, event_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            organization_id,
            bot_id,
            contact_id,
            signal.get("conversation_id"),
            signal.get("appointment_id"),
            signal.get("payment_id"),
            signal.get("lead_id"),
            signal["signal_key"],
            _signal_family(signal["signal_key"]),
            float(signal.get("strength_score") or 0),
            to_json(signal.get("facts") or {}),
            event_at,
            utcnow_iso(),
        ),
    )
    return fetch_one(conn, "SELECT * FROM proactive_signal_events WHERE id = ?", (row_id,)) or {}


def _upsert_candidate(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    contact_id: str,
    signal_row: dict[str, Any],
    playbook: ProactivePlaybookDefinition,
    policy: dict[str, Any],
    priority_score: float,
    suggested_send_at: str,
    title: str,
    message_text: str,
    candidate_key: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    now = utcnow_iso()
    policy_profile = policy["profile"]
    decision = policy["decision"]
    existing = fetch_one(conn, "SELECT * FROM proactive_contact_candidates WHERE candidate_key = ?", (candidate_key,))
    payload = (
        organization_id,
        bot_id,
        contact_id,
        signal_row.get("conversation_id"),
        signal_row.get("appointment_id"),
        signal_row.get("payment_id"),
        signal_row.get("lead_id"),
        signal_row.get("id"),
        signal_row.get("signal_key"),
        signal_row.get("signal_family"),
        playbook.key,
        playbook.version,
        playbook.specialist_agent_key,
        policy_profile.get("key"),
        policy_profile.get("version"),
        playbook.objective,
        playbook.recommended_action,
        "whatsapp",
        priority_score,
        _priority_band(priority_score),
        1 if decision.get("eligible") else 0,
        decision.get("suppression_reason"),
        suggested_send_at,
        title,
        message_text,
        playbook.timing_policy_id,
        playbook.nba_policy_id,
        to_json(policy),
        to_json({"signal": from_json(signal_row.get("facts_json"), {}), "warnings": decision.get("warnings") or []}),
        to_json(metadata),
    )
    if existing:
        execute(
            conn,
            """
            UPDATE proactive_contact_candidates
            SET organization_id = ?, bot_id = ?, contact_id = ?, conversation_id = ?, appointment_id = ?, payment_id = ?, lead_id = ?,
                signal_event_id = ?, signal_key = ?, signal_family = ?, playbook_id = ?, playbook_version_id = ?,
                specialist_agent_key = ?, policy_profile_key = ?, policy_profile_version = ?, objective = ?, recommended_action = ?,
                channel = ?, priority_score = ?, priority_band = ?, eligible = ?, suppression_reason = ?, suggested_send_at = ?,
                title = ?, message_text = ?, timing_policy_id = ?, nba_policy_id = ?, policy_json = ?, reasoning_json = ?, metadata_json = ?, updated_at = ?
            WHERE candidate_key = ?
            """,
            (*payload, now, candidate_key),
        )
    else:
        execute(
            conn,
            """
            INSERT INTO proactive_contact_candidates (
                id, organization_id, bot_id, contact_id, conversation_id, appointment_id, payment_id, lead_id,
                signal_event_id, signal_key, signal_family, playbook_id, playbook_version_id, specialist_agent_key,
                policy_profile_key, policy_profile_version, objective, recommended_action, channel,
                priority_score, priority_band, eligible, suppression_reason, suggested_send_at,
                title, message_text, timing_policy_id, nba_policy_id, policy_json, reasoning_json, metadata_json,
                candidate_key, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (new_id("pcand"), *payload, candidate_key, now, now),
        )
    return fetch_one(conn, "SELECT * FROM proactive_contact_candidates WHERE candidate_key = ?", (candidate_key,)) or {}


def _serialize_candidate(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        **row,
        "eligible": bool(row.get("eligible")),
        "policy": from_json(row.get("policy_json"), {}),
        "reasoning": from_json(row.get("reasoning_json"), {}),
        "metadata": from_json(row.get("metadata_json"), {}),
    }


def _serialize_run(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        **row,
        "action_payload": from_json(row.get("action_payload_json"), {}),
        "metadata": from_json(row.get("metadata_json"), {}),
    }


def evaluate_proactive_candidates(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    contact_ids: list[str] | None = None,
    conversation_ids: list[str] | None = None,
    as_of: str | None = None,
    persist: bool = True,
    include_suppressed: bool = False,
    limit: int = 100,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_proactive_reasoning_schema(conn)
    now = parse_iso(as_of) or utcnow()
    contacts = _select_contacts(conn, organization_id=organization_id, bot_id=bot_id, contact_ids=contact_ids, conversation_ids=conversation_ids, limit=limit)
    optimizer_context = load_optimizer_runtime_context(conn, organization_id=organization_id, bot_id=bot_id)
    candidates: list[dict[str, Any]] = []
    signal_rows: list[dict[str, Any]] = []
    for contact in contacts:
        pref_conv = None
        if conversation_ids:
            pref_conv = fetch_one(
                conn,
                "SELECT id FROM conversations WHERE contact_id = ? AND id IN (%s) LIMIT 1" % ", ".join("?" for _ in conversation_ids),
                (contact["id"], *conversation_ids),
            )
            pref_conv = (pref_conv or {}).get("id")
        context = _contact_context(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact["id"], preferred_conversation_id=pref_conv)
        for signal in _build_signals(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact["id"], preferred_conversation_id=pref_conv, as_of=_iso(now)):
            playbook = PLAYBOOKS.get(signal["signal_key"])
            if not playbook:
                continue
            signal_row = _persist_signal(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact["id"], signal=signal, event_at=_iso(now)) if persist else {
                "id": None,
                "contact_id": contact["id"],
                "conversation_id": signal.get("conversation_id"),
                "appointment_id": signal.get("appointment_id"),
                "payment_id": signal.get("payment_id"),
                "lead_id": signal.get("lead_id"),
                "signal_key": signal["signal_key"],
                "signal_family": _signal_family(signal["signal_key"]),
                "facts_json": to_json(signal.get("facts") or {}),
            }
            signal_rows.append({**signal_row, "facts": signal.get("facts") or {}})
            candidate_key = _candidate_key(organization_id=organization_id, bot_id=bot_id, contact_id=contact["id"], playbook=playbook, signal=signal)
            policy = _policy_for_candidate(conn, playbook=playbook, contact=context["contact"], conversation=context["conversation"], candidate_key=candidate_key, now=now)
            if not include_suppressed and not policy["decision"].get("eligible"):
                continue
            priority_score = _priority_score(playbook, signal_strength=float(signal.get("strength_score") or 0), facts=signal.get("facts") or {})
            title, message_text = _message_for_signal(playbook, facts=signal.get("facts") or {})
            suggested_send_at = _minutes_after(_iso(now), playbook.send_delay_minutes)
            optimizer_applied = proactive_override(
                context=optimizer_context,
                playbook_key=playbook.key,
                priority_score=priority_score,
                suggested_send_at=suggested_send_at,
                channel='whatsapp',
                message_text=message_text,
            )
            priority_score = float(optimizer_applied.get('priority_score') or priority_score)
            suggested_send_at = str(optimizer_applied.get('suggested_send_at') or suggested_send_at)
            candidate_channel = str(optimizer_applied.get('channel') or 'whatsapp')
            template_version_id = optimizer_applied.get('template_version_id')
            row = _upsert_candidate(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                contact_id=contact["id"],
                signal_row=signal_row,
                playbook=playbook,
                policy=policy,
                priority_score=priority_score,
                suggested_send_at=suggested_send_at,
                title=title,
                message_text=message_text,
                candidate_key=candidate_key,
                metadata={**(metadata or {}), "signal_facts": signal.get("facts") or {}, "optimizer": optimizer_applied},
            ) if persist else {
                "id": new_id("pcand_preview"),
                "organization_id": organization_id,
                "bot_id": bot_id,
                "contact_id": contact["id"],
                "conversation_id": signal.get("conversation_id"),
                "appointment_id": signal.get("appointment_id"),
                "payment_id": signal.get("payment_id"),
                "lead_id": signal.get("lead_id"),
                "signal_event_id": signal_row.get("id"),
                "signal_key": signal["signal_key"],
                "signal_family": _signal_family(signal["signal_key"]),
                "playbook_id": playbook.key,
                "playbook_version_id": playbook.version,
                "specialist_agent_key": playbook.specialist_agent_key,
                "policy_profile_key": policy["profile"].get("key"),
                "policy_profile_version": policy["profile"].get("version"),
                "objective": playbook.objective,
                "recommended_action": playbook.recommended_action,
                "channel": candidate_channel,
                "priority_score": priority_score,
                "priority_band": _priority_band(priority_score),
                "eligible": 1 if policy["decision"].get("eligible") else 0,
                "suppression_reason": policy["decision"].get("suppression_reason"),
                "suggested_send_at": suggested_send_at,
                "title": title,
                "message_text": message_text,
                "timing_policy_id": playbook.timing_policy_id,
                "nba_policy_id": playbook.nba_policy_id,
                "policy_json": to_json(policy),
                "reasoning_json": to_json({"signal": signal.get("facts") or {}}),
                "metadata_json": to_json({**(metadata or {}), "optimizer": optimizer_applied, "template_version_id": template_version_id}),
                "candidate_key": candidate_key,
                "status": "open",
                "created_at": _iso(now),
                "updated_at": _iso(now),
            }
            candidates.append(_serialize_candidate(row))
    candidates.sort(key=lambda item: (float(item.get("priority_score") or 0), item.get("updated_at") or ""), reverse=True)
    return {
        "engine_version": "proactive_reasoning_v1",
        "policy_engine": "proactive_policy_v1",
        "items": candidates[:limit],
        "count": len(candidates[:limit]),
        "signals_recorded": len(signal_rows),
    }


def list_proactive_candidates(
    conn,
    *,
    organization_id: str,
    bot_id: str | None = None,
    status: str | None = None,
    specialist_agent_key: str | None = None,
    eligible: bool | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_proactive_reasoning_schema(conn)
    conditions = ["organization_id = ?"]
    params: list[Any] = [organization_id]
    if bot_id:
        conditions.append("bot_id = ?")
        params.append(bot_id)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if specialist_agent_key:
        conditions.append("specialist_agent_key = ?")
        params.append(specialist_agent_key)
    if eligible is not None:
        conditions.append("eligible = ?")
        params.append(1 if eligible else 0)
    where = " AND ".join(conditions)
    rows = fetch_all(
        conn,
        f"SELECT * FROM proactive_contact_candidates WHERE {where} ORDER BY priority_score DESC, updated_at DESC LIMIT ?",
        (*params, limit),
    )
    return [_serialize_candidate(item) for item in rows]


def _record_outcome_exposure(conn, *, candidate: dict[str, Any], run_id: str, actor_user_id: str | None) -> dict[str, Any] | None:
    if not table_exists(conn, "outcome_exposures"):
        return None
    now = utcnow_iso()
    profile = (candidate.get("policy") or {}).get("profile") or {}
    row_id = new_id("outcome_exposure")
    execute(
        conn,
        """
        INSERT INTO outcome_exposures (
            id, organization_id, bot_id, conversation_id, contact_id, lead_id, appointment_id, payment_id,
            message_id, source_type, channel, prompt_run_id, prompt_version_id, flow_id, flow_version_id,
            template_id, template_version_id, routing_rule_id, decision_path_id, timing_policy_id,
            tone_policy_id, nba_policy_id, escalation_policy_id, playbook_id, playbook_version_id,
            handoff_id, handoff_kind, specialist_agent_key, specialist_agent_version, specialist_prompt_id,
            intent_family, agent_routing_run_id, policy_profile_key, policy_profile_version, policy_evaluation_id, operator_user_id, assigned_variant, vertical, funnel_stage,
            metadata_json, sent_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            candidate.get("organization_id"),
            candidate.get("bot_id"),
            candidate.get("conversation_id"),
            candidate.get("contact_id"),
            candidate.get("lead_id"),
            candidate.get("appointment_id"),
            candidate.get("payment_id"),
            None,
            "proactive_playbook",
            candidate.get("channel") or "whatsapp",
            run_id,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            candidate.get("timing_policy_id"),
            None,
            candidate.get("nba_policy_id"),
            None,
            candidate.get("playbook_id"),
            candidate.get("playbook_version_id"),
            None,
            None,
            candidate.get("specialist_agent_key"),
            None,
            None,
            candidate.get("specialist_agent_key"),
            None,
            profile.get("key"),
            profile.get("version"),
            None,
            actor_user_id,
            None,
            None,
            candidate.get("objective") or candidate.get("signal_family"),
            to_json({"candidate_id": candidate.get("id"), "run_id": run_id, "reasoning": candidate.get("reasoning")}),
            now,
            now,
        ),
    )
    return fetch_one(conn, "SELECT * FROM outcome_exposures WHERE id = ?", (row_id,))


def materialize_proactive_candidate(
    conn,
    *,
    candidate_id: str,
    actor_user_id: str | None,
    schedule_for: str | None = None,
    record_exposure: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_proactive_reasoning_schema(conn)
    candidate = _serialize_candidate(fetch_one(conn, "SELECT * FROM proactive_contact_candidates WHERE id = ?", (candidate_id,)))
    if not candidate:
        raise ValueError("candidate_not_found")
    existing = fetch_one(conn, "SELECT * FROM proactive_playbook_runs WHERE candidate_id = ? ORDER BY created_at DESC LIMIT 1", (candidate_id,))
    if existing:
        return {
            "candidate": candidate,
            "run": _serialize_run(existing),
            "exposure": fetch_one(conn, "SELECT * FROM outcome_exposures WHERE id = ?", (existing.get("outcome_exposure_id"),)) if existing.get("outcome_exposure_id") else None,
            "deduped": True,
        }
    now = utcnow_iso()
    scheduled_for = schedule_for or candidate.get("suggested_send_at") or now
    action_payload = {
        "contact_id": candidate.get("contact_id"),
        "conversation_id": candidate.get("conversation_id"),
        "appointment_id": candidate.get("appointment_id"),
        "payment_id": candidate.get("payment_id"),
        "lead_id": candidate.get("lead_id"),
        "objective": candidate.get("objective"),
    }
    run_id = new_id("prun")
    execute(
        conn,
        """
        INSERT INTO proactive_playbook_runs (
            id, organization_id, bot_id, candidate_id, contact_id, conversation_id, appointment_id, payment_id, lead_id,
            specialist_agent_key, playbook_id, playbook_version_id, objective, recommended_action, channel,
            status, scheduled_for, message_text, action_payload_json, outcome_exposure_id, tool_execution_run_id,
            metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'materialized', ?, ?, ?, NULL, NULL, ?, ?, ?)
        """,
        (
            run_id,
            candidate.get("organization_id"),
            candidate.get("bot_id"),
            candidate.get("id"),
            candidate.get("contact_id"),
            candidate.get("conversation_id"),
            candidate.get("appointment_id"),
            candidate.get("payment_id"),
            candidate.get("lead_id"),
            candidate.get("specialist_agent_key"),
            candidate.get("playbook_id"),
            candidate.get("playbook_version_id"),
            candidate.get("objective"),
            candidate.get("recommended_action"),
            candidate.get("channel") or "whatsapp",
            scheduled_for,
            candidate.get("message_text"),
            to_json(action_payload),
            to_json({**(metadata or {}), "materialized_by": actor_user_id}),
            now,
            now,
        ),
    )
    exposure = _record_outcome_exposure(conn, candidate=candidate, run_id=run_id, actor_user_id=actor_user_id) if record_exposure else None
    if exposure:
        execute(conn, "UPDATE proactive_playbook_runs SET outcome_exposure_id = ?, updated_at = ? WHERE id = ?", (exposure.get("id"), now, run_id))
    execute(conn, "UPDATE proactive_contact_candidates SET status = 'materialized', updated_at = ? WHERE id = ?", (now, candidate_id))
    run = fetch_one(conn, "SELECT * FROM proactive_playbook_runs WHERE id = ?", (run_id,)) or {}
    return {"candidate": _serialize_candidate(fetch_one(conn, "SELECT * FROM proactive_contact_candidates WHERE id = ?", (candidate_id,))), "run": _serialize_run(run), "exposure": exposure, "deduped": False}


def list_proactive_runs(conn, *, organization_id: str, bot_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    ensure_proactive_reasoning_schema(conn)
    if bot_id:
        rows = fetch_all(
            conn,
            "SELECT * FROM proactive_playbook_runs WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT ?",
            (organization_id, bot_id, limit),
        )
    else:
        rows = fetch_all(conn, "SELECT * FROM proactive_playbook_runs WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, limit))
    return [_serialize_run(item) for item in rows]
