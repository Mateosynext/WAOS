from __future__ import annotations

from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ..db import execute, fetch_all, fetch_one
from ..repositories import create_audit_log, create_message, get_bot, get_contact, get_conversation
from ..utils import add_minutes, from_json, new_id, parse_iso, to_json, utcnow_iso

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "reports"

def _json(row: dict | None, key: str, default: Any):
    if not row:
        return default
    return from_json(row.get(key), default)


def director_dashboard(conn, organization_id: str) -> dict[str, Any]:
    leads = fetch_one(conn, "SELECT COUNT(*) as value FROM crm_leads WHERE organization_id = ?", (organization_id,))
    rescued = fetch_one(conn, "SELECT COUNT(*) as value FROM reactivation_recommendations WHERE organization_id = ?", (organization_id,))
    appointments = fetch_one(conn, "SELECT COUNT(*) as value FROM appointments WHERE organization_id = ? AND status IN ('scheduled','confirmed')", (organization_id,))
    paid = fetch_one(conn, "SELECT COUNT(*) as value FROM commerce_payments WHERE organization_id = ? AND status = 'paid'", (organization_id,))
    revenue = fetch_one(conn, "SELECT COALESCE(SUM(amount),0) as value FROM commerce_payments WHERE organization_id = ? AND status = 'paid'", (organization_id,))
    ai_msgs = fetch_one(conn, "SELECT COUNT(*) as value FROM messages WHERE organization_id = ? AND source = 'ai' AND direction = 'outbound'", (organization_id,))
    inbound = fetch_one(conn, "SELECT COUNT(*) as value FROM messages WHERE organization_id = ? AND direction = 'inbound'", (organization_id,))
    response_rate = round((int(ai_msgs.get('value') or 0) / max(1, int(inbound.get('value') or 0))) * 100, 1)
    conversion_rate = round((int(paid.get('value') or 0) / max(1, int(leads.get('value') or 0))) * 100, 1)
    return {
        "summary": {
            "leads_attended": int(leads.get("value") or 0),
            "leads_rescued_by_ai": int(rescued.get("value") or 0),
            "hours_saved": round((int(ai_msgs.get("value") or 0) * 2) / 60, 1),
            "appointments_scheduled": int(appointments.get("value") or 0),
            "sales_generated": int(paid.get("value") or 0),
            "response_rate": response_rate,
            "conversion_rate": conversion_rate,
            "attributed_revenue": float(revenue.get("value") or 0),
        },
        "narrative": [
            "WAOS ya opera como copiloto comercial: capta, califica, da seguimiento, cobra y reporta.",
            "El foco recomendado es empujar recuperación automática y playbooks por industria para mejorar cierre.",
        ],
    }


def _generate_executive_report_base(conn, *, organization_id: str, period_start: str, period_end: str, bot_id: str | None = None, delivery_channels: list[str] | None = None) -> dict:
    delivery_channels = delivery_channels or ["email", "whatsapp", "pdf"]
    lead_where = "organization_id = ?"
    lead_params: list[Any] = [organization_id]
    if bot_id:
        lead_where += " AND bot_id = ?"
        lead_params.append(bot_id)
    leads = fetch_one(conn, f"SELECT COUNT(*) as value FROM crm_leads WHERE {lead_where}", lead_params)
    qualified = fetch_one(conn, f"SELECT COUNT(*) as value FROM crm_leads WHERE {lead_where} AND stage NOT IN ('nuevo')", lead_params)
    human = fetch_one(conn, "SELECT COUNT(*) as value FROM conversations WHERE organization_id = ? AND human_takeover = 1", (organization_id,))
    sold = fetch_one(conn, "SELECT COUNT(*) as value FROM commerce_payments WHERE organization_id = ? AND status = 'paid'", (organization_id,))
    sold_amount = fetch_one(conn, "SELECT COALESCE(SUM(amount),0) as value FROM commerce_payments WHERE organization_id = ? AND status = 'paid'", (organization_id,))
    campaigns = fetch_all(conn, "SELECT source_campaign, COUNT(*) as total FROM crm_leads WHERE organization_id = ? GROUP BY source_campaign ORDER BY total DESC LIMIT 5", (organization_id,))
    objections = Counter()
    for row in fetch_all(conn, "SELECT detected_objections_json FROM crm_leads WHERE organization_id = ?", (organization_id,)):
        objections.update(_json(row, "detected_objections_json", []))
    agent_reviews = fetch_all(conn, "SELECT agent_user_id, AVG(quality_score) as avg_score, COUNT(*) as total FROM conversation_reviews WHERE organization_id = ? GROUP BY agent_user_id ORDER BY avg_score DESC", (organization_id,))
    next_actions = [
        "Activar recuperación automática sobre cotizaciones no cerradas.",
        "Empujar link de pago en leads con probabilidad de cierre mayor a 75%.",
        "Revisar agentes con score menor a 80 para coaching semanal.",
    ]
    report = {
        "period": {"start": period_start, "end": period_end},
        "summary": {
            "leads_entered": int(leads.get("value") or 0),
            "qualified": int(qualified.get("value") or 0),
            "passed_to_human": int(human.get("value") or 0),
            "sales_count": int(sold.get("value") or 0),
            "sales_amount": float(sold_amount.get("value") or 0),
        },
        "best_campaigns": campaigns,
        "repeated_objections": [{"objection": k, "count": v} for k, v in objections.most_common(5)],
        "top_advisors": agent_reviews,
        "recommended_next_week": next_actions,
        "delivery_formats": delivery_channels,
        "email_subject": f"WAOS Insights semanal · {period_start} a {period_end}",
        "whatsapp_text": f"Reporte WAOS: {int(leads.get('value') or 0)} leads, {int(sold.get('value') or 0)} ventas, ingreso {float(sold_amount.get('value') or 0):.2f}.",
        "pdf_ready": True,
    }
    report_id = new_id("rpt")
    now = utcnow_iso()
    execute(
        conn,
        "INSERT INTO executive_reports (id, organization_id, bot_id, period_start, period_end, report_type, summary_json, delivery_channels_json, generated_at, created_at) VALUES (?, ?, ?, ?, ?, 'weekly', ?, ?, ?, ?)",
        (report_id, organization_id, bot_id, period_start, period_end, to_json(report), to_json(delivery_channels), now, now),
    )
    saved = fetch_one(conn, "SELECT * FROM executive_reports WHERE id = ?", (report_id,))
    return {**saved, "summary": report}


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "waos-report"


def _pdf_lines(report: dict[str, Any]) -> list[str]:
    summary = report.get("summary", {})
    return [
        f"Periodo: {report.get('period', {}).get('start')} a {report.get('period', {}).get('end')}",
        f"Leads entrados: {summary.get('leads_entered', 0)}",
        f"Leads calificados: {summary.get('qualified', 0)}",
        f"Pasados a humano: {summary.get('passed_to_human', 0)}",
        f"Ventas: {summary.get('sales_count', 0)}",
        f"Monto vendido: {summary.get('sales_amount', 0)}",
        "",
        "Campañas top:",
        *[f"- {item.get('source_campaign') or '-'}: {item.get('total', 0)}" for item in report.get('best_campaigns', [])[:5]],
        "",
        "Objeciones repetidas:",
        *[f"- {item.get('objection')}: {item.get('count', 0)}" for item in report.get('repeated_objections', [])[:5]],
        "",
        "Recomendado la próxima semana:",
        *[f"- {item}" for item in report.get('recommended_next_week', [])[:5]],
    ]


def build_report_pdf(report_id: str, report: dict[str, Any]) -> dict[str, str]:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_filename(report.get('email_subject') or report_id)}-{report_id}.pdf"
    path = ARTIFACTS_DIR / filename
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 50
    c.setTitle(report.get("email_subject") or "WAOS Insights")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "WAOS Insights")
    y -= 24
    c.setFont("Helvetica", 11)
    for line in _pdf_lines(report):
        if y < 55:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)
        c.drawString(40, y, str(line)[:110])
        y -= 16
    c.save()
    return {"pdf_path": str(path), "pdf_filename": filename}


def ensure_executive_report_pdf(conn, report_row: dict[str, Any]) -> dict[str, Any]:
    summary = from_json(report_row.get("summary_json"), {})
    pdf_meta = build_report_pdf(report_row["id"], summary)
    execute(
        conn,
        "UPDATE executive_reports SET pdf_path = ?, pdf_filename = ?, pdf_generated_at = ?, updated_at = ? WHERE id = ?",
        (pdf_meta["pdf_path"], pdf_meta["pdf_filename"], utcnow_iso(), utcnow_iso(), report_row["id"]),
    )
    refreshed = fetch_one(conn, "SELECT * FROM executive_reports WHERE id = ?", (report_row["id"],)) or report_row
    return {**refreshed, **pdf_meta, "summary": summary}


def omnichannel_overview(conn, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = [organization_id]
    bot_clause = ""
    if bot_id:
        bot_clause = " AND bot_id = ?"
        params.append(bot_id)
    channels = fetch_all(
        conn,
        f"SELECT source_channel AS channel, COUNT(*) AS total FROM crm_leads WHERE organization_id = ?{bot_clause} GROUP BY source_channel ORDER BY total DESC",
        params,
    )
    active = fetch_all(
        conn,
        f"SELECT c.id, c.status, c.updated_at, ct.name, ct.phone FROM conversations c JOIN contacts ct ON ct.id = c.contact_id WHERE c.organization_id = ?{' AND c.bot_id = ?' if bot_id else ''} ORDER BY c.updated_at DESC LIMIT 10",
        params,
    )
    return {
        "summary": {
            "channels": channels,
            "active_threads": len(active),
            "recommended_channels": ["whatsapp", "instagram_dm", "webchat"],
        },
        "threads": active,
    }


def generate_executive_report(conn, *, organization_id: str, period_start: str, period_end: str, bot_id: str | None = None, delivery_channels: list[str] | None = None) -> dict:
    saved = _generate_executive_report_base(conn, organization_id=organization_id, period_start=period_start, period_end=period_end, bot_id=bot_id, delivery_channels=delivery_channels)
    report = saved.get("summary") or {}
    pdf_meta = build_report_pdf(saved["id"], report)
    execute(
        conn,
        "UPDATE executive_reports SET pdf_path = ?, pdf_filename = ?, pdf_generated_at = ?, updated_at = ? WHERE id = ?",
        (pdf_meta["pdf_path"], pdf_meta["pdf_filename"], utcnow_iso(), utcnow_iso(), saved["id"]),
    )
    refreshed = fetch_one(conn, "SELECT * FROM executive_reports WHERE id = ?", (saved["id"],)) or saved
    return {
        **refreshed,
        "summary": report,
        **pdf_meta,
    }
