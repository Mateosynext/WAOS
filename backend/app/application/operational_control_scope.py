from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from ..db import execute, fetch_all, fetch_one, table_exists
from ..repositories.audit import create_audit_log
from ..repositories.bots import get_bot
from ..repositories.conversations import create_message
from ..security import ensure_bot_access
from ..utils import add_minutes, new_id, parse_iso, to_json, utcnow, utcnow_iso
from .operational_control_policy import needs_second_approval, requires_confirmation, risk_level
from .operational_control_presenters import (
    serialize_alert,
    serialize_appointment,
    serialize_authorized_number,
    serialize_command,
    serialize_override,
    serialize_scheduled_action,
)

class OperationalControlScopeMixin:
    def _select_target_appointments(self, conn, organization_id: str, bot_id: str, entities: dict) -> list[dict]:
        scope = entities.get('scope_type') or ((entities.get('scope') or {}).get('scope_type')) or 'date_range'
        scope_details = entities.get('scope') or {}
        now = utcnow_iso()
        if scope == 'next_appointment':
            rows = fetch_all(conn, "SELECT * FROM appointments WHERE organization_id = ? AND bot_id = ? AND status IN ('scheduled','confirmed') AND scheduled_for >= ? ORDER BY scheduled_for ASC LIMIT 20", (organization_id, bot_id, now))
            for row in rows:
                if self._appointment_matches_scope(conn, row, scope_details):
                    return [row]
            return []
        if scope == 'today_appointments':
            start_at, end_at = self._date_window('today')
        else:
            start_at = entities.get('start_at') or entities.get('date_start') or self._date_window('today')[0]
            end_at = entities.get('end_at') or entities.get('date_end') or self._date_window('today')[1]
        rows = fetch_all(conn, "SELECT * FROM appointments WHERE organization_id = ? AND bot_id = ? AND status IN ('scheduled','confirmed') AND scheduled_for >= ? AND scheduled_for <= ? ORDER BY scheduled_for ASC", (organization_id, bot_id, start_at, end_at))
        return [row for row in rows if self._appointment_matches_scope(conn, row, scope_details)]

    def _structured_reschedule_entities(self, payload) -> dict:
        start_at, end_at = self._structured_scope_window(payload.scope_day, payload.target_date)
        return {
            'scope_type': 'date_range',
            'scope': {'scope_type': 'date_range'},
            'start_at': start_at,
            'end_at': end_at,
            'strategy': payload.strategy,
            'delay_minutes': int(payload.delay_minutes or 0),
            'target_date': payload.target_date,
            'target_start_time': payload.target_start_time,
            'target_end_time': payload.target_end_time,
            'notify_clients': bool(payload.notify_clients),
        }

    def _plan_reschedule(self, conn, organization_id: str, bot_id: str, entities: dict) -> list[dict]:
        appointments = self._select_target_appointments(conn, organization_id, bot_id, entities)
        strategy = entities.get('strategy') or 'next_available_window'
        planned: list[dict] = []
        reserved: set[str] = set()
        for appointment in appointments:
            old_value = appointment.get('scheduled_for')
            duration = int(appointment.get('duration_minutes') or 30)
            if strategy == 'shift_minutes' and int(entities.get('delay_minutes') or 0) > 0:
                candidate = add_minutes(old_value, int(entities.get('delay_minutes') or 0))
                slot = self._find_next_available_slot(conn, organization_id, bot_id, candidate, duration_minutes=duration, entities=entities, reserved=reserved, target_date=None, window=None)
            else:
                target_date = entities.get('target_date')
                if not target_date:
                    start_dt = parse_iso(old_value) or utcnow()
                    target_date = start_dt.date().isoformat()
                window = (entities.get('target_start_time') or '09:00', entities.get('target_end_time') or '18:00')
                slot = self._find_next_available_slot(conn, organization_id, bot_id, old_value, duration_minutes=duration, entities=entities, reserved=reserved, target_date=target_date, window=window)
            if slot:
                reserved.add(slot)
                planned.append({"appointment_id": appointment['id'], "old_scheduled_for": old_value, "new_scheduled_for": slot, "status": 'planned'})
            else:
                planned.append({"appointment_id": appointment['id'], "old_scheduled_for": old_value, "new_scheduled_for": None, "status": 'unresolved', "reason": 'no_slot_found'})
        return planned

    def _find_next_available_slot(self, conn, organization_id: str, bot_id: str, base_time: str, *, duration_minutes: int, entities: dict, reserved: set[str], target_date: str | None, window: tuple[str, str] | None) -> str | None:
        base_dt = parse_iso(base_time) or utcnow()
        if target_date:
            year, month, day = [int(part) for part in target_date.split('-')]
            start_hour, start_min = [int(part) for part in (window[0] if window else '09:00').split(':')]
            end_hour, end_min = [int(part) for part in (window[1] if window else '18:00').split(':')]
            candidate = dt.datetime(year, month, day, start_hour, start_min, tzinfo=dt.timezone.utc)
            latest = dt.datetime(year, month, day, end_hour, end_min, tzinfo=dt.timezone.utc)
        else:
            candidate = base_dt
            latest = candidate + dt.timedelta(hours=12)
        while candidate <= latest:
            iso = candidate.isoformat().replace('+00:00', 'Z')
            if iso not in reserved and self._slot_is_available(conn, organization_id, bot_id, iso, duration_minutes=duration_minutes):
                return iso
            candidate = candidate + dt.timedelta(minutes=30)
        return None

    def _slot_is_available(self, conn, organization_id: str, bot_id: str, slot_iso: str, *, duration_minutes: int) -> bool:
        slot_dt = parse_iso(slot_iso)
        if not slot_dt:
            return False
        end_dt = slot_dt + dt.timedelta(minutes=duration_minutes)
        blocking = fetch_one(conn, "SELECT id FROM availability_overrides WHERE organization_id = ? AND bot_id = ? AND status = 'active' AND override_type IN ('block_slot','block_day','vacation') AND start_at < ? AND end_at > ? LIMIT 1", (organization_id, bot_id, end_dt.isoformat().replace('+00:00', 'Z'), slot_iso)) if table_exists(conn, 'availability_overrides') else None
        if blocking:
            return False
        occupancy = fetch_one(conn, "SELECT COUNT(*) AS value FROM appointments WHERE organization_id = ? AND bot_id = ? AND status IN ('scheduled','confirmed') AND scheduled_for = ?", (organization_id, bot_id, slot_iso)) or {"value": 0}
        capacity = self._capacity_for_slot(conn, organization_id, bot_id, slot_dt)
        return int(occupancy.get('value') or 0) < max(1, capacity)

    def _capacity_for_slot(self, conn, organization_id: str, bot_id: str, slot_dt: dt.datetime) -> int:
        if not table_exists(conn, 'agenda_resource_capacity_rules'):
            return 1
        weekday = slot_dt.weekday()
        hhmm = f"{slot_dt.hour:02d}:{slot_dt.minute:02d}"
        row = fetch_one(conn, "SELECT COALESCE(SUM(slot_capacity), 0) AS total FROM agenda_resource_capacity_rules WHERE organization_id = ? AND (bot_id = ? OR bot_id IS NULL) AND status = 'active' AND day_of_week = ? AND start_time <= ? AND end_time > ?", (organization_id, bot_id, weekday, hhmm, hhmm))
        total = int((row or {}).get('total') or 0)
        return total or 1

    def _is_feature_enabled(self, conn, organization_id: str, bot_id: str | None, feature_key: str) -> bool:
        if not table_exists(conn, 'feature_flag_overrides'):
            return False
        row = fetch_one(conn, "SELECT is_enabled FROM feature_flag_overrides WHERE organization_id = ? AND COALESCE(bot_id, '') = COALESCE(?, '') AND feature_key = ?", (organization_id, bot_id, feature_key))
        if row is None and bot_id:
            row = fetch_one(conn, "SELECT is_enabled FROM feature_flag_overrides WHERE organization_id = ? AND bot_id IS NULL AND feature_key = ?", (organization_id, feature_key))
        return bool(row and int(row.get('is_enabled') or 0) == 1)

    def _number_allows_intent(self, authorized: dict, intent: str) -> bool:
        allowed = self._json(authorized.get('allowed_intents_json'), [])
        if not allowed:
            return True
        return '*' in allowed or intent in allowed

    def _get_authorized_number(self, conn, organization_id: str, bot_id: str, phone: str) -> dict | None:
        if not table_exists(conn, 'authorized_operational_numbers'):
            return None
        row = fetch_one(conn, "SELECT * FROM authorized_operational_numbers WHERE organization_id = ? AND bot_id = ? AND phone_e164 = ? AND status = 'verified'", (organization_id, bot_id, phone))
        if row:
            execute(conn, "UPDATE authorized_operational_numbers SET last_used_at = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), row['id']))
        return row

    def _scope_summary(self, scope: dict) -> str:
        if not scope:
            return 'Sin restricción'
        parts: list[str] = []
        branches = scope.get('branches') or []
        if branches:
            parts.append(f"Sede: {', '.join(branches)}")
        resource_ids = scope.get('resource_ids') or []
        if resource_ids:
            parts.append(f"Recursos: {', '.join(resource_ids)}")
        resource_names = scope.get('resource_names') or []
        if resource_names:
            parts.append(f"Profesionales: {', '.join(resource_names)}")
        service_names = scope.get('service_names') or []
        if service_names:
            parts.append(f"Servicios: {', '.join(service_names)}")
        return ' · '.join(parts) if parts else 'Sin restricción'

    def _apply_authorized_scope(self, parsed: dict, authorized: dict) -> dict:
        scope = self._json(authorized.get('scope_json'), {})
        if not scope:
            return parsed
        entities = dict(parsed.get('entities') or {})
        merged_scope = {**(entities.get('scope') or {}), **scope}
        if merged_scope.get('branches') or merged_scope.get('resource_ids') or merged_scope.get('resource_names') or merged_scope.get('service_names'):
            merged_scope['whole_business'] = False
            merged_scope['scope_type'] = merged_scope.get('scope_type') or 'scoped_subset'
        entities['scope'] = merged_scope
        if merged_scope.get('scope_type') and not entities.get('scope_type'):
            entities['scope_type'] = merged_scope.get('scope_type')
        return {**parsed, 'entities': entities}

    def _appointment_scope_context(self, conn, appointment_id: str) -> dict:
        ctx = {'branch': None, 'resource_id': None, 'resource_name': None, 'service_name': None}
        if table_exists(conn, 'appointment_resource_assignments') and table_exists(conn, 'agenda_resources'):
            row = fetch_one(conn, "SELECT ara.resource_id, ar.name AS resource_name, ar.branch, ar.metadata_json FROM appointment_resource_assignments ara LEFT JOIN agenda_resources ar ON ar.id = ara.resource_id WHERE ara.appointment_id = ? ORDER BY ara.updated_at DESC LIMIT 1", (appointment_id,))
            if row:
                ctx['resource_id'] = row.get('resource_id')
                ctx['resource_name'] = row.get('resource_name')
                ctx['branch'] = row.get('branch')
                metadata = self._json(row.get('metadata_json'), {})
                if metadata.get('service_name'):
                    ctx['service_name'] = metadata.get('service_name')
        appt = fetch_one(conn, "SELECT provider_payload_json FROM appointments WHERE id = ?", (appointment_id,))
        payload = self._json((appt or {}).get('provider_payload_json'), {})
        ctx['service_name'] = ctx['service_name'] or payload.get('service_name') or payload.get('service') or payload.get('service_id')
        return ctx

    def _appointment_matches_scope(self, conn, appointment: dict, scope: dict) -> bool:
        if not scope:
            return True
        if scope.get('whole_business'):
            return True
        ctx = self._appointment_scope_context(conn, appointment['id'])
        branches = scope.get('branches') or []
        if branches and (ctx.get('branch') not in branches):
            return False
        resource_ids = scope.get('resource_ids') or []
        if resource_ids and (ctx.get('resource_id') not in resource_ids):
            return False
        resource_names = [str(item).lower() for item in (scope.get('resource_names') or []) if str(item).strip()]
        if resource_names:
            candidate = str(ctx.get('resource_name') or '').lower()
            if not any(token in candidate for token in resource_names):
                return False
        service_names = [str(item).lower() for item in (scope.get('service_names') or []) if str(item).strip()]
        if service_names:
            candidate = str(ctx.get('service_name') or '').lower()
            if not any(token in candidate for token in service_names):
                return False
        return True
