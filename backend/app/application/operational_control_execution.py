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

class OperationalControlExecutionMixin:
    def _submit_preparsed_command(self, conn, *, user: dict, bot: dict, raw_text: str, parsed: dict, source_channel: str, dry_run: bool, actor_phone_e164: str | None = None) -> dict:
        impact = self._build_impact(conn, bot, parsed)
        command = self._create_command(conn, bot=bot, source_channel=source_channel, actor_user_id=user.get("id"), actor_phone_e164=actor_phone_e164, raw_text=raw_text, parsed=parsed, impact=impact)
        if dry_run:
            execute(conn, "UPDATE operational_command_requests SET status = 'executed', result_json = ?, updated_at = ? WHERE id = ?", (to_json({"preview": True, "impact": impact}), utcnow_iso(), command["id"]))
            return {**self._serialize_command(fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command["id"],))), "preview": {"impact": impact}}
        if self._requires_confirmation(parsed["intent"], impact):
            code = self._confirmation_code(command["id"])
            execute(conn, "UPDATE operational_command_requests SET status = 'awaiting_confirmation', confirmation_code = ?, requires_confirmation = 1, updated_at = ? WHERE id = ?", (code, utcnow_iso(), command["id"]))
            return self._serialize_command(fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command["id"],)))
        return self._execute_command(conn, command_id=command["id"])

    def _cancel_command_internal(self, conn, command: dict, *, reason: str) -> None:
        execute(conn, "UPDATE operational_command_requests SET status = 'cancelled', cancelled_at = ?, error_json = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), to_json({"reason": reason}), utcnow_iso(), command["id"]))
        if table_exists(conn, "scheduled_operational_actions"):
            execute(conn, "UPDATE scheduled_operational_actions SET status = 'cancelled', updated_at = ? WHERE command_id = ? AND status IN ('scheduled','queued','running')", (utcnow_iso(), command["id"]))
        if table_exists(conn, "automation_jobs"):
            execute(conn, "UPDATE automation_jobs SET status = 'cancelled', last_error = ? WHERE payload_json LIKE ? AND status IN ('scheduled','queued','retry','running')", ("cancelled_by_command", f'%{command["id"]}%'))

    def _execute_command(self, conn, *, command_id: str) -> dict:
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))
        if not command:
            raise HTTPException(status_code=404, detail="Command not found")
        bot = get_bot(conn, command["bot_id"])
        parsed = {"intent": command.get("detected_intent"), "entities": self._json(command.get("parsed_entities_json"), {})}
        impact = self._json(command.get("result_json"), {}).get("impact") or self._build_impact(conn, bot, parsed)
        entities = parsed.get("entities", {})
        now = utcnow_iso()
        execute(conn, "UPDATE operational_command_requests SET status = 'executing', updated_at = ? WHERE id = ?", (now, command_id))
        result: dict[str, Any] = {"impact": impact}
        intent = parsed["intent"]
        try:
            if intent == "bot.status_query":
                result["reply_text"] = self._bot_status_reply(bot)
            elif intent == "availability.query":
                result["reply_text"] = self._availability_reply(conn, command["organization_id"], command["bot_id"], entities)
            elif intent == "impact.preview":
                result["reply_text"] = self._preview_reply(intent, entities, impact, False)
            elif intent in {"availability.block_slot", "availability.block_day", "availability.open_exception"}:
                override_id = new_id("ovr")
                execute(conn, "INSERT INTO availability_overrides (id, organization_id, bot_id, override_type, start_at, end_at, reason, scope_json, status, created_by, command_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)", (override_id, command["organization_id"], command["bot_id"], entities.get("override_type"), entities.get("start_at"), entities.get("end_at"), entities.get("reason") or entities.get("message") or '', to_json(entities.get("scope") or {}), command.get("actor_user_id"), command_id, now, now))
                self._record_impact(conn, command, "availability_override", override_id, {}, entities)
                result["reply_text"] = "Listo. Actualicé la disponibilidad." if intent != "availability.open_exception" else "Listo. Abrí disponibilidad excepcional."
            elif intent == "availability.vacation_set":
                vacation_id = new_id("vac")
                execute(conn, "INSERT INTO vacation_periods (id, organization_id, bot_id, start_date, end_date, reason, scope_json, status, created_by, command_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)", (vacation_id, command["organization_id"], command["bot_id"], entities.get("start_date"), entities.get("end_date"), entities.get("reason") or 'vacaciones', to_json(entities.get("scope") or {}), command.get("actor_user_id"), command_id, now, now))
                override_id = new_id("ovr")
                execute(conn, "INSERT INTO availability_overrides (id, organization_id, bot_id, override_type, start_at, end_at, reason, scope_json, status, created_by, command_id, created_at, updated_at) VALUES (?, ?, ?, 'vacation', ?, ?, ?, ?, 'active', ?, ?, ?, ?)", (override_id, command["organization_id"], command["bot_id"], entities.get("start_at"), entities.get("end_at"), entities.get("reason") or 'vacaciones', to_json(entities.get("scope") or {}), command.get("actor_user_id"), command_id, now, now))
                self._record_impact(conn, command, "vacation", vacation_id, {}, entities)
                result["reply_text"] = "Listo. Registré vacaciones y bloqueé la disponibilidad del rango indicado."
            elif intent in {"appointment.notify_next", "appointment.notify_affected", "appointment.reschedule_request_mass"}:
                appointments = self._select_target_appointments(conn, command["organization_id"], command["bot_id"], entities)
                batch_id = self._create_notification_batch(conn, command, appointments, entities, now)
                result["reply_text"] = f"Listo. Preparé avisos para {len(appointments)} cita(s)."
                result["batch_id"] = batch_id
            elif intent == "appointment.reschedule_mass":
                plan = self._plan_reschedule(conn, command["organization_id"], command["bot_id"], entities)
                batch_id = new_id("rbat")
                batch_status = 'partial' if any(item['status'] != 'planned' for item in plan) else 'executed'
                execute(conn, "INSERT INTO mass_reschedule_batches (id, organization_id, bot_id, command_id, status, strategy, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (batch_id, command["organization_id"], command["bot_id"], command_id, batch_status, entities.get('strategy') or 'next_available_window', to_json({"notify_clients": bool(entities.get('notify_clients')), "plan": plan}), now, now))
                moved = 0
                for item in plan:
                    execute(conn, "INSERT INTO mass_reschedule_items (id, batch_id, organization_id, appointment_id, old_scheduled_for, new_scheduled_for, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (new_id('ritm'), batch_id, command["organization_id"], item["appointment_id"], item["old_scheduled_for"], item.get("new_scheduled_for"), item["status"], now))
                    if item["status"] != 'planned' or not item.get("new_scheduled_for"):
                        continue
                    moved += 1
                    execute(conn, "UPDATE appointments SET scheduled_for = ?, updated_at = ? WHERE id = ?", (item["new_scheduled_for"], now, item["appointment_id"]))
                    self._record_impact(conn, command, "appointment_reschedule", item["appointment_id"], {"scheduled_for": item["old_scheduled_for"]}, {"scheduled_for": item["new_scheduled_for"]})
                if entities.get('notify_clients'):
                    appointments = fetch_all(conn, f"SELECT * FROM appointments WHERE id IN ({','.join('?' for _ in plan if _.get('new_scheduled_for'))})", [item['appointment_id'] for item in plan if item.get('new_scheduled_for')]) if any(item.get('new_scheduled_for') for item in plan) else []
                    if appointments:
                        notification_entities = {"message": "Actualizamos tu cita por un ajuste operativo. Revisa tu nuevo horario.", "scope": {"scope_type": "rescheduled_batch"}, "notification_kind": "reschedule_notice"}
                        result["notification_batch_id"] = self._create_notification_batch(conn, command, appointments, notification_entities, now)
                unresolved = len([item for item in plan if item['status'] != 'planned'])
                result["reply_text"] = f"Listo. Reprogramé {moved} cita(s) con matching real de slots. {unresolved} quedaron sin slot automático." if unresolved else f"Listo. Reprogramé {moved} cita(s) con matching real de slots."
                result["batch_id"] = batch_id
                result["plan"] = plan
                if unresolved:
                    self._create_alert(conn, organization_id=command["organization_id"], bot_id=command["bot_id"], command_id=command_id, alert_type="partial_reschedule", title="Reprogramación parcial", body=f"La reprogramación masiva dejó {unresolved} cita(s) sin slot automático.", severity="warning", details={"batch_id": batch_id, "unresolved": unresolved})
            elif intent in {"bot.pause", "bot.shutdown", "bot.restart", "bot.human_only", "bot.resume", "bot.set_temp_unavailability_message"}:
                result.update(self._apply_bot_state_change(conn, bot, command, intent, entities, now))
            elif intent == "bot.schedule_state_change":
                result.update(self._schedule_state_change(conn, bot, command, entities, now))
            elif intent == "command.undo_last":
                pending = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND id != ? AND status IN ('awaiting_confirmation','awaiting_second_approval','scheduled','queued') ORDER BY created_at DESC LIMIT 1", (command["organization_id"], command["bot_id"], command_id))
                if pending:
                    self._cancel_command_internal(conn, pending, reason="undo_last")
                    result["reply_text"] = "Listo. Cancelé el último comando pendiente."
                    result["cancelled_command_id"] = pending["id"]
                else:
                    executed_target = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND id != ? AND status = 'executed' ORDER BY created_at DESC LIMIT 1", (command["organization_id"], command["bot_id"], command_id))
                    if executed_target:
                        undo_result = self._undo_command_internal(conn, executed_target, actor_user_id=command.get('actor_user_id'), reason='undo_last')
                        result.update(undo_result)
                    else:
                        result["reply_text"] = "No encontré comandos pendientes o revertibles para cancelar."
            else:
                result["reply_text"] = "Comando recibido, pero esta acción todavía no está habilitada en esta versión."
            final_status = 'executed'
            if result.get('undo_status') == 'partially_reverted':
                final_status = 'partially_reverted'
            execute(conn, "UPDATE operational_command_requests SET status = ?, executed_at = ?, result_json = ?, updated_at = ? WHERE id = ?", (final_status, utcnow_iso(), to_json(result), utcnow_iso(), command_id))
            create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=command.get("actor_user_id"), actor_type="user" if command.get("actor_user_id") else "whatsapp_number", entity_type="operational_command", entity_id=command_id, action="operations.command.executed", metadata={"intent": intent, "impact": impact})
            return {**self._serialize_command(fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))), "reply_text": result.get("reply_text"), "status": final_status}
        except Exception as exc:
            execute(conn, "UPDATE operational_command_requests SET status = 'failed', failed_at = ?, error_json = ?, updated_at = ? WHERE id = ?", (utcnow_iso(), to_json({"error": str(exc)}), utcnow_iso(), command_id))
            self._create_alert(conn, organization_id=command["organization_id"], bot_id=command["bot_id"], command_id=command_id, alert_type="execution_failed", title="Comando operativo fallido", body=f"El comando {intent or 'unknown'} falló: {exc}", severity="critical", details={"intent": intent, "error": str(exc)})
            raise

    def _schedule_state_change(self, conn, bot: dict, command: dict, entities: dict, now: str) -> dict:
        action_id = new_id("opsched")
        execute(conn, "INSERT INTO scheduled_operational_actions (id, organization_id, bot_id, command_id, action_type, execute_at, payload_json, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, ?, ?)", (action_id, command["organization_id"], command["bot_id"], command["id"], entities.get("bot_target_state") or 'active', entities.get("effective_at"), to_json(entities), command.get("actor_user_id"), now, now))
        if table_exists(conn, 'automation_jobs'):
            execute(conn, "INSERT INTO automation_jobs (id, organization_id, bot_id, conversation_id, contact_id, rule_id, job_type, dedupe_key, scheduled_for, status, attempts, payload_json, priority, created_at) VALUES (?, ?, ?, NULL, NULL, NULL, 'operational_state_transition_execute', ?, ?, 'queued', 0, ?, 90, ?)", (new_id('job'), command['organization_id'], command['bot_id'], f"ops:{action_id}", entities.get('effective_at'), to_json({"command_id": command['id'], "action_id": action_id}), now))
        execute(conn, "UPDATE bots SET operational_state = 'scheduled_pause', operational_resume_at = ?, last_operational_command_id = ?, updated_at = ? WHERE id = ?", (entities.get('effective_at'), command['id'], now, bot['id']))
        return {"scheduled_action_id": action_id, "reply_text": f"Listo. Programé el cambio para {entities.get('effective_at')}."}

    def _apply_bot_state_change(self, conn, bot: dict, command: dict, intent: str, entities: dict, now: str) -> dict:
        prev_state = bot.get('operational_state') or ('paused' if bot.get('ai_paused') else 'active')
        new_state = prev_state
        status = bot.get('status')
        ai_paused = int(bot.get('ai_paused') or 0)
        temp_message = bot.get('temp_unavailability_message')
        if intent == 'bot.pause':
            new_state = 'paused'; ai_paused = 1
        elif intent == 'bot.shutdown':
            new_state = 'maintenance'; ai_paused = 1; status = 'inactive'
        elif intent == 'bot.restart':
            new_state = 'active'; ai_paused = 0; status = 'active'
        elif intent == 'bot.human_only':
            new_state = 'human_only'; ai_paused = 1
        elif intent == 'bot.resume':
            new_state = 'active'; ai_paused = 0; status = 'active'
        elif intent == 'bot.set_temp_unavailability_message':
            temp_message = entities.get('message') or entities.get('custom_message') or ''
        execute(conn, "UPDATE bots SET operational_state = ?, ai_paused = ?, status = ?, temp_unavailability_message = ?, last_operational_command_id = ?, updated_at = ? WHERE id = ?", (new_state, ai_paused, status, temp_message, command['id'], now, bot['id']))
        history_id = new_id('bstate')
        execute(conn, "INSERT INTO bot_operational_state_history (id, organization_id, bot_id, command_id, previous_state, new_state, message, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (history_id, bot['organization_id'], bot['id'], command['id'], prev_state, new_state, temp_message if temp_message else entities.get('message'), command.get('actor_user_id'), now))
        self._record_impact(conn, command, 'bot_state', bot['id'], {"operational_state": prev_state, "status": bot.get('status'), "ai_paused": bot.get('ai_paused')}, {"operational_state": new_state, "status": status, "ai_paused": ai_paused})
        if intent == 'bot.restart':
            reply = 'Listo. Reinicié el bot y quedó nuevamente activo.'
        elif intent == 'bot.shutdown':
            reply = 'Listo. El bot quedó apagado para operación automática.'
        elif intent == 'bot.human_only':
            reply = 'Listo. El bot quedó en modo solo humano.'
        elif intent == 'bot.resume':
            reply = 'Listo. El bot volvió a estar activo.'
        elif intent == 'bot.set_temp_unavailability_message':
            reply = 'Listo. Actualicé el mensaje temporal de indisponibilidad.'
        else:
            reply = 'Listo. El estado operativo del bot quedó actualizado.'
        return {"reply_text": reply, "bot_state": {"previous": prev_state, "current": new_state, "status": status}}

    def _create_notification_batch(self, conn, command: dict, appointments: list[dict], entities: dict, now: str) -> str:
        batch_id = new_id('apnb')
        execute(conn, "INSERT INTO appointment_notification_batches (id, organization_id, bot_id, command_id, kind, scope_json, message_text, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'executed', ?, ?, ?)", (batch_id, command['organization_id'], command['bot_id'], command['id'], entities.get('notification_kind') or 'operational_notice', to_json(entities.get('scope') or {}), entities.get('message') or entities.get('custom_message') or '', command.get('actor_user_id'), now, now))
        for appointment in appointments:
            execute(conn, "INSERT INTO appointment_notification_targets (id, batch_id, organization_id, appointment_id, contact_id, conversation_id, delivery_status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?)", (new_id('apnt'), batch_id, command['organization_id'], appointment['id'], appointment.get('contact_id'), appointment.get('conversation_id'), now))
            if appointment.get('conversation_id'):
                create_message(conn, organization_id=command['organization_id'], conversation_id=appointment['conversation_id'], contact_id=appointment.get('contact_id'), bot_id=command['bot_id'], direction='outbound', kind='text', source='system', body=(entities.get('message') or entities.get('custom_message') or 'Aviso operativo sobre tu cita.'), status='queued', metadata={"category": "operational_notification", "batch_id": batch_id})
        self._record_impact(conn, command, 'notification_batch', batch_id, {}, {"appointments": [item['id'] for item in appointments]})
        return batch_id

    def _create_command(self, conn, *, bot: dict, source_channel: str, actor_user_id: str | None, actor_phone_e164: str | None, raw_text: str, parsed: dict, impact: dict, source_message_id: str | None = None, source_webhook_receipt_id: str | None = None) -> dict:
        command_id = new_id('opcmd')
        now = utcnow_iso()
        execute(conn, "INSERT INTO operational_command_requests (id, organization_id, bot_id, source_channel, source_message_id, source_webhook_receipt_id, actor_user_id, actor_phone_e164, actor_role, detected_intent, raw_text, parsed_entities_json, resolved_scope_json, risk_level, requires_confirmation, confirmation_code, status, scheduled_for, executed_at, failed_at, cancelled_at, undoable_until, result_json, error_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, 'queued', ?, NULL, NULL, NULL, ?, ?, '{}', ?, ?)", (command_id, bot['organization_id'], bot['id'], source_channel, source_message_id, source_webhook_receipt_id, actor_user_id, actor_phone_e164, self._resolve_actor_role(conn, bot['organization_id'], actor_user_id), parsed.get('intent'), raw_text, to_json(parsed.get('entities') or {}), to_json((parsed.get('entities') or {}).get('scope') or {}), self._risk_level(parsed.get('intent'), impact), (parsed.get('entities') or {}).get('effective_at'), add_minutes(now, 30), to_json({"impact": impact}), now, now))
        create_audit_log(conn, organization_id=bot['organization_id'], actor_user_id=actor_user_id, actor_type='user' if actor_user_id else 'whatsapp_number', entity_type='operational_command', entity_id=command_id, action='operations.command.created', metadata={"intent": parsed.get('intent'), "source_channel": source_channel, "impact": impact})
        return fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))

    def _risk_level(self, intent: str | None, impact: dict) -> str:
        return risk_level(intent, impact, high_impact_intents=self.HIGH_IMPACT_INTENTS)

    def _requires_confirmation(self, intent: str | None, impact: dict) -> bool:
        return requires_confirmation(intent, impact, high_impact_intents=self.HIGH_IMPACT_INTENTS)

    def _needs_second_approval(self, conn, organization_id: str, bot_id: str, intent: str | None, impact: dict) -> bool:
        return needs_second_approval(conn, organization_id=organization_id, bot_id=bot_id, intent=intent, impact=impact, dual_approval_intents=self.DUAL_APPROVAL_INTENTS, is_feature_enabled=self._is_feature_enabled)

    def _build_impact(self, conn, bot: dict, parsed: dict) -> dict:
        intent = parsed.get('intent')
        entities = parsed.get('entities') or {}
        if intent in {'availability.block_slot', 'availability.block_day', 'availability.vacation_set', 'appointment.notify_next', 'appointment.notify_affected', 'appointment.reschedule_mass', 'appointment.reschedule_request_mass', 'impact.preview'}:
            appointments = self._select_target_appointments(conn, bot['organization_id'], bot['id'], entities)
            impact = {
                'appointments_affected': len(appointments),
                'clients_notified': len(appointments) if intent in {'appointment.notify_next', 'appointment.notify_affected', 'appointment.reschedule_request_mass'} else 0,
                'appointment_ids': [item['id'] for item in appointments],
                'whole_business': bool((entities.get('scope') or {}).get('whole_business')),
            }
            if intent == 'appointment.reschedule_mass':
                plan = self._plan_reschedule(conn, bot['organization_id'], bot['id'], entities)
                impact['planned'] = len([item for item in plan if item['status'] == 'planned'])
                impact['unresolved'] = len([item for item in plan if item['status'] != 'planned'])
            return impact
        return {'appointments_affected': 0, 'clients_notified': 0, 'whole_business': bool((entities.get('scope') or {}).get('whole_business'))}

    def _record_impact(self, conn, command: dict, impact_type: str, entity_id: str, before: dict, after: dict) -> None:
        execute(conn, "INSERT INTO operational_command_impacts (id, command_id, organization_id, impact_type, entity_type, entity_id, before_json, after_json, reversible, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)", (new_id('opcimp'), command['id'], command['organization_id'], impact_type, impact_type, entity_id, to_json(before), to_json(after), utcnow_iso()))

    def _check_operational_rate_limit(self, conn, *, organization_id: str, bot_id: str, actor_key: str, source_channel: str, intent: str | None) -> dict:
        if source_channel != 'whatsapp':
            return {'allowed': True, 'checks': []}
        now_dt = utcnow()
        rules = [
            {'scope': 'ops_phone', 'scope_key': actor_key, 'window_seconds': 600, 'max_requests': 8},
            {'scope': 'ops_phone_intent', 'scope_key': f"{actor_key}:{intent or 'unknown'}", 'window_seconds': 600, 'max_requests': 4 if intent in self.HIGH_IMPACT_INTENTS else 6},
        ]
        checks: list[dict[str, Any]] = []
        for rule in rules:
            window_start = (now_dt - dt.timedelta(seconds=int(rule['window_seconds']))).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
            current = fetch_one(conn, "SELECT COALESCE(SUM(request_count), 0) AS total FROM request_counters WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND scope = ? AND scope_key = ? AND last_seen_at >= ?", (organization_id, bot_id, rule['scope'], rule['scope_key'], window_start)) or {'total': 0}
            current_total = int(current.get('total') or 0)
            allowed = current_total < int(rule['max_requests'])
            checks.append({**rule, 'current': current_total, 'allowed': allowed})
            if not allowed:
                return {'allowed': False, 'checks': checks}
        window_bucket = now_dt.replace(second=0, microsecond=0).isoformat().replace('+00:00', 'Z')
        for rule in rules:
            existing = fetch_one(conn, "SELECT * FROM request_counters WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND scope = ? AND scope_key = ? AND window_started_at = ?", (organization_id, bot_id, rule['scope'], rule['scope_key'], window_bucket))
            if existing:
                execute(conn, "UPDATE request_counters SET request_count = request_count + 1, last_seen_at = ? WHERE id = ?", (utcnow_iso(), existing['id']))
            else:
                execute(conn, "INSERT INTO request_counters (id, organization_id, bot_id, scope, scope_key, window_started_at, request_count, last_seen_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)", (new_id('ctr'), organization_id, bot_id, rule['scope'], rule['scope_key'], window_bucket, utcnow_iso()))
        return {'allowed': True, 'checks': checks}

    def _create_alert(self, conn, *, organization_id: str, bot_id: str | None, command_id: str | None, alert_type: str, title: str, body: str, severity: str = 'warning', details: dict | None = None) -> dict | None:
        if not table_exists(conn, 'operational_command_alerts'):
            return None
        alert_id = new_id('opalt')
        execute(conn, "INSERT INTO operational_command_alerts (id, organization_id, bot_id, command_id, severity, alert_type, title, body, status, details_json, created_at, acknowledged_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, NULL)", (alert_id, organization_id, bot_id, command_id, severity, alert_type, title, body, to_json(details or {}), utcnow_iso()))
        return fetch_one(conn, "SELECT * FROM operational_command_alerts WHERE id = ?", (alert_id,))

    def _undo_command_internal(self, conn, command: dict, *, actor_user_id: str | None, reason: str) -> dict:
        impacts = fetch_all(conn, "SELECT * FROM operational_command_impacts WHERE command_id = ? ORDER BY created_at DESC", (command['id'],))
        if not impacts:
            raise HTTPException(status_code=409, detail='No reversible impacts found for this command')
        reverted = 0
        partial = False
        for impact in impacts:
            impact_type = impact.get('impact_type')
            entity_id = impact.get('entity_id')
            before = self._json(impact.get('before_json'), {})
            if impact_type == 'availability_override' and entity_id:
                execute(conn, "UPDATE availability_overrides SET status = 'cancelled', updated_at = ? WHERE id = ?", (utcnow_iso(), entity_id))
                reverted += 1
            elif impact_type == 'vacation' and entity_id:
                execute(conn, "UPDATE vacation_periods SET status = 'cancelled', updated_at = ? WHERE id = ?", (utcnow_iso(), entity_id))
                execute(conn, "UPDATE availability_overrides SET status = 'cancelled', updated_at = ? WHERE command_id = ? AND override_type = 'vacation'", (utcnow_iso(), command['id']))
                reverted += 1
            elif impact_type == 'bot_state' and entity_id:
                execute(conn, "UPDATE bots SET operational_state = ?, status = ?, ai_paused = ?, updated_at = ? WHERE id = ?", (before.get('operational_state') or 'active', before.get('status') or 'active', int(before.get('ai_paused') or 0), utcnow_iso(), entity_id))
                reverted += 1
            elif impact_type == 'notification_batch' and entity_id:
                targets = fetch_all(conn, "SELECT * FROM appointment_notification_targets WHERE batch_id = ?", (entity_id,))
                cancelled = 0
                delivered = 0
                for target in targets:
                    if target.get('delivery_status') in {'queued', 'pending'}:
                        execute(conn, "UPDATE appointment_notification_targets SET delivery_status = 'cancelled' WHERE id = ?", (target['id'],))
                        cancelled += 1
                    else:
                        delivered += 1
                execute(conn, "UPDATE appointment_notification_batches SET status = ? , updated_at = ? WHERE id = ?", ('reverted_partial' if delivered else 'reverted', utcnow_iso(), entity_id))
                reverted += cancelled
                partial = partial or bool(delivered)
            elif impact_type == 'appointment_reschedule' and entity_id:
                current = fetch_one(conn, "SELECT scheduled_for FROM appointments WHERE id = ?", (entity_id,)) or {}
                after = self._json(impact.get('after_json'), {})
                if current.get('scheduled_for') == after.get('scheduled_for') and before.get('scheduled_for'):
                    execute(conn, "UPDATE appointments SET scheduled_for = ?, updated_at = ? WHERE id = ?", (before.get('scheduled_for'), utcnow_iso(), entity_id))
                    reverted += 1
                else:
                    partial = True
        final_status = 'partially_reverted' if partial else 'reverted'
        execute(conn, "UPDATE operational_command_requests SET status = ?, updated_at = ?, result_json = ? WHERE id = ?", (final_status, utcnow_iso(), to_json({**self._json(command.get('result_json'), {}), 'undo_reason': reason, 'reverted_impacts': reverted}), command['id']))
        return {'status': final_status, 'reply_text': 'Listo. Revertí el último comando posible.' if not partial else 'Revertí parcialmente el comando. Algunas acciones ya no podían deshacerse.', 'reverted_impacts': reverted, 'undo_status': final_status}

    def _resolve_actor_role(self, conn, organization_id: str, actor_user_id: str | None) -> str | None:
        if not actor_user_id:
            return None
        membership = fetch_one(conn, "SELECT role FROM organization_members WHERE organization_id = ? AND user_id = ? AND is_active = 1", (organization_id, actor_user_id))
        return membership.get('role') if membership else None

    def _get_bot(self, conn, user: dict, bot_id: str) -> dict:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail='Bot not found')
        ensure_bot_access(user, bot)
        return bot
