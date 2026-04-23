from __future__ import annotations

from fastapi import APIRouter, Request

from ...application.auth_service import AuthService
from ...schemas import FlexibleSchema, LoginRequest, RefreshTokenRequest
from ..dependencies import CurrentUoW, CurrentUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
service = AuthService()


@router.post("/login", response_model=FlexibleSchema)
def login(payload: LoginRequest, request: Request, uow: CurrentUoW) -> dict:
    return service.login(uow, payload=payload, request=request)


@router.post("/refresh", response_model=FlexibleSchema)
def refresh_login(payload: RefreshTokenRequest, request: Request, uow: CurrentUoW) -> dict:
    return service.refresh(uow, refresh_token=payload.refresh_token, request=request)


@router.post("/logout", response_model=FlexibleSchema)
def logout(payload: RefreshTokenRequest, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.logout(uow, refresh_token=payload.refresh_token, user=user, request=request)


@router.get("/me", response_model=FlexibleSchema)
def me(user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.me(uow, user=user)


@router.get("/sessions", response_model=FlexibleSchema)
def sessions(user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.sessions(uow, user=user)


@router.post("/sessions/revoke-others", response_model=FlexibleSchema)
def revoke_other_sessions(request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.revoke_other_sessions(uow, user=user, request=request)


@router.post("/sessions/{session_id}/revoke", response_model=FlexibleSchema)
def revoke_session(session_id: str, request: Request, user: CurrentUser, uow: CurrentUoW) -> dict:
    return service.revoke_session(uow, session_id=session_id, user=user, request=request)
