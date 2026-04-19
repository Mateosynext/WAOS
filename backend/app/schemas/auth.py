from __future__ import annotations

from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
EmailLikeStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
OtpCodeStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=6, max_length=16)]


class LoginRequest(BaseModel):
    email: EmailLikeStr
    password: Annotated[str, StringConstraints(min_length=8, max_length=256)]
    otp_code: OtpCodeStr | None = None
    challenge_id: NonEmptyStr | None = None
    mfa_setup_code: OtpCodeStr | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: NonEmptyStr


class MFAActivateRequest(BaseModel):
    code: OtpCodeStr


class MFARecoveryCodesRegenerateRequest(BaseModel):
    code: OtpCodeStr
