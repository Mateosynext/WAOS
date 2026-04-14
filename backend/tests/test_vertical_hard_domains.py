from __future__ import annotations

from backend.app.db import execute, get_connection, init_db
from backend.app.utils import new_id, utcnow_iso
from backend.app.vertical_transactions import vertical_transaction_service

HARD_VERTICALS = {
    'fitness': ('members', 'goal_profiles', 'program_recommendations', 'attendance_risk'),
    'dental': ('patients', 'cases', 'treatment_plans', 'documents', 'recalls'),
    'aesthetic': ('patients', 'treatment_plans', 'session_packages', 'aftercare_cycles', 'consents'),
    'vet': ('guardians', 'pets', 'preventive_plans', 'vaccine_schedules', 'service_history'),
    'auto-service': ('vehicles', 'orders', 'inspections', 'maintenance_cycles', 'approvals'),
}


def _seed_actor_and_org() -> tuple[dict, str]:
    organization_id = new_id('org')
    user_id = new_id('user')
    now = utcnow_iso()
    with get_connection() as conn:
        execute(conn, "INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)", (user_id, f'{user_id}@example.com', 'Hard Domain User', 'not-used', 'super_admin', now, now))
        execute(conn, "INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES (?, ?, ?, 'active', 'America/Mexico_City', NULL, '{}', ?, ?)", (organization_id, 'Hard Domain Org', f'org-{organization_id[-8:]}', now, now))
    return ({'id': user_id, 'global_role': 'super_admin', 'organization_ids': [organization_id]}, organization_id)


def test_hard_verticals_materialize_domain_records() -> None:
    init_db()
    actor, organization_id = _seed_actor_and_org()
    with get_connection() as conn:
        for vertical_id, expected_keys in HARD_VERTICALS.items():
            account = vertical_transaction_service.create_account(
                conn,
                organization_id=organization_id,
                vertical_id=vertical_id,
                actor_user=actor,
                external_reference=f'{vertical_id}-hard-domain',
                metadata={'source': 'pytest', 'patient_name': 'Demo', 'pet_name': 'Milo'},
            )
            result = vertical_transaction_service.execute_playbook(
                conn,
                organization_id=organization_id,
                account_id=account['id'],
                actor_user=actor,
            )
            snapshot = result['account']['domain_snapshot']
            assert snapshot['hard_domain_enabled'] is True
            for key in expected_keys:
                assert key in snapshot['records']
                assert snapshot['records'][key], f'{vertical_id} missing {key}'


def test_non_hard_verticals_remain_on_common_transaction_core() -> None:
    init_db()
    actor, organization_id = _seed_actor_and_org()
    with get_connection() as conn:
        account = vertical_transaction_service.create_account(
            conn,
            organization_id=organization_id,
            vertical_id='real-estate',
            actor_user=actor,
        )
        assert account['domain_snapshot']['hard_domain_enabled'] is False
        assert account['domain_snapshot']['records'] == {}
