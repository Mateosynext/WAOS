from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    email: str
    password: str
    otp_code: str | None = None
    challenge_id: str | None = None
    mfa_setup_code: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MFAActivateRequest(BaseModel):
    code: str


class MFARecoveryCodesRegenerateRequest(BaseModel):
    code: str
