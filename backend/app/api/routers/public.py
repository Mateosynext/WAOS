from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from ..handlers.public import root, app_console, health, health_live, health_ready, public_sso_providers

router = APIRouter(tags=["public"])

router.add_api_route('/', root, methods=["GET"], response_class=HTMLResponse)
router.add_api_route('/app', app_console, methods=["GET"])
router.add_api_route('/health', health, methods=["GET"])
router.add_api_route('/health/live', health_live, methods=["GET"])
router.add_api_route('/health/ready', health_ready, methods=["GET"])
router.add_api_route('/api/public/sso/providers', public_sso_providers, methods=["GET"])
