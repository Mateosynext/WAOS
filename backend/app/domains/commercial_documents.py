from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ..repositories import create_audit_log, get_contact
from ..repositories.base import execute, fetch_all, fetch_one
from ..utils import from_json, new_id, to_json, utcnow_iso

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "commercial_documents"
DOC_TYPE_PREFIX = {
    "quote": "COT",
    "work_order": "OT",
    "receipt": "REC",
    "proposal": "PROP",
    "warranty": "GAR",
}
DOC_TYPE_LABEL = {
    "quote": "Presupuesto",
    "work_order": "Orden de trabajo",
    "receipt": "Recibo",
    "proposal": "Propuesta comercial",
    "warranty": "Garantia",
}
DEFAULT_TERMS = {
    "quote": "Vigencia sujeta a disponibilidad. Cambios de alcance, materiales o zona pueden ajustar el total final. Este documento no sustituye factura fiscal.",
    "work_order": "La orden describe el alcance aprobado. Cambios en sitio requieren autorizacion antes de ejecutarse.",
    "receipt": "Comprobante interno de pago. Este recibo no sustituye factura fiscal cuando aplique.",
    "proposal": "Propuesta sujeta a validacion de alcance y disponibilidad operativa.",
    "warranty": "La garantia aplica solo sobre el alcance descrito y bajo las condiciones especificadas.",
}


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "waos-documento"


def _parse_row(row: dict | None) -> dict:
    if not row:
        return {}
    parsed = dict(row)
    for key, default in {
        "missing_questions_json": [],
        "approval_reasons_json": [],
        "next_actions_json": [],
        "metadata_json": {},
    }.items():
        parsed[key[:-5] if key.endswith("_json") else key] = from_json(parsed.get(key), default)
    return parsed


def _parse_item(row: dict) -> dict:
    parsed = dict(row)
    parsed["metadata"] = from_json(parsed.get("metadata_json"), {})
    return parsed


def _parse_branding(row: dict | None) -> dict:
    if not row:
        return {}
    parsed = dict(row)
    parsed["metadata"] = from_json(parsed.get("metadata_json"), {})
    return parsed


def _money(value: Any, currency: str = "MXN") -> str:
    try:
        amount = float(value or 0)
    except Exception:
        amount = 0.0
    return f"${amount:,.2f} {currency}"


def _clean_color(value: str | None, fallback: colors.Color) -> colors.Color:
    if not value:
        return fallback
    value = value.strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        return fallback
    return colors.HexColor(value)


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word]).strip()
        if len(candidate) <= max_chars:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [""]


def _document_with_items(conn, document_id: str) -> dict:
    document = _parse_row(fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,)))
    if not document:
        return {}
    items = fetch_all(conn, "SELECT * FROM commercial_document_items WHERE document_id = ? ORDER BY sort_order ASC, created_at ASC", (document_id,))
    events = fetch_all(conn, "SELECT * FROM commercial_document_events WHERE document_id = ? ORDER BY created_at DESC LIMIT 20", (document_id,))
    document["items"] = [_parse_item(item) for item in items]
    document["events"] = [{**dict(event), "metadata": from_json(event.get("metadata_json"), {})} for event in events]
    return document


def _folio(conn, organization_id: str, document_type: str) -> str:
    prefix = DOC_TYPE_PREFIX.get(document_type, "DOC")
    row = fetch_one(conn, "SELECT COUNT(*) AS value FROM commercial_documents WHERE organization_id = ? AND document_type = ?", (organization_id, document_type))
    count = int((row or {}).get("value") or 0) + 1
    return f"{prefix}-{count:06d}"


def _item_total(item: dict[str, Any]) -> float:
    quantity = max(0, float(item.get("quantity") or 0))
    unit_price = float(item.get("unit_price") or 0)
    discount = max(0, float(item.get("discount") or 0))
    tax = max(0, float(item.get("tax") or 0))
    return max(0.0, quantity * unit_price - discount + tax)


def _totals(items: list[dict[str, Any]], deposit_required: float = 0) -> dict[str, float]:
    subtotal = 0.0
    discount_total = 0.0
    tax_total = 0.0
    total = 0.0
    for item in items:
        quantity = max(0, float(item.get("quantity") or 0))
        unit_price = float(item.get("unit_price") or 0)
        subtotal += quantity * unit_price
        discount_total += max(0, float(item.get("discount") or 0))
        tax_total += max(0, float(item.get("tax") or 0))
        total += _item_total(item)
    deposit = min(max(0.0, float(deposit_required or 0)), total)
    return {
        "subtotal": round(subtotal, 2),
        "discount_total": round(discount_total, 2),
        "tax_total": round(tax_total, 2),
        "total": round(total, 2),
        "deposit_required": round(deposit, 2),
        "balance_due": round(max(0.0, total - deposit), 2),
    }


def _record_event(conn, *, organization_id: str, document_id: str, event_type: str, actor_type: str = "system", actor_id: str | None = None, metadata: dict[str, Any] | None = None) -> dict:
    now = utcnow_iso()
    row_id = new_id("cde")
    execute(
        conn,
        "INSERT INTO commercial_document_events (id, organization_id, document_id, event_type, actor_type, actor_id, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, organization_id, document_id, event_type, actor_type, actor_id, to_json(metadata or {}), now),
    )
    return fetch_one(conn, "SELECT * FROM commercial_document_events WHERE id = ?", (row_id,)) or {}


def get_organization_branding(conn, organization_id: str) -> dict:
    branding = fetch_one(conn, "SELECT * FROM organization_branding WHERE organization_id = ?", (organization_id,))
    org = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (organization_id,)) or {}
    parsed = _parse_branding(branding)
    if parsed:
        return parsed
    return {
        "organization_id": organization_id,
        "business_name": org.get("name") or "WAOS Business",
        "legal_name": org.get("name"),
        "primary_color": "#25D366",
        "secondary_color": "#111827",
        "footer_note": "Documento generado por WAOS Smart Docs.",
        "metadata": {},
    }


def upsert_organization_branding(conn, *, actor_user: dict | None = None, **payload: Any) -> dict:
    now = utcnow_iso()
    organization_id = payload["organization_id"]
    current = fetch_one(conn, "SELECT * FROM organization_branding WHERE organization_id = ?", (organization_id,))
    values = {
        "business_name": payload.get("business_name") or payload.get("legal_name") or "",
        "legal_name": payload.get("legal_name"),
        "logo_url": payload.get("logo_url"),
        "primary_color": payload.get("primary_color") or "#25D366",
        "secondary_color": payload.get("secondary_color") or "#111827",
        "phone": payload.get("phone"),
        "whatsapp": payload.get("whatsapp"),
        "email": payload.get("email"),
        "website": payload.get("website"),
        "address": payload.get("address"),
        "footer_note": payload.get("footer_note"),
        "metadata_json": to_json(payload.get("metadata") or {}),
    }
    if current:
        execute(
            conn,
            """
            UPDATE organization_branding SET business_name = ?, legal_name = ?, logo_url = ?, primary_color = ?, secondary_color = ?, phone = ?, whatsapp = ?, email = ?, website = ?, address = ?, footer_note = ?, metadata_json = ?, updated_at = ?
            WHERE organization_id = ?
            """,
            (
                values["business_name"], values["legal_name"], values["logo_url"], values["primary_color"], values["secondary_color"],
                values["phone"], values["whatsapp"], values["email"], values["website"], values["address"], values["footer_note"],
                values["metadata_json"], now, organization_id,
            ),
        )
    else:
        execute(
            conn,
            """
            INSERT INTO organization_branding (id, organization_id, business_name, legal_name, logo_url, primary_color, secondary_color, phone, whatsapp, email, website, address, footer_note, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("brand"), organization_id, values["business_name"], values["legal_name"], values["logo_url"], values["primary_color"], values["secondary_color"],
                values["phone"], values["whatsapp"], values["email"], values["website"], values["address"], values["footer_note"],
                values["metadata_json"], now, now,
            ),
        )
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="organization_branding", entity_id=organization_id, action="commercial_docs.branding_upserted", metadata={"business_name": values["business_name"]})
    return get_organization_branding(conn, organization_id)


def list_commercial_documents(conn, organization_id: str, *, bot_id: str | None = None, document_type: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM commercial_documents WHERE organization_id = ?"
    if bot_id:
        sql += " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    if document_type:
        sql += " AND document_type = ?"
        params.append(document_type)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(max(1, min(int(limit or 50), 100)))
    rows = fetch_all(conn, sql, params)
    return [{**_parse_row(row), "items": [_parse_item(item) for item in fetch_all(conn, "SELECT * FROM commercial_document_items WHERE document_id = ? ORDER BY sort_order ASC", (row["id"],))]} for row in rows]


def commercial_documents_overview(conn, organization_id: str, bot_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = [organization_id]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    rows = fetch_all(
        conn,
        f"""
        SELECT document_type, status, COUNT(*) AS total, COALESCE(SUM(total), 0) AS amount
        FROM commercial_documents
        WHERE organization_id = ?{bot_sql}
        GROUP BY document_type, status
        ORDER BY document_type ASC, status ASC
        """,
        params,
    )
    sent_amount = fetch_one(conn, f"SELECT COALESCE(SUM(total), 0) AS value FROM commercial_documents WHERE organization_id = ?{bot_sql} AND status IN ('sent','viewed','accepted','paid','converted')", params)
    accepted_amount = fetch_one(conn, f"SELECT COALESCE(SUM(total), 0) AS value FROM commercial_documents WHERE organization_id = ?{bot_sql} AND status IN ('accepted','paid','converted','completed')", params)
    pending_approval = fetch_one(conn, f"SELECT COUNT(*) AS value FROM commercial_documents WHERE organization_id = ?{bot_sql} AND status = 'requires_approval'", params)
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    amount_by_type: dict[str, float] = {}
    for row in rows:
        by_status[str(row.get("status") or "draft")] = by_status.get(str(row.get("status") or "draft"), 0) + int(row.get("total") or 0)
        dtype = str(row.get("document_type") or "quote")
        by_type[dtype] = by_type.get(dtype, 0) + int(row.get("total") or 0)
        amount_by_type[dtype] = amount_by_type.get(dtype, 0.0) + float(row.get("amount") or 0)
    docs = list_commercial_documents(conn, organization_id, bot_id=bot_id, limit=10)
    total_docs = sum(int(row.get("total") or 0) for row in rows)
    accepted_docs = sum(int(row.get("total") or 0) for row in rows if row.get("status") in {"accepted", "paid", "converted", "completed"})
    return {
        "summary": {
            "documents": total_docs,
            "sent_amount": float((sent_amount or {}).get("value") or 0),
            "accepted_amount": float((accepted_amount or {}).get("value") or 0),
            "acceptance_rate": round((accepted_docs / max(1, total_docs)) * 100, 1),
            "pending_approval": int((pending_approval or {}).get("value") or 0),
        },
        "by_status": by_status,
        "by_type": by_type,
        "amount_by_type": amount_by_type,
        "recent": docs,
        "recommendations": [
            "Activa anticipo para presupuestos aceptados de mayor ticket.",
            "Usa opciones Basica, Recomendada y Premium para elevar ticket promedio.",
            "Bloquea envio automatico cuando el catalogo tenga precio variable o falten datos clave.",
        ],
    }


def _infer_customer(conn, contact_id: str | None) -> dict[str, str | None]:
    if not contact_id:
        return {"customer_name": None, "customer_phone": None, "customer_email": None}
    contact = get_contact(conn, contact_id) or {}
    return {
        "customer_name": contact.get("name") or contact.get("full_name"),
        "customer_phone": contact.get("phone"),
        "customer_email": contact.get("email"),
    }


def _active_catalog(conn, organization_id: str, bot_id: str | None = None) -> tuple[list[dict], list[dict]]:
    params: list[Any] = [organization_id]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    products = fetch_all(conn, f"SELECT * FROM catalog_products WHERE organization_id = ?{bot_sql} AND status = 'active' ORDER BY priority DESC, updated_at DESC", params)
    services = fetch_all(conn, f"SELECT * FROM catalog_services WHERE organization_id = ?{bot_sql} AND status = 'active' ORDER BY updated_at DESC", params)
    return products, services


def _catalog_item_to_doc_item(row: dict, source_type: str) -> dict[str, Any]:
    description = row.get("short_description") if source_type == "product" else row.get("preparation")
    unit = "unidad" if source_type == "product" else "servicio"
    if source_type == "service" and int(row.get("duration_minutes") or 0) >= 60:
        unit = "servicio"
    return {
        "source_type": source_type,
        "source_id": row.get("id"),
        "name": row.get("name") or "Concepto",
        "description": description or "",
        "quantity": 1,
        "unit": unit,
        "unit_price": float(row.get("promotional_price") or row.get("price") or 0),
        "discount": 0,
        "tax": 0,
        "metadata": {
            "catalog_status": row.get("status"),
            "duration_minutes": row.get("duration_minutes"),
            "pricing_model": from_json(row.get("availability_json"), {}).get("pricing_model") if source_type == "service" else from_json(row.get("specs_json"), {}).get("pricing_model"),
        },
    }


def _match_catalog_items(products: list[dict], services: list[dict], request_text: str, catalog_item_ids: list[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    request = (request_text or "").lower()
    ids = set(catalog_item_ids or [])
    for source_type, rows in (("product", products), ("service", services)):
        for row in rows:
            row_id = str(row.get("id") or "")
            name = str(row.get("name") or "").lower()
            tokens = [token for token in re.split(r"\W+", name) if len(token) >= 4]
            direct = row_id in ids
            semantic = bool(request and name and (name in request or any(token in request for token in tokens[:4])))
            if (direct or semantic) and row_id not in seen:
                selected.append(_catalog_item_to_doc_item(row, source_type))
                seen.add(row_id)
    return selected



def _apply_quote_rules(conn, organization_id: str, bot_id: str | None, items: list[dict[str, Any]], request_text: str) -> tuple[list[dict[str, Any]], float, list[str]]:
    enriched: list[dict[str, Any]] = []
    terms: list[str] = []
    max_deposit_percent = 0.0
    numbers = [float(match) for match in re.findall(r"\b\d+(?:\.\d+)?\b", request_text or "")]
    for item in items:
        params: list[Any] = [organization_id, item.get("source_type"), item.get("source_id")]
        sql = "SELECT * FROM catalog_quote_rules WHERE organization_id = ? AND catalog_item_type = ? AND catalog_item_id = ? AND is_active = 1"
        if bot_id:
            sql += " AND (bot_id = ? OR bot_id IS NULL)"
            params.append(bot_id)
        sql += " ORDER BY updated_at DESC LIMIT 1"
        rule = fetch_one(conn, sql, params)
        next_item = dict(item)
        if rule:
            pricing_model = str(rule.get("pricing_model") or "fixed")
            minimum_quantity = max(1.0, float(rule.get("minimum_quantity") or 1))
            if rule.get("base_price") is not None:
                next_item["unit_price"] = float(rule.get("base_price") or 0)
            next_item["unit"] = rule.get("unit_label") or next_item.get("unit") or "unidad"
            if pricing_model in {"hourly", "per_hour", "m2", "per_unit"}:
                next_item["quantity"] = max(minimum_quantity, numbers[0] if numbers else float(next_item.get("quantity") or 1))
            if float(rule.get("travel_fee") or 0) > 0:
                enriched.append({
                    "source_type": "fee",
                    "source_id": rule.get("id"),
                    "name": "Servicio a domicilio / traslado",
                    "description": "Cargo configurado en reglas de cotizacion del catalogo.",
                    "quantity": 1,
                    "unit": "servicio",
                    "unit_price": float(rule.get("travel_fee") or 0),
                    "discount": 0,
                    "tax": 0,
                    "metadata": {"quote_rule_id": rule.get("id")},
                })
            next_item["metadata"] = {
                **(next_item.get("metadata") or {}),
                "quote_rule_id": rule.get("id"),
                "pricing_model": pricing_model,
                "required_questions": from_json(rule.get("required_questions_json"), []),
                "approval_rules": from_json(rule.get("approval_rules_json"), {}),
            }
            max_deposit_percent = max(max_deposit_percent, float(rule.get("deposit_percent") or 0))
            if rule.get("terms"):
                terms.append(str(rule.get("terms")))
        enriched.append(next_item)
    return enriched, max_deposit_percent, terms


def _missing_questions_for_request(request_text: str, items: list[dict[str, Any]]) -> list[str]:
    text = (request_text or "").lower()
    questions: list[str] = []
    required_from_rules: list[str] = []
    for item in items:
        required_from_rules.extend(str(question) for question in ((item.get("metadata") or {}).get("required_questions") or []))
    if not items:
        questions.append("Que producto o servicio del catalogo quiere cotizar el cliente?")
    if not re.search(r"\b\d+\b", text):
        questions.append("Cantidad, piezas, horas o metros a cotizar.")
    if any(word in text for word in ["domicilio", "visita", "instal", "mantenimiento", "servicio"]) and not any(word in text for word in ["colonia", "direccion", "zona", "ubicacion", "ciudad"]):
        questions.append("Zona o direccion donde se realizara el servicio.")
    if any(float(item.get("unit_price") or 0) <= 0 for item in items):
        questions.append("Validar precio final porque hay conceptos sin precio en catalogo.")
    for question in required_from_rules:
        if question and question not in questions:
            questions.append(question)
    return questions
def _approval_reasons(items: list[dict[str, Any]], missing_questions: list[str], total: float) -> list[str]:
    reasons: list[str] = []
    if missing_questions:
        reasons.append("Faltan datos para enviar precio final sin riesgo.")
    if total <= 0:
        reasons.append("El total calculado es cero; requiere revision humana.")
    if total >= 50000:
        reasons.append("Monto alto; requiere aprobacion antes de envio.")
    if any((item.get("metadata") or {}).get("pricing_model") in {"variable", "from", "custom"} for item in items):
        reasons.append("Hay conceptos con precio variable o desde; requiere validacion.")
    return reasons


def create_commercial_document(conn, *, actor_user: dict | None = None, **payload: Any) -> dict:
    now = utcnow_iso()
    document_type = payload.get("document_type") or "quote"
    organization_id = payload["organization_id"]
    items = [dict(item) for item in payload.get("items") or []]
    totals = _totals(items, payload.get("deposit_required") or 0)
    status = payload.get("status") or "draft"
    if payload.get("approval_reasons") and status == "draft":
        status = "requires_approval"
    elif payload.get("missing_questions") and status == "draft":
        status = "requires_data"
    row_id = new_id("cdoc")
    folio = _folio(conn, organization_id, document_type)
    execute(
        conn,
        """
        INSERT INTO commercial_documents (
            id, organization_id, bot_id, conversation_id, contact_id, template_id, document_type, folio, status, title,
            customer_name, customer_phone, customer_email, customer_address, summary, currency, subtotal, discount_total,
            tax_total, total, deposit_required, balance_due, valid_until, public_url, payment_url, terms, notes,
            missing_questions_json, approval_reasons_json, next_actions_json, metadata_json, created_by_user_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id, organization_id, payload.get("bot_id"), payload.get("conversation_id"), payload.get("contact_id"), payload.get("template_id"),
            document_type, folio, status, payload.get("title") or DOC_TYPE_LABEL.get(document_type, "Documento comercial"),
            payload.get("customer_name"), payload.get("customer_phone"), payload.get("customer_email"), payload.get("customer_address"),
            payload.get("summary") or "", payload.get("currency") or "MXN", totals["subtotal"], totals["discount_total"], totals["tax_total"],
            totals["total"], totals["deposit_required"], totals["balance_due"], payload.get("valid_until"), payload.get("public_url"),
            payload.get("payment_url"), payload.get("terms") or DEFAULT_TERMS.get(document_type, DEFAULT_TERMS["quote"]), payload.get("notes") or "",
            to_json(payload.get("missing_questions") or []), to_json(payload.get("approval_reasons") or []), to_json(payload.get("next_actions") or []),
            to_json(payload.get("metadata") or {}), actor_user.get("id") if actor_user else None, now, now,
        ),
    )
    for index, item in enumerate(items):
        total = _item_total(item)
        execute(
            conn,
            """
            INSERT INTO commercial_document_items (id, organization_id, document_id, source_type, source_id, name, description, quantity, unit, unit_price, discount, tax, total, sort_order, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("cdi"), organization_id, row_id, item.get("source_type") or "custom", item.get("source_id"), item.get("name") or "Concepto",
                item.get("description") or "", float(item.get("quantity") or 1), item.get("unit") or "unidad", float(item.get("unit_price") or 0),
                float(item.get("discount") or 0), float(item.get("tax") or 0), total, index, to_json(item.get("metadata") or {}), now, now,
            ),
        )
    _record_event(conn, organization_id=organization_id, document_id=row_id, event_type="created", actor_type="user" if actor_user else "system", actor_id=actor_user.get("id") if actor_user else None, metadata={"status": status, "document_type": document_type})
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="commercial_document", entity_id=row_id, action="commercial_document.created", metadata={"folio": folio, "status": status, "total": totals["total"]})
    return _document_with_items(conn, row_id)


def draft_commercial_document_from_catalog(conn, *, actor_user: dict | None = None, **payload: Any) -> dict:
    organization_id = payload["organization_id"]
    bot_id = payload.get("bot_id")
    products, services = _active_catalog(conn, organization_id, bot_id)
    items = _match_catalog_items(products, services, payload.get("request_text") or "", payload.get("catalog_item_ids") or [])
    if not items:
        items.append({
            "source_type": "custom",
            "source_id": None,
            "name": "Servicio por confirmar",
            "description": payload.get("request_text") or "Solicitud recibida por WhatsApp",
            "quantity": 1,
            "unit": "servicio",
            "unit_price": 0,
            "discount": 0,
            "tax": 0,
            "metadata": {"confidence": "requires_catalog_match"},
        })
    items, deposit_percent, rule_terms = _apply_quote_rules(conn, organization_id, bot_id, items, payload.get("request_text") or "")
    deposit_required = 0.0
    missing = _missing_questions_for_request(payload.get("request_text") or "", items)
    totals = _totals(items, 0)
    if deposit_percent > 0:
        deposit_required = round(totals["total"] * min(max(deposit_percent, 0), 100) / 100, 2)
    approvals = _approval_reasons(items, missing, totals["total"])
    contact = _infer_customer(conn, payload.get("contact_id"))
    document_type = payload.get("document_type") or "quote"
    next_actions = [
        "Enviar preguntas faltantes antes de precio final." if missing else "Enviar PDF al cliente por WhatsApp.",
        "Convertir a orden de trabajo cuando el cliente acepte.",
        "Cobrar anticipo si el servicio requiere agenda o materiales.",
    ]
    document = create_commercial_document(
        conn,
        actor_user=actor_user,
        organization_id=organization_id,
        bot_id=bot_id,
        conversation_id=payload.get("conversation_id"),
        contact_id=payload.get("contact_id"),
        document_type=document_type,
        status="requires_approval" if approvals else ("requires_data" if missing else "draft"),
        title=DOC_TYPE_LABEL.get(document_type, "Documento comercial"),
        customer_name=payload.get("customer_name") or contact.get("customer_name"),
        customer_phone=payload.get("customer_phone") or contact.get("customer_phone"),
        customer_email=payload.get("customer_email") or contact.get("customer_email"),
        customer_address=payload.get("customer_address"),
        summary=_build_summary(payload.get("request_text") or "", items, document_type),
        currency=(items[0].get("currency") if items else None) or "MXN",
        deposit_required=deposit_required,
        terms="\n".join(rule_terms) if rule_terms else DEFAULT_TERMS.get(document_type, DEFAULT_TERMS["quote"]),
        missing_questions=missing,
        approval_reasons=approvals,
        next_actions=next_actions,
        metadata={**(payload.get("metadata") or {}), "source": "draft_from_catalog", "request_text": payload.get("request_text") or "", "quote_rules_applied": bool(rule_terms)},
        items=items,
    )
    if payload.get("auto_generate_pdf", True):
        document = ensure_commercial_document_pdf(conn, document)
    return document


def draft_commercial_document_from_conversation(conn, *, actor_user: dict | None = None, **payload: Any) -> dict:
    conversation_id = payload.get("conversation_id")
    conversation = fetch_one(conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,)) if conversation_id else None
    if not conversation:
        return draft_commercial_document_from_catalog(conn, actor_user=actor_user, **payload)
    messages = fetch_all(conn, "SELECT body, direction FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT 40", (conversation_id,))
    request_text = payload.get("request_text") or "\n".join(str(row.get("body") or "") for row in messages if row.get("direction") == "inbound")
    merged = {**payload, "request_text": request_text, "organization_id": payload.get("organization_id") or conversation.get("organization_id"), "bot_id": payload.get("bot_id") or conversation.get("bot_id"), "contact_id": payload.get("contact_id") or conversation.get("contact_id")}
    return draft_commercial_document_from_catalog(conn, actor_user=actor_user, **merged)


def _build_summary(request_text: str, items: list[dict[str, Any]], document_type: str) -> str:
    names = ", ".join(item.get("name") or "concepto" for item in items[:4])
    label = DOC_TYPE_LABEL.get(document_type, "Documento comercial").lower()
    if request_text:
        return f"{label.capitalize()} generado a partir de la solicitud del cliente: {request_text[:220]}. Conceptos detectados: {names}."
    return f"{label.capitalize()} generado desde catalogo. Conceptos: {names}."


def update_commercial_document_status(conn, document_id: str, *, status: str, actor_user: dict | None = None, note: str | None = None, metadata: dict[str, Any] | None = None) -> dict:
    document = fetch_one(conn, "SELECT * FROM commercial_documents WHERE id = ?", (document_id,))
    if not document:
        return {}
    now = utcnow_iso()
    fields = "status = ?, updated_at = ?"
    params: list[Any] = [status, now]
    if status == "sent":
        fields += ", sent_at = ?"
        params.append(now)
    if status == "accepted":
        fields += ", accepted_at = ?"
        params.append(now)
    if status == "paid":
        fields += ", paid_at = ?"
        params.append(now)
    params.append(document_id)
    execute(conn, f"UPDATE commercial_documents SET {fields} WHERE id = ?", params)
    _record_event(conn, organization_id=document["organization_id"], document_id=document_id, event_type=f"status.{status}", actor_type="user" if actor_user else "system", actor_id=actor_user.get("id") if actor_user else None, metadata={"note": note, **(metadata or {})})
    return _document_with_items(conn, document_id)


def _draw_logo_or_mark(c: canvas.Canvas, branding: dict, x: float, y: float, size: float, primary: colors.Color) -> None:
    logo = branding.get("logo_url")
    if logo and not str(logo).startswith(("http://", "https://")):
        path = Path(str(logo))
        if path.exists():
            try:
                c.drawImage(ImageReader(str(path)), x, y - size, width=size, height=size, preserveAspectRatio=True, mask="auto")
                return
            except Exception:
                pass
    c.setFillColor(primary)
    c.roundRect(x, y - size, size, size, 10, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    initials = "".join(part[:1] for part in str(branding.get("business_name") or "WAOS").split()[:2]).upper() or "W"
    c.drawCentredString(x + size / 2, y - size / 2 - 5, initials[:3])


def _draw_text_block(c: canvas.Canvas, lines: list[str], x: float, y: float, max_width_chars: int, line_height: float = 13, font: str = "Helvetica", size: int = 9, color: colors.Color = colors.black) -> float:
    c.setFont(font, size)
    c.setFillColor(color)
    current_y = y
    for raw in lines:
        for line in _wrap_text(raw, max_width_chars):
            c.drawString(x, current_y, line[:max_width_chars + 8])
            current_y -= line_height
    return current_y


def build_commercial_document_pdf(document: dict[str, Any], branding: dict[str, Any]) -> dict[str, str]:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_filename(document.get('folio') or document.get('title') or document.get('id'))}-{document.get('id')}.pdf"
    path = ARTIFACTS_DIR / filename
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    primary = _clean_color(branding.get("primary_color"), colors.HexColor("#25D366"))
    secondary = _clean_color(branding.get("secondary_color"), colors.HexColor("#111827"))
    currency = document.get("currency") or "MXN"
    c.setTitle(f"{document.get('folio')} · {document.get('title')}")

    # Header
    c.setFillColor(secondary)
    c.rect(0, height - 118, width, 118, fill=1, stroke=0)
    _draw_logo_or_mark(c, branding, 42, height - 30, 54, primary)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(110, height - 52, str(branding.get("business_name") or "WAOS Business")[:44])
    c.setFont("Helvetica", 9)
    contact_line = " · ".join(filter(None, [branding.get("phone"), branding.get("whatsapp"), branding.get("email"), branding.get("website")]))
    c.drawString(110, height - 69, contact_line[:90])
    if branding.get("address"):
        c.drawString(110, height - 84, str(branding.get("address"))[:90])
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(width - 42, height - 52, DOC_TYPE_LABEL.get(document.get("document_type"), "Documento"))
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 42, height - 70, str(document.get("folio") or ""))
    c.drawRightString(width - 42, height - 86, f"Estado: {document.get('status') or 'draft'}")

    y = height - 150
    c.setFillColor(secondary)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(42, y, str(document.get("title") or DOC_TYPE_LABEL.get(document.get("document_type"), "Documento"))[:80])
    y -= 22
    summary = document.get("summary") or "Documento comercial generado desde WAOS Smart Docs."
    y = _draw_text_block(c, _wrap_text(summary, 92), 42, y, 92, line_height=13, font="Helvetica", size=9, color=colors.HexColor("#374151")) - 6

    # Customer and metadata cards
    card_y = y
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.setFillColor(colors.HexColor("#F9FAFB"))
    c.roundRect(42, card_y - 72, 245, 64, 10, fill=1, stroke=1)
    c.roundRect(307, card_y - 72, 246, 64, 10, fill=1, stroke=1)
    c.setFillColor(secondary)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(56, card_y - 25, "Cliente")
    c.drawString(321, card_y - 25, "Resumen financiero")
    c.setFont("Helvetica", 9)
    customer_lines = [
        str(document.get("customer_name") or "Cliente por confirmar"),
        str(document.get("customer_phone") or ""),
        str(document.get("customer_email") or ""),
        str(document.get("customer_address") or ""),
    ]
    yy = card_y - 40
    for line in [line for line in customer_lines if line][:3]:
        c.drawString(56, yy, line[:42])
        yy -= 11
    yy = card_y - 40
    financial = [
        f"Subtotal: {_money(document.get('subtotal'), currency)}",
        f"Descuento: {_money(document.get('discount_total'), currency)}",
        f"Impuesto: {_money(document.get('tax_total'), currency)}",
        f"Total: {_money(document.get('total'), currency)}",
    ]
    for line in financial:
        c.drawString(321, yy, line[:42])
        yy -= 11
    y = card_y - 96

    # Items table
    c.setFillColor(primary)
    c.roundRect(42, y - 20, width - 84, 20, 7, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    headers = [("Concepto", 52), ("Cant.", 300), ("Unidad", 340), ("P. unitario", 405), ("Total", 490)]
    for label, x in headers:
        c.drawString(x, y - 13, label)
    y -= 32
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#111827"))
    for item in document.get("items", [])[:18]:
        if y < 165:
            c.showPage()
            y = height - 55
            c.setFillColor(secondary)
            c.setFont("Helvetica-Bold", 13)
            c.drawString(42, y, f"{document.get('folio')} · conceptos")
            y -= 28
            c.setFont("Helvetica", 8)
        name_lines = _wrap_text(str(item.get("name") or "Concepto"), 42)
        desc_lines = _wrap_text(str(item.get("description") or ""), 60)[:2]
        row_h = 16 + max(0, len(name_lines) - 1) * 10 + len([line for line in desc_lines if line]) * 9
        c.setStrokeColor(colors.HexColor("#E5E7EB"))
        c.line(42, y + 6, width - 42, y + 6)
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold", 8)
        yy = y
        for line in name_lines[:2]:
            c.drawString(52, yy, line[:48])
            yy -= 10
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#6B7280"))
        for line in desc_lines:
            if line:
                c.drawString(52, yy, line[:70])
                yy -= 9
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica", 8)
        c.drawRightString(325, y, str(item.get("quantity") or 1))
        c.drawString(340, y, str(item.get("unit") or "unidad")[:12])
        c.drawRightString(465, y, _money(item.get("unit_price"), currency))
        c.drawRightString(width - 52, y, _money(item.get("total"), currency))
        y -= max(26, row_h)

    # Totals panel
    if y < 185:
        c.showPage()
        y = height - 60
    c.setFillColor(colors.HexColor("#F9FAFB"))
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.roundRect(width - 255, y - 86, 213, 75, 10, fill=1, stroke=1)
    c.setFillColor(secondary)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 238, y - 30, "Total")
    c.setFont("Helvetica-Bold", 17)
    c.drawRightString(width - 58, y - 31, _money(document.get("total"), currency))
    c.setFont("Helvetica", 9)
    c.drawString(width - 238, y - 50, "Anticipo")
    c.drawRightString(width - 58, y - 50, _money(document.get("deposit_required"), currency))
    c.drawString(width - 238, y - 66, "Saldo")
    c.drawRightString(width - 58, y - 66, _money(document.get("balance_due"), currency))

    # Terms and next actions
    y -= 110
    c.setFillColor(secondary)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(42, y, "Condiciones y siguiente paso")
    y -= 16
    terms = document.get("terms") or DEFAULT_TERMS.get(document.get("document_type"), DEFAULT_TERMS["quote"])
    y = _draw_text_block(c, _wrap_text(terms, 100), 42, y, 100, line_height=12, font="Helvetica", size=8, color=colors.HexColor("#374151")) - 4
    next_actions = document.get("next_actions") or []
    for action in next_actions[:4]:
        y = _draw_text_block(c, [f"• {action}"], 42, y, 100, line_height=12, font="Helvetica", size=8, color=colors.HexColor("#374151"))

    # Footer
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.line(42, 56, width - 42, 56)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#6B7280"))
    footer = branding.get("footer_note") or "Documento generado por WAOS Smart Docs."
    c.drawString(42, 40, str(footer)[:105])
    c.drawRightString(width - 42, 40, f"Generado por WAOS · {document.get('folio')}")
    c.save()
    return {"pdf_path": str(path), "pdf_filename": filename}


def ensure_commercial_document_pdf(conn, document_or_id: dict | str) -> dict:
    document = _document_with_items(conn, document_or_id) if isinstance(document_or_id, str) else document_or_id
    if not document:
        return {}
    branding = get_organization_branding(conn, document["organization_id"])
    pdf_meta = build_commercial_document_pdf(document, branding)
    now = utcnow_iso()
    execute(
        conn,
        "UPDATE commercial_documents SET pdf_path = ?, pdf_filename = ?, pdf_generated_at = ?, updated_at = ? WHERE id = ?",
        (pdf_meta["pdf_path"], pdf_meta["pdf_filename"], now, now, document["id"]),
    )
    _record_event(conn, organization_id=document["organization_id"], document_id=document["id"], event_type="pdf.generated", metadata={"pdf_filename": pdf_meta["pdf_filename"]})
    refreshed = _document_with_items(conn, document["id"])
    return {**refreshed, **pdf_meta}


def convert_quote_to_work_order(conn, quote_id: str, *, actor_user: dict | None = None) -> dict:
    quote = _document_with_items(conn, quote_id)
    if not quote:
        return {}
    items = [
        {
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "name": item.get("name"),
            "description": item.get("description"),
            "quantity": item.get("quantity"),
            "unit": item.get("unit"),
            "unit_price": item.get("unit_price"),
            "discount": item.get("discount"),
            "tax": item.get("tax"),
            "metadata": {**(item.get("metadata") or {}), "converted_from_item_id": item.get("id")},
        }
        for item in quote.get("items", [])
    ]
    work_order = create_commercial_document(
        conn,
        actor_user=actor_user,
        organization_id=quote["organization_id"],
        bot_id=quote.get("bot_id"),
        conversation_id=quote.get("conversation_id"),
        contact_id=quote.get("contact_id"),
        document_type="work_order",
        status="approved",
        title=f"Orden de trabajo de {quote.get('folio')}",
        customer_name=quote.get("customer_name"),
        customer_phone=quote.get("customer_phone"),
        customer_email=quote.get("customer_email"),
        customer_address=quote.get("customer_address"),
        summary=f"Orden de trabajo generada desde {quote.get('folio')}. Alcance aprobado: {quote.get('summary') or ''}",
        currency=quote.get("currency") or "MXN",
        deposit_required=quote.get("deposit_required") or 0,
        terms=DEFAULT_TERMS["work_order"],
        next_actions=["Asignar responsable o tecnico.", "Confirmar horario con cliente.", "Solicitar evidencia antes/despues y firma de cierre."],
        metadata={"source_quote_id": quote_id, "source_quote_folio": quote.get("folio")},
        items=items,
    )
    update_commercial_document_status(conn, quote_id, status="converted", actor_user=actor_user, metadata={"work_order_id": work_order.get("id")})
    return work_order


def create_catalog_quote_rule(conn, *, actor_user: dict | None = None, **payload: Any) -> dict:
    now = utcnow_iso()
    row_id = new_id("cqr")
    execute(
        conn,
        """
        INSERT INTO catalog_quote_rules (id, organization_id, bot_id, catalog_item_type, catalog_item_id, pricing_model, unit_label, base_price, minimum_quantity, travel_fee, urgency_modifier_percent, deposit_percent, required_questions_json, approval_rules_json, terms, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            payload["organization_id"],
            payload.get("bot_id"),
            payload.get("catalog_item_type"),
            payload.get("catalog_item_id"),
            payload.get("pricing_model") or "fixed",
            payload.get("unit_label") or "unidad",
            payload.get("base_price"),
            float(payload.get("minimum_quantity") or 1),
            float(payload.get("travel_fee") or 0),
            float(payload.get("urgency_modifier_percent") or 0),
            float(payload.get("deposit_percent") or 0),
            to_json(payload.get("required_questions") or []),
            to_json(payload.get("approval_rules") or {}),
            payload.get("terms"),
            1 if payload.get("is_active", True) else 0,
            now,
            now,
        ),
    )
    if actor_user:
        create_audit_log(conn, organization_id=payload["organization_id"], actor_user_id=actor_user.get("id"), actor_type="user", entity_type="catalog_quote_rule", entity_id=row_id, action="catalog.quote_rule_created", metadata={"catalog_item_type": payload.get("catalog_item_type"), "catalog_item_id": payload.get("catalog_item_id"), "pricing_model": payload.get("pricing_model")})
    return parse_catalog_quote_rule(fetch_one(conn, "SELECT * FROM catalog_quote_rules WHERE id = ?", (row_id,)))


def parse_catalog_quote_rule(row: dict | None) -> dict:
    if not row:
        return {}
    parsed = dict(row)
    parsed["required_questions"] = from_json(parsed.get("required_questions_json"), [])
    parsed["approval_rules"] = from_json(parsed.get("approval_rules_json"), {})
    return parsed


def list_catalog_quote_rules(conn, organization_id: str, *, bot_id: str | None = None, catalog_item_type: str | None = None, catalog_item_id: str | None = None) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM catalog_quote_rules WHERE organization_id = ?"
    if bot_id:
        sql += " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    if catalog_item_type:
        sql += " AND catalog_item_type = ?"
        params.append(catalog_item_type)
    if catalog_item_id:
        sql += " AND catalog_item_id = ?"
        params.append(catalog_item_id)
    sql += " ORDER BY updated_at DESC"
    return [parse_catalog_quote_rule(row) for row in fetch_all(conn, sql, params)]
