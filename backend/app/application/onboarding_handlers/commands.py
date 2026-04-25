from __future__ import annotations

from fastapi import HTTPException

from app.config import settings

from ...contracts import ok
from ...db import execute, table_exists
from ...repositories import create_audit_log
from ...security import ensure_org_access
from ...utils import new_id, to_json, utcnow_iso
from ...vertical_onboarding_ai_prefill import apply_ai_autofix_to_wizard, generate_ai_wizard_autopilot, generate_ai_wizard_prefill
from ...vertical_onboarding_runtime import (
    apply_guided_onboarding_wizard,
    dry_run_guided_onboarding_wizard,
    reconcile_guided_onboarding_wizard_integrity,
    start_guided_onboarding_wizard,
    update_guided_onboarding_step,
)
from ..support import require_permission
from ..uow import UnitOfWork


def start_wizard(service, uow: UnitOfWork, *, payload, user: dict) -> dict:
    org, bot = service._resolve_scope(uow, user=user, organization_id=payload.organization_id, bot_id=payload.bot_id)
    require_permission(user, org["id"], "activation.manage")
    wizard = start_guided_onboarding_wizard(
        uow.conn,
        organization_id=org["id"],
        bot_id=(bot or {}).get("id"),
        actor_user_id=user.get("id"),
        vertical_id=payload.vertical_id or ((bot or {}).get("vertical")) or org.get("vertical"),
        subvertical=payload.subvertical,
        business_name=payload.business_name or ((bot or {}).get("business_name")) or org.get("name") or "",
        bot_name=payload.bot_name or ((bot or {}).get("name")) or "",
        tone=payload.tone or "",
        language=payload.language or (((bot or {}).get("language")) or "es"),
        timezone=payload.timezone or (((bot or {}).get("timezone")) or org.get("timezone") or "America/Mexico_City"),
        primary_objective=payload.primary_objective or "agendar",
        hours=payload.hours or "",
        whatsapp_number=payload.whatsapp_number or "",
        answers=payload.answers,
    )
    uow.commit()
    return ok(wizard)


def ai_prefill_wizard(service, uow: UnitOfWork, *, payload, user: dict) -> dict:
    org, bot = service._resolve_scope(uow, user=user, organization_id=payload.organization_id, bot_id=payload.bot_id)
    require_permission(user, org["id"], "activation.manage")
    result = generate_ai_wizard_prefill(
        uow.conn,
        organization_id=org["id"],
        bot_id=(bot or {}).get("id"),
        vertical_id=payload.vertical_id or ((bot or {}).get("vertical")) or org.get("vertical"),
        subvertical=payload.subvertical,
        primary_objective=payload.primary_objective,
        user_description=payload.user_description,
        existing_answers=payload.existing_answers,
        intensity=payload.intensity,
    )
    return ok(result)


def ai_autofix_wizard(service, uow: UnitOfWork, *, wizard_id: str, payload, user: dict) -> dict:
    service._get_accessible_wizard(uow.conn, wizard_id=wizard_id, user=user, permission="activation.manage")
    try:
        result = apply_ai_autofix_to_wizard(
            uow.conn,
            wizard_id=wizard_id,
            user_description=getattr(payload, "user_description", ""),
            max_rounds=int(getattr(payload, "max_rounds", 3) or 3),
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "wizard_not_found":
            raise HTTPException(status_code=404, detail="Wizard not found")
        if detail == "wizard_revision_conflict":
            raise HTTPException(status_code=409, detail="wizard_revision_conflict")
        raise HTTPException(status_code=400, detail=detail)
    uow.commit()
    return ok(result)


def ai_autopilot_wizard(service, uow: UnitOfWork, *, payload, user: dict) -> dict:
    org, bot = service._resolve_scope(uow, user=user, organization_id=payload.organization_id, bot_id=payload.bot_id)
    require_permission(user, org["id"], "activation.manage")
    try:
        result = generate_ai_wizard_autopilot(
            uow.conn,
            organization_id=org["id"],
            bot_id=(bot or {}).get("id"),
            vertical_id=payload.vertical_id or ((bot or {}).get("vertical")) or org.get("vertical"),
            subvertical=payload.subvertical,
            primary_objective=payload.primary_objective,
            user_description=payload.user_description,
            existing_answers=payload.existing_answers,
            intensity=payload.intensity,
            max_autofix_rounds=max(1, min(int(payload.max_autofix_rounds or settings.autopilot_max_autofix_rounds), settings.autopilot_max_autofix_rounds)),
            auto_apply=bool(payload.auto_apply),
            actor_user=user,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "wizard_not_found":
            raise HTTPException(status_code=404, detail="Wizard not found")
        if detail == "wizard_revision_conflict":
            raise HTTPException(status_code=409, detail="wizard_revision_conflict")
        if detail in {"dry_run_required", "dry_run_blocked", "wizard_requires_bot", "bot_not_found", "organization_required"}:
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=400, detail=detail)
    uow.commit()
    return ok(result)

def update_wizard_step(service, uow: UnitOfWork, *, wizard_id: str, step_key: str, payload, user: dict) -> dict:
    wizard = service._get_accessible_wizard(uow.conn, wizard_id=wizard_id, user=user, permission="activation.manage")
    diagnostics = (wizard.get("diagnostics") or {}) if isinstance(wizard.get("diagnostics"), dict) else {}
    if diagnostics.get("integrity_mismatch"):
        wizard = reconcile_guided_onboarding_wizard_integrity(uow.conn, wizard_id=wizard_id, source="before_update")
    try:
        updated = update_guided_onboarding_step(
            uow.conn,
            wizard_id=wizard_id,
            step_key=step_key,
            payload=payload.payload,
            expected_revision=payload.expected_revision,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "wizard_revision_conflict":
            raise HTTPException(status_code=409, detail="wizard_revision_conflict")
        if detail == "invalid_step_key":
            raise HTTPException(status_code=400, detail="invalid_step_key")
        if detail == "wizard_step_out_of_sequence":
            raise HTTPException(status_code=409, detail="wizard_step_out_of_sequence")
        if detail == "wizard_not_found":
            raise HTTPException(status_code=404, detail="Wizard not found")
        raise HTTPException(status_code=400, detail=detail)
    uow.commit()
    return ok(updated)


def dry_run_wizard(service, uow: UnitOfWork, *, wizard_id: str, user: dict) -> dict:
    wizard = service._get_accessible_wizard(uow.conn, wizard_id=wizard_id, user=user, permission="activation.manage")
    diagnostics = (wizard.get("diagnostics") or {}) if isinstance(wizard.get("diagnostics"), dict) else {}
    if diagnostics.get("integrity_mismatch"):
        reconcile_guided_onboarding_wizard_integrity(uow.conn, wizard_id=wizard_id, source="before_dry_run")
    try:
        result = dry_run_guided_onboarding_wizard(uow.conn, wizard_id=wizard_id)
    except ValueError as exc:
        detail = str(exc)
        if detail == "wizard_not_found":
            raise HTTPException(status_code=404, detail="Wizard not found")
        raise HTTPException(status_code=400, detail=detail)
    uow.commit()
    return ok(result)


def apply_wizard(service, uow: UnitOfWork, *, wizard_id: str, user: dict) -> dict:
    wizard = service._get_accessible_wizard(uow.conn, wizard_id=wizard_id, user=user, permission="activation.manage")
    diagnostics = (wizard.get("diagnostics") or {}) if isinstance(wizard.get("diagnostics"), dict) else {}
    if diagnostics.get("integrity_mismatch"):
        reconcile_guided_onboarding_wizard_integrity(uow.conn, wizard_id=wizard_id, source="before_apply")
    try:
        result = apply_guided_onboarding_wizard(uow.conn, wizard_id=wizard_id, actor_user=user)
    except ValueError as exc:
        detail = str(exc)
        if detail == "wizard_requires_bot":
            raise HTTPException(status_code=400, detail="Wizard requires a bot before apply")
        if detail == "bot_not_found":
            raise HTTPException(status_code=404, detail="Bot not found")
        if detail == "dry_run_required":
            raise HTTPException(status_code=400, detail="dry_run_required")
        if detail == "dry_run_blocked":
            raise HTTPException(status_code=400, detail="dry_run_blocked")
        raise HTTPException(status_code=400, detail=detail)
    uow.commit()
    return ok(result)


def set_tenant_mode(service, uow: UnitOfWork, *, payload, user: dict) -> dict:
    conn = uow.conn
    org, _ = service._resolve_scope(uow, user=user, organization_id=payload.organization_id, bot_id=None)
    require_permission(user, org["id"], "activation.manage")
    now = utcnow_iso()
    execute(conn, "UPDATE organizations SET tenant_mode = ?, updated_at = ? WHERE id = ?", (payload.tenant_mode, now, org["id"]))
    if table_exists(conn, "product_events"):
        execute(
            conn,
            "INSERT INTO product_events (id, organization_id, bot_id, actor_user_id, event_name, entity_type, entity_id, value_numeric, value_json, created_at) VALUES (?, ?, NULL, ?, ?, 'organization', ?, NULL, ?, ?)",
            (new_id("pevt"), org["id"], user["id"], "tenant.mode_changed", org["id"], to_json({"tenant_mode": payload.tenant_mode}), now),
        )
    create_audit_log(
        conn,
        organization_id=org["id"],
        actor_user_id=user["id"],
        actor_type="user",
        entity_type="organization",
        entity_id=org["id"],
        action="organization.tenant_mode_updated",
        metadata={"tenant_mode": payload.tenant_mode},
    )
    uow.commit()
    return service.summary(uow, user=user, organization_id=org["id"], bot_id=None)


def create_saved_view(service, uow: UnitOfWork, *, payload, user: dict) -> dict:
    ensure_org_access(user, payload.organization_id)
    require_permission(user, payload.organization_id, "conversation.manage")
    saved_view = service._upsert_saved_view(uow.conn, organization_id=payload.organization_id, user_id=user["id"], payload=payload)
    uow.commit()
    return ok(saved_view)
