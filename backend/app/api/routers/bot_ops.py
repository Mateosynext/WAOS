from __future__ import annotations

from fastapi import APIRouter
from ..handlers.bot_ops import validate_bot_draft, bot_versions_diff, list_bot_builds, get_release_requests, create_release_request_route, approve_release_request_route, publish_release_request_route, bot_release_readiness, bot_traceability, bot_library_templates, publish_schedules_list, publish_schedules_create, publish_schedule_runs_all, publish_schedule_runs_list, whatsapp_numbers_status, list_bot_simulation_cases, create_bot_simulation_case, run_bot_simulation, list_bot_simulation_runs, create_draft_snapshot

router = APIRouter(tags=["bot_ops"])

router.add_api_route('/api/v1/bots/{bot_id}/validate-draft', validate_bot_draft, methods=["GET"])
router.add_api_route('/api/v1/bots/{bot_id}/versions/diff', bot_versions_diff, methods=["GET"])
router.add_api_route('/api/v1/bots/{bot_id}/builds', list_bot_builds, methods=["GET"])
router.add_api_route('/api/v1/bots/{bot_id}/release-requests', get_release_requests, methods=["GET"])
router.add_api_route('/api/v1/bots/{bot_id}/release-requests', create_release_request_route, methods=["POST"])
router.add_api_route('/api/v1/bots/{bot_id}/release-readiness', bot_release_readiness, methods=["GET"])
router.add_api_route('/api/v1/release-requests/{release_id}/approve', approve_release_request_route, methods=["POST"])
router.add_api_route('/api/v1/release-requests/{release_id}/publish', publish_release_request_route, methods=["POST"])
router.add_api_route('/api/v1/bots/{bot_id}/traceability', bot_traceability, methods=["GET"])
router.add_api_route('/api/v1/bot-library/templates', bot_library_templates, methods=["GET"])
router.add_api_route('/api/v1/publish-schedules', publish_schedules_list, methods=["GET"])
router.add_api_route('/api/v1/publish-schedules', publish_schedules_create, methods=["POST"])
router.add_api_route('/api/v1/publish-schedule-runs', publish_schedule_runs_all, methods=["GET"])
router.add_api_route('/api/v1/publish-schedules/{schedule_id}/runs', publish_schedule_runs_list, methods=["GET"])
router.add_api_route('/api/v1/whatsapp/numbers/status', whatsapp_numbers_status, methods=["GET"])

router.add_api_route('/api/v1/bots/{bot_id}/simulation-cases', list_bot_simulation_cases, methods=['GET'])
router.add_api_route('/api/v1/bots/{bot_id}/simulation-cases', create_bot_simulation_case, methods=['POST'])
router.add_api_route('/api/v1/bots/{bot_id}/simulation-runs', list_bot_simulation_runs, methods=['GET'])
router.add_api_route('/api/v1/bots/{bot_id}/simulate', run_bot_simulation, methods=['POST'])
router.add_api_route('/api/v1/bots/{bot_id}/versions/draft-snapshot', create_draft_snapshot, methods=['POST'])
