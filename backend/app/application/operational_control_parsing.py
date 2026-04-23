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

class OperationalControlParsingMixin:
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
