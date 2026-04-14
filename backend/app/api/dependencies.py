from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends

from ..application.uow import UnitOfWork
from ..security import get_current_user

CurrentUser = Annotated[dict, Depends(get_current_user)]


def get_uow() -> Generator[UnitOfWork, None, None]:
    with UnitOfWork() as uow:
        yield uow


CurrentUoW = Annotated[UnitOfWork, Depends(get_uow)]
