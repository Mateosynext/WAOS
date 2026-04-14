from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ...application.security_service import security_service
from ...schemas import MFAActivateRequest, MFARecoveryCodesRegenerateRequest, SecurityPolicyUpsertRequest, SSOProviderUpsertRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(tags=["security"])


@router.get("/api/v1/access/matrix")
def access_matrix(user: CurrentUser) -> dict:
    return security_service.access_matrix(user=user)


@router.get("/api/v1/security/mfa")
def get_mfa_status(user: CurrentUser, uow: CurrentUoW) -> dict:
    return security_service.get_mfa_status(uow, user=user)


@router.post("/api/v1/security/mfa/enroll")
def enroll_mfa(request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return security_service.enroll_mfa(uow, user=user, request=request)


@router.post("/api/v1/security/mfa/activate")
def activate_mfa(payload: MFAActivateRequest, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return security_service.activate_mfa(uow, payload=payload, user=user, request=request)


@router.post("/api/v1/security/mfa/recovery-codes/regenerate")
def regenerate_mfa_recovery_codes(payload: MFARecoveryCodesRegenerateRequest, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return security_service.regenerate_mfa_recovery_codes(uow, payload=payload, user=user, request=request)


@router.get("/api/v1/security/policies")
def get_security_policies(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> dict:
    return security_service.get_security_policies(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/security/policies")
def upsert_security_policies(payload: SecurityPolicyUpsertRequest, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return security_service.upsert_security_policies(uow, payload=payload, user=user, request=request)


@router.get("/api/v1/security/sso")
def get_sso_providers(user: CurrentUser, uow: CurrentUoW, organization_id: str = Query(...)) -> list[dict]:
    return security_service.get_sso_providers(uow, organization_id=organization_id, user=user)


@router.post("/api/v1/security/sso")
def upsert_sso(payload: SSOProviderUpsertRequest, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return security_service.upsert_sso(uow, payload=payload, user=user, request=request)


@router.post("/api/v1/security/sso/{provider_id}/test")
def test_sso_provider(provider_id: str, user: CurrentUser, uow: CurrentUoW) -> dict:
    return security_service.test_sso_provider(uow, provider_id=provider_id, user=user)


@router.post("/api/v1/security/sso/{provider_id}/start")
def start_sso_provider(provider_id: str, uow: CurrentUoW) -> dict:
    return security_service.start_sso_provider(uow, provider_id=provider_id)


@router.get("/api/v1/security/sso/callback")
def finish_sso_provider(state: str, code: str, request: Request, uow: CurrentUoW) -> dict:
    return security_service.finish_sso_provider(uow, state=state, code=code, request=request)
