from __future__ import annotations

from .common import *
from ...verticals import get_vertical_profile, list_vertical_profiles

def business_hub_overview_route(
    organization_id: str | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return business_hub_overview(conn, organization_id, bot_id)

def categories_list(organization_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return list_catalog_categories(conn, organization_id)

def categories_create(payload: CatalogCategoryRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return create_catalog_category(conn, actor_user=user, **payload.model_dump())

def products_list(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return list_catalog_products(conn, organization_id, bot_id)

def products_create(payload: CatalogProductRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return create_catalog_product(conn, actor_user=user, **payload.model_dump())

def services_list(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return list_catalog_services(conn, organization_id, bot_id)

def services_create(payload: CatalogServiceRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return create_catalog_service(conn, actor_user=user, **payload.model_dump())

def media_assets_list(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return list_media_assets(conn, organization_id, bot_id)

def media_assets_create(payload: MediaAssetRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return create_media_asset(conn, actor_user=user, **payload.model_dump())

def promotions_list(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return list_catalog_promotions(conn, organization_id, bot_id)

def promotions_create(payload: CatalogPromotionRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return create_catalog_promotion(conn, actor_user=user, **payload.model_dump())

def promotion_rules_list(organization_id: str | None = Query(default=None), promotion_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return list_promotion_rules(conn, organization_id, promotion_id)

def promotion_rules_create(payload: PromotionRuleRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return create_promotion_rule(conn, actor_user=user, **payload.model_dump())

def verticals_catalog(user: dict = Depends(get_current_user)) -> list[dict]:
    _ = user
    return list_vertical_profiles()


def vertical_profile_get(vertical: str | None = Query(default=None), organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict:
    resolved_vertical = vertical
    with get_connection() as conn:
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
            resolved_vertical = bot.get("vertical") or resolved_vertical
        elif organization_id:
            ensure_org_access(user, organization_id)
            org = get_org(conn, organization_id)
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")
            resolved_vertical = org.get("vertical") or resolved_vertical
    return get_vertical_profile(resolved_vertical)


def bot_templates_list(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> list[dict]:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return list_bot_response_templates(conn, organization_id, bot_id)

def bot_templates_create(payload: BotResponseTemplateRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return upsert_bot_response_template(conn, actor_user=user, **payload.model_dump())

def bot_behavior_get(organization_id: str, bot_id: str, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return get_bot_behavior_settings(conn, organization_id, bot_id)

def bot_behavior_upsert(payload: BotBehaviorSettingsRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        return upsert_bot_behavior_settings(conn, actor_user=user, **payload.model_dump())

def commerce_insights_route(organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict = Depends(get_current_user)) -> dict:
    if not organization_id:
        organization_id = accessible_org_ids(user)[0] if accessible_org_ids(user) else None
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required")
    ensure_org_access(user, organization_id)
    with get_connection() as conn:
        return commerce_insights(conn, organization_id, bot_id)

def customer_experience_preview_route(payload: CustomerExperiencePreviewRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    with get_connection() as conn:
        return customer_experience_preview(conn, **payload.model_dump())
