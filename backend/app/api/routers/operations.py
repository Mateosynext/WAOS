from __future__ import annotations

from fastapi import APIRouter
from ..handlers.operations import list_runs, get_run, list_technical_logs, deliveries_list, notifications_list, notifications_mark_read, alert_events_list

router = APIRouter(tags=["operations"])

router.add_api_route('/api/v1/runs', list_runs, methods=["GET"])
router.add_api_route('/api/v1/runs/{run_id}', get_run, methods=["GET"])
router.add_api_route('/api/v1/logs/technical', list_technical_logs, methods=["GET"])
router.add_api_route('/api/v1/deliveries', deliveries_list, methods=["GET"])
router.add_api_route('/api/v1/notifications', notifications_list, methods=["GET"])
router.add_api_route('/api/v1/notifications/{notification_id}/read', notifications_mark_read, methods=["POST"])
router.add_api_route('/api/v1/alerts/events', alert_events_list, methods=["GET"])
