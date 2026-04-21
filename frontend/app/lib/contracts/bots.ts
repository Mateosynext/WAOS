import {
  asArray,
  asRecord,
  booleanOrNull,
  booleanValue,
  JsonMap,
  nullableNumber,
  numberOrNull,
  numberValue,
  pickString,
  pickTimestamp,
  stringList,
  stringOrNull,
  stringValue,
  unwrapApiEnvelope,
} from "./shared";

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
