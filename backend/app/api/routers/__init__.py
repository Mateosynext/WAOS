from .appointments import router as appointments_router
from .auth import router as auth_router
from .bots import router as bots_router
from .conversations import router as conversations_router
from .organizations import router as organizations_router

__all__ = [
    'appointments_router',
    'auth_router',
    'bots_router',
    'conversations_router',
    'organizations_router',
]
