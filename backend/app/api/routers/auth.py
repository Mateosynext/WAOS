from __future__ import annotations

from fastapi import APIRouter, Request

from ...application.auth_service import AuthService
from ...schemas import LoginRequest, RefreshTokenRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
service = AuthService()


@router.post("/login")
def login(payload: LoginRequest, request: Request, uow: CurrentUoW) -> dict:
    return service.login(uow, payload=payload, request=request)


@router.post("/refresh")
def refresh_login(payload: RefreshTokenRequest, request: Request, uow: CurrentUoW) -> dict:
    return service.refresh(uow, refresh_token=payload.refresh_token, request=request)


@router.post("/logout")
def logout(payload: RefreshTokenRequest, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.logout(uow, refresh_token=payload.refresh_token, user=user, request=request)


@router.get("/me")
def me(user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.me(uow, user=user)


@router.get("/sessions")
def sessions(user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.sessions(uow, user=user)


@router.post("/sessions/revoke-others")
def revoke_other_sessions(request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.revoke_other_sessions(uow, user=user, request=request)


@router.post("/sessions/{session_id}/revoke")
def revoke_session(session_id: str, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.revoke_session(uow, session_id=session_id, user=user, request=request)
