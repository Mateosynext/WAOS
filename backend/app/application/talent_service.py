from __future__ import annotations

from copy import deepcopy

from fastapi import HTTPException

from ..db import fetch_one
from ..repositories import create_audit_log, get_bot
from ..security import ensure_bot_access
from ..serializers import serialize_bot_details
from ..talent_runtime import confirm_candidate, default_talent_config, list_candidates, normalize_talent_config
from ..utils import from_json, new_id, to_json, utcnow_iso
from .support import require_permission
from .uow import UnitOfWork


class TalentService:
    def _get_bot(self, conn, user: dict, bot_id: str) -> dict:
        bot = get_bot(conn, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        return bot

    def _load_config(self, bot: dict) -> dict:
        config = from_json(bot.get("config_draft_json") or "{}", {})
        config.setdefault("talent", default_talent_config())
        config["talent"] = normalize_talent_config(config.get("talent"))
        return config

    def _save_config(self, conn, bot: dict, config: dict, *, user: dict, action: str, metadata: dict) -> dict:
        now = utcnow_iso()
        conn.execute("UPDATE bots SET config_draft_json = ?, updated_at = ? WHERE id = ?", (to_json(config), now, bot["id"]))
        create_audit_log(
            conn,
            organization_id=bot["organization_id"],
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="bot",
            entity_id=bot["id"],
            action=action,
            metadata=metadata,
        )
        return serialize_bot_details(conn, get_bot(conn, bot["id"]))

    def overview(self, uow: UnitOfWork, *, user: dict, bot_id: str) -> dict:
        conn = uow.conn
        bot = self._get_bot(conn, user, bot_id)
        config = self._load_config(bot)
        talent = config["talent"]
        vacancies = talent.get("vacancies", [])
        candidates = list_candidates(conn, bot_id=bot_id)
        without_schedule = [item for item in vacancies if item.get("status") == "active" and not str(item.get("interview_schedule") or "").strip()]
        return {
            "bot_id": bot_id,
            "bot_name": bot.get("name"),
            "config": talent,
            "vacancies": vacancies,
            "candidates": candidates,
            "summary": {
                "active_vacancies": len([item for item in vacancies if item.get("status") == "active"]),
                "draft_vacancies": len([item for item in vacancies if item.get("status") == "draft"]),
                "closed_vacancies": len([item for item in vacancies if item.get("status") == "closed"]),
                "vacancies_without_interview_schedule": len(without_schedule),
                "confirmed_candidates": len(candidates),
                "worker_keywords": len((talent.get("worker_recognition", {}) or {}).get("keywords", [])),
            },
        }

    def update_policy(self, uow: UnitOfWork, *, user: dict, bot_id: str, payload) -> dict:
        conn = uow.conn
        bot = self._get_bot(conn, user, bot_id)
        require_permission(user, bot["organization_id"], "bot.manage")
        config = self._load_config(bot)
        talent = normalize_talent_config(config.get("talent"))
        talent.update(
            {
                "enabled": payload.enabled,
                "vacancies_enabled": payload.vacancies_enabled,
                "worker_recognition_enabled": payload.worker_recognition_enabled,
                "never_silent": payload.never_silent,
                "default_handoff_on_unknown": payload.default_handoff_on_unknown,
            }
        )
        talent.setdefault("interview_policy", {})["no_schedule_message"] = payload.no_schedule_message
        talent.setdefault("salary_policy", {})["hide_message"] = payload.salary_hide_message
        talent.setdefault("worker_recognition", {})["keywords"] = payload.worker_keywords
        talent.setdefault("worker_recognition", {})["worker_fallback_message"] = payload.worker_fallback_message
        talent.setdefault("worker_recognition", {})["route_worker_to_human"] = payload.route_worker_to_human
        config["talent"] = normalize_talent_config(talent)
        bot = self._save_config(conn, bot, config, user=user, action="bot.talent_policy_updated", metadata={"enabled": payload.enabled, "vacancies": len(config["talent"].get("vacancies", []))})
        return self.overview(uow, user=user, bot_id=bot_id)

    def create_vacancy(self, uow: UnitOfWork, *, user: dict, bot_id: str, payload) -> dict:
        conn = uow.conn
        bot = self._get_bot(conn, user, bot_id)
        require_permission(user, bot["organization_id"], "bot.manage")
        config = self._load_config(bot)
        talent = normalize_talent_config(config.get("talent"))
        vacancies = list(talent.get("vacancies", []))
        vacancy = payload.model_dump()
        vacancy["id"] = new_id("vac")
        vacancies.append(vacancy)
        talent["vacancies"] = vacancies
        config["talent"] = normalize_talent_config(talent)
        self._save_config(conn, bot, config, user=user, action="bot.talent_vacancy_created", metadata={"vacancy_id": vacancy["id"], "title": vacancy["title"]})
        return next(item for item in config["talent"]["vacancies"] if item["id"] == vacancy["id"])

    def update_vacancy(self, uow: UnitOfWork, *, user: dict, bot_id: str, vacancy_id: str, payload) -> dict:
        conn = uow.conn
        bot = self._get_bot(conn, user, bot_id)
        require_permission(user, bot["organization_id"], "bot.manage")
        config = self._load_config(bot)
        talent = normalize_talent_config(config.get("talent"))
        updated = None
        vacancies: list[dict] = []
        for item in talent.get("vacancies", []):
            if item.get("id") == vacancy_id:
                merged = deepcopy(item)
                merged.update({k: v for k, v in payload.model_dump().items()})
                updated = merged
                vacancies.append(merged)
            else:
                vacancies.append(item)
        if updated is None:
            raise HTTPException(status_code=404, detail="Vacancy not found")
        talent["vacancies"] = vacancies
        config["talent"] = normalize_talent_config(talent)
        self._save_config(conn, bot, config, user=user, action="bot.talent_vacancy_updated", metadata={"vacancy_id": vacancy_id, "title": updated.get("title")})
        for item in config["talent"]["vacancies"]:
            if item["id"] == vacancy_id:
                return item
        raise HTTPException(status_code=500, detail="Updated vacancy not found")

    def list_candidates(self, uow: UnitOfWork, *, user: dict, bot_id: str) -> list[dict]:
        conn = uow.conn
        bot = self._get_bot(conn, user, bot_id)
        return list_candidates(conn, bot_id=bot["id"])

    def confirm_candidate(self, uow: UnitOfWork, *, user: dict, bot_id: str, payload) -> dict:
        conn = uow.conn
        bot = self._get_bot(conn, user, bot_id)
        require_permission(user, bot["organization_id"], "bot.manage")
        candidate = confirm_candidate(
            conn,
            organization_id=bot["organization_id"],
            bot_id=bot["id"],
            conversation_id=payload.conversation_id,
            contact_id=payload.contact_id,
            vacancy_id=payload.vacancy_id,
            vacancy_title=payload.vacancy_title,
            profile={"notes": payload.notes, "confirmed_by": user.get("id"), "confirmed_at": utcnow_iso()},
        )
        create_audit_log(
            conn,
            organization_id=bot["organization_id"],
            actor_user_id=user["id"],
            actor_type="user",
            entity_type="talent_candidate",
            entity_id=candidate.get("id"),
            action="talent.candidate_confirmed",
            metadata={"bot_id": bot_id, "vacancy_id": payload.vacancy_id, "contact_id": payload.contact_id},
        )
        return candidate
