from __future__ import annotations

from fastapi import APIRouter

from .routers.appointments import router as appointments_router
from .routers.auth import router as auth_router
from .routers.automations import router as automations_router
from .routers.analytics import router as analytics_router
from .routers.bot_ops import router as bot_ops_router
from .routers.bots import router as bots_router
from .routers.commerce import router as commerce_router
from .routers.conversations import router as conversations_router
from .routers.crm_sales import router as crm_sales_router
from .routers.engagement import router as engagement_router
from .routers.integrations import router as integrations_router
from .routers.operations import router as operations_router
from .routers.organizations import router as organizations_router
from .routers.public import router as public_router
from .routers.reports import router as reports_router
from .routers.runtime import router as runtime_router
from .routers.security import router as security_router
from .routers.system import router as system_router
from .routers.transactions import router as transactions_router
from .routers.vertical_domains import router as vertical_domains_router
from .routers.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(webhooks_router)
api_router.include_router(auth_router)
api_router.include_router(organizations_router)
api_router.include_router(bots_router)
api_router.include_router(bot_ops_router)
api_router.include_router(conversations_router)
api_router.include_router(appointments_router)
api_router.include_router(system_router)
api_router.include_router(runtime_router)
api_router.include_router(integrations_router)
api_router.include_router(security_router)
api_router.include_router(automations_router)
api_router.include_router(analytics_router)
api_router.include_router(reports_router)
api_router.include_router(crm_sales_router)
api_router.include_router(commerce_router)
api_router.include_router(engagement_router)
api_router.include_router(operations_router)

api_router.include_router(transactions_router)
api_router.include_router(vertical_domains_router)
