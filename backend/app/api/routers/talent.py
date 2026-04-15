from __future__ import annotations

from fastapi import APIRouter

from ...application.talent_service import TalentService
from ...schemas import TalentCandidateConfirmRequest, TalentPolicyRequest, TalentVacancyRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["talent"])
service = TalentService()


@router.get("/api/v1/bots/{bot_id}/talent/overview")
def talent_overview(bot_id: str, user: CurrentUser = None, uow: CurrentUoW = None) -> dict:
    return service.overview(uow, user=user, bot_id=bot_id)


@router.patch("/api/v1/bots/{bot_id}/talent/policy")
def update_talent_policy(bot_id: str, payload: TalentPolicyRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.update_policy(uow, user=user, bot_id=bot_id, payload=payload)


@router.post("/api/v1/bots/{bot_id}/talent/vacancies")
def create_talent_vacancy(bot_id: str, payload: TalentVacancyRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.create_vacancy(uow, user=user, bot_id=bot_id, payload=payload)


@router.patch("/api/v1/bots/{bot_id}/talent/vacancies/{vacancy_id}")
def update_talent_vacancy(bot_id: str, vacancy_id: str, payload: TalentVacancyRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.update_vacancy(uow, user=user, bot_id=bot_id, vacancy_id=vacancy_id, payload=payload)


@router.get("/api/v1/bots/{bot_id}/talent/candidates")
def list_talent_candidates(bot_id: str, user: CurrentUser = None, uow: CurrentUoW = None) -> list[dict]:
    return service.list_candidates(uow, user=user, bot_id=bot_id)


@router.post("/api/v1/bots/{bot_id}/talent/candidates/confirm")
def confirm_talent_candidate(bot_id: str, payload: TalentCandidateConfirmRequest, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.confirm_candidate(uow, user=user, bot_id=bot_id, payload=payload)
