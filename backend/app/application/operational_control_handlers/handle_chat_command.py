from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from ...db import execute, fetch_all, fetch_one, table_exists
from ...repositories.audit import create_audit_log
from ...repositories.bots import get_bot
from ...repositories.conversations import create_message
from ...security import ensure_bot_access
from ...utils import add_minutes, new_id, parse_iso, to_json, utcnow, utcnow_iso
from ..operational_control_policy import needs_second_approval, requires_confirmation, risk_level
from ..operational_control_presenters import (
    serialize_alert,
    serialize_appointment,
    serialize_authorized_number,
    serialize_command,
    serialize_override,
    serialize_scheduled_action,
)
from ..support import require_permission



def handle(service, conn, *, bot_id: str, phone: str, body: str, conversation_id: str, contact_id: str | None, inbound_message_id: str | None = None, external_id: str | None = None, correlation_id: str | None = None) -> dict | None:
    bot = get_bot(conn, bot_id)
    if not bot:
        return None
    authorized = service._get_authorized_number(conn, bot["organization_id"], bot_id, phone)
    parsed = service._parse_command(body, bot)
    is_confirm = parsed.get("intent") in {"command.confirm", "command.cancel_by_code"}
    if not authorized and not is_confirm:
        if parsed.get("intent"):
            service._create_alert(conn, organization_id=bot["organization_id"], bot_id=bot_id, command_id=None, alert_type="unauthorized_attempt", title="Intento no autorizado por WhatsApp", body=f"El número {phone} intentó ejecutar {parsed.get('intent')} sin autorización.", severity="warning", details={"phone": phone, "intent": parsed.get("intent")})
        return None
    if parsed.get("intent") == "command.confirm":
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE bot_id = ? AND actor_phone_e164 = ? AND status = 'awaiting_confirmation' AND confirmation_code = ? ORDER BY created_at DESC LIMIT 1", (bot_id, phone, parsed.get("entities", {}).get("confirmation_code")))
        if not command:
            return {"handled": True, "reply_text": "No encontré un comando pendiente con ese código.", "status": "not_found"}
        impact = service._json(command.get("result_json"), {}).get("impact") or {}
        if service._needs_second_approval(conn, command["organization_id"], command["bot_id"], command.get("detected_intent"), impact):
            execute(conn, "UPDATE operational_command_requests SET status = 'awaiting_second_approval', updated_at = ? WHERE id = ?", (utcnow_iso(), command["id"]))
            return {"handled": True, "reply_text": "Este comando quedó pendiente de aprobación final desde el portal por ser de alto impacto.", "status": "awaiting_second_approval"}
        result = service._execute_command(conn, command_id=command["id"])
        return {"handled": True, "reply_text": result.get("reply_text") or "Listo. El comando quedó ejecutado.", "status": result.get("status"), "command": result}
    if parsed.get("intent") == "command.cancel_by_code":
        command = fetch_one(conn, "SELECT * FROM operational_command_requests WHERE bot_id = ? AND actor_phone_e164 = ? AND confirmation_code = ? ORDER BY created_at DESC LIMIT 1", (bot_id, phone, parsed.get("entities", {}).get("confirmation_code")))
        if not command:
            return {"handled": True, "reply_text": "No encontré un comando pendiente con ese código.", "status": "not_found"}
        if command.get("status") in {"awaiting_confirmation", "awaiting_second_approval", "scheduled", "queued"}:
            service._cancel_command_internal(conn, command, reason="cancelled_from_whatsapp")
            return {"handled": True, "reply_text": "Listo. Cancelé el comando pendiente.", "status": "cancelled"}
        if command.get("status") == "executed":
            undo = service._undo_command_internal(conn, command, actor_user_id=None, reason="undo_from_whatsapp")
            return {"handled": True, "reply_text": undo.get("reply_text") or "Listo. Revertí el último comando posible.", "status": undo.get("status", "reverted")}
        return {"handled": True, "reply_text": "Ese comando ya no se puede cancelar.", "status": "not_cancellable"}
    if not parsed.get("intent"):
        return {"handled": True, "reply_text": parsed.get("reply_text") or "No pude entender el comando operativo. Puedo ayudarte a pausar el bot, bloquear horarios o avisar citas afectadas.", "status": "ambiguous"}
    if authorized and not service._number_allows_intent(authorized, parsed["intent"]):
        service._create_alert(conn, organization_id=bot["organization_id"], bot_id=bot_id, command_id=None, alert_type="forbidden_intent", title="Intento fuera de scope", body=f"El número {phone} intentó ejecutar {parsed['intent']} fuera de sus permisos.", severity="warning", details={"phone": phone, "intent": parsed["intent"]})
        return {"handled": True, "reply_text": "Este número no tiene permiso para ejecutar ese tipo de comando. Usa el portal o pide una autorización más amplia.", "status": "forbidden"}
    if authorized:
        parsed = service._apply_authorized_scope(parsed, authorized)
    limit_check = service._check_operational_rate_limit(conn, organization_id=bot["organization_id"], bot_id=bot_id, actor_key=phone, source_channel="whatsapp", intent=parsed.get("intent"))
    if not limit_check.get("allowed"):
        service._create_alert(conn, organization_id=bot["organization_id"], bot_id=bot_id, command_id=None, alert_type="rate_limit", title="Rate limit operativo", body=f"El número {phone} excedió el límite para {parsed.get('intent')}.", severity="warning", details=limit_check)
        return {"handled": True, "reply_text": "Llegaste al límite temporal de comandos operativos. Espera unos minutos o usa el portal para revisar el estado.", "status": "rate_limited"}
    impact = service._build_impact(conn, bot, parsed)
    command = service._create_command(conn, bot=bot, source_channel="whatsapp", actor_user_id=None, actor_phone_e164=phone, raw_text=body, parsed=parsed, impact=impact, source_message_id=inbound_message_id, source_webhook_receipt_id=external_id)
    if service._requires_confirmation(parsed["intent"], impact):
        code = service._confirmation_code(command["id"])
        execute(conn, "UPDATE operational_command_requests SET status = 'awaiting_confirmation', confirmation_code = ?, requires_confirmation = 1, updated_at = ? WHERE id = ?", (code, utcnow_iso(), command["id"]))
        return {"handled": True, "reply_text": service._preview_reply(parsed["intent"], parsed.get("entities", {}), impact, True, confirmation_code=code), "status": "awaiting_confirmation"}
    result = service._execute_command(conn, command_id=command["id"])
    return {"handled": True, "reply_text": result.get("reply_text") or "Listo. El comando quedó ejecutado.", "status": result.get("status"), "command": result}
