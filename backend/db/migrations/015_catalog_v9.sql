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
