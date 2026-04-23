CREATE TABLE IF NOT EXISTS authorized_operational_numbers (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    phone_e164 TEXT NOT NULL,
    role TEXT NOT NULL,
    allowed_intents_json TEXT NOT NULL DEFAULT '[]',
    scope_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'verified',
    verified_at TEXT,
    last_used_at TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, bot_id, phone_e164),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS operational_command_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    source_channel TEXT NOT NULL,
    source_message_id TEXT,
    source_webhook_receipt_id TEXT,
    actor_user_id TEXT,
    actor_phone_e164 TEXT,
    actor_role TEXT,
    detected_intent TEXT,
    raw_text TEXT,
    parsed_entities_json TEXT NOT NULL DEFAULT '{}',
    resolved_scope_json TEXT NOT NULL DEFAULT '{}',
    risk_level TEXT NOT NULL DEFAULT 'low',
    requires_confirmation INTEGER NOT NULL DEFAULT 0,
    confirmation_code TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    scheduled_for TEXT,
    executed_at TEXT,
    failed_at TEXT,
    cancelled_at TEXT,
    undoable_until TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (actor_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS operational_command_impacts (
    id TEXT PRIMARY KEY,
    command_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    impact_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    before_json TEXT NOT NULL DEFAULT '{}',
    after_json TEXT NOT NULL DEFAULT '{}',
    reversible INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS availability_overrides (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    override_type TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    reason TEXT,
    scope_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    created_by TEXT,
    command_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
);

CREATE TABLE IF NOT EXISTS vacation_periods (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    reason TEXT,
    scope_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    created_by TEXT,
    command_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
);

CREATE TABLE IF NOT EXISTS appointment_notification_batches (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    command_id TEXT,
    kind TEXT NOT NULL,
    scope_json TEXT NOT NULL DEFAULT '{}',
    message_text TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS appointment_notification_targets (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    appointment_id TEXT NOT NULL,
    contact_id TEXT,
    conversation_id TEXT,
    delivery_status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL,
    FOREIGN KEY (batch_id) REFERENCES appointment_notification_batches(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS mass_reschedule_batches (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    command_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    strategy TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
);

CREATE TABLE IF NOT EXISTS mass_reschedule_items (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    appointment_id TEXT NOT NULL,
    old_scheduled_for TEXT,
    new_scheduled_for TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL,
    FOREIGN KEY (batch_id) REFERENCES mass_reschedule_batches(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);

CREATE TABLE IF NOT EXISTS bot_operational_state_history (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    command_id TEXT,
    previous_state TEXT,
    new_state TEXT,
    message TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS scheduled_operational_actions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    command_id TEXT,
    action_type TEXT NOT NULL,
    execute_at TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bot_temp_messages (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    command_id TEXT,
    message_text TEXT NOT NULL,
    starts_at TEXT,
    expires_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS operational_undo_tokens (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    command_id TEXT NOT NULL,
    token TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    FOREIGN KEY (command_id) REFERENCES operational_command_requests(id)
);

CREATE INDEX IF NOT EXISTS idx_operational_commands_bot_created ON operational_command_requests(bot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_operational_commands_phone_status ON operational_command_requests(actor_phone_e164, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_authorized_operational_numbers_bot_phone ON authorized_operational_numbers(bot_id, phone_e164);
CREATE INDEX IF NOT EXISTS idx_availability_overrides_bot_start ON availability_overrides(bot_id, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_scheduled_operational_actions_bot_execute ON scheduled_operational_actions(bot_id, execute_at, status);
