from __future__ import annotations

import hashlib
import hmac
from typing import Any

from ..config import settings
from ..db import execute, fetch_all, fetch_one
from ..contracts import count_row, runtime_callback_row, integration_sync_run_row
from ..verticals import get_vertical_profile

from .runtime import compute_observability_overview
from .secrets import _canonical_json, resolve_secret
from .security import get_security_policy

from ..utils import (
    add_minutes,
    current_mfa_code,
    decrypt_secret,
    encrypt_secret,
    from_json,
    generate_recovery_codes,
    generate_totp_secret,
    hash_value,
    new_id,
    next_day_iso,
    parse_iso,
    provisioning_uri,
    qr_svg_data_url,
    random_token,
    to_json,
    utcnow_iso,
    verify_totp,
)

def diff_configs(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    _walk_diff("", left, right, changes)
    return {
        "changed": len(changes) > 0,
        "total_changes": len(changes),
        "changes": changes[:100],
        "fingerprints": {
            "left": hashlib.sha256(_canonical_json(left).encode("utf-8")).hexdigest(),
            "right": hashlib.sha256(_canonical_json(right).encode("utf-8")).hexdigest(),
        },
    }


def validate_bot_config(config: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    identity = config.get("identity", {})
    objective = config.get("objective", {})
    knowledge = config.get("business_knowledge", {})
    rules = config.get("rules", {})
    agenda = config.get("agenda", {})
    followups = config.get("followups", {})
    integrations = config.get("integrations", {})

    if not identity.get("bot_name"):
        errors.append("Falta identity.bot_name")
    if not identity.get("business_name"):
        errors.append("Falta identity.business_name")
    if not objective.get("primary"):
        errors.append("Falta objective.primary")
    if not knowledge.get("services"):
        errors.append("Debe existir al menos un servicio en business_knowledge.services")
    if not rules.get("cannot_say"):
        warnings.append("Conviene definir rules.cannot_say para hardening operativo")
    if not agenda.get("availability") and not knowledge.get("hours"):
        warnings.append("No hay disponibilidad ni horario configurado")
    if not isinstance(followups.get("rules", []), list) or len(followups.get("rules", [])) == 0:
        warnings.append("No hay reglas de follow-up configuradas")
    if not integrations.get("whatsapp", {}).get("provider"):
        errors.append("Falta integrations.whatsapp.provider")
    calendar_integration = integrations.get("calendar", {})
    if calendar_integration.get("mode") in {"internal_only", "sandbox"}:
        warnings.append("Calendar sigue en modo no conectado; falta completar OAuth y sincronización del proveedor")
    elif calendar_integration.get("mode") == "google_oauth" and not calendar_integration.get("calendar_id"):
        warnings.append("Calendar usa google_oauth pero aún no define calendar_id")
    if len(knowledge.get("faqs", [])) == 0:
        warnings.append("No hay FAQs cargadas")

    score = max(0, 100 - (len(errors) * 20) - (len(warnings) * 5))
    return {
        "ok": len(errors) == 0,
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "checks": {
            "identity": bool(identity.get("bot_name") and identity.get("business_name")),
            "objective": bool(objective.get("primary")),
            "services": bool(knowledge.get("services")),
            "followups": bool(followups.get("rules")),
            "whatsapp": bool(integrations.get("whatsapp", {}).get("provider")),
        },
    }


def _walk_diff(path: str, left: Any, right: Any, changes: list[dict[str, Any]]) -> None:
    if type(left) is not type(right):
        changes.append({"path": path or "$", "type": "changed_type", "left": left, "right": right})
        return
    if isinstance(left, dict):
        keys = sorted(set(left.keys()) | set(right.keys()))
        for key in keys:
            next_path = f"{path}.{key}" if path else key
            if key not in left:
                changes.append({"path": next_path, "type": "added", "left": None, "right": right[key]})
            elif key not in right:
                changes.append({"path": next_path, "type": "removed", "left": left[key], "right": None})
            else:
                _walk_diff(next_path, left[key], right[key], changes)
        return
    if isinstance(left, list):
        if left != right:
            changes.append(
                {
                    "path": path or "$",
                    "type": "list_changed",
                    "left_count": len(left),
                    "right_count": len(right),
                    "left_preview": left[:3],
                    "right_preview": right[:3],
                }
            )
        return
    if left != right:
        changes.append({"path": path or "$", "type": "changed", "left": left, "right": right})



_EXPECTED_INTEGRATION_ALIASES = {
    'google_calendar': ('google_calendar', 'google', 'calendar'),
    'payments': ('payments', 'payment', 'stripe'),
    'crm': ('crm', 'sales', 'leads'),
    'whatsapp': ('whatsapp', 'meta', 'meta_cloud_api'),
    'sso': ('sso',),
}

def _integration_expected_key(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"calendar", "google_calendar"}:
        return "google_calendar"
    if raw in {"payment", "payments", "stripe"}:
        return "payments"
    return raw or "unknown"


def _integration_matches_expected(row: dict[str, Any] | None, expected: str) -> bool:
    if not row:
        return False
    aliases = set(_EXPECTED_INTEGRATION_ALIASES.get(_integration_expected_key(expected), (_integration_expected_key(expected),)))
    values = {str(row.get('provider') or '').lower(), str(row.get('integration_type') or '').lower(), str(row.get('name') or '').lower(), str(row.get('status') or '').lower()}
    return any(alias in value or value in aliases for alias in aliases for value in values if value)


def _best_integration(conn, *, organization_id: str, bot_id: str, expected: str) -> dict[str, Any] | None:
    rows = fetch_all(
        conn,
        """
        SELECT * FROM integration_connections
        WHERE organization_id = ? AND (bot_id = ? OR bot_id IS NULL)
        ORDER BY CASE WHEN bot_id = ? THEN 0 ELSE 1 END, updated_at DESC
        """,
        (organization_id, bot_id, bot_id),
    )
    for row in rows:
        if _integration_matches_expected(row, expected):
            return row
    return None


def _release_item(key: str, label: str, ok: bool, detail: str, *, href: str, required: bool = True) -> dict[str, Any]:
    return {"key": key, "label": label, "ok": bool(ok), "detail": detail, "href": href, "required": required}


def compute_observability_overview(conn, organization_id: str | None = None, bot_id: str | None = None) -> dict[str, Any]:
    where = []
    params: list[Any] = []
    if organization_id:
        where.append("organization_id = ?")
        params.append(organization_id)
    if bot_id:
        where.append("bot_id = ?")
        params.append(bot_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    runs = fetch_all(conn, f"SELECT status, duration_ms FROM execution_runs {where_sql} ORDER BY created_at DESC LIMIT 1000", params)
    total = len(runs)
    failed = len([r for r in runs if r.get("status") == "failed"])
    completed = [int(r["duration_ms"]) for r in runs if r.get("duration_ms") is not None]
    completed.sort()

    def percentile(values: list[int], p: float) -> int | None:
        if not values:
            return None
        idx = max(0, min(len(values) - 1, int(round((len(values) - 1) * p))))
        return values[idx]

    recent_failures = fetch_all(
        conn,
        f"SELECT id, status, trace_id, execution_id, created_at, error_json FROM execution_runs {where_sql} {'AND' if where_sql else 'WHERE'} status = 'failed' ORDER BY created_at DESC LIMIT 10",
        params,
    )
    logs = fetch_all(
        conn,
        f"SELECT level, category, message, trace_id, execution_id, created_at FROM technical_logs {where_sql} ORDER BY created_at DESC LIMIT 20",
        params,
    )
    dead_jobs = fetch_one(conn, f"SELECT COUNT(*) AS value FROM automation_jobs {where_sql} {'AND' if where_sql else 'WHERE'} status = 'dead_letter'", params)
    dead_outbox = fetch_one(conn, f"SELECT COUNT(*) AS value FROM outbox_messages {where_sql} {'AND' if where_sql else 'WHERE'} status = 'dead_letter'", params)
    callbacks = fetch_one(conn, f"SELECT COUNT(*) AS value FROM runtime_callbacks {where_sql}", params)
    return {
        "totals": {
            "runs": total,
            "failed_runs": failed,
            "success_rate": round(((total - failed) / total) * 100, 2) if total else None,
            "p95_duration_ms": percentile(completed, 0.95),
            "p99_duration_ms": percentile(completed, 0.99),
            "dead_letter_jobs": int((dead_jobs or {}).get("value") or 0),
            "dead_letter_outbox": int((dead_outbox or {}).get("value") or 0),
            "callbacks": int((callbacks or {}).get("value") or 0),
        },
        "recent_failures": recent_failures,
        "recent_logs": logs,
    }


def get_security_policy(conn, *, organization_id: str) -> dict[str, Any]:
    row = fetch_one(conn, "SELECT * FROM organization_security_policies WHERE organization_id = ?", (organization_id,))
    if row:
        return {**row, "ip_allowlist": from_json(row.get("ip_allowlist_json"), []), "allowed_origins": from_json(row.get("allowed_origins_json"), [])}
    return {
        "organization_id": organization_id,
        "require_mfa": 0,
        "require_sso": 0,
        "session_ttl_minutes": settings.refresh_token_ttl_minutes,
        "session_idle_timeout_minutes": settings.session_idle_timeout_minutes,
        "step_up_window_minutes": settings.step_up_window_minutes,
        "max_sessions_per_user": settings.max_sessions_per_user,
        "require_dual_approval_releases": 1,
        "webhook_signature_required": 1,
        "strict_idempotency": 1,
        "ip_allowlist": [],
        "allowed_origins": [],
    }


def resolve_secret(
    conn,
    *,
    organization_id: str,
    key_name: str,
    bot_id: str | None = None,
    actor_type: str = 'runtime',
    actor_id: str | None = None,
) -> str | None:
    candidates = []
    if bot_id:
        candidates.append((organization_id, bot_id, key_name))
    candidates.append((organization_id, None, key_name))
    for org_id, scoped_bot_id, scoped_key in candidates:
        row = fetch_one(
            conn,
            "SELECT * FROM secret_entries WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND key_name = ? ORDER BY updated_at DESC LIMIT 1",
            (org_id, scoped_bot_id, scoped_key),
        )
        if not row:
            continue
        encrypted = row.get('value_encrypted')
        if encrypted:
            secret_value = decrypt_secret(encrypted, settings.secret_encryption_key)
            _record_secret_access(conn, secret_id=row['id'], organization_id=organization_id, actor_type=actor_type, actor_id=actor_id, metadata={'key_name': key_name})
            return secret_value
    return None


def _compute_release_checklist(conn, *, organization_id: str, bot_id: str, validation: dict[str, Any], diff_summary: dict[str, Any]) -> dict[str, Any]:
    readiness = release_readiness(conn, organization_id=organization_id, bot_id=bot_id)
    checklist = dict(readiness.get('checklist') or {})
    checklist['validation_ok'] = bool(validation.get('ok'))
    checklist['diff_reviewed'] = int(diff_summary.get('total_changes') or 0) > 0 or bool(diff_summary.get('fingerprints'))
    checklist['requires_approval'] = True
    return checklist


def record_bot_build(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    version_id: str,
    validation: dict[str, Any],
    diff_summary: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    build_id = new_id("build")
    services = config.get("business_knowledge", {}).get("services", [])
    artifact = {
        "manifest": {
            "services_count": len(services),
            "faq_count": len(config.get("business_knowledge", {}).get("faqs", [])),
            "followup_rules_count": len(config.get("followups", {}).get("rules", [])),
            "integrations": sorted((config.get("integrations") or {}).keys()),
            "generated_at": utcnow_iso(),
        },
        "files": [
            {"name": "config.json", "kind": "bot_config"},
            {"name": "manifest.json", "kind": "build_manifest"},
            {"name": "release-notes.txt", "kind": "release_metadata"},
        ],
    }
    execute(
        conn,
        """
        INSERT INTO bot_builds
        (id, organization_id, bot_id, version_id, validation_status, validation_json, diff_summary_json, artifact_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            build_id,
            organization_id,
            bot_id,
            version_id,
            "passed" if validation.get("ok") else "failed",
            to_json(validation),
            to_json(diff_summary),
            to_json(artifact),
            utcnow_iso(),
        ),
    )
    return fetch_one(conn, "SELECT * FROM bot_builds WHERE id = ?", (build_id,))


def release_readiness(conn, *, organization_id: str, bot_id: str) -> dict[str, Any]:
    bot = fetch_one(conn, "SELECT * FROM bots WHERE id = ?", (bot_id,))
    if not bot:
        raise ValueError("bot_not_found")
    org = fetch_one(conn, "SELECT * FROM organizations WHERE id = ?", (organization_id,)) or {}
    profile = get_vertical_profile(bot.get('vertical') or org.get('vertical'))
    config = from_json(bot.get('config_draft_json'), {})
    validation = validate_bot_config(config)
    previous_version = fetch_one(conn, "SELECT * FROM bot_versions WHERE id = ?", (bot.get('published_version_id'),)) if bot.get('published_version_id') else None
    diff_summary = diff_configs(from_json((previous_version or {}).get('config_json'), {}) if previous_version else {}, config)
    observability = compute_observability_overview(conn, organization_id=organization_id, bot_id=bot_id)
    security_policy = get_security_policy(conn, organization_id=organization_id)

    behavior = fetch_one(conn, "SELECT * FROM bot_behavior_settings WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id)) or {}
    templates_count = int((fetch_one(conn, "SELECT COUNT(*) AS value FROM bot_response_templates WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id)) or {}).get('value') or 0)
    products_count = int((fetch_one(conn, "SELECT COUNT(*) AS value FROM catalog_products WHERE organization_id = ? AND (bot_id = ? OR bot_id IS NULL)", (organization_id, bot_id)) or {}).get('value') or 0)
    services_count = int((fetch_one(conn, "SELECT COUNT(*) AS value FROM catalog_services WHERE organization_id = ? AND (bot_id = ? OR bot_id IS NULL)", (organization_id, bot_id)) or {}).get('value') or 0)
    promos_count = int((fetch_one(conn, "SELECT COUNT(*) AS value FROM catalog_promotions WHERE organization_id = ? AND (bot_id = ? OR bot_id IS NULL) AND status IN ('active','draft')", (organization_id, bot_id)) or {}).get('value') or 0)
    versions_count = int((fetch_one(conn, "SELECT COUNT(*) AS value FROM bot_versions WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id)) or {}).get('value') or 0)
    secrets_count = int((fetch_one(conn, "SELECT COUNT(*) AS value FROM secret_entries WHERE organization_id = ? AND (expires_at IS NULL OR expires_at > ?)", (organization_id, utcnow_iso())) or {}).get('value') or 0)
    audits_count = int((fetch_one(conn, "SELECT COUNT(*) AS value FROM audit_logs WHERE organization_id = ?", (organization_id,)) or {}).get('value') or 0)
    dead_jobs = int((((observability or {}).get('totals') or {}).get('dead_letter_jobs') or 0))
    dead_outbox = int((((observability or {}).get('totals') or {}).get('dead_letter_outbox') or 0))

    whatsapp_row = fetch_one(conn, "SELECT * FROM whatsapp_numbers WHERE organization_id = ? AND bot_id = ? ORDER BY updated_at DESC LIMIT 1", (organization_id, bot_id)) or {}
    whatsapp_token = resolve_secret(conn, organization_id=organization_id, bot_id=bot_id, key_name='META_ACCESS_TOKEN') or resolve_secret(conn, organization_id=organization_id, bot_id=bot_id, key_name='WHATSAPP_ACCESS_TOKEN')
    whatsapp_connected = bool(whatsapp_row.get('phone_number_id') and whatsapp_row.get('connection_status') == 'connected' and whatsapp_token)

    google_row = _best_integration(conn, organization_id=organization_id, bot_id=bot_id, expected='google_calendar') or {}
    google_config = from_json(google_row.get('config_json'), {}) if google_row else {}
    google_connected = bool(google_row.get('id') and google_row.get('status') in {'active', 'configured'} and (google_row.get('credential_status') in {'connected', 'configured'} or google_config.get('calendar_id')))

    payments_row = _best_integration(conn, organization_id=organization_id, bot_id=bot_id, expected='payments') or {}
    payments_config = from_json(payments_row.get('config_json'), {}) if payments_row else {}
    payments_connected = bool(payments_row.get('id') and (payments_row.get('status') in {'active', 'configured'} or payments_row.get('credential_status') in {'connected', 'configured'}) and (payments_config.get('success_url') and payments_config.get('cancel_url')))

    crm_row = _best_integration(conn, organization_id=organization_id, bot_id=bot_id, expected='crm') or {}
    crm_connected = bool(crm_row.get('id') and crm_row.get('status') in {'active', 'configured', 'connected'})

    has_behavior = bool(behavior and (behavior.get('bot_mode') or behavior.get('tone') or behavior.get('response_length')))
    has_templates = templates_count > 0
    has_content = (products_count + services_count + promos_count) > 0
    has_org_vertical = bool(org.get('vertical'))
    has_bot_vertical = bool(bot.get('vertical'))
    observability_ready = dead_jobs == 0 and dead_outbox == 0
    security_ready = bool(security_policy.get('id'))
    secrets_hardened = secrets_count > 0 and bool(security_policy.get('webhook_signature_required'))
    rollback_ready = versions_count >= 1
    diff_reviewed = int(diff_summary.get('total_changes') or 0) > 0 or bool(bot.get('published_version_id'))
    authz_ready = bool(security_policy.get('id'))

    recommended = list(profile.get('recommended_integrations') or [])
    requires_calendar = any(_integration_expected_key(item) == 'google_calendar' for item in recommended)
    requires_payments = any(_integration_expected_key(item) == 'payments' for item in recommended)
    requires_crm = any(_integration_expected_key(item) == 'crm' for item in recommended)

    checklist_items = [
        _release_item('org_vertical', 'Vertical en organización', has_org_vertical, 'La organización activa ya tiene vertical definida.' if has_org_vertical else 'Define la vertical del tenant para cargar lenguaje y defaults.', href='/onboarding?step=cuenta'),
        _release_item('bot_vertical', 'Vertical en bot', has_bot_vertical, 'El bot ya quedó alineado a una vertical.' if has_bot_vertical else 'Aplica la vertical al bot antes de salir.', href='/onboarding?step=bot'),
        _release_item('whatsapp', 'WhatsApp conectado', whatsapp_connected, 'Ya existe número conectado con token operativo.' if whatsapp_connected else 'Falta conectar WhatsApp Cloud API para operar en producción.', href='/integrations?section=configuracion'),
        _release_item('calendar', 'Calendar listo', google_connected, 'Calendar ya puede sincronizar agenda.' if google_connected else 'Configura Google Calendar para citas y disponibilidad.', href='/integrations?section=configuracion', required=requires_calendar),
        _release_item('payments', 'Payments listos', payments_connected, 'Stripe ya tiene URLs y credenciales base.' if payments_connected else 'Configura pagos para cobrar o apartar desde el flujo.', href='/integrations?section=configuracion', required=requires_payments),
        _release_item('crm', 'CRM alineado', crm_connected, 'Ya hay frente CRM visible para seguimiento.' if crm_connected else 'El CRM sigue siendo opcional, pero ayuda a no perder continuidad.', href='/integrations?section=configuracion', required=False),
        _release_item('behavior', 'Comportamiento sembrado', has_behavior, 'El bot ya tiene tono, modo y reglas visibles.' if has_behavior else 'Todavía falta sembrar comportamiento del bot.', href='/bot-studio'),
        _release_item('templates', 'Templates sembrados', has_templates, f'Ya hay {templates_count} plantilla(s) operativas.' if has_templates else 'Faltan plantillas para responder y seguir conversaciones con consistencia.', href='/bot-studio'),
        _release_item('content', 'Contenido visible', has_content, f'Hay {products_count} productos, {services_count} servicios y {promos_count} promos visibles.' if has_content else 'Falta contenido comercial u operativo para un release serio.', href='/catalog'),
        _release_item('validation', 'Validación del draft', bool(validation.get('ok')), 'El draft pasó la validación base.' if validation.get('ok') else 'El draft todavía falla validación operativa.', href=f'/bots/{bot_id}/versions'),
        _release_item('observability', 'Observabilidad limpia', observability_ready, 'No hay dead letters visibles que bloqueen salida.' if observability_ready else 'Hay dead letters o fallas recientes que conviene limpiar antes de publicar.', href='/status'),
        _release_item('security', 'Seguridad revisada', security_ready, 'Existe política de seguridad activa para la organización.' if security_ready else 'Falta política de seguridad visible para este tenant.', href='/security'),
        _release_item('secrets', 'Secrets endurecidos', secrets_hardened, 'Ya hay secretos vigentes y firma webhook endurecida.' if secrets_hardened else 'Falta terminar de guardar secretos o endurecer firma webhook.', href='/secrets'),
        _release_item('audit', 'Auditoría visible', audits_count > 0, 'Ya existe rastro de auditoría para soporte y releases.' if audits_count > 0 else 'Todavía no se ve auditoría suficiente para el tenant.', href='/audit'),
        _release_item('rollback', 'Rollback disponible', rollback_ready, 'Ya existe al menos una versión sobre la cual apoyarte.' if rollback_ready else 'Todavía no hay historia suficiente de versiones para rollback.', href=f'/bots/{bot_id}/versions'),
        _release_item('diff', 'Diff revisable', diff_reviewed, 'El draft tiene diff o historia publicada para revisar.' if diff_reviewed else 'Todavía no hay diff útil contra publicado.', href=f'/bots/{bot_id}/versions'),
        _release_item('authz', 'Autorización y política', authz_ready, 'La política organizacional ya puede respaldar aprobación y publish.' if authz_ready else 'Falta política organizacional para sostener el release flow.', href='/security'),
    ]

    blockers = [
        {"key": item['key'], "title": item['label'], "detail": item['detail'], "href": item['href']}
        for item in checklist_items
        if item['required'] and not item['ok'] and item['key'] not in {'crm'}
    ]
    warnings = [
        {"key": item['key'], "title": item['label'], "detail": item['detail'], "href": item['href']}
        for item in checklist_items
        if (not item['required']) and not item['ok']
    ]
    score = max(0, 100 - (len(blockers) * 12) - (len(validation.get('warnings') or []) * 3) - (len(warnings) * 2))
    status = 'green' if not blockers and score >= 85 else 'amber' if len(blockers) <= 2 and score >= 65 else 'red'

    integrations = [
        {"key": 'whatsapp', "label": 'WhatsApp', "required": True, "connected": whatsapp_connected, "status": 'connected' if whatsapp_connected else ('configured' if whatsapp_row.get('id') else 'missing'), "detail": 'Cloud API y número listos.' if whatsapp_connected else 'Falta terminar número, token o webhook.', "href": '/integrations?section=configuracion'},
        {"key": 'google_calendar', "label": 'Google Calendar', "required": requires_calendar, "connected": google_connected, "status": 'connected' if google_connected else ('configured' if google_row.get('id') else 'missing'), "detail": 'Agenda lista para disponibilidad real.' if google_connected else 'Falta OAuth o calendar_id.', "href": '/integrations?section=configuracion'},
        {"key": 'payments', "label": 'Payments', "required": requires_payments, "connected": payments_connected, "status": 'connected' if payments_connected else ('configured' if payments_row.get('id') else 'missing'), "detail": 'Cobro y reconciliación listos.' if payments_connected else 'Faltan URLs o credenciales.', "href": '/integrations?section=configuracion'},
        {"key": 'crm', "label": 'CRM', "required": requires_crm, "connected": crm_connected, "status": 'connected' if crm_connected else ('configured' if crm_row.get('id') else 'missing'), "detail": 'Seguimiento comercial ya aterrizado.' if crm_connected else 'Sigue siendo un frente opcional o pendiente.', "href": '/integrations?section=configuracion'},
    ]

    checklist = {
        'validation_ok': bool(validation.get('ok')),
        'diff_reviewed': diff_reviewed,
        'observability_ready': observability_ready,
        'rollback_ready': rollback_ready,
        'security_reviewed': security_ready,
        'authz_tests_passed': authz_ready,
        'secrets_hardened': secrets_hardened,
        'audit_ready': audits_count > 0,
        'channel_ready': whatsapp_connected,
        'payments_ready': payments_connected if requires_payments else True,
        'calendar_ready': google_connected if requires_calendar else True,
        'behavior_ready': has_behavior,
        'templates_ready': has_templates,
        'content_ready': has_content,
        'vertical_ready': has_org_vertical and has_bot_vertical,
        'requires_approval': True,
    }

    return {
        'bot_id': bot_id,
        'organization_id': organization_id,
        'vertical': {'id': profile.get('id'), 'name': profile.get('name'), 'short_name': profile.get('short_name')},
        'summary': {
            'score': score,
            'status': status,
            'can_request_release': has_org_vertical and has_bot_vertical and has_behavior and has_templates,
            'can_approve_release': bool(validation.get('ok')) and security_ready and authz_ready,
            'can_publish_release': len(blockers) == 0,
            'blocking_count': len(blockers),
            'warning_count': len(validation.get('warnings') or []) + len(warnings),
        },
        'checklist': checklist,
        'checklist_items': checklist_items,
        'blockers': blockers,
        'warnings': warnings,
        'integrations': integrations,
        'validation': validation,
        'diff_summary': diff_summary,
    }


def create_release_request(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    requested_by: str,
    title: str,
    notes: str,
    validation: dict[str, Any],
    diff_summary: dict[str, Any],
) -> dict[str, Any]:
    release_id = new_id("rel")
    checklist = _compute_release_checklist(conn, organization_id=organization_id, bot_id=bot_id, validation=validation, diff_summary=diff_summary)
    execute(
        conn,
        """
        INSERT INTO release_requests
        (id, organization_id, bot_id, version_id, requested_by, approved_by, status, title, notes, validation_json, diff_summary_json, checklist_json, created_at, approved_at, published_at)
        VALUES (?, ?, ?, NULL, ?, NULL, 'requested', ?, ?, ?, ?, ?, ?, NULL, NULL)
        """,
        (
            release_id,
            organization_id,
            bot_id,
            requested_by,
            title,
            notes,
            to_json(validation),
            to_json(diff_summary),
            to_json(checklist),
            utcnow_iso(),
        ),
    )
    return fetch_one(conn, "SELECT * FROM release_requests WHERE id = ?", (release_id,))


def approve_release_request(conn, *, release_id: str, approved_by: str, note: str = "") -> dict[str, Any]:
    row = fetch_one(conn, "SELECT * FROM release_requests WHERE id = ?", (release_id,))
    if not row:
        raise ValueError("release_not_found")
    execute(
        conn,
        """
        UPDATE release_requests
        SET status = 'approved', approved_by = ?, approved_at = ?, notes = CASE WHEN ? = '' THEN notes ELSE TRIM(COALESCE(notes,'') || '\n' || ?) END
        WHERE id = ?
        """,
        (approved_by, utcnow_iso(), note, note, release_id),
    )
    return fetch_one(conn, "SELECT * FROM release_requests WHERE id = ?", (release_id,))


def publish_release_request(conn, *, release_id: str, version_id: str) -> dict[str, Any]:
    execute(
        conn,
        "UPDATE release_requests SET status = 'published', version_id = ?, published_at = ? WHERE id = ?",
        (version_id, utcnow_iso(), release_id),
    )
    return fetch_one(conn, "SELECT * FROM release_requests WHERE id = ?", (release_id,))


def list_release_requests(conn, *, bot_id: str) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM release_requests WHERE bot_id = ? ORDER BY created_at DESC", (bot_id,))
    return [
        {
            **row,
            "validation": from_json(row.get("validation_json"), {}),
            "diff_summary": from_json(row.get("diff_summary_json"), {}),
            "checklist": from_json(row.get("checklist_json"), {}),
        }
        for row in rows
    ]
