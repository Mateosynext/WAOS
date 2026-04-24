import type { ConversationItem } from "@/app/lib/contracts/inbox";
import { safeText } from "@/app/lib/ui";

export function urgencyLabel(level?: string) {
  const normalized = String(level || "normal").toLowerCase();
  if (normalized === "critical") return "Crítica";
  if (normalized === "high") return "Alta";
  if (normalized === "medium") return "Media";
  return "Normal";
}

export function priorityLabel(item: ConversationItem) {
  if (String(item.status || "").toLowerCase() === "human_takeover") return "Humano";
  if (String(item.attention_tier || "").toLowerCase() === "owner_now") return "Dueño";
  if (String(item.urgency_level || "").toLowerCase() === "critical") return "Urgente";
  if (!item.last_outbound_at) return "Pendiente";
  if (Number(item.lead_score || 0) >= 70) return "Caliente";
  return "Normal";
}

export function compactValue(value: unknown, fallback = "sin dato") {
  return safeText(String(value || ""), fallback);
}
