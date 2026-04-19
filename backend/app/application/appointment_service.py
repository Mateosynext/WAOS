from __future__ import annotations

from fastapi import HTTPException

from ..db import fetch_all, fetch_one
from ..security import accessible_org_ids, ensure_org_access
from ..domains.appointments import (
    appointment_dashboard,
    cancel_appointment,
    confirm_appointment,
    create_appointment_bundle,
    mark_appointment_no_show,
    reschedule_appointment,
    send_appointment_followup,
)
from .support import org_filter_sql, require_permission
from .uow import UnitOfWork
from ..utils import new_id, utcnow_iso


class AppointmentService:
    def list(self, uow: UnitOfWork, *, user: dict, organization_id: str | None) -> list[dict]:
        conn = uow.conn
        if organization_id:
            ensure_org_access(user, organization_id)
            require_permission(user, organization_id, "appointment.manage")
        where_sql, params = org_filter_sql(user, organization_id, "organization_id")
        return fetch_all(conn, f"SELECT * FROM appointments {where_sql} ORDER BY scheduled_for ASC", params)

    def create(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "appointment.manage")
        return create_appointment_bundle(uow.conn, actor_user=user, **payload.model_dump())

    def confirm(self, uow: UnitOfWork, *, user: dict, appointment_id: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return confirm_appointment(uow.conn, appointment["id"], actor_user=user)

    def reschedule(self, uow: UnitOfWork, *, user: dict, appointment_id: str, scheduled_for: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return reschedule_appointment(uow.conn, appointment["id"], scheduled_for=scheduled_for, actor_user=user)

    def cancel(self, uow: UnitOfWork, *, user: dict, appointment_id: str, reason: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return cancel_appointment(uow.conn, appointment["id"], reason=reason, actor_user=user)

    def no_show(self, uow: UnitOfWork, *, user: dict, appointment_id: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return mark_appointment_no_show(uow.conn, appointment["id"], actor_user=user)

    def follow_up(self, uow: UnitOfWork, *, user: dict, appointment_id: str) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        return send_appointment_followup(uow.conn, appointment["id"], actor_user=user)

    def reminder_preferences(self, uow: UnitOfWork, *, user: dict, organization_id: str | None) -> dict:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, "appointment.manage")
        row = fetch_one(uow.conn, "SELECT * FROM agenda_reminder_preferences WHERE organization_id = ?", (selected_org,))
        if not row:
            return {
                "organization_id": selected_org,
                "tone": "amable",
                "hours_before": 24,
                "last_hours": 2,
                "count": 2,
                "updated_at": None,
            }
        return row

    def save_reminder_preferences(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "appointment.manage")
        now = utcnow_iso()
        existing = fetch_one(uow.conn, "SELECT id FROM agenda_reminder_preferences WHERE organization_id = ?", (payload.organization_id,))
        if existing:
            uow.conn.execute(
                """
                UPDATE agenda_reminder_preferences
                SET tone = ?, hours_before = ?, last_hours = ?, count = ?, updated_by_user_id = ?, updated_at = ?
                WHERE organization_id = ?
                """,
                (payload.tone, payload.hours_before, payload.last_hours, payload.count, user["id"], now, payload.organization_id),
            )
        else:
            uow.conn.execute(
                """
                INSERT INTO agenda_reminder_preferences
                (id, organization_id, tone, hours_before, last_hours, count, updated_by_user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id("arp"), payload.organization_id, payload.tone, payload.hours_before, payload.last_hours, payload.count, user["id"], now, now),
            )
        return self.reminder_preferences(uow, user=user, organization_id=payload.organization_id)

    def list_blocked_slots(self, uow: UnitOfWork, *, user: dict, organization_id: str | None) -> list[dict]:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, "appointment.manage")
        return fetch_all(
            uow.conn,
            "SELECT * FROM agenda_blocked_slots WHERE organization_id = ? ORDER BY start_at ASC, created_at DESC LIMIT 200",
            (selected_org,),
        )

    def create_blocked_slot(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, "appointment.manage")
        if str(payload.end_at) <= str(payload.start_at):
            raise HTTPException(status_code=400, detail="blocked_slot_invalid_range")
        overlapping = fetch_one(
            uow.conn,
            """
            SELECT id FROM agenda_blocked_slots
            WHERE organization_id = ?
              AND COALESCE(bot_id, '') = COALESCE(?, '')
              AND start_at < ?
              AND end_at > ?
            LIMIT 1
            """,
            (payload.organization_id, payload.bot_id, payload.end_at, payload.start_at),
        )
        if overlapping:
            raise HTTPException(status_code=409, detail="blocked_slot_overlaps_existing")
        now = utcnow_iso()
        slot_id = new_id("abk")
        uow.conn.execute(
            """
            INSERT INTO agenda_blocked_slots
            (id, organization_id, bot_id, start_at, end_at, reason, created_by_user_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (slot_id, payload.organization_id, payload.bot_id, payload.start_at, payload.end_at, payload.reason, user["id"], now, now),
        )
        return fetch_one(uow.conn, "SELECT * FROM agenda_blocked_slots WHERE id = ?", (slot_id,)) or {}

    def delete_blocked_slot(self, uow: UnitOfWork, *, user: dict, slot_id: str) -> dict:
        slot = fetch_one(uow.conn, "SELECT * FROM agenda_blocked_slots WHERE id = ?", (slot_id,))
        if not slot:
            raise HTTPException(status_code=404, detail="blocked_slot_not_found")
        ensure_org_access(user, slot["organization_id"])
        require_permission(user, slot["organization_id"], "appointment.manage")
        uow.conn.execute("DELETE FROM agenda_blocked_slots WHERE id = ?", (slot_id,))
        return {"ok": True, "id": slot_id}

    def agenda_overview(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> dict:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail="organization_id is required")
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, "appointment.manage")
        return appointment_dashboard(uow.conn, selected_org, bot_id)

    def list_resources(self, uow: UnitOfWork, *, user: dict, organization_id: str | None) -> list[dict]:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail='organization_id is required')
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, 'appointment.manage')
        return fetch_all(uow.conn, 'SELECT * FROM agenda_resources WHERE organization_id = ? ORDER BY updated_at DESC, name ASC', (selected_org,))

    def create_resource(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, 'appointment.manage')
        now = utcnow_iso()
        resource_id = new_id('ares')
        uow.conn.execute(
            """
            INSERT INTO agenda_resources (id, organization_id, bot_id, name, resource_type, branch, status, metadata_json, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', '{}', ?, ?, ?)
            """,
            (resource_id, payload.organization_id, payload.bot_id, payload.name, payload.resource_type, payload.branch, user['id'], now, now),
        )
        return fetch_one(uow.conn, 'SELECT * FROM agenda_resources WHERE id = ?', (resource_id,)) or {}

    def list_capacity_rules(self, uow: UnitOfWork, *, user: dict, organization_id: str | None) -> list[dict]:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail='organization_id is required')
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, 'appointment.manage')
        return fetch_all(
            uow.conn,
            """
            SELECT r.*, ar.name AS resource_name, ar.resource_type
            FROM agenda_resource_capacity_rules r
            JOIN agenda_resources ar ON ar.id = r.resource_id
            WHERE r.organization_id = ?
            ORDER BY r.day_of_week ASC, r.start_time ASC
            """,
            (selected_org,),
        )

    def create_capacity_rule(self, uow: UnitOfWork, *, user: dict, payload) -> dict:
        ensure_org_access(user, payload.organization_id)
        require_permission(user, payload.organization_id, 'appointment.manage')
        resource = fetch_one(uow.conn, 'SELECT * FROM agenda_resources WHERE id = ?', (payload.resource_id,))
        if not resource or resource['organization_id'] != payload.organization_id:
            raise HTTPException(status_code=404, detail='resource_not_found')
        if str(payload.end_time) <= str(payload.start_time):
            raise HTTPException(status_code=400, detail='capacity_rule_invalid_range')
        overlapping = fetch_one(
            uow.conn,
            """
            SELECT id FROM agenda_resource_capacity_rules
            WHERE resource_id = ? AND day_of_week = ? AND status = 'active'
              AND start_time < ? AND end_time > ?
            LIMIT 1
            """,
            (payload.resource_id, payload.day_of_week, payload.end_time, payload.start_time),
        )
        if overlapping:
            raise HTTPException(status_code=409, detail='capacity_rule_overlaps_existing')
        now = utcnow_iso()
        rule_id = new_id('acap')
        uow.conn.execute(
            """
            INSERT INTO agenda_resource_capacity_rules (id, organization_id, bot_id, resource_id, day_of_week, start_time, end_time, slot_capacity, status, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (rule_id, payload.organization_id, payload.bot_id, payload.resource_id, payload.day_of_week, payload.start_time, payload.end_time, payload.slot_capacity, user['id'], now, now),
        )
        return fetch_one(uow.conn, 'SELECT * FROM agenda_resource_capacity_rules WHERE id = ?', (rule_id,)) or {}

    def assign_resource(self, uow: UnitOfWork, *, user: dict, appointment_id: str, payload) -> dict:
        appointment = self._get_accessible_appointment(uow, user=user, appointment_id=appointment_id)
        resource = fetch_one(uow.conn, 'SELECT * FROM agenda_resources WHERE id = ?', (payload.resource_id,))
        if not resource or resource['organization_id'] != appointment['organization_id']:
            raise HTTPException(status_code=404, detail='resource_not_found')
        now = utcnow_iso()
        existing = fetch_one(uow.conn, 'SELECT * FROM appointment_resource_assignments WHERE appointment_id = ?', (appointment_id,))
        if existing:
            uow.conn.execute('UPDATE appointment_resource_assignments SET resource_id = ?, assigned_by = ?, note = ?, updated_at = ? WHERE appointment_id = ?', (payload.resource_id, user['id'], payload.note, now, appointment_id))
        else:
            uow.conn.execute(
                """
                INSERT INTO appointment_resource_assignments (id, organization_id, appointment_id, resource_id, assigned_by, note, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id('apar'), appointment['organization_id'], appointment_id, payload.resource_id, user['id'], payload.note, now, now),
            )
        return fetch_one(
            uow.conn,
            """
            SELECT ara.*, ar.name AS resource_name, ar.resource_type
            FROM appointment_resource_assignments ara
            JOIN agenda_resources ar ON ar.id = ara.resource_id
            WHERE ara.appointment_id = ?
            LIMIT 1
            """,
            (appointment_id,),
        ) or {}

    def capacity_overview(self, uow: UnitOfWork, *, user: dict, organization_id: str | None, bot_id: str | None) -> dict:
        selected_org = organization_id or (accessible_org_ids(user)[0] if accessible_org_ids(user) else None)
        if not selected_org:
            raise HTTPException(status_code=400, detail='organization_id is required')
        ensure_org_access(user, selected_org)
        require_permission(user, selected_org, 'appointment.manage')
        params = [selected_org]
        bot_filter = ''
        if bot_id:
            bot_filter = ' AND COALESCE(ar.bot_id, "") = COALESCE(?, "") '
            params.append(bot_id)
        resources = fetch_all(uow.conn, f'SELECT * FROM agenda_resources ar WHERE ar.organization_id = ? {bot_filter} ORDER BY ar.name ASC', params)
        params_rules = [selected_org]
        rule_bot_filter = ''
        if bot_id:
            rule_bot_filter = ' AND COALESCE(r.bot_id, "") = COALESCE(?, "") '
            params_rules.append(bot_id)
        rules_sql = f"SELECT r.*, ar.name AS resource_name FROM agenda_resource_capacity_rules r JOIN agenda_resources ar ON ar.id = r.resource_id WHERE r.organization_id = ? {rule_bot_filter} AND r.status = 'active' ORDER BY r.day_of_week ASC, r.start_time ASC"
        rules = fetch_all(uow.conn, rules_sql, params_rules)
        appt_params = [selected_org]
        appt_filter = ''
        if bot_id:
            appt_filter = ' AND a.bot_id = ? '
            appt_params.append(bot_id)
        upcoming = fetch_all(uow.conn, f"SELECT * FROM appointments a WHERE a.organization_id = ? {appt_filter} AND a.status NOT IN ('cancelled','no_show') ORDER BY a.scheduled_for ASC", appt_params)
        assignments = fetch_all(uow.conn, 'SELECT * FROM appointment_resource_assignments WHERE organization_id = ?', (selected_org,))
        assigned_by_appt = {row['appointment_id']: row for row in assignments}

        def window_slots(start: str, end: str, slot_capacity: int) -> int:
            try:
                start_hour, start_min = [int(part) for part in str(start).split(':', 1)]
                end_hour, end_min = [int(part) for part in str(end).split(':', 1)]
                minutes = max(0, (end_hour * 60 + end_min) - (start_hour * 60 + start_min))
                return max(0, minutes // 30) * max(1, int(slot_capacity or 1))
            except Exception:
                return 0

        declared_weekly_slots = sum(window_slots(row.get('start_time'), row.get('end_time'), row.get('slot_capacity')) for row in rules)
        resource_rows = []
        for resource in resources:
            resource_rules = [row for row in rules if row.get('resource_id') == resource['id']]
            resource_assignments = [row for row in assignments if row.get('resource_id') == resource['id']]
            resource_rows.append({
                'resource_id': resource['id'],
                'name': resource['name'],
                'resource_type': resource.get('resource_type'),
                'branch': resource.get('branch'),
                'weekly_slots': sum(window_slots(row.get('start_time'), row.get('end_time'), row.get('slot_capacity')) for row in resource_rules),
                'rules_count': len(resource_rules),
                'assigned_appointments': len(resource_assignments),
            })
        return {
            'organization_id': selected_org,
            'bot_id': bot_id,
            'summary': {
                'resources': len(resources),
                'capacity_rules': len(rules),
                'declared_weekly_slots': declared_weekly_slots,
                'upcoming_appointments': len(upcoming),
                'assigned_upcoming_appointments': len([row for row in upcoming if row['id'] in assigned_by_appt]),
                'unassigned_upcoming_appointments': len([row for row in upcoming if row['id'] not in assigned_by_appt]),
            },
            'resources': resource_rows,
            'rules': rules[:40],
            'upcoming': [{**row, 'resource_id': (assigned_by_appt.get(row['id']) or {}).get('resource_id')} for row in upcoming[:40]],
        }

    def _get_accessible_appointment(self, uow: UnitOfWork, *, user: dict, appointment_id: str) -> dict:
        appointment = fetch_one(uow.conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        if not appointment:
            raise HTTPException(status_code=404, detail="appointment_not_found")
        ensure_org_access(user, appointment["organization_id"])
        require_permission(user, appointment["organization_id"], "appointment.manage")
        return appointment
