import { getCurrentBotId, getSession } from "@/app/lib/session";
import { getConversationDecisionSupport, getConversations, getInboxOwnership, getInboxQueues, getInboxSavedViews } from "@/app/lib/data/inbox";
import { getVerticalProfile } from "@/app/lib/data/verticals";
import type { ConversationDecisionSupportContract, ConversationItem, InboxQueuesContract, InboxSavedViewContract } from "@/app/lib/contracts/inbox";
import type { VerticalProfileContract } from "@/app/lib/contracts/verticals";

export type InboxSearchParams = Record<string, string | string[] | undefined>;

export type InboxFiltersModel = {
  filter: string;
  sort: string;
  q: string;
  relation: string;
  mode: string;
  urgency: string;
  selectedId: string;
};

export type InboxOwnerSummary = Record<string, unknown>;

export type InboxPageModel = {
  filters: InboxFiltersModel;
  conversations: ConversationItem[];
  filtered: ConversationItem[];
  selected: ConversationItem | null;
  selectedIndex: number;
  listUrls: string[];
  savedViews: InboxSavedViewContract[];
  queueSummary: InboxQueuesContract;
  ownership: Record<string, unknown>;
  owners: InboxOwnerSummary[];
  decisionSupport: ConversationDecisionSupportContract | null;
  activeOrganizationId: string;
  hasOrganizationContext: boolean;
  currentOrg: { id?: string; vertical?: string | null; subvertical?: string | null } | null;
  verticalProfile: VerticalProfileContract | null;
  metrics: {
    total: number;
    human: number;
    pending: number;
    hot: number;
    ownerNow: number;
  };
};

export function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export function buildInboxQuery(params: Record<string, string | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const rendered = query.toString();
  return rendered ? `?${rendered}` : "";
}

function byFilter(item: ConversationItem, filter: string) {
  const status = String(item.status || "").toLowerCase();
  const leadStage = String(item.lead_stage || "").toLowerCase();
  const leadScore = Number(item.lead_score || 0);
  if (filter === "human") return status === "human_takeover";
  if (filter === "pending") return !item.last_outbound_at;
  if (filter === "hot") return leadStage.includes("hot") || leadScore >= 70;
  if (filter === "owner") return String(item.attention_tier || "").toLowerCase() === "owner_now";
  return true;
}

function searchMatches(item: ConversationItem, query: string) {
  if (!query) return true;
  const haystack = [
    item.contact_name,
    item.contact_phone,
    item.bot_name,
    item.summary,
    item.latest_message_preview,
    item.relationship_label,
    item.recommended_mode,
    item.attention_tier,
  ].join(" ").toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function sortConversations(items: ConversationItem[], sort: string) {
  const cloned = [...items];
  if (sort === "urgency") return cloned.sort((a, b) => Number(b.urgency_score || 0) - Number(a.urgency_score || 0));
  if (sort === "lead") return cloned.sort((a, b) => Number(b.lead_score || 0) - Number(a.lead_score || 0));
  if (sort === "owner") return cloned.sort((a, b) => String(a.owner_name || "").localeCompare(String(b.owner_name || "")));
  if (sort === "name") return cloned.sort((a, b) => String(a.contact_name || "").localeCompare(String(b.contact_name || "")));
  return cloned.sort((a, b) => String(b.updated_at || b.last_inbound_at || "").localeCompare(String(a.updated_at || a.last_inbound_at || "")));
}

export async function getInboxPageModel(searchParams?: InboxSearchParams): Promise<InboxPageModel> {
  const params = searchParams || {};
  const session = await getSession();
  const currentBotId = await getCurrentBotId();
  const filters: InboxFiltersModel = {
    filter: first(params.filter) || "all",
    sort: first(params.sort) || "priority",
    q: first(params.q) || "",
    relation: first(params.relation) || "all",
    mode: first(params.mode) || "all",
    urgency: first(params.urgency) || "all",
    selectedId: first(params.selected) || "",
  };

  const [conversations, savedViews, queueSummary, ownership] = await Promise.all([
    getConversations(filters.sort),
    getInboxSavedViews(),
    getInboxQueues(),
    getInboxOwnership(),
  ]);

  const currentOrg = session?.user.organizations.find((item) => item.id === session?.organizationId) || null;
  const verticalProfile = currentOrg?.vertical
    ? await getVerticalProfile(currentOrg.vertical, currentBotId || undefined, currentOrg.subvertical || undefined, session?.organizationId || undefined)
    : null;

  const filtered = sortConversations(
    conversations
      .filter((item) => byFilter(item, filters.filter))
      .filter((item) => searchMatches(item, filters.q))
      .filter((item) => filters.relation === "all" ? true : String(item.relationship_key || item.relationship_label || "").toLowerCase().includes(filters.relation.toLowerCase()))
      .filter((item) => filters.mode === "all" ? true : String(item.recommended_mode || "").toLowerCase() === filters.mode.toLowerCase())
      .filter((item) => filters.urgency === "all" ? true : String(item.urgency_level || "normal").toLowerCase() === filters.urgency.toLowerCase()),
    filters.sort,
  );

  const selected = filters.selectedId ? filtered.find((item) => item.id === filters.selectedId) || null : null;
  const decisionSupport = selected?.id ? await getConversationDecisionSupport(selected.id) : null;
  const selectedIndex = Math.max(filtered.findIndex((item) => item.id === selected?.id), 0);
  const listUrls = filtered.map((item) => `/inbox${buildInboxQuery({ filter: filters.filter, sort: filters.sort, q: filters.q, relation: filters.relation, mode: filters.mode, urgency: filters.urgency, selected: item.id })}`);
  const owners = Array.isArray((ownership as Record<string, unknown>).owners)
    ? ((ownership as Record<string, unknown>).owners as InboxOwnerSummary[])
    : [];
  const activeOrganizationId = String(session?.organizationId || conversations[0]?.organization_id || "").trim();

  return {
    filters,
    conversations,
    filtered,
    selected,
    selectedIndex,
    listUrls,
    savedViews,
    queueSummary,
    ownership,
    owners,
    decisionSupport,
    activeOrganizationId,
    hasOrganizationContext: Boolean(activeOrganizationId),
    currentOrg,
    verticalProfile,
    metrics: {
      total: conversations.length,
      human: conversations.filter((item) => String(item.status).toLowerCase() === "human_takeover").length,
      pending: conversations.filter((item) => !item.last_outbound_at).length,
      hot: conversations.filter((item) => String(item.lead_stage || "").toLowerCase().includes("hot") || Number(item.lead_score || 0) >= 70).length,
      ownerNow: conversations.filter((item) => String(item.attention_tier || "").toLowerCase() === "owner_now").length,
    },
  };
}
