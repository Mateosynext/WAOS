from __future__ import annotations

from .schema_sql import apply_migration_sql

import datetime as dt
from dataclasses import dataclass
from typing import Any

from .agent_policy_runtime import get_policy_profile_for_specialist, serialize_policy_profile
from .db import execute, fetch_all, fetch_one, table_exists
from .repositories.proactive_reasoning import (
    attach_exposure_to_run as repo_attach_exposure_to_run,
    find_preferred_conversation as repo_find_preferred_conversation,
    get_candidate_by_id as repo_get_candidate_by_id,
    get_latest_run_for_candidate as repo_get_latest_run_for_candidate,
    get_outcome_exposure_by_id as repo_get_outcome_exposure_by_id,
    insert_outcome_exposure_for_playbook as repo_insert_outcome_exposure_for_playbook,
    insert_playbook_run as repo_insert_playbook_run,
    insert_proactive_signal as repo_insert_proactive_signal,
    list_candidate_rows as repo_list_candidate_rows,
    list_proactive_run_rows,
    load_contact_context as repo_load_contact_context,
    mark_candidate_materialized as repo_mark_candidate_materialized,
    recent_run_counts as repo_recent_run_counts,
    select_contacts as repo_select_contacts,
    upsert_proactive_candidate as repo_upsert_proactive_candidate,
)
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
    apply_migration_sql(conn, '010_proactive_reasoning_engine.sql')


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
    return repo_select_contacts(conn, organization_id=organization_id, bot_id=bot_id, contact_ids=contact_ids, conversation_ids=conversation_ids, limit=limit)


def _contact_context(conn, *, organization_id: str, bot_id: str, contact_id: str, preferred_conversation_id: str | None) -> dict[str, Any]:
    return repo_load_contact_context(conn, organization_id=organization_id, bot_id=bot_id, contact_id=contact_id, preferred_conversation_id=preferred_conversation_id)


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
    return repo_recent_run_counts(conn, contact_id=contact_id, objective=objective, candidate_key=candidate_key, since_24h=_hours_ago(now, 24), since_7d=_days_ago(now, 7))


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
    return repo_insert_proactive_signal(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_id=contact_id,
        signal=signal,
        signal_family=_signal_family(signal["signal_key"]),
        event_at=event_at,
    )


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
    policy_profile = policy["profile"]
    decision = policy["decision"]
    return repo_upsert_proactive_candidate(
        conn,
        candidate_key=candidate_key,
        organization_id=organization_id,
        bot_id=bot_id,
        contact_id=contact_id,
        signal_row=signal_row,
        playbook_id=playbook.key,
        playbook_version_id=playbook.version,
        specialist_agent_key=playbook.specialist_agent_key,
        policy_profile_key=policy_profile.get("key"),
        policy_profile_version=policy_profile.get("version"),
        objective=playbook.objective,
        recommended_action=playbook.recommended_action,
        channel="whatsapp",
        priority_score=priority_score,
        priority_band=_priority_band(priority_score),
        eligible=bool(decision.get("eligible")),
        suppression_reason=decision.get("suppression_reason"),
        suggested_send_at=suggested_send_at,
        title=title,
        message_text=message_text,
        timing_policy_id=playbook.timing_policy_id,
        nba_policy_id=playbook.nba_policy_id,
        policy=policy,
        reasoning={"signal": from_json(signal_row.get("facts_json"), {}), "warnings": decision.get("warnings") or []},
        metadata=metadata,
    )


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
            pref_conv = (repo_find_preferred_conversation(conn, contact_id=contact["id"], conversation_ids=conversation_ids) or {}).get("id")
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
    rows = repo_list_candidate_rows(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        status=status,
        specialist_agent_key=specialist_agent_key,
        eligible=eligible,
        limit=limit,
    )
    return [_serialize_candidate(item) for item in rows]


def _record_outcome_exposure(conn, *, candidate: dict[str, Any], run_id: str, actor_user_id: str | None) -> dict[str, Any] | None:
    if not table_exists(conn, "outcome_exposures"):
        return None
    return repo_insert_outcome_exposure_for_playbook(conn, candidate=candidate, run_id=run_id, actor_user_id=actor_user_id)


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
    candidate = _serialize_candidate(repo_get_candidate_by_id(conn, candidate_id))
    if not candidate:
        raise ValueError("candidate_not_found")
    existing = repo_get_latest_run_for_candidate(conn, candidate_id)
    if existing:
        return {
            "candidate": candidate,
            "run": _serialize_run(existing),
            "exposure": repo_get_outcome_exposure_by_id(conn, existing.get("outcome_exposure_id")),
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
    run = repo_insert_playbook_run(
        conn,
        candidate=candidate,
        scheduled_for=scheduled_for,
        action_payload=action_payload,
        metadata={**(metadata or {}), "materialized_by": actor_user_id},
    )
    run_id = run.get("id")
    exposure = _record_outcome_exposure(conn, candidate=candidate, run_id=run_id, actor_user_id=actor_user_id) if record_exposure else None
    if exposure:
        run = repo_attach_exposure_to_run(conn, run_id=run_id, exposure_id=exposure.get("id"), updated_at=now) or run
    candidate_row = repo_mark_candidate_materialized(conn, candidate_id=candidate_id, updated_at=now)
    return {"candidate": _serialize_candidate(candidate_row), "run": _serialize_run(run), "exposure": exposure, "deduped": False}


def list_proactive_runs(conn, *, organization_id: str, bot_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    ensure_proactive_reasoning_schema(conn)
    return [_serialize_run(item) for item in list_proactive_run_rows(conn, organization_id=organization_id, bot_id=bot_id, limit=limit)]
