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
from .support import require_permission


class OperationalControlService:
    HIGH_IMPACT_INTENTS = {
        "bot.shutdown",
        "bot.restart",
        "bot.human_only",
        "availability.block_day",
        "availability.vacation_set",
        "appointment.notify_affected",
        "appointment.reschedule_mass",
        "appointment.reschedule_request_mass",
    }
    DUAL_APPROVAL_INTENTS = {"bot.shutdown", "appointment.reschedule_mass"}

    def summary(self, uow, *, user: dict, organization_id: str, bot_id: str) -> dict:
        conn = uow.conn
        require_permission(user, organization_id, "operations.control.read")
        bot = self._get_bot(conn, user, bot_id)
        authorized = fetch_all(conn, "SELECT * FROM authorized_operational_numbers WHERE organization_id = ? AND bot_id = ? AND status = 'verified' ORDER BY updated_at DESC", (organization_id, bot_id)) if table_exists(conn, "authorized_operational_numbers") else []
        recent = fetch_all(conn, "SELECT * FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 12", (organization_id, bot_id)) if table_exists(conn, "operational_command_requests") else []
        scheduled = fetch_all(conn, "SELECT * FROM scheduled_operational_actions WHERE organization_id = ? AND bot_id = ? AND status IN ('scheduled','queued','running') ORDER BY execute_at ASC LIMIT 12", (organization_id, bot_id)) if table_exists(conn, "scheduled_operational_actions") else []
        alerts = fetch_all(conn, "SELECT * FROM operational_command_alerts WHERE organization_id = ? AND bot_id = ? AND status = 'open' ORDER BY created_at DESC LIMIT 8", (organization_id, bot_id)) if table_exists(conn, "operational_command_alerts") else []
        today_start, today_end = self._date_window("today")
        blocked = fetch_all(conn, "SELECT * FROM availability_overrides WHERE organization_id = ? AND bot_id = ? AND status = 'active' AND start_at >= ? AND start_at <= ? ORDER BY start_at ASC", (organization_id, bot_id, today_start, today_end)) if table_exists(conn, "availability_overrides") else []
        upcoming_appointments = fetch_all(conn, "SELECT * FROM appointments WHERE organization_id = ? AND bot_id = ? AND status IN ('scheduled','confirmed') AND scheduled_for >= ? ORDER BY scheduled_for ASC LIMIT 20", (organization_id, bot_id, utcnow_iso()))
        return {
            "organization_id": organization_id,
            "bot_id": bot_id,
            "bot": {
                "id": bot["id"],
                "name": bot.get("name"),
                "status": bot.get("status"),
                "ai_paused": bool(bot.get("ai_paused")),
                "current_state": bot.get("current_state"),
                "operational_state": bot.get("operational_state") or ("paused" if bot.get("ai_paused") else "active"),
                "temp_unavailability_message": bot.get("temp_unavailability_message"),
                "operational_resume_at": bot.get("operational_resume_at"),
            },
            "counts": {
                "authorized_numbers": len(authorized),
                "recent_commands": len(recent),
                "scheduled_actions": len(scheduled),
                "alerts_open": len(alerts),
                "blocked_slots_today": len(blocked),
                "upcoming_appointments": len(upcoming_appointments),
            },
            "authorized_numbers": [self._serialize_authorized_number(item) for item in authorized[:8]],
            "recent_commands": [self._serialize_command(item) for item in recent],
            "scheduled_actions": [self._serialize_scheduled_action(item) for item in scheduled],
            "alerts": [self._serialize_alert(item) for item in alerts],
            "upcoming_appointments": [self._serialize_appointment(item) for item in upcoming_appointments[:8]],
        }

    def availability(self, uow, *, user: dict, organization_id: str, bot_id: str, day: str | None = None) -> dict:
        conn = uow.conn
        require_permission(user, organization_id, "operations.control.read")
        self._get_bot(conn, user, bot_id)
        start_at, end_at = self._date_window(day or "today")
        appointments = fetch_all(conn, "SELECT * FROM appointments WHERE organization_id = ? AND bot_id = ? AND scheduled_for >= ? AND scheduled_for <= ? ORDER BY scheduled_for ASC", (organization_id, bot_id, start_at, end_at))
        overrides = fetch_all(conn, "SELECT * FROM availability_overrides WHERE organization_id = ? AND bot_id = ? AND status = 'active' AND end_at >= ? AND start_at <= ? ORDER BY start_at ASC", (organization_id, bot_id, start_at, end_at)) if table_exists(conn, "availability_overrides") else []
        return {
            "day": day or "today",
            "start_at": start_at,
            "end_at": end_at,
            "appointments": [self._serialize_appointment(item) for item in appointments],
            "overrides": [self._serialize_override(item) for item in overrides],
            "summary": {
                "appointments": len(appointments),
                "blocked_ranges": len([item for item in overrides if item.get("override_type") in {"block_slot", "block_day", "vacation"}]),
                "open_exceptions": len([item for item in overrides if item.get("override_type") == "open_exception"]),
            },
        }

    def metrics(self, uow, *, user: dict, organization_id: str, bot_id: str, window_days: int = 7) -> dict:
        conn = uow.conn
        require_permission(user, organization_id, "operations.control.read")
        self._get_bot(conn, user, bot_id)
        since = (utcnow() - dt.timedelta(days=max(1, int(window_days)))).isoformat().replace("+00:00", "Z")
        totals = fetch_one(conn, "SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed, SUM(CASE WHEN status = 'awaiting_confirmation' THEN 1 ELSE 0 END) AS awaiting_confirmation, SUM(CASE WHEN status = 'executed' THEN 1 ELSE 0 END) AS executed, SUM(CASE WHEN status IN ('reverted','partially_reverted') THEN 1 ELSE 0 END) AS reverted, SUM(CASE WHEN status = 'rate_limited' THEN 1 ELSE 0 END) AS rate_limited, SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_risk FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND created_at >= ?", (organization_id, bot_id, since)) or {}
        intents = fetch_all(conn, "SELECT detected_intent, COUNT(*) AS count FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND created_at >= ? GROUP BY detected_intent ORDER BY count DESC LIMIT 8", (organization_id, bot_id, since))
        statuses = fetch_all(conn, "SELECT status, COUNT(*) AS count FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND created_at >= ? GROUP BY status ORDER BY count DESC", (organization_id, bot_id, since))
        ambiguous = fetch_one(conn, "SELECT COUNT(*) AS total FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? AND created_at >= ? AND detected_intent IS NULL", (organization_id, bot_id, since)) or {"total": 0}
        alerts_open = fetch_one(conn, "SELECT COUNT(*) AS total FROM operational_command_alerts WHERE organization_id = ? AND bot_id = ? AND status = 'open' AND created_at >= ?", (organization_id, bot_id, since)) if table_exists(conn, 'operational_command_alerts') else {"total": 0}
        return {
            "window_days": window_days,
            "summary": {
                "total": int(totals.get("total") or 0),
                "executed": int(totals.get("executed") or 0),
                "failed": int(totals.get("failed") or 0),
                "awaiting_confirmation": int(totals.get("awaiting_confirmation") or 0),
                "high_risk": int(totals.get("high_risk") or 0),
                "ambiguous": int(ambiguous.get("total") or 0),
                "rate_limited": int(totals.get("rate_limited") or 0),
                "reverted": int(totals.get("reverted") or 0),
                "alerts_open": int((alerts_open or {}).get("total") or 0),
            },
            "intents": [{"intent": row.get("detected_intent") or "unknown", "count": int(row.get("count") or 0)} for row in intents],
            "statuses": [{"status": row.get("status") or "unknown", "count": int(row.get("count") or 0)} for row in statuses],
        }

    def list_alerts(self, uow, *, user: dict, organization_id: str, bot_id: str) -> list[dict]:
        conn = uow.conn
        require_permission(user, organization_id, "operations.control.read")
        self._get_bot(conn, user, bot_id)
        if not table_exists(conn, 'operational_command_alerts'):
            return []
        rows = fetch_all(conn, "SELECT * FROM operational_command_alerts WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 30", (organization_id, bot_id))
        return [self._serialize_alert(item) for item in rows]

    def list_authorized_numbers(self, uow, *, user: dict, organization_id: str, bot_id: str) -> list[dict]:
        conn = uow.conn
        require_permission(user, organization_id, "operations.chat.authorize_number")
        self._get_bot(conn, user, bot_id)
        rows = fetch_all(conn, "SELECT * FROM authorized_operational_numbers WHERE organization_id = ? AND bot_id = ? ORDER BY updated_at DESC", (organization_id, bot_id))
        return [self._serialize_authorized_number(item) for item in rows]

    def create_authorized_number(self, uow, *, user: dict, payload) -> dict:
        conn = uow.conn
        require_permission(user, payload.organization_id, "operations.chat.authorize_number")
        self._get_bot(conn, user, payload.bot_id)
        existing = fetch_one(conn, "SELECT * FROM authorized_operational_numbers WHERE organization_id = ? AND bot_id = ? AND phone_e164 = ?", (payload.organization_id, payload.bot_id, payload.phone_e164))
        now = utcnow_iso()
        if existing:
            execute(conn, "UPDATE authorized_operational_numbers SET role = ?, allowed_intents_json = ?, scope_json = ?, status = ?, verified_at = ?, updated_at = ?, created_by = ? WHERE id = ?", (payload.role, to_json(payload.allowed_intents), to_json(payload.scope), payload.status, now if payload.status == 'verified' else None, now, user['id'], existing['id']))
            row = fetch_one(conn, "SELECT * FROM authorized_operational_numbers WHERE id = ?", (existing["id"],))
        else:
            number_id = new_id("opnum")
            execute(conn, "INSERT INTO authorized_operational_numbers (id, organization_id, bot_id, phone_e164, role, allowed_intents_json, scope_json, status, verified_at, last_used_at, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)", (number_id, payload.organization_id, payload.bot_id, payload.phone_e164, payload.role, to_json(payload.allowed_intents), to_json(payload.scope), payload.status, now if payload.status == 'verified' else None, user['id'], now, now))
            row = fetch_one(conn, "SELECT * FROM authorized_operational_numbers WHERE id = ?", (number_id,))
        create_audit_log(conn, organization_id=payload.organization_id, actor_user_id=user["id"], actor_type="user", entity_type="authorized_operational_number", entity_id=row["id"], action="operations.authorized_number.upserted", metadata={"phone": payload.phone_e164, "status": payload.status, "allowed_intents": payload.allowed_intents})
        return self._serialize_authorized_number(row)

    def list_commands(self, uow, *, user: dict, organization_id: str, bot_id: str) -> list[dict]:
        conn = uow.conn
        require_permission(user, organization_id, "operations.control.read")
        self._get_bot(conn, user, bot_id)
        rows = fetch_all(conn, "SELECT * FROM operational_command_requests WHERE organization_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT 30", (organization_id, bot_id))
        return [self._serialize_command(item) for item in rows]

    def preview_command(self, uow, *, user: dict, payload) -> dict:
        conn = uow.conn
        require_permission(user, payload.organization_id, "operations.control.execute")
        bot = self._get_bot(conn, user, payload.bot_id)
        parsed = self._parse_command(payload.text, bot)
        if not parsed.get("intent"):
            return {
                "ok": False,
                "status": "ambiguous",
                "reply_text": parsed.get("reply_text") or "No pude interpretar el comando operativo.",
                "intent": None,
                "impact": {"appointments_affected": 0, "clients_notified": 0},
                "requires_confirmation": False,
            }
        impact = self._build_impact(conn, bot, parsed)
        requires_confirmation = self._requires_confirmation(parsed["intent"], impact)
        second_approval = self._needs_second_approval(conn, bot["organization_id"], bot["id"], parsed["intent"], impact)
        return {
            "ok": True,
            "status": "preview",
            "intent": parsed["intent"],
            "entities": parsed.get("entities", {}),
            "impact": impact,
            "requires_confirmation": requires_confirmation,
            "requires_second_approval": second_approval,
            "reply_text": self._preview_reply(parsed["intent"], parsed.get("entities", {}), impact, requires_confirmation),
        }

    def submit_command(self, uow, *, user: dict, payload) -> dict:
        conn = uow.conn
        require_permission(user, payload.organization_id, "operations.control.execute")
        bot = self._get_bot(conn, user, payload.bot_id)
        parsed = self._parse_command(payload.text, bot)
        if not parsed.get("intent"):
            raise HTTPException(status_code=400, detail={"message": parsed.get("reply_text") or "Comando ambiguo", "code": "operational_command_ambiguous"})
        return self._submit_preparsed_command(conn, user=user, bot=bot, raw_text=payload.text, parsed=parsed, source_channel=payload.source_channel, dry_run=payload.dry_run, actor_phone_e164=payload.actor_phone_e164)

    def confirm_command(self, uow, *, user: dict, command_id: str, confirmation_code: str | None = None) -> dict:
        conn = uow.conn
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))
        if not command:
            raise HTTPException(status_code=404, detail="Command not found")
        require_permission(user, command["organization_id"], "operations.control.high_impact")
        self._get_bot(conn, user, command["bot_id"])
        if command.get("status") != "awaiting_confirmation":
            raise HTTPException(status_code=409, detail="Command is not awaiting confirmation")
        if confirmation_code and command.get("confirmation_code") and confirmation_code.upper() != str(command.get("confirmation_code")).upper():
            raise HTTPException(status_code=400, detail="Invalid confirmation code")
        parsed = {"intent": command.get("detected_intent"), "entities": self._json(command.get("parsed_entities_json"), {})}
        impact = self._json(command.get("result_json"), {}).get("impact") or self._build_impact(conn, get_bot(conn, command["bot_id"]), parsed)
        if self._needs_second_approval(conn, command["organization_id"], command["bot_id"], parsed.get("intent"), impact):
            execute(conn, "UPDATE operational_command_requests SET status = 'awaiting_second_approval', approved_by_user_id = ?, approved_at = ?, updated_at = ? WHERE id = ?", (user["id"], utcnow_iso(), utcnow_iso(), command_id))
            create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="operational_command", entity_id=command_id, action="operations.command.first_approved", metadata={"intent": parsed.get("intent")})
            return self._serialize_command(fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,)))
        result = self._execute_command(conn, command_id=command_id)
        return result

    def approve_command(self, uow, *, user: dict, command_id: str, note: str = "") -> dict:
        conn = uow.conn
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))
        if not command:
            raise HTTPException(status_code=404, detail="Command not found")
        require_permission(user, command["organization_id"], "operations.control.high_impact")
        if command.get("status") != "awaiting_second_approval":
            raise HTTPException(status_code=409, detail="Command does not require second approval")
        if command.get("approved_by_user_id") and command.get("approved_by_user_id") == user["id"]:
            raise HTTPException(status_code=409, detail="A different approver is required")
        execute(conn, "UPDATE operational_command_requests SET approval_note = ?, updated_at = ? WHERE id = ?", (note, utcnow_iso(), command_id))
        create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="operational_command", entity_id=command_id, action="operations.command.second_approved", metadata={"note": note})
        return self._execute_command(conn, command_id=command_id)

    def cancel_command(self, uow, *, user: dict, command_id: str, reason: str = "") -> dict:
        conn = uow.conn
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))
        if not command:
            raise HTTPException(status_code=404, detail="Command not found")
        require_permission(user, command["organization_id"], "operations.control.undo")
        self._cancel_command_internal(conn, command, reason=reason or "cancelled_by_user")
        create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="operational_command", entity_id=command_id, action="operations.command.cancelled", metadata={"reason": reason})
        return self._serialize_command(fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,)))

    def undo_command(self, uow, *, user: dict, command_id: str, reason: str = "undo_requested") -> dict:
        conn = uow.conn
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))
        if not command:
            raise HTTPException(status_code=404, detail="Command not found")
        require_permission(user, command["organization_id"], "operations.control.undo")
        if command.get("status") not in {"executed", "partially_reverted"}:
            raise HTTPException(status_code=409, detail="Only executed commands can be undone")
        if command.get("undoable_until"):
            until = parse_iso(command.get("undoable_until"))
            if until and until < utcnow():
                raise HTTPException(status_code=409, detail="Undo window expired")
        result = self._undo_command_internal(conn, command, actor_user_id=user.get("id"), reason=reason)
        create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=user["id"], actor_type="user", entity_type="operational_command", entity_id=command_id, action="operations.command.undone", metadata={"reason": reason, "result": result})
        return {**self._serialize_command(fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (command_id,))), "undo_result": result}

    def preview_reschedule_batch(self, uow, *, user: dict, payload) -> dict:
        conn = uow.conn
        require_permission(user, payload.organization_id, "appointment.manage")
        bot = self._get_bot(conn, user, payload.bot_id)
        entities = self._structured_reschedule_entities(payload)
        parsed = {"intent": "appointment.reschedule_mass", "entities": entities}
        impact = self._build_impact(conn, bot, parsed)
        plan = self._plan_reschedule(conn, payload.organization_id, payload.bot_id, entities)
        impact["planned"] = len([item for item in plan if item["status"] == "planned"])
        impact["unresolved"] = len([item for item in plan if item["status"] != "planned"])
        return {
            "ok": True,
            "status": "preview",
            "intent": "appointment.reschedule_mass",
            "entities": entities,
            "impact": impact,
            "plan": plan,
            "requires_confirmation": True,
            "reply_text": f"Preview listo. Se afectarían {impact['appointments_affected']} cita(s) y {impact['planned']} quedarían reprogramadas con slot válido.",
        }

    def execute_reschedule_batch(self, uow, *, user: dict, payload) -> dict:
        conn = uow.conn
        require_permission(user, payload.organization_id, "appointment.manage")
        bot = self._get_bot(conn, user, payload.bot_id)
        entities = self._structured_reschedule_entities(payload)
        parsed = {"intent": "appointment.reschedule_mass", "entities": entities}
        return self._submit_preparsed_command(conn, user=user, bot=bot, raw_text=f"structured_reschedule:{payload.scope_day}", parsed=parsed, source_channel="portal", dry_run=False)

    def handle_chat_command(self, conn, *, bot_id: str, phone: str, body: str, conversation_id: str, contact_id: str | None, inbound_message_id: str | None = None, external_id: str | None = None, correlation_id: str | None = None) -> dict | None:
        bot = get_bot(conn, bot_id)
        if not bot:
            return None
        authorized = self._get_authorized_number(conn, bot["organization_id"], bot_id, phone)
        parsed = self._parse_command(body, bot)
        is_confirm = parsed.get("intent") in {"command.confirm", "command.cancel_by_code"}
        if not authorized and not is_confirm:
            if parsed.get("intent"):
                self._create_alert(conn, organization_id=bot["organization_id"], bot_id=bot_id, command_id=None, alert_type="unauthorized_attempt", title="Intento no autorizado por WhatsApp", body=f"El número {phone} intentó ejecutar {parsed.get('intent')} sin autorización.", severity="warning", details={"phone": phone, "intent": parsed.get("intent")})
            return None
        if parsed.get("intent") == "command.confirm":
            command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE bot_id = ? AND actor_phone_e164 = ? AND status = 'awaiting_confirmation' AND confirmation_code = ? ORDER BY created_at DESC LIMIT 1", (bot_id, phone, parsed.get("entities", {}).get("confirmation_code")))
            if not command:
                return {"handled": True, "reply_text": "No encontré un comando pendiente con ese código.", "status": "not_found"}
            impact = self._json(command.get("result_json"), {}).get("impact") or {}
            if self._needs_second_approval(conn, command["organization_id"], command["bot_id"], command.get("detected_intent"), impact):
                execute(conn, "UPDATE operational_command_requests SET status = 'awaiting_second_approval', updated_at = ? WHERE id = ?", (utcnow_iso(), command["id"]))
                return {"handled": True, "reply_text": "Este comando quedó pendiente de aprobación final desde el portal por ser de alto impacto.", "status": "awaiting_second_approval"}
            result = self._execute_command(conn, command_id=command["id"])
            return {"handled": True, "reply_text": result.get("reply_text") or "Listo. El comando quedó ejecutado.", "status": result.get("status"), "command": result}
        if parsed.get("intent") == "command.cancel_by_code":
            command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE bot_id = ? AND actor_phone_e164 = ? AND confirmation_code = ? ORDER BY created_at DESC LIMIT 1", (bot_id, phone, parsed.get("entities", {}).get("confirmation_code")))
            if not command:
                return {"handled": True, "reply_text": "No encontré un comando pendiente con ese código.", "status": "not_found"}
            if command.get("status") in {"awaiting_confirmation", "awaiting_second_approval", "scheduled", "queued"}:
                self._cancel_command_internal(conn, command, reason="cancelled_from_whatsapp")
                return {"handled": True, "reply_text": "Listo. Cancelé el comando pendiente.", "status": "cancelled"}
            if command.get("status") == "executed":
                undo = self._undo_command_internal(conn, command, actor_user_id=None, reason="undo_from_whatsapp")
                return {"handled": True, "reply_text": undo.get("reply_text") or "Listo. Revertí el último comando posible.", "status": undo.get("status", "reverted")}
            return {"handled": True, "reply_text": "Ese comando ya no se puede cancelar.", "status": "not_cancellable"}
        if not parsed.get("intent"):
            return {"handled": True, "reply_text": parsed.get("reply_text") or "No pude entender el comando operativo. Puedo ayudarte a pausar el bot, bloquear horarios o avisar citas afectadas.", "status": "ambiguous"}
        if authorized and not self._number_allows_intent(authorized, parsed["intent"]):
            self._create_alert(conn, organization_id=bot["organization_id"], bot_id=bot_id, command_id=None, alert_type="forbidden_intent", title="Intento fuera de scope", body=f"El número {phone} intentó ejecutar {parsed['intent']} fuera de sus permisos.", severity="warning", details={"phone": phone, "intent": parsed["intent"]})
            return {"handled": True, "reply_text": "Este número no tiene permiso para ejecutar ese tipo de comando. Usa el portal o pide una autorización más amplia.", "status": "forbidden"}
        if authorized:
            parsed = self._apply_authorized_scope(parsed, authorized)
        limit_check = self._check_operational_rate_limit(conn, organization_id=bot["organization_id"], bot_id=bot_id, actor_key=phone, source_channel="whatsapp", intent=parsed.get("intent"))
        if not limit_check.get("allowed"):
            self._create_alert(conn, organization_id=bot["organization_id"], bot_id=bot_id, command_id=None, alert_type="rate_limit", title="Rate limit operativo", body=f"El número {phone} excedió el límite para {parsed.get('intent')}.", severity="warning", details=limit_check)
            return {"handled": True, "reply_text": "Llegaste al límite temporal de comandos operativos. Espera unos minutos o usa el portal para revisar el estado.", "status": "rate_limited"}
        impact = self._build_impact(conn, bot, parsed)
        command = self._create_command(conn, bot=bot, source_channel="whatsapp", actor_user_id=None, actor_phone_e164=phone, raw_text=body, parsed=parsed, impact=impact, source_message_id=inbound_message_id, source_webhook_receipt_id=external_id)
        if self._requires_confirmation(parsed["intent"], impact):
            code = self._confirmation_code(command["id"])
            execute(conn, "UPDATE operational_command_requests SET status = 'awaiting_confirmation', confirmation_code = ?, requires_confirmation = 1, updated_at = ? WHERE id = ?", (code, utcnow_iso(), command["id"]))
            return {"handled": True, "reply_text": self._preview_reply(parsed["intent"], parsed.get("entities", {}), impact, True, confirmation_code=code), "status": "awaiting_confirmation"}
        result = self._execute_command(conn, command_id=command["id"])
        return {"handled": True, "reply_text": result.get("reply_text") or "Listo. El comando quedó ejecutado.", "status": result.get("status"), "command": result}

    def execute_scheduled_action(self, conn, *, action_id: str | None = None, command_id: str | None = None) -> dict:
        action = None
        if action_id:
            action = fetch_one(conn, "SELECT * FROM scheduled_operational_actions WHERE id = ?", (action_id,))
        elif command_id:
            action = fetch_one(conn, "SELECT * FROM scheduled_operational_actions WHERE command_id = ? AND status IN ('scheduled','queued','running') ORDER BY execute_at ASC LIMIT 1", (command_id,))
        if not action:
            raise HTTPException(status_code=404, detail="scheduled_action_not_found")
        if action.get("status") == "executed":
            return self._serialize_scheduled_action(action)
        execute(conn, "UPDATE scheduled_operational_actions SET status = 'running', updated_at = ? WHERE id = ?", (utcnow_iso(), action["id"]))
        payload = self._json(action.get("payload_json"), {})
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE id = ?", (action.get("command_id"),)) if action.get("command_id") else None
        if not command:
            execute(conn, "UPDATE scheduled_operational_actions SET status = 'failed', updated_at = ? WHERE id = ?", (utcnow_iso(), action["id"]))
            return {"id": action["id"], "status": "failed", "error": "missing_command"}
        bot = get_bot(conn, action["bot_id"])
        result = self._apply_bot_state_change(conn, bot, command, "bot.resume" if action.get("action_type") == "active" else f"bot.{action.get('action_type')}", {"message": payload.get("message"), "bot_target_state": action.get("action_type")}, utcnow_iso())
        execute(conn, "UPDATE scheduled_operational_actions SET status = 'executed', updated_at = ? WHERE id = ?", (utcnow_iso(), action["id"]))
        execute(conn, "UPDATE operational_command_requests SET status = CASE WHEN status IN ('scheduled','queued','running') THEN 'executed' ELSE status END, executed_at = COALESCE(executed_at, ?), updated_at = ? WHERE id = ?", (utcnow_iso(), utcnow_iso(), command["id"]))
        create_audit_log(conn, organization_id=command["organization_id"], actor_user_id=command.get("actor_user_id"), actor_type="system", entity_type="operational_command", entity_id=command["id"], action="operations.command.executed_from_scheduler", metadata={"action_id": action["id"], "result": result})
        return {"id": action["id"], "status": "executed", "result": result}

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
        if not intent:
            return 'low'
        if intent in self.HIGH_IMPACT_INTENTS or int(impact.get('appointments_affected') or 0) > 3:
            return 'high'
        if intent.startswith('bot.') or int(impact.get('appointments_affected') or 0) > 0:
            return 'medium'
        return 'low'

    def _requires_confirmation(self, intent: str | None, impact: dict) -> bool:
        if not intent:
            return False
        if intent in self.HIGH_IMPACT_INTENTS:
            return True
        return int(impact.get('appointments_affected') or 0) > 3 or bool(impact.get('whole_business'))

    def _needs_second_approval(self, conn, organization_id: str, bot_id: str, intent: str | None, impact: dict) -> bool:
        if intent not in self.DUAL_APPROVAL_INTENTS:
            return False
        if not self._is_feature_enabled(conn, organization_id, bot_id, 'ops_control_dual_approval_enterprise_v1'):
            return False
        policy = fetch_one(conn, "SELECT * FROM organization_security_policies WHERE organization_id = ?", (organization_id,)) if table_exists(conn, 'organization_security_policies') else None
        return bool(policy and int(policy.get('require_dual_approval_releases') or 0) == 1)

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

    def _parse_command(self, text: str, bot: dict) -> dict:
        raw = (text or '').strip()
        lowered = raw.lower()
        if not raw:
            return {"intent": None, "reply_text": "No recibí texto para interpretar."}
        m = re.match(r'^(confirmar|confirm)\s+(\w+)$', lowered)
        if m:
            return {"intent": "command.confirm", "entities": {"confirmation_code": m.group(2).upper()}}
        m = re.match(r'^(cancelar|cancel)\s+(\w+)$', lowered)
        if m:
            return {"intent": "command.cancel_by_code", "entities": {"confirmation_code": m.group(2).upper()}}
        if 'cancela lo último' in lowered or 'cancela lo ultimo' in lowered:
            return {"intent": "command.undo_last", "entities": {}}
        if 'apaga el bot' in lowered or 'apagar bot' in lowered:
            return {"intent": "bot.shutdown", "entities": {}}
        if 'reinicia el bot' in lowered or 'reiniciar bot' in lowered:
            return {"intent": "bot.restart", "entities": {}}
        if 'solo humano' in lowered:
            return {"intent": "bot.human_only", "entities": {}}
        if 'pausa el bot' in lowered or 'pausar bot' in lowered:
            return {"intent": "bot.pause", "entities": {}}
        if lowered.startswith('react') and ('mañana' in lowered or 'lunes' in lowered or re.search(r'\b\d{1,2}\b', lowered)):
            when = self._parse_future_datetime(lowered)
            return {"intent": "bot.schedule_state_change", "entities": {"bot_target_state": "active", "effective_at": when}}
        if 'reactiva' in lowered or 'reactívalo' in lowered or 'reactivalo' in lowered:
            return {"intent": "bot.resume", "entities": {}}
        if 'estado actual del bot' in lowered or 'estado del bot' in lowered or 'cómo está el bot' in lowered or 'como esta el bot' in lowered:
            return {"intent": "bot.status_query", "entities": {}}
        if 'disponibilidad actual' in lowered or 'hay disponibilidad' in lowered or 'cómo está mi agenda' in lowered or 'como esta mi agenda' in lowered:
            day = 'tomorrow' if 'mañana' in lowered else 'today'
            return {"intent": "availability.query", "entities": {"day": day}}
        if 'me voy de vacaciones' in lowered:
            days = 5
            match = re.search(r'(\d+)\s*d[ií]as', lowered)
            if match:
                days = max(1, int(match.group(1)))
            start_at, end_at, start_date, end_date = self._vacation_range(days)
            return {"intent": "availability.vacation_set", "entities": {"start_at": start_at, "end_at": end_at, "start_date": start_date, "end_date": end_date, "override_type": "vacation", "scope": {"scope_type": "whole_business", "whole_business": True}, "reason": "vacaciones"}}
        if 'bloquéame mañana de' in lowered or 'bloqueame mañana de' in lowered:
            hours = re.search(r'de\s+(\d{1,2})\s+a\s+(\d{1,2})', lowered)
            if hours:
                start_at, end_at = self._tomorrow_range(int(hours.group(1)), int(hours.group(2)))
                return {"intent": "availability.block_slot", "entities": {"start_at": start_at, "end_at": end_at, "override_type": "block_slot", "scope": {"scope_type": "date_range"}, "reason": "bloqueo_operativo"}}
        if 'reprograma mis citas de mañana' in lowered or 'reprogramar mis citas de mañana' in lowered:
            start_at, end_at = self._date_window('tomorrow')
            return {"intent": "appointment.reschedule_mass", "entities": {"scope_type": "date_range", "scope": {"scope_type": "date_range"}, "start_at": start_at, "end_at": end_at, "strategy": "shift_minutes", "delay_minutes": 30, "notify_clients": True}}
        if 'solicita reprogramación' in lowered or 'solicita reprogramacion' in lowered:
            return {"intent": "appointment.reschedule_request_mass", "entities": {"scope_type": "today_appointments", "message": "Necesitamos reprogramar tu cita por un ajuste operativo."}}
        if 'cierro mañana' in lowered or 'cierro manana' in lowered:
            start_at, end_at = self._date_window('tomorrow')
            return {"intent": "impact.preview", "entities": {"start_at": start_at, "end_at": end_at, "override_type": "block_day", "scope_type": "date_range", "scope": {"scope_type": "whole_business", "whole_business": True}}}
        if 'avísale a mi próxima cita' in lowered or 'avisale a mi proxima cita' in lowered:
            return {"intent": "appointment.notify_next", "entities": {"scope_type": "next_appointment", "message": "Aviso operativo: tuvimos una emergencia y podríamos necesitar ajustar tu cita."}}
        if 'avísale a mis citas de hoy' in lowered or 'avisale a mis citas de hoy' in lowered:
            delay = 0
            match = re.search(r'(\d+)\s+min', lowered)
            if match:
                delay = int(match.group(1))
            return {"intent": "appointment.notify_affected", "entities": {"scope_type": "today_appointments", "delay_minutes": delay, "message": f"Aviso operativo: vamos {delay} minutos tarde." if delay else "Aviso operativo: tuvimos un retraso en agenda."}}
        if 'qué citas se verían afectadas' in lowered or 'que citas se verian afectadas' in lowered:
            start_at, end_at = self._date_window('tomorrow' if 'mañana' in lowered else 'today')
            return {"intent": "impact.preview", "entities": {"start_at": start_at, "end_at": end_at, "override_type": "block_day", "scope": {"scope_type": "whole_business", "whole_business": True}}}
        if 'mensaje temporal' in lowered or 'deja mensaje' in lowered:
            message = raw.split(':', 1)[1].strip() if ':' in raw else raw
            return {"intent": "bot.set_temp_unavailability_message", "entities": {"message": message}}
        return {"intent": None, "reply_text": "Necesito más detalle. Ejemplos: 'apaga el bot', 'bloquéame mañana de 2 a 6', 'avísale a mi próxima cita'."}

    def _preview_reply(self, intent: str | None, entities: dict, impact: dict, requires_confirmation: bool, confirmation_code: str | None = None) -> str:
        if intent == 'impact.preview':
            return f"Si ejecutas este cambio, se afectarían {impact.get('appointments_affected', 0)} cita(s)."
        if intent == 'bot.status_query':
            return "Consulta de estado registrada."
        if intent == 'availability.query':
            return "Consulta de disponibilidad registrada."
        if requires_confirmation:
            return f"Entendí el comando {intent}. Citas afectadas: {impact.get('appointments_affected', 0)}. Responde CONFIRMAR {confirmation_code or 'CODIGO'} para ejecutar o CANCELAR {confirmation_code or 'CODIGO'} para abortar."
        return f"Preview listo para {intent}. Citas afectadas: {impact.get('appointments_affected', 0)}."

    def _bot_status_reply(self, bot: dict) -> str:
        state = bot.get('operational_state') or ('paused' if bot.get('ai_paused') else 'active')
        resume = bot.get('operational_resume_at')
        message = bot.get('temp_unavailability_message')
        reply = f"Estado actual del bot: {state}."
        if resume:
            reply += f" Reanudación programada: {resume}."
        if message:
            reply += f" Mensaje temporal: {message}."
        return reply

    def _availability_reply(self, conn, organization_id: str, bot_id: str, entities: dict) -> str:
        day = entities.get('day') or 'today'
        start_at, end_at = self._date_window(day)
        appts = fetch_one(conn, "SELECT COUNT(*) AS value FROM appointments WHERE organization_id = ? AND bot_id = ? AND scheduled_for >= ? AND scheduled_for <= ? AND status IN ('scheduled','confirmed')", (organization_id, bot_id, start_at, end_at)) or {"value": 0}
        blocked = fetch_one(conn, "SELECT COUNT(*) AS value FROM availability_overrides WHERE organization_id = ? AND bot_id = ? AND status = 'active' AND end_at >= ? AND start_at <= ? AND override_type IN ('block_slot','block_day','vacation')", (organization_id, bot_id, start_at, end_at)) if table_exists(conn, 'availability_overrides') else {"value": 0}
        scope = entities.get('scope') or {}
        if scope.get('branches'):
            return f"Disponibilidad {day} para {', '.join(scope.get('branches') or [])}: {int(appts.get('value') or 0)} cita(s) activas y {int(blocked.get('value') or 0)} bloqueo(s) visibles."
        return f"Disponibilidad {day}: {int(appts.get('value') or 0)} cita(s) activas y {int(blocked.get('value') or 0)} bloqueo(s) visibles."

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

    def _record_impact(self, conn, command: dict, impact_type: str, entity_id: str, before: dict, after: dict) -> None:
        execute(conn, "INSERT INTO operational_command_impacts (id, command_id, organization_id, impact_type, entity_type, entity_id, before_json, after_json, reversible, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)", (new_id('opcimp'), command['id'], command['organization_id'], impact_type, impact_type, entity_id, to_json(before), to_json(after), utcnow_iso()))

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

    def _json(self, value: str | None, default: Any) -> Any:
        try:
            return json.loads(value) if value else default
        except Exception:
            return default

    def _serialize_command(self, row: dict) -> dict:
        return {
            'id': row['id'],
            'organization_id': row.get('organization_id'),
            'bot_id': row.get('bot_id'),
            'source_channel': row.get('source_channel'),
            'actor_user_id': row.get('actor_user_id'),
            'actor_phone_e164': row.get('actor_phone_e164'),
            'detected_intent': row.get('detected_intent'),
            'status': row.get('status'),
            'risk_level': row.get('risk_level'),
            'requires_confirmation': bool(row.get('requires_confirmation')),
            'confirmation_code': row.get('confirmation_code'),
            'approved_by_user_id': row.get('approved_by_user_id'),
            'approval_note': row.get('approval_note'),
            'parsed_entities': self._json(row.get('parsed_entities_json'), {}),
            'resolved_scope': self._json(row.get('resolved_scope_json'), {}),
            'result': self._json(row.get('result_json'), {}),
            'error': self._json(row.get('error_json'), {}),
            'created_at': row.get('created_at'),
            'updated_at': row.get('updated_at'),
            'scheduled_for': row.get('scheduled_for'),
            'executed_at': row.get('executed_at'),
            'undoable_until': row.get('undoable_until'),
        }

    def _serialize_authorized_number(self, row: dict) -> dict:
        return {
            'id': row['id'],
            'organization_id': row.get('organization_id'),
            'bot_id': row.get('bot_id'),
            'phone_e164': row.get('phone_e164'),
            'role': row.get('role'),
            'allowed_intents': self._json(row.get('allowed_intents_json'), []),
            'scope': self._json(row.get('scope_json'), {}),
            'status': row.get('status'),
            'verified_at': row.get('verified_at'),
            'last_used_at': row.get('last_used_at'),
            'updated_at': row.get('updated_at'),
            'scope_summary': self._scope_summary(self._json(row.get('scope_json'), {})),
        }

    def _serialize_scheduled_action(self, row: dict) -> dict:
        return {'id': row['id'], 'action_type': row.get('action_type'), 'execute_at': row.get('execute_at'), 'status': row.get('status'), 'payload': self._json(row.get('payload_json'), {})}

    def _serialize_appointment(self, row: dict) -> dict:
        return {'id': row['id'], 'scheduled_for': row.get('scheduled_for'), 'status': row.get('status'), 'conversation_id': row.get('conversation_id'), 'contact_id': row.get('contact_id')}

    def _serialize_override(self, row: dict) -> dict:
        return {'id': row['id'], 'override_type': row.get('override_type'), 'start_at': row.get('start_at'), 'end_at': row.get('end_at'), 'reason': row.get('reason'), 'scope': self._json(row.get('scope_json'), {}), 'status': row.get('status')}

    def _serialize_alert(self, row: dict) -> dict:
        return {
            'id': row.get('id'),
            'severity': row.get('severity'),
            'alert_type': row.get('alert_type'),
            'title': row.get('title'),
            'body': row.get('body'),
            'status': row.get('status'),
            'details': self._json(row.get('details_json'), {}),
            'created_at': row.get('created_at'),
            'command_id': row.get('command_id'),
        }

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

    def _confirmation_code(self, command_id: str) -> str:
        return command_id.split('_')[-1][:4].upper()

    def _local_now(self) -> dt.datetime:
        fixed_now = os.getenv('WAOS_OPERATIONAL_CONTROL_NOW')
        if fixed_now:
            value = fixed_now.replace('Z', '+00:00')
            parsed = dt.datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(ZoneInfo('America/Mexico_City'))
        return utcnow().astimezone(ZoneInfo('America/Mexico_City'))

    def _date_window(self, day: str) -> tuple[str, str]:
        base_local = self._local_now()
        if day == 'tomorrow':
            base_local = base_local + dt.timedelta(days=1)
        start_local = base_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + dt.timedelta(days=1) - dt.timedelta(seconds=1)
        start = start_local.astimezone(dt.timezone.utc)
        end = end_local.astimezone(dt.timezone.utc)
        return start.isoformat().replace('+00:00', 'Z'), end.isoformat().replace('+00:00', 'Z')

    def _structured_scope_window(self, scope_day: str, target_date: str | None) -> tuple[str, str]:
        if scope_day == 'today':
            return self._date_window('today')
        if scope_day == 'tomorrow':
            return self._date_window('tomorrow')
        if target_date:
            year, month, day = [int(part) for part in target_date.split('-')]
            start = dt.datetime(year, month, day, 0, 0, 0, tzinfo=dt.timezone.utc)
            end = start + dt.timedelta(days=1) - dt.timedelta(seconds=1)
            return start.isoformat().replace('+00:00', 'Z'), end.isoformat().replace('+00:00', 'Z')
        return self._date_window('tomorrow')

    def _tomorrow_range(self, start_hour: int, end_hour: int) -> tuple[str, str]:
        base_local = self._local_now() + dt.timedelta(days=1)
        start_local = base_local.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_local = base_local.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        start = start_local.astimezone(dt.timezone.utc)
        end = end_local.astimezone(dt.timezone.utc)
        return start.isoformat().replace('+00:00', 'Z'), end.isoformat().replace('+00:00', 'Z')

    def _vacation_range(self, days: int) -> tuple[str, str, str, str]:
        start_local = self._local_now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = (start_local + dt.timedelta(days=days)).replace(hour=23, minute=59, second=59)
        start = start_local.astimezone(dt.timezone.utc)
        end = end_local.astimezone(dt.timezone.utc)
        return start.isoformat().replace('+00:00', 'Z'), end.isoformat().replace('+00:00', 'Z'), start_local.date().isoformat(), end_local.date().isoformat()

    def _parse_future_datetime(self, lowered: str) -> str:
        now_local = self._local_now()
        target_local = now_local
        if 'mañana' in lowered or 'manana' in lowered:
            target_local = now_local + dt.timedelta(days=1)
        elif 'lunes' in lowered:
            days_ahead = (0 - now_local.weekday()) % 7
            days_ahead = 7 if days_ahead == 0 else days_ahead
            target_local = now_local + dt.timedelta(days=days_ahead)
        hour_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', lowered)
        hour = 8
        minute = 0
        if hour_match:
            hour = int(hour_match.group(1))
            minute = int(hour_match.group(2) or 0)
            suffix = hour_match.group(3)
            if suffix == 'pm' and hour < 12:
                hour += 12
            if suffix == 'am' and hour == 12:
                hour = 0
        target_local = target_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_local <= now_local:
            target_local = target_local + dt.timedelta(days=1)
        target = target_local.astimezone(dt.timezone.utc)
        return target.isoformat().replace('+00:00', 'Z')


operational_control_service = OperationalControlService()
