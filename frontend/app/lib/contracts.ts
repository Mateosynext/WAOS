export type JsonMap = Record<string, unknown>;

export type ApiEnvelope<T = unknown> = {
  ok?: boolean;
  data?: T;
  error?: { code?: string; message?: string; details?: unknown; retryable?: boolean };
  meta?: Record<string, unknown>;
  request_id?: string | null;
  correlation_id?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function stringOrNull(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return null;
}

function stringValue(value: unknown, fallback = ""): string {
  return stringOrNull(value) ?? fallback;
}

function numberValue(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function booleanValue(value: unknown, fallback = false): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "enabled", "active", "on"].includes(normalized)) return true;
    if (["0", "false", "no", "disabled", "inactive", "off"].includes(normalized)) return false;
  }
  return fallback;
}

function nullableNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  return numberValue(value, 0);
}

function numberOrNull(value: unknown): number | null {
  return nullableNumber(value);
}

function booleanOrNull(value: unknown): boolean | null {
  if (value === null || value === undefined || value === "") return null;
  return booleanValue(value);
}

function stringList(value: unknown): string[] {
  return asArray(value)
    .map((item) => stringOrNull(item))
    .filter((item): item is string => Boolean(item));
}

function pickTimestamp(record: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const value = stringOrNull(record[key]);
    if (value) return value;
  }
  return null;
}

function pickString(record: Record<string, unknown>, keys: string[], fallback = "") {
  for (const key of keys) {
    const value = stringOrNull(record[key]);
    if (value) return value;
  }
  return fallback;
}

export function unwrapApiEnvelope<T = unknown>(value: T | ApiEnvelope<T>): T | unknown {
  const record = asRecord(value);
  if ("data" in record && ("ok" in record || "meta" in record)) return record.data;
  return value;
}

export type SessionOrganization = {
  id: string;
  name: string;
  vertical?: string;
  subvertical?: string;
  timezone?: string;
  status?: string;
};

export type SessionUser = {
  id: string;
  email: string;
  full_name?: string;
  global_role?: string;
  organizations: SessionOrganization[];
};

export function normalizeOrganization(raw: unknown): SessionOrganization {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "organization_name"], "Organización"),
    vertical: stringOrNull(record.vertical) ?? undefined,
    subvertical: (() => { const settings = asRecord(record.settings_json); return stringOrNull(record.subvertical) ?? stringOrNull(settings.subvertical) ?? stringOrNull(settings.active_subvertical) ?? undefined; })(),
    timezone: stringOrNull(record.timezone) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
  };
}

export function normalizeSessionUser(raw: unknown): SessionUser {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    id: stringValue(record.id),
    email: stringValue(record.email),
    full_name: stringOrNull(record.full_name) ?? undefined,
    global_role: stringOrNull(record.global_role) ?? undefined,
    organizations: asArray(record.organizations).map(normalizeOrganization).filter((item) => Boolean(item.id)),
  };
}

export type Summary = {
  active_conversations?: number;
  new_leads?: number;
  hot_leads?: number;
  appointments_scheduled?: number;
  human_handoffs?: number;
  messages_sent?: number;
  bots_with_error?: number;
  bots_paused?: number;
  avg_response_time_seconds?: number | null;
};

export type BotVersion = {
  id: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  notes?: string;
};

export type BotContract = {
  id: string;
  organization_id: string;
  name: string;
  business_name?: string;
  vertical?: string;
  language?: string;
  timezone?: string;
  status?: string;
  current_state?: string;
  published_version_id?: string | null;
  ai_paused: boolean;
  phone_number?: string | null;
  connection_status?: string | null;
  phone_number_id?: string | null;
  goal?: string;
  objective?: string;
  tone?: string;
  primary_channel?: string;
  bot_mode?: string;
  auto_send_images?: boolean;
  can_mention_stock?: boolean;
  whatsapp_number?: JsonMap | null;
  config_draft: JsonMap;
  versions: BotVersion[];
  validation_score?: number | null;
  last_release_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export function normalizeBot(raw: unknown): BotContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  const numberRecord = asRecord(record.whatsapp_number);
  return {
    id: stringValue(record.id),
    organization_id: stringValue(record.organization_id),
    name: pickString(record, ["name", "bot_name"], "Bot"),
    business_name: stringOrNull(record.business_name) ?? undefined,
    vertical: stringOrNull(record.vertical) ?? undefined,
    language: stringOrNull(record.language) ?? undefined,
    timezone: stringOrNull(record.timezone) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    current_state: stringOrNull(record.current_state) ?? undefined,
    published_version_id: stringOrNull(record.published_version_id),
    ai_paused: booleanValue(record.ai_paused),
    phone_number: stringOrNull(numberRecord.phone_number ?? record.phone_number),
    connection_status: stringOrNull(numberRecord.connection_status ?? record.connection_status),
    phone_number_id: stringOrNull(numberRecord.phone_number_id ?? record.phone_number_id),
    goal: stringOrNull(record.goal ?? record.primary_objective) ?? undefined,
    objective: stringOrNull(record.objective ?? record.primary_objective) ?? undefined,
    tone: stringOrNull(record.tone) ?? undefined,
    primary_channel: stringOrNull(record.primary_channel ?? record.integration_type) ?? undefined,
    bot_mode: stringOrNull(record.bot_mode) ?? undefined,
    auto_send_images: booleanValue(record.auto_send_images),
    can_mention_stock: booleanValue(record.can_mention_stock),
    whatsapp_number: Object.keys(numberRecord).length ? numberRecord : null,
    config_draft: asRecord(record.config_draft),
    versions: asArray(record.versions).map((item) => {
      const version = asRecord(item);
      return {
        id: stringValue(version.id),
        status: stringOrNull(version.status) ?? undefined,
        created_at: pickTimestamp(version, "created_at", "published_at") ?? undefined,
        updated_at: pickTimestamp(version, "updated_at", "published_at") ?? undefined,
        notes: stringOrNull(version.notes) ?? undefined,
      };
    }).filter((item) => Boolean(item.id)),
    validation_score: nullableNumber(record.validation_score),
    last_release_at: pickTimestamp(record, "last_release_at", "published_at"),
    created_at: pickTimestamp(record, "created_at") ?? undefined,
    updated_at: pickTimestamp(record, "updated_at") ?? undefined,
  };
}

export type ActivationSummaryContract = {
  organization_id?: string;
  bot_id?: string | null;
  tenant_mode?: string;
  vertical?: string | null;
  counts: Record<string, number>;
  progress: Record<string, number>;
  readiness_score?: number;
  blockers: Array<Record<string, unknown>>;
  checklist: Array<Record<string, unknown>>;
  next_step: Record<string, unknown>;
  guided_wizard?: Record<string, unknown> | null;
  first_value_at?: string | null;
  created_at?: string | null;
  feature_flags: Record<string, boolean>;
};

export function normalizeActivationSummary(raw: unknown): ActivationSummaryContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    bot_id: stringOrNull(record.bot_id),
    tenant_mode: stringOrNull(record.tenant_mode) ?? undefined,
    vertical: stringOrNull(record.vertical),
    counts: asRecord(record.counts) as Record<string, number>,
    progress: asRecord(record.progress) as Record<string, number>,
    readiness_score: nullableNumber(record.readiness_score) ?? undefined,
    blockers: asArray(record.blockers).map((item) => asRecord(item)),
    checklist: asArray(record.checklist).map((item) => asRecord(item)),
    next_step: asRecord(record.next_step),
    guided_wizard: Object.keys(asRecord(record.guided_wizard)).length ? asRecord(record.guided_wizard) : null,
    first_value_at: pickTimestamp(record, "first_value_at"),
    created_at: pickTimestamp(record, "created_at"),
    feature_flags: asRecord(record.feature_flags) as Record<string, boolean>,
  };
}

export type InboxSavedViewContract = {
  id: string;
  name: string;
  slug?: string;
  is_default?: boolean;
  filters: Record<string, unknown>;
};

export function normalizeInboxSavedView(raw: unknown): InboxSavedViewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    id: stringValue(record.id),
    name: stringValue(record.name, "Vista"),
    slug: stringOrNull(record.slug) ?? undefined,
    is_default: booleanValue(record.is_default),
    filters: asRecord(record.filters),
  };
}

export type DashboardContract = {
  summary: Summary;
  bots: BotContract[];
};

export function normalizeDashboard(raw: unknown): DashboardContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  const summary = asRecord(record.summary);
  return {
    summary: {
      active_conversations: numberValue(summary.active_conversations),
      new_leads: numberValue(summary.new_leads),
      hot_leads: numberValue(summary.hot_leads),
      appointments_scheduled: numberValue(summary.appointments_scheduled),
      human_handoffs: numberValue(summary.human_handoffs),
      messages_sent: numberValue(summary.messages_sent),
      bots_with_error: numberValue(summary.bots_with_error),
      bots_paused: numberValue(summary.bots_paused),
      avg_response_time_seconds: nullableNumber(summary.avg_response_time_seconds),
    },
    bots: asArray(record.bots).map(normalizeBot).filter((item) => Boolean(item.id)),
  };
}

export type IntegrationContract = {
  id: string;
  organization_id: string;
  bot_id?: string | null;
  related_bot_id?: string | null;
  name: string;
  provider?: string;
  integration_type?: string;
  status?: string;
  health_status?: string;
  credential_status?: string;
  credential_expires_at?: string | null;
  expires_at?: string | null;
  last_error?: string | null;
  last_test_at?: string | null;
  last_provider_event_at?: string | null;
  last_provider_status_code?: number | null;
  auto_sync_enabled?: boolean;
  sync_frequency_minutes?: number | null;
  next_sync_at?: string | null;
  last_success_at?: string | null;
  updated_at?: string | null;
  config: Record<string, unknown>;
  result?: Record<string, unknown>;
};

export function normalizeIntegration(raw: unknown): IntegrationContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    id: stringValue(record.id),
    organization_id: stringValue(record.organization_id),
    bot_id: stringOrNull(record.bot_id),
    related_bot_id: stringOrNull(record.related_bot_id),
    name: pickString(record, ["name", "display_name"], "Integración"),
    provider: stringOrNull(record.provider) ?? undefined,
    integration_type: stringOrNull(record.integration_type) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    health_status: stringOrNull(record.health_status ?? record.status) ?? undefined,
    credential_status: stringOrNull(record.credential_status) ?? undefined,
    credential_expires_at: stringOrNull(record.credential_expires_at),
    expires_at: stringOrNull(record.expires_at ?? record.credential_expires_at),
    last_error: stringOrNull(record.last_error),
    last_test_at: stringOrNull(record.last_test_at),
    last_provider_event_at: stringOrNull(record.last_provider_event_at),
    last_provider_status_code: nullableNumber(record.last_provider_status_code),
    auto_sync_enabled: booleanValue(record.auto_sync_enabled ?? asRecord(record.config).auto_sync_enabled),
    sync_frequency_minutes: nullableNumber(record.sync_frequency_minutes ?? asRecord(record.config).sync_frequency_minutes),
    next_sync_at: stringOrNull(record.next_sync_at),
    last_success_at: stringOrNull(record.last_success_at),
    updated_at: pickTimestamp(record, "updated_at", "created_at"),
    config: asRecord(record.config),
    result: Object.keys(asRecord(record.result)).length ? asRecord(record.result) : undefined,
  };
}

export type ConversationItem = {
  id: string;
  organization_id?: string;
  bot_id?: string;
  contact_id?: string;
  status?: string;
  contact_name?: string;
  contact_phone?: string;
  bot_name?: string;
  lead_score?: number;
  owner_id?: string;
  owner_name?: string;
  lead_stage?: string;
  summary?: string;
  relationship_label?: string;
  relationship_key?: string;
  relationship_status?: string;
  relationship_confidence?: number;
  urgency_level?: string;
  urgency_score?: number;
  attention_tier?: string;
  recommended_mode?: string;
  known_contact?: boolean;
  latest_message_preview?: string;
  last_outbound_at?: string;
  last_inbound_at?: string;
  updated_at?: string;
  created_at?: string;
  priority_score?: number;
  priority_band?: string;
  next_best_action?: string;
  attention_class?: string;
  stalled?: boolean;
  requires_human?: boolean;
  work_queue_role?: string;
  work_queue_reason?: string;
  sla_status?: string;
  sla_due_at?: string;
  sla_target_minutes?: number;
  sla_overdue_minutes?: number;
};

export function normalizeConversation(raw: unknown): ConversationItem {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    id: stringValue(record.id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    bot_id: stringOrNull(record.bot_id) ?? undefined,
    contact_id: stringOrNull(record.contact_id) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    contact_name: stringOrNull(record.contact_name ?? record.name) ?? undefined,
    contact_phone: stringOrNull(record.contact_phone ?? record.phone) ?? undefined,
    bot_name: stringOrNull(record.bot_name ?? record.name) ?? undefined,
    lead_score: nullableNumber(record.lead_score) ?? undefined,
    owner_id: stringOrNull(record.owner_id) ?? undefined,
    owner_name: stringOrNull(record.owner_name) ?? undefined,
    lead_stage: stringOrNull(record.lead_stage) ?? undefined,
    summary: stringOrNull(record.summary) ?? undefined,
    relationship_label: stringOrNull(record.relationship_label) ?? undefined,
    relationship_key: stringOrNull(record.relationship_key) ?? undefined,
    relationship_status: stringOrNull(record.relationship_status) ?? undefined,
    relationship_confidence: nullableNumber(record.relationship_confidence) ?? undefined,
    urgency_level: stringOrNull(record.urgency_level) ?? undefined,
    urgency_score: nullableNumber(record.urgency_score) ?? undefined,
    attention_tier: stringOrNull(record.attention_tier) ?? undefined,
    recommended_mode: stringOrNull(record.recommended_mode) ?? undefined,
    known_contact: booleanValue(record.known_contact, false),
    latest_message_preview: stringOrNull(record.latest_message_preview ?? record.last_message ?? record.preview) ?? undefined,
    last_outbound_at: pickTimestamp(record, "last_outbound_at") ?? undefined,
    last_inbound_at: pickTimestamp(record, "last_inbound_at") ?? undefined,
    updated_at: pickTimestamp(record, "updated_at", "last_message_at", "created_at") ?? undefined,
    created_at: pickTimestamp(record, "created_at") ?? undefined,
    priority_score: nullableNumber(record.priority_score) ?? undefined,
    priority_band: stringOrNull(record.priority_band) ?? undefined,
    next_best_action: stringOrNull(record.next_best_action) ?? undefined,
    attention_class: stringOrNull(record.attention_class) ?? undefined,
    stalled: booleanValue(record.stalled),
    requires_human: booleanValue(record.requires_human),
    work_queue_role: stringOrNull(record.work_queue_role) ?? undefined,
    work_queue_reason: stringOrNull(record.work_queue_reason) ?? undefined,
    sla_status: stringOrNull(record.sla_status) ?? undefined,
    sla_due_at: pickTimestamp(record, "sla_due_at") ?? undefined,
    sla_target_minutes: nullableNumber(record.sla_target_minutes) ?? undefined,
    sla_overdue_minutes: nullableNumber(record.sla_overdue_minutes) ?? undefined,
  };
}

export type MessageContract = {
  id: string;
  direction?: string;
  type?: string;
  kind?: string;
  status?: string;
  source?: string;
  body: string;
  content: string;
  created_at?: string | null;
  sent_at?: string | null;
  timestamp?: string | null;
  metadata: Record<string, unknown>;
};

export function normalizeMessage(raw: unknown): MessageContract {
  const record = asRecord(raw);
  const body = pickString(record, ["body", "content", "text"], "");
  const type = stringOrNull(record.type ?? record.kind) ?? undefined;
  const createdAt = pickTimestamp(record, "created_at", "sent_at", "timestamp");
  return {
    id: stringValue(record.id || createdAt || body || Math.random().toString(36).slice(2)),
    direction: stringOrNull(record.direction) ?? undefined,
    type,
    kind: type,
    status: stringOrNull(record.status) ?? undefined,
    source: stringOrNull(record.source) ?? undefined,
    body,
    content: body,
    created_at: createdAt,
    sent_at: stringOrNull(record.sent_at),
    timestamp: stringOrNull(record.timestamp ?? createdAt),
    metadata: asRecord(record.metadata),
  };
}

export type ConversationDetailContract = {
  conversation: ConversationItem;
  contact: JsonMap;
  memory: JsonMap;
  bot: BotContract | JsonMap;
  tags: string[];
  latest_summary: JsonMap | null;
  cross_bot_memory: JsonMap[];
  messages: MessageContract[];
};

export function normalizeConversationDetail(raw: unknown): ConversationDetailContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  const botRecord = asRecord(record.bot);
  return {
    conversation: normalizeConversation(record.conversation),
    contact: asRecord(record.contact),
    memory: asRecord(record.memory),
    bot: botRecord.id ? normalizeBot(botRecord) : botRecord,
    tags: stringList(record.tags),
    latest_summary: Object.keys(asRecord(record.latest_summary)).length ? asRecord(record.latest_summary) : null,
    cross_bot_memory: asArray(record.cross_bot_memory).map((item) => asRecord(item)),
    messages: asArray(record.messages).map(normalizeMessage),
  };
}

export type QueueCount = { kind: string; type: string; status: string; count: number };
export type QueueOverviewContract = { automation_jobs: QueueCount[]; outbox: QueueCount[]; callbacks: QueueCount[]; integration_sync: QueueCount[] };

function normalizeCountRow(raw: unknown, fallbackKind: string): QueueCount {
  const record = asRecord(raw);
  const status = pickString(record, ["status", "kind", "type"], fallbackKind);
  const kind = pickString(record, ["kind", "type"], status || fallbackKind);
  return { kind, type: kind, status, count: numberValue(record.count) };
}

export function normalizeQueueOverview(raw: unknown): QueueOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    automation_jobs: asArray(record.automation_jobs).map((item) => normalizeCountRow(item, "automation_jobs")),
    outbox: asArray(record.outbox).map((item) => normalizeCountRow(item, "outbox")),
    callbacks: asArray(record.callbacks).map((item) => normalizeCountRow(item, "callbacks")),
    integration_sync: asArray(record.integration_sync).map((item) => normalizeCountRow(item, "integration_sync")),
  };
}

export type SchedulerOverviewContract = {
  counts: QueueCount[];
  due_now: number;
  next_job: JsonMap | null;
  stale_locks: number;
  integration_due_now: number;
  next_integration: JsonMap | null;
  integration_retries: number;
};

export function normalizeSchedulerOverview(raw: unknown): SchedulerOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    counts: asArray(record.counts).map((item) => normalizeCountRow(item, "scheduler")),
    due_now: numberValue(record.due_now),
    next_job: Object.keys(asRecord(record.next_job)).length ? asRecord(record.next_job) : null,
    stale_locks: numberValue(record.stale_locks),
    integration_due_now: numberValue(record.integration_due_now),
    next_integration: Object.keys(asRecord(record.next_integration)).length ? asRecord(record.next_integration) : null,
    integration_retries: numberValue(record.integration_retries),
  };
}

export type RuntimeCallbackContract = {
  id: string;
  kind: string;
  type: string;
  status?: string;
  health_status?: string;
  target?: string | null;
  updated_at?: string | null;
  last_run_at?: string | null;
  payload: Record<string, unknown>;
  response: Record<string, unknown>;
};

export function normalizeRuntimeCallback(raw: unknown): RuntimeCallbackContract {
  const record = asRecord(raw);
  const kind = pickString(record, ["kind", "callback_type", "type"], "callback");
  const updatedAt = pickTimestamp(record, "updated_at", "delivered_at", "created_at");
  return {
    id: stringValue(record.id),
    kind,
    type: kind,
    status: stringOrNull(record.status) ?? undefined,
    health_status: stringOrNull(record.health_status ?? record.status) ?? undefined,
    target: stringOrNull(record.target),
    updated_at: updatedAt,
    last_run_at: stringOrNull(record.last_run_at ?? updatedAt),
    payload: asRecord(record.payload),
    response: asRecord(record.response),
  };
}

export type DeadLetterItem = {
  id: string;
  kind: string;
  type: string;
  status: string;
  detail: string;
  error?: string | null;
  payload: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
  scheduled_for?: string | null;
};

export type DeadLettersContract = { jobs: DeadLetterItem[]; outbox: DeadLetterItem[] };

export function normalizeDeadLetter(raw: unknown, channel: string): DeadLetterItem {
  const record = asRecord(raw);
  const detail = pickString(record, ["detail", "kind", "type", "id"], channel);
  return {
    id: stringValue(record.id || detail),
    kind: channel,
    type: pickString(record, ["kind", "type"], channel),
    status: pickString(record, ["status"], "dead_letter"),
    detail,
    error: stringOrNull(record.last_error ?? record.error),
    payload: asRecord(record.payload),
    created_at: pickTimestamp(record, "created_at") ?? null,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    scheduled_for: stringOrNull(record.scheduled_for),
  };
}

export function normalizeDeadLetters(raw: unknown): DeadLettersContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    jobs: asArray(record.jobs).map((item) => normalizeDeadLetter(item, "job")),
    outbox: asArray(record.outbox).map((item) => normalizeDeadLetter(item, "outbox")),
  };
}

export type ObservabilityContract = {
  totals: JsonMap;
  recent_failures: JsonMap[];
  recent_logs: JsonMap[];
};

export function normalizeObservability(raw: unknown): ObservabilityContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    totals: asRecord(record.totals),
    recent_failures: asArray(record.recent_failures).map((item) => asRecord(item)),
    recent_logs: asArray(record.recent_logs).map((item) => asRecord(item)),
  };
}

export type SecurityPolicyContract = {
  organization_id: string | null;
  require_mfa: boolean;
  require_sso: boolean;
  session_ttl_minutes: number;
  webhook_signature_required: boolean;
  strict_idempotency: boolean;
  ip_allowlist: string[];
  allowed_origins: string[];
};

export function normalizeSecurityPolicy(raw: unknown): SecurityPolicyContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    organization_id: stringOrNull(record.organization_id),
    require_mfa: booleanValue(record.require_mfa),
    require_sso: booleanValue(record.require_sso),
    session_ttl_minutes: numberValue(record.session_ttl_minutes, 0),
    webhook_signature_required: booleanValue(record.webhook_signature_required),
    strict_idempotency: booleanValue(record.strict_idempotency),
    ip_allowlist: stringList(record.ip_allowlist),
    allowed_origins: stringList(record.allowed_origins),
  };
}

export type RateLimitPolicyContract = {
  id: string;
  organization_id?: string;
  bot_id?: string | null;
  scope?: string;
  kind?: string;
  window_seconds: number;
  window?: number;
  max_requests: number;
  limit?: number;
  is_active: boolean;
};

export function normalizeRateLimitPolicy(raw: unknown): RateLimitPolicyContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    bot_id: stringOrNull(record.bot_id),
    scope: stringOrNull(record.scope) ?? undefined,
    kind: stringOrNull(record.kind ?? record.scope) ?? undefined,
    window_seconds: numberValue(record.window_seconds ?? record.window),
    window: numberValue(record.window ?? record.window_seconds),
    max_requests: numberValue(record.max_requests ?? record.limit),
    limit: numberValue(record.limit ?? record.max_requests),
    is_active: booleanValue(record.is_active, true),
  };
}

export type SSOProviderContract = {
  id: string;
  organization_id?: string;
  name?: string;
  provider?: string;
  status?: string;
  health_status?: string;
  issuer?: string;
  client_id?: string;
  scopes: string[];
  expires_at?: string | null;
  updated_at?: string | null;
};

export function normalizeSSOProvider(raw: unknown): SSOProviderContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    name: stringOrNull(record.name ?? record.provider) ?? undefined,
    provider: stringOrNull(record.provider) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    health_status: stringOrNull(record.health_status ?? record.status) ?? undefined,
    issuer: stringOrNull(record.issuer) ?? undefined,
    client_id: stringOrNull(record.client_id) ?? undefined,
    scopes: stringList(record.scopes),
    expires_at: stringOrNull(record.expires_at ?? record.credential_expires_at),
    updated_at: pickTimestamp(record, "updated_at", "created_at"),
  };
}

export type AppointmentContract = {
  id: string;
  contact_name?: string;
  service_name?: string;
  starts_at?: string | null;
  start_at?: string | null;
  scheduled_for?: string | null;
  status?: string;
  payment_status?: string | null;
  reconciliation_status?: string | null;
};

export function normalizeAppointment(raw: unknown): AppointmentContract {
  const record = asRecord(raw);
  const startsAt = pickTimestamp(record, "starts_at", "start_at", "scheduled_for");
  return {
    id: stringValue(record.id),
    contact_name: stringOrNull(record.contact_name ?? record.customer_name) ?? undefined,
    service_name: stringOrNull(record.service_name ?? record.service) ?? undefined,
    starts_at: startsAt,
    start_at: startsAt,
    scheduled_for: startsAt,
    status: stringOrNull(record.status) ?? undefined,
    payment_status: stringOrNull(record.payment_status),
    reconciliation_status: stringOrNull(record.reconciliation_status),
  };
}

export type AgendaOverviewContract = {
  summary: JsonMap;
  upcoming: AppointmentContract[];
};

export function normalizeAgendaOverview(raw: unknown): AgendaOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    summary: asRecord(record.summary),
    upcoming: asArray(record.upcoming).map(normalizeAppointment),
  };
}

export type IntegrationEventContract = {
  id: string;
  provider?: string | null;
  event_type?: string | null;
  status?: string | null;
  summary?: string | null;
  detail?: string | null;
  provider_status_code?: number | null;
  created_at?: string | null;
  error: JsonMap;
  response: JsonMap;
};

export function normalizeIntegrationEvent(raw: unknown): IntegrationEventContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    provider: stringOrNull(record.provider),
    event_type: stringOrNull(record.event_type ?? record.kind),
    status: stringOrNull(record.status),
    summary: stringOrNull(record.summary),
    detail: stringOrNull(record.detail ?? record.summary),
    provider_status_code: nullableNumber(record.provider_status_code),
    created_at: pickTimestamp(record, "created_at", "timestamp") ?? null,
    error: asRecord(record.error),
    response: asRecord(record.response),
  };
}

export type IntegrationObservabilityContract = {
  totals: JsonMap;
  latest_error: IntegrationEventContract | null;
  providers: JsonMap[];
  recent: IntegrationEventContract[];
};

export function normalizeIntegrationObservability(raw: unknown): IntegrationObservabilityContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    totals: asRecord(record.totals),
    latest_error: record.latest_error ? normalizeIntegrationEvent(record.latest_error) : null,
    providers: asArray(record.providers).map((item) => asRecord(item)),
    recent: asArray(record.recent).map(normalizeIntegrationEvent),
  };
}

export type SyncRunContract = {
  id: string;
  integration_id?: string | null;
  provider?: string | null;
  status?: string;
  summary: JsonMap;
  detail?: string;
  error: JsonMap;
  created_at?: string | null;
};

export function normalizeSyncRun(raw: unknown): SyncRunContract {
  const record = asRecord(raw);
  const summary = asRecord(record.summary);
  return {
    id: stringValue(record.id),
    integration_id: stringOrNull(record.integration_id),
    provider: stringOrNull(record.provider ?? summary.provider),
    status: stringOrNull(record.status) ?? undefined,
    summary,
    detail: stringOrNull(record.detail ?? summary.reason ?? summary.mode ?? summary.provider) ?? undefined,
    error: asRecord(record.error),
    created_at: pickTimestamp(record, "created_at", "started_at") ?? null,
  };
}

export type SecretContract = {
  id: string;
  organization_id?: string;
  bot_id?: string | null;
  scope?: string;
  key_name?: string;
  name?: string;
  updated_at?: string | null;
  last_rotated_at?: string | null;
  rotation_due?: boolean;
};

export function normalizeSecret(raw: unknown): SecretContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    bot_id: stringOrNull(record.bot_id),
    scope: stringOrNull(record.scope) ?? undefined,
    key_name: stringOrNull(record.key_name) ?? undefined,
    name: stringOrNull(record.name ?? record.key_name) ?? undefined,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    last_rotated_at: pickTimestamp(record, "last_rotated_at", "updated_at", "created_at") ?? null,
    rotation_due: booleanValue(record.rotation_due),
  };
}

export type BusinessHubOverviewContract = {
  summary: JsonMap;
  top_products: JsonMap[];
  attention: JsonMap[];
};

export function normalizeBusinessHubOverview(raw: unknown): BusinessHubOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    summary: asRecord(record.summary),
    top_products: asArray(record.top_products).map((item) => asRecord(item)),
    attention: asArray(record.attention).map((item) => asRecord(item)),
  };
}

export type AnalyticsDailyContract = {
  day: string;
  metrics: Record<string, unknown>;
  window: JsonMap;
};

export function normalizeAnalyticsDaily(raw: unknown): AnalyticsDailyContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  const metrics = asRecord(record.metrics);
  if (!Object.keys(metrics).length) {
    const fallbackMetrics = {
      ...asRecord(record),
      messages: numberValue(record.messages ?? record.inbound_messages, 0) + numberValue(record.outbound_messages, 0),
      conversations: numberValue(record.conversations ?? record.runs, 0),
    };
    return {
      day: stringValue(record.day, "-"),
      metrics: fallbackMetrics,
      window: asRecord(record.window),
    };
  }
  const enrichedMetrics = {
    ...metrics,
    messages: numberValue(metrics.messages ?? metrics.inbound_messages, 0) + numberValue(metrics.outbound_messages, 0),
    conversations: numberValue(metrics.conversations ?? metrics.runs, 0),
  };
  return {
    day: stringValue(record.day || metrics.day, "-"),
    metrics: enrichedMetrics,
    window: asRecord(record.window ?? metrics.window),
  };
}


export type AuditLogContract = {
  id: string;
  kind?: string;
  event?: string;
  message?: string;
  summary?: string;
  payload: JsonMap;
  details: JsonMap;
  created_at?: string | null;
  updated_at?: string | null;
  timestamp?: string | null;
};

export function normalizeAuditLog(raw: unknown): AuditLogContract {
  const record = asRecord(raw);
  const payload = asRecord(record.payload);
  const details = asRecord(record.details);
  const message = stringOrNull(record.message ?? record.summary ?? details.message ?? payload.message) ?? undefined;
  return {
    id: stringValue(record.id || record.trace_id || record.execution_id || message || "log"),
    kind: stringOrNull(record.kind ?? record.event ?? record.level) ?? undefined,
    event: stringOrNull(record.event ?? record.kind) ?? undefined,
    message,
    summary: stringOrNull(record.summary ?? message) ?? undefined,
    payload,
    details,
    created_at: pickTimestamp(record, "created_at") ?? null,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    timestamp: pickTimestamp(record, "timestamp", "created_at", "updated_at") ?? null,
  };
}

export type RunContract = {
  id: string;
  status?: string;
  created_at?: string | null;
  updated_at?: string | null;
  summary?: string;
  detail?: string;
  input: JsonMap;
  output: JsonMap;
  error: JsonMap;
};

export function normalizeRun(raw: unknown): RunContract {
  const record = asRecord(raw);
  const error = asRecord(record.error);
  const summary = stringOrNull(record.summary ?? record.execution_id ?? record.trace_id ?? record.id) ?? undefined;
  return {
    id: stringValue(record.id),
    status: stringOrNull(record.status) ?? undefined,
    created_at: pickTimestamp(record, "created_at") ?? null,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    summary,
    detail: stringOrNull(record.detail ?? error.message ?? record.source_type ?? record.status) ?? summary,
    input: asRecord(record.input),
    output: asRecord(record.output),
    error,
  };
}

export type BuildContract = {
  id: string;
  version_id?: string | null;
  status?: string;
  created_at?: string | null;
  updated_at?: string | null;
  summary?: string;
  detail?: string;
  validation: JsonMap;
  diff_summary: JsonMap;
  artifact: JsonMap;
};

export function normalizeBuild(raw: unknown): BuildContract {
  const record = asRecord(raw);
  const validation = asRecord(record.validation);
  const diffSummary = asRecord(record.diff_summary);
  const artifact = asRecord(record.artifact);
  const summary = stringOrNull(record.summary ?? diffSummary.summary ?? diffSummary.label ?? validation.summary ?? record.id) ?? undefined;
  return {
    id: stringValue(record.id),
    version_id: stringOrNull(record.version_id),
    status: stringOrNull(record.status) ?? undefined,
    created_at: pickTimestamp(record, "created_at") ?? null,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    summary,
    detail: stringOrNull(record.detail ?? record.notes ?? diffSummary.detail ?? summary) ?? summary,
    validation,
    diff_summary: diffSummary,
    artifact,
  };
}

export type ReleaseRequestContract = {
  id: string;
  bot_id?: string | null;
  version_id?: string | null;
  status?: string;
  title?: string;
  summary?: string;
  notes?: string;
  created_at?: string | null;
  updated_at?: string | null;
  validation: JsonMap;
  diff_summary: JsonMap;
  checklist: JsonMap;
};

export function normalizeReleaseRequest(raw: unknown): ReleaseRequestContract {
  const record = asRecord(raw);
  const diffSummary = asRecord(record.diff_summary);
  const validation = asRecord(record.validation);
  const checklist = asRecord(record.checklist);
  const title = stringOrNull(record.title);
  const notes = stringOrNull(record.notes) ?? undefined;
  return {
    id: stringValue(record.id),
    bot_id: stringOrNull(record.bot_id),
    version_id: stringOrNull(record.version_id),
    status: stringOrNull(record.status) ?? undefined,
    title: title ?? undefined,
    summary: stringOrNull(record.summary ?? title ?? notes ?? diffSummary.summary ?? validation.summary) ?? undefined,
    notes,
    created_at: pickTimestamp(record, "created_at") ?? null,
    updated_at: pickTimestamp(record, "updated_at", "created_at") ?? null,
    validation,
    diff_summary: diffSummary,
    checklist,
  };
}

export type TraceabilityContract = {
  bot: JsonMap;
  versions: JsonMap[];
  builds: BuildContract[];
  releases: ReleaseRequestContract[];
  runs: RunContract[];
};

export function normalizeTraceability(raw: unknown): TraceabilityContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    bot: asRecord(record.bot),
    versions: asArray(record.versions).map((item) => asRecord(item)),
    builds: asArray(record.builds).map(normalizeBuild),
    releases: asArray(record.releases).map(normalizeReleaseRequest),
    runs: asArray(record.runs).map(normalizeRun),
  };
}

export type PaymentContract = {
  id: string;
  reference?: string;
  amount: number;
  currency?: string;
  status?: string;
  provider?: string | null;
  provider_status?: string | null;
  checkout_status?: string | null;
  checkout_url?: string | null;
  appointment_id?: string | null;
  reconciliation_status?: string | null;
  created_at?: string | null;
};

export function normalizePayment(raw: unknown): PaymentContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.reference),
    reference: stringOrNull(record.reference) ?? undefined,
    amount: numberValue(record.amount),
    currency: stringOrNull(record.currency) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    provider: stringOrNull(record.provider),
    provider_status: stringOrNull(record.provider_status),
    checkout_status: stringOrNull(record.checkout_status ?? record.payment_link_status),
    checkout_url: stringOrNull(record.checkout_url ?? record.payment_link_url),
    appointment_id: stringOrNull(record.appointment_id),
    reconciliation_status: stringOrNull(record.reconciliation_status),
    created_at: pickTimestamp(record, "created_at", "paid_at") ?? null,
  };
}

export type CRMLeadContract = {
  id: string;
  contact_name?: string;
  status?: string;
  stage?: string;
  score?: number | null;
};

export function normalizeCRMLead(raw: unknown): CRMLeadContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    contact_name: stringOrNull(record.contact_name ?? record.name) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    stage: stringOrNull(record.stage ?? record.lead_stage) ?? undefined,
    score: nullableNumber(record.score ?? record.lead_score),
  };
}

export type RecommendationContract = {
  id: string;
  contact_name?: string;
  reason?: string;
  next_step?: string;
};

export function normalizeRecommendation(raw: unknown): RecommendationContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.contact_name || record.reason),
    contact_name: stringOrNull(record.contact_name ?? record.name) ?? undefined,
    reason: stringOrNull(record.reason) ?? undefined,
    next_step: stringOrNull(record.next_step) ?? undefined,
  };
}

export type FeedbackItemContract = {
  id: string;
  kind?: string;
  comment?: string;
  message?: string;
  detail?: string;
  created_at?: string | null;
};

export function normalizeFeedbackItem(raw: unknown): FeedbackItemContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.comment || record.message),
    kind: stringOrNull(record.kind) ?? undefined,
    comment: stringOrNull(record.comment) ?? undefined,
    message: stringOrNull(record.message) ?? undefined,
    detail: stringOrNull(record.detail ?? record.comment ?? record.message) ?? undefined,
    created_at: pickTimestamp(record, "created_at") ?? null,
  };
}

export type PortalRequestContract = {
  id: string;
  kind?: string;
  detail?: string;
  message?: string;
  status?: string;
  created_at?: string | null;
};

export function normalizePortalRequest(raw: unknown): PortalRequestContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.kind || record.message),
    kind: stringOrNull(record.kind) ?? undefined,
    detail: stringOrNull(record.detail ?? record.message) ?? undefined,
    message: stringOrNull(record.message) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    created_at: pickTimestamp(record, "created_at") ?? null,
  };
}

export type CatalogProductContract = {
  id: string;
  name: string;
  price?: number | null;
  promotional_price?: number | null;
  currency?: string;
  short_description?: string;
  delivery_eta?: string;
  inventory: JsonMap[];
};

export function normalizeCatalogProduct(raw: unknown): CatalogProductContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Producto"),
    price: nullableNumber(record.price),
    promotional_price: nullableNumber(record.promotional_price),
    currency: stringOrNull(record.currency) ?? undefined,
    short_description: stringOrNull(record.short_description) ?? undefined,
    delivery_eta: stringOrNull(record.delivery_eta) ?? undefined,
    inventory: asArray(record.inventory).map((item) => asRecord(item)),
  };
}

export type CatalogServiceContract = {
  id: string;
  name: string;
  price?: number | null;
  currency?: string;
  duration_minutes?: number | null;
  branch?: string;
};

export function normalizeCatalogService(raw: unknown): CatalogServiceContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Servicio"),
    price: nullableNumber(record.price),
    currency: stringOrNull(record.currency) ?? undefined,
    duration_minutes: nullableNumber(record.duration_minutes),
    branch: stringOrNull(record.branch) ?? undefined,
  };
}

export type MediaAssetContract = {
  id: string;
  name: string;
  file_name?: string;
  label?: string;
  asset_type?: string;
  type?: string;
  status?: string;
  file_url?: string;
  url?: string;
  created_at?: string | null;
};

export function normalizeMediaAsset(raw: unknown): MediaAssetContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title", "filename", "file_name"], "Asset"),
    file_name: stringOrNull(record.file_name ?? record.filename) ?? undefined,
    label: stringOrNull(record.label) ?? undefined,
    asset_type: stringOrNull(record.asset_type ?? record.type ?? record.kind) ?? undefined,
    type: stringOrNull(record.type ?? record.kind ?? record.asset_type) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    file_url: stringOrNull(record.file_url ?? record.url ?? record.asset_url) ?? undefined,
    url: stringOrNull(record.url ?? record.asset_url ?? record.file_url) ?? undefined,
    created_at: pickTimestamp(record, "created_at", "updated_at") ?? null,
  };
}

export type PromotionContract = {
  id: string;
  name: string;
  status?: string;
  cta_label?: string;
  message_short?: string;
  message_long?: string;
  starts_at?: string | null;
  ends_at?: string | null;
};

export function normalizePromotion(raw: unknown): PromotionContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Promoción"),
    status: stringOrNull(record.status) ?? undefined,
    cta_label: stringOrNull(record.cta_label) ?? undefined,
    message_short: stringOrNull(record.message_short ?? record.summary) ?? undefined,
    message_long: stringOrNull(record.message_long ?? record.detail) ?? undefined,
    starts_at: pickTimestamp(record, "starts_at") ?? null,
    ends_at: pickTimestamp(record, "ends_at") ?? null,
  };
}

export type BotTemplateContract = {
  id: string;
  name: string;
  type?: string;
  detail?: string;
  description?: string;
  vertical?: string;
};

export function normalizeBotTemplate(raw: unknown): BotTemplateContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Template"),
    type: stringOrNull(record.type ?? record.kind) ?? undefined,
    detail: stringOrNull(record.detail ?? record.summary ?? record.description) ?? undefined,
    description: stringOrNull(record.description ?? record.detail ?? record.summary) ?? undefined,
    vertical: stringOrNull(record.vertical) ?? undefined,
  };
}

export type VerticalBuyerContract = {
  primary?: string;
  secondary: string[];
};

export type VerticalOnePagerContract = {
  headline?: string;
  thesis?: string;
  problem?: string;
  promise?: string;
  monetizes: string[];
  packaging: string[];
  strategic_care?: string;
};

export type VerticalNativeObjectsContract = {
  core: string[];
  commercial: string[];
  operations: string[];
};

export type VerticalPipelineStageContract = {
  name: string;
  states: string[];
};

export type VerticalPipelineContract = {
  primary?: VerticalPipelineStageContract;
  secondary: VerticalPipelineStageContract[];
};

export type VerticalBotPlaybookContract = {
  must_do: string[];
  must_ask: string[];
  objections: string[];
  escalate_when: string[];
  forbidden: string[];
  success_signals: string[];
};

export type VerticalAutomationSequenceContract = {
  key: string;
  name: string;
  trigger?: string;
  goal?: string;
  steps: string[];
};

export type VerticalDashboardSectionContract = {
  name: string;
  metrics: string[];
};

export type VerticalDashboardContract = {
  north_star?: string;
  sections: VerticalDashboardSectionContract[];
};

export type VerticalHardeningModelContract = {
  goal?: string;
  wave?: string;
  entity_queen?: string;
  reusable_modules: string[];
  minimum_viable_hardening: string[];
  hard_checklist: string[];
};

export type VerticalSpecialistLayersContract = {
  persistent_entities: string[];
  business_pipeline: JsonMap;
  pricing_and_quotes: string[];
  agenda_and_resources: string[];
  post_sale_and_recurrence: string[];
  documents_compliance: string[];
  kpis_that_matter: string[];
  money_automations: string[];
};

export type VerticalDomainContractContract = {
  vertical_entity_types: string[];
  vertical_pipeline_stages: JsonMap;
  vertical_quote_types: string[];
  vertical_resource_types: string[];
  vertical_followup_policies: string[];
  vertical_kpi_definitions: string[];
  vertical_playbooks: string[];
  vertical_document_types: string[];
};

export type VerticalNamedFocusContract = {
  name: string;
  focus?: string;
  status?: string;
};

export type VerticalRuntimeContract = {
  pipeline_machine: JsonMap;
  pricing_engine: JsonMap;
  resource_capacity: JsonMap;
  recurrence_engine: JsonMap;
  kpi_engine: JsonMap;
  automation_engine: JsonMap;
  document_flow: JsonMap;
  matching_engine: JsonMap;
};

export type VerticalTransactionalMotorV12Contract = {
  version?: string;
  aggregate_root?: string;
  main_business_entity?: string;
  transaction_unit?: string;
  system_of_record: JsonMap;
  transaction_primitives: JsonMap;
  aggregates: JsonMap;
  orchestration: JsonMap;
  finance: JsonMap;
  operations: JsonMap;
  audit_compliance: JsonMap;
  transaction_views: JsonMap;
  command_catalog: JsonMap[];
  event_catalog: JsonMap[];
};



export type VerticalSubverticalProfileContract = {
  id: string;
  name: string;
  strength_score?: number;
  promise?: string;
  growth_motion?: string;
  buyer?: string;
  monetizes: string[];
  service_bundle: string[];
  qualification_questions: string[];
  objections: string[];
  automation_priorities: string[];
  kpi_pack: string[];
  recommended_commands: string[];
  launch_assets: string[];
  templates: JsonMap[];
};

export type VerticalRuntimeConnectionContract = {
  active_vertical?: string;
  active_subvertical?: string;
  pack_status: JsonMap;
  surface_focus: JsonMap;
};

export type VerticalProfileContract = {
  id: string;
  name: string;
  short_name?: string;
  description?: string;
  problem?: string;
  portfolio_tier?: string;
  master_thesis?: string;
  subverticals: string[];
  objects: string[];
  flows: string[];
  kpis: string[];
  recommended_integrations: string[];
  buyer: VerticalBuyerContract;
  one_pager: VerticalOnePagerContract;
  demo_flow: string[];
  native_objects: VerticalNativeObjectsContract;
  pipeline: VerticalPipelineContract;
  bot_playbook: VerticalBotPlaybookContract;
  automation_sequences: VerticalAutomationSequenceContract[];
  dashboard: VerticalDashboardContract;
  hardening_model: VerticalHardeningModelContract;
  specialist_layers: VerticalSpecialistLayersContract;
  domain_contract: VerticalDomainContractContract;
  vertical_runtime: VerticalRuntimeContract;
  transactional_motor_v12: VerticalTransactionalMotorV12Contract;
  subvertical_playbooks: VerticalNamedFocusContract[];
  business_e2e_tests: VerticalNamedFocusContract[];
  is_strongest_vertical?: boolean;
  strongest_rank?: number;
  ten_x_score?: number;
  ten_x_narrative?: string;
  ten_x_growth_loops: string[];
  recommended_subverticals: string[];
  ten_x_operational_pack: JsonMap;
  subvertical_profiles: VerticalSubverticalProfileContract[];
  selected_subvertical?: VerticalSubverticalProfileContract;
  runtime_connection?: VerticalRuntimeConnectionContract;
};

function normalizeVerticalBuyer(raw: unknown): VerticalBuyerContract {
  const record = asRecord(raw);
  return {
    primary: stringOrNull(record.primary) ?? undefined,
    secondary: stringList(record.secondary),
  };
}

function normalizeVerticalOnePager(raw: unknown): VerticalOnePagerContract {
  const record = asRecord(raw);
  return {
    headline: stringOrNull(record.headline) ?? undefined,
    thesis: stringOrNull(record.thesis) ?? undefined,
    problem: stringOrNull(record.problem) ?? undefined,
    promise: stringOrNull(record.promise) ?? undefined,
    monetizes: stringList(record.monetizes),
    packaging: stringList(record.packaging),
    strategic_care: stringOrNull(record.strategic_care) ?? undefined,
  };
}

function normalizeVerticalNativeObjects(raw: unknown): VerticalNativeObjectsContract {
  const record = asRecord(raw);
  return {
    core: stringList(record.core),
    commercial: stringList(record.commercial),
    operations: stringList(record.operations),
  };
}

function normalizeVerticalPipelineStage(raw: unknown): VerticalPipelineStageContract {
  const record = asRecord(raw);
  return {
    name: pickString(record, ["name", "title"], "Pipeline"),
    states: stringList(record.states),
  };
}

function normalizeVerticalPipeline(raw: unknown): VerticalPipelineContract {
  const record = asRecord(raw);
  const primaryRecord = asRecord(record.primary);
  return {
    primary: Object.keys(primaryRecord).length ? normalizeVerticalPipelineStage(primaryRecord) : undefined,
    secondary: asArray(record.secondary).map(normalizeVerticalPipelineStage),
  };
}

function normalizeVerticalBotPlaybook(raw: unknown): VerticalBotPlaybookContract {
  const record = asRecord(raw);
  return {
    must_do: stringList(record.must_do),
    must_ask: stringList(record.must_ask),
    objections: stringList(record.objections),
    escalate_when: stringList(record.escalate_when),
    forbidden: stringList(record.forbidden),
    success_signals: stringList(record.success_signals),
  };
}

function normalizeVerticalAutomationSequence(raw: unknown): VerticalAutomationSequenceContract {
  const record = asRecord(raw);
  return {
    key: stringValue(record.key),
    name: pickString(record, ["name", "title"], "Secuencia"),
    trigger: stringOrNull(record.trigger) ?? undefined,
    goal: stringOrNull(record.goal) ?? undefined,
    steps: stringList(record.steps),
  };
}

function normalizeVerticalDashboard(raw: unknown): VerticalDashboardContract {
  const record = asRecord(raw);
  return {
    north_star: stringOrNull(record.north_star) ?? undefined,
    sections: asArray(record.sections).map((item) => {
      const section = asRecord(item);
      return {
        name: pickString(section, ["name", "title"], "Métricas"),
        metrics: stringList(section.metrics),
      };
    }),
  };
}

function normalizeVerticalHardeningModel(raw: unknown): VerticalHardeningModelContract {
  const record = asRecord(raw);
  return {
    goal: stringOrNull(record.goal) ?? undefined,
    wave: stringOrNull(record.wave) ?? undefined,
    entity_queen: stringOrNull(record.entity_queen) ?? undefined,
    reusable_modules: stringList(record.reusable_modules),
    minimum_viable_hardening: stringList(record.minimum_viable_hardening),
    hard_checklist: stringList(record.hard_checklist),
  };
}

function normalizeVerticalSpecialistLayers(raw: unknown): VerticalSpecialistLayersContract {
  const record = asRecord(raw);
  return {
    persistent_entities: stringList(record.persistent_entities),
    business_pipeline: asRecord(record.business_pipeline),
    pricing_and_quotes: stringList(record.pricing_and_quotes),
    agenda_and_resources: stringList(record.agenda_and_resources),
    post_sale_and_recurrence: stringList(record.post_sale_and_recurrence),
    documents_compliance: stringList(record.documents_compliance),
    kpis_that_matter: stringList(record.kpis_that_matter),
    money_automations: stringList(record.money_automations),
  };
}

function normalizeVerticalDomainContract(raw: unknown): VerticalDomainContractContract {
  const record = asRecord(raw);
  return {
    vertical_entity_types: stringList(record.vertical_entity_types),
    vertical_pipeline_stages: asRecord(record.vertical_pipeline_stages),
    vertical_quote_types: stringList(record.vertical_quote_types),
    vertical_resource_types: stringList(record.vertical_resource_types),
    vertical_followup_policies: stringList(record.vertical_followup_policies),
    vertical_kpi_definitions: stringList(record.vertical_kpi_definitions),
    vertical_playbooks: stringList(record.vertical_playbooks),
    vertical_document_types: stringList(record.vertical_document_types),
  };
}

function normalizeVerticalRuntime(raw: unknown): VerticalRuntimeContract {
  const record = asRecord(raw);
  return {
    pipeline_machine: asRecord(record.pipeline_machine),
    pricing_engine: asRecord(record.pricing_engine),
    resource_capacity: asRecord(record.resource_capacity),
    recurrence_engine: asRecord(record.recurrence_engine),
    kpi_engine: asRecord(record.kpi_engine),
    automation_engine: asRecord(record.automation_engine),
    document_flow: asRecord(record.document_flow),
    matching_engine: asRecord(record.matching_engine),
  };
}

function normalizeVerticalTransactionalMotorV12(raw: unknown): VerticalTransactionalMotorV12Contract {
  const record = asRecord(raw);
  return {
    version: stringOrNull(record.version) ?? undefined,
    aggregate_root: stringOrNull(record.aggregate_root) ?? undefined,
    main_business_entity: stringOrNull(record.main_business_entity) ?? undefined,
    transaction_unit: stringOrNull(record.transaction_unit) ?? undefined,
    system_of_record: asRecord(record.system_of_record),
    transaction_primitives: asRecord(record.transaction_primitives),
    aggregates: asRecord(record.aggregates),
    orchestration: asRecord(record.orchestration),
    finance: asRecord(record.finance),
    operations: asRecord(record.operations),
    audit_compliance: asRecord(record.audit_compliance),
    transaction_views: asRecord(record.transaction_views),
    command_catalog: asArray(record.command_catalog).map((item) => asRecord(item)),
    event_catalog: asArray(record.event_catalog).map((item) => asRecord(item)),
  };
}



function normalizeVerticalSubverticalProfile(raw: unknown): VerticalSubverticalProfileContract {
  const record = asRecord(raw);
  return {
    id: pickString(record, ["id", "slug", "name"], "subvertical"),
    name: pickString(record, ["name", "title"], "Subvertical"),
    strength_score: numberOrNull(record.strength_score) ?? undefined,
    promise: stringOrNull(record.promise) ?? undefined,
    growth_motion: stringOrNull(record.growth_motion) ?? undefined,
    buyer: stringOrNull(record.buyer) ?? undefined,
    monetizes: stringList(record.monetizes),
    service_bundle: stringList(record.service_bundle),
    qualification_questions: stringList(record.qualification_questions),
    objections: stringList(record.objections),
    automation_priorities: stringList(record.automation_priorities),
    kpi_pack: stringList(record.kpi_pack),
    recommended_commands: stringList(record.recommended_commands),
    launch_assets: stringList(record.launch_assets),
    templates: asArray(record.templates).map((item) => asRecord(item)),
  };
}

function normalizeVerticalNamedFocus(raw: unknown): VerticalNamedFocusContract {
  const record = asRecord(raw);
  return {
    name: pickString(record, ["name", "title"], "Elemento"),
    focus: stringOrNull(record.focus) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
  };
}

export function normalizeVerticalProfile(raw: unknown): VerticalProfileContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Vertical"),
    short_name: stringOrNull(record.short_name) ?? undefined,
    description: stringOrNull(record.description) ?? undefined,
    problem: stringOrNull(record.problem) ?? undefined,
    portfolio_tier: stringOrNull(record.portfolio_tier) ?? undefined,
    master_thesis: stringOrNull(record.master_thesis) ?? undefined,
    subverticals: stringList(record.subverticals),
    objects: stringList(record.objects),
    flows: stringList(record.flows),
    kpis: stringList(record.kpis),
    recommended_integrations: stringList(record.recommended_integrations),
    buyer: normalizeVerticalBuyer(record.buyer),
    one_pager: normalizeVerticalOnePager(record.one_pager),
    demo_flow: stringList(record.demo_flow),
    native_objects: normalizeVerticalNativeObjects(record.native_objects),
    pipeline: normalizeVerticalPipeline(record.pipeline),
    bot_playbook: normalizeVerticalBotPlaybook(record.bot_playbook),
    automation_sequences: asArray(record.automation_sequences).map(normalizeVerticalAutomationSequence),
    dashboard: normalizeVerticalDashboard(record.dashboard),
    hardening_model: normalizeVerticalHardeningModel(record.hardening_model),
    specialist_layers: normalizeVerticalSpecialistLayers(record.specialist_layers),
    domain_contract: normalizeVerticalDomainContract(record.domain_contract),
    vertical_runtime: normalizeVerticalRuntime(record.vertical_runtime),
    transactional_motor_v12: normalizeVerticalTransactionalMotorV12(record.transactional_motor_v12),
    subvertical_playbooks: asArray(record.subvertical_playbooks).map(normalizeVerticalNamedFocus),
    business_e2e_tests: asArray(record.business_e2e_tests).map(normalizeVerticalNamedFocus),
    is_strongest_vertical: booleanOrNull(record.is_strongest_vertical) ?? undefined,
    strongest_rank: numberOrNull(record.strongest_rank) ?? undefined,
    ten_x_score: numberOrNull(record.ten_x_score) ?? undefined,
    ten_x_narrative: stringOrNull(record.ten_x_narrative) ?? undefined,
    ten_x_growth_loops: stringList(record.ten_x_growth_loops),
    recommended_subverticals: stringList(record.recommended_subverticals),
    ten_x_operational_pack: asRecord(record.ten_x_operational_pack),
    subvertical_profiles: asArray(record.subvertical_profiles).map(normalizeVerticalSubverticalProfile),
    selected_subvertical: Object.keys(asRecord(record.selected_subvertical)).length ? normalizeVerticalSubverticalProfile(record.selected_subvertical) : undefined,
    runtime_connection: Object.keys(asRecord(record.runtime_connection)).length ? {
      active_vertical: stringOrNull(asRecord(record.runtime_connection).active_vertical) ?? undefined,
      active_subvertical: stringOrNull(asRecord(record.runtime_connection).active_subvertical) ?? undefined,
      pack_status: asRecord(asRecord(record.runtime_connection).pack_status),
      surface_focus: asRecord(asRecord(record.runtime_connection).surface_focus),
    } : undefined,
  };
}

export type ReleaseReadinessContract = {
  bot_id: string;
  organization_id?: string;
  vertical?: JsonMap;
  summary: JsonMap;
  checklist: JsonMap;
  checklist_items: JsonMap[];
  blockers: JsonMap[];
  warnings: JsonMap[];
  integrations: JsonMap[];
  validation: JsonMap;
  diff_summary: JsonMap;
};

export function normalizeReleaseReadiness(raw: unknown): ReleaseReadinessContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    bot_id: stringValue(record.bot_id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    vertical: asRecord(record.vertical),
    summary: asRecord(record.summary),
    checklist: asRecord(record.checklist),
    checklist_items: asArray(record.checklist_items).map((item) => asRecord(item)),
    blockers: asArray(record.blockers).map((item) => asRecord(item)),
    warnings: asArray(record.warnings).map((item) => asRecord(item)),
    integrations: asArray(record.integrations).map((item) => asRecord(item)),
    validation: asRecord(record.validation),
    diff_summary: asRecord(record.diff_summary),
  };
}

export type CommerceInsightsContract = {
  summary: JsonMap;
  top_products: JsonMap[];
  top_assets: JsonMap[];
  top_promotions: JsonMap[];
  recommendations: JsonMap[];
  alerts: JsonMap[];
};

export function normalizeCommerceInsights(raw: unknown): CommerceInsightsContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    summary: asRecord(record.summary),
    top_products: asArray(record.top_products).map((item) => asRecord(item)),
    top_assets: asArray(record.top_assets).map((item) => asRecord(item)),
    top_promotions: asArray(record.top_promotions).map((item) => asRecord(item)),
    recommendations: asArray(record.recommendations).map((item) => asRecord(item)),
    alerts: asArray(record.alerts).map((item) => asRecord(item)),
  };
}

export function normalizeCollection<T>(raw: unknown, normalizeItem: (value: unknown) => T): T[] {
  return asArray(unwrapApiEnvelope(raw)).map(normalizeItem);
}

export function normalizeRecord<T>(raw: unknown, normalizeItem: (value: unknown) => T): T {
  return normalizeItem(unwrapApiEnvelope(raw));
}


export type TalentVacancyContract = {
  id: string;
  title: string;
  status?: string;
  summary?: string;
  description?: string;
  requirements: string[];
  benefits: string[];
  location_label?: string;
  address?: string;
  modality?: string;
  work_days?: string;
  work_hours?: string;
  salary_visible: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string;
  interview_schedule?: string;
  interview_location?: string;
  interview_notes?: string;
  documents_required: string[];
};

export type TalentCandidateContract = {
  id: string;
  contact_id: string;
  conversation_id?: string | null;
  vacancy_id?: string | null;
  vacancy_title?: string | null;
  status?: string;
  interview_confirmed_at?: string | null;
  updated_at?: string | null;
};

export type TalentOverviewContract = {
  bot_id: string;
  bot_name?: string;
  config: JsonMap;
  vacancies: TalentVacancyContract[];
  candidates: TalentCandidateContract[];
  summary: Record<string, unknown>;
};

export function normalizeTalentVacancy(raw: unknown): TalentVacancyContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    title: stringValue(record.title, 'Vacante'),
    status: stringOrNull(record.status) ?? undefined,
    summary: stringOrNull(record.summary) ?? undefined,
    description: stringOrNull(record.description) ?? undefined,
    requirements: stringList(record.requirements),
    benefits: stringList(record.benefits),
    location_label: stringOrNull(record.location_label) ?? undefined,
    address: stringOrNull(record.address) ?? undefined,
    modality: stringOrNull(record.modality) ?? undefined,
    work_days: stringOrNull(record.work_days) ?? undefined,
    work_hours: stringOrNull(record.work_hours) ?? undefined,
    salary_visible: booleanValue(record.salary_visible),
    salary_min: nullableNumber(record.salary_min),
    salary_max: nullableNumber(record.salary_max),
    currency: stringOrNull(record.currency) ?? undefined,
    interview_schedule: stringOrNull(record.interview_schedule) ?? undefined,
    interview_location: stringOrNull(record.interview_location) ?? undefined,
    interview_notes: stringOrNull(record.interview_notes) ?? undefined,
    documents_required: stringList(record.documents_required),
  };
}

export function normalizeTalentCandidate(raw: unknown): TalentCandidateContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    contact_id: stringValue(record.contact_id),
    conversation_id: stringOrNull(record.conversation_id),
    vacancy_id: stringOrNull(record.vacancy_id),
    vacancy_title: stringOrNull(record.vacancy_title),
    status: stringOrNull(record.status) ?? undefined,
    interview_confirmed_at: stringOrNull(record.interview_confirmed_at),
    updated_at: stringOrNull(record.updated_at),
  };
}

export function normalizeTalentOverview(raw: unknown): TalentOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    bot_id: stringValue(record.bot_id),
    bot_name: stringOrNull(record.bot_name) ?? undefined,
    config: asRecord(record.config),
    vacancies: asArray(record.vacancies).map(normalizeTalentVacancy).filter((item) => Boolean(item.id)),
    candidates: asArray(record.candidates).map(normalizeTalentCandidate).filter((item) => Boolean(item.id)),
    summary: asRecord(record.summary),
  };
}


export type InboxQueueContract = {
  role_key: string;
  count: number;
  requires_human: number;
  stalled: number;
  sla_breached: number;
  top_priority: number;
};

export type InboxQueuesContract = {
  organization_id?: string;
  queues: InboxQueueContract[];
};

export function normalizeInboxQueues(raw: unknown): InboxQueuesContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    queues: asArray(record.queues).map((item) => {
      const queue = asRecord(item);
      return {
        role_key: stringValue(queue.role_key),
        count: numberValue(queue.count),
        requires_human: numberValue(queue.requires_human),
        stalled: numberValue(queue.stalled),
        sla_breached: numberValue(queue.sla_breached),
        top_priority: numberValue(queue.top_priority),
      };
    }).filter((item) => Boolean(item.role_key)),
  };
}

export type ConversationDecisionSupportContract = {
  conversation_id: string;
  next_best_action?: string;
  priority_score?: number;
  priority_band?: string;
  confidence_score?: number;
  confidence_band?: string;
  queue: Record<string, unknown>;
  sla: Record<string, unknown>;
  explanation: Record<string, unknown>;
  risk_flags: Record<string, unknown>[];
};

export function normalizeConversationDecisionSupport(raw: unknown): ConversationDecisionSupportContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    conversation_id: stringValue(record.conversation_id),
    next_best_action: stringOrNull(record.next_best_action) ?? undefined,
    priority_score: nullableNumber(record.priority_score) ?? undefined,
    priority_band: stringOrNull(record.priority_band) ?? undefined,
    confidence_score: nullableNumber(record.confidence_score) ?? undefined,
    confidence_band: stringOrNull(record.confidence_band) ?? undefined,
    queue: asRecord(record.queue),
    sla: asRecord(record.sla),
    explanation: asRecord(record.explanation),
    risk_flags: asArray(record.risk_flags).map((item) => asRecord(item)),
  };
}

export type CRMPipelineSummaryContract = {
  total_leads: number;
  weighted_amount: number;
  stages: Record<string, unknown>[];
  lost_reasons: Record<string, unknown>[];
  recent_stage_changes: Record<string, unknown>[];
};

export function normalizeCRMPipelineSummary(raw: unknown): CRMPipelineSummaryContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    total_leads: numberValue(record.total_leads),
    weighted_amount: numberValue(record.weighted_amount),
    stages: asArray(record.stages).map((item) => asRecord(item)),
    lost_reasons: asArray(record.lost_reasons).map((item) => asRecord(item)),
    recent_stage_changes: asArray(record.recent_stage_changes).map((item) => asRecord(item)),
  };
}

export type IntegrationCenterContract = {
  organization_id?: string;
  summary: Record<string, unknown>;
  integrations: IntegrationContract[];
  observability: Record<string, unknown>;
  recent_sync_runs: Record<string, unknown>[];
  failed_receipts: Record<string, unknown>[];
  retry_hotspots: Record<string, unknown>[];
  dependency_map: Record<string, unknown>[];
};

export function normalizeIntegrationCenter(raw: unknown): IntegrationCenterContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    summary: asRecord(record.summary),
    integrations: asArray(record.integrations).map(normalizeIntegration).filter((item) => Boolean(item.id)),
    observability: asRecord(record.observability),
    recent_sync_runs: asArray(record.recent_sync_runs).map((item) => asRecord(item)),
    failed_receipts: asArray(record.failed_receipts).map((item) => asRecord(item)),
    retry_hotspots: asArray(record.retry_hotspots).map((item) => asRecord(item)),
    dependency_map: asArray(record.dependency_map).map((item) => asRecord(item)),
  };
}
