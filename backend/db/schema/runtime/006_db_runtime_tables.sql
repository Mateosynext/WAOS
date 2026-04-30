-- 006_db_runtime_tables.sql
-- Cumulative schema slice for WAOS production hardened artifact.

CREATE TABLE IF NOT EXISTS activation_progress (
    id TEXT PRIMARY KEY,
    activated_channels_count INTEGER NOT NULL DEFAULT 0,
    agenda_ready TEXT,
    blockers_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    bots_ready_count INTEGER NOT NULL DEFAULT 0,
    catalog_items_count INTEGER NOT NULL DEFAULT 0,
    checklist_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    first_value_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    readiness_score REAL NOT NULL DEFAULT 0,
    recommended_next_step TEXT,
    status TEXT,
    tenant_mode TEXT,
    ttfv_hours TEXT,
    updated_at TEXT,
    vertical TEXT
);

CREATE TABLE IF NOT EXISTS agenda_blocked_slots (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    created_by_user_id TEXT,
    end_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    reason TEXT,
    start_at TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS agenda_reminder_preferences (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT,
    hours_before TEXT,
    last_hours TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    tone TEXT,
    updated_at TEXT,
    updated_by_user_id TEXT
);

CREATE TABLE IF NOT EXISTS agenda_resource_capacity_rules (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    created_by TEXT,
    day_of_week TEXT,
    end_time TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    resource_id TEXT,
    slot_capacity TEXT,
    start_time TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS agenda_resources (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    branch TEXT,
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    resource_type TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_policy_evaluations (
    id TEXT PRIMARY KEY,
    agent_routing_run_id TEXT,
    bot_id TEXT,
    budget_state_json TEXT NOT NULL DEFAULT '{}',
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    decision_json TEXT NOT NULL DEFAULT '{}',
    enforcement_status TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    observed_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    policy_profile_key TEXT,
    policy_profile_version TEXT,
    requested_action TEXT,
    requires_human_review TEXT,
    sla_state_json TEXT NOT NULL DEFAULT '{}',
    specialist_agent_key TEXT,
    status TEXT,
    tool_execution_run_id TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_policy_packs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ai_workflow_actions (
    id TEXT PRIMARY KEY,
    action_type TEXT,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    run_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ai_workflow_event_cursors (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    next_sequence TEXT,
    organization_id TEXT,
    run_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ai_workflow_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    dedupe_key TEXT,
    entity_id TEXT,
    entity_type TEXT,
    event_type TEXT,
    message TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    progress TEXT,
    run_id TEXT,
    sequence TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ai_workflow_runs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    cost_estimate_usd REAL NOT NULL DEFAULT 0,
    created_at TEXT,
    current_step TEXT,
    error_json TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT,
    intensity TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    progress TEXT,
    prompt TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT,
    user_id TEXT,
    workflow_type TEXT
);

CREATE TABLE IF NOT EXISTS ai_workflow_steps (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    completed_at TEXT,
    cost_estimate_usd REAL NOT NULL DEFAULT 0,
    created_at TEXT,
    error_json TEXT NOT NULL DEFAULT '{}',
    input_json TEXT NOT NULL DEFAULT '{}',
    latency_ms REAL NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    output_json TEXT NOT NULL DEFAULT '{}',
    retry_count INTEGER NOT NULL DEFAULT 0,
    run_id TEXT,
    started_at TEXT,
    status TEXT,
    step_key TEXT,
    step_label TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS appointment_notification_batches (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    command_id TEXT,
    created_at TEXT,
    created_by TEXT,
    kind TEXT,
    message_text TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    scope_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS appointment_notification_targets (
    id TEXT PRIMARY KEY,
    appointment_id TEXT,
    batch_id TEXT,
    bot_id TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    delivery_status TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS appointment_resource_assignments (
    id TEXT PRIMARY KEY,
    appointment_id TEXT,
    assigned_by TEXT,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    note TEXT,
    organization_id TEXT,
    resource_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    cancelled_at TEXT,
    confirmed_at TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    duration_minutes REAL NOT NULL DEFAULT 0,
    external_id TEXT,
    followup_sent_at TEXT,
    followup_status TEXT,
    integration_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    no_show_at TEXT,
    notes TEXT,
    organization_id TEXT,
    payment_id TEXT,
    payment_status TEXT,
    provider TEXT,
    provider_payload_json TEXT NOT NULL DEFAULT '{}',
    reconciliation_status TEXT,
    reminder_scheduled_at TEXT,
    rescheduled_from_appointment_id TEXT,
    scheduled_for TEXT,
    status TEXT,
    synced_at TEXT,
    timezone TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS auth_login_attempts (
    id TEXT PRIMARY KEY,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    blocked_until TEXT,
    bot_id TEXT,
    created_at TEXT,
    first_attempt_at INTEGER NOT NULL DEFAULT 0,
    last_attempt_at INTEGER NOT NULL DEFAULT 0,
    last_ip_address TEXT,
    last_user_agent TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    scope_key TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    family_id TEXT,
    issued_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    previous_token_hash TEXT,
    replaced_by_token_hash TEXT,
    reuse_detected_at TEXT,
    revoked_at TEXT,
    rotated_at TEXT,
    session_id TEXT,
    status TEXT,
    token_hash TEXT,
    updated_at TEXT,
    used_at TEXT
);

CREATE TABLE IF NOT EXISTS authorized_operational_numbers (
    id TEXT PRIMARY KEY,
    allowed_intents_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    created_at TEXT,
    created_by TEXT,
    last_used_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    phone_e164 TEXT,
    role TEXT,
    scope_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT,
    verified_at TEXT
);

CREATE TABLE IF NOT EXISTS automation_rules (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    rule_type TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS availability_overrides (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    command_id TEXT,
    created_at TEXT,
    created_by TEXT,
    end_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    override_type TEXT,
    reason TEXT,
    scope_json TEXT NOT NULL DEFAULT '{}',
    start_at TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_behavior_settings (
    id TEXT PRIMARY KEY,
    active_channels_json TEXT NOT NULL DEFAULT '{}',
    active_hours_json TEXT NOT NULL DEFAULT '{}',
    auto_send_images TEXT,
    bot_id TEXT,
    bot_mode TEXT,
    can_mention_stock TEXT,
    can_negotiate TEXT,
    can_share_price_directly TEXT,
    created_at TEXT,
    escalate_when_json TEXT NOT NULL DEFAULT '{}',
    fallback_message TEXT,
    forbidden_topics_json TEXT NOT NULL DEFAULT '{}',
    insistence_policy TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    offer_promotions_when TEXT,
    organization_id TEXT,
    required_phrases_json TEXT NOT NULL DEFAULT '{}',
    response_length TEXT,
    sales_intensity TEXT,
    status TEXT,
    tone TEXT,
    updated_at TEXT,
    use_emojis TEXT
);

CREATE TABLE IF NOT EXISTS bot_builds (
    id TEXT PRIMARY KEY,
    artifact_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    created_at TEXT,
    diff_summary_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT,
    validation_json TEXT NOT NULL DEFAULT '{}',
    validation_status TEXT,
    version_id TEXT
);

CREATE TABLE IF NOT EXISTS bot_decision_explanations (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    confidence_band TEXT,
    confidence_score REAL NOT NULL DEFAULT 0,
    conversation_id TEXT,
    created_at TEXT,
    explanation_json TEXT NOT NULL DEFAULT '{}',
    message_ai_run_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    risk_flags_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_language_configs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    default_language TEXT,
    detect_contact_language TEXT,
    fallback_language TEXT,
    handoff_respect_language TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    supported_languages_json TEXT NOT NULL DEFAULT '{}',
    templates_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_operational_state_history (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    command_id TEXT,
    created_at TEXT,
    created_by TEXT,
    message TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    new_state TEXT,
    organization_id TEXT,
    previous_state TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_response_templates (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    channel TEXT,
    content TEXT,
    created_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    template_key TEXT,
    title TEXT,
    updated_at TEXT,
    variables_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS bot_simulation_cases (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    created_by TEXT,
    expected_outcome_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    scenario_text TEXT,
    status TEXT,
    tags_json TEXT NOT NULL DEFAULT '{}',
    title TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_simulation_run_results (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    passed TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    simulation_case_id TEXT,
    simulation_run_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_simulation_runs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    cases_total INTEGER NOT NULL DEFAULT 0,
    compare_target TEXT,
    created_at TEXT,
    created_by TEXT,
    failed_count INTEGER NOT NULL DEFAULT 0,
    left_version_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    passed_count INTEGER NOT NULL DEFAULT 0,
    right_version_id TEXT,
    status TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bot_versions (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    notes TEXT,
    organization_id TEXT,
    status TEXT,
    updated_at TEXT,
    version_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS catalog_categories (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    kind TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    slug TEXT,
    sort_order TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS catalog_inventory (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    branch TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    min_stock TEXT,
    organization_id TEXT,
    product_id TEXT,
    replacement_product_id TEXT,
    status TEXT,
    stock_quantity TEXT,
    updated_at TEXT,
    variant_id TEXT,
    visible_to_bot TEXT,
    waitlist_enabled INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS catalog_product_assets (
    id TEXT PRIMARY KEY,
    asset_role TEXT,
    bot_id TEXT,
    created_at TEXT,
    media_asset_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    product_id TEXT,
    sort_order TEXT,
    status TEXT,
    updated_at TEXT,
    variant_id TEXT
);

CREATE TABLE IF NOT EXISTS catalog_product_variants (
    id TEXT PRIMARY KEY,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    price TEXT,
    product_id TEXT,
    promotional_price TEXT,
    sku TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS catalog_products (
    id TEXT PRIMARY KEY,
    availability_json TEXT NOT NULL DEFAULT '{}',
    benefits_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    category_id TEXT,
    checkout_url TEXT,
    created_at TEXT,
    currency TEXT,
    delivery_eta TEXT,
    faq_json TEXT NOT NULL DEFAULT '{}',
    long_description TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    price TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    promotional_price TEXT,
    related_products_json TEXT NOT NULL DEFAULT '{}',
    short_description TEXT,
    sku TEXT,
    specs_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    stock_visibility TEXT,
    tags_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS catalog_promotion_rules (
    id TEXT PRIMARY KEY,
    action_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    conditions_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    promotion_id TEXT,
    status TEXT,
    trigger_type TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS catalog_promotions (
    id TEXT PRIMARY KEY,
    applies_to_json TEXT NOT NULL DEFAULT '{}',
    auto_offer_enabled INTEGER NOT NULL DEFAULT 0,
    banner_asset_id TEXT,
    bot_id TEXT,
    branch TEXT,
    channels_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    cta_label TEXT,
    cta_url TEXT,
    ends_at TEXT,
    legal_terms TEXT,
    message_long TEXT,
    message_short TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    promo_code TEXT,
    promo_type TEXT,
    starts_at TEXT,
    status TEXT,
    stock_limit TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS catalog_quote_rules (
    id TEXT PRIMARY KEY,
    approval_rules_json TEXT NOT NULL DEFAULT '{}',
    base_price TEXT,
    bot_id TEXT,
    catalog_item_id TEXT,
    catalog_item_type TEXT,
    created_at TEXT,
    deposit_percent TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    minimum_quantity TEXT,
    organization_id TEXT,
    pricing_model TEXT,
    required_questions_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    terms TEXT,
    travel_fee TEXT,
    unit_label TEXT,
    updated_at TEXT,
    urgency_modifier_percent TEXT
);

CREATE TABLE IF NOT EXISTS catalog_services (
    id TEXT PRIMARY KEY,
    associated_staff TEXT,
    availability_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    branch TEXT,
    category_id TEXT,
    created_at TEXT,
    currency TEXT,
    duration_minutes REAL NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    photos_json TEXT NOT NULL DEFAULT '{}',
    preparation TEXT,
    price TEXT,
    restrictions TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS channel_events (
    id TEXT PRIMARY KEY,
    body TEXT,
    bot_id TEXT,
    channel TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    direction TEXT,
    event_type TEXT,
    external_thread_id TEXT,
    external_user_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS commercial_document_events (
    id TEXT PRIMARY KEY,
    actor_id TEXT,
    actor_type TEXT,
    bot_id TEXT,
    created_at TEXT,
    document_id TEXT,
    event_type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS commercial_document_items (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    description TEXT,
    discount INTEGER NOT NULL DEFAULT 0,
    document_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    quantity TEXT,
    sort_order TEXT,
    source_id TEXT,
    source_type TEXT,
    status TEXT,
    tax TEXT,
    total INTEGER NOT NULL DEFAULT 0,
    unit TEXT,
    unit_price TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS contact_memory_history (
    id TEXT PRIMARY KEY,
    after_json TEXT NOT NULL DEFAULT '{}',
    before_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    changed_at TEXT,
    changed_by TEXT,
    contact_id TEXT,
    contact_memory_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    email TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    phone TEXT,
    status TEXT,
    tags_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_assignment_history (
    id TEXT PRIMARY KEY,
    assignment_mode TEXT,
    bot_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    new_assigned_user_id TEXT,
    organization_id TEXT,
    previous_assigned_user_id TEXT,
    queue_role TEXT,
    reasoning_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_internal_notes (
    id TEXT PRIMARY KEY,
    author_user_id TEXT,
    bot_id TEXT,
    category TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    detail TEXT,
    message_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    next_steps_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    risk_flags_json TEXT NOT NULL DEFAULT '{}',
    risk_level TEXT,
    sources_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    summary TEXT,
    updated_at TEXT,
    visibility TEXT
);

CREATE TABLE IF NOT EXISTS conversation_reviews (
    id TEXT PRIMARY KEY,
    agent_user_id TEXT,
    bot_id TEXT,
    checklist_json TEXT NOT NULL DEFAULT '{}',
    conversation_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    missed_opportunities_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    quality_score REAL NOT NULL DEFAULT 0,
    recommendations_json TEXT NOT NULL DEFAULT '{}',
    response_delay_seconds INTEGER NOT NULL DEFAULT 0,
    review_type TEXT,
    status TEXT,
    tone TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    content_json TEXT NOT NULL DEFAULT '{}',
    conversation_id TEXT,
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    summary_type TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_tags (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    tag TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_takeover_briefs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    brief_type TEXT,
    contact_id TEXT,
    content_json TEXT NOT NULL DEFAULT '{}',
    conversation_id TEXT,
    created_at TEXT,
    generated_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    ai_active TEXT,
    assigned_user_id TEXT,
    automation_freeze_until TEXT,
    bot_id TEXT,
    contact_id TEXT,
    created_at TEXT,
    human_takeover TEXT,
    last_ai_at TEXT,
    last_human_at TEXT,
    last_message_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    paused_until TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS crm_leads (
    id TEXT PRIMARY KEY,
    best_next_action TEXT,
    bot_id TEXT,
    close_probability TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    detected_objections_json TEXT NOT NULL DEFAULT '{}',
    estimated_amount REAL NOT NULL DEFAULT 0,
    followup_at TEXT,
    language TEXT,
    last_qualification_at TEXT,
    lost_reason TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    next_action TEXT,
    notes TEXT,
    organization_id TEXT,
    owner_user_id TEXT,
    pipeline_json TEXT NOT NULL DEFAULT '{}',
    score_buying_intent REAL NOT NULL DEFAULT 0,
    source_campaign TEXT,
    source_channel TEXT,
    stage TEXT,
    status TEXT,
    tags_json TEXT NOT NULL DEFAULT '{}',
    temperature_status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS customer_feedback (
    id TEXT PRIMARY KEY,
    agent_user_id TEXT,
    bot_id TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    detractor_alert TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    reason TEXT,
    recovery_status TEXT,
    score_type REAL NOT NULL DEFAULT 0,
    score_value REAL NOT NULL DEFAULT 0,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS dead_letter_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    error TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    topic TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS delivery_attempts (
    id TEXT PRIMARY KEY,
    attempt_number INTEGER NOT NULL DEFAULT 0,
    body TEXT,
    bot_id TEXT,
    channel TEXT,
    conversation_id TEXT,
    created_at TEXT,
    delivered_at TEXT,
    entity_id TEXT,
    entity_type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    provider TEXT,
    scheduled_at TEXT,
    status TEXT,
    subject TEXT,
    target TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS domain_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    conversation_id TEXT,
    correlation_id TEXT,
    created_at TEXT,
    event_name TEXT,
    message_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS execution_runs (
    id TEXT PRIMARY KEY,
    attempt INTEGER NOT NULL DEFAULT 0,
    bot_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    duration_ms REAL NOT NULL DEFAULT 0,
    error_json TEXT NOT NULL DEFAULT '{}',
    execution_id TEXT,
    finished_at TEXT,
    input_json TEXT NOT NULL DEFAULT '{}',
    job_id TEXT,
    message_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    output_json TEXT NOT NULL DEFAULT '{}',
    queue_name TEXT,
    source_type TEXT,
    started_at TEXT,
    status TEXT,
    trace_id TEXT,
    updated_at TEXT,
    version_id TEXT
);

CREATE TABLE IF NOT EXISTS followup_experiment_assignments (
    id TEXT PRIMARY KEY,
    assigned_at TEXT,
    booked_at TEXT,
    bot_id TEXT,
    channel TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    experiment_id TEXT,
    last_event_at TEXT,
    message_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    replied_at TEXT,
    status TEXT,
    updated_at TEXT,
    variant TEXT,
    won_at TEXT
);

CREATE TABLE IF NOT EXISTS followup_experiments (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    channel TEXT,
    created_at TEXT,
    created_by TEXT,
    goal_metric TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    results_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT,
    variant_a_text TEXT,
    variant_b_text TEXT,
    vertical TEXT
);

CREATE TABLE IF NOT EXISTS go_live_readiness_reports (
    id TEXT PRIMARY KEY,
    blockers_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    can_apply TEXT,
    can_publish TEXT,
    canary_required INTEGER NOT NULL DEFAULT 0,
    created_at TEXT,
    human_confirmations_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    run_id TEXT,
    score REAL NOT NULL DEFAULT 0,
    status TEXT,
    updated_at TEXT,
    warnings_json TEXT NOT NULL DEFAULT '{}',
    wizard_id TEXT
);

CREATE TABLE IF NOT EXISTS human_confirmation_items (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    confirmed_value TEXT,
    created_at TEXT,
    field_key TEXT,
    label TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    reason TEXT,
    run_id TEXT,
    status TEXT,
    suggested_value TEXT,
    updated_at TEXT,
    wizard_id TEXT
);

CREATE TABLE IF NOT EXISTS human_reply_suggestions (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    draft_text TEXT,
    explanation_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    objective TEXT,
    operator_user_id TEXT,
    organization_id TEXT,
    risk_json TEXT NOT NULL DEFAULT '{}',
    sources_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    suggestion_text TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS inbound_message_locks (
    id TEXT PRIMARY KEY,
    acquired_at TEXT,
    bot_id TEXT,
    correlation_id TEXT,
    created_at TEXT,
    external_id TEXT,
    lock_key TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS inbox_saved_views (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    filter_json TEXT NOT NULL DEFAULT '{}',
    is_default INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    slug TEXT,
    status TEXT,
    updated_at TEXT,
    user_id TEXT
);

CREATE TABLE IF NOT EXISTS industry_playbooks (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    industry TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS integration_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    error_json TEXT NOT NULL DEFAULT '{}',
    event_type TEXT,
    external_reference TEXT,
    integration_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    provider TEXT,
    provider_status_code INTEGER NOT NULL DEFAULT 0,
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    severity TEXT,
    status TEXT,
    summary TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS integration_replay_requests (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    dry_run TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    requested_by TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT,
    webhook_receipt_id TEXT
);

CREATE TABLE IF NOT EXISTS integration_sync_runs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    direction TEXT,
    error_json TEXT NOT NULL DEFAULT '{}',
    finished_at TEXT,
    integration_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    started_at TEXT,
    status TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_document_versions (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    content_hash TEXT,
    content_text TEXT,
    created_at TEXT,
    document_id TEXT,
    extracted_entities_json TEXT NOT NULL DEFAULT '{}',
    freshness_status TEXT,
    is_current INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    source_snapshot_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    supports_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT,
    vector_json TEXT NOT NULL DEFAULT '{}',
    version_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    current_version_id TEXT,
    domain TEXT,
    freshness_window_days INTEGER NOT NULL DEFAULT 0,
    invalidated_reason TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    owner_type TEXT,
    refresh_after TEXT,
    refresh_strategy TEXT,
    source_key TEXT,
    source_kind TEXT,
    source_uri TEXT,
    status TEXT,
    tags_json TEXT NOT NULL DEFAULT '{}',
    title TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    source_id TEXT,
    status TEXT,
    text TEXT,
    updated_at TEXT,
    vector_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    content TEXT,
    created_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    item_type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    order_index TEXT,
    organization_id TEXT,
    status TEXT,
    title TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_refresh_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    document_id TEXT,
    event_type TEXT,
    freshness_after TEXT,
    freshness_before TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_source_connections (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    connector_key TEXT,
    created_at TEXT,
    current_snapshot_hash TEXT,
    label TEXT,
    last_error TEXT,
    last_published_at TEXT,
    last_seen_source_updated_at TEXT,
    last_synced_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    owner_user_id TEXT,
    publish_policy TEXT,
    source_key TEXT,
    source_uri TEXT,
    status TEXT,
    sync_interval_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT,
    validation_policy_json TEXT NOT NULL DEFAULT '{}',
    watch_mode TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_source_publications (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    external_item_key TEXT,
    knowledge_document_id TEXT,
    knowledge_version_id TEXT,
    last_synced_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    owner_user_id TEXT,
    published_at TEXT,
    source_connection_id TEXT,
    source_kind TEXT,
    source_updated_at TEXT,
    source_uri TEXT,
    state TEXT,
    status TEXT,
    updated_at TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_source_sync_items (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    change_status TEXT,
    created_at TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    external_item_key TEXT,
    knowledge_document_id TEXT,
    knowledge_version_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    publication_state TEXT,
    source_connection_id TEXT,
    source_uri TEXT,
    status TEXT,
    sync_run_id TEXT,
    title TEXT,
    updated_at TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_source_sync_runs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    error_text TEXT,
    finished_at TEXT,
    full_refresh TEXT,
    items_invalidated TEXT,
    items_published TEXT,
    items_seen TEXT,
    items_skipped TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    snapshot_hash TEXT,
    source_connection_id TEXT,
    started_at TEXT,
    status TEXT,
    trigger_kind TEXT,
    updated_at TEXT,
    validate_only TEXT
);

CREATE TABLE IF NOT EXISTS lead_stage_history (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    changed_by TEXT,
    created_at TEXT,
    crm_lead_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    new_stage TEXT,
    organization_id TEXT,
    previous_stage TEXT,
    reason TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS legal_acceptance_events (
    id TEXT PRIMARY KEY,
    acceptance_type TEXT,
    bot_id TEXT,
    contact_id TEXT,
    created_at TEXT,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    slug TEXT,
    source TEXT,
    status TEXT,
    subject_key TEXT,
    subject_type TEXT,
    updated_at TEXT,
    user_id TEXT,
    version TEXT
);

CREATE TABLE IF NOT EXISTS legal_audit_events (
    id TEXT PRIMARY KEY,
    actor_id TEXT,
    actor_type TEXT,
    bot_id TEXT,
    created_at TEXT,
    event_type TEXT,
    ip_address TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    request_id TEXT,
    status TEXT,
    subject_key TEXT,
    subject_type TEXT,
    updated_at TEXT,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS legal_consent_records (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    categories_json TEXT NOT NULL DEFAULT '{}',
    consent_key TEXT,
    contact_id TEXT,
    created_at TEXT,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    source TEXT,
    status TEXT,
    subject_key TEXT,
    subject_type TEXT,
    updated_at TEXT,
    user_id TEXT,
    version TEXT
);

CREATE TABLE IF NOT EXISTS mass_reschedule_batches (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    command_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    strategy TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS mass_reschedule_items (
    id TEXT PRIMARY KEY,
    appointment_id TEXT,
    batch_id TEXT,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    new_scheduled_for TEXT,
    old_scheduled_for TEXT,
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS media_assets (
    id TEXT PRIMARY KEY,
    alt_text TEXT,
    asset_type TEXT,
    bot_id TEXT,
    category TEXT,
    created_at TEXT,
    file_name TEXT,
    file_size INTEGER NOT NULL DEFAULT 0,
    file_url TEXT,
    format TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    label TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    mime_type TEXT,
    organization_id TEXT,
    preview_url TEXT,
    product_id TEXT,
    promotion_id TEXT,
    service_id TEXT,
    sort_order TEXT,
    status TEXT,
    updated_at TEXT,
    usage_scope TEXT
);

CREATE TABLE IF NOT EXISTS memory_episodes (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    summary TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS memory_vectors (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    text TEXT,
    updated_at TEXT,
    vector_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS message_operational_reasoning (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    classifier_source TEXT,
    conversation_id TEXT,
    created_at TEXT,
    generator_source TEXT,
    intent_detected TEXT,
    message_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    policy_applied TEXT,
    status TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    takeover_reason TEXT,
    updated_at TEXT,
    urgency_level TEXT,
    urgency_score REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS metrics_daily (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    day TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS oauth_states (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    code_verifier TEXT,
    consumed_at TEXT,
    created_at TEXT,
    expires_at TEXT,
    integration_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    provider TEXT,
    redirect_uri TEXT,
    scope TEXT,
    state_token_hash TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS omnichannel_identities (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    confidence TEXT,
    contact_id TEXT,
    created_at TEXT,
    identity_key TEXT,
    identity_type TEXT,
    identity_value TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS operational_command_impacts (
    id TEXT PRIMARY KEY,
    after_json TEXT NOT NULL DEFAULT '{}',
    before_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    command_id TEXT,
    created_at TEXT,
    entity_id TEXT,
    entity_type TEXT,
    impact_type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    reversible TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS operational_provider_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    conversation_id TEXT,
    correlation_id TEXT,
    created_at TEXT,
    error_json TEXT NOT NULL DEFAULT '{}',
    event_type TEXT,
    integration_id TEXT,
    job_id TEXT,
    message_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    outbox_message_id TEXT,
    payment_id TEXT,
    provider TEXT,
    provider_message_id TEXT,
    provider_request_id TEXT,
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    source TEXT,
    state TEXT,
    status TEXT,
    tool_execution_id TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS operator_copilot_suggestions (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    draft_text TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    operator_user_id TEXT,
    organization_id TEXT,
    status TEXT,
    suggestion_text TEXT,
    tone TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS operator_notifications (
    id TEXT PRIMARY KEY,
    body TEXT,
    bot_id TEXT,
    category TEXT,
    channel TEXT,
    conversation_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    severity TEXT,
    status TEXT,
    title TEXT,
    updated_at TEXT,
    user_id TEXT
);

CREATE TABLE IF NOT EXISTS operator_training_examples (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    context_json TEXT NOT NULL DEFAULT '{}',
    conversation_id TEXT,
    created_at TEXT,
    example_type TEXT,
    input_text TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    operator_user_id TEXT,
    organization_id TEXT,
    output_text TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS optimizer_change_audits (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    created_by TEXT,
    decision_id TEXT,
    event_type TEXT,
    experiment_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    proposal_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS optimizer_control_states (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    current_state_json TEXT NOT NULL DEFAULT '{}',
    last_decision_action TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    target_name TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS optimizer_cycles (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    mode TEXT,
    organization_id TEXT,
    scorecard_window REAL NOT NULL DEFAULT 0,
    status TEXT,
    targets_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS optimizer_experiments (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    candidate_entity_id TEXT,
    candidate_entity_type TEXT,
    champion_entity_id TEXT,
    champion_entity_type TEXT,
    created_at TEXT,
    created_by TEXT,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    experiment_key TEXT,
    guardrails_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    mode TEXT,
    organization_id TEXT,
    proposal_id TEXT,
    rollout_percentage TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS optimizer_proposals (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    challenger_entity_id TEXT,
    challenger_entity_type TEXT,
    champion_entity_id TEXT,
    champion_entity_type TEXT,
    change_set_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    created_by TEXT,
    cycle_id TEXT,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    proposal_kind TEXT,
    rationale_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    summary TEXT,
    target_name TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS organization_branding (
    id TEXT PRIMARY KEY,
    address TEXT,
    bot_id TEXT,
    business_name TEXT,
    created_at TEXT,
    email TEXT,
    footer_note TEXT,
    legal_name TEXT,
    logo_url TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    phone TEXT,
    primary_color TEXT,
    secondary_color TEXT,
    status TEXT,
    updated_at TEXT,
    website TEXT,
    whatsapp TEXT
);

CREATE TABLE IF NOT EXISTS organization_security_policies (
    id TEXT PRIMARY KEY,
    allowed_origins_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    created_at TEXT,
    ip_allowlist_json TEXT NOT NULL DEFAULT '{}',
    max_sessions_per_user TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    require_dual_approval_releases INTEGER NOT NULL DEFAULT 0,
    require_mfa INTEGER NOT NULL DEFAULT 0,
    require_sso INTEGER NOT NULL DEFAULT 0,
    session_idle_timeout_minutes INTEGER NOT NULL DEFAULT 0,
    session_ttl_minutes INTEGER NOT NULL DEFAULT 0,
    status TEXT,
    step_up_window_minutes INTEGER NOT NULL DEFAULT 0,
    strict_idempotency TEXT,
    updated_at TEXT,
    updated_by TEXT,
    webhook_signature_required INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS outcome_attribution_facts (
    id TEXT PRIMARY KEY,
    attribution_model TEXT,
    attribution_weight TEXT,
    attribution_window_hours INTEGER NOT NULL DEFAULT 0,
    bot_id TEXT,
    contribution_value TEXT,
    created_at TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    entity_id TEXT,
    entity_type TEXT,
    exposure_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    metric_name TEXT,
    organization_id TEXT,
    outcome_event_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS outcome_optimization_decisions (
    id TEXT PRIMARY KEY,
    action TEXT,
    applied_at TEXT,
    bot_id TEXT,
    created_at TEXT,
    created_by TEXT,
    decision_source TEXT,
    entity_id TEXT,
    entity_type TEXT,
    evidence_snapshot_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    new_state_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    previous_state_json TEXT NOT NULL DEFAULT '{}',
    reason_code TEXT,
    rollback_of_decision_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS outcome_scorecard_snapshots (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    computed_at TEXT,
    confidence_score REAL NOT NULL DEFAULT 0,
    created_at TEXT,
    entity_id TEXT,
    entity_type TEXT,
    guardrail_state TEXT,
    guardrails_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    outcome_score REAL NOT NULL DEFAULT 0,
    primary_metric TEXT,
    primary_metric_value TEXT,
    rationale_json TEXT NOT NULL DEFAULT '{}',
    recommendation TEXT,
    scorecard_window REAL NOT NULL DEFAULT 0,
    status TEXT,
    traffic_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS privacy_requests (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    country INTEGER NOT NULL DEFAULT 0,
    created_at TEXT,
    email TEXT,
    message TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    phone TEXT,
    request_type TEXT,
    requested_at TEXT,
    requester_name TEXT,
    source TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS proactive_contact_candidates (
    id TEXT PRIMARY KEY,
    appointment_id TEXT,
    bot_id TEXT,
    candidate_key TEXT,
    channel TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    eligible TEXT,
    lead_id TEXT,
    message_text TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    nba_policy_id TEXT,
    objective TEXT,
    organization_id TEXT,
    payment_id TEXT,
    playbook_id TEXT,
    playbook_version_id TEXT,
    policy_json TEXT NOT NULL DEFAULT '{}',
    policy_profile_key TEXT,
    policy_profile_version TEXT,
    priority_band INTEGER NOT NULL DEFAULT 0,
    priority_score REAL NOT NULL DEFAULT 0,
    reasoning_json TEXT NOT NULL DEFAULT '{}',
    recommended_action TEXT,
    signal_event_id TEXT,
    signal_family TEXT,
    signal_key TEXT,
    specialist_agent_key TEXT,
    status TEXT,
    suggested_send_at TEXT,
    suppression_reason TEXT,
    timing_policy_id TEXT,
    title TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS proactive_playbook_runs (
    id TEXT PRIMARY KEY,
    action_payload_json TEXT NOT NULL DEFAULT '{}',
    appointment_id TEXT,
    bot_id TEXT,
    candidate_id TEXT,
    channel TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    lead_id TEXT,
    message_text TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    objective TEXT,
    organization_id TEXT,
    outcome_exposure_id TEXT,
    payment_id TEXT,
    playbook_id TEXT,
    playbook_version_id TEXT,
    recommended_action TEXT,
    scheduled_for TEXT,
    specialist_agent_key TEXT,
    status TEXT,
    tool_execution_run_id TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS proactive_signal_events (
    id TEXT PRIMARY KEY,
    appointment_id TEXT,
    bot_id TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    event_at TEXT,
    facts_json TEXT NOT NULL DEFAULT '{}',
    lead_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payment_id TEXT,
    signal_family TEXT,
    signal_key TEXT,
    status TEXT,
    strength_score REAL NOT NULL DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS product_events (
    id TEXT PRIMARY KEY,
    actor_user_id TEXT,
    bot_id TEXT,
    created_at TEXT,
    entity_id TEXT,
    entity_type TEXT,
    event_name TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT,
    value_json TEXT NOT NULL DEFAULT '{}',
    value_numeric TEXT
);

CREATE TABLE IF NOT EXISTS product_question_logs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    converted TEXT,
    created_at TEXT,
    entity_id TEXT,
    entity_type TEXT,
    intent TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    requested_variant TEXT,
    source_channel TEXT,
    status TEXT,
    unanswered TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS prompt_artifacts (
    id TEXT PRIMARY KEY,
    artifact_key TEXT,
    artifact_type TEXT,
    body TEXT,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    title TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS public_api_credentials (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    last_used_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    scopes_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    token_hash TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS publish_schedules (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    notes TEXT,
    organization_id TEXT,
    scheduled_for TEXT,
    status TEXT,
    updated_at TEXT,
    version_id TEXT
);

CREATE TABLE IF NOT EXISTS rate_limit_policies (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    max_requests TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    scope TEXT,
    status TEXT,
    updated_at TEXT,
    window_seconds INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reactivation_recommendations (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    created_at TEXT,
    crm_lead_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    rationale TEXT,
    segment TEXT,
    status TEXT,
    suggested_channel TEXT,
    suggested_incentive TEXT,
    suggested_message TEXT,
    suggested_send_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS release_requests (
    id TEXT PRIMARY KEY,
    approved_at TEXT,
    approved_by TEXT,
    bot_id TEXT,
    checklist_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    diff_summary_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    notes TEXT,
    organization_id TEXT,
    published_at TEXT,
    requested_by TEXT,
    status TEXT,
    title TEXT,
    updated_at TEXT,
    validation_json TEXT NOT NULL DEFAULT '{}',
    version_id TEXT
);

CREATE TABLE IF NOT EXISTS report_schedules (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    created_by TEXT,
    delivery_channels_json TEXT NOT NULL DEFAULT '{}',
    frequency TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    next_run_at TEXT,
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS request_counters (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    last_seen_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    request_count INTEGER NOT NULL DEFAULT 0,
    scope TEXT,
    scope_key TEXT,
    status TEXT,
    updated_at TEXT,
    window_started_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS revenue_events (
    id TEXT PRIMARY KEY,
    amount REAL NOT NULL DEFAULT 0,
    bot_id TEXT,
    created_at TEXT,
    currency TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS routing_assignments (
    id TEXT PRIMARY KEY,
    assigned_team TEXT,
    assigned_user_id TEXT,
    bot_id TEXT,
    contact_id TEXT,
    conversation_id TEXT,
    created_at TEXT,
    matched_conditions_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    rule_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS routing_rules (
    id TEXT PRIMARY KEY,
    assigned_team TEXT,
    assigned_user_id TEXT,
    bot_id TEXT,
    conditions_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    created_by TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS runtime_callbacks (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    callback_type TEXT,
    created_at TEXT,
    delivered_at TEXT,
    execution_run_id TEXT,
    last_error TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    target TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS scheduled_operational_actions (
    id TEXT PRIMARY KEY,
    action_type TEXT,
    bot_id TEXT,
    command_id TEXT,
    created_at TEXT,
    created_by TEXT,
    execute_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS secret_entries (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    encryption_version TEXT,
    expires_at TEXT,
    key_name TEXT,
    last_access_actor_id TEXT,
    last_access_actor_type TEXT,
    last_accessed_at TEXT,
    last_rotated_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    scope TEXT,
    status TEXT,
    updated_at TEXT,
    value_encrypted TEXT,
    value_masked TEXT
);

CREATE TABLE IF NOT EXISTS service_requests (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    contact_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    request_type TEXT,
    response_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS shadow_runs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    candidate_output_json TEXT NOT NULL DEFAULT '{}',
    conversation_id TEXT,
    created_at TEXT,
    diff_json TEXT NOT NULL DEFAULT '{}',
    experiment_key TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    production_output_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT,
    verdict TEXT
);

CREATE TABLE IF NOT EXISTS simulation_reports (
    id TEXT PRIMARY KEY,
    blocking_failures_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    created_at TEXT,
    failed_scenarios TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    passed_scenarios TEXT,
    report_json TEXT NOT NULL DEFAULT '{}',
    run_id TEXT,
    score REAL NOT NULL DEFAULT 0,
    status TEXT,
    total_scenarios INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT,
    wizard_id TEXT
);

CREATE TABLE IF NOT EXISTS simulation_scenarios (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    run_id TEXT,
    scenario_key TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS sso_identities (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    email TEXT,
    external_subject TEXT,
    last_login_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    provider_id TEXT,
    status TEXT,
    updated_at TEXT,
    user_id TEXT
);

CREATE TABLE IF NOT EXISTS supervisor_console_snapshots (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    created_by TEXT,
    failed_takeovers_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    qa_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    teams_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS technical_logs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    category TEXT,
    conversation_id TEXT,
    created_at TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    execution_id TEXT,
    execution_run_id TEXT,
    level TEXT,
    message TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    trace_id TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS tool_execution_step_logs (
    id TEXT PRIMARY KEY,
    action TEXT,
    adapter_key TEXT,
    bot_id TEXT,
    created_at TEXT,
    execution_run_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    provider TEXT,
    status TEXT,
    step_name TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS vacation_periods (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    command_id TEXT,
    created_at TEXT,
    created_by TEXT,
    end_date TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    reason TEXT,
    scope_json TEXT NOT NULL DEFAULT '{}',
    start_date TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS vertical_marketplace_installs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS vertical_marketplace_packages (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    package_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    updated_at TEXT,
    version TEXT,
    vertical_key TEXT
);

CREATE TABLE IF NOT EXISTS vertical_onboarding_step_runs (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    completed_at TEXT,
    created_at TEXT,
    generated_patch_json TEXT NOT NULL DEFAULT '{}',
    is_required INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    step_key TEXT,
    step_status TEXT,
    updated_at TEXT,
    wizard_id TEXT
);

CREATE TABLE IF NOT EXISTS vertical_onboarding_wizard_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    event_type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    step_key TEXT,
    updated_at TEXT,
    wizard_id TEXT
);

CREATE TABLE IF NOT EXISTS vertical_onboarding_wizards (
    id TEXT PRIMARY KEY,
    answers_json TEXT NOT NULL DEFAULT '{}',
    applied_summary_json TEXT NOT NULL DEFAULT '{}',
    bot_id TEXT,
    bot_name TEXT,
    business_name TEXT,
    checklist_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    created_by TEXT,
    current_step TEXT,
    language TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    primary_objective TEXT,
    progress_percent TEXT,
    recommended_ctas_json TEXT NOT NULL DEFAULT '{}',
    recommended_integrations_json TEXT NOT NULL DEFAULT '{}',
    recommended_playbooks_json TEXT NOT NULL DEFAULT '{}',
    recompute_state_json TEXT NOT NULL DEFAULT '{}',
    setup_json TEXT NOT NULL DEFAULT '{}',
    status TEXT,
    subvertical TEXT,
    timezone TEXT,
    tone TEXT,
    updated_at TEXT,
    validation_snapshot_json TEXT NOT NULL DEFAULT '{}',
    vertical_id TEXT,
    wizard_revision TEXT,
    wizard_version TEXT
);

CREATE TABLE IF NOT EXISTS webhook_event_receipts (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    channel TEXT,
    created_at TEXT,
    external_event_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_hash TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_events (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    event_type TEXT,
    execution_id TEXT,
    flow_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    screen_id TEXT,
    status TEXT,
    step_index TEXT,
    updated_at TEXT,
    variant TEXT,
    version_id TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_executions (
    id TEXT PRIMARY KEY,
    assigned_variant TEXT,
    bot_id TEXT,
    channel_message_id TEXT,
    completed_at TEXT,
    contact_id TEXT,
    context_json TEXT NOT NULL DEFAULT '{}',
    conversation_id TEXT,
    created_at TEXT,
    current_screen_id TEXT,
    fallback_mode TEXT,
    fallback_reason TEXT,
    flow_id TEXT,
    flow_token TEXT,
    last_event_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT,
    status TEXT,
    updated_at TEXT,
    version_id TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_experiments (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    flow_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    note TEXT,
    organization_id TEXT,
    rollout_percentage TEXT,
    status TEXT,
    updated_at TEXT,
    version_a_id TEXT,
    version_b_id TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_publications (
    id TEXT PRIMARY KEY,
    action TEXT,
    bot_id TEXT,
    created_at TEXT,
    finished_at TEXT,
    flow_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    provider TEXT,
    remote_flow_id TEXT,
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT,
    status TEXT,
    updated_at TEXT,
    validation_errors_json TEXT NOT NULL DEFAULT '{}',
    version_id TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_flow_versions (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    cloned_from_version_id TEXT,
    compatibility_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    flow_id TEXT,
    flow_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    published_at TEXT,
    remote_asset_status TEXT,
    rollout_json TEXT NOT NULL DEFAULT '{}',
    state TEXT,
    status TEXT,
    updated_at TEXT,
    validation_errors_json TEXT NOT NULL DEFAULT '{}',
    version_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS whatsapp_flows (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    current_version_id TEXT,
    definition_json TEXT NOT NULL DEFAULT '{}',
    fallback_json TEXT NOT NULL DEFAULT '{}',
    flow_type TEXT,
    language TEXT,
    last_sync_error TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    published_version_id TEXT,
    remote_details_json TEXT NOT NULL DEFAULT '{}',
    remote_flow_id TEXT,
    remote_last_published_at TEXT,
    remote_last_synced_at TEXT,
    remote_status TEXT,
    runtime_config_json TEXT NOT NULL DEFAULT '{}',
    runtime_endpoint TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_template_failovers (
    id TEXT PRIMARY KEY,
    bot_id TEXT,
    created_at TEXT,
    current_template_id TEXT,
    current_version_id TEXT,
    fallback_template_id TEXT,
    fallback_version_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    outbox_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    reason_code TEXT,
    source TEXT,
    status TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_template_sync_runs (
    id TEXT PRIMARY KEY,
    action TEXT,
    bot_id TEXT,
    created_at TEXT,
    finished_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    provider TEXT,
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT,
    status TEXT,
    template_id TEXT,
    updated_at TEXT,
    validation_errors_json TEXT NOT NULL DEFAULT '{}',
    version_id TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_template_versions (
    id TEXT PRIMARY KEY,
    approval_status TEXT,
    assets_json TEXT NOT NULL DEFAULT '{}',
    body_text TEXT,
    bot_id TEXT,
    buttons_json TEXT NOT NULL DEFAULT '{}',
    category TEXT,
    coverage_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    fallback_template_id TEXT,
    footer_text TEXT,
    header_text TEXT,
    header_type TEXT,
    language_code TEXT,
    lint_report_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    organization_id TEXT,
    published_at TEXT,
    rejection_reason TEXT,
    remote_quality_rating TEXT,
    remote_status TEXT,
    remote_template_id TEXT,
    sample_values_json TEXT NOT NULL DEFAULT '{}',
    state TEXT,
    status TEXT,
    synced_at TEXT,
    template_id TEXT,
    updated_at TEXT,
    variables_json TEXT NOT NULL DEFAULT '{}',
    version_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS whatsapp_templates (
    id TEXT PRIMARY KEY,
    approved_version_id TEXT,
    bot_id TEXT,
    category TEXT,
    created_at TEXT,
    default_language TEXT,
    fallback_template_id TEXT,
    last_sync_status TEXT,
    latest_version_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    organization_id TEXT,
    performance_score REAL NOT NULL DEFAULT 0,
    remote_template_id TEXT,
    status TEXT,
    updated_at TEXT
);

