from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends, Request

from ..application.uow import UnitOfWork
from ..request_context import build_request_context
from ..security import get_current_user

CurrentUser = Annotated[dict, Depends(get_current_user)]


def get_uow(request: Request) -> Generator[UnitOfWork, None, None]:
    mode = "read" if request.method.upper() in {"GET", "HEAD", "OPTIONS"} else "write"
    request.state.transaction_mode = mode
    with UnitOfWork(mode=mode) as uow:
        uow.request_context = build_request_context(request)
        yield uow


CurrentUoW = Annotated[UnitOfWork, Depends(get_uow)]
