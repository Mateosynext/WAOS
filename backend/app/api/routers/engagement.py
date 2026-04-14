from __future__ import annotations

from fastapi import APIRouter
from ..handlers.engagement import review_conversation_route, list_conversation_reviews, conversation_summary_on_demand, conversation_copilot, inbox_search, inbox_risk, list_conversation_tags, upsert_conversation_tags, memory_history, alerts_rules_list, alerts_rules_create, routing_rules_list, routing_rules_create, followup_experiments_list, followup_experiments_create, followup_experiments_send, followup_experiment_performance, followup_experiment_assignments_list, routing_assignments_list

router = APIRouter(tags=["engagement"])

router.add_api_route('/api/v1/conversations/{conversation_id}/review', review_conversation_route, methods=["POST"])
router.add_api_route('/api/v1/conversations/reviews', list_conversation_reviews, methods=["GET"])
router.add_api_route('/api/v1/conversations/{conversation_id}/summary-on-demand', conversation_summary_on_demand, methods=["POST"])
router.add_api_route('/api/v1/conversations/{conversation_id}/copilot', conversation_copilot, methods=["POST"])
router.add_api_route('/api/v1/inbox/search', inbox_search, methods=["GET"])
router.add_api_route('/api/v1/inbox/risk', inbox_risk, methods=["GET"])
router.add_api_route('/api/v1/conversations/{conversation_id}/tags', list_conversation_tags, methods=["GET"])
router.add_api_route('/api/v1/conversations/{conversation_id}/tags', upsert_conversation_tags, methods=["POST"])
router.add_api_route('/api/v1/contacts/{contact_id}/memory/history', memory_history, methods=["GET"])
router.add_api_route('/api/v1/alerts/rules', alerts_rules_list, methods=["GET"])
router.add_api_route('/api/v1/alerts/rules', alerts_rules_create, methods=["POST"])
router.add_api_route('/api/v1/routing/rules', routing_rules_list, methods=["GET"])
router.add_api_route('/api/v1/routing/rules', routing_rules_create, methods=["POST"])
router.add_api_route('/api/v1/followups/experiments', followup_experiments_list, methods=["GET"])
router.add_api_route('/api/v1/followups/experiments', followup_experiments_create, methods=["POST"])
router.add_api_route('/api/v1/followups/experiments/{experiment_id}/send', followup_experiments_send, methods=["POST"])
router.add_api_route('/api/v1/followups/experiments/{experiment_id}/performance', followup_experiment_performance, methods=["GET"])
router.add_api_route('/api/v1/followups/assignments', followup_experiment_assignments_list, methods=["GET"])
router.add_api_route('/api/v1/routing/assignments', routing_assignments_list, methods=["GET"])
