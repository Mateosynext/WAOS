from __future__ import annotations

from fastapi import APIRouter
from ..handlers.reports import list_executive_report_jobs, queue_executive_report, create_executive_report, list_executive_reports, download_executive_report_pdf, report_schedules_list, report_schedules_create, report_schedule_runs_all, report_schedule_runs_list

router = APIRouter(tags=["reports"])

router.add_api_route('/api/v1/reports/executive/jobs', list_executive_report_jobs, methods=["GET"])
router.add_api_route('/api/v1/reports/executive/queue', queue_executive_report, methods=["POST"])
router.add_api_route('/api/v1/reports/executive/generate', create_executive_report, methods=["POST"])
router.add_api_route('/api/v1/reports/executive', list_executive_reports, methods=["GET"])
router.add_api_route('/api/v1/reports/executive/{report_id}/pdf', download_executive_report_pdf, methods=["GET"])
router.add_api_route('/api/v1/reports/schedules', report_schedules_list, methods=["GET"])
router.add_api_route('/api/v1/reports/schedules', report_schedules_create, methods=["POST"])
router.add_api_route('/api/v1/reports/schedule-runs', report_schedule_runs_all, methods=["GET"])
router.add_api_route('/api/v1/reports/schedules/{schedule_id}/runs', report_schedule_runs_list, methods=["GET"])
