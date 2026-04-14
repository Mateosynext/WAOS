from __future__ import annotations

from typing import Any

from ..config import settings
from ..utils import from_json, new_id, slugify, to_json, utcnow_iso

def fetch_one(conn, sql: str, params=()):
    row = conn.execute(sql, tuple(params)).fetchone()
    return dict(row) if row else None


def fetch_all(conn, sql: str, params=()):
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def execute(conn, sql: str, params=()):
    conn.execute(sql, tuple(params))
    conn.commit()


def create_audit_log(conn, *, organization_id: str | None, actor_user_id: str | None, actor_type: str, entity_type: str, entity_id: str | None, action: str, metadata: dict[str, Any] | None = None) -> None:
    execute(conn, """
        INSERT INTO audit_logs (id, organization_id, actor_user_id, actor_type, entity_type, entity_id, action, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (new_id('audit'), organization_id, actor_user_id, actor_type, entity_type, entity_id, action, to_json(metadata or {}), utcnow_iso()))


V9_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS catalog_categories (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'product',
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, slug),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_categories_org ON catalog_categories(organization_id, kind, sort_order);

CREATE TABLE IF NOT EXISTS catalog_products (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    category_id TEXT,
    name TEXT NOT NULL,
    sku TEXT,
    short_description TEXT,
    long_description TEXT,
    price REAL NOT NULL DEFAULT 0,
    promotional_price REAL,
    currency TEXT NOT NULL DEFAULT 'MXN',
    status TEXT NOT NULL DEFAULT 'active',
    priority INTEGER NOT NULL DEFAULT 50,
    tags_json TEXT NOT NULL DEFAULT '[]',
    specs_json TEXT NOT NULL DEFAULT '{}',
    benefits_json TEXT NOT NULL DEFAULT '[]',
    faq_json TEXT NOT NULL DEFAULT '[]',
    related_products_json TEXT NOT NULL DEFAULT '[]',
    checkout_url TEXT,
    availability_json TEXT NOT NULL DEFAULT '{}',
    delivery_eta TEXT,
    stock_visibility TEXT NOT NULL DEFAULT 'visible',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (category_id) REFERENCES catalog_categories(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_products_org ON catalog_products(organization_id, status, priority);
CREATE INDEX IF NOT EXISTS idx_catalog_products_bot ON catalog_products(bot_id, updated_at);

CREATE TABLE IF NOT EXISTS catalog_product_variants (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    sku TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    price REAL,
    promotional_price REAL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (product_id) REFERENCES catalog_products(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_variants_product ON catalog_product_variants(product_id, status);

CREATE TABLE IF NOT EXISTS catalog_services (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    category_id TEXT,
    name TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    price REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'MXN',
    preparation TEXT,
    restrictions TEXT,
    availability_json TEXT NOT NULL DEFAULT '{}',
    photos_json TEXT NOT NULL DEFAULT '[]',
    associated_staff TEXT,
    branch TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (category_id) REFERENCES catalog_categories(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_services_org ON catalog_services(organization_id, status, updated_at);

CREATE TABLE IF NOT EXISTS media_assets (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    product_id TEXT,
    service_id TEXT,
    promotion_id TEXT,
    asset_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER NOT NULL DEFAULT 0,
    format TEXT,
    alt_text TEXT,
    label TEXT,
    category TEXT,
    usage_scope TEXT NOT NULL DEFAULT 'general',
    file_url TEXT,
    preview_url TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (product_id) REFERENCES catalog_products(id),
    FOREIGN KEY (service_id) REFERENCES catalog_services(id)
);
CREATE INDEX IF NOT EXISTS idx_media_assets_org ON media_assets(organization_id, asset_type, category, updated_at);

CREATE TABLE IF NOT EXISTS catalog_product_assets (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    variant_id TEXT,
    media_asset_id TEXT NOT NULL,
    asset_role TEXT NOT NULL DEFAULT 'gallery',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (product_id) REFERENCES catalog_products(id),
    FOREIGN KEY (variant_id) REFERENCES catalog_product_variants(id),
    FOREIGN KEY (media_asset_id) REFERENCES media_assets(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_product_assets_product ON catalog_product_assets(product_id, variant_id, sort_order);

CREATE TABLE IF NOT EXISTS catalog_inventory (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    variant_id TEXT,
    branch TEXT,
    status TEXT NOT NULL DEFAULT 'available',
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    min_stock INTEGER NOT NULL DEFAULT 0,
    visible_to_bot INTEGER NOT NULL DEFAULT 1,
    replacement_product_id TEXT,
    waitlist_enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (product_id) REFERENCES catalog_products(id),
    FOREIGN KEY (variant_id) REFERENCES catalog_product_variants(id),
    FOREIGN KEY (replacement_product_id) REFERENCES catalog_products(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_inventory_product ON catalog_inventory(product_id, variant_id, status);

CREATE TABLE IF NOT EXISTS catalog_promotions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    name TEXT NOT NULL,
    promo_type TEXT NOT NULL,
    message_short TEXT,
    message_long TEXT,
    banner_asset_id TEXT,
    applies_to_json TEXT NOT NULL DEFAULT '{}',
    channels_json TEXT NOT NULL DEFAULT '[]',
    starts_at TEXT,
    ends_at TEXT,
    stock_limit INTEGER,
    branch TEXT,
    priority INTEGER NOT NULL DEFAULT 50,
    cta_label TEXT,
    cta_url TEXT,
    legal_terms TEXT,
    promo_code TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    auto_offer_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (banner_asset_id) REFERENCES media_assets(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_promotions_org ON catalog_promotions(organization_id, status, priority);

CREATE TABLE IF NOT EXISTS catalog_promotion_rules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    promotion_id TEXT NOT NULL,
    name TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    conditions_json TEXT NOT NULL DEFAULT '{}',
    action_json TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 50,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (promotion_id) REFERENCES catalog_promotions(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_promo_rules_promo ON catalog_promotion_rules(promotion_id, is_active, priority);

CREATE TABLE IF NOT EXISTS bot_response_templates (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    template_key TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    title TEXT,
    content TEXT NOT NULL,
    variables_json TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id, template_key, channel),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);
CREATE INDEX IF NOT EXISTS idx_bot_templates_bot ON bot_response_templates(bot_id, channel, updated_at);

CREATE TABLE IF NOT EXISTS bot_behavior_settings (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    tone TEXT NOT NULL DEFAULT 'cercano',
    response_length TEXT NOT NULL DEFAULT 'media',
    use_emojis INTEGER NOT NULL DEFAULT 0,
    sales_intensity TEXT NOT NULL DEFAULT 'media',
    offer_promotions_when TEXT NOT NULL DEFAULT 'when_relevant',
    escalate_when_json TEXT NOT NULL DEFAULT '[]',
    insistence_policy TEXT NOT NULL DEFAULT 'respectful',
    can_share_price_directly INTEGER NOT NULL DEFAULT 1,
    can_negotiate INTEGER NOT NULL DEFAULT 0,
    can_mention_stock INTEGER NOT NULL DEFAULT 1,
    auto_send_images INTEGER NOT NULL DEFAULT 1,
    bot_mode TEXT NOT NULL DEFAULT 'hybrid',
    active_hours_json TEXT NOT NULL DEFAULT '[]',
    active_channels_json TEXT NOT NULL DEFAULT '["whatsapp"]',
    forbidden_topics_json TEXT NOT NULL DEFAULT '[]',
    required_phrases_json TEXT NOT NULL DEFAULT '[]',
    fallback_message TEXT NOT NULL DEFAULT 'Te ayudo con gusto, pero necesito un poco mas de detalle para responderte bien.',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);
CREATE INDEX IF NOT EXISTS idx_bot_behavior_bot ON bot_behavior_settings(bot_id, updated_at);

CREATE TABLE IF NOT EXISTS catalog_collections (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'collection',
    description TEXT,
    product_ids_json TEXT NOT NULL DEFAULT '[]',
    service_ids_json TEXT NOT NULL DEFAULT '[]',
    promotion_ids_json TEXT NOT NULL DEFAULT '[]',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_collections_org ON catalog_collections(organization_id, kind, sort_order);

CREATE TABLE IF NOT EXISTS product_question_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT,
    conversation_id TEXT,
    contact_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    intent TEXT NOT NULL,
    requested_variant TEXT,
    source_channel TEXT NOT NULL DEFAULT 'whatsapp',
    converted INTEGER NOT NULL DEFAULT 0,
    unanswered INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);
CREATE INDEX IF NOT EXISTS idx_product_question_logs_org ON product_question_logs(organization_id, entity_type, created_at);
"""


def ensure_v9_schema(conn) -> None:
    conn.executescript(V9_SCHEMA_SQL)
    conn.commit()


def _parse_row(row: dict, mapping: dict[str, Any]) -> dict:
    parsed = dict(row)
    for key, default in mapping.items():
        clean_key = key[:-5] if key.endswith("_json") else key
        parsed[clean_key] = from_json(parsed.get(key), default)
    return parsed


def _parse_product(conn, row: dict) -> dict:
    product = _parse_row(
        row,
        {
            "tags_json": [],
            "specs_json": {},
            "benefits_json": [],
            "faq_json": [],
            "related_products_json": [],
            "availability_json": {},
        },
    )
    variants = fetch_all(conn, "SELECT * FROM catalog_product_variants WHERE product_id = ? ORDER BY created_at ASC", (row["id"],))
    product["variants"] = [_parse_row(v, {"attributes_json": {}}) for v in variants]
    assets = fetch_all(
        conn,
        """
        SELECT a.*, pa.asset_role, pa.variant_id, pa.sort_order AS link_sort_order
        FROM catalog_product_assets pa
        JOIN media_assets a ON a.id = pa.media_asset_id
        WHERE pa.product_id = ?
        ORDER BY pa.sort_order ASC, a.created_at ASC
        """,
        (row["id"],),
    )
    product["assets"] = [_parse_row(a, {"metadata_json": {}}) for a in assets]
    product["inventory"] = fetch_all(conn, "SELECT * FROM catalog_inventory WHERE product_id = ? ORDER BY updated_at DESC", (row["id"],))
    return product


def _parse_service(row: dict) -> dict:
    return _parse_row(row, {"availability_json": {}, "photos_json": []})


def _parse_media(row: dict) -> dict:
    return _parse_row(row, {"metadata_json": {}})


def _parse_promotion(row: dict) -> dict:
    return _parse_row(row, {"applies_to_json": {}, "channels_json": []})


def _parse_rule(row: dict) -> dict:
    return _parse_row(row, {"conditions_json": {}, "action_json": {}})


def _parse_template(row: dict) -> dict:
    return _parse_row(row, {"variables_json": []})


def _parse_behavior(row: dict) -> dict:
    return _parse_row(
        row,
        {
            "escalate_when_json": [],
            "active_hours_json": [],
            "active_channels_json": [],
            "forbidden_topics_json": [],
            "required_phrases_json": [],
        },
    )


def create_catalog_category(conn, *, organization_id: str, name: str, kind: str = "product", description: str = "", sort_order: int = 0, is_active: bool = True, actor_user: dict | None = None) -> dict:
    now = utcnow_iso()
    row_id = new_id("cat")
    execute(
        conn,
        """
        INSERT INTO catalog_categories (id, organization_id, name, slug, kind, description, sort_order, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (row_id, organization_id, name, slugify(name), kind, description, sort_order, 1 if is_active else 0, now, now),
    )
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="catalog_category", entity_id=row_id, action="catalog.category_created", metadata={"name": name, "kind": kind})
    return fetch_one(conn, "SELECT * FROM catalog_categories WHERE id = ?", (row_id,)) or {}


def list_catalog_categories(conn, organization_id: str) -> list[dict]:
    return fetch_all(conn, "SELECT * FROM catalog_categories WHERE organization_id = ? ORDER BY kind ASC, sort_order ASC, name ASC", (organization_id,))


def create_catalog_product(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    name: str,
    category_id: str | None = None,
    sku: str | None = None,
    short_description: str = "",
    long_description: str = "",
    price: float = 0,
    promotional_price: float | None = None,
    currency: str = "MXN",
    status: str = "active",
    priority: int = 50,
    tags: list[str] | None = None,
    specs: dict[str, Any] | None = None,
    benefits: list[str] | None = None,
    faq: list[dict[str, Any]] | None = None,
    related_product_ids: list[str] | None = None,
    checkout_url: str | None = None,
    availability: dict[str, Any] | None = None,
    delivery_eta: str | None = None,
    stock_visibility: str = "visible",
    variants: list[dict[str, Any]] | None = None,
    inventory: list[dict[str, Any]] | None = None,
    actor_user: dict | None = None,
) -> dict:
    now = utcnow_iso()
    row_id = new_id("prod")
    execute(
        conn,
        """
        INSERT INTO catalog_products (
            id, organization_id, bot_id, category_id, name, sku, short_description, long_description,
            price, promotional_price, currency, status, priority, tags_json, specs_json, benefits_json,
            faq_json, related_products_json, checkout_url, availability_json, delivery_eta, stock_visibility,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id, organization_id, bot_id, category_id, name, sku, short_description, long_description,
            price, promotional_price, currency, status, priority, to_json(tags or []), to_json(specs or {}),
            to_json(benefits or []), to_json(faq or []), to_json(related_product_ids or []), checkout_url,
            to_json(availability or {}), delivery_eta, stock_visibility, now, now,
        ),
    )
    for variant in variants or []:
        execute(
            conn,
            """
            INSERT INTO catalog_product_variants (id, organization_id, product_id, name, sku, attributes_json, price, promotional_price, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("var"), organization_id, row_id, variant.get("name", "Variante"), variant.get("sku"),
                to_json(variant.get("attributes", {})), variant.get("price"), variant.get("promotional_price"), variant.get("status", "active"), now, now,
            ),
        )
    for inv in inventory or []:
        execute(
            conn,
            """
            INSERT INTO catalog_inventory (id, organization_id, product_id, variant_id, branch, status, stock_quantity, min_stock, visible_to_bot, replacement_product_id, waitlist_enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("inv"), organization_id, row_id, inv.get("variant_id"), inv.get("branch"), inv.get("status", "available"),
                int(inv.get("stock_quantity", 0)), int(inv.get("min_stock", 0)), 1 if inv.get("visible_to_bot", True) else 0,
                inv.get("replacement_product_id"), 1 if inv.get("waitlist_enabled", False) else 0, now,
            ),
        )
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="catalog_product", entity_id=row_id, action="catalog.product_created", metadata={"name": name, "status": status})
    row = fetch_one(conn, "SELECT * FROM catalog_products WHERE id = ?", (row_id,)) or {}
    return _parse_product(conn, row) if row else {}


def list_catalog_products(conn, organization_id: str, bot_id: str | None = None) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM catalog_products WHERE organization_id = ?"
    if bot_id:
        sql += " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    sql += " ORDER BY priority DESC, updated_at DESC"
    return [_parse_product(conn, row) for row in fetch_all(conn, sql, params)]


def create_catalog_service(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    name: str,
    category_id: str | None = None,
    duration_minutes: int = 30,
    price: float = 0,
    currency: str = "MXN",
    preparation: str = "",
    restrictions: str = "",
    availability: dict[str, Any] | None = None,
    photos: list[str] | None = None,
    associated_staff: str | None = None,
    branch: str | None = None,
    status: str = "active",
    actor_user: dict | None = None,
) -> dict:
    now = utcnow_iso()
    row_id = new_id("svc")
    execute(
        conn,
        """
        INSERT INTO catalog_services (id, organization_id, bot_id, category_id, name, duration_minutes, price, currency, preparation, restrictions, availability_json, photos_json, associated_staff, branch, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (row_id, organization_id, bot_id, category_id, name, duration_minutes, price, currency, preparation, restrictions, to_json(availability or {}), to_json(photos or []), associated_staff, branch, status, now, now),
    )
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="catalog_service", entity_id=row_id, action="catalog.service_created", metadata={"name": name})
    row = fetch_one(conn, "SELECT * FROM catalog_services WHERE id = ?", (row_id,)) or {}
    return _parse_service(row) if row else {}


def list_catalog_services(conn, organization_id: str, bot_id: str | None = None) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM catalog_services WHERE organization_id = ?"
    if bot_id:
        sql += " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    sql += " ORDER BY updated_at DESC"
    return [_parse_service(row) for row in fetch_all(conn, sql, params)]


def create_media_asset(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    asset_type: str,
    file_name: str,
    file_url: str,
    mime_type: str | None = None,
    file_size: int = 0,
    format: str | None = None,
    alt_text: str = "",
    label: str = "",
    category: str = "",
    usage_scope: str = "general",
    preview_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    sort_order: int = 0,
    is_active: bool = True,
    product_id: str | None = None,
    service_id: str | None = None,
    promotion_id: str | None = None,
    actor_user: dict | None = None,
) -> dict:
    now = utcnow_iso()
    row_id = new_id("asset")
    execute(
        conn,
        """
        INSERT INTO media_assets (id, organization_id, bot_id, product_id, service_id, promotion_id, asset_type, file_name, mime_type, file_size, format, alt_text, label, category, usage_scope, file_url, preview_url, metadata_json, sort_order, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (row_id, organization_id, bot_id, product_id, service_id, promotion_id, asset_type, file_name, mime_type, file_size, format, alt_text, label, category, usage_scope, file_url, preview_url, to_json(metadata or {}), sort_order, 1 if is_active else 0, now, now),
    )
    if product_id:
        execute(conn, "INSERT INTO catalog_product_assets (id, organization_id, product_id, variant_id, media_asset_id, asset_role, sort_order, created_at) VALUES (?, ?, ?, NULL, ?, 'gallery', ?, ?)", (new_id("link"), organization_id, product_id, row_id, sort_order, now))
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="media_asset", entity_id=row_id, action="media.asset_created", metadata={"file_name": file_name, "asset_type": asset_type})
    row = fetch_one(conn, "SELECT * FROM media_assets WHERE id = ?", (row_id,)) or {}
    return _parse_media(row) if row else {}


def list_media_assets(conn, organization_id: str, bot_id: str | None = None) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM media_assets WHERE organization_id = ?"
    if bot_id:
        sql += " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    sql += " ORDER BY sort_order ASC, updated_at DESC"
    return [_parse_media(row) for row in fetch_all(conn, sql, params)]


def create_catalog_promotion(
    conn,
    *,
    organization_id: str,
    bot_id: str | None,
    name: str,
    promo_type: str,
    message_short: str = "",
    message_long: str = "",
    banner_asset_id: str | None = None,
    applies_to: dict[str, Any] | None = None,
    channels: list[str] | None = None,
    starts_at: str | None = None,
    ends_at: str | None = None,
    stock_limit: int | None = None,
    branch: str | None = None,
    priority: int = 50,
    cta_label: str | None = None,
    cta_url: str | None = None,
    legal_terms: str | None = None,
    promo_code: str | None = None,
    status: str = "draft",
    auto_offer_enabled: bool = True,
    actor_user: dict | None = None,
) -> dict:
    now = utcnow_iso()
    row_id = new_id("promo")
    execute(
        conn,
        """
        INSERT INTO catalog_promotions (id, organization_id, bot_id, name, promo_type, message_short, message_long, banner_asset_id, applies_to_json, channels_json, starts_at, ends_at, stock_limit, branch, priority, cta_label, cta_url, legal_terms, promo_code, status, auto_offer_enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (row_id, organization_id, bot_id, name, promo_type, message_short, message_long, banner_asset_id, to_json(applies_to or {}), to_json(channels or ["whatsapp"]), starts_at, ends_at, stock_limit, branch, priority, cta_label, cta_url, legal_terms, promo_code, status, 1 if auto_offer_enabled else 0, now, now),
    )
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="catalog_promotion", entity_id=row_id, action="promotion.created", metadata={"name": name, "status": status})
    row = fetch_one(conn, "SELECT * FROM catalog_promotions WHERE id = ?", (row_id,)) or {}
    return _parse_promotion(row) if row else {}


def list_catalog_promotions(conn, organization_id: str, bot_id: str | None = None) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM catalog_promotions WHERE organization_id = ?"
    if bot_id:
        sql += " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    sql += " ORDER BY priority DESC, updated_at DESC"
    return [_parse_promotion(row) for row in fetch_all(conn, sql, params)]


def create_promotion_rule(
    conn,
    *,
    organization_id: str,
    promotion_id: str,
    name: str,
    trigger_type: str,
    conditions: dict[str, Any] | None = None,
    action: dict[str, Any] | None = None,
    priority: int = 50,
    is_active: bool = True,
    actor_user: dict | None = None,
) -> dict:
    now = utcnow_iso()
    row_id = new_id("prule")
    execute(
        conn,
        """
        INSERT INTO catalog_promotion_rules (id, organization_id, promotion_id, name, trigger_type, conditions_json, action_json, priority, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (row_id, organization_id, promotion_id, name, trigger_type, to_json(conditions or {}), to_json(action or {}), priority, 1 if is_active else 0, now, now),
    )
    if actor_user:
        create_audit_log(conn, organization_id=organization_id, actor_user_id=actor_user.get("id"), actor_type="user", entity_type="promotion_rule", entity_id=row_id, action="promotion.rule_created", metadata={"name": name, "trigger_type": trigger_type})
    row = fetch_one(conn, "SELECT * FROM catalog_promotion_rules WHERE id = ?", (row_id,)) or {}
    return _parse_rule(row) if row else {}


def list_promotion_rules(conn, organization_id: str, promotion_id: str | None = None) -> list[dict]:
    params: list[Any] = [organization_id]
    sql = "SELECT * FROM catalog_promotion_rules WHERE organization_id = ?"
    if promotion_id:
        sql += " AND promotion_id = ?"
        params.append(promotion_id)
    sql += " ORDER BY priority DESC, updated_at DESC"
    return [_parse_rule(row) for row in fetch_all(conn, sql, params)]


def business_hub_overview(conn, organization_id: str, bot_id: str | None = None) -> dict:
    params: list[Any] = [organization_id]
    bot_sql = ""
    if bot_id:
        bot_sql = " AND (bot_id = ? OR bot_id IS NULL)"
        params.append(bot_id)
    def _count(sql: str, p: list[Any] | tuple[Any, ...]) -> int:
        row = fetch_one(conn, sql, p)
        return int((row or {}).get("value") or 0)
    counts = {
        "products": _count(f"SELECT COUNT(*) AS value FROM catalog_products WHERE organization_id = ?{bot_sql}", params),
        "services": _count(f"SELECT COUNT(*) AS value FROM catalog_services WHERE organization_id = ?{bot_sql}", params),
        "assets": _count(f"SELECT COUNT(*) AS value FROM media_assets WHERE organization_id = ?{bot_sql}", params),
        "promotions": _count(f"SELECT COUNT(*) AS value FROM catalog_promotions WHERE organization_id = ?{bot_sql} AND status IN ('active','draft')", params),
        "active_promotions": _count(f"SELECT COUNT(*) AS value FROM catalog_promotions WHERE organization_id = ?{bot_sql} AND status = 'active'", params),
        "templates": _count(f"SELECT COUNT(*) AS value FROM bot_response_templates WHERE organization_id = ?{bot_sql}", params),
    }
    no_stock = _count("SELECT COUNT(*) AS value FROM catalog_inventory WHERE organization_id = ? AND status = 'agotado'", (organization_id,))
    low_stock = _count("SELECT COUNT(*) AS value FROM catalog_inventory WHERE organization_id = ? AND status = 'bajo_stock'", (organization_id,))
    conversations = _count("SELECT COUNT(*) AS value FROM conversations WHERE organization_id = ? AND status IN ('ai_active','human_takeover','waiting_followup')", (organization_id,))
    leads = _count("SELECT COUNT(*) AS value FROM contacts WHERE organization_id = ? AND created_at >= datetime('now','-7 day')", (organization_id,))
    handoffs = _count("SELECT COUNT(*) AS value FROM conversations WHERE organization_id = ? AND human_takeover = 1", (organization_id,))
    appointments_today = _count("SELECT COUNT(*) AS value FROM appointments WHERE organization_id = ? AND substr(scheduled_for, 1, 10) = substr(datetime('now'), 1, 10)", (organization_id,))
    payments_row = fetch_one(conn, "SELECT COALESCE(SUM(amount), 0) AS value FROM commerce_payments WHERE organization_id = ? AND status = 'paid'", (organization_id,))
    top_products_rows = fetch_all(
        conn,
        """
        SELECT p.name, COUNT(*) AS total
        FROM product_question_logs q
        JOIN catalog_products p ON p.id = q.entity_id
        WHERE q.organization_id = ? AND q.entity_type = 'product'
        GROUP BY p.id, p.name
        ORDER BY total DESC, p.name ASC
        LIMIT 5
        """,
        (organization_id,),
    )
    failed_messages = _count("SELECT COUNT(*) AS value FROM outbox_messages WHERE organization_id = ? AND status IN ('failed','dead_letter')", (organization_id,))
    return {
        "summary": {
            "products": counts["products"],
            "services": counts["services"],
            "media_assets": counts["assets"],
            "promotions": counts["promotions"],
            "active_promotions": counts["active_promotions"],
            "templates": counts["templates"],
            "conversations_active": conversations,
            "new_leads_7d": leads,
            "appointments_today": appointments_today,
            "payments_attributed": float((payments_row or {}).get("value") or 0),
            "handoffs": handoffs,
            "out_of_stock": no_stock,
            "low_stock": low_stock,
            "failed_messages": failed_messages,
        },
        "top_products": top_products_rows,
        "attention": [
            {"type": "stock", "label": "Productos agotados", "value": no_stock},
            {"type": "quality", "label": "Mensajes fallidos", "value": failed_messages},
            {"type": "handoff", "label": "Chats escalados", "value": handoffs},
        ],
    }


def commerce_insights(conn, organization_id: str, bot_id: str | None = None) -> dict:
    params: list[Any] = [organization_id]
    bot_filter = ""
    if bot_id:
        bot_filter = " AND q.bot_id = ?"
        params.append(bot_id)
    top_products = fetch_all(
        conn,
        f"""
        SELECT p.name, COUNT(*) AS questions,
               SUM(CASE WHEN q.converted = 1 THEN 1 ELSE 0 END) AS conversions,
               SUM(CASE WHEN q.unanswered = 1 THEN 1 ELSE 0 END) AS unanswered
        FROM product_question_logs q
        JOIN catalog_products p ON p.id = q.entity_id
        WHERE q.organization_id = ?{bot_filter} AND q.entity_type = 'product'
        GROUP BY p.id, p.name
        ORDER BY questions DESC, conversions DESC
        LIMIT 10
        """,
        params,
    )
    top_assets = fetch_all(
        conn,
        """
        SELECT COALESCE(label, file_name) AS asset, COUNT(*) AS linked_products
        FROM media_assets
        WHERE organization_id = ?
        GROUP BY id, asset
        ORDER BY linked_products DESC, asset ASC
        LIMIT 10
        """,
        (organization_id,),
    )
    top_promos = fetch_all(
        conn,
        """
        SELECT p.name, COUNT(r.id) AS rules, p.status
        FROM catalog_promotions p
        LEFT JOIN catalog_promotion_rules r ON r.promotion_id = p.id AND r.is_active = 1
        WHERE p.organization_id = ?
        GROUP BY p.id, p.name, p.status
        ORDER BY rules DESC, p.priority DESC
        LIMIT 10
        """,
        (organization_id,),
    )
    status_rows = fetch_all(conn, "SELECT status, COUNT(*) AS total FROM catalog_inventory WHERE organization_id = ? GROUP BY status ORDER BY total DESC", (organization_id,))
    summary = {
        "products_asked": sum(int(item.get("questions") or 0) for item in top_products),
        "products_with_unanswered": sum(1 for item in top_products if int(item.get("unanswered") or 0) > 0),
        "promotions_active": sum(1 for item in top_promos if item.get("status") == "active"),
        "low_or_out_stock": sum(int(item.get("total") or 0) for item in status_rows if item.get("status") in {"bajo_stock", "agotado"}),
    }
    return {
        "summary": summary,
        "top_products": top_products,
        "top_assets": top_assets,
        "top_promotions": top_promos,
        "inventory_breakdown": status_rows,
        "recommendations": [
            "Refuerza productos con muchas preguntas y conversion baja.",
            "Usa banners activos solo en promociones con regla y CTA claro.",
            "Activa reemplazos para inventario agotado o bajo stock.",
        ],
    }
