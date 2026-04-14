from __future__ import annotations

from fastapi import APIRouter
from ..handlers.analytics import analytics_dashboard, audit_logs, analytics_daily, read_i18n_config, write_i18n_config, read_i18n_analytics, read_omnichannel_overview, analytics_director_mode, analytics_funnel, analytics_operator_performance, analytics_objections, analytics_heatmap, analytics_contact_windows, analytics_closure_attribution

router = APIRouter(tags=["analytics"])

router.add_api_route('/api/v1/analytics/dashboard', analytics_dashboard, methods=["GET"])
router.add_api_route('/api/v1/audit/logs', audit_logs, methods=["GET"])
router.add_api_route('/api/v1/analytics/daily', analytics_daily, methods=["GET"])
router.add_api_route('/api/v1/i18n/config', read_i18n_config, methods=["GET"])
router.add_api_route('/api/v1/i18n/config', write_i18n_config, methods=["POST"])
router.add_api_route('/api/v1/i18n/analytics', read_i18n_analytics, methods=["GET"])
router.add_api_route('/api/v1/omnichannel/overview', read_omnichannel_overview, methods=["GET"])
router.add_api_route('/api/v1/analytics/director-mode', analytics_director_mode, methods=["GET"])
router.add_api_route('/api/v1/analytics/funnel', analytics_funnel, methods=["GET"])
router.add_api_route('/api/v1/analytics/operator-performance', analytics_operator_performance, methods=["GET"])
router.add_api_route('/api/v1/analytics/objections', analytics_objections, methods=["GET"])
router.add_api_route('/api/v1/analytics/heatmap', analytics_heatmap, methods=["GET"])
router.add_api_route('/api/v1/analytics/contact-windows', analytics_contact_windows, methods=["GET"])
router.add_api_route('/api/v1/analytics/closure-attribution', analytics_closure_attribution, methods=["GET"])
