from __future__ import annotations

from fastapi import APIRouter
from ..handlers.automations import list_automation_rules, create_automation_rule, list_automation_jobs, process_due_jobs

router = APIRouter(tags=["automations"])

router.add_api_route('/api/v1/automations/rules', list_automation_rules, methods=["GET"])
router.add_api_route('/api/v1/automations/rules', create_automation_rule, methods=["POST"])
router.add_api_route('/api/v1/automations/jobs', list_automation_jobs, methods=["GET"])
router.add_api_route('/api/v1/automations/process-due', process_due_jobs, methods=["POST"])
