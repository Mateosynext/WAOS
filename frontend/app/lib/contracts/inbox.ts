import type { BotContract } from "./bots";
import { normalizeBot } from "./bots";
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
