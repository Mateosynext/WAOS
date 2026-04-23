from __future__ import annotations

from ..utils import add_minutes, parse_iso, utcnow_iso


def queue_role_for_item(item: dict) -> tuple[str, str]:
    intent = str(item.get("current_intent") or "").lower()
    if int(item.get("pending_payment_count") or 0) > 0 or intent in {"payment", "invoice", "cobranza", "charge"}:
        return "cobranza", "Tiene pago pendiente o intento de cobro activo"
    if int(item.get("appointment_count") or 0) > 0 or intent in {"schedule", "appointment", "reschedule", "booking"}:
        return "agenda", "Tiene cita o intención clara de agenda"
    if int(item.get("lead_score") or 0) >= 60 or int(item.get("close_probability") or 0) >= 60 or str(item.get("lead_stage") or "").lower() in {"hot", "qualified", "propuesta", "cotizacion", "nuevo"}:
        return "ventas", "Lead activo con oportunidad comercial"
    return "soporte", "Necesita seguimiento operativo o soporte humano"


def sla_for_item(item: dict) -> dict[str, int | str]:
    role_key, _ = queue_role_for_item(item)
    now = parse_iso(utcnow_iso())
    anchor = parse_iso(item.get("last_inbound_at") or item.get("updated_at") or item.get("created_at"))
    overdue_minutes = 0
    target_minutes = {"ventas": 10, "soporte": 20, "agenda": 8, "cobranza": 15}.get(role_key, 15)
    if anchor and now:
        overdue_minutes = max(0, int((now - anchor).total_seconds() // 60) - target_minutes)
    status = "healthy"
    if overdue_minutes > 0:
        status = "breached"
    elif anchor and now and int((now - anchor).total_seconds() // 60) >= max(1, target_minutes - 3):
        status = "at_risk"
    due_at = add_minutes(item.get("last_inbound_at") or item.get("updated_at") or utcnow_iso(), target_minutes)
    return {
        "role_key": role_key,
        "target_minutes": target_minutes,
        "due_at": due_at,
        "status": status,
        "overdue_minutes": overdue_minutes,
    }
