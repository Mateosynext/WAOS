from __future__ import annotations

from .common import *
from ...security import get_optional_current_user
from ...verticals import get_vertical_profile, list_vertical_profiles
from ...vertical_10x import apply_subvertical_pack, build_strongest_verticals, enrich_vertical_profile_for_runtime, get_subvertical_profile
from ...schemas.commerce import VerticalSubverticalPackApplyRequest

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

def verticals_catalog(top_only: bool = Query(default=False), user: dict | None = Depends(get_optional_current_user)) -> list[dict]:
    _ = user
    profiles = list_vertical_profiles()
    return build_strongest_verticals(profiles) if top_only else profiles


def vertical_profile_get(vertical: str | None = Query(default=None), subvertical: str | None = Query(default=None), organization_id: str | None = Query(default=None), bot_id: str | None = Query(default=None), user: dict | None = Depends(get_optional_current_user)) -> dict:
    resolved_vertical = vertical
    bot: dict | None = None
    org: dict | None = None
    needs_database_context = bool(bot_id or organization_id)
    if not needs_database_context:
        profile = get_vertical_profile(resolved_vertical)
        if subvertical:
            selected = get_subvertical_profile(profile, subvertical)
            if not selected:
                raise HTTPException(status_code=404, detail="Subvertical not found")
            profile = {**profile, "selected_subvertical": selected}
        return profile
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required for organization or bot scoped vertical profile")
    with get_connection() as conn:
        if bot_id:
            bot = get_bot(conn, bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            ensure_bot_access(user, bot)
            resolved_vertical = bot.get("vertical") or resolved_vertical
            organization_id = organization_id or bot.get("organization_id")
        if organization_id:
            ensure_org_access(user, organization_id)
            org = get_org(conn, organization_id)
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")
            resolved_vertical = resolved_vertical or org.get("vertical")
        profile = get_vertical_profile(resolved_vertical)
        return enrich_vertical_profile_for_runtime(conn, profile=profile, organization_id=organization_id, bot=bot, org=org, subvertical=subvertical)


def vertical_subvertical_profile_get(vertical: str, subvertical: str | None = Query(default=None), user: dict | None = Depends(get_optional_current_user)) -> dict:
    _ = user
    profile = get_vertical_profile(vertical)
    selected = get_subvertical_profile(profile, subvertical)
    if not selected:
        raise HTTPException(status_code=404, detail="Subvertical not found")
    return {"vertical": profile.get("id"), "vertical_name": profile.get("name"), "subvertical_profile": selected}


def vertical_apply_subvertical_pack(payload: VerticalSubverticalPackApplyRequest, user: dict = Depends(get_current_user)) -> dict:
    ensure_org_access(user, payload.organization_id)
    _require_permission(user, payload.organization_id, "bot.manage")
    with get_connection() as conn:
        bot = get_bot(conn, payload.bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        ensure_bot_access(user, bot)
        profile = get_vertical_profile(payload.vertical)
        return apply_subvertical_pack(conn, profile=profile, organization_id=payload.organization_id, bot_id=payload.bot_id, subvertical=payload.subvertical, actor_user=user)


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
