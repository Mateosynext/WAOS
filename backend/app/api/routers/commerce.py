from __future__ import annotations

from fastapi import APIRouter
from ..handlers.commerce import business_hub_overview_route, categories_list, categories_create, products_list, products_create, services_list, services_create, media_assets_list, media_assets_create, promotions_list, promotions_create, promotion_rules_list, promotion_rules_create, verticals_catalog, vertical_profile_get, vertical_subvertical_profile_get, vertical_apply_subvertical_pack, bot_templates_list, bot_templates_create, bot_behavior_get, bot_behavior_upsert, commerce_insights_route, customer_experience_preview_route

router = APIRouter(tags=["commerce"])

router.add_api_route('/api/v1/business-hub/overview', business_hub_overview_route, methods=["GET"])
router.add_api_route('/api/v1/catalog/categories', categories_list, methods=["GET"])
router.add_api_route('/api/v1/catalog/categories', categories_create, methods=["POST"])
router.add_api_route('/api/v1/catalog/products', products_list, methods=["GET"])
router.add_api_route('/api/v1/catalog/products', products_create, methods=["POST"])
router.add_api_route('/api/v1/catalog/services', services_list, methods=["GET"])
router.add_api_route('/api/v1/catalog/services', services_create, methods=["POST"])
router.add_api_route('/api/v1/media/assets', media_assets_list, methods=["GET"])
router.add_api_route('/api/v1/media/assets', media_assets_create, methods=["POST"])
router.add_api_route('/api/v1/promotions', promotions_list, methods=["GET"])
router.add_api_route('/api/v1/promotions', promotions_create, methods=["POST"])
router.add_api_route('/api/v1/promotions/rules', promotion_rules_list, methods=["GET"])
router.add_api_route('/api/v1/promotions/rules', promotion_rules_create, methods=["POST"])
router.add_api_route('/api/v1/verticals', verticals_catalog, methods=["GET"])
router.add_api_route('/api/v1/verticals/profile', vertical_profile_get, methods=["GET"])
router.add_api_route('/api/v1/verticals/subvertical-profile', vertical_subvertical_profile_get, methods=["GET"])
router.add_api_route('/api/v1/verticals/apply-subvertical-pack', vertical_apply_subvertical_pack, methods=["POST"])
router.add_api_route('/api/v1/bot-studio/templates', bot_templates_list, methods=["GET"])
router.add_api_route('/api/v1/bot-studio/templates', bot_templates_create, methods=["POST"])
router.add_api_route('/api/v1/bot-studio/behavior', bot_behavior_get, methods=["GET"])
router.add_api_route('/api/v1/bot-studio/behavior', bot_behavior_upsert, methods=["POST"])
router.add_api_route('/api/v1/commerce/insights', commerce_insights_route, methods=["GET"])
router.add_api_route('/api/v1/customer-experience/preview', customer_experience_preview_route, methods=["POST"])
