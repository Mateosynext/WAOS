import type { BotContract } from "@/app/lib/contracts/bots";
import type { WizardRecommendedIntegration } from "../domain/wizardTypes";

export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function splitList(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item || "").trim()).filter(Boolean) : [];
}

export function botServices(bot?: BotContract | null) {
  return splitList(asRecord(asRecord(bot?.config_draft).business_knowledge).services);
}

export function botPolicies(bot?: BotContract | null) {
  return splitList(asRecord(asRecord(bot?.config_draft).business_knowledge).policies);
}

export function botIntegrations(bot?: BotContract | null) {
  return Object.keys(asRecord(asRecord(bot?.config_draft).integrations)).filter(Boolean);
}

export function integrationLabel(item: WizardRecommendedIntegration) {
  return item.name || item.provider || item.integration_key || "";
}
