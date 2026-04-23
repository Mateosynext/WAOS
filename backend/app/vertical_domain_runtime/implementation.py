from __future__ import annotations

from typing import Any

from ..utils import from_json, new_id, to_json, utcnow_iso
from ..runtime_schema_guards import assert_schema_ready

HARD_VERTICALS = {"fitness", "dental", "aesthetic", "vet", "auto-service"}

def _db():
    from .db import execute, fetch_all, fetch_one
    return execute, fetch_all, fetch_one


def ensure_vertical_domain_schema(conn: Any) -> None:
    assert_schema_ready(
        conn,
        owner="vertical_domain_runtime",
        tables=(
            "dental_patients", "dental_cases", "dental_treatment_plans", "dental_case_documents", "dental_recalls",
            "fitness_members", "fitness_goal_profiles", "fitness_program_recommendations", "fitness_attendance_risk", "fitness_freezes",
            "auto_service_vehicles", "auto_service_orders", "auto_service_inspections", "auto_service_maintenance_cycles", "auto_service_approvals",
            "vet_guardians", "vet_pets", "vet_preventive_plans", "vet_vaccine_schedules", "vet_service_history",
            "aesthetic_patients", "aesthetic_treatment_plans", "aesthetic_session_packages", "aesthetic_aftercare_cycles", "aesthetic_consents",
        ),
    )


def _upsert(conn: Any, sql: str, params: tuple[Any, ...]) -> None:
    execute, _, _ = _db()
    execute(conn, sql, params)


def _fetch_rows(conn: Any, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    _, fetch_all, _ = _db()
    return [dict(row) for row in fetch_all(conn, sql, params)]


def _fetch_row(conn: Any, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    _, _, fetch_one = _db()
    row = fetch_one(conn, sql, params)
    return dict(row) if row else None


def bootstrap_vertical_domain(conn: Any, account: dict[str, Any]) -> None:
    vertical_id = account.get("vertical_id")
    if vertical_id not in HARD_VERTICALS:
        return
    if vertical_id == "dental":
        _bootstrap_dental(conn, account)
    elif vertical_id == "fitness":
        _bootstrap_fitness(conn, account)
    elif vertical_id == "auto-service":
        _bootstrap_auto_service(conn, account)
    elif vertical_id == "vet":
        _bootstrap_vet(conn, account)
    elif vertical_id == "aesthetic":
        _bootstrap_aesthetic(conn, account)


def apply_vertical_domain_command(conn: Any, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> None:
    vertical_id = account.get("vertical_id")
    if vertical_id not in HARD_VERTICALS:
        return
    bootstrap_vertical_domain(conn, account)
    if vertical_id == "dental":
        _apply_dental_command(conn, account, command_name, payload)
    elif vertical_id == "fitness":
        _apply_fitness_command(conn, account, command_name, payload)
    elif vertical_id == "auto-service":
        _apply_auto_service_command(conn, account, command_name, payload)
    elif vertical_id == "vet":
        _apply_vet_command(conn, account, command_name, payload)
    elif vertical_id == "aesthetic":
        _apply_aesthetic_command(conn, account, command_name, payload)


def get_vertical_domain_snapshot(conn: Any, *, organization_id: str, account_id: str, vertical_id: str) -> dict[str, Any]:
    if vertical_id not in HARD_VERTICALS:
        return {"vertical_id": vertical_id, "hard_domain_enabled": False, "records": {}}
    if vertical_id == "dental":
        return {
            "vertical_id": vertical_id,
            "hard_domain_enabled": True,
            "records": {
                "patients": _fetch_rows(conn, "SELECT * FROM dental_patients WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "cases": _fetch_rows(conn, "SELECT * FROM dental_cases WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "treatment_plans": _fetch_rows(conn, "SELECT * FROM dental_treatment_plans WHERE organization_id = ? AND account_id = ? ORDER BY updated_at DESC", (organization_id, account_id)),
                "documents": _fetch_rows(conn, "SELECT * FROM dental_case_documents WHERE organization_id = ? AND account_id = ? ORDER BY updated_at DESC", (organization_id, account_id)),
                "recalls": _fetch_rows(conn, "SELECT * FROM dental_recalls WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
            },
        }
    if vertical_id == "fitness":
        return {
            "vertical_id": vertical_id,
            "hard_domain_enabled": True,
            "records": {
                "members": _fetch_rows(conn, "SELECT * FROM fitness_members WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "goal_profiles": _fetch_rows(conn, "SELECT * FROM fitness_goal_profiles WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "program_recommendations": _fetch_rows(conn, "SELECT * FROM fitness_program_recommendations WHERE organization_id = ? AND account_id = ? ORDER BY updated_at DESC", (organization_id, account_id)),
                "attendance_risk": _fetch_rows(conn, "SELECT * FROM fitness_attendance_risk WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "freezes": _fetch_rows(conn, "SELECT * FROM fitness_freezes WHERE organization_id = ? AND account_id = ? ORDER BY updated_at DESC", (organization_id, account_id)),
            },
        }
    if vertical_id == "auto-service":
        return {
            "vertical_id": vertical_id,
            "hard_domain_enabled": True,
            "records": {
                "vehicles": _fetch_rows(conn, "SELECT * FROM auto_service_vehicles WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "orders": _fetch_rows(conn, "SELECT * FROM auto_service_orders WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "inspections": _fetch_rows(conn, "SELECT * FROM auto_service_inspections WHERE organization_id = ? AND account_id = ? ORDER BY updated_at DESC", (organization_id, account_id)),
                "maintenance_cycles": _fetch_rows(conn, "SELECT * FROM auto_service_maintenance_cycles WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "approvals": _fetch_rows(conn, "SELECT * FROM auto_service_approvals WHERE organization_id = ? AND account_id = ? ORDER BY updated_at DESC", (organization_id, account_id)),
            },
        }
    if vertical_id == "vet":
        return {
            "vertical_id": vertical_id,
            "hard_domain_enabled": True,
            "records": {
                "guardians": _fetch_rows(conn, "SELECT * FROM vet_guardians WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "pets": _fetch_rows(conn, "SELECT * FROM vet_pets WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "preventive_plans": _fetch_rows(conn, "SELECT * FROM vet_preventive_plans WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
                "vaccine_schedules": _fetch_rows(conn, "SELECT * FROM vet_vaccine_schedules WHERE organization_id = ? AND account_id = ? ORDER BY updated_at DESC", (organization_id, account_id)),
                "service_history": _fetch_rows(conn, "SELECT * FROM vet_service_history WHERE organization_id = ? AND account_id = ? ORDER BY created_at DESC", (organization_id, account_id)),
            },
        }
    return {
        "vertical_id": vertical_id,
        "hard_domain_enabled": True,
        "records": {
            "patients": _fetch_rows(conn, "SELECT * FROM aesthetic_patients WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
            "treatment_plans": _fetch_rows(conn, "SELECT * FROM aesthetic_treatment_plans WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
            "session_packages": _fetch_rows(conn, "SELECT * FROM aesthetic_session_packages WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
            "aftercare_cycles": _fetch_rows(conn, "SELECT * FROM aesthetic_aftercare_cycles WHERE organization_id = ? AND account_id = ?", (organization_id, account_id)),
            "consents": _fetch_rows(conn, "SELECT * FROM aesthetic_consents WHERE organization_id = ? AND account_id = ? ORDER BY updated_at DESC", (organization_id, account_id)),
        },
    }


def _bootstrap_dental(conn: Any, account: dict[str, Any]) -> None:
    now = utcnow_iso()
    patient_id = f"dent-patient-{account['id']}"
    case_id = f"dent-case-{account['id']}"
    _upsert(conn, "INSERT INTO dental_patients (id, organization_id, account_id, contact_id, full_name, patient_status, chief_complaint, risk_flags_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (patient_id, account['organization_id'], account['id'], account.get('contact_id'), account.get('metadata', {}).get('patient_name') or 'Paciente dental', 'prospect', account.get('metadata', {}).get('chief_complaint') or 'valoracion inicial', to_json([]), now, now))
    _upsert(conn, "INSERT INTO dental_cases (id, organization_id, account_id, patient_id, case_status, triage_type, diagnosis_summary, phase_count, accepted_phase_count, next_recall_due_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (case_id, account['organization_id'], account['id'], patient_id, 'intake', 'valoracion', 'pendiente', now, now))
    _upsert(conn, "INSERT INTO dental_treatment_plans (id, organization_id, account_id, case_id, plan_name, plan_status, total_amount, phases_json, financing_allowed, created_at, updated_at) VALUES (?, ?, ?, ?, 'baseline-plan', 'draft', 0, '[]', 1, ?, ?) ON CONFLICT(account_id, plan_name) DO UPDATE SET updated_at = excluded.updated_at", (new_id('dtp'), account['organization_id'], account['id'], case_id, now, now))
    _upsert(conn, "INSERT INTO dental_case_documents (id, organization_id, account_id, case_id, document_name, status, document_kind, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, 'consentimiento-inicial', 'pending', 'consent', '{}', ?, ?) ON CONFLICT(account_id, document_name) DO UPDATE SET updated_at = excluded.updated_at", (new_id('ddoc'), account['organization_id'], account['id'], case_id, now, now))
    _upsert(conn, "INSERT INTO dental_recalls (id, organization_id, account_id, case_id, recall_type, status, due_at, last_completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, 'recall', 'pending', ?, NULL, ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('drec'), account['organization_id'], account['id'], case_id, now, now, now))


def _apply_dental_command(conn: Any, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> None:
    now = utcnow_iso()
    case_row = _fetch_row(conn, "SELECT * FROM dental_cases WHERE account_id = ?", (account['id'],))
    if not case_row:
        return
    if command_name in {'qualify_record', 'mark_eligibility'}:
        _upsert(conn, "UPDATE dental_cases SET case_status = 'diagnosed', triage_type = ?, diagnosis_summary = ?, updated_at = ? WHERE account_id = ?", (payload.get('triage_type') or 'valoracion', payload.get('diagnosis') or 'caso diagnosticado', now, account['id']))
    if command_name in {'create_quote', 'approve_quote', 'start_case'}:
        plan_name = str(payload.get('plan_name') or 'plan-tratamiento-principal')
        phases = payload.get('phases') or [{'phase': 'fase_1', 'amount': float(payload.get('amount') or 1000)}]
        status = 'accepted' if command_name == 'approve_quote' else ('active' if command_name == 'start_case' else 'proposed')
        _upsert(conn, "INSERT INTO dental_treatment_plans (id, organization_id, account_id, case_id, plan_name, plan_status, total_amount, phases_json, financing_allowed, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account_id, plan_name) DO UPDATE SET plan_status = excluded.plan_status, total_amount = excluded.total_amount, phases_json = excluded.phases_json, financing_allowed = excluded.financing_allowed, updated_at = excluded.updated_at", (new_id('dtp'), account['organization_id'], account['id'], case_row['id'], plan_name, status, float(payload.get('amount') or 1000), to_json(phases), 1, now, now))
        _upsert(conn, "UPDATE dental_cases SET case_status = ?, phase_count = ?, accepted_phase_count = ?, updated_at = ? WHERE account_id = ?", ('active' if command_name == 'start_case' else 'quoted', len(phases), len(phases) if status in {'accepted','active'} else 0, now, account['id']))
    docs = payload.get('documents') or []
    for item in docs:
        name = item if isinstance(item, str) else str(item.get('name') or 'consentimiento')
        status = 'signed' if (isinstance(item, dict) and item.get('status') == 'signed') else 'pending'
        _upsert(conn, "INSERT INTO dental_case_documents (id, organization_id, account_id, case_id, document_name, status, document_kind, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account_id, document_name) DO UPDATE SET status = excluded.status, document_kind = excluded.document_kind, payload_json = excluded.payload_json, updated_at = excluded.updated_at", (new_id('ddoc'), account['organization_id'], account['id'], case_row['id'], name, status, 'consent', to_json(item if isinstance(item, dict) else {'name': name}), now, now))
    if command_name in {'schedule_recurrence', 'schedule_maintenance', 'activate_plan', 'close_fulfillment'}:
        due_at = str(payload.get('due_at') or payload.get('next_recall_due_at') or now)
        _upsert(conn, "INSERT INTO dental_recalls (id, organization_id, account_id, case_id, recall_type, status, due_at, last_completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account_id) DO UPDATE SET recall_type = excluded.recall_type, status = excluded.status, due_at = excluded.due_at, last_completed_at = excluded.last_completed_at, updated_at = excluded.updated_at", (new_id('drec'), account['organization_id'], account['id'], case_row['id'], 'recall', 'scheduled', due_at, now if command_name == 'close_fulfillment' else None, now, now))


def _bootstrap_fitness(conn: Any, account: dict[str, Any]) -> None:
    now = utcnow_iso()
    member_id = f"fit-member-{account['id']}"
    _upsert(conn, "INSERT INTO fitness_members (id, organization_id, account_id, contact_id, member_status, suggested_program, coach_match, weekly_attendance_target, created_at, updated_at) VALUES (?, ?, ?, ?, 'lead', 'starter-program', 'pending', 3, ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (member_id, account['organization_id'], account['id'], account.get('contact_id'), now, now))
    _upsert(conn, "INSERT INTO fitness_goal_profiles (id, organization_id, account_id, member_id, primary_goal, level_band, preferred_modality, restrictions_json, created_at, updated_at) VALUES (?, ?, ?, ?, 'recomposition', 'beginner', 'functional', '[]', ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('fgp'), account['organization_id'], account['id'], member_id, now, now))
    _upsert(conn, "INSERT INTO fitness_program_recommendations (id, organization_id, account_id, member_id, program_name, recommendation_status, sessions_per_week, package_type, notes_json, created_at, updated_at) VALUES (?, ?, ?, ?, 'starter-program', 'draft', 3, 'membership', '{}', ?, ?) ON CONFLICT(account_id, program_name) DO UPDATE SET updated_at = excluded.updated_at", (new_id('fpr'), account['organization_id'], account['id'], member_id, now, now))
    _upsert(conn, "INSERT INTO fitness_attendance_risk (id, organization_id, account_id, member_id, attendance_last_7d, attendance_last_30d, risk_level, churn_signals_json, updated_at) VALUES (?, ?, ?, ?, 0, 0, 'low', '[]', ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('far'), account['organization_id'], account['id'], member_id, now))


def _apply_fitness_command(conn: Any, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> None:
    now = utcnow_iso()
    member = _fetch_row(conn, "SELECT * FROM fitness_members WHERE account_id = ?", (account['id'],))
    if not member:
        return
    if command_name in {'qualify_record', 'mark_eligibility'}:
        _upsert(conn, "UPDATE fitness_goal_profiles SET primary_goal = ?, level_band = ?, preferred_modality = ?, updated_at = ? WHERE account_id = ?", (payload.get('goal') or 'fat-loss', payload.get('level') or 'intermediate', payload.get('modality') or 'strength', now, account['id']))
    if command_name in {'create_quote', 'approve_quote', 'activate_plan'}:
        program_name = str(payload.get('program_name') or 'transformation-12w')
        status = 'accepted' if command_name in {'approve_quote', 'activate_plan'} else 'recommended'
        _upsert(conn, "INSERT INTO fitness_program_recommendations (id, organization_id, account_id, member_id, program_name, recommendation_status, sessions_per_week, package_type, notes_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account_id, program_name) DO UPDATE SET recommendation_status = excluded.recommendation_status, sessions_per_week = excluded.sessions_per_week, package_type = excluded.package_type, notes_json = excluded.notes_json, updated_at = excluded.updated_at", (new_id('fpr'), account['organization_id'], account['id'], member['id'], program_name, status, int(payload.get('sessions_per_week') or 3), str(payload.get('package_type') or 'membership'), to_json({'amount': payload.get('amount')}), now, now))
        _upsert(conn, "UPDATE fitness_members SET member_status = ?, suggested_program = ?, coach_match = ?, updated_at = ? WHERE account_id = ?", ('active' if status == 'accepted' else 'trial', program_name, payload.get('coach_match') or 'coach-primary', now, account['id']))
    if command_name in {'confirm_booking', 'collect_payment', 'reactivate_customer'}:
        attendance_7 = 1 if command_name == 'confirm_booking' else 2
        attendance_30 = 4 if command_name == 'collect_payment' else 2
        risk = 'low' if command_name in {'collect_payment', 'reactivate_customer'} else 'medium'
        _upsert(conn, "UPDATE fitness_attendance_risk SET attendance_last_7d = ?, attendance_last_30d = ?, risk_level = ?, churn_signals_json = ?, updated_at = ? WHERE account_id = ?", (attendance_7, attendance_30, risk, to_json([] if risk == 'low' else ['low_attendance']), now, account['id']))
    if command_name in {'schedule_maintenance'}:
        _upsert(conn, "INSERT INTO fitness_freezes (id, organization_id, account_id, member_id, freeze_status, reason, start_at, end_at, created_at, updated_at) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)", (new_id('ffr'), account['organization_id'], account['id'], member['id'], payload.get('reason') or 'travel', payload.get('start_at') or now, payload.get('end_at') or now, now, now))


def _bootstrap_auto_service(conn: Any, account: dict[str, Any]) -> None:
    now = utcnow_iso()
    vehicle_id = f"veh-{account['id']}"
    order_id = f"aso-{account['id']}"
    _upsert(conn, "INSERT INTO auto_service_vehicles (id, organization_id, account_id, contact_id, vin, plate, make_model, vehicle_year, odometer_km, vehicle_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'intake', ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (vehicle_id, account['organization_id'], account['id'], account.get('contact_id'), account.get('metadata', {}).get('vin') or 'VIN-DEMO', account.get('metadata', {}).get('plate') or 'ABC123', account.get('metadata', {}).get('make_model') or 'Sedan Demo', int(account.get('metadata', {}).get('vehicle_year') or 2022), now, now))
    _upsert(conn, "INSERT INTO auto_service_orders (id, organization_id, account_id, vehicle_id, order_status, service_reason, quoted_amount, approved_amount, promised_delivery_at, created_at, updated_at) VALUES (?, ?, ?, ?, 'diagnostic', 'inspeccion general', 0, 0, NULL, ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (order_id, account['organization_id'], account['id'], vehicle_id, now, now))
    _upsert(conn, "INSERT INTO auto_service_inspections (id, organization_id, account_id, order_id, inspection_status, findings_json, diagnostic_summary, created_at, updated_at) VALUES (?, ?, ?, ?, 'open', '[]', 'pendiente', ?, ?) ON CONFLICT(account_id, order_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('ains'), account['organization_id'], account['id'], order_id, now, now))
    _upsert(conn, "INSERT INTO auto_service_maintenance_cycles (id, organization_id, account_id, vehicle_id, cycle_status, next_service_at, trigger_kind, trigger_value, updated_at) VALUES (?, ?, ?, ?, 'pending', NULL, 'kilometraje', '5000', ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('amc'), account['organization_id'], account['id'], vehicle_id, now))
    _upsert(conn, "INSERT INTO auto_service_approvals (id, organization_id, account_id, order_id, approval_status, approved_by, amount, created_at, updated_at) VALUES (?, ?, ?, ?, 'pending', 'customer', 0, ?, ?) ON CONFLICT(account_id, order_id, approval_status) DO UPDATE SET updated_at = excluded.updated_at", (new_id('aapp'), account['organization_id'], account['id'], order_id, now, now))


def _apply_auto_service_command(conn: Any, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> None:
    now = utcnow_iso()
    order = _fetch_row(conn, "SELECT * FROM auto_service_orders WHERE account_id = ?", (account['id'],))
    vehicle = _fetch_row(conn, "SELECT * FROM auto_service_vehicles WHERE account_id = ?", (account['id'],))
    if not order or not vehicle:
        return
    if command_name in {'capture_intent', 'qualify_record'}:
        findings = payload.get('findings') or ['battery', 'brakes']
        _upsert(conn, "INSERT INTO auto_service_inspections (id, organization_id, account_id, order_id, inspection_status, findings_json, diagnostic_summary, created_at, updated_at) VALUES (?, ?, ?, ?, 'completed', ?, ?, ?, ?) ON CONFLICT(account_id, order_id) DO UPDATE SET inspection_status = excluded.inspection_status, findings_json = excluded.findings_json, diagnostic_summary = excluded.diagnostic_summary, updated_at = excluded.updated_at", (new_id('ains'), account['organization_id'], account['id'], order['id'], to_json(findings), payload.get('diagnostic_summary') or 'diagnostico preliminar completado', now, now))
        _upsert(conn, "UPDATE auto_service_orders SET order_status = 'quoted', service_reason = ?, updated_at = ? WHERE account_id = ?", (payload.get('service_reason') or 'mantenimiento preventivo', now, account['id']))
    if command_name in {'create_quote', 'approve_quote', 'start_fulfillment'}:
        quoted = float(payload.get('amount') or 1000)
        approved = quoted if command_name in {'approve_quote', 'start_fulfillment'} else 0
        status = 'approved' if command_name == 'approve_quote' else ('in_service' if command_name == 'start_fulfillment' else 'quoted')
        _upsert(conn, "UPDATE auto_service_orders SET order_status = ?, quoted_amount = ?, approved_amount = ?, promised_delivery_at = ?, updated_at = ? WHERE account_id = ?", (status, quoted, approved, payload.get('promised_delivery_at') or now, now, account['id']))
    if command_name in {'approve_quote'}:
        _upsert(conn, "INSERT INTO auto_service_approvals (id, organization_id, account_id, order_id, approval_status, approved_by, amount, created_at, updated_at) VALUES (?, ?, ?, ?, 'approved', ?, ?, ?, ?) ON CONFLICT(account_id, order_id, approval_status) DO UPDATE SET approved_by = excluded.approved_by, amount = excluded.amount, updated_at = excluded.updated_at", (new_id('aapp'), account['organization_id'], account['id'], order['id'], payload.get('approved_by') or 'customer', float(payload.get('amount') or 1000), now, now))
    if command_name in {'schedule_maintenance', 'close_fulfillment'}:
        _upsert(conn, "UPDATE auto_service_maintenance_cycles SET cycle_status = ?, next_service_at = ?, trigger_kind = ?, trigger_value = ?, updated_at = ? WHERE account_id = ?", ('scheduled', payload.get('next_service_at') or now, payload.get('trigger_kind') or 'time', str(payload.get('trigger_value') or '90d'), now, account['id']))
        _upsert(conn, "UPDATE auto_service_vehicles SET vehicle_status = ?, odometer_km = ?, updated_at = ? WHERE account_id = ?", ('ready' if command_name == 'close_fulfillment' else 'scheduled', int(payload.get('odometer_km') or vehicle.get('odometer_km') or 0), now, account['id']))


def _bootstrap_vet(conn: Any, account: dict[str, Any]) -> None:
    now = utcnow_iso()
    guardian_id = f"vg-{account['id']}"
    pet_id = f"vp-{account['id']}"
    _upsert(conn, "INSERT INTO vet_guardians (id, organization_id, account_id, contact_id, guardian_name, household_size, preferred_channel, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, 'whatsapp', ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (guardian_id, account['organization_id'], account['id'], account.get('contact_id'), account.get('metadata', {}).get('guardian_name') or 'Tutor principal', now, now))
    _upsert(conn, "INSERT INTO vet_pets (id, organization_id, account_id, guardian_id, pet_name, species, breed, age_months, weight_kg, pet_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 12, 10, 'registered', ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (pet_id, account['organization_id'], account['id'], guardian_id, account.get('metadata', {}).get('pet_name') or 'Luna', account.get('metadata', {}).get('species') or 'canine', account.get('metadata', {}).get('breed') or 'mestizo', now, now))
    _upsert(conn, "INSERT INTO vet_preventive_plans (id, organization_id, account_id, pet_id, plan_status, plan_name, next_review_at, grooming_frequency_days, updated_at) VALUES (?, ?, ?, ?, 'draft', 'preventive-care', NULL, 30, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('vpp'), account['organization_id'], account['id'], pet_id, now))
    _upsert(conn, "INSERT INTO vet_vaccine_schedules (id, organization_id, account_id, pet_id, vaccine_name, schedule_status, due_at, completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, 'basica', 'pending', ?, NULL, ?, ?) ON CONFLICT(account_id, vaccine_name) DO UPDATE SET updated_at = excluded.updated_at", (new_id('vvac'), account['organization_id'], account['id'], pet_id, now, now, now))


def _apply_vet_command(conn: Any, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> None:
    now = utcnow_iso()
    pet = _fetch_row(conn, "SELECT * FROM vet_pets WHERE account_id = ?", (account['id'],))
    if not pet:
        return
    if command_name in {'activate_plan', 'schedule_recurrence'}:
        _upsert(conn, "UPDATE vet_preventive_plans SET plan_status = 'active', next_review_at = ?, grooming_frequency_days = ?, updated_at = ? WHERE account_id = ?", (payload.get('next_review_at') or now, int(payload.get('grooming_frequency_days') or 30), now, account['id']))
        _upsert(conn, "INSERT INTO vet_vaccine_schedules (id, organization_id, account_id, pet_id, vaccine_name, schedule_status, due_at, completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'scheduled', ?, NULL, ?, ?) ON CONFLICT(account_id, vaccine_name) DO UPDATE SET schedule_status = excluded.schedule_status, due_at = excluded.due_at, updated_at = excluded.updated_at", (new_id('vvac'), account['organization_id'], account['id'], pet['id'], payload.get('vaccine_name') or 'triple_felina', payload.get('due_at') or now, now, now))
    if command_name in {'confirm_booking', 'close_fulfillment'}:
        _upsert(conn, "INSERT INTO vet_service_history (id, organization_id, account_id, pet_id, service_type, service_status, performed_at, notes_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (new_id('vsh'), account['organization_id'], account['id'], pet['id'], payload.get('service_type') or ('vaccination' if command_name == 'close_fulfillment' else 'consultation'), 'completed', payload.get('performed_at') or now, to_json({'notes': payload.get('notes') or ''}), now))
        _upsert(conn, "UPDATE vet_pets SET pet_status = ?, updated_at = ? WHERE account_id = ?", ('active_care', now, account['id']))


def _bootstrap_aesthetic(conn: Any, account: dict[str, Any]) -> None:
    now = utcnow_iso()
    patient_id = f"aes-{account['id']}"
    _upsert(conn, "INSERT INTO aesthetic_patients (id, organization_id, account_id, contact_id, patient_status, primary_goal, eligibility_status, created_at, updated_at) VALUES (?, ?, ?, ?, 'lead', 'skin-quality', 'pending', ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (patient_id, account['organization_id'], account['id'], account.get('contact_id'), now, now))
    _upsert(conn, "INSERT INTO aesthetic_treatment_plans (id, organization_id, account_id, patient_id, treatment_name, plan_status, contraindications_json, maintenance_interval_days, total_amount, created_at, updated_at) VALUES (?, ?, ?, ?, 'skin-reset', 'draft', '[]', 30, 0, ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('atp'), account['organization_id'], account['id'], patient_id, now, now))
    _upsert(conn, "INSERT INTO aesthetic_session_packages (id, organization_id, account_id, patient_id, package_status, session_count, sessions_completed, total_amount, created_at, updated_at) VALUES (?, ?, ?, ?, 'proposed', 1, 0, 0, ?, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('asp'), account['organization_id'], account['id'], patient_id, now, now))
    _upsert(conn, "INSERT INTO aesthetic_aftercare_cycles (id, organization_id, account_id, patient_id, cycle_status, aftercare_notes_json, next_maintenance_at, updated_at) VALUES (?, ?, ?, ?, 'pending', '[]', NULL, ?) ON CONFLICT(account_id) DO UPDATE SET updated_at = excluded.updated_at", (new_id('aac'), account['organization_id'], account['id'], patient_id, now))
    _upsert(conn, "INSERT INTO aesthetic_consents (id, organization_id, account_id, patient_id, consent_name, consent_status, signed_at, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, 'consentimiento-estetico', 'pending', NULL, '{}', ?, ?) ON CONFLICT(account_id, consent_name) DO UPDATE SET updated_at = excluded.updated_at", (new_id('acon'), account['organization_id'], account['id'], patient_id, now, now))


def _apply_aesthetic_command(conn: Any, account: dict[str, Any], command_name: str, payload: dict[str, Any]) -> None:
    now = utcnow_iso()
    patient = _fetch_row(conn, "SELECT * FROM aesthetic_patients WHERE account_id = ?", (account['id'],))
    if not patient:
        return
    if command_name in {'mark_eligibility', 'qualify_record'}:
        _upsert(conn, "UPDATE aesthetic_patients SET primary_goal = ?, eligibility_status = ?, updated_at = ? WHERE account_id = ?", (payload.get('primary_goal') or 'body-contouring', payload.get('eligibility_status') or 'eligible', now, account['id']))
    if command_name in {'create_quote', 'approve_quote', 'start_case'}:
        _upsert(conn, "INSERT INTO aesthetic_treatment_plans (id, organization_id, account_id, patient_id, treatment_name, plan_status, contraindications_json, maintenance_interval_days, total_amount, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account_id) DO UPDATE SET treatment_name = excluded.treatment_name, plan_status = excluded.plan_status, contraindications_json = excluded.contraindications_json, maintenance_interval_days = excluded.maintenance_interval_days, total_amount = excluded.total_amount, updated_at = excluded.updated_at", (new_id('atp'), account['organization_id'], account['id'], patient['id'], payload.get('treatment_name') or 'laser-package', 'active' if command_name == 'start_case' else ('accepted' if command_name == 'approve_quote' else 'proposed'), to_json(payload.get('contraindications') or []), int(payload.get('maintenance_interval_days') or 30), float(payload.get('amount') or 1000), now, now))
    if command_name in {'sell_session_package', 'collect_payment'}:
        _upsert(conn, "INSERT INTO aesthetic_session_packages (id, organization_id, account_id, patient_id, package_status, session_count, sessions_completed, total_amount, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account_id) DO UPDATE SET package_status = excluded.package_status, session_count = excluded.session_count, sessions_completed = excluded.sessions_completed, total_amount = excluded.total_amount, updated_at = excluded.updated_at", (new_id('asp'), account['organization_id'], account['id'], patient['id'], 'active', int(payload.get('session_count') or 6), 1 if command_name == 'collect_payment' else 0, float(payload.get('amount') or 1000), now, now))
    docs = payload.get('documents') or []
    for item in docs:
        name = item if isinstance(item, str) else str(item.get('name') or 'consentimiento-estetico')
        status = 'signed' if (isinstance(item, dict) and item.get('status') == 'signed') else 'pending'
        _upsert(conn, "INSERT INTO aesthetic_consents (id, organization_id, account_id, patient_id, consent_name, consent_status, signed_at, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account_id, consent_name) DO UPDATE SET consent_status = excluded.consent_status, signed_at = excluded.signed_at, payload_json = excluded.payload_json, updated_at = excluded.updated_at", (new_id('acon'), account['organization_id'], account['id'], patient['id'], name, status, now if status == 'signed' else None, to_json(item if isinstance(item, dict) else {'name': name}), now, now))
    if command_name in {'deliver_aftercare', 'schedule_recurrence', 'close_fulfillment'}:
        _upsert(conn, "UPDATE aesthetic_aftercare_cycles SET cycle_status = ?, aftercare_notes_json = ?, next_maintenance_at = ?, updated_at = ? WHERE account_id = ?", ('active', to_json(payload.get('aftercare_notes') or ['spf', 'hydration']), payload.get('next_maintenance_at') or now, now, account['id']))
