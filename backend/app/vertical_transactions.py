from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from .utils import from_json, new_id, to_json, utcnow_iso
from .verticals import get_vertical_profile


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vertical_transaction_accounts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    contact_id TEXT,
    vertical_id TEXT NOT NULL,
    aggregate_root TEXT NOT NULL,
    main_business_entity TEXT NOT NULL,
    transaction_unit TEXT NOT NULL,
    external_reference TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    commercial_status TEXT,
    operations_status TEXT,
    finance_status TEXT,
    continuity_status TEXT,
    last_command TEXT,
    last_event TEXT,
    quote_status TEXT,
    booking_status TEXT,
    execution_status TEXT,
    payment_status TEXT,
    continuity_plan_status TEXT,
    amount_expected REAL NOT NULL DEFAULT 0,
    amount_collected REAL NOT NULL DEFAULT 0,
    amount_outstanding REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'MXN',
    profile_json TEXT NOT NULL DEFAULT '{}',
    state_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    UNIQUE(organization_id, vertical_id, external_reference)
);
CREATE INDEX IF NOT EXISTS idx_vtx_accounts_org ON vertical_transaction_accounts(organization_id, vertical_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_vtx_accounts_bot ON vertical_transaction_accounts(bot_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_commands (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    command_name TEXT NOT NULL,
    command_key TEXT NOT NULL,
    actor_user_id TEXT,
    actor_type TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    processed_at TEXT,
    UNIQUE(organization_id, account_id, command_key),
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_commands_account ON vertical_transaction_commands(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    event_name TEXT NOT NULL,
    command_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id),
    FOREIGN KEY (command_id) REFERENCES vertical_transaction_commands(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_events_account ON vertical_transaction_events(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_ledger (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'MXN',
    reference_type TEXT,
    reference_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_ledger_account ON vertical_transaction_ledger(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_documents (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    document_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    signed_at TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, document_name),
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_docs_account ON vertical_transaction_documents(account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_resources (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_reference TEXT,
    status TEXT NOT NULL DEFAULT 'reserved',
    starts_at TEXT,
    ends_at TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_resources_account ON vertical_transaction_resources(account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS vertical_transaction_views (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    view_name TEXT NOT NULL,
    summary TEXT,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    payload_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, view_name),
    FOREIGN KEY (account_id) REFERENCES vertical_transaction_accounts(id)
);
CREATE INDEX IF NOT EXISTS idx_vtx_views_account ON vertical_transaction_views(account_id, updated_at DESC);
"""


@dataclass
class VerticalTransactionDefinition:
    profile: dict[str, Any]
    command_to_event: dict[str, str]
    view_names: list[str]




def _db():
    from .db import execute, fetch_all, fetch_one
    return execute, fetch_all, fetch_one


def _audit(conn: Any, **kwargs: Any) -> None:
    from .repositories.audit import create_audit_log
    create_audit_log(conn, **kwargs)

MONEY_COMMANDS = {
    "create_quote": "expected",
    "request_deposit": "expected",
    "approve_quote": "expected",
    "collect_payment": "collected",
    "issue_refund": "refund",
    "sell_session_package": "expected",
    "schedule_maintenance": "expected",
    "propose_fee": "expected",
    "capture_order": "expected",
    "collect_order_payment": "collected",
}
RESOURCE_COMMANDS = {"reserve_capacity", "confirm_booking", "assign_technician", "assign_specialist", "schedule_service_window"}
DOCUMENT_COMMANDS = {"start_case", "start_matter", "start_admission", "mark_eligibility", "qualify_record", "intake_case"}
CLOSING_COMMANDS = {"close_fulfillment", "deliver_aftercare", "mark_delivery_complete", "close_matter", "close_job"}
CONTINUITY_COMMANDS = {"schedule_recurrence", "schedule_maintenance", "reactivate_customer", "enroll_membership", "activate_plan"}


def ensure_vertical_transaction_schema(conn: Any) -> None:
    conn.executescript(SCHEMA_SQL)




def _first_integration(conn: Any, *, organization_id: str, bot_id: str | None, integration_type: str, providers: tuple[str, ...]) -> dict[str, Any] | None:
    _, _, fetch_one = _db()
    if bot_id:
        row = fetch_one(
            conn,
            f"""
            SELECT * FROM integration_connections
            WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '')
              AND integration_type = ? AND provider IN ({','.join(['?'] * len(providers))})
              AND status IN ('active', 'configured')
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (organization_id, bot_id, integration_type, *providers),
        )
        if row:
            return row
    return fetch_one(
        conn,
        f"""
        SELECT * FROM integration_connections
        WHERE organization_id = ? AND bot_id IS NULL
          AND integration_type = ? AND provider IN ({','.join(['?'] * len(providers))})
          AND status IN ('active', 'configured')
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (organization_id, integration_type, *providers),
    )


def _upsert_account_metadata(conn: Any, account_id: str, metadata: dict[str, Any]) -> None:
    execute, _, _ = _db()
    execute(conn, "UPDATE vertical_transaction_accounts SET metadata_json = ?, updated_at = ? WHERE id = ?", (to_json(metadata), utcnow_iso(), account_id))


def _sync_payment_back_to_account(conn: Any, *, account_id: str, payment: dict[str, Any]) -> None:
    execute, _, fetch_one = _db()
    row = fetch_one(conn, "SELECT * FROM vertical_transaction_accounts WHERE id = ?", (account_id,))
    if not row:
        return
    account = _parse_account(row)
    amount = float(payment.get("amount") or 0)
    payment_status = str(payment.get("status") or "pending")
    amount_collected = float(account.get("amount_collected") or 0)
    amount_expected = max(float(account.get("amount_expected") or 0), amount)
    if payment_status == 'paid':
        exists = fetch_one(conn, "SELECT id FROM vertical_transaction_ledger WHERE account_id = ? AND reference_type = 'commerce_payment' AND reference_id = ? AND entry_type = 'collected'", (account_id, payment['id']))
        if not exists:
            execute(conn, "INSERT INTO vertical_transaction_ledger (id, organization_id, account_id, vertical_id, entry_type, amount, currency, reference_type, reference_id, payload_json, created_at) VALUES (?, ?, ?, ?, 'collected', ?, ?, 'commerce_payment', ?, ?, ?)", (new_id('vled'), account['organization_id'], account_id, account['vertical_id'], amount, payment.get('currency') or account.get('currency') or 'MXN', payment['id'], to_json({'provider': payment.get('provider'), 'payment_status': payment_status}), utcnow_iso()))
        amount_collected = max(amount_collected, amount)
    amount_outstanding = max(amount_expected - amount_collected, 0)
    finance_status = 'paid' if payment_status == 'paid' else ('pending' if amount_expected > 0 else account.get('finance_status'))
    execute(conn, "UPDATE vertical_transaction_accounts SET payment_status = ?, finance_status = ?, amount_expected = ?, amount_collected = ?, amount_outstanding = ?, updated_at = ? WHERE id = ?", (payment_status, finance_status, amount_expected, amount_collected, amount_outstanding, utcnow_iso(), account_id))
    definition = _transaction_definition(account['vertical_id'])
    _refresh_views(conn, account_id, definition)


def sync_account_payment_status(conn: Any, *, account_id: str, payment_id: str) -> None:
    _, _, fetch_one = _db()
    payment = fetch_one(conn, "SELECT * FROM commerce_payments WHERE id = ?", (payment_id,))
    if payment:
        _sync_payment_back_to_account(conn, account_id=account_id, payment=payment)


def _maybe_create_checkout(conn: Any, *, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if command_name not in {"create_quote", "request_deposit", "capture_order", "sell_session_package", "propose_fee"}:
        return None
    if not account.get('bot_id') or not account.get('contact_id'):
        return None
    from .domains.payments import create_payment_request
    amount = float(payload.get('amount') or payload.get('price') or payload.get('quote_total') or 0)
    if amount <= 0:
        return None
    metadata = dict(payload.get('payment_metadata') or {})
    metadata.update({
        'vertical_transaction_account_id': account['id'],
        'vertical_id': account['vertical_id'],
        'command_name': command_name,
    })
    conversation_id = payload.get('conversation_id') or account.get('metadata', {}).get('conversation_id')
    if not conversation_id:
        conversation_id = f"vtx-{account['id']}"
    payment = create_payment_request(
        conn,
        organization_id=account['organization_id'],
        bot_id=account['bot_id'],
        conversation_id=conversation_id,
        contact_id=account['contact_id'],
        title=str(payload.get('title') or f"{account['vertical_id']} {command_name}"),
        amount=amount,
        currency=str(payload.get('currency') or account.get('currency') or 'MXN'),
        reminder_minutes=int(payload.get('reminder_minutes') or 60),
        metadata=metadata,
    )
    merged = dict(account.get('metadata') or {})
    merged.setdefault('payment_ids', []).append(payment['id'])
    merged['last_payment_id'] = payment['id']
    _upsert_account_metadata(conn, account['id'], merged)
    _sync_payment_back_to_account(conn, account_id=account['id'], payment=payment)
    return payment


def _maybe_create_appointment(conn: Any, *, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if command_name not in {"reserve_capacity", "confirm_booking", "schedule_service_window"}:
        return None
    if not account.get('bot_id'):
        return None
    from .domains.appointments import create_appointment_bundle, confirm_appointment
    scheduled_for = str(payload.get('scheduled_for') or payload.get('starts_at') or utcnow_iso())
    duration = int(payload.get('duration_minutes') or 60)
    timezone = str(payload.get('timezone') or 'America/Mexico_City')
    appointment = create_appointment_bundle(
        conn,
        organization_id=account['organization_id'],
        bot_id=account['bot_id'],
        scheduled_for=scheduled_for,
        duration_minutes=duration,
        timezone=timezone,
        notes=str(payload.get('notes') or f"{account['vertical_id']} {command_name}"),
        conversation_id=payload.get('conversation_id') or account.get('metadata', {}).get('conversation_id'),
        contact_id=account.get('contact_id'),
        status='confirmed' if command_name == 'confirm_booking' else 'scheduled',
    )
    if command_name == 'confirm_booking':
        appointment = confirm_appointment(conn, appointment['id'])
    integration = _first_integration(conn, organization_id=account['organization_id'], bot_id=account.get('bot_id'), integration_type='calendar', providers=('google_calendar',))
    if integration and str(integration.get('credential_status') or '').strip() in {'connected', 'configured'}:
        try:
            from .integrations_runtime import sync_google_calendar
            sync_google_calendar(conn, integration)
        except Exception:
            pass
    merged = dict(account.get('metadata') or {})
    merged.setdefault('appointment_ids', []).append(appointment['id'])
    merged['last_appointment_id'] = appointment['id']
    _upsert_account_metadata(conn, account['id'], merged)
    return appointment


def _apply_side_effects(conn: Any, *, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    effects: dict[str, Any] = {}
    payment = _maybe_create_checkout(conn, account=account, command_name=command_name, payload=payload)
    if payment:
        effects['payment'] = {
            'id': payment['id'],
            'status': payment.get('status'),
            'payment_link_url': payment.get('payment_link_url'),
            'provider': payment.get('provider'),
        }
    appointment = _maybe_create_appointment(conn, account=account, command_name=command_name, payload=payload)
    if appointment:
        effects['appointment'] = {
            'id': appointment['id'],
            'status': appointment.get('status'),
            'scheduled_for': appointment.get('scheduled_for'),
            'provider': appointment.get('provider'),
            'external_id': appointment.get('external_id'),
        }
    return effects

def _transaction_definition(vertical_id: str) -> VerticalTransactionDefinition:
    profile = get_vertical_profile(vertical_id)
    motor = profile.get("transactional_motor_v12", {})
    command_catalog = motor.get("command_catalog") or []
    command_to_event: dict[str, str] = {}
    for item in command_catalog:
        command = str(item.get("command") or "").strip()
        event = str(item.get("emits") or "").strip()
        if command and event:
            command_to_event[command] = event
    view_names = list((motor.get("transaction_views") or {}).keys()) or ["commercial", "operations", "finance", "continuity"]
    return VerticalTransactionDefinition(profile=profile, command_to_event=command_to_event, view_names=view_names)


def _allowed_commands(definition: VerticalTransactionDefinition) -> set[str]:
    command_catalog = definition.profile.get("transactional_motor_v12", {}).get("command_catalog") or []
    names = {str(item.get("command") or "").strip() for item in command_catalog if item.get("command")}
    if not names:
        names = set(definition.command_to_event)
    return {item for item in names if item}


def _parse_account(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    row["profile"] = from_json(row.get("profile_json"), {})
    row["state"] = from_json(row.get("state_json"), {})
    row["metadata"] = from_json(row.get("metadata_json"), {})
    return row


def _parse_payload_rows(rows: list[dict[str, Any]], field: str = "payload_json") -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = from_json(item.get(field), {})
        if "result_json" in item:
            item["result"] = from_json(item.get("result_json"), {})
        if "metrics_json" in item:
            item["metrics"] = from_json(item.get("metrics_json"), {})
        parsed.append(item)
    return parsed


def _guard_message(profile: dict[str, Any], command_name: str) -> str | None:
    for item in profile.get("transactional_motor_v12", {}).get("command_catalog") or []:
        if str(item.get("command")) == command_name:
            return str(item.get("guard") or "").strip() or None
    return None


def _event_name(definition: VerticalTransactionDefinition, command_name: str) -> str:
    if command_name in definition.command_to_event:
        return definition.command_to_event[command_name]
    normalized = command_name.strip().lower().replace(" ", "_")
    if normalized.startswith("handle_"):
        normalized = normalized[7:]
    return f"{normalized}_applied"


def _infer_status_axes(command_name: str, event_name: str) -> dict[str, str | None]:
    commercial = None
    operations = None
    finance = None
    continuity = None
    if command_name in {"capture_intent", "intake_case"}:
        commercial = "intake"
    elif command_name in {"qualify_record", "mark_eligibility"}:
        commercial = "qualified"
    elif command_name in {"create_quote", "sell_session_package", "propose_fee", "capture_order"}:
        commercial = "quoted"
    elif command_name in {"approve_quote", "confirm_booking"}:
        commercial = "committed"
    elif event_name in {"payment_collected", "package_sold", "order_paid"}:
        commercial = "won"

    if command_name in {"reserve_capacity", "confirm_booking", "assign_technician", "assign_specialist", "schedule_service_window"}:
        operations = "scheduled"
    elif command_name in {"start_case", "start_fulfillment", "start_matter", "start_admission"}:
        operations = "in_progress"
    elif command_name in CLOSING_COMMANDS:
        operations = "completed"

    if command_name in {"create_quote", "request_deposit", "sell_session_package", "schedule_maintenance", "propose_fee", "capture_order"}:
        finance = "awaiting_payment"
    elif command_name in {"collect_payment", "collect_order_payment"}:
        finance = "paid"
    elif command_name == "issue_refund":
        finance = "refunded"

    if command_name in CONTINUITY_COMMANDS:
        continuity = "active"
    elif command_name in CLOSING_COMMANDS:
        continuity = "ready_for_followup"
    return {
        "commercial_status": commercial,
        "operations_status": operations,
        "finance_status": finance,
        "continuity_status": continuity,
    }


def _upsert_document_requirements(conn: Any, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> None:
    execute, _, _ = _db()
    documents = payload.get("documents") or []
    now = utcnow_iso()
    if command_name in DOCUMENT_COMMANDS and not documents:
        profile = get_vertical_profile(account["vertical_id"])
        documents = (profile.get("vertical_runtime", {}).get("document_flow", {}).get("required_documents") or [])[:2]
    for item in documents:
        name = item if isinstance(item, str) else str(item.get("name") or item.get("document") or "document")
        status = "signed" if (isinstance(item, dict) and item.get("signed")) else str(item.get("status") or "pending") if isinstance(item, dict) else "pending"
        signed_at = now if status == "signed" else None
        execute(
            conn,
            """
            INSERT INTO vertical_transaction_documents (id, organization_id, account_id, vertical_id, document_name, status, signed_at, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, document_name) DO UPDATE SET status = excluded.status, signed_at = excluded.signed_at, payload_json = excluded.payload_json, updated_at = excluded.updated_at
            """,
            (
                new_id("vdoc"),
                account["organization_id"],
                account["id"],
                account["vertical_id"],
                name,
                status,
                signed_at,
                to_json(item if isinstance(item, dict) else {"name": name}),
                now,
                now,
            ),
        )


def _record_resource(conn: Any, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> None:
    execute, _, _ = _db()
    if command_name not in RESOURCE_COMMANDS:
        return
    now = utcnow_iso()
    resource_type = str(payload.get("resource_type") or payload.get("resource") or "primary_resource")
    reference = str(payload.get("resource_reference") or payload.get("slot") or payload.get("owner") or new_id("slot"))
    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    status = "confirmed" if command_name == "confirm_booking" else "reserved"
    execute(
        conn,
        """
        INSERT INTO vertical_transaction_resources (id, organization_id, account_id, vertical_id, resource_type, resource_reference, status, starts_at, ends_at, payload_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("vres"),
            account["organization_id"],
            account["id"],
            account["vertical_id"],
            resource_type,
            reference,
            status,
            starts_at,
            ends_at,
            to_json(payload),
            now,
            now,
        ),
    )


def _record_money(conn: Any, account: dict[str, Any], command_name: str, event_name: str, payload: dict[str, Any], command_id: str) -> tuple[float, float, float]:
    execute, _, _ = _db()
    kind = MONEY_COMMANDS.get(command_name)
    if not kind:
        return (0.0, 0.0, 0.0)
    amount = float(payload.get("amount") or payload.get("quote_amount") or payload.get("deposit_amount") or 0)
    if amount <= 0 and kind in {"expected", "collected"}:
        amount = 1000.0
    delta_expected = 0.0
    delta_collected = 0.0
    if kind == "expected":
        entry_type = "charge_opened"
        delta_expected = amount
    elif kind == "collected":
        entry_type = "payment_applied"
        delta_collected = amount
    else:
        entry_type = "refund_issued"
        delta_collected = -abs(amount or 250.0)
    execute(
        conn,
        """
        INSERT INTO vertical_transaction_ledger (id, organization_id, account_id, vertical_id, entry_type, amount, currency, reference_type, reference_id, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("vled"),
            account["organization_id"],
            account["id"],
            account["vertical_id"],
            entry_type,
            amount if delta_collected >= 0 else abs(delta_collected),
            str(payload.get("currency") or account.get("currency") or "MXN"),
            "command",
            command_id,
            to_json({"command": command_name, "event": event_name, **payload}),
            utcnow_iso(),
        ),
    )
    outstanding = max((account.get("amount_outstanding") or 0) + delta_expected - delta_collected, 0)
    return (delta_expected, delta_collected, outstanding)


def _refresh_views(conn: Any, account_id: str, definition: VerticalTransactionDefinition) -> list[dict[str, Any]]:
    execute, fetch_all, fetch_one = _db()
    account_row = fetch_one(conn, "SELECT * FROM vertical_transaction_accounts WHERE id = ?", (account_id,))
    if not account_row:
        return []
    account = _parse_account(account_row)
    events = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_events WHERE account_id = ? ORDER BY created_at ASC", (account_id,)))
    docs = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_documents WHERE account_id = ? ORDER BY updated_at DESC", (account_id,)))
    resources = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_resources WHERE account_id = ? ORDER BY updated_at DESC", (account_id,)))
    views: list[dict[str, Any]] = []
    now = utcnow_iso()
    for view_name in definition.view_names:
        metrics = {
            "events": len(events),
            "documents_ready": sum(1 for item in docs if item.get("status") == "signed"),
            "documents_total": len(docs),
            "resources_reserved": len(resources),
            "amount_expected": float(account.get("amount_expected") or 0),
            "amount_collected": float(account.get("amount_collected") or 0),
            "amount_outstanding": float(account.get("amount_outstanding") or 0),
        }
        payload = {
            "account": {
                "id": account["id"],
                "vertical_id": account["vertical_id"],
                "last_event": account.get("last_event"),
                "commercial_status": account.get("commercial_status"),
                "operations_status": account.get("operations_status"),
                "finance_status": account.get("finance_status"),
                "continuity_status": account.get("continuity_status"),
            },
            "latest_events": [item.get("event_name") for item in events[-5:]],
            "documents": [{"name": item.get("document_name"), "status": item.get("status")} for item in docs[:5]],
            "resources": [{"type": item.get("resource_type"), "status": item.get("status")} for item in resources[:5]],
        }
        summary = f"{view_name}: {account.get('last_event') or account.get('last_command') or 'new'}"
        execute(
            conn,
            """
            INSERT INTO vertical_transaction_views (id, organization_id, account_id, vertical_id, view_name, summary, metrics_json, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, view_name) DO UPDATE SET summary = excluded.summary, metrics_json = excluded.metrics_json, payload_json = excluded.payload_json, updated_at = excluded.updated_at
            """,
            (
                new_id("vview"),
                account["organization_id"],
                account["id"],
                account["vertical_id"],
                view_name,
                summary,
                to_json(metrics),
                to_json(payload),
                now,
            ),
        )
        views.append({"view_name": view_name, "summary": summary, "metrics": metrics, "payload": payload, "updated_at": now})
    return views


class VerticalTransactionService:
    def create_account(
        self,
        conn: Any,
        *,
        organization_id: str,
        vertical_id: str,
        actor_user: dict | None,
        bot_id: str | None = None,
        contact_id: str | None = None,
        external_reference: str | None = None,
        metadata: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        execute, _, _ = _db()
        definition = _transaction_definition(vertical_id)
        motor = definition.profile.get("transactional_motor_v12", {})
        now = utcnow_iso()
        account_id = new_id("vtx")
        execute(
            conn,
            """
            INSERT INTO vertical_transaction_accounts (
                id, organization_id, bot_id, contact_id, vertical_id, aggregate_root, main_business_entity, transaction_unit,
                external_reference, status, commercial_status, operations_status, finance_status, continuity_status,
                profile_json, state_json, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', 'intake', 'queued', 'pending', 'not_started', ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                organization_id,
                bot_id,
                contact_id,
                vertical_id,
                str(motor.get("aggregate_root") or vertical_id),
                str(motor.get("main_business_entity") or "record"),
                str(motor.get("transaction_unit") or "transaction"),
                external_reference,
                to_json(definition.profile),
                to_json(state or {}),
                to_json(metadata or {}),
                now,
                now,
            ),
        )
        account = self.get_account(conn, organization_id=organization_id, account_id=account_id)
        from .vertical_domain_runtime import bootstrap_vertical_domain
        bootstrap_vertical_domain(conn, account)
        if actor_user:
            _audit(
                conn,
                organization_id=organization_id,
                actor_user_id=actor_user.get("id"),
                actor_type="user",
                entity_type="vertical_transaction_account",
                entity_id=account_id,
                action="vertical_transaction.account_created",
                metadata={"vertical_id": vertical_id, "external_reference": external_reference},
            )
        return self.get_account(conn, organization_id=organization_id, account_id=account_id)

    def get_account(self, conn: Any, *, organization_id: str, account_id: str) -> dict[str, Any]:
        _, fetch_all, fetch_one = _db()
        row = fetch_one(conn, "SELECT * FROM vertical_transaction_accounts WHERE id = ? AND organization_id = ?", (account_id, organization_id))
        if not row:
            raise HTTPException(status_code=404, detail="Transaction account not found")
        account = _parse_account(row)
        account["timeline"] = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_events WHERE account_id = ? ORDER BY created_at ASC", (account_id,)))
        account["commands"] = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_commands WHERE account_id = ? ORDER BY created_at ASC", (account_id,)))
        account["ledger"] = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_ledger WHERE account_id = ? ORDER BY created_at ASC", (account_id,)))
        account["documents"] = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_documents WHERE account_id = ? ORDER BY updated_at DESC", (account_id,)))
        account["resources"] = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_resources WHERE account_id = ? ORDER BY updated_at DESC", (account_id,)))
        account["views"] = _parse_payload_rows(fetch_all(conn, "SELECT * FROM vertical_transaction_views WHERE account_id = ? ORDER BY view_name ASC", (account_id,)), field="payload_json")
        from .vertical_domain_runtime import bootstrap_vertical_domain, get_vertical_domain_snapshot
        bootstrap_vertical_domain(conn, account)
        account["domain_snapshot"] = get_vertical_domain_snapshot(conn, organization_id=organization_id, account_id=account_id, vertical_id=account["vertical_id"])
        return account

    def dispatch_command(
        self,
        conn: Any,
        *,
        organization_id: str,
        account_id: str,
        command_name: str,
        payload: dict[str, Any] | None,
        actor_user: dict,
    ) -> dict[str, Any]:
        execute, _, fetch_one = _db()
        account = self.get_account(conn, organization_id=organization_id, account_id=account_id)
        definition = _transaction_definition(account["vertical_id"])
        if command_name not in _allowed_commands(definition):
            raise HTTPException(status_code=400, detail=f"Unsupported command for {account['vertical_id']}: {command_name}")
        payload = dict(payload or {})
        command_key = str(payload.get("idempotency_key") or new_id("cmdkey"))
        existing = fetch_one(
            conn,
            "SELECT * FROM vertical_transaction_commands WHERE organization_id = ? AND account_id = ? AND command_key = ?",
            (organization_id, account_id, command_key),
        )
        if existing:
            return {"ok": True, "idempotent": True, "command": _parse_payload_rows([existing])[0], "account": self.get_account(conn, organization_id=organization_id, account_id=account_id)}

        event_name = _event_name(definition, command_name)
        now = utcnow_iso()
        command_id = new_id("vcmd")
        guard = _guard_message(definition.profile, command_name)
        execute(
            conn,
            """
            INSERT INTO vertical_transaction_commands (id, organization_id, account_id, vertical_id, command_name, command_key, actor_user_id, actor_type, status, payload_json, result_json, created_at, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'user', 'applied', ?, ?, ?, ?)
            """,
            (command_id, organization_id, account_id, account["vertical_id"], command_name, command_key, actor_user.get("id"), to_json(payload), to_json({"event": event_name, "guard": guard}), now, now),
        )
        side_effects = _apply_side_effects(conn, account=account, command_name=command_name, payload=payload)
        if side_effects:
            execute(conn, "UPDATE vertical_transaction_commands SET result_json = ? WHERE id = ?", (to_json({"event": event_name, "guard": guard, "side_effects": side_effects}), command_id))
        event_id = new_id("vevt")
        execute(
            conn,
            """
            INSERT INTO vertical_transaction_events (id, organization_id, account_id, vertical_id, event_name, command_id, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, organization_id, account_id, account["vertical_id"], event_name, command_id, to_json(payload), now),
        )
        _upsert_document_requirements(conn, account, command_name, payload)
        _record_resource(conn, account, command_name, payload)
        from .vertical_domain_runtime import apply_vertical_domain_command
        apply_vertical_domain_command(conn, account, command_name, payload)
        delta_expected, delta_collected, outstanding = _record_money(conn, account, command_name, event_name, payload, command_id)
        axes = _infer_status_axes(command_name, event_name)
        state = dict(account.get("state") or {})
        state.update({
            "last_command_payload": payload,
            "last_guard": guard,
            "command_count": int(state.get("command_count") or 0) + 1,
            "last_event_at": now,
        })
        quote_status = account.get("quote_status")
        booking_status = account.get("booking_status")
        execution_status = account.get("execution_status")
        payment_status = account.get("payment_status")
        continuity_plan_status = account.get("continuity_plan_status")
        if command_name in {"create_quote", "propose_fee", "capture_order", "sell_session_package"}:
            quote_status = "sent"
        if command_name in {"approve_quote"}:
            quote_status = "accepted"
        if command_name in {"reserve_capacity"}:
            booking_status = "reserved"
        if command_name in {"confirm_booking"}:
            booking_status = "confirmed"
        if command_name in {"start_case", "start_fulfillment", "start_matter", "start_admission"}:
            execution_status = "in_progress"
        if command_name in CLOSING_COMMANDS:
            execution_status = "completed"
        if command_name in {"collect_payment", "collect_order_payment"}:
            payment_status = "paid"
        elif command_name in {"request_deposit", "create_quote", "propose_fee", "capture_order"}:
            payment_status = "pending"
        elif command_name == "issue_refund":
            payment_status = "refunded"
        if command_name in CONTINUITY_COMMANDS:
            continuity_plan_status = "active"
        elif command_name in CLOSING_COMMANDS:
            continuity_plan_status = continuity_plan_status or "ready"
        updated_expected = float(account.get("amount_expected") or 0) + delta_expected
        updated_collected = float(account.get("amount_collected") or 0) + delta_collected
        updated_outstanding = max(updated_expected - max(updated_collected, 0), 0)
        status = "closed" if command_name in CLOSING_COMMANDS and updated_outstanding <= 0 else "open"
        execute(
            conn,
            """
            UPDATE vertical_transaction_accounts
            SET updated_at = ?, status = ?, last_command = ?, last_event = ?,
                commercial_status = COALESCE(?, commercial_status),
                operations_status = COALESCE(?, operations_status),
                finance_status = COALESCE(?, finance_status),
                continuity_status = COALESCE(?, continuity_status),
                quote_status = ?, booking_status = ?, execution_status = ?, payment_status = ?, continuity_plan_status = ?,
                amount_expected = ?, amount_collected = ?, amount_outstanding = ?, state_json = ?, closed_at = CASE WHEN ? = 'closed' THEN ? ELSE closed_at END
            WHERE id = ?
            """,
            (
                now,
                status,
                command_name,
                event_name,
                axes.get("commercial_status"),
                axes.get("operations_status"),
                axes.get("finance_status"),
                axes.get("continuity_status"),
                quote_status,
                booking_status,
                execution_status,
                payment_status,
                continuity_plan_status,
                updated_expected,
                updated_collected,
                updated_outstanding,
                to_json(state),
                status,
                now,
                account_id,
            ),
        )
        _refresh_views(conn, account_id, definition)
        _audit(
            conn,
            organization_id=organization_id,
            actor_user_id=actor_user.get("id"),
            actor_type="user",
            entity_type="vertical_transaction_account",
            entity_id=account_id,
            action="vertical_transaction.command_applied",
            metadata={"command": command_name, "event": event_name, "guard": guard, "vertical_id": account["vertical_id"]},
        )
        return {"ok": True, "idempotent": False, "command_id": command_id, "event_id": event_id, "account": self.get_account(conn, organization_id=organization_id, account_id=account_id)}

    def execute_playbook(self, conn: DBConnection, *, organization_id: str, account_id: str, actor_user: dict) -> dict[str, Any]:
        account = self.get_account(conn, organization_id=organization_id, account_id=account_id)
        definition = _transaction_definition(account["vertical_id"])
        command_catalog = definition.profile.get("transactional_motor_v12", {}).get("command_catalog") or []
        commands = [str(item.get("command") or "").strip() for item in command_catalog if item.get("command")]
        if not commands:
            raise HTTPException(status_code=400, detail="No transactional playbook available")
        executed: list[dict[str, Any]] = []
        for index, command_name in enumerate(commands, start=1):
            payload = {
                "idempotency_key": f"playbook-{index}",
                "amount": 1000 * index if command_name in MONEY_COMMANDS else 0,
                "resource_type": f"resource_{index}",
                "resource_reference": f"slot_{index}",
                "documents": [{"name": f"doc_{index}", "status": "signed"}] if command_name in DOCUMENT_COMMANDS else [],
            }
            result = self.dispatch_command(
                conn,
                organization_id=organization_id,
                account_id=account_id,
                command_name=command_name,
                payload=payload,
                actor_user=actor_user,
            )
            executed.append({"command": command_name, "last_event": result["account"].get("last_event")})
        final_account = self.get_account(conn, organization_id=organization_id, account_id=account_id)
        return {"ok": True, "vertical_id": account["vertical_id"], "commands_executed": executed, "account": final_account}


vertical_transaction_service = VerticalTransactionService()
